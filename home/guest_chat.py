"""Ephemeral, local-only guest chat boundary."""

from types import SimpleNamespace

from home.gemini_chat import _run_local_fallback


class GuestChatUnavailable(RuntimeError):
    """The local-only guest route cannot safely serve this request."""


def run_guest_local_turn(*, message, history=(), adapter=None, cancelled=None):
    """Run one guest turn without creating durable application objects.

    The transient shape intentionally has no database owner and the local
    fallback is called directly, so gateway/provider routing cannot be reached.
    """
    turn = SimpleNamespace(
        model_mode="local",
        requested_provider="",
        requested_model="",
        openrouter_risk_accepted=False,
        user_message=SimpleNamespace(content=message),
        conversation=SimpleNamespace(owner_id="guest"),
    )
    if cancelled is None:
        cancelled = lambda: False
    try:
        return _run_local_fallback(
            turn=turn,
            history=tuple(history),
            authorized=lambda: True,
            cancelled=cancelled,
            adapter=adapter,
        )
    except Exception as exc:
        raise GuestChatUnavailable("guest_local_inference_unavailable") from exc
