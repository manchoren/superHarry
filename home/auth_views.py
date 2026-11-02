from django.contrib import admin
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth.decorators import login_not_required
from django.contrib.auth.views import LoginView
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache


class FreshSessionLoginView(LoginView):
    def form_valid(self, form):
        self.request.session.flush()
        return super().form_valid(form)


@method_decorator(never_cache, name="dispatch")
@method_decorator(login_not_required, name="dispatch")
class FreshAdminSessionLoginView(FreshSessionLoginView):
    authentication_form = AdminAuthenticationForm
    template_name = "admin/login.html"

    def get_default_redirect_url(self):
        return reverse("admin:index")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(admin.site.each_context(self.request))
        context.update(
            {
                "title": _("Log in"),
                "subtitle": None,
                "app_path": self.request.get_full_path(),
                "username": self.request.user.get_username(),
            }
        )
        return context
