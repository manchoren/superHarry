# T206 image validation evidence

Status: Pending. This is a local implementation slice only; it does not
establish sandbox, VM, deployment, OCR, production or release acceptance.

## Implemented slice

- Added a dependency-free, fail-closed image ingress validator.
- PNG, GIF, JPEG and WebP inputs must have a recognized signature and a
  minimally parseable dimension header; unknown or truncated image containers
  are rejected.
- Enforced maximum dimension (10,000 per axis), maximum canvas
  (25,000,000 pixels), and a bounded pixel-to-input expansion ratio (1,000).
- Rejected JPEG `Exif`, PNG `eXIf`, and WebP `EXIF` metadata before any future
  decoder or OCR process receives the staged file.
- File validation now checks the complete stored payload (not only the first
  MiB), rejects invalid declared sizes, and detects metadata placed after the
  header window.
- Integrated the check into `home.file_store.upload` after bounded storage and
  before the database record/audit event is committed. Failed validation cleans
  up the exclusive temporary file through the existing upload error path.
- No image decoder, metadata rewriting, dependency installation, external
  provider, real user data, VM or production service was used.

## Validation

Environment: Windows PowerShell, synthetic byte fixtures only.

- `.venv\\Scripts\\python.exe manage.py test home.test_file_store` — 28 tests
  passed, 1 platform-dependent symlink test skipped.
- `.venv\\Scripts\\python.exe manage.py check` — passed.
- `.venv\\Scripts\\python.exe manage.py makemigrations --check --dry-run` —
  no changes detected.
- `git diff --check` — no whitespace errors.

## Open gates

The validator does not prove full format conformance, safe decoding of all
codec features, metadata stripping, archive/polyglot policy, sandbox isolation,
resource enforcement in a worker, VM behavior, deployment correctness or
production acceptance. T206 remains Pending.
