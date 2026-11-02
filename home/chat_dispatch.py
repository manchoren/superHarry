from threading import RLock
from typing import Protocol
from uuid import UUID


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
