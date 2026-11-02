from django.db import DatabaseError, connection
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_GET

from home.observability import render_metrics


def _health_response(payload, status=200):
    response = JsonResponse(payload, status=status)
    response["Cache-Control"] = "no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@require_GET
def liveness(request):
    return _health_response({"status": "ok"})


@require_GET
def readiness(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return _health_response({"status": "not_ready"}, status=503)
    return _health_response({"status": "ready"})


@require_GET
def metrics(request):
    user = request.user
    if not user.is_authenticated:
        return redirect(reverse("admin:login"))
    if not user.is_active or not user.is_staff:
        return HttpResponse("Forbidden.", status=403)

    response = HttpResponse(
        render_metrics(),
        content_type="text/plain; version=0.0.4; charset=utf-8",
    )
    response["Cache-Control"] = "no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response
