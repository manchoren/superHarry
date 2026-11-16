# T236 theme preference storage-sync evidence

## Scope

This bounded slice keeps the existing light/dark/system controls and account-backed
save flow unchanged. Device-local preferences now synchronize between open tabs via
the browser `storage` event. Account-backed preferences remain authoritative and
ignore device storage events.

## Validation

- `node --test tests/test_theme_client.cjs`: 7 tests passed.
- `.\\venv\\Scripts\\python.exe manage.py test home.test_theme`: 8 tests passed.
- Signed-out conversation-delete rendering no longer emits `data-account-theme`, so
  device-local preferences are not mistaken for an account preference on that page.
- Existing server-side theme tests remain in `home.test_theme`.
- No policy, model, migration, provider, VM, or production changes were made.

## Limits

This does not constitute T236 closure. Browser visual, keyboard, mobile, contrast,
and complete page-by-page acceptance still require separate evidence.
