"""Persistent Gemini development queue; claimed work is never retried."""

import logging
import threading
from datetime import timedelta

from django.db import DatabaseError, close_old_connections, transaction
from django.utils import timezone

from home.chat_events import append_chat_event
from home.models import ChatEvent, ChatTurn, GeminiChatJob

logger = logging.getLogger(__name__)
_WAKE = threading.Event()
_START_LOCK = threading.Lock()
_started = False
_STALE_AFTER = timedelta(minutes=5)
_TERMINAL = (ChatTurn.State.COMPLETED, ChatTurn.State.FAILED, ChatTurn.State.CANCELLED)


def wake_worker():
    _WAKE.set()


def claim_next():
    """Claim one queued record atomically across processes."""
    job_id = (GeminiChatJob.objects.filter(state=GeminiChatJob.State.QUEUED)
              .order_by('created_at', 'pk').values_list('pk', flat=True).first())
    if job_id is None:
        return None
    claimed = GeminiChatJob.objects.filter(pk=job_id, state=GeminiChatJob.State.QUEUED).update(
        state=GeminiChatJob.State.CLAIMED, claimed_at=timezone.now())
    if not claimed:
        return None
    return GeminiChatJob.objects.get(pk=job_id)


def run_one():
    job = claim_next()
    if job is None:
        return False
    from home.gemini_chat import run_gemini_turn
    run_gemini_turn(job.turn_id)
    if ChatTurn.objects.filter(pk=job.turn_id, state__in=_TERMINAL).exists():
        GeminiChatJob.objects.filter(pk=job.pk, state=GeminiChatJob.State.CLAIMED).update(
            state=GeminiChatJob.State.DONE)
    return True


def reconcile_stale(*, now=None):
    """Close abandoned claims without redispatch or quota release."""
    now = now or timezone.now()
    ids = list(GeminiChatJob.objects.filter(state=GeminiChatJob.State.CLAIMED,
        claimed_at__lte=now - _STALE_AFTER).order_by('claimed_at', 'pk').values_list('pk', flat=True)[:20])
    reconciled = 0
    for job_id in ids:
        with transaction.atomic():
            changed = GeminiChatJob.objects.filter(pk=job_id, state=GeminiChatJob.State.CLAIMED,
                claimed_at__lte=now - _STALE_AFTER).update(state=GeminiChatJob.State.INTERRUPTED)
            if not changed:
                continue
            job = GeminiChatJob.objects.select_related('turn').get(pk=job_id)
            turn = ChatTurn.objects.select_for_update().get(pk=job.turn_id)
            if turn.state in _TERMINAL:
                GeminiChatJob.objects.filter(pk=job.pk).update(state=GeminiChatJob.State.DONE)
            elif turn.state == ChatTurn.State.CANCEL_REQUESTED:
                append_chat_event(turn=turn, event_type=ChatEvent.EventType.TURN_CANCELLED, payload={'status': 'cancelled'})
            else:
                if turn.state == ChatTurn.State.QUEUED:
                    append_chat_event(turn=turn, event_type=ChatEvent.EventType.TURN_STARTED, payload={'status': 'running'})
                append_chat_event(turn=turn, event_type=ChatEvent.EventType.TURN_FAILED,
                                  payload={'error': {'code': 'UNAVAILABLE', 'retryable': False}, 'reason': 'interrupted_unknown'})
            reconciled += 1
    return reconciled


def _worker_loop():
    while True:
        try:
            close_old_connections()
            reconcile_stale()
            if run_one():
                continue
        except DatabaseError:
            logger.warning('gemini_queue_database_unavailable')
        except Exception:
            logger.warning('gemini_queue_worker_failed')
        finally:
            close_old_connections()
        _WAKE.wait(timeout=1)
        _WAKE.clear()


def start_development_worker():
    global _started
    with _START_LOCK:
        if _started:
            return
        thread = threading.Thread(target=_worker_loop, name='gemini-development-queue', daemon=True)
        thread.start()
        _started = True
