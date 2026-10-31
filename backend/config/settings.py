import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv
from config.cloudinary_client import configure_cloudinary

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
configure_cloudinary()

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
DEBUG = os.getenv("DJANGO_DEBUG", "false").strip().lower() in {"1", "true", "yes"}
ALLOWED_HOSTS = [host.strip() for host in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if host.strip()]

EMAIL_BACKEND = os.getenv("DJANGO_EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend").strip()
EMAIL_HOST = os.getenv("SMTP_HOST", "").strip()
EMAIL_PORT = int(os.getenv("SMTP_PORT", "587"))
EMAIL_HOST_USER = os.getenv("SMTP_USERNAME", "").strip()
EMAIL_HOST_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("SMTP_USE_TLS", "true").strip().lower() in {"1", "true", "yes"}
EMAIL_USE_SSL = os.getenv("SMTP_USE_SSL", "false").strip().lower() in {"1", "true", "yes"}
EMAIL_TIMEOUT = 10
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "").strip()
EMAIL_VERIFICATION_EXPIRY_MINUTES = int(os.getenv("EMAIL_VERIFICATION_EXPIRY_MINUTES", "10"))
EMAIL_VERIFICATION_MAX_ATTEMPTS = int(os.getenv("EMAIL_VERIFICATION_MAX_ATTEMPTS", "5"))
EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS = int(os.getenv("EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS", "60"))

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
JWT_ACCESS_TOKEN_LIFETIME = int(os.getenv("JWT_ACCESS_TOKEN_LIFETIME", "15"))
JWT_REFRESH_TOKEN_LIFETIME = int(os.getenv("JWT_REFRESH_TOKEN_LIFETIME", "7"))
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256").strip()
JWT_ISSUER = os.getenv("JWT_ISSUER", "").strip()
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "").strip()

if EMAIL_VERIFICATION_EXPIRY_MINUTES < 1:
    raise ImproperlyConfigured("EMAIL_VERIFICATION_EXPIRY_MINUTES must be positive.")
if EMAIL_VERIFICATION_MAX_ATTEMPTS < 1:
    raise ImproperlyConfigured("EMAIL_VERIFICATION_MAX_ATTEMPTS must be positive.")
if EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS < 1:
    raise ImproperlyConfigured("EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS must be positive.")
if JWT_ACCESS_TOKEN_LIFETIME < 1 or JWT_REFRESH_TOKEN_LIFETIME < 1:
    raise ImproperlyConfigured("JWT token lifetimes must be positive.")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "core",
    "accounts",
    "movies",
    "series",
    "media",
    "favorites",
    "watch_progress",
    "reviews",
    "analytics",
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

ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Django's own framework components require this setting. CineSplit application
# persistence uses PyMongo exclusively and does not use this database.
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / ".framework.sqlite3"}}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = [origin.strip() for origin in os.getenv("DJANGO_CORS_ALLOWED_ORIGINS", "").split(",") if origin.strip()]
if DEBUG:
    for origin in (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ):
        if origin not in CORS_ALLOWED_ORIGINS:
            CORS_ALLOWED_ORIGINS.append(origin)

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": ["accounts.authentication.MongoJWTAuthentication"],
    "DEFAULT_THROTTLE_CLASSES": ["accounts.throttles.MongoRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        "auth_register": "5/hour",
        "auth_login": "10/minute",
        "auth_verify": "10/hour",
        "auth_resend": "3/hour",
        "auth_refresh": "30/hour",
    },
    "EXCEPTION_HANDLER": "accounts.exceptions.safe_exception_handler",
}
SPECTACULAR_SETTINGS = {
    "TITLE": "CineSplit API",
    "DESCRIPTION": "CineSplit REST API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "REDOC_DIST": "https://cdn.jsdelivr.net/npm/redoc@2.1.5",
}

CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
