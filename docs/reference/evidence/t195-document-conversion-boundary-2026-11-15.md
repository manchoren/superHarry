# T195 document conversion boundary evidence

**Status:** Pending; bounded local planning and validation slice only.

This slice adds `home.document_conversion`, a pure fail-closed boundary for the
first-release DOCX-to-PDF and XLSX-to-PDF operations declared by T200. It
requires a T200 catalog capability, an explicit sandbox plan, disabled network,
no-new-privileges, and bounded CPU, memory, writable storage, process count,
input, and output values. Reported output size is checked before any future
authorized store handoff.

The module does not read document bytes, invoke LibreOffice or another
converter, create processes, install packages, access the filesystem, or
perform conversion. It does not establish T192 sandbox enforcement, T193
package approval, T233 staging integration, VM isolation, deployment, or
production acceptance.

Audit note: the local contract explicitly admits both required first-release
operations (`docx_to_pdf` and `xlsx_to_pdf`), requires the catalog capability,
and rejects execution/network access. No local defect was found in that
boundary during this review; no converter or LibreOffice was invoked.

Validation performed:

- `\.venv\Scripts\python.exe manage.py test home.test_document_conversion`
- `\.venv\Scripts\python.exe manage.py check`
- `\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run`
- `git diff --check`

