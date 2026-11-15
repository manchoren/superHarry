# T230 budget visibility - 2026-11-14

Status: Pending. Windows checkout; constitution SHA-256
`59b3e1cc1f504f5dc510a7257a20a7d9e558b5b52033a7fc28831b62b3e92d8a`.

The principal-scoped budget page now displays unresolved reservations carried
from earlier UTC periods and available capacity after subtracting those holds.
It displays the 80% warning when current usage plus carried reservations
reaches the threshold, even if no new reservation has set the stored warning
flag. Current-period unknown reservations are already included in the current
reserved counter and are not subtracted twice. Global figures remain limited to
staff with the relevant permission. The page is informational; it does not
change the reservation or dispatch gates.

The accepted D2 amounts have no durable configuration or period-provisioning
workflow in the current code. Missing budget rows continue to reject external
admission. Automatically recreating a missing row without a protected durable
configuration and counter-integrity contract could reopen capacity after a
reset or deletion; this follow-up does not do so. Configurable, audited budget
changes, safe period creation, denial history, notification semantics, and
gateway/memory integration remain open. No live provider or VM validation is
claimed.

Windows validation: `.venv\Scripts\python.exe manage.py test
home.test_budget_views home.test_application_budget` passed 17 tests, including
prior-period reserved and unknown holds, foreign-user isolation, threshold and
zero-capacity cases, and Spanish labels. The full `manage.py test` run passed
654 tests with 11 skipped; the additional Spanish assertions were added after
that run and passed in the focused rerun.
