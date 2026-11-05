from threading import RLock
from typing import Protocol
from uuid import UUID

from home.models import ChatTurn


class ChatDispatchError(RuntimeError):
    pass


class ChatTurnDispatcher(Protocol):
    """Persist work in the caller's transaction; do not execute before commit."""

    def enqueue(self, turn_id: UUID) -> None: ...

    def request_cancel(self, turn_id: UUID) -> None: ...


_lock = RLock()
_dispatcher: ChatTurnDispatcher | None = None


def configure_chat_dispatcher(dispatcher: ChatTurnDispatcher | None) -> None:
    global _dispatcher
    with _lock:
        _dispatcher = dispatcher


def get_chat_dispatcher() -> ChatTurnDispatcher | None:
    with _lock:
        return _dispatcher


class ChatTurnCancellation:
    """Fail closed when a persisted turn is no longer running."""

    def __init__(self, turn_id: UUID):
        if not isinstance(turn_id, UUID):
            raise ValueError("turn_id_invalid")
        self._turn_id = turn_id

    def __call__(self) -> bool:
        try:
            state = ChatTurn.objects.filter(pk=self._turn_id).values_list("state", flat=True).first()
            return state != ChatTurn.State.RUNNING
        except Exception:
            return True
