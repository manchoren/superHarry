from django.contrib import admin
from django.urls import include, path

from home.auth_views import (
    FreshAdminSessionLoginView,
    FreshSessionLoginView,
    FreshSessionLogoutView,
)
from home.health_views import metrics

urlpatterns = [
    path("admin/login/", FreshAdminSessionLoginView.as_view(), name="admin-login"),
    path("admin/audit/", include("home.audit_urls")),
    path("health/", include("home.health_urls")),
    path("metrics", metrics, name="metrics"),
    path("admin/", admin.site.urls),
    path(
        "accounts/login/",
        FreshSessionLoginView.as_view(
            template_name="registration/login.html",
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("accounts/logout/", FreshSessionLogoutView.as_view(), name="logout"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("home.urls")),
]
