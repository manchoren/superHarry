from django.contrib.auth.password_validation import (
    CommonPasswordValidator,
    MinimumLengthValidator,
    UserAttributeSimilarityValidator,
)

from home.passwords import normalize_password


class NFCMinimumLengthValidator(MinimumLengthValidator):
    def validate(self, password, user=None):
        return super().validate(normalize_password(password), user)


class NFCCommonPasswordValidator(CommonPasswordValidator):
    def validate(self, password, user=None):
        return super().validate(normalize_password(password), user)


class NFCUserAttributeSimilarityValidator(UserAttributeSimilarityValidator):
    def validate(self, password, user=None):
        return super().validate(normalize_password(password), user)
