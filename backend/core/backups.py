"""Full data backup and restore for the desktop installation.

Supporting documents are database blobs, so one SQLite snapshot is a complete
backup. A .zerp-backup file is a zip holding manifest.json and the database,
optionally encrypted with AES-256-GCM using a scrypt-derived key. Passwords are
never stored or logged; a forgotten password makes that backup unreadable.

Restore replaces every record, account and password with the backup's, after
saving an unencrypted safety copy of the current data. All sessions end.
"""
import base64
from contextlib import closing
from datetime import date, datetime
import hashlib
import io
import json
import re
import secrets
import sqlite3
import tempfile
import threading
import time
import zipfile
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from django.conf import settings
from django.core import signing
from django.core.management import call_command
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.http import HttpResponse
from django.utils.http import content_disposition_header
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from .auth import audit, require
from .first_run import setup_required
from .models import AccessSession

FORMAT = 'zakaria-erp-backup'
EXTENSION = '.zerp-backup'
AUTOMATIC_KEEP = 7
MAX_DATABASE_BYTES = 2 * 1024 ** 3
SCRYPT = {'n': 2 ** 15, 'r': 8, 'p': 1}
AAD = b'zakaria-erp-backup-v1'
NAME_PATTERN = re.compile(r'^(manual|auto|pre-restore|before-upgrade)-\d{8}-\d{6}(-\d+)?\.zerp-backup$')
_restore_lock = threading.Lock()


def app_version():
    return '2.1.0'


def backups_dir():
    folder = Path(settings.DESKTOP_DATA_DIR) / 'backups'
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def staging_dir():
    folder = Path(settings.DESKTOP_DATA_DIR) / 'restore-staging'
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _key(password, salt, params):
    return Scrypt(salt=salt, length=32, **params).derive(password.encode('utf-8'))


def snapshot_bytes():
    """Consistent copy of the live database, without sign-in sessions."""
    with tempfile.TemporaryDirectory() as folder:
        target = Path(folder) / 'snapshot.sqlite3'
        connection.ensure_connection()
        with closing(sqlite3.connect(target)) as copy:
            connection.connection.backup(copy)
            copy.execute('DELETE FROM core_accesssession')
            copy.commit()
            if copy.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValidationError('The database failed its integrity check; no backup was written.')
        return target.read_bytes()


def build_backup(kind, password='', when=None):
    database = snapshot_bytes()
    manifest = {'format': FORMAT, 'format_version': 1, 'app_version': app_version(), 'kind': kind,
                'created_at': datetime.now().astimezone().isoformat(timespec='seconds'),
                'sha256': hashlib.sha256(database).hexdigest(), 'encrypted': bool(password)}
    stream = io.BytesIO()
    if password:
        salt, nonce = secrets.token_bytes(16), secrets.token_bytes(12)
        manifest['kdf'] = {'name': 'scrypt', **SCRYPT, 'salt': base64.b64encode(salt).decode()}
        manifest['nonce'] = base64.b64encode(nonce).decode()
        payload = AESGCM(_key(password, salt, SCRYPT)).encrypt(nonce, database, AAD)
        with zipfile.ZipFile(stream, 'w', zipfile.ZIP_STORED) as archive:
            archive.writestr('manifest.json', json.dumps(manifest, indent=2))
            archive.writestr('database.sqlite3.enc', payload)
    else:
        with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('manifest.json', json.dumps(manifest, indent=2))
            archive.writestr('database.sqlite3', database)
    stamp = (when or datetime.now()).strftime('%Y%m%d-%H%M%S')
    return f'{kind}-{stamp}{EXTENSION}', stream.getvalue(), manifest


def save_local_backup(kind, when=None):
    name, content, manifest = build_backup(kind, when=when)
    target = backups_dir() / name
    if target.exists():
        target = target.with_name(target.name.replace(EXTENSION, f'-{secrets.randbelow(10 ** 6)}{EXTENSION}'))
    temporary = target.with_suffix('.partial')
    temporary.write_bytes(content)
    temporary.replace(target)
    return target, manifest


def automatic_backup_if_due(today=None):
    """One automatic copy per local day; keep only the newest AUTOMATIC_KEEP."""
    if setup_required():
        return None  # Nothing worth keeping before the first account exists.
    today = today or date.today()
    folder = backups_dir()
    automatic = sorted(folder.glob('auto-*' + EXTENSION))
    created = None
    if not any(path.name.startswith(f"auto-{today.strftime('%Y%m%d')}-") for path in automatic):
        created, _ = save_local_backup('auto', datetime.combine(today, datetime.now().time()))
        automatic = sorted(folder.glob('auto-*' + EXTENSION))
    for old in automatic[:-AUTOMATIC_KEEP]:
        old.unlink(missing_ok=True)
    return created


def read_manifest(archive):
    try:
        manifest = json.loads(archive.read('manifest.json'))
    except (KeyError, ValueError):
        raise ValidationError('This is not a Zakaria ERP backup file.')
    if manifest.get('format') != FORMAT or manifest.get('format_version') != 1:
        raise ValidationError('This backup format is not supported by this version.')
    return manifest


def open_backup(content, password=''):
    """Validate a backup file and return (manifest, database bytes)."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile:
        raise ValidationError('This is not a Zakaria ERP backup file.')
    with archive:
        manifest = read_manifest(archive)
        member = 'database.sqlite3.enc' if manifest.get('encrypted') else 'database.sqlite3'
        try:
            info = archive.getinfo(member)
        except KeyError:
            raise ValidationError('The backup file is incomplete.')
        if info.file_size > MAX_DATABASE_BYTES:
            raise ValidationError('The backup is larger than this version can restore.')
        payload = archive.read(member)
    if manifest.get('encrypted'):
        if not password:
            raise ValidationError({'password': ['This backup is password-protected. Enter its backup password.']})
        kdf = manifest.get('kdf', {})
        try:
            params = {name: int(kdf[name]) for name in ('n', 'r', 'p')}
            if params != SCRYPT:
                raise ValueError
            key = _key(password, base64.b64decode(kdf['salt']), params)
            payload = AESGCM(key).decrypt(base64.b64decode(manifest['nonce']), payload, AAD)
        except (InvalidTag, KeyError, ValueError, TypeError):
            raise ValidationError({'password': ['Wrong backup password, or the file is damaged.']})
    if hashlib.sha256(payload).hexdigest() != manifest.get('sha256'):
        raise ValidationError('The backup file is damaged (checksum mismatch).')
    return manifest, payload


def inspect_database(path):
    """Integrity, compatibility and a summary of what restoring would bring back."""
    known = set(MigrationLoader(None, ignore_no_migrations=True).disk_migrations)
    try:
        with closing(sqlite3.connect(f'file:{path.as_posix()}?mode=ro', uri=True)) as db:
            if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValidationError('The backup database failed its integrity check.')
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not {'django_migrations', 'core_user', 'core_role'} <= tables:
                raise ValidationError('This file does not contain Zakaria ERP data.')
            applied = set(db.execute('SELECT app, name FROM django_migrations').fetchall())
            if applied - known:
                raise ValidationError('This backup was made by a newer version of Zakaria ERP. Install that version first.')

            def scalar(sql):
                try:
                    row = db.execute(sql).fetchone()
                except sqlite3.OperationalError:
                    return None
                return row[0] if row else None
            return {
                'company': scalar('SELECT name FROM core_company WHERE id = 1') or '',
                'active_users': scalar("SELECT COUNT(*) FROM core_user WHERE status = 'active'") or 0,
                'users': scalar('SELECT COUNT(*) FROM core_user') or 0,
                'register_entries': scalar('SELECT COUNT(*) FROM core_registerentry') or 0,
                'latest_entry_date': scalar('SELECT MAX(date) FROM core_registerentry'),
                'attachments': scalar('SELECT COUNT(*) FROM core_registerattachment') or 0,
                'upgrade_required': bool(known - applied),
            }
    except sqlite3.DatabaseError:
        raise ValidationError('The backup database cannot be read.')


def stage_restore(content, password, user):
    for old in staging_dir().glob('*.sqlite3'):
        if time.time() - old.stat().st_mtime > 3600:
            old.unlink(missing_ok=True)
    manifest, database = open_backup(content, password)
    staged = staging_dir() / f'{secrets.token_hex(16)}.sqlite3'
    staged.write_bytes(database)
    try:
        summary = inspect_database(staged)
    except Exception:
        staged.unlink(missing_ok=True)
        raise
    token = signing.dumps({'file': staged.name, 'user': user.pk if user else None, 'sha256': manifest['sha256']}, salt='system-restore')
    backup = {key: manifest.get(key) for key in ('created_at', 'app_version', 'kind', 'encrypted')}
    return {'token': token, 'backup': backup, 'summary': summary}


def apply_restore(token, user, actor_label):
    try:
        claim = signing.loads(token, salt='system-restore', max_age=1800)
    except signing.BadSignature:
        raise ValidationError('The restore preview expired. Choose the backup file again.')
    if claim.get('user') != (user.pk if user else None):
        raise ValidationError('The restore preview belongs to another session.')
    staged = staging_dir() / claim['file']
    if not staged.is_file() or hashlib.sha256(staged.read_bytes()).hexdigest() != claim['sha256']:
        raise ValidationError('The restore preview expired. Choose the backup file again.')
    if not _restore_lock.acquire(blocking=False):
        raise ValidationError('Another restore is in progress.')
    try:
        safety, _ = save_local_backup('pre-restore')
        connection.ensure_connection()
        with closing(sqlite3.connect(staged)) as source:
            source.backup(connection.connection)
        call_command('migrate', interactive=False, verbosity=0)
        AccessSession.objects.all().delete()
        audit(None, 'system.restored', claim['sha256'][:16], restored_by=actor_label, safety_backup=safety.name)
        staged.unlink(missing_ok=True)
        return safety.name
    finally:
        _restore_lock.release()


def list_backups():
    rows = []
    for path in sorted(backups_dir().glob('*' + EXTENSION), reverse=True):
        if not NAME_PATTERN.match(path.name):
            continue
        try:
            with zipfile.ZipFile(path) as archive:
                manifest = read_manifest(archive)
        except (zipfile.BadZipFile, ValidationError):
            continue
        rows.append({'name': path.name, 'size': path.stat().st_size, 'kind': manifest.get('kind'),
                     'created_at': manifest.get('created_at'), 'app_version': manifest.get('app_version'),
                     'encrypted': bool(manifest.get('encrypted'))})
    return rows


def local_backup(name):
    if not NAME_PATTERN.match(str(name)):
        raise NotFound()
    path = backups_dir() / name
    if not path.is_file():
        raise NotFound()
    return path


def download(name, content):
    response = HttpResponse(content, content_type='application/octet-stream')
    response['Content-Disposition'] = content_disposition_header(True, name)
    return response


class DesktopOnly(APIView):
    def initial(self, request, *args, **kwargs):
        if not getattr(settings, 'V2_DESKTOP', False):
            raise NotFound()
        super().initial(request, *args, **kwargs)


class Backups(DesktopOnly):
    def get(self, request, name=None):
        require(request.user, 'system.backup')
        if name:
            path = local_backup(name)
            audit(request.user, 'system.backup_downloaded', name)
            return download(name, path.read_bytes())
        return Response({'backups': list_backups(), 'automatic_keep': AUTOMATIC_KEEP, 'folder': str(backups_dir())})

    def post(self, request):
        require(request.user, 'system.backup')
        password = str(request.data.get('password', ''))
        if password and len(password) < 10:
            raise ValidationError({'password': ['Use at least 10 characters for a backup password.']})
        if password != str(request.data.get('confirm_password', '')):
            raise ValidationError({'confirm_password': ['Passwords do not match.']})
        name, content, _ = build_backup('manual', password)
        audit(request.user, 'system.backup_created', name, encrypted=bool(password), size=len(content))
        return download(name, content)


def uploaded_backup(request):
    if request.data.get('name'):
        return local_backup(request.data['name']).read_bytes()
    upload = request.FILES.get('file')
    if not upload:
        raise ValidationError('Choose a backup file.')
    return upload.read()


class Restore(DesktopOnly):
    def post(self, request, step=None):
        require(request.user, 'system.restore')
        if step == 'apply':
            if not request.user.check_password(str(request.data.get('current_password', ''))):
                raise ValidationError({'current_password': ['Current password is incorrect.']})
            safety = apply_restore(request.data.get('token', ''), request.user, request.user.username)
            return Response({'message': 'Restore complete. Everyone has been signed out; sign in with an account from the backup.', 'safety_backup': safety})
        result = stage_restore(uploaded_backup(request), str(request.data.get('password', '')), request.user)
        audit(request.user, 'system.restore_previewed', result['backup']['created_at'])
        return Response(result)


class SetupRestoreThrottle(AnonRateThrottle):
    scope = 'login'


class SetupRestore(DesktopOnly):
    """Restore into a new installation before any account exists."""
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [SetupRestoreThrottle]

    def post(self, request, step=None):
        if not setup_required():
            raise ValidationError('This installation is already set up. Sign in and use Backup & restore.')
        if step == 'apply':
            safety = apply_restore(request.data.get('token', ''), None, 'first-run setup')
            return Response({'message': 'Restore complete. Sign in with an account from the backup.', 'safety_backup': safety})
        upload = request.FILES.get('file')
        if not upload:
            raise ValidationError('Choose a backup file.')
        return Response(stage_restore(upload.read(), str(request.data.get('password', '')), None))
