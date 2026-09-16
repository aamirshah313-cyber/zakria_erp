"""Browser acceptance service, bound only to loopback and isolated V2 data."""
import os
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root/'backend'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.desktop'
os.environ['ERP_DESKTOP_DATA_DIR'] = str(root/'storage/v2-desktop')
print('Starting isolated V2 acceptance service.', flush=True)
import config.desktop as profile
profile.CORS_ALLOWED_ORIGINS = ['http://127.0.0.1:5174']
from django.core.wsgi import get_wsgi_application
from waitress import serve
application = get_wsgi_application()
print('V2 application loaded; listening on 127.0.0.1:8766.', flush=True)
serve(application, host='127.0.0.1', port=8766)
