# T203 missed-job recovery evidence (2026-11-15)

Implemented a pure local post-restart evaluator in `home/missed_job_recovery.py`.
It produces an immutable evaluation and an explicit reconciliation plan; it does
not claim, enqueue, dispatch, retry, mutate `MaintenanceJob`, or execute a job.

The context boundary now fails closed for structurally invalid values, including
falsy non-mappings, and rejects memory-bearing fields such as `memory_records`,
conversation history, transcripts, and protected context. This evaluator carries
job metadata only; memory retrieval remains outside T203 and must use its own
authorization boundary.

The evaluator preserves the original task context and durable cancellation
decision. Jobs with unknown authority (possibly claimed or dispatched) require
reconciliation and are never replayed automatically. Expired or unauthorized
jobs are skipped or denied. Eligible missed jobs receive only a `recover`
decision for a future authorized scheduler integration.

Validation:

```text
.\\venv\\Scripts\\python.exe manage.py test home.test_t203_missed_job_recovery
6 tests, OK
```

Limits: this does not provide persistence, a scheduler, execution, external
outcome reconciliation, VM/systemd restart handling, deployment, or production
acceptance. T203 remains Pending.
