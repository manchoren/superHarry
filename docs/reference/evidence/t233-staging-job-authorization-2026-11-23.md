# T233 staging job authorization review - 2026-11-23

## Finding

No current application contract binds a sandbox job to its owner, an explicit
set of `StoredFile` identifiers, and a server-derived staging destination.
`HeavyJob` is the shared resource governor's queue/seat record; it has no
destination path or authorized-file relation. `GeminiChatJob` tracks durable
chat dispatch, not sandbox work. `stage_for_authorized_job()` currently accepts
an arbitrary `destination_dir` beneath the configured staging root and checks
the file owner's identity, but it cannot verify that the directory belongs to
an active job or that the job selected that file. Its only callers are tests.

Creating a job ID from `HeavyJob`, inferring a path convention, or accepting a
caller-supplied job token would invent authorization semantics and would not
prove the requested job/file relationship. No runtime staging was activated or
changed in this review.

## Closure path

1. T232 must provide the authorized tool/agent handoff contract that can
   request a file for a specific operation.
2. T192 or another accepted sandbox-job contract must identify the owner,
   operation, selected file IDs, and server-owned destination.
3. T233 can then accept that job record or an unforgeable application-owned
   authorization object, recheck owner and selected-file membership at copy
   time, derive the destination server-side, and test revocation, cancellation,
   cross-user and directory-replacement races.

T233 remains Pending. Existing upload/download, owner checks, bounded verified
I/O, and HTTP denial tests remain valid local implementation evidence; they do
not establish explicit sandbox-job authorization. No schema, dependency,
provider, VM, deployment, or production change was made.

## Inspection

- Read `home/file_store.py`, the `HeavyJob`, `GeminiChatJob` and `StoredFile`
  model definitions, all `stage_for_authorized_job()` callers, T233 acceptance,
  existing T233 evidence, and current T232/T192 task records.
- Search confirmed the staging helper has no application runtime caller.
- Documentation-only review; no application tests were run.
