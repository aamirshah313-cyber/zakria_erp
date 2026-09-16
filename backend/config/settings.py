import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = os.environ.get('ERP_DEBUG', '1') == '1'
SECRET_KEY = os.environ.get('ERP_SECRET_KEY', 'development-only-change-before-deployment')
if not DEBUG and SECRET_KEY == 'development-only-change-before-deployment':
    raise RuntimeError('Set ERP_SECRET_KEY before production deployment')
ALLOWED_HOSTS = os.environ.get('ERP_ALLOWED_HOSTS', 'localhost,127.0.0.1,10.0.2.2,testserver').split(',')
INSTALLED_APPS = ['django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions', 'corsheaders', 'rest_framework', 'core']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'corsheaders.middleware.CorsMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware']
ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'
AUTH_USER_MODEL = 'core.User'
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'local.sqlite3', 'OPTIONS': {'timeout': 20}}}
if os.environ.get('POSTGRES_HOST'):
    DATABASES['default'] = {'ENGINE': 'django.db.backends.postgresql', 'NAME': os.environ.get('POSTGRES_DB', 'zakaria'), 'USER': os.environ.get('POSTGRES_USER', 'zakaria'), 'PASSWORD': os.environ['POSTGRES_PASSWORD'], 'HOST': os.environ['POSTGRES_HOST'], 'PORT': os.environ.get('POSTGRES_PORT', '5432')}
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 10}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
REST_FRAMEWORK = {'DEFAULT_AUTHENTICATION_CLASSES': ['core.auth.SessionAuthentication'], 'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'], 'DEFAULT_THROTTLE_CLASSES': ['rest_framework.throttling.AnonRateThrottle'], 'DEFAULT_THROTTLE_RATES': {'anon': '60/min', 'login': '10/min'}}
CORS_ALLOWED_ORIGINS = ['http://localhost:5173', 'http://127.0.0.1:5173'] if DEBUG else os.environ.get('ERP_CORS_ORIGINS', '').split(',')
USE_TZ = True
TIME_ZONE = 'Asia/Karachi'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
