"""Isolated Windows desktop development profile. No public listener/hosting."""
import os
from pathlib import Path
from .settings import *  # noqa: F403,F401

DESKTOP_DATA_DIR = Path(os.environ.get('ERP_DESKTOP_DATA_DIR', str(BASE_DIR.parent / 'storage' / 'v2-desktop')))  # noqa: F405
secret_path = DESKTOP_DATA_DIR / 'service-secret.txt'
if not secret_path.is_file():
    raise RuntimeError('Initialize the desktop profile with scripts/prepare-v2-desktop.ps1 first.')
SECRET_KEY = secret_path.read_text(encoding='utf-8').strip()
if len(SECRET_KEY) < 48:
    raise RuntimeError('Desktop service secret is invalid.')
DEBUG = False
V2_DESKTOP = True
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '[::1]']
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': DESKTOP_DATA_DIR / 'register.sqlite3', 'OPTIONS': {'timeout': 20}}}
CORS_ALLOWED_ORIGINS = []
# Private native-client loopback traffic only; never use this for a public host.
SECURE_SSL_REDIRECT = False
MEDIA_ROOT = DESKTOP_DATA_DIR / 'evidence'
# Register supporting documents are private database blobs, served only through authenticated APIs.
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
