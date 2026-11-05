import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.core.management.utils import get_random_secret_key

BASE_DIR = Path(__file__).resolve().parent.parent
SUPERHARRY_CONSTITUTION_SHA256 = (
    "6e18224de33f639501cb7b20fb57a764dcff691282d4b63153b54ab4cd7735eb"
)

debug_value = os.environ.get("DJANGO_DEBUG", "1").strip().lower()
if debug_value not in {"0", "1", "false", "true"}:
    raise ImproperlyConfigured("DJANGO_DEBUG must be one of: 0, 1, false, true.")
DEBUG = debug_value in {"1", "true"}

SUPERHARRY_DIAGNOSTIC_LOG_PATH = os.environ.get(
    "SUPERHARRY_DIAGNOSTIC_LOG_PATH",
    "",
).strip()
if SUPERHARRY_DIAGNOSTIC_LOG_PATH:
    from home.observability import purge_expired_diagnostic_logs

    purge_expired_diagnostic_logs(SUPERHARRY_DIAGNOSTIC_LOG_PATH)

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is disabled.")
    SECRET_KEY = get_random_secret_key()

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")
    if host.strip()
]
SUPERHARRY_HOSTNAME = "superharry.local"

# Development free-provider routing. The order is administrator-configured; a
# provider is attempted only with a configured key and an explicit quota row.
SUPERHARRY_FREE_PROVIDER_ORDER = os.environ.get("SUPERHARRY_FREE_PROVIDER_ORDER", "gemini,groq,openrouter")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "liquid/lfm-2.5-2.6b:free")
OPENROUTER_UPSTREAM = os.environ.get("OPENROUTER_UPSTREAM", "liquid/fp8")
# Non-resetting shared allowances for Groq and OpenRouter (defaults proposed; owner confirmation pending).
SUPERHARRY_PROVIDER_REQUEST_ALLOWANCE = int(os.environ.get("SUPERHARRY_PROVIDER_REQUEST_ALLOWANCE", "100"))
SUPERHARRY_PROVIDER_TOKEN_ALLOWANCE = int(os.environ.get("SUPERHARRY_PROVIDER_TOKEN_ALLOWANCE", "100000"))
if not ALLOWED_HOSTS:
    if not DEBUG:
        raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must be set when DJANGO_DEBUG is disabled.")
    ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]", SUPERHARRY_HOSTNAME]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "home",
]

MIDDLEWARE = [
    "home.observability.ObservabilityMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "home.middleware.StrictOriginMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "home.middleware.SessionLifetimeMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "superharry_json": {
            "()": "home.observability.JsonEventFormatter",
        },
    },
    "filters": {
        "superharry_diagnostics_enabled": {
            "()": "home.observability.DiagnosticEnabledFilter",
        },
    },
    "handlers": (
        {
            "superharry_null": {
                "class": "logging.NullHandler",
            },
            "superharry_diagnostics": {
                "()": "home.observability.PrivateTimedRotatingFileHandler",
                "filename": SUPERHARRY_DIAGNOSTIC_LOG_PATH,
                "when": "midnight",
                "interval": 1,
                "backupCount": 29,
                "utc": True,
                "encoding": "utf-8",
                "formatter": "superharry_json",
                "filters": ["superharry_diagnostics_enabled"],
            },
        }
        if SUPERHARRY_DIAGNOSTIC_LOG_PATH
        else {
            "superharry_null": {
                "class": "logging.NullHandler",
            },
        }
    ),
    "loggers": {
        "superharry.diagnostics": {
            "handlers": (
                ["superharry_diagnostics"]
                if SUPERHARRY_DIAGNOSTIC_LOG_PATH
                else ["superharry_null"]
            ),
            "level": "INFO",
            "propagate": False,
        },
    },
}

ROOT_URLCONF = "superharry.urls"
CSRF_FAILURE_VIEW = "home.api_errors.csrf_failure"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "superharry.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en"
LANGUAGES = [("en", "English"), ("es", "Spanish")]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_NAME = "__Host-superharry_session"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Strict"
SESSION_COOKIE_PATH = "/"
SESSION_COOKIE_DOMAIN = None
SESSION_ENGINE = "django.contrib.sessions.backends.db"
CSRF_USE_SESSIONS = True
CSRF_COOKIE_SECURE = not DEBUG
CSRF_TRUSTED_ORIGINS = [f"https://{SUPERHARRY_HOSTNAME}"]
