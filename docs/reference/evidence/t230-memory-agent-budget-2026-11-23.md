# T230 memory-agent budget integration review - 2026-11-23

Status: T230 implementation and isolated VM acceptance completed on
2026-11-23. Dispatch remains fail-closed by default. Server configuration declares route
eligibility; it does not independently prove zero charges for a particular
Nous account/model route, so account-specific verification is still required
before activation under D2. No provider request
or production database was used in this validation.

## Current code boundary

- `home/omniroute_client.py::memory_agent_search()` delegates to the budgeted
  `home.memory_agent_dispatch` boundary. It accepts an authenticated
  principal, operation ID and explicit request disclosure decision; it accepts
  no caller-supplied provider, model, endpoint, budget identity or reservation.
- The route is fixed to Nous Portal model `upstage/solar-mini4:free`, upstream
  `upstage`, with `reasoning_effort=none`, a 2,048-token output cap, verified
  constitution and bounded query/memory snapshot.
- Before dispatch it checks administrator enablement, the declared free plan,
  absent billing methods, exact approved model and request disclosure. It
  reserves serialized UTF-8 bytes plus output cap against the user and global
  daily/monthly budgets, then marks the hold unknown before network I/O. It
  settles only exact correlated usage for the expected model and preserves
  ambiguous or malformed outcomes without replay.
- `home.memory_access.py` and `home.memory_agent_contract.py` reload visible
  records for the authenticated principal and validate returned IDs. Guest,
  inactive, unsaved, foreign and deleted records cannot be included.
- `home/memory_retrieval.py::retrieve_authorized_memory_records()` performs
  bounded local semantic/keyword retrieval and requires an injected
  `charge_usage` callback. It does not make a model call, and its content-size
  accounting is not a substitute for provider token accounting.
- Gateway and memory-agent consumers share the same application-budget
  reservation and settlement lifecycle. Local inference is not charged to
  external allowances.

## Period activation and rollover

Saving the audited budget configuration creates the current daily and monthly
periods and synchronizes limits without resetting usage or reservations.
`manage.py provision_application_budgets` applies all configured scopes.
The persistent chat worker provisions them at startup and checks again every
60 seconds for UTC day/month rollover. Missing configuration fails closed;
dispatch never creates budget rows on demand. Unresolved prior-period holds
remain encumbered.

## Earlier validation (superseded)

On 2026-11-23, against the local Windows checkout and Django test database:

```text
python manage.py test home.test_t226_dispatch_context home.test_application_budget home.test_memory_access home.test_memory_recall
Ran 32 tests; OK. Django system check: no issues.

python manage.py test home.test_free_provider_dispatch home.test_gemini_chat home.test_application_budget home.test_t226_dispatch_context
Ran 55 tests; OK. Django system check: no issues.
```

Those early tests covered only the fail-closed stub and existing consumers.
Their statement that dispatch and VM acceptance remained open was accurate then
and is superseded by the integrated implementation and acceptance recorded
below.

## Intermediate status history (superseded)

The older implementation and follow-up paragraphs recorded that dispatch and
VM acceptance were still open. That was an intermediate checkpoint; the
integrated implementation and acceptance below supersede it.

## Official Nous Portal API documentation check - 2026-11-23

Nous Portal's own comparison page states that its API is OpenAI-compatible at
`https://inference-api.nousresearch.com/v1` and accepts OpenRouter-style model
IDs. It also says API keys use pay-as-you-go credits rather than included plan
usage. The page listed Solar Mini 4 as free on 2026-11-10 and directs users to
the current Free filter for availability. These published details establish
the API shape and model-ID convention, but do not establish the current price
for API-key calls to this model, exact usage/framing behavior, enforceable
non-reasoning controls, or application route admission. No live API request or
provider activation was made. See the [Nous Portal API and pricing notes](https://portal.nousresearch.com/compare).

## Owner disclosure authorization update - 2026-11-23

The owner withdrew the prior no-disclosure restriction after confirming Nous
is the provider designated in `product-requirements.md` §8.1.1 and accepted
provider disclosure for this route. D2 still requires account-specific verification that the exact account/model
route is zero-billable and prohibits paid or ambiguous fallback.
The code keeps dispatch disabled by default and requires an explicit
per-request disclosure decision. The official [Nous model catalog](https://portal.nousresearch.com/models)
currently lists the canonical route as FREE; Nous also states that API keys
use pay-as-you-go credits on its [API comparison page](https://portal.nousresearch.com/compare).
No live API-key or inference request was made.

## Integrated T230 validation - 2026-11-23

Local Windows:

```text
manage.py test -v 1
Ran 996 tests; OK (14 skipped).
pytest tests/test_omniroute_client.py
93 passed, 3 skipped.
manage.py check: no issues.
manage.py makemigrations --check --dry-run: no changes detected.
```

ARM64 Debian 13 development VM, isolated archive of commit `1ee9f73` plus
only the T230 source/test overlay, disposable Django test database:

```text
Ran 87 tests; OK.
manage.py check: no issues.
manage.py makemigrations --check --dry-run: no changes detected.
```

The VM had Python 3.13.5 and Django 6.1.2. Tests used synthetic users,
memories, budgets and a fake provider client; the installed application and
database were not touched. Live provider billing/behavior and production
activation remain outside this test and under T241/release activation.
