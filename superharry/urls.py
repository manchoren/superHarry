from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from home.auth_views import (
    FreshAdminSessionLoginView,
    FreshSessionLoginView,
    FreshSessionLogoutView,
)
from home.health_views import metrics
from home.password_reset_views import complete_password_reset
from home.totp_views import (
    admin_reset_user_totp,
    totp_disable,
    totp_enrollment_confirm,
    totp_enrollment_start,
)

urlpatterns = [
    path("admin/login/", FreshAdminSessionLoginView.as_view(), name="admin-login"),
    path("admin/audit/", include("home.audit_urls")),
    path(
        "admin/users/<int:user_id>/totp/reset/",
        admin_reset_user_totp,
        name="admin-totp-reset",
    ),
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
    path("accounts/password-reset/", complete_password_reset, name="password_reset"),
    path(
        "accounts/password-change/",
        auth_views.PasswordChangeView.as_view(),
        name="password_change",
    ),
    path(
        "accounts/password-change/done/",
        auth_views.PasswordChangeDoneView.as_view(),
        name="password_change_done",
    ),
    path("accounts/totp/enrollment/start/", totp_enrollment_start, name="totp-enrollment-start"),
    path("accounts/totp/enrollment/confirm/", totp_enrollment_confirm, name="totp-enrollment-confirm"),
    path("accounts/totp/disable/", totp_disable, name="totp-disable"),
    path("", include("home.urls")),
]
