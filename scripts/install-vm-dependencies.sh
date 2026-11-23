#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_PATH="${SUPERHARRY_VENV_PATH:-$PROJECT_ROOT/.venv}"
INSTALL_TEST_DEPENDENCIES="${INSTALL_TEST_DEPENDENCIES:-0}"

die() { echo "install-vm-dependencies: $*" >&2; exit 1; }

[[ "$(uname -s)" == Linux ]] || die "Debian/Linux is required"
[[ "$(uname -m)" == aarch64 ]] || die "ARM64/aarch64 is required for the approved SQLCipher wheel"
[[ "$INSTALL_TEST_DEPENDENCIES" == 0 || "$INSTALL_TEST_DEPENDENCIES" == 1 ]] || die "INSTALL_TEST_DEPENDENCIES must be 0 or 1"
[[ "$VENV_PATH" == /* ]] || die "SUPERHARRY_VENV_PATH must be absolute"
[[ -f "$PROJECT_ROOT/requirements.txt" ]] || die "requirements.txt is missing from $PROJECT_ROOT"

"$PYTHON_BIN" - <<'PY'
import os
import platform
import re
import sys

if sys.version_info[:2] != (3, 13):
    raise SystemExit("Python 3.13 is required for the pinned ARM64 SQLCipher wheel")
if platform.machine() != "aarch64":
    raise SystemExit("ARM64/aarch64 is required")
glibc = os.confstr("CS_GNU_LIBC_VERSION") or ""
match = re.fullmatch(r"glibc (\d+)\.(\d+)", glibc)
if not match or tuple(map(int, match.groups())) < (2, 28):
    raise SystemExit("glibc 2.28 or newer is required; no system libraries will be installed automatically")
print(f"Target: {platform.system()} {platform.machine()}, Python {platform.python_version()}, {glibc}")
PY

if [[ ! -x "$VENV_PATH/bin/python" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_PATH"
fi
VENV_PYTHON="$VENV_PATH/bin/python"
[[ -x "$VENV_PYTHON" ]] || die "virtualenv creation failed: $VENV_PATH"

PIP_DISABLE_PIP_VERSION_CHECK=1 "$VENV_PYTHON" -m pip --isolated install \
  --only-binary=:all: -r "$PROJECT_ROOT/requirements.txt"

if [[ "$INSTALL_TEST_DEPENDENCIES" == 1 ]]; then
  [[ -f "$PROJECT_ROOT/requirements-test.txt" ]] || die "requirements-test.txt is missing"
  PIP_DISABLE_PIP_VERSION_CHECK=1 "$VENV_PYTHON" -m pip --isolated install \
    --only-binary=:all: -r "$PROJECT_ROOT/requirements-test.txt"
fi

# The application service must be able to read packages installed by this
# root-owned provisioner; keep the environment non-writable to the service.
chmod -R a+rX "$VENV_PATH"

PIP_DISABLE_PIP_VERSION_CHECK=1 "$VENV_PYTHON" -m pip check

# Inspect the installed ELF dependencies before importing any SQLCipher code.
SITE_PACKAGES="$("$VENV_PYTHON" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
SQLCIPHER_DIR="$SITE_PACKAGES/sqlcipher3"
[[ -d "$SQLCIPHER_DIR" ]] || die "sqlcipher3 package is missing after installation"
command -v ldd >/dev/null 2>&1 || die "ldd is unavailable; refusing to import the native binding"
mapfile -d '' NATIVE_LIBS < <(find "$SQLCIPHER_DIR" -type f -name '*.so' -print0)
(( ${#NATIVE_LIBS[@]} > 0 )) || die "no SQLCipher native library was found"
for native_lib in "${NATIVE_LIBS[@]}"; do
  linkage="$(ldd "$native_lib")" || die "ldd failed for $native_lib"
  printf '%s\n' "$linkage"
  if grep -q 'not found' <<<"$linkage"; then
    die "SQLCipher has an unresolved native dependency; install it only through a separately approved package change"
  fi
done

if [[ -f "$PROJECT_ROOT/scripts/verify_sqlcipher_binding.py" ]]; then
  "$VENV_PYTHON" "$PROJECT_ROOT/scripts/verify_sqlcipher_binding.py"
fi

echo "VM dependencies installed and checked in $VENV_PATH"
