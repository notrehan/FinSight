"""
Django settings for FinSight AI backend.
"""
import os
import sys
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

# Ensure apps, agent, rag, schemas, prompts can be imported directly if needed
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() in ("true", "1", "yes")
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set when DEBUG is disabled.")
    SECRET_KEY = "local-development-only-insecure-secret-key"

ALLOWED_HOSTS = [host.strip() for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if host.strip()]
if not DEBUG and ALLOWED_HOSTS == ['localhost', '127.0.0.1']:
    raise ImproperlyConfigured('Set DJANGO_ALLOWED_HOSTS to the production domain before deploying.')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party
    'corsheaders',
    'rest_framework',
    # FinSight Domain Apps
    'apps.accounts',
    'apps.companies',
    'apps.market_data',
    'apps.documents',
    'apps.announcements',
    'apps.sessions',
    'apps.tools',
    'apps.assistant',
    'apps.evaluations',
    'apps.observability',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Serve collected static assets from the production WSGI process.
MIDDLEWARE.insert(2, 'whitenoise.middleware.WhiteNoiseMiddleware')

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates', BASE_DIR.parent / 'frontend'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Database configuration: MySQL by default, SQLite only for explicit local fallback.
USE_MYSQL = os.getenv("USE_MYSQL", "true").lower() in ("true", "1", "yes")

if USE_MYSQL:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.getenv('MYSQL_DATABASE', 'finsight_db'),
            'USER': os.getenv('MYSQL_USER', 'finsight_app'),
            'PASSWORD': os.getenv('MYSQL_PASSWORD', 'finsight_secure_pass'),
            'HOST': os.getenv('MYSQL_HOST', 'localhost'),
            'PORT': os.getenv('MYSQL_PORT', '3306'),
            'OPTIONS': {
                'charset': 'utf8mb4',
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            }
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR.parent / 'frontend' / 'static']
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if origin.strip()]
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',') if origin.strip()]
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '0' if DEBUG else '31536000'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ],
}

# FinSight Agent & LLM settings
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")
LLM_API_KEY = os.getenv("LLM_API_KEY", os.getenv("GEMINI_API_KEY", ""))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
VECTOR_INDEX_PATH = BASE_DIR.parent / "vector_index"
PRICE_DATA_MAX_AGE_HOURS = int(os.getenv("PRICE_DATA_MAX_AGE_HOURS", "24"))
MAX_AGENT_STEPS = int(os.getenv("MAX_AGENT_STEPS", "8"))
MAX_QUERY_TOKENS = int(os.getenv("MAX_QUERY_TOKENS", "4000"))
PROMPT_VERSION = os.getenv("PROMPT_VERSION", "v1.2-grounded")
