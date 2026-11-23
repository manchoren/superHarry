# T236 local theme and browser review - 2026-11-23

## Scope

The review used a synthetic user/admin and isolated database at `C:\Users\Matias\AppData\Local\Temp\superharry-t236-207c20700d464805a85a1a745399c4fd\isolated.sqlite3`. Django listened on `127.0.0.1:18765` behind a temporary HTTPS proxy on `127.0.0.1:18766`, exercising secure cookies and origin checks. No repository or production database, provider, external service, or dependency installation was used. Chrome 135 headless used the already available Playwright Core.

## Behavior exercised

- Device selection persists across reload; explicit light/dark ignores OS changes and system mode tracks emulated `prefers-color-scheme` changes. Signed-in account choice persists after save/reload and overrides device preference.
- Keyboard focus and sampled text/control contrast were checked in light and dark themes across password reset, login, authenticated chat, budgets, audit events, conversation deletion confirmation (GET only), Django admin index and user list: 7 page types x 2 themes (14 cases). Every case returned HTTP 200, had visible keyboard focus, sampled contrast at least 4.5:1, and had no browser errors or failed requests.
- At a 390px viewport, no page had document-level horizontal overflow. The audit table scrolls inside a labeled, keyboard-focusable `role=region`; a final check after the no-wrap refinement measured its 1481px table inside a 390px region.
- The review found and corrected three presentation defects: disabled composer contrast, audit-table mobile overflow, and Django admin's low-contrast/too-thin dark-mode keyboard focus. Admin focus now has a 3.2px outline; measured outline contrast was 5.41:1 light and 10.31:1 dark.
- Browser screenshots are linked below. Login, chat and password reset images include desktop theme examples; chat includes mobile light/dark and keyboard focus; budget, audit, audit mobile, delete confirmation, admin index and admin user list are also captured.

## Validation

- `node --test tests/test_theme_client.cjs` - 7 passed.
- `.venv\Scripts\python.exe manage.py test home.test_theme` - 11 passed; system checks passed.
- Expanded browser script `C:\Users\Matias\AppData\Local\Temp\superharry-t236-207c20700d464805a85a1a745399c4fd\browser-runtime\remaining-pages.cjs` - 14 page/theme cases passed; audit viewport contained its wide table; zero page errors or failed requests.
- Final audit mobile recheck `audit-mobile-recheck.cjs` - light and dark passed: document/region 390px, table 1481px, no-wrap cell text and Spanish accessible region name.
- `.venv\Scripts\python.exe manage.py test` - 1009 passed, 14 skipped (combined worktree).
- `.venv\Scripts\python.exe manage.py check` - passed.
- `.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` - no changes detected.
- `git diff --check` - passed; only standard Git LF/CRLF normalization notices.

## Screenshots

- Login dark desktop: [login](t236-theme-browser-2026-11-23/login-dark-desktop.png)
- Chat desktop: [dark](t236-theme-browser-2026-11-23/chat-dark-desktop.png), [light](t236-theme-browser-2026-11-23/chat-light-desktop.png), [keyboard focus](t236-theme-browser-2026-11-23/chat-dark-keyboard-focus.png)
- Chat mobile 390 x 844: [dark](t236-theme-browser-2026-11-23/chat-dark-mobile.png), [light](t236-theme-browser-2026-11-23/chat-light-mobile.png)
- Password reset dark: [reset](t236-theme-browser-2026-11-23/password-reset-dark-desktop.png)
- Budget light: [budget](t236-theme-browser-2026-11-23/budget-status-light-desktop.png)
- Audit dark desktop/mobile: [desktop](t236-theme-browser-2026-11-23/audit-events-dark-desktop.png), [mobile](t236-theme-browser-2026-11-23/audit-events-dark-mobile.png)
- Conversation confirmation light (GET only): [confirmation](t236-theme-browser-2026-11-23/conversation-delete-light-desktop.png)
- Django admin: [index](t236-theme-browser-2026-11-23/admin-index-dark-desktop.png), [user list](t236-theme-browser-2026-11-23/admin-user-list-light-desktop.png)

## Limits

OS theme changes were emulated in Chrome. This is synthetic local/browser evidence; it does not claim screen-reader, physical-device, VM, provider, deployment or release acceptance. The local T236 acceptance criterion in the specification is met; those broader checks are not prerequisites for closing this local feature scope.
