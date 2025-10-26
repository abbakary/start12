from pathlib import Path
import os
import pymysql

# Install MySQL driver
pymysql.install_as_MySQLdb()

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Security key (DO NOT use this in production)
SECRET_KEY = 'django-insecure-your-secret-key-here'

# Debug mode (set to False in production)
DEBUG = True

# Allowed hosts
ALLOWED_HOSTS = ['*'] if DEBUG else ['yourdomain.com']

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django_apscheduler",
    "tracker.apps.TrackerConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "tracker.middleware.TimezoneMiddleware",  # Custom middleware
    "tracker.middleware.AutoProgressOrdersMiddleware",  # Auto-progress orders
]

ROOT_URLCONF = "pos_tracker.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "tracker" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "tracker.context_processors.header_notifications",
            ],
        },
    },
]

WSGI_APPLICATION = "pos_tracker.wsgi.application"

# --- DATABASE CONFIGURATION (MySQL) ---
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.mysql',
#         'NAME': 'stms',
#         'USER': 'root',
#         'PASSWORD': '',  # Set your MySQL password here
#         'HOST': 'localhost',
#         'PORT': '3306',
#         'OPTIONS': {
#             'init_command': "SET sql_mode='STRICT_TRANS_TABLES', default_storage_engine=INNODB",
#             'charset': 'utf8mb4',
#             'autocommit': True,
#         },
#         'TIME_ZONE': 'Asia/Riyadh',
#         'CONN_MAX_AGE': 300,  # Optional: keep connections alive longer
#     }
# }
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Timezone settings
TIME_ZONE = 'Asia/Riyadh'
USE_TZ = True

# Password validation (disable for local/dev)
AUTH_PASSWORD_VALIDATORS = [] if DEBUG else [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Language and localization
LANGUAGE_CODE = "en-us"
USE_I18N = True
USE_L10N = False  # Custom date formats below

# Custom date/time formats
DATE_FORMAT = 'M d, Y'
DATETIME_FORMAT = 'M d, Y H:i'
SHORT_DATE_FORMAT = 'M d, Y'
SHORT_DATETIME_FORMAT = 'M d, Y H:i'

# Static files (CSS, JS, etc.)
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "tracker" / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Media files (uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Allow same-origin embedding (needed to preview PDFs in iframes)
X_FRAME_OPTIONS = 'SAMEORIGIN'

# Primary key auto field
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Authentication redirects
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"
LOGIN_URL = "/login/"

# Session settings
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = 1209600  # 2 weeks in seconds

# Security settings for production
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True

# APScheduler configuration
APSCHEDULER_DATETIME_FORMAT = "N j, Y, f:s a"
APSCHEDULER_RUN_NOW_TIMEOUT = 25  # Seconds

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG' if DEBUG else 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'debug.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'DEBUG' if DEBUG else 'INFO',
    },
}
