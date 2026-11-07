from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model


class UsernameAuthenticationBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(get_user_model().USERNAME_FIELD)
        if username is None or password is None:
            return None
        user = super().authenticate(request, username=username, password=password, **kwargs)
        if user is None:
            return None
        return user
