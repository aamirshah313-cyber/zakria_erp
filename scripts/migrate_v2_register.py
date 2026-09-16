"""Back up and migrate the isolated V2 database; never migrates the pilot."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import os
import sqlite3
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
data_dir = root/'storage/v2-desktop'
database = data_dir/'register.sqlite3'
pilot = root/'backend/local.sqlite3'
assert database.is_file() and database.resolve() != pilot.resolve()
pilot_hash = hashlib.sha256(pilot.read_bytes()).hexdigest() if pilot.exists() else None
backup_dir = root/'storage/backups'
backup_dir.mkdir(parents=True, exist_ok=True)
backup = backup_dir / ('before-register-extension-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')+'.sqlite3')
assert not backup.exists()
with sqlite3.connect(database.as_uri()+'?mode=ro', uri=True) as source:
    users = source.execute('SELECT id, username, password, role_id, status, is_active FROM core_user ORDER BY id').fetchall()
    count = source.execute('SELECT COUNT(*) FROM core_registerentry').fetchone()[0]
    with sqlite3.connect(backup) as target:
        source.backup(target)
        assert target.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
environment = dict(os.environ, DJANGO_SETTINGS_MODULE='config.desktop', ERP_DESKTOP_DATA_DIR=str(data_dir))
subprocess.run([sys.executable, str(root/'backend/manage.py'), 'migrate', '--noinput', '--settings=config.desktop'], env=environment, cwd=root/'backend', check=True)
with sqlite3.connect(database.as_uri()+'?mode=ro', uri=True) as source:
    assert source.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    assert users == source.execute('SELECT id, username, password, role_id, status, is_active FROM core_user ORDER BY id').fetchall()
    assert count == source.execute('SELECT COUNT(*) FROM core_registerentry').fetchone()[0]
assert pilot_hash == (hashlib.sha256(pilot.read_bytes()).hexdigest() if pilot.exists() else None)
print('PASS: V2 integrity, users/passwords/roles and existing register count preserved; pilot unchanged.')
print('Backup:', backup)
