"""
Django settings for Inventory & POS Management System.
"""
import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

# ডেভেলপমেন্টের জন্য। প্রোডাকশনে অবশ্যই environment variable থেকে নিতে হবে।
SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-change-me-before-production")

DEBUG = os.environ.get("DEBUG", "True").lower() in ("1", "true", "yes")

#ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

ALLOWED_HOSTS = os.environ.get(
    "ALLOWED_HOSTS",
    "localhost,127.0.0.1"
).split(",")

# Production security settings
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_SSL_REDIRECT = not DEBUG

SESSION_COOKIE_SECURE = not DEBUG

CSRF_COOKIE_SECURE = not DEBUG

CSRF_TRUSTED_ORIGINS = os.environ.get(
    "CSRF_TRUSTED_ORIGINS",
    ""
).split(",") if os.environ.get("CSRF_TRUSTED_ORIGINS") else []


def _env_bool(name, default):
    return os.environ.get(name, str(default)).lower() in ("1", "true", "yes")


# Self-registration (POST /api/auth/register/)
# - ENABLED:      false করলে public registration বন্ধ (শুধু Admin ইউজার তৈরি করতে পারবে)
# - AUTO_APPROVE: false (default) হলে নতুন অ্যাকাউন্ট inactive থাকে, Admin approve করলে তবেই login করা যায়।
#                 true হলে সাথে সাথে login করা যায়। নতুন ইউজার সবসময় Cashier role পায়।
SELF_REGISTRATION_ENABLED = _env_bool("SELF_REGISTRATION_ENABLED", True)
SELF_REGISTRATION_AUTO_APPROVE = _env_bool("SELF_REGISTRATION_AUTO_APPROVE", False)


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "drf_spectacular",
    # Local apps
    "accounts",
    "categories",
    "products",
    "suppliers",
    "customers",
    "purchases",
    "sales",
    "inventory",
    "reports",
    "dashboard",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # অবশ্যই CommonMiddleware-এর আগে
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware", # Radia
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database: শুধু SQLite
# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.sqlite3",
#         "NAME": BASE_DIR / "db.sqlite3",
#     }
# }


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME"),
        "USER": os.environ.get("DB_USER"),
        "PASSWORD": os.environ.get("DB_PASSWORD"),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

# Custom User Model (Phase 2-তে role যোগ হবে)
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Dhaka"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
}


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "config.pagination.StandardPagination",
    "DEFAULT_FILTER_BACKENDS": (
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "EXCEPTION_HANDLER": "config.exceptions.custom_exception_handler",
    # শুধু যেসব view-তে throttle_scope দেওয়া আছে সেগুলোতে প্রযোজ্য (register: spam রোধ)
    "DEFAULT_THROTTLE_RATES": {
        "register": os.environ.get("REGISTER_THROTTLE_RATE", "10/hour"),
    },
}

# Simple JWT
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# CORS: ভবিষ্যতের React (Vite) ফ্রন্টএন্ডের জন্য
# CORS_ALLOWED_ORIGINS = [
#     "http://localhost:5173",
#     "http://127.0.0.1:5173",
# ]

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]


# drf-spectacular (Swagger / ReDoc)
SPECTACULAR_SETTINGS = {
    "TITLE": "Inventory & POS Management API",
    "DESCRIPTION": (
        "Backend API for the Inventory & POS Management System (BASIS final project).\n\n"
        "**How to authenticate:** call `POST /api/auth/login/`, copy the `access` token, "
        "click **Authorize** and paste it (the `Bearer` prefix is added automatically).\n\n"
        "**Roles:** Admin (full access) and Cashier (POS/sales, read-only catalog)."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": "/api",
    "TAGS": [
        {"name": "Auth"}, {"name": "Users"}, {"name": "Categories"}, {"name": "Products"},
        {"name": "Suppliers"}, {"name": "Customers"}, {"name": "Purchases"}, {"name": "Sales"},
        {"name": "Inventory"}, {"name": "Reports"}, {"name": "Dashboard"},
    ],
}


# Shop details printed on invoices / receipts (override with environment variables)
SHOP_NAME = os.environ.get("SHOP_NAME", "Inventory POS")
SHOP_ADDRESS = os.environ.get("SHOP_ADDRESS", "")
SHOP_PHONE = os.environ.get("SHOP_PHONE", "")
SHOP_RECEIPT_FOOTER = os.environ.get("SHOP_RECEIPT_FOOTER", "Thank you for your purchase!")

# Optional Unicode .ttf for PDFs so Bengali text and the ৳ sign can be printed (see sales/pdf.py)
PDF_FONT_REGULAR = os.environ.get("PDF_FONT_REGULAR", "")
PDF_FONT_BOLD = os.environ.get("PDF_FONT_BOLD", "")
