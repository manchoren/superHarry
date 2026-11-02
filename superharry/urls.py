from django.contrib import admin
from django.urls import include, path

from home.auth_views import FreshAdminSessionLoginView, FreshSessionLoginView

urlpatterns = [
    path("admin/login/", FreshAdminSessionLoginView.as_view(), name="admin-login"),
    path("admin/", admin.site.urls),
    path(
        "accounts/login/",
        FreshSessionLoginView.as_view(
            template_name="registration/login.html",
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("home.urls")),
]
