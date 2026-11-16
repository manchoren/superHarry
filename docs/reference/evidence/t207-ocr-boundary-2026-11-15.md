# T207 OCR local boundary evidence

Date: 2026-11-15. Scope: local request validation and unavailable-capability
fallback only. Tesseract and RapidOCR were not installed, imported, downloaded,
or executed.

## Implemented boundary

- Accepts only PNG, JPEG, GIF, and WebP content types whose detected container
  matches the declared type; validation is delegated to the dependency-free
  T206 image boundary.
- Limits input to 10 MiB and accepts only the approved initial language codes
  `spa` and `eng`, with at most one occurrence of each.
- Returns `UNAVAILABLE` when no OCR engine is available.
- Records the approved initial engine (`tesseract`) without importing,
  probing, installing, or executing it; RapidOCR is not an automatic fallback
  and remains unapproved in this boundary.
- Supports a bounded textual fallback (20,000 characters) marked as untrusted
  data; the boundary does not interpret markup, commands, or instructions.
- Publishes a declarative isolation contract requiring network-disabled,
  sandboxed execution and untrusted output. It does not implement those
  runtime controls in this local-only slice.
- Does not claim OCR quality, language recognition, latency, memory behavior,
  sandbox isolation, VM behavior, or production readiness.

## Validation

`\.venv\Scripts\python.exe manage.py test home.test_t207_ocr_boundary`

Observed result: `Ran 5 tests ... OK`. The tests cover accepted bilingual input,
format/language/mismatch rejection, input limits, explicit fallback, and the
no-engine result. No package installation or OCR invocation is part of the test.

Additional checks: `manage.py check` reported no issues; Python compilation and
`git diff --check` passed for the three T207 files. No package installation or
OCR invocation is part of these checks.

## Remaining T207 gates

T207 remains Pending. Exact engine artifacts, package approval, target-VM
validation, sandbox/resource enforcement, integrated OCR execution, recovery,
and deployment/production acceptance remain open. The historical choice of
Tesseract as the initial candidate does not authorize installation or runtime
execution.
