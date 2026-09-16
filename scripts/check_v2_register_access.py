"""Read-only endpoint and role checks against the existing isolated V2 profile.

Uses Django's request factory to exercise permissions with existing active users;
does not create a login token, change a password or insert test transactions.
"""
import os
from pathlib import Path
import sys
from urllib.request import urlopen
import json

root = Path(__file__).resolve().parents[1]
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.desktop'
os.environ['ERP_DESKTOP_DATA_DIR'] = str(root / 'storage/v2-desktop')
sys.path.insert(0, str(root / 'backend'))
import django
django.setup()
from django.urls import resolve
from rest_framework.test import APIRequestFactory, force_authenticate
from core.models import User

factory = APIRequestFactory()
paths = ['/api/profile/', '/api/register/masters/', '/api/register/entries/',
         '/api/register/positions/', '/api/register/reports/', '/api/register/imports/']
for role in ['Administrator', 'Finance Manager']:
    user = User.objects.select_related('role').filter(role__name=role, status='active', is_active=True).first()
    if user is None:
        print(role + ': no active account to verify')
        continue
    for path in paths:
        request = factory.get(path)
        force_authenticate(request, user=user)
        match = resolve(path)
        response = match.func(request, **match.kwargs)
        assert response.status_code == 200, (role, path, response.status_code)
    print(role + ': profile, masters, entries, openings/transfers, reports and imports all return 200')
    if role == 'Administrator':
        for path in ['/api/register/data-management/', '/api/register/import-template/']:
            request = factory.get(path)
            force_authenticate(request, user=user)
            match = resolve(path)
            response = match.func(request, **match.kwargs)
            assert response.status_code == 200, (path, response.status_code)
            response.close()
        print('Administrator: data management and workbook download return 200')

request = factory.get('/api/register/entries/')
assert resolve('/api/register/entries/').func(request).status_code == 401
print('Unauthenticated register request: 401')
for url in ['http://127.0.0.1:5174/', 'http://127.0.0.1:8766/api/health/']:
    with urlopen(url, timeout=15) as response:
        assert response.status == 200
        if '/health/' in url:
            assert json.load(response)['version'] == '2.1.0'
        print(url + ': 200')
