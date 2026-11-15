from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from home.models import UserThemePreference


@login_required
@require_POST
def update_theme(request):
    theme = request.POST.get('theme')
    if theme not in ('system', 'light', 'dark'):
        return HttpResponseBadRequest('invalid_theme')
    UserThemePreference.objects.update_or_create(user=request.user, defaults={'theme': theme})
    target = request.POST.get('next', '')
    if not target.startswith('/') or not url_has_allowed_host_and_scheme(target, allowed_hosts=set(), require_https=request.is_secure()):
        target = '/'
    return redirect(target)
