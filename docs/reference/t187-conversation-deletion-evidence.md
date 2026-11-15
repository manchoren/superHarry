# T187 conversation deletion evidence - 2026-11-14

Status: Pending. Windows checkout; constitution SHA-256
`59b3e1cc1f504f5dc510a7257a20a7d9e558b5b52033a7fc28831b62b3e92d8a`.

Given a signed-in owner, when they request deletion, the application shows a
confirmation page and requires a CSRF-protected POST. A completed conversation
without a claimed or interrupted worker is removed with its messages, turns,
events and completed jobs. The deletion and a content-free audit event commit
in one transaction. Unknown application-budget reservations remain intact.
Given another user, a missing confirmation, active work, an unresolved claim,
or an unavailable audit store, deletion is refused. An initial conditional
write serializes the deletion check with competing SQLite writers; turn
creation handles a conversation removed before its own transaction.

An interrupted job may still have a live worker under the existing claim-age
recovery contract. Deletion therefore refuses interrupted as well as claimed
jobs. A follow-up now marks the job done when its original worker has actually
returned and the turn is terminal, allowing confirmed deletion while leaving
unknown budget reservations untouched. A stale terminal turn alone no longer
marks its claim done. Migration 0032 now records local worker return even if
the turn is not terminal yet, so subsequent stale recovery can terminate the
turn and mark that particular job done. If the worker crashes before recording
its return, an explicit safe resolution path remains to be implemented. Actual
cross-process contention, browser accessibility and target-VM behavior have
not been validated. This slice does not claim cancellation of a remote request
or full T187 completion.

Windows validation:

- `.venv\Scripts\python.exe manage.py test home.test_t187_history_isolation
  home.test_chat home.test_gemini_queue home.test_theme` passed 59 tests.
- `.venv\Scripts\python.exe manage.py test` passed 649 tests with 11 skipped;
  the additional reservation-retention assertion was added afterwards, and
  the focused `home.test_t187_history_isolation` selection then passed five.
- The first focused command named nonexistent `home.test_chat_api` and failed
  to import it; the corrected command above passed.
- In a temporary isolated SQLite database, migration 0031 was applied and a
  synthetic deletion audit event created. Reversal was refused and the event
  remained intact. No VM or production database was changed.
- Worker-return follow-up: `.venv\Scripts\python.exe manage.py test
  home.test_t229_recovery home.test_gemini_queue home.test_t187_history_isolation`
  passed 25 tests. The focused test confirms deletion is blocked while a stale
  worker is running, succeeds once that worker returns, and leaves its unknown
  reservation held. The full `manage.py test` suite passed 650 tests with 11
  skipped. This is synthetic local evidence, not remote-stop proof.
- SQLite contention follow-up: separate connections in two threads exercised
  a turn-creation HTTP request while deletion held its transaction and a
  deletion HTTP request while a synthetic turn-write transaction held its lock.
  The first attempt exposed an unhandled lock error during the initial owner
  lookup; turn creation and deletion now return 503 when that lookup cannot
  access the database. Both orderings passed in `home.test_t187_concurrency`.
  This is not a cross-process or VM test.
- The initial full-suite runs with these tests failed because two earlier
  migration tests left the shared schema at migration 0010, before the chat
  risk-acceptance column. Their cleanup now restores the current migration
  graph. The migration-test/concurrency sequence passed four tests and the
  subsequent full `manage.py test` passed 652 tests with 11 skipped. Earlier
  green suite counts did not detect this schema leak and do not establish that
  tests following those migration tests used the current schema.
- Worker-return evidence follow-up: `.venv\Scripts\python.exe manage.py test
  home.test_t229_recovery home.test_gemini_queue home.test_t187_history_isolation`
  passed 28 tests, including a return before recovery, an exception, a refusal
  to replay a queued job with exit evidence, and preserved unknown usage. The
  full suite passed 658 tests with 11 skipped before the exception regression
  was added; the focused rerun includes that regression. In a temporary SQLite
  database, migration 0032 preserved an existing claim with no invented exit
  timestamp, refused a lossy rollback, and reversed/reapplied after the
  synthetic evidence was cleared. The first isolated attempt used the current
  ORM against the earlier schema and failed; the repeat used historical models.
  This records local execution return only, not remote provider termination.
