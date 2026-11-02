import csv
import hashlib
import json
import re
from datetime import datetime, time, timedelta, timezone as datetime_timezone
from io import StringIO
from uuid import UUID

from django.contrib.auth import get_user_model
from django.core import signing
from django.db import DatabaseError, connection, transaction
from django.db.models import F, Q
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET

from home.audit import AuditUnavailable, record_event
from home.models import AuditEvent

PAGE_SIZE = 100
EXPORT_LIMIT = 1000
EXPORT_BYTE_LIMIT = 1024 * 1024
EXPORTS_PER_HOUR = 5
CURSOR_MAX_AGE_SECONDS = 15 * 60
CURSOR_SALT = "home.audit.cursor.v1"
AUDIT_PERMISSION = "home.view_auditevent"
CSV_FIELDS = (
    "event_id",
    "occurred_at",
    "event_type",
    "outcome",
    "actor_kind",
    "actor_user_id",
    "target_user_id",
    "aggregate_count",
    "request_id",
)
FILTER_FIELDS = ("start_date", "end_date", "event_type", "actor_user_id", "target_user_id")
MAX_USER_ID = 2**63 - 1


def _authorized(request):
    return (
        request.user.is_authenticated
        and request.user.is_staff
        and request.user.has_perm(AUDIT_PERMISSION)
    )


def _authorized_user(user):
    return user.is_active and user.is_staff and user.has_perm(AUDIT_PERMISSION)


def _authorized_response(request):
    if not request.user.is_authenticated:
        return redirect(reverse("admin:login"))
    if not _authorized(request):
        return HttpResponse("Forbidden.", status=403)
    return None


def _parse_filters(query):
    allowed = {*FILTER_FIELDS, "cursor"}
    if set(query.keys()) - allowed or any(len(query.getlist(key)) != 1 for key in query):
        raise ValueError

    start_value = query.get("start_date", "")
    end_value = query.get("end_date", "")
    if bool(start_value) != bool(end_value):
        raise ValueError

    if start_value:
        start_day = datetime.strptime(start_value, "%Y-%m-%d").date()
        end_day = datetime.strptime(end_value, "%Y-%m-%d").date()
        if start_day.isoformat() != start_value or end_day.isoformat() != end_value:
            raise ValueError
    else:
        today = timezone.localdate()
        start_day = today - timedelta(days=6)
        end_day = today + timedelta(days=1)

    if end_day <= start_day or (end_day - start_day).days > 31:
        raise ValueError

    event_type = query.get("event_type", "")
    if event_type and event_type not in {
        value for value, _label in AuditEvent.EventType.choices
    }:
        raise ValueError

    filters = {
        "start_date": start_day.isoformat(),
        "end_date": end_day.isoformat(),
        "event_type": event_type,
    }
    for field in ("actor_user_id", "target_user_id"):
        value = query.get(field, "")
        if value:
            if not re.fullmatch(r"[1-9][0-9]*", value) or int(value) > MAX_USER_ID:
                raise ValueError
            filters[field] = value
        else:
            filters[field] = ""
    return filters


def _filtered_events(filters):
    start = datetime.combine(
        datetime.fromisoformat(filters["start_date"]).date(),
        time.min,
        tzinfo=datetime_timezone.utc,
    )
    end = datetime.combine(
        datetime.fromisoformat(filters["end_date"]).date(),
        time.min,
        tzinfo=datetime_timezone.utc,
    )
    events = AuditEvent.objects.filter(occurred_at__gte=start, occurred_at__lt=end)
    if filters["event_type"]:
        events = events.filter(event_type=filters["event_type"])
    if filters["actor_user_id"]:
        events = events.filter(actor_user_id=int(filters["actor_user_id"]))
    if filters["target_user_id"]:
        events = events.filter(target_user_id=int(filters["target_user_id"]))
    return events.order_by("-occurred_at", "-event_id")


def _filter_digest(filters):
    encoded = json.dumps(filters, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _make_cursor(event, filters):
    return signing.dumps(
        {
            "filter_digest": _filter_digest(filters),
            "occurred_at": event.occurred_at.isoformat(),
            "event_id": str(event.event_id),
        },
        salt=CURSOR_SALT,
    )


def _read_cursor(token, filters):
    payload = signing.loads(token, salt=CURSOR_SALT, max_age=CURSOR_MAX_AGE_SECONDS)
    if (
        not isinstance(payload, dict)
        or set(payload) != {"filter_digest", "occurred_at", "event_id"}
        or payload["filter_digest"] != _filter_digest(filters)
        or not isinstance(payload["occurred_at"], str)
        or not isinstance(payload["event_id"], str)
    ):
        raise ValueError
    occurred_at = datetime.fromisoformat(payload["occurred_at"])
    if timezone.is_naive(occurred_at):
        raise ValueError
    event_id = UUID(payload["event_id"])
    return occurred_at, event_id


def _query_with_cursor(events, cursor):
    if cursor is None:
        return events
    occurred_at, event_id = cursor
    return events.filter(
        Q(occurred_at__lt=occurred_at)
        | Q(occurred_at=occurred_at, event_id__lt=event_id),
    )


def _record_access(event_type, actor_user_id):
    return record_event(
        event_type=event_type,
        outcome=AuditEvent.Outcome.SUCCESS,
        actor_kind=AuditEvent.ActorKind.USER,
        actor_user_id=actor_user_id,
    )


@require_GET
def audit_event_list(request):
    access_response = _authorized_response(request)
    if access_response is not None:
        return access_response

    try:
        filters = _parse_filters(request.GET)
        cursor_token = request.GET.get("cursor", "")
        cursor = _read_cursor(cursor_token, filters) if cursor_token else None
    except (ValueError, TypeError, signing.BadSignature):
        return HttpResponseBadRequest("Invalid audit query.")

    try:
        with transaction.atomic():
            events = _query_with_cursor(_filtered_events(filters), cursor)
            rows = list(events[: PAGE_SIZE + 1])
            has_next = len(rows) > PAGE_SIZE
            page = rows[:PAGE_SIZE]
            next_cursor = _make_cursor(page[-1], filters) if has_next else ""
            _record_access(AuditEvent.EventType.ADMIN_AUDIT_READ, request.user.pk)
    except (AuditUnavailable, DatabaseError):
        return HttpResponse("Service temporarily unavailable.", status=503)

    response = render(
        request,
        "home/audit_events.html",
        {
            "events": page,
            "filters": filters,
            "next_cursor": next_cursor,
            "event_types": AuditEvent.EventType.choices,
        },
    )
    response["Cache-Control"] = "no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def _csv_bytes(events):
    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerow(CSV_FIELDS)
    for event in events:
        writer.writerow(
            [
                event.event_id,
                event.occurred_at.isoformat(),
                event.event_type,
                event.outcome,
                event.actor_kind,
                event.actor_user_id if event.actor_user_id is not None else "",
                event.target_user_id if event.target_user_id is not None else "",
                event.aggregate_count if event.aggregate_count is not None else "",
                event.request_id or "",
            ]
        )
    return output.getvalue().encode("utf-8")


@require_GET
def audit_event_export(request):
    access_response = _authorized_response(request)
    if access_response is not None:
        return access_response

    try:
        filters = _parse_filters(request.GET)
        if "cursor" in request.GET:
            raise ValueError
    except (ValueError, TypeError):
        return HttpResponseBadRequest("Invalid audit query.")

    try:
        with transaction.atomic():
            user_model = get_user_model()
            actor_query = user_model._default_manager.filter(pk=request.user.pk)
            if connection.features.has_select_for_update:
                actor = actor_query.select_for_update().first()
            else:
                actor = actor_query.first()
                if actor is not None:
                    # SQLite has no row locks; reserve its writer lock before checking quota.
                    primary_key = user_model._meta.pk.name
                    if not actor_query.update(**{primary_key: F(primary_key)}):
                        actor = None
                    else:
                        actor = actor_query.first()
            if actor is None or not _authorized_user(actor):
                return HttpResponse("Forbidden.", status=403)

            cutoff = timezone.now() - timedelta(hours=1)
            export_count = AuditEvent.objects.filter(
                event_type=AuditEvent.EventType.ADMIN_AUDIT_EXPORTED,
                actor_user_id=actor.pk,
                occurred_at__gte=cutoff,
            ).count()
            if export_count >= EXPORTS_PER_HOUR:
                return HttpResponse("Export limit reached.", status=429)

            events = list(_filtered_events(filters)[: EXPORT_LIMIT + 1])
            if len(events) > EXPORT_LIMIT:
                return HttpResponse("Export limit exceeded.", status=413)

            content = _csv_bytes(events)
            if len(content) > EXPORT_BYTE_LIMIT:
                return HttpResponse("Export limit exceeded.", status=413)
            _record_access(AuditEvent.EventType.ADMIN_AUDIT_EXPORTED, actor.pk)
    except (AuditUnavailable, DatabaseError):
        return HttpResponse("Service temporarily unavailable.", status=503)

    response = HttpResponse(content, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="audit-events.csv"'
    response["Cache-Control"] = "no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response
