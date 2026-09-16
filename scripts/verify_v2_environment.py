"""Read-only readiness checks; prints no passwords, hashes or secret values."""
from pathlib import Path
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.request

root = Path(__file__).resolve().parents[1]
pilot_path = root / 'backend' / 'local.sqlite3'
desktop_path = root / 'storage' / 'v2-desktop' / 'register.sqlite3'
assert pilot_path.resolve() != desktop_path.resolve()

with sqlite3.connect(pilot_path.as_uri() + '?mode=ro', uri=True) as pilot:
    with sqlite3.connect(desktop_path.as_uri() + '?mode=ro', uri=True) as desktop:
        # Suitable immediately after the optional initialization copy; later
        # deliberate account changes in either independent database may differ.
        fields = 'id, username, password, role_id, status, is_active'
        original_users = pilot.execute(f'SELECT {fields} FROM core_user ORDER BY id').fetchall()
        copied_users = desktop.execute(f'SELECT {fields} FROM core_user ORDER BY id').fetchall()
        assert copied_users == original_users, 'User records differ; check whether either environment has since been edited.'
        assert desktop.execute('SELECT count(*) FROM core_accesssession').fetchone()[0] == 0
        assert desktop.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
print('PASS: isolated database, account preservation, cleared copied sessions and SQLite integrity.')

before = desktop_path.read_bytes()
subprocess.run([sys.executable, str(root / 'scripts' / 'prepare_v2_desktop.py'), '--copy-pilot'], check=True)
assert desktop_path.read_bytes() == before, 'Reinitialization changed existing V2 data.'
print('PASS: repeated initialization preserves the existing V2 database.')

with urllib.request.urlopen('http://127.0.0.1:8765/api/health/', timeout=5) as response:
    assert response.status == 200
try:
    urllib.request.urlopen('http://127.0.0.1:8765/api/parties/', timeout=5)
except urllib.error.HTTPError as response:
    assert response.code == 401
else:
    raise AssertionError('Unauthenticated business endpoint was not rejected.')
print('PASS: local service healthy and business records require authentication.')
