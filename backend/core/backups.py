"""Full data backup and restore for the desktop installation.

Supporting documents are database blobs, so one SQLite snapshot is a complete
backup. A .zerp-backup file is a zip holding the database and manifest.json,
optionally encrypted with AES-256-GCM using a scrypt-derived key. Passwords are
never stored or logged; a forgotten password makes that backup unreadable.

Backups stream through files on disk, so their size is limited by free disk
space rather than memory. Format 2 encrypts in authenticated chunks: each
chunk's number and a final-chunk flag are bound into its tag, so reordering,
dropping or truncating chunks fails decryption. Format 1 backups (2.1.0.5 to
2.1.0.8, whole-message encryption) remain restorable.

Restore replaces every record, account and password with the backup's, after
saving an unencrypted safety copy of the current data. All sessions end.
"""
import base64
from contextlib import closing
from datetime import date, datetime
import hashlib
import io
import json
import os
import re
import secrets
import shutil
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
from django.http import FileResponse
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from .auth import audit, require
from .first_run import setup_required
from .models import AccessSession

FORMAT = 'zakaria-erp-backup'
FORMAT_VERSION = 2
EXTENSION = '.zerp-backup'
AUTOMATIC_KEEP = 7
CHUNK = 4 * 1024 * 1024
COPY_BUFFER = 1024 * 1024
TAG = 16
SCRYPT = {'n': 2 ** 15, 'r': 8, 'p': 1}
AAD_V1 = b'zakaria-erp-backup-v1'
AAD_V2 = b'zakaria-erp-backup-v2'
DATABASE, ENCRYPTED = 'database.sqlite3', 'database.sqlite3.enc'
# Previews expire after 30 minutes; anything left longer was abandoned.
STALE = 3600
UPLOAD_PATTERN = re.compile(r'^upload-[0-9a-f]{32}\.zerp-backup$')
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


def clean_leftovers(older_than=None):
    """Remove files an interrupted backup or restore left behind.

    Covers spooled restore uploads and staged databases in restore-staging, and
    unfinished snapshots and copies in backups. With `older_than` (seconds),
    only files untouched for that long go; files still open are skipped.
    Returns the number of bytes freed.
    """
    candidates = [*staging_dir().iterdir(), *backups_dir().glob('*.snapshot'), *backups_dir().glob('*.partial')]
    freed = 0
    for path in candidates:
        try:
            info = path.stat()
            if not path.is_file() or (older_than is not None and time.time() - info.st_mtime < older_than):
                continue
            path.unlink()
            freed += info.st_size
        except OSError:
            continue  # In use (for example an upload being received) or already gone.
    return freed


def ensure_space(folder, needed):
    """Refuse early, with a readable message, when the disk cannot hold the work."""
    free = shutil.disk_usage(folder).free
    required = int(needed * 1.1) + 50 * 1024 * 1024
    if free < required:
        raise ValidationError(f'Not enough free disk space: about {required // (1024 * 1024)} MB is needed, '
                              f'{free // (1024 * 1024)} MB is free on the data drive.')


def _key(password, salt, params):
    return Scrypt(salt=salt, length=32, **params).derive(password.encode('utf-8'))


def _chunk_nonce_aad(prefix, index, final):
    counter = index.to_bytes(4, 'big')
    return prefix + counter, AAD_V2 + counter + (b'\x01' if final else b'\x00')


def _chunks(size):
    return max(1, -(-size // CHUNK))


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as source:
        while block := source.read(COPY_BUFFER):
            digest.update(block)
    return digest.hexdigest()


def snapshot_to(path):
    """Consistent copy of the live database, without sign-in sessions."""
    connection.ensure_connection()
    with closing(sqlite3.connect(path)) as copy:
        connection.connection.backup(copy)
        copy.execute('DELETE FROM core_accesssession')
        copy.commit()
        if copy.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValidationError('The database failed its integrity check; no backup was written.')


def write_backup(kind, target, password=''):
    """Write a complete backup zip to the writable binary file `target`."""
    live = Path(settings.DATABASES['default']['NAME'])
    estimate = live.stat().st_size if live.is_file() else 0
    ensure_space(backups_dir(), estimate * 2)
    handle, snapshot = tempfile.mkstemp(suffix='.snapshot', dir=backups_dir())
    os.close(handle)
    try:
        snapshot_to(snapshot)
        size = os.path.getsize(snapshot)
        manifest = {'format': FORMAT, 'format_version': FORMAT_VERSION, 'app_version': app_version(), 'kind': kind,
                    'created_at': datetime.now().astimezone().isoformat(timespec='seconds'),
                    'size': size, 'encrypted': bool(password)}
        digest = hashlib.sha256()
        stamp = datetime.now().timetuple()[:6]
        with zipfile.ZipFile(target, 'w') as archive:
            if password:
                salt, prefix = secrets.token_bytes(16), secrets.token_bytes(8)
                manifest['kdf'] = {'name': 'scrypt', **SCRYPT, 'salt': base64.b64encode(salt).decode()}
                manifest['cipher'] = {'name': 'aes-256-gcm-chunked', 'chunk': CHUNK, 'nonce_prefix': base64.b64encode(prefix).decode()}
                cipher = AESGCM(_key(password, salt, SCRYPT))
                info = zipfile.ZipInfo(ENCRYPTED, stamp)
                info.compress_type = zipfile.ZIP_STORED
                with open(snapshot, 'rb') as source, archive.open(info, 'w', force_zip64=True) as sink:
                    count = _chunks(size)
                    for index in range(count):
                        block = source.read(CHUNK)
                        digest.update(block)
                        nonce, aad = _chunk_nonce_aad(prefix, index, index == count - 1)
                        sink.write(cipher.encrypt(nonce, block, aad))
            else:
                info = zipfile.ZipInfo(DATABASE, stamp)
                info.compress_type = zipfile.ZIP_DEFLATED
                with open(snapshot, 'rb') as source, archive.open(info, 'w', force_zip64=True) as sink:
                    while block := source.read(COPY_BUFFER):
                        digest.update(block)
                        sink.write(block)
            manifest['sha256'] = digest.hexdigest()
            archive.writestr(zipfile.ZipInfo('manifest.json', stamp), json.dumps(manifest, indent=2))
    finally:
        Path(snapshot).unlink(missing_ok=True)
    return manifest


def backup_name(kind, when=None):
    return f"{kind}-{(when or datetime.now()).strftime('%Y%m%d-%H%M%S')}{EXTENSION}"


def build_backup(kind, password='', when=None):
    """Backup as bytes (small databases and tests); prefer write_backup."""
    stream = io.BytesIO()
    manifest = write_backup(kind, stream, password)
    return backup_name(kind, when), stream.getvalue(), manifest


def save_local_backup(kind, when=None):
    target = backups_dir() / backup_name(kind, when)
    if target.exists():
        target = target.with_name(target.name.replace(EXTENSION, f'-{secrets.randbelow(10 ** 6)}{EXTENSION}'))
    temporary = target.with_suffix('.partial')
    try:
        with open(temporary, 'wb') as sink:
            manifest = write_backup(kind, sink)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
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
    if manifest.get('format') != FORMAT or manifest.get('format_version') not in (1, 2):
        raise ValidationError('This backup format is not supported by this version.')
    return manifest


def _wrong_password():
    return ValidationError({'password': ['Wrong backup password, or the file is damaged.']})


def _key_for(manifest, password):
    if not password:
        raise ValidationError({'password': ['This backup is password-protected. Enter its backup password.']})
    kdf = manifest.get('kdf', {})
    try:
        params = {name: int(kdf[name]) for name in ('n', 'r', 'p')}
        if params != SCRYPT:
            raise ValueError
        return _key(password, base64.b64decode(kdf['salt']), params)
    except (KeyError, ValueError, TypeError):
        raise _wrong_password()


def extract_backup(source, password, target):
    """Validate a backup (path or seekable file) and write its database to `target`.

    Streams in bounded chunks and verifies the SHA-256 of the result. Returns the manifest.
    """
    try:
        archive = zipfile.ZipFile(source)
    except (zipfile.BadZipFile, OSError):
        raise ValidationError('This is not a Zakaria ERP backup file.')
    with archive:
        manifest = read_manifest(archive)
        encrypted = bool(manifest.get('encrypted'))
        try:
            info = archive.getinfo(ENCRYPTED if encrypted else DATABASE)
        except KeyError:
            raise ValidationError('The backup file is incomplete.')
        ensure_space(Path(target).parent, int(manifest.get('size') or info.file_size))
        digest = hashlib.sha256()
        with archive.open(info) as payload, open(target, 'wb') as sink:
            if not encrypted:
                while block := payload.read(COPY_BUFFER):
                    digest.update(block)
                    sink.write(block)
            elif manifest['format_version'] == 1:
                # Whole-message format from 2.1.0.5-2.1.0.8; such backups were built in memory.
                key = _key_for(manifest, password)
                try:
                    block = AESGCM(key).decrypt(base64.b64decode(manifest['nonce']), payload.read(), AAD_V1)
                except (InvalidTag, KeyError, ValueError, TypeError):
                    raise _wrong_password()
                digest.update(block)
                sink.write(block)
            else:
                key = _key_for(manifest, password)
                try:
                    cipher = manifest['cipher']
                    prefix, chunk, size = base64.b64decode(cipher['nonce_prefix']), int(cipher['chunk']), int(manifest['size'])
                    if cipher.get('name') != 'aes-256-gcm-chunked' or len(prefix) != 8 or not 0 < chunk <= 64 * 1024 * 1024 or size < 0:
                        raise ValueError
                except (KeyError, ValueError, TypeError):
                    raise ValidationError('The backup file is damaged (invalid encryption header).')
                aes, count, remaining = AESGCM(key), max(1, -(-size // chunk)), size
                for index in range(count):
                    length = min(chunk, remaining)
                    sealed = payload.read(length + TAG)
                    nonce, aad = _chunk_nonce_aad(prefix, index, index == count - 1)
                    try:
                        block = aes.decrypt(nonce, sealed, aad)
                    except InvalidTag:
                        raise _wrong_password()
                    remaining -= len(block)
                    digest.update(block)
                    sink.write(block)
                if remaining or payload.read(1):
                    raise ValidationError('The backup file is damaged (unexpected length).')
    if digest.hexdigest() != manifest.get('sha256'):
        raise ValidationError('The backup file is damaged (checksum mismatch).')
    return manifest


def open_backup(content, password=''):
    """Validate backup bytes and return (manifest, database bytes). For small files and tests."""
    handle, path = tempfile.mkstemp(suffix='.sqlite3', dir=staging_dir())
    os.close(handle)
    try:
        manifest = extract_backup(io.BytesIO(content), password, path)
        return manifest, Path(path).read_bytes()
    finally:
        Path(path).unlink(missing_ok=True)


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


def stage_restore(source, password, user):
    """Extract and check a backup (path or seekable file); return a preview and signed token."""
    clean_leftovers(older_than=STALE)
    staged = staging_dir() / f'{secrets.token_hex(16)}.sqlite3'
    try:
        manifest = extract_backup(source, password, staged)
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
    if not staged.is_file() or file_sha256(staged) != claim['sha256']:
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


def download(name, stream):
    """Stream an open binary file to the client; FileResponse closes it afterwards."""
    return FileResponse(stream, as_attachment=True, filename=name, content_type='application/octet-stream')


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
            return download(name, open(path, 'rb'))
        return Response({'backups': list_backups(), 'automatic_keep': AUTOMATIC_KEEP, 'folder': str(backups_dir())})

    def post(self, request):
        require(request.user, 'system.backup')
        password = str(request.data.get('password', ''))
        if password and len(password) < 10:
            raise ValidationError({'password': ['Use at least 10 characters for a backup password.']})
        if password != str(request.data.get('confirm_password', '')):
            raise ValidationError({'confirm_password': ['Passwords do not match.']})
        # Deleted automatically when the response finishes streaming.
        stream = tempfile.TemporaryFile(dir=backups_dir())
        try:
            write_backup('manual', stream, password)
            size = stream.tell()
            stream.seek(0)
        except Exception:
            stream.close()
            raise
        name = backup_name('manual')
        audit(request.user, 'system.backup_created', name, encrypted=bool(password), size=size)
        return download(name, stream)


def keep_upload(upload, user):
    """Copy an uploaded backup into staging so a password attempt need not re-send it."""
    ensure_space(staging_dir(), upload.size or 0)
    path = staging_dir() / f'upload-{secrets.token_hex(16)}{EXTENSION}'
    upload.seek(0)
    with open(path, 'wb') as sink:
        shutil.copyfileobj(upload, sink, COPY_BUFFER)
    claim = signing.dumps({'file': path.name, 'user': user.pk if user else None}, salt='restore-upload')
    return path, claim


def kept_upload(token, user):
    try:
        claim = signing.loads(token, salt='restore-upload', max_age=STALE)
    except signing.BadSignature:
        raise ValidationError('The backup file is no longer on this computer. Choose it again.')
    if claim.get('user') != (user.pk if user else None) or not UPLOAD_PATTERN.match(claim['file']):
        raise ValidationError('The backup file belongs to another session. Choose it again.')
    path = staging_dir() / claim['file']
    if not path.is_file():
        raise ValidationError('The backup file is no longer on this computer. Choose it again.')
    return path


def _needs_password(error):
    detail = getattr(error, 'detail', None)
    return isinstance(detail, dict) and 'password' in detail


def restore_preview(request, user, allow_local):
    """Stage a restore from a local copy, a kept upload, or a newly uploaded file.

    An uploaded file is kept while the password is asked for, so a password-protected
    backup is sent once instead of twice; it is removed as soon as staging ends.
    """
    if allow_local and request.data.get('name'):
        return stage_restore(local_backup(request.data['name']), str(request.data.get('password', '')), user)
    if request.data.get('upload'):
        claim = str(request.data['upload'])
        source = kept_upload(claim, user)
    else:
        upload = request.FILES.get('file')
        if not upload:
            raise ValidationError('Choose a backup file.')
        source, claim = keep_upload(upload, user)
    remove = source
    try:
        return stage_restore(source, str(request.data.get('password', '')), user)
    except ValidationError as error:
        if _needs_password(error):
            # Keep the file so the password attempt reuses it instead of uploading again.
            error.detail['upload'] = claim
            remove = None
        raise
    finally:
        if remove is not None:
            remove.unlink(missing_ok=True)


class Restore(DesktopOnly):
    def post(self, request, step=None):
        require(request.user, 'system.restore')
        if step == 'apply':
            if not request.user.check_password(str(request.data.get('current_password', ''))):
                raise ValidationError({'current_password': ['Current password is incorrect.']})
            safety = apply_restore(request.data.get('token', ''), request.user, request.user.username)
            return Response({'message': 'Restore complete. Everyone has been signed out; sign in with an account from the backup.', 'safety_backup': safety})
        result = restore_preview(request, request.user, allow_local=True)
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
        return Response(restore_preview(request, None, allow_local=False))
