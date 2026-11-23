# T230 budget visibility - 2026-11-14

Status: implementation and isolated VM acceptance complete for the current product-first scope; constitution SHA-256
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

T230 follow-up (2026-11-15): `mark_unknown` now validates reservation IDs and
performs the reserved-to-unknown transition under a row lock and transaction.
Repeated recovery is idempotent, while missing, malformed, or already-settled
reservations fail closed with the budget error contract. This protects the
unknown reservation held across ambiguous gateway/fallback outcomes without
changing provider routing or VM behavior. Focused validation is recorded in the
handoff; no live provider, deployment, VM, or production gate is claimed.

T230 local slice (2026-11-15): added durable per-scope daily/monthly limit
configuration and an explicit, idempotent `provision_period_budgets` operation.
It creates only the UTC period rows requested by the caller, preserves existing
usage/reservations, and fails closed when configuration is missing or malformed.
`reserve()` still does not auto-create rows, so a reset or deleted configuration
cannot silently reopen external capacity. This is local contract evidence only;
gateway/provider acceptance, VM rollover and production acceptance remain open.

T230 current-period activation path (2026-11-23): saving a budget configuration
through the audited admin now provisions its current daily and monthly rows and
synchronizes their hard limits without resetting `used` or `reserved`. Added
`manage.py provision_application_budgets` to apply durable configurations to
all scopes and create missing current UTC periods. It is idempotent and fails
closed on invalid/missing scope configuration; the dispatch path still does not
auto-create rows. The persistent chat worker now provisions periods at startup and retries every
60 seconds for UTC rollover. VM testing used a disposable test database; no
production database was changed.

T230 administrative configuration slice (2026-11-15): registered
`ApplicationBudgetConfiguration` in Django Admin with canonical scope-key
validation, deletion disabled, and an append-only audit event for every
persisted change. The save is transactional: if the audit writer is
unavailable, the configuration write is rolled back and the admin request
fails closed. This does not authorize paid routes, activate providers, or
prove VM/release acceptance.

Focused validation for the administrative slice: 25 tests passed across the
admin, application-budget, and budget-status suites; `manage.py check`,
`makemigrations --check --dry-run`, and `git diff --check` also passed.

Validation of this slice: `manage.py check`, `makemigrations --check --dry-run`,
the focused budget/view suite (21 tests), and a focused rerun of the unrelated
storage-pressure test passed. The full suite reached 873 tests with 11 skips
but had one order-sensitive failure in
`PersistedCleanupInventoryTests.test_inventory_has_a_hard_candidate_limit`;
that test passed when run alone. No T230-focused failure was observed.


Current integrated memory-dispatch, budget settlement, period rollover, and isolated VM results are consolidated in [T230 integrated evidence](evidence/t230-memory-agent-budget-2026-11-23.md). Live-provider billing and release activation remain deferred under T241/release; dispatch stays disabled unless the exact account/model route passes D2 configuration gates.
