# T200 document-skill catalog evidence

## Scope

`home/document_skills.py` adds a pure, deterministic in-memory catalog of
reusable document-skill descriptors. It consumes the parsed T196
`SkillDefinition`, validates document formats, declared operations, file
permissions and bounded CPU/memory/input/output limits, and permits selection
only for capabilities explicitly declared by the descriptor.

Validated resource limits are copied into an immutable mapping, so later
caller mutation cannot widen them.

The catalog does not persist, install, approve, load, execute or convert a
skill. Manifest permissions and roles remain untrusted claims. Sandbox
execution belongs to T192/T195 and lifecycle approval/integrity belongs to
T197-T199; those dependencies are not represented as complete here.

## Validation

```text
.\.venv\Scripts\python.exe manage.py test home.test_document_skills
5 tests, OK
.\.venv\Scripts\python.exe manage.py check
OK
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
No changes detected
git diff --check
OK
```

No packages were installed, no document was processed, and no conversion,
VM, deployment or production acceptance was performed. T200 remains Pending.
