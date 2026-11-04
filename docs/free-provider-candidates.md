# Free-provider candidates

Owner direction, 2026-11-04: configure an administrator-controlled provider order, block routes whose zero cost cannot be verified, and use local inference if all free routes are unavailable and local inference is available; otherwise inform the user. A provider that uses conversations to improve models requires disclosure and explicit administrator enablement. Guests remain local-only. OpenAI is disabled for now.

The following are **candidates for review**, not enabled configurations or claims that a specific model, account, endpoint or price is verified. Rates, model availability and terms change. The administrator must configure each credential outside the repository, approve the exact provider/model and its data treatment, and ensure the effective request is zero-cost before activation. Do not put credentials in this file or logs.

1. **Groq** ? [OpenAI-compatible API](https://console.groq.com/docs/openai), [rate limits](https://console.groq.com/docs/rate-limits), and [data policy](https://console.groq.com/docs/your-data). Review the selected model, organization limits and actual account tier. The data policy describes default handling and exceptions; do not infer zero retention or no training from a model name.
2. **OpenRouter free models** ? [free-model collection](https://openrouter.ai/collections/free-models), [provider routing](https://openrouter.ai/docs/guides/routing/provider-selection), and [pricing](https://openrouter.ai/pricing/). One key can access paid models too; enforce free eligibility and route restrictions rather than trusting the key or a suffix alone. Free variants may share request quotas; actual endpoint data policy and account features need verification. An experimental local synthetic adapter does not establish live compatibility.
3. **Google Gemini free tier** ? [pricing and data-use policy](https://ai.google.dev/gemini-api/docs/pricing) and [API compatibility](https://ai.google.dev/gemini-api/docs/openai). Google states that content in the free tier is used to improve products. Disclose that fact and require explicit administrator enablement before any request; verify the exact model and account free eligibility.

The proposed order is a development starting point and must remain configurable. No provider is currently enabled by this document. Verify the full current constitution is delivered on every model request, and reject or defer requests when the context, free price, provider privacy settings, quota accounting, authorization, or safe retry status cannot be established. A 429 is not automatically proof of a permanent free-tier exhaustion, and a timeout or partial response must not trigger a blind retry elsewhere.

The application currently has no production-ready provider transport, local fallback, global quota state or administrator configuration for these candidates. The existing proxy work is simulated; see T177?T179 in [the backlog](reference/backlog.md).

For future development, credentials can be placed locally in the ignored `.env`
using `GROQ_API_KEY`, `OPENROUTER_API_KEY`, or `GEMINI_API_KEY`. Add only keys
for accounts you intend to use; never paste values into the repository or chat.
The proxy does not yet load these variables or make real provider calls.
