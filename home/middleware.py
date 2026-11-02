import ipaddress
from datetime import datetime, timedelta, timezone as datetime_timezone
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.auth import logout
from django.http import HttpResponseForbidden
from django.middleware.csrf import CSRF_SESSION_KEY
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

from home.api_errors import api_error, is_chat_api_path

_PREAUTH_STARTED_AT = "_superharry_preauth_started_at"
_AUTHENTICATED_STARTED_AT = "_superharry_authenticated_started_at"
_AUTHENTICATED_LAST_ACTIVITY_AT = "_superharry_authenticated_last_activity_at"

_PREAUTH_LIFETIME = timedelta(minutes=10)
_AUTHENTICATED_IDLE_TIMEOUT = timedelta(minutes=60)
_AUTHENTICATED_ABSOLUTE_TIMEOUT = timedelta(hours=24)
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def _trusted_https_proxy(request):
    if request.is_secure():
        return True

    if request.META.get("HTTP_X_FORWARDED_PROTO") != "https":
        return False

    remote_addr = request.META.get("REMOTE_ADDR")
    try:
        proxy_address = ipaddress.ip_address(remote_addr)
    except (TypeError, ValueError):
        return False
    if not proxy_address.is_loopback:
        return False

    request.META["wsgi.url_scheme"] = "https"
    return True


def _origin_authority(value):
    if (
        not value
        or value == "null"
        or "," in value
        or "\\" in value
        or "?" in value
        or "#" in value
    ):
        return None
    if any(character.isspace() or ord(character) < 0x20 for character in value):
        return None

    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme.lower() != "https"
            or not parsed.netloc
            or parsed.netloc.endswith(":")
            or parsed.path
            or parsed.query
            or parsed.fragment
            or parsed.username is not None
            or parsed.password is not None
        ):
            return None
        hostname = parsed.hostname
        port = parsed.port if parsed.port is not None else 443
    except ValueError:
        return None

    if hostname is None:
        return None
    if ":" in hostname:
        if "%" in hostname:
            return None
        try:
            hostname = ipaddress.IPv6Address(hostname).compressed
        except ipaddress.AddressValueError:
            return None
    else:
        try:
            hostname = hostname.encode("idna").decode("ascii").lower()
        except UnicodeError:
            return None
    return hostname, port


class StrictOriginMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.method in _SAFE_METHODS:
            return None
        if not _trusted_https_proxy(request):
            if is_chat_api_path(request.path):
                return api_error(request, "FORBIDDEN", 403)
            return HttpResponseForbidden()

        origin = request.META.get("HTTP_ORIGIN")
        request_host = request.get_host()
        request_authority = _origin_authority(f"https://{request_host}")
        if request_authority is None:
            if is_chat_api_path(request.path):
                return api_error(request, "FORBIDDEN", 403)
            return HttpResponseForbidden()
        if not settings.DEBUG and (
            request_authority[0] != settings.SUPERHARRY_HOSTNAME
            or request_authority[1] != 443
        ):
            if is_chat_api_path(request.path):
                return api_error(request, "FORBIDDEN", 403)
            return HttpResponseForbidden()
        if _origin_authority(origin) != request_authority:
            if is_chat_api_path(request.path):
                return api_error(request, "FORBIDDEN", 403)
            return HttpResponseForbidden()
        request.META["HTTP_ORIGIN"] = f"https://{request_host}"
        return None


class SessionLifetimeMiddleware(MiddlewareMixin):
    def process_request(self, request):
        now = timezone.now()
        now_timestamp = now.timestamp()

        if request.user.is_authenticated:
            started_at = request.session.get(_AUTHENTICATED_STARTED_AT)
            last_activity_at = request.session.get(_AUTHENTICATED_LAST_ACTIVITY_AT)
            if started_at is not None and (
                now_timestamp
                >= started_at
                + _AUTHENTICATED_ABSOLUTE_TIMEOUT.total_seconds()
                or (
                    last_activity_at is not None
                    and now_timestamp
                    >= last_activity_at + _AUTHENTICATED_IDLE_TIMEOUT.total_seconds()
                )
            ):
                logout(request)
            return

        preauth_started_at = request.session.get(_PREAUTH_STARTED_AT)
        if preauth_started_at is not None and now_timestamp >= (
            preauth_started_at + _PREAUTH_LIFETIME.total_seconds()
        ):
            request.session.flush()

    def process_response(self, request, response):
        session = request.session
        if request.user.is_authenticated:
            now = timezone.now()
            now_timestamp = now.timestamp()
            started_at = session.get(_AUTHENTICATED_STARTED_AT)
            if started_at is None:
                started_at = now_timestamp
                session[_AUTHENTICATED_STARTED_AT] = started_at
            last_activity_at = session.get(_AUTHENTICATED_LAST_ACTIVITY_AT)
            if last_activity_at is None:
                last_activity_at = started_at
                session[_AUTHENTICATED_LAST_ACTIVITY_AT] = last_activity_at
            if request.method not in _SAFE_METHODS and response.status_code < 400:
                last_activity_at = now_timestamp
                session[_AUTHENTICATED_LAST_ACTIVITY_AT] = last_activity_at
            absolute_expiry = datetime.fromtimestamp(
                started_at + _AUTHENTICATED_ABSOLUTE_TIMEOUT.total_seconds(),
                tz=datetime_timezone.utc,
            )
            idle_expiry = datetime.fromtimestamp(
                last_activity_at + _AUTHENTICATED_IDLE_TIMEOUT.total_seconds(),
                tz=datetime_timezone.utc,
            )
            session.set_expiry(min(absolute_expiry, idle_expiry))
        elif CSRF_SESSION_KEY in session:
            now_timestamp = timezone.now().timestamp()
            started_at = session.get(_PREAUTH_STARTED_AT)
            if started_at is None:
                started_at = now_timestamp
                session[_PREAUTH_STARTED_AT] = started_at
            session.set_expiry(
                datetime.fromtimestamp(
                    started_at + _PREAUTH_LIFETIME.total_seconds(),
                    tz=datetime_timezone.utc,
                )
            )
        return response
