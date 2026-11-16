"""Fail-closed, process-independent admission limits for ephemeral guests."""

import hashlib
import ipaddress
import time
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache


class GuestLimitDenied(RuntimeError):
    """The guest request cannot be admitted under the configured limits."""


@dataclass(frozen=True)
class GuestAdmission:
    session_key: str
    origin_key: str
    pending_key: str


def _trusted_https_request(request):
    """Accept direct TLS or the same loopback proxy contract as the middleware."""
    if request.is_secure():
        return True
    if request.META.get("HTTP_X_FORWARDED_PROTO") != "https":
        return False
    try:
        proxy = ipaddress.ip_address(request.META.get("REMOTE_ADDR"))
    except (TypeError, ValueError):
        return False
    return proxy.is_loopback


def _origin_key(request):
    if not _trusted_https_request(request):
        raise GuestLimitDenied("guest_transport_untrusted")
    origin = request.META.get("HTTP_ORIGIN", "").strip().lower()
    host = request.get_host().strip().lower()
    if not origin or not host or origin != f"https://{host}":
        raise GuestLimitDenied("guest_origin_untrusted")
    return hashlib.sha256(origin.encode("ascii", errors="strict")).hexdigest()


def _counter(key, limit, window):
    try:
        if cache.add(key, 1, timeout=window):
            return
        value = cache.incr(key)
    except Exception as exc:
        raise GuestLimitDenied("guest_limit_store_unavailable") from exc
    if value > limit:
        try:
            cache.decr(key)
        except Exception:
            pass
        raise GuestLimitDenied("guest_rate_limited")


def admit_guest(request):
    """Create/refresh the 24-hour guest session and atomically reserve one turn."""
    origin = _origin_key(request)
    session = request.session
    new_session = not session.session_key
    window = int(time.time() // settings.GUEST_RATE_WINDOW_SECONDS)
    if new_session:
        # Reserve before creating a session, so a rejected new session cannot
        # be turned into a reusable cookie that bypasses the origin limit.
        _counter(
            f"guest:origin:{origin}:sessions:{window}",
            settings.GUEST_SESSIONS_PER_ORIGIN,
            settings.GUEST_RATE_WINDOW_SECONDS + 1,
        )
    if not session.session_key:
        try:
            session.create()
        except Exception as exc:
            raise GuestLimitDenied("guest_session_unavailable") from exc
    session.set_expiry(settings.GUEST_SESSION_LIFETIME_SECONDS)
    session_key = session.session_key
    pending_key = f"guest:session:{session_key}:pending"
    try:
        if not cache.add(pending_key, "1", timeout=settings.GUEST_QUEUE_TIMEOUT_SECONDS):
            raise GuestLimitDenied("guest_request_pending")
    except GuestLimitDenied:
        raise
    except Exception as exc:
        raise GuestLimitDenied("guest_limit_store_unavailable") from exc
    try:
        _counter(
            f"guest:session:{session_key}:questions:{window}",
            settings.GUEST_QUESTIONS_PER_SESSION,
            settings.GUEST_RATE_WINDOW_SECONDS + 1,
        )
    except Exception:
        # Do not leave a reservation that blocks the session after admission fails.
        try:
            cache.delete(pending_key)
        except Exception:
            pass
        raise
    return GuestAdmission(session_key, origin, pending_key)


def release_guest(admission):
    try:
        cache.delete(admission.pending_key)
    except Exception:
        # The TTL remains the fail-closed recovery path if deletion is unavailable.
        pass
