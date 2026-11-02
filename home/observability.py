import json
import logging
import os
import re
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
from logging.handlers import TimedRotatingFileHandler
from uuid import uuid4

from django.db import DatabaseError

HTTP_HISTOGRAM_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5)
HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}
DIAGNOSTIC_RETENTION_SECONDS = 30 * 24 * 60 * 60
ROTATED_LOG_SUFFIX = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
_METRICS_LOCK = threading.Lock()
_REQUEST_COUNTS = defaultdict(int)
_REQUEST_DURATION_BUCKET_COUNTS = defaultdict(
    lambda: [0] * (len(HTTP_HISTOGRAM_BUCKETS) + 1)
)
_REQUEST_DURATION_COUNTS = defaultdict(int)
_REQUEST_DURATION_SUMS = defaultdict(float)
_DIAGNOSTICS_STATE_WARNING_LOCK = threading.Lock()
_DIAGNOSTICS_STATE_WARNING_EMITTED = False


class JsonEventFormatter(logging.Formatter):
    fields = (
        "request_id",
        "route",
        "method",
        "status_code",
        "duration_ms",
        "component",
        "operation",
        "error_code",
        "severity",
    )

    def format(self, record):
        event_name = getattr(record, "event_name", None)
        if event_name not in {"http.request", "application.error", "background.operation"}:
            event_name = "application.error"
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "event": event_name,
        }
        for field in self.fields:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload, ensure_ascii=True, separators=(",", ":"))


class PrivateTimedRotatingFileHandler(TimedRotatingFileHandler):
    def __init__(self, filename, *args, **kwargs):
        parent = os.path.dirname(os.path.abspath(filename))
        if not os.path.isdir(parent):
            raise OSError("Diagnostic log directory must already exist.")
        super().__init__(filename, *args, delay=True, **kwargs)
        purge_expired_diagnostic_logs(self.baseFilename)

    def _open(self):
        flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(self.baseFilename, flags, 0o600)
        try:
            os.chmod(self.baseFilename, 0o600)
            return os.fdopen(
                descriptor,
                mode="a",
                encoding=self.encoding,
                errors=self.errors,
            )
        except Exception:
            os.close(descriptor)
            raise

    def emit(self, record):
        try:
            if self.stream is not None:
                try:
                    stream_stat = os.fstat(self.stream.fileno())
                    path_stat = os.stat(self.baseFilename, follow_symlinks=False)
                except FileNotFoundError:
                    self.stream.close()
                    self.stream = None
                else:
                    if (stream_stat.st_dev, stream_stat.st_ino) != (
                        path_stat.st_dev,
                        path_stat.st_ino,
                    ):
                        self.stream.close()
                        self.stream = None
            purge_expired_diagnostic_logs(self.baseFilename)
        except OSError:
            self.handleError(record)
            return
        super().emit(record)


class DiagnosticEnabledFilter(logging.Filter):
    def filter(self, record):
        global _DIAGNOSTICS_STATE_WARNING_EMITTED
        from home.models import DiagnosticSettings

        try:
            enabled = DiagnosticSettings.objects.filter(pk=1).values_list(
                "enabled",
                flat=True,
            ).first()
        except DatabaseError:
            with _DIAGNOSTICS_STATE_WARNING_LOCK:
                if not _DIAGNOSTICS_STATE_WARNING_EMITTED:
                    logging.getLogger("django").error(
                        "Could not read the diagnostics setting; diagnostic event discarded."
                    )
                    _DIAGNOSTICS_STATE_WARNING_EMITTED = True
            return False

        with _DIAGNOSTICS_STATE_WARNING_LOCK:
            _DIAGNOSTICS_STATE_WARNING_EMITTED = False
        return enabled is True


def validate_diagnostic_log_path(filename):
    parent = os.path.dirname(os.path.abspath(filename))
    if not os.path.isdir(parent):
        raise OSError("Diagnostic log directory must already exist.")
    flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(filename, flags, 0o600)
    try:
        os.chmod(filename, 0o600)
    finally:
        os.close(descriptor)


def purge_expired_diagnostic_logs(filename, *, now=None):
    directory = os.path.dirname(os.path.abspath(filename))
    if not os.path.isdir(directory):
        return 0
    basename = os.path.basename(filename)
    prefix = basename + "."
    cutoff = (time.time() if now is None else now) - DIAGNOSTIC_RETENTION_SECONDS
    removed = 0
    with os.scandir(directory) as entries:
        for entry in entries:
            if entry.name != basename and not entry.name.startswith(prefix):
                continue
            if entry.name != basename and not ROTATED_LOG_SUFFIX.fullmatch(
                entry.name[len(prefix):]
            ):
                continue
            if not entry.is_file(follow_symlinks=False):
                continue
            if entry.stat(follow_symlinks=False).st_mtime < cutoff:
                os.unlink(entry.path)
                removed += 1
    return removed


def record_http_request(route, method, status_code, duration_seconds):
    safe_route = route or "unmatched"
    safe_method = method if method in HTTP_METHODS else "OTHER"
    status_class = f"{status_code // 100}xx" if 100 <= status_code < 600 else "other"
    key = (safe_route, safe_method, status_class)
    with _METRICS_LOCK:
        _REQUEST_COUNTS[key] += 1
        duration = max(0.0, duration_seconds)
        _REQUEST_DURATION_COUNTS[key] += 1
        _REQUEST_DURATION_SUMS[key] += duration
        for index, bucket in enumerate(HTTP_HISTOGRAM_BUCKETS):
            if duration <= bucket:
                _REQUEST_DURATION_BUCKET_COUNTS[key][index] += 1
        _REQUEST_DURATION_BUCKET_COUNTS[key][-1] += 1


def render_metrics():
    with _METRICS_LOCK:
        counts = dict(_REQUEST_COUNTS)
        duration_buckets = {
            key: tuple(values)
            for key, values in _REQUEST_DURATION_BUCKET_COUNTS.items()
        }
        duration_counts = dict(_REQUEST_DURATION_COUNTS)
        duration_sums = dict(_REQUEST_DURATION_SUMS)

    lines = [
        "# HELP superharry_http_requests_total Total HTTP requests handled by this process.",
        "# TYPE superharry_http_requests_total counter",
    ]
    for (route, method, status_class), value in sorted(counts.items()):
        labels = _format_labels(route, method, status_class)
        lines.append(f"superharry_http_requests_total{labels} {value}")

    lines.extend(
        [
            "# HELP superharry_http_request_duration_seconds HTTP request duration in seconds.",
            "# TYPE superharry_http_request_duration_seconds histogram",
        ]
    )
    for key, buckets in sorted(duration_buckets.items()):
        route, method, status_class = key
        for index, bucket in enumerate(HTTP_HISTOGRAM_BUCKETS):
            count = buckets[index]
            labels = _format_labels(route, method, status_class, le=_format_number(bucket))
            lines.append(
                f"superharry_http_request_duration_seconds_bucket{labels} {count}"
            )
        labels = _format_labels(route, method, status_class, le="+Inf")
        lines.append(
            f"superharry_http_request_duration_seconds_bucket{labels} {buckets[-1]}"
        )
        labels = _format_labels(route, method, status_class)
        lines.append(
            f"superharry_http_request_duration_seconds_sum{labels} "
            f"{_format_number(duration_sums[key])}"
        )
        lines.append(
            f"superharry_http_request_duration_seconds_count{labels} "
            f"{duration_counts[key]}"
        )
    return "\n".join(lines) + "\n"


def _format_labels(route, method, status_class, *, le=None):
    labels = {
        "route": route,
        "method": method,
        "status_class": status_class,
    }
    if le is not None:
        labels["le"] = le
    encoded = ",".join(
        f'{key}="{_escape_label(value)}"'
        for key, value in labels.items()
    )
    return "{" + encoded + "}"


def _escape_label(value):
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _format_number(value):
    return format(value, ".12g")


class ObservabilityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.diagnostic_logger = logging.getLogger("superharry.diagnostics")

    def __call__(self, request):
        started = time.perf_counter()
        request_id = str(uuid4())
        try:
            response = self.get_response(request)
        except Exception:
            duration = time.perf_counter() - started
            route = _route_name(request)
            record_http_request(route, request.method, 500, duration)
            self.diagnostic_logger.error(
                "application.error",
                extra={
                    "event_name": "application.error",
                    "request_id": request_id,
                    "route": route,
                    "method": request.method if request.method in HTTP_METHODS else "OTHER",
                    "status_code": 500,
                    "duration_ms": round(duration * 1000, 3),
                    "component": "http",
                    "operation": "request",
                    "error_code": "unhandled_request_error",
                    "severity": "error",
                },
            )
            raise

        duration = time.perf_counter() - started
        route = _route_name(request)
        record_http_request(route, request.method, response.status_code, duration)
        fields = {
            "event_name": "http.request",
            "request_id": request_id,
            "route": route,
            "method": request.method if request.method in HTTP_METHODS else "OTHER",
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 3),
        }
        if response.status_code >= 500:
            fields.update(
                {
                    "event_name": "application.error",
                    "component": "http",
                    "operation": "request",
                    "error_code": "http_server_error",
                    "severity": "error",
                }
            )
            self.diagnostic_logger.error("application.error", extra=fields)
        else:
            self.diagnostic_logger.info("http.request", extra=fields)
        return response


def _route_name(request):
    match = getattr(request, "resolver_match", None)
    if match is None:
        return "unmatched"
    return match.view_name or "unmatched"
