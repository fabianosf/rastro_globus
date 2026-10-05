import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = (os.environ.get("SECRET_KEY") or "").strip() or (
    "django-insecure-rastroglobus-mvp-dev-only-change-in-prod"
)

DEBUG = (os.environ.get("DEBUG") or "1").strip().lower() in {"1", "true", "yes", "on"}

_allowed = (os.environ.get("ALLOWED_HOSTS") or "*").strip()
ALLOWED_HOSTS = [h.strip() for h in _allowed.split(",") if h.strip()] or ["*"]

_csrf = (os.environ.get("CSRF_TRUSTED_ORIGINS") or "").strip()
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf.split(",") if o.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "apps.core.apps.CoreConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "rastroglobus.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "rastroglobus.wsgi.application"

_DB_ENGINE = (os.environ.get("DB_ENGINE") or "").strip()
if _DB_ENGINE:
    DATABASES = {
        "default": {
            "ENGINE": _DB_ENGINE,
            "NAME": os.environ.get("DB_NAME", ""),
            "USER": os.environ.get("DB_USER", ""),
            "PASSWORD": os.environ.get("DB_PASSWORD", ""),
            "HOST": os.environ.get("DB_HOST", ""),
            "PORT": os.environ.get("DB_PORT", ""),
            "OPTIONS": {
                "charset": "utf8mb4",
                "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }
    # Servidor corporativo MariaDB 10.2 (Django 5 oficialmente exige 10.5+).
    # Ative com DB_ALLOW_LEGACY_MARIADB=1 no .env — preferir upgrade do servidor quando possível.
    # Django 5.2 assume RETURNING em todo MariaDB; 10.2 nao suporta — desliga o recurso.
    if (os.environ.get("DB_ALLOW_LEGACY_MARIADB") or "").strip() in {"1", "true", "yes"}:
        from django.db.backends.base.base import BaseDatabaseWrapper
        from django.db.backends.mysql.features import DatabaseFeatures

        BaseDatabaseWrapper.check_database_version_supported = lambda self: None  # noqa: E731
        DatabaseFeatures.can_return_columns_from_insert = property(lambda self: False)
        DatabaseFeatures.can_return_rows_from_bulk_insert = property(lambda self: False)
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "core.Usuario"

CORS_ALLOW_ALL_ORIGINS = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=8),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

# OCR DANFE (OpenAI Vision) — foto → campos; persistência só após revisão no formulário
OPENAI_API_KEY = (os.environ.get("OPENAI_API_KEY") or "").strip()
OPENAI_VISION_MODEL = (os.environ.get("OPENAI_VISION_MODEL") or "gpt-4o-mini").strip()

# --- Samba / AD LDAPS (auth-only; não altera o diretório) ---
# Ligar com AD_LDAP_ENABLED=1 após CA + conta de serviço. Padrão: desligado.
from apps.core.ldap_auth import configure_ldap_settings  # noqa: E402

_ldap_cfg = configure_ldap_settings()
AD_LDAP_ENABLED = bool(_ldap_cfg.pop("AD_LDAP_ENABLED", False))
for _k, _v in _ldap_cfg.items():
    globals()[_k] = _v

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "loggers": {
        "sggi.auth": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "django_auth_ldap": {
            "handlers": ["console"],
            "level": "WARNING",
        },
    },
}
