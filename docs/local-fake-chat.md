# Local fake chat demonstration

This is a development-only, single-process demonstration. It uses a deterministic fake response with no provider or network calls; it does not establish deployment, real-model, or VM acceptance. The in-process worker is not durable across a restart.

With the existing project environment and local development database prepared, run from the project root in PowerShell:

```powershell
$env:SUPERHARRY_FAKE_CHAT = "1"
python manage.py runserver 127.0.0.1:8000 --noreload
```

In a second terminal run the existing local HTTPS proxy with `caddy run --config Caddyfile`. Resolve `superharry.local` to `127.0.0.1` locally and follow the [clean installation guide](clean-local-install.md#run-the-local-fake-chat-through-https) to verify and trust the local development CA before browsing `https://superharry.local/`. Sign in with an existing local account, start a conversation and send a text message. The fake dispatcher is active only when both Django debug mode and the environment flag are enabled. Cancellation is observed between output chunks. This demonstration requires no guest access, attachments or tools.

The client recovery checks use Node.js built-in test modules and require no npm packages:

```powershell
node --test tests/test_chat_client.cjs
```

These checks simulate the browser interfaces and network responses; they do not replace a browser or deployment acceptance run.
