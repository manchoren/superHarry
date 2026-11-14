# T218 - External services audit (bounded local evidence)

Date: 2026-11-12. Historical partial local/documentary evidence. T218 was cancelled on 2026-11-14; [T243 and selected integration tasks](product-first-validation.md) own follow-up scope.

This record audits the currently documented boundaries without contacting Gmail,
voice providers, weather services, or reading local secrets.

| Service | Local/documentary evidence | Consent and mode | Pending |
|---|---|---|---|
| Gmail | `docs/reference/gmail-auth-proposal.md`, checked 2026-11-12 | OAuth `gmail.readonly` only; local drafts; a human sends; no `gmail.send`, `gmail.modify`, SMTP, autonomous sending, or external-model sharing without separate consent | Actual Google consent, client setup, protected token provisioning, revocation/renewal tests, integration and deployment |
| Voice models | `docs/reference/product-requirements.md` sections 11A.6 and P-42/P-43/P-48; `docs/reference/t215-voice-proposal.md` | Local VM transcription with whisper.cpp and local Piper TTS; voice replies initially disabled; no cloud audio route is activated | Exact artifacts and licenses, target-VM functional/security/resource checks, and release activation |
| Weather | `docs/reference/product-requirements.md` sections 11.3 and 11.4 | Open-Meteo is the documented free weather candidate for the local idle display, with attribution and provider limits; no weather client or credentials are enabled by this audit | Terms/limits and attribution implementation, offline/cache behavior, functional/security checks, and deployment acceptance |

## Evidence matrix by lifecycle stage

`Selection` records a chosen direction only. Each later column requires its own
evidence; a selection, license note, or local test cannot stand in for consent,
activation, revocation, or target-VM acceptance.

| Service | Selection | License evidence | Digest/artifact evidence | Consent | Activation | Revocation | VM acceptance |
|---|---|---|---|---|---|---|---|
| Gmail | Dedicated mailbox and Gmail API selected; `gmail.readonly` is the initial scope | Gmail scope references are documented; this is not application-license clearance | OAuth client and token artifact identity are not evidenced; no token was read | Owner accepted the read-only/local-draft design; actual Google account consent is still absent | No OAuth grant, mailbox access, native Gmail draft, send, or autonomous action | Renewal/revocation and disconnected-state tests are not evidenced | T214/T218/T238 integration, security, deployment and release evidence remain open |
| Voice | whisper.cpp 1.9.5, Piper 1.8.0, Daniela preferred and Ald fallback selected | MIT/GPL and voice model-card obligations are recorded as leads, not legal clearance | Immutable runtime, ONNX/JSON and model digests remain incomplete; no artifacts were downloaded | Selection does not grant permission to download, install, distribute, or use in production | Voice replies remain initially disabled; no cloud audio route is enabled | Model/license withdrawal and voice-disable recovery behavior are not evidenced | Target-VM functional/security/resource checks and release approval remain open |
| Weather | Open-Meteo documented as the initial free API candidate for the local display | Provider terms/attribution obligations are not verified by this local audit | No client or dependency artifact/digest is selected or installed | Product requirement does not prove current provider terms or authorize data sharing beyond the defined display use | No request, refresh job, cache, attribution UI, or offline behavior is active | Cache invalidation/provider-unavailable handling is not evidenced | Provider-limit, attribution, offline/error and deployment acceptance remain open |

## Missing-evidence checklist

The entries below are deliberately not marked as failed or approved. `missing`
means no evidence is recorded in this checkout; `not verified` means a source or
requirement is mentioned but its current implementation/evidence is absent;
`not activated` means the local policy explicitly records that no activation
occurred.

| Area | Item | Status | Required evidence before acceptance |
|---|---|---|---|
| OAuth | Dedicated-account consent with the exact `gmail.readonly` scope | missing | Operator-mediated consent record, returned account binding, and sanitized scope evidence |
| OAuth | Client type, redirect/PKCE/state behavior and protected token custody | not verified | Reviewed client configuration, implementation tests and protected-storage evidence without exposing tokens |
| Revocation | Expiry/revocation, disconnected state and administrator reauthorization | not verified | Functional tests showing fail-closed behavior, local draft preservation and no scope expansion |
| Artifacts/digests | whisper.cpp/Piper runtimes and STT/TTS model files | missing | Immutable source/revision, SHA-256 for every file, architecture, dependency and size manifest |
| Licenses | Runtime, model, voice and attribution obligations | not verified | License texts/notices for exact artifacts plus a distribution/use review; model-card notes alone are insufficient |
| Weather | Open-Meteo terms, limits, attribution, cache and offline behavior | not verified | Current terms/limits review, bounded client design, attribution and error/offline tests |
| Activation | Gmail, voice and weather runtime activation | not activated | Explicit activation record after prerequisites; current audit provides none |
| VM acceptance | Target-VM functional, security, resource, recovery and deployment checks | missing | Isolated target-VM evidence tied to approved artifact identities and release scope |

## Verifiable criteria for the missing evidence

These criteria define what a future evidence package must demonstrate. They do
not convert the current `missing`, `not verified`, or `not activated` states into
passes.

| Evidence area | Verifiable criterion | Current state |
|---|---|---|
| Revocation | A revoked or expired Gmail credential produces a disconnected state, blocks reads/sends, preserves local drafts, and requires administrator reauthorization without widening scope | not verified |
| Renewal | A renewal test records the same dedicated account and exact `gmail.readonly` scope, rejects account mismatch, and does not log or persist token material in application data | not verified |
| Digest | Every runtime, model, ONNX and JSON artifact has an immutable source/revision and independently recorded SHA-256; the tested file matches the recorded digest | missing |
| Notices | The exact runtime, model and voice licenses and required attribution notices are stored with the manifest; unresolved obligations block distribution/release | not verified |
| Weather attribution | A weather response/display includes the required provider attribution, identifies the data timestamp/source, and remains bounded by documented provider limits | not verified |
| Weather failure | Provider timeout, limit exhaustion or stale data produces a bounded unavailable/stale state without leaking credentials or retrying without limits | not verified |
| VM acceptance | On the target VM, the approved artifact manifest, local-only voice path, bounded weather behavior, Gmail authorization boundary, recovery behavior and release scope are recorded together | missing |

## Explicit non-actions

- No `.env` value, OAuth token, mailbox, provider account, or credential was read.
- No OAuth consent, Gmail access, message send, voice model download, audio
  processing, weather request, dependency installation, or service activation
  occurred.
- This evidence does not close T218, T214, T215, T216, or deployment/release
  gates.

## License and activation boundary

- The T215 record identifies whisper.cpp as MIT, Piper 1.8.0 as
  GPL-3.0-or-later, and separate model-card obligations for the Daniela and
  Ald voices. These are audit leads, not legal clearance.
- No voice artifact is approved for download, installation, distribution, or
  production use until its immutable artifact identity, dependency/license
  notices, architecture compatibility, and applicable owner-scoped approval
  are recorded.
- The documented Open-Meteo choice is a product requirement, not evidence that
  terms, limits, attribution, cache behavior, or a client have been verified.

## Sources and reproducibility

- `docs/reference/gmail-auth-proposal.md` (G1, 2026-11-11).
- `docs/reference/product-requirements.md` (Q-51, Q-53, Q-54, P-42, P-43,
  P-48, and idle-display weather requirements).
- `docs/owner-attention.md` (G1 boundary and activation restrictions).

The accompanying `tests/test_t218_external_services.py` checks these local
documents for the required consent and no-activation boundaries. It performs no
network access and intentionally does not inspect `.env`.
