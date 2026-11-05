# Development model quota controls

The optional `SUPERHARRY_REQUIRE_MODEL_QUOTAS=1` control adds a model ceiling
to the existing shared request and token ceilings for Gemini, Groq and
OpenRouter. It is off by default; it does not enable any provider or create
allowances. When enabled, each exact provider/model combination needs a
`ProviderModelQuota` for both the provider's shared request quota and its
shared token quota. Missing or exhausted model quotas block the attempt.
Limits and provisioning remain administrator policy decisions; this development
slice does not provide an approved administration workflow.

Each new reservation records its model quota alongside the original shared
quota. Admission and settlement update both in one transaction. Historical or
opt-out usage has no model attribution: the entire unclassified shared usage
and outstanding reservation balance is conservatively counted against every
model's ceiling. This can unnecessarily block models, but neither moves nor
releases earlier reservations. It does not account for usage outside this
ledger, prove provider/upstream quota relationships, or reconcile ambiguous
outcomes.

Migration 0009 leaves existing reservations unchanged. Its rollback is blocked
while model quota rows exist, to avoid discarding model accounting; do not
delete accounting records to bypass this safeguard. Safe rollback after model
quota use needs a separately reviewed data-preservation procedure. Local
inference remains outside monetary quotas, and OpenAI remains disabled. No
periodic reset, billing, production configuration or live-provider acceptance
is provided by this feature.

OpenRouter's owner-confirmed route is `liquid/lfm-2.5-2.6b:free` via
`liquid/fp8`, with non-resetting shared ceilings of 100 requests and 100,000
tokens. The application rejects other routes and shared limits above these
ceilings. `SUPERHARRY_OPENROUTER_APPROXIMATE_QUOTA=1` is an explicit opt-in,
separate from provider admission, and defaults to off. The byte length of the
UTF-8 serialized request is only an estimate: the historical
`count_upper_bound` name does not establish a bound. The owner accepts that
underestimation and concurrency can exceed the ceilings. This is not a hard
budget and does not include usage outside the ledger.

Migration 0010 removes the two database checks that required used plus reserved
to fit the corresponding limit. Reservation admission still enforces both
limits. Only the OpenRouter token settlement path opts into recording valid
reported overage, atomically in the shared and attributed model quotas; other
holds remain intact and new holds are denied until the balances permit them.
Groq and Gemini settlement remain strict. Unknown usage stays reserved. Values
outside the signed 64-bit range, or additions that would overflow either
balance, fail without changing the transaction. Repeating the same settlement
is idempotent; a conflicting one fails.

Rollback of 0010 reintroduces the original checks and therefore fails atomically
if any existing quota has `used + reserved > limit`. Do not delete accounting
records to bypass that failure; a separately reviewed preservation or
reconciliation procedure is needed. Apply/reverse/reapply and blocked rollback
were exercised only on synthetic SQLite.

The opt-in does not enable OpenRouter: protected-context delivery remains
unverified. Requests explicitly set `context-compression` to disabled.
[OpenRouter's message-transform documentation](https://openrouter.ai/docs/guides/features/message-transforms)
says that with compression disabled an over-context request fails rather than
being compressed. However, its [plugin documentation](https://openrouter.ai/docs/guides/features/plugins)
says an administrator may enable a default plugin with "Prevent overrides",
making request-level disabling ineffective. Account settings were not inspected
and no response attestation of effective plugin settings is established here.
Other account-default plugins can also mutate requests. Evidence is required
that the effective account/organization and guardrail settings prevent all
protected-context transformations, and that this remains enforceable when
settings change. Separately, evidence is needed that `liquid/fp8` does not
silently truncate or omit protected messages; the cited OpenRouter behavior
does not establish that upstream guarantee.

The request contains the complete constitution locally, but a synthetic
serialization test cannot prove effective remote settings or what the upstream
model receives. The route remains closed until these conditions can be checked
reliably and fail closed. Do not reset or create a separate ledger to bypass
unknown reservations.
