#!/usr/bin/env bash
set -Eeuo pipefail

# Install and bootstrap OmniRoute for superHarry on Debian ARM64.
# Provider values are read from PROVIDER_ENV_FILE and are never printed.

OMNI_USER="${OMNI_USER:-omniroute}"
OMNI_HOME="${OMNI_HOME:-/var/lib/omniroute}"
OMNI_ENV="${OMNI_ENV:-/etc/omniroute/omniroute.env}"
OMNI_PORT="${OMNI_PORT:-20128}"
OMNI_HOST="${OMNI_HOST:-127.0.0.1}"
PROVIDER_ENV_FILE="${PROVIDER_ENV_FILE:-/etc/omniroute/provider.env}"
PACKAGE="${OMNIROUTE_PACKAGE:-omniroute@3.8.54}"
NODE_VERSION="${NODE_VERSION:-24.14.1}"
API_KEY_FILE="${API_KEY_FILE:-/etc/omniroute/superharry-api-key}"

die() { echo "install-omniroute: $*" >&2; exit 1; }
need_root() { [ "$(id -u)" -eq 0 ] || die "run as root"; }
require_env_file() { [ -r "$PROVIDER_ENV_FILE" ] || die "missing PROVIDER_ENV_FILE=$PROVIDER_ENV_FILE"; }

valid_provider_env() {
  awk -F= '
    /^(GROQ_API_KEY|OPENROUTER_API_KEY|GEMINI_API_KEY)=/ { found[$1]=1; next }
    /^[[:space:]]*#/ || /^[[:space:]]*$/ { next }
    { bad=1 }
    END { exit (bad || !found["GROQ_API_KEY"] || !found["OPENROUTER_API_KEY"] || !found["GEMINI_API_KEY"]) }
  ' "$PROVIDER_ENV_FILE"
}

install_runtime() {
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y ca-certificates curl openssl python3 xz-utils nodejs npm
  local major
  major="$(node -p 'process.versions.node.split(".")[0]')"
  if [ "$major" -lt 22 ]; then
    local archive="node-v${NODE_VERSION}-linux-arm64.tar.xz"
    local target="/opt/node-v${NODE_VERSION}-linux-arm64"
    curl --fail --silent --show-error --location --retry 3 \
      "https://nodejs.org/dist/v${NODE_VERSION}/${archive}" -o "/tmp/${archive}"
    rm -rf "$target"
    tar -xJf "/tmp/${archive}" -C /opt
    ln -sfn "$target/bin/node" /usr/local/bin/node
    ln -sfn "$target/bin/npm" /usr/local/bin/npm
    ln -sfn "$target/bin/npx" /usr/local/bin/npx
    rm -f "/tmp/${archive}"
  fi
  [ "$(node -p 'process.versions.node.split(".")[0]')" -ge 22 ] || die "Node.js 22+ is required"
  npm install --global "$PACKAGE"
}

prepare_files() {
  install -d -o "$OMNI_USER" -g "$OMNI_USER" -m 0750 "$OMNI_HOME" /etc/omniroute
  chown root:"$OMNI_USER" "$PROVIDER_ENV_FILE"
  chmod 0640 "$PROVIDER_ENV_FILE"

  touch "$OMNI_ENV"
  grep -q '^OMNIROUTE_SERVER_HOST=' "$OMNI_ENV" || echo "OMNIROUTE_SERVER_HOST=$OMNI_HOST" >> "$OMNI_ENV"
  grep -q '^OMNIROUTE_PORT=' "$OMNI_ENV" || echo "OMNIROUTE_PORT=$OMNI_PORT" >> "$OMNI_ENV"
  grep -q '^REQUIRE_API_KEY=' "$OMNI_ENV" || echo 'REQUIRE_API_KEY=true' >> "$OMNI_ENV"
  grep -q '^DATA_DIR=' "$OMNI_ENV" || echo "DATA_DIR=$OMNI_HOME" >> "$OMNI_ENV"
  grep -q '^API_KEY_SECRET=' "$OMNI_ENV" || echo "API_KEY_SECRET=$(openssl rand -hex 32)" >> "$OMNI_ENV"
  grep -q '^STORAGE_ENCRYPTION_KEY=' "$OMNI_ENV" || echo "STORAGE_ENCRYPTION_KEY=$(openssl rand -hex 32)" >> "$OMNI_ENV"
  grep -q '^INITIAL_PASSWORD=' "$OMNI_ENV" || echo "INITIAL_PASSWORD=$(openssl rand -base64 36 | tr -d '/+=\\n')" >> "$OMNI_ENV"
  chown root:"$OMNI_USER" "$OMNI_ENV"
  chmod 0640 "$OMNI_ENV"
}

install_unit() {
  cat > /etc/systemd/system/omniroute.service <<EOF
[Unit]
Description=OmniRoute AI gateway
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$OMNI_USER
Group=$OMNI_USER
WorkingDirectory=$OMNI_HOME
EnvironmentFile=$OMNI_ENV
EnvironmentFile=$PROVIDER_ENV_FILE
ExecStart=/usr/local/bin/omniroute
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$OMNI_HOME
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  systemctl enable --now omniroute.service
}

probe() {
  local base="http://$OMNI_HOST:$OMNI_PORT"
  local key
  key="$(cat "$API_KEY_FILE")"
  curl --fail --silent --show-error --max-time 20 "$base/api/health" >/dev/null
  curl --fail --silent --show-error --max-time 20 -H "Authorization: Bearer $key" "$base/v1/models" >/dev/null
}

bootstrap() {
  local url="http://$OMNI_HOST:$OMNI_PORT"
  local password
  password="$(awk -F= '$1=="INITIAL_PASSWORD" {sub(/^[^=]*=/, ""); print; exit}' "$OMNI_ENV")"
  [ -n "$password" ] || die "INITIAL_PASSWORD is missing from $OMNI_ENV"
  API_KEY_FILE="$API_KEY_FILE" OMNI_URL="$url" OMNI_ENV_FILE="$OMNI_ENV" PROVIDER_FILE="$PROVIDER_ENV_FILE" \
    INITIAL_PASSWORD="$password" python3 - <<'PY'
import json, os, pathlib, urllib.error, urllib.request

base = os.environ['OMNI_URL']
key_path = pathlib.Path(os.environ['API_KEY_FILE'])
env = {}
for raw in pathlib.Path(os.environ['PROVIDER_FILE']).read_text().splitlines():
    if raw and not raw.startswith('#') and '=' in raw:
        k, v = raw.split('=', 1); env[k] = v

def request(path, method='GET', payload=None, headers=None):
    data = None if payload is None else json.dumps(payload).encode()
    h = {'Content-Type': 'application/json', **(headers or {})}
    req = urllib.request.Request(base + path, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return res.status, json.loads(res.read() or b'{}'), dict(res.headers)
    except urllib.error.HTTPError as exc:
        exc.read()
        raise RuntimeError(f'{method} {path} returned HTTP {exc.code}')

cookie = None
status, body, headers = request('/api/auth/login', 'POST', {'password': os.environ['INITIAL_PASSWORD']})
cookie = headers.get('Set-Cookie', '').split(';', 1)[0]
if not cookie:
    raise RuntimeError('OmniRoute login did not return a session cookie')
admin = {'Cookie': cookie}
_, providers, _ = request('/api/providers', headers=admin)
existing = {p.get('name') for p in providers.get('providers', providers if isinstance(providers, list) else [])}
for provider, env_name in (('groq', 'GROQ_API_KEY'), ('openrouter', 'OPENROUTER_API_KEY'), ('gemini', 'GEMINI_API_KEY')):
    name = f'{provider}-default'
    if name not in existing and env.get(env_name, '').strip():
        request('/api/providers', 'POST', {'provider': provider, 'name': name, 'authType': 'api_key', 'apiKey': env[env_name]}, admin)
# Upstream provider probes are intentionally omitted; bootstrap never spends provider credits.

api_key = key_path.read_text().strip() if key_path.exists() else ''
if api_key:
    try:
        request('/v1/models', headers={'Authorization': f'Bearer {api_key}'})
    except RuntimeError:
        api_key = ''
if not api_key:
    _, created, _ = request('/api/keys', 'POST', {'name': 'superharry', 'scopes': ['inference']}, admin)
    api_key = created.get('key', '')
    if not api_key:
        raise RuntimeError('OmniRoute did not return the generated API key')
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_text(api_key + '\n')
    os.chmod(key_path, 0o640)
PY
  chown root:"$OMNI_USER" "$API_KEY_FILE"
  chmod 0640 "$API_KEY_FILE"
}

main() {
  [[ "$PACKAGE" =~ ^(@[A-Za-z0-9._-]+/)?[A-Za-z0-9._-]+@[0-9]+\.[0-9]+\.[0-9]+([+-][A-Za-z0-9.-]+)?$ ]] || die "OMNIROUTE_PACKAGE must use an exact version"
  [[ "$NODE_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "NODE_VERSION must be an exact version"
  need_root
  require_env_file
  valid_provider_env || die "provider env must contain only GROQ_API_KEY, OPENROUTER_API_KEY and GEMINI_API_KEY"
  id "$OMNI_USER" >/dev/null 2>&1 || useradd --system --home-dir "$OMNI_HOME" --create-home --shell /usr/sbin/nologin "$OMNI_USER"
  install_runtime
  prepare_files
  install_unit
  for _ in $(seq 1 30); do curl --silent --fail "http://$OMNI_HOST:$OMNI_PORT/api/health" >/dev/null && break; sleep 2; done
  bootstrap
  probe
  echo "OmniRoute installed and healthy on $OMNI_HOST:$OMNI_PORT (upstream providers were not probed)"
}

main "$@"
