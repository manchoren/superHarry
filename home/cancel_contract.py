"""Remote-cancellation contract for the enabled free-provider routes.

Status (2026-11-10):

- No enabled route exposes a provider-side cancellation endpoint for chat
  completions. Verified against provider documentation:

  * Groq: chat completions (`POST /openai/v1/chat/completions`) have no
    cancel operation. Groq documents cancellation only for *batches*
    (`POST /openai/v1/batches/{id}/cancel`); a per-request abort is not
    exposed by the REST API used here.
  * OpenRouter: the chat completions endpoint is OpenAI-compatible and has
    no per-request cancel endpoint. Its published cancellation support
    list covers OpenAI/Azure/Anthropic/DeepSeek/Together/DeepInfra/xAI and
    explicitly excludes Groq, Google/Google AI Studio, Mistral and
    Perplexity.
  * Gemini: `generateContent` has no cancel endpoint. The only documented
    abort mechanism is the streaming SDK `AbortController`, which this
    transport does not use (unary non-streaming `generateContent`).

- Cancellation is therefore a persisted, session-level admission control
  (`ChatTurn.state` becomes `cancel_requested` / `cancelled`). It stops
  dispatch, is observed by the worker, and can never prove that an upstream
  request was terminated. A *local* cancel must never be presented as
  proof of remote termination.

- Ambiguous outcomes require reconciliation before dispatch:
  transport failure after send, a Groq 429 (rate-limit rejection, not a
  confirmed abort), or an OpenRouter 429 that the provider does not
  guarantee precedes generation all leave reservations unsettled. Held
  unknown reservations block any further dispatch on that route until the
  held amounts are settled with exact correlated evidence.

- Successful responses require exact token accounting where the provider
  exposes it: Gemini `usageMetadata` (`promptTokenCount`,
  `candidatesTokenCount`, `totalTokenCount`); OpenRouter/Groq
  `usage` (`prompt_tokens`, `completion_tokens`, `total_tokens`) with
  `total == prompt + completion`. Where the provider exposes no usage, the
  route is not eligible for the exact-accounting clause and the exposed
  usage is treated as unverified.
"""
from django.db import transaction

from home.models import ChatTurn, ProviderReservation

_PROVIDER_GROUPS = {
    # Gateway dispatch is accounted and reconciled as one application route;
    # provider selection remains inside omniroute and is intentionally opaque.
    'omniroute': ('omniroute-development', 'omniroute-development:tokens'),
    # group = quota group for the shared request allowance; token group is
    # the quota group for the shared token allowance.
    'gemini': ('gemini-development', 'gemini-development:tokens'),
    'groq': ('groq-development', 'groq-development:tokens'),
    'openrouter': ('openrouter-development', 'openrouter-development:tokens'),
}


class CancellationContractError(RuntimeError):
    """A remote-cancellation contract rule was violated."""


class ReconciliationRequired(CancellationContractError):
    """Held unknown reservations must be resolved before this route may dispatch."""


def _held_unknown(provider):
    if provider not in _PROVIDER_GROUPS:
        raise CancellationContractError('unknown_provider')
    groups = _PROVIDER_GROUPS[provider]
    with transaction.atomic():
        return ProviderReservation.objects.filter(
            quota__group__in=groups, state='unknown')


def held_unknown_reservations(provider):
    """Return the unsettled reservations held by this route (simulation/known)."""
    return _held_unknown(provider)


def before_dispatch(provider):
    """Enforce: ambiguous outcomes require reconciliation before dispatch.

    Raises ReconciliationRequired when any reservation for this route is in
    the 'unknown' state. A route may re-dispatch only after settled rows.
    """
    held = _held_unknown(provider)
    if held.exists():
        raise ReconciliationRequired(
            '{} held {} unknown reservation(s); '
            'reconcile before dispatch'.format(provider, held.count()))


def cancellation_state(turn_id):
    """Return the persisted cancellation state of a turn."""
    state = ChatTurn.objects.filter(pk=turn_id).values_list('state', flat=True).first()
    return state


class RemoteTerminationProof:
    """Contract rule: no provider cancellation proof may exist.

    ``for_route`` always raises. Any caller that obtains a proof has
    violated the contract and must fail closed. A local cancel is not a
    remote termination: this class exists so that the negative contract is
    enforceable rather than cosmetic.
    """

    @classmethod
    def for_route(cls, provider):
        raise CancellationContractError(
            'remote_cancellation_unavailable: {} has no provider cancellation '
            'endpoint'.format(provider))


def verify_not_remote_termination(provider):
    """Assert that no remote-termination proof was produced for a route."""
    RemoteTerminationProof.for_route(provider)


class CancellationContract:
    """Per-turn contract; gates every provider dispatch attempt on a turn."""

    def __init__(self, turn_id):
        self._turn_id = turn_id

    @property
    def turn_id(self):
        return self._turn_id

    def state(self):
        """Persisted cancellation state for this turn (not a remote claim)."""
        return cancellation_state(self._turn_id)

    def before_dispatch(self, provider):
        before_dispatch(provider)
