from django.urls import path

from .audit_views import audit_event_export, audit_event_list

urlpatterns = [
    path("", audit_event_list, name="admin-audit-list"),
    path("export.csv", audit_event_export, name="admin-audit-export"),
]
