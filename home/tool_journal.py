"""Committed per-call markers for potentially consequential tool execution."""

from django.db import DatabaseError, IntegrityError, connection
from django.utils import timezone

from home.models import ToolExecution
from home.tool_boundary import ToolDenied


class ToolJournalError(Exception):
    pass


class DatabaseToolJournal:
    def _require_autocommit(self):
        if connection.in_atomic_block or not connection.get_autocommit():
            raise ToolDenied('Tool journal requires an independent transaction.')

    def begin(self, invocation, declaration):
        self._require_autocommit()
        try:
            ToolExecution.objects.using('default').create(operation_id=invocation.operation_id,
                request_id=invocation.request_id, tool_name=declaration.name,
                actor_user_id=invocation.actor_user_id)
        except IntegrityError:
            raise ToolDenied('Tool operation already exists or is invalid.') from None
        except DatabaseError:
            raise ToolDenied('Tool journal is unavailable.') from None

    def finish(self, operation_id, state):
        self._require_autocommit()
        if state not in ('succeeded', 'unknown_effect', 'not_dispatched'):
            raise ToolJournalError('Invalid journal transition.')
        try:
            changed = ToolExecution.objects.using('default').filter(operation_id=operation_id)._finish_started(
                state, timezone.now())
        except DatabaseError:
            raise ToolJournalError('Tool journal is unavailable.') from None
        if changed != 1:
            raise ToolJournalError('Tool journal transition unavailable.')
