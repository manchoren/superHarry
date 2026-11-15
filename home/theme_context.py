from home.models import UserThemePreference


def theme_preference(request):
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {}
    theme = UserThemePreference.objects.filter(user=request.user).values_list('theme', flat=True).first()
    return {'account_theme': theme or 'system'}
