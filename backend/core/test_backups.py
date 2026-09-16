from datetime import date, timedelta
import io
import json
import shutil
import sqlite3
import tempfile
import zipfile
from pathlib import Path
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TransactionTestCase, override_settings
from rest_framework.test import APIClient
from . import backups
from .models import AccessSession, AuditEvent, RegisterCategory, Role, User

PASSWORD = 'Owner-account-phrase-4410!'
BACKUP_PASSWORD = 'Backup-file-phrase-9031!'


class BackupTestCase(TransactionTestCase):
    def setUp(self):
        cache.clear()
        self.data = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.data, ignore_errors=True)
        override = override_settings(V2_DESKTOP=True, DESKTOP_DATA_DIR=self.data, PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
        override.enable()
        self.addCleanup(override.disable)
        self.role = Role.objects.create(name='Administrator', permissions=['system.backup', 'system.restore', 'register.view'])
        self.owner = User.objects.create_user('owner', password=PASSWORD, role=self.role, status='active')
        self.client = APIClient()
        self.client.force_authenticate(self.owner)

    def backup(self, **body):
        response = self.client.post('/api/system/backups/', body, format='json')
        self.assertEqual(response.status_code, 200, getattr(response, 'data', None))
        return response.content

    def upload(self, content, path='/api/system/restore/', **fields):
        return self.client.post(path, {'file': SimpleUploadedFile('data.zerp-backup', content), **fields}, format='multipart')


class BackupTests(BackupTestCase):
    def test_manual_backup_is_complete_and_excludes_sessions(self):
        RegisterCategory.objects.create(code='KEEP', name='Kept category')
        AccessSession.objects.create(user=self.owner, key_hash='x' * 64, expires_at='2030-01-01T00:00:00Z')
        content = self.backup()
        manifest, database = backups.open_backup(content)
        self.assertEqual((manifest['kind'], manifest['encrypted']), ('manual', False))
        copy = self.data / 'check.sqlite3'
        copy.write_bytes(database)
        with sqlite3.connect(copy) as db:
            self.assertEqual(db.execute("SELECT name FROM core_registercategory").fetchall(), [('Kept category',)])
            self.assertEqual(db.execute('SELECT COUNT(*) FROM core_accesssession').fetchone()[0], 0)
        self.assertTrue(AuditEvent.objects.filter(action='system.backup_created').exists())

    def test_encrypted_backup_needs_the_right_password(self):
        content = self.backup(password=BACKUP_PASSWORD, confirm_password=BACKUP_PASSWORD)
        self.assertNotIn(BACKUP_PASSWORD.encode(), content)
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            self.assertNotIn(b'SQLite format 3', archive.read('database.sqlite3.enc'))
        self.assertIn('password', self.upload(content).data)
        self.assertIn('password', self.upload(content, password='Wrong-phrase-000000').data)
        self.assertEqual(self.upload(content, password=BACKUP_PASSWORD).status_code, 200)
        event = AuditEvent.objects.get(action='system.backup_created')
        self.assertNotIn(BACKUP_PASSWORD, json.dumps(event.details))

    def test_backup_password_rules(self):
        short = self.client.post('/api/system/backups/', {'password': 'short', 'confirm_password': 'short'}, format='json')
        mismatch = self.client.post('/api/system/backups/', {'password': BACKUP_PASSWORD, 'confirm_password': 'x'}, format='json')
        self.assertEqual((short.status_code, mismatch.status_code), (400, 400))

    def test_permissions_are_required(self):
        clerk = User.objects.create_user('clerk', password=PASSWORD, role=Role.objects.create(name='Clerk', permissions=['register.view']), status='active')
        self.client.force_authenticate(clerk)
        self.assertEqual(self.client.post('/api/system/backups/', {}, format='json').status_code, 403)
        self.assertEqual(self.client.get('/api/system/backups/').status_code, 403)
        self.assertEqual(self.client.post('/api/system/restore/', {}, format='multipart').status_code, 403)

    @override_settings(V2_DESKTOP=False)
    def test_absent_outside_desktop_mode(self):
        self.assertEqual(self.client.get('/api/system/backups/').status_code, 404)

    def test_rejects_damaged_foreign_and_newer_backups(self):
        content = self.backup()
        self.assertEqual(self.upload(b'not a zip').status_code, 400)
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            manifest = json.loads(archive.read('manifest.json'))
            database = bytearray(archive.read('database.sqlite3'))
        database[5000] ^= 0xFF
        damaged = io.BytesIO()
        with zipfile.ZipFile(damaged, 'w') as archive:
            archive.writestr('manifest.json', json.dumps(manifest))
            archive.writestr('database.sqlite3', bytes(database))
        self.assertIn('damaged', str(self.upload(damaged.getvalue()).data))
        _, clean = backups.open_backup(content)
        newer_file = self.data / 'newer.sqlite3'
        newer_file.write_bytes(clean)
        with sqlite3.connect(newer_file) as db:
            db.execute("INSERT INTO django_migrations (app, name, applied) VALUES ('core', '9999_future', '2030-01-01')")
        newer = newer_file.read_bytes()
        manifest['sha256'] = __import__('hashlib').sha256(newer).hexdigest()
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as archive:
            archive.writestr('manifest.json', json.dumps(manifest))
            archive.writestr('database.sqlite3', newer)
        self.assertIn('newer version', str(self.upload(stream.getvalue()).data))

    def test_restore_replaces_data_signs_everyone_out_and_keeps_safety_copy(self):
        kept = RegisterCategory.objects.create(code='KEEP', name='Kept category')
        content = self.backup(password=BACKUP_PASSWORD, confirm_password=BACKUP_PASSWORD)
        kept.delete()
        RegisterCategory.objects.create(code='LATER', name='Added after backup')
        self.owner.set_password('Changed-after-backup-551!')
        self.owner.save()
        AccessSession.objects.create(user=self.owner, key_hash='y' * 64, expires_at='2030-01-01T00:00:00Z')
        preview = self.upload(content, password=BACKUP_PASSWORD)
        self.assertEqual(preview.status_code, 200, preview.data)
        self.assertEqual(preview.data['summary']['active_users'], 1)
        self.assertFalse(preview.data['summary']['upgrade_required'])
        token = preview.data['token']
        wrong = self.client.post('/api/system/restore/apply/', {'token': token, 'current_password': PASSWORD}, format='json')
        self.assertEqual(wrong.status_code, 400)
        self.assertTrue(RegisterCategory.objects.filter(code='LATER').exists())
        applied = self.client.post('/api/system/restore/apply/', {'token': token, 'current_password': 'Changed-after-backup-551!'}, format='json')
        self.assertEqual(applied.status_code, 200, applied.data)
        self.assertEqual(list(RegisterCategory.objects.values_list('code', flat=True)), ['KEEP'])
        self.assertTrue(User.objects.get(username='owner').check_password(PASSWORD))
        self.assertFalse(AccessSession.objects.exists())
        self.assertTrue(AuditEvent.objects.filter(action='system.restored', details__restored_by='owner').exists())
        safety = self.data / 'backups' / applied.data['safety_backup']
        _, previous = backups.open_backup(safety.read_bytes())
        check = self.data / 'previous.sqlite3'
        check.write_bytes(previous)
        with sqlite3.connect(check) as db:
            self.assertEqual(db.execute('SELECT code FROM core_registercategory').fetchall(), [('LATER',)])
        reused = self.client.post('/api/system/restore/apply/', {'token': token, 'current_password': PASSWORD}, format='json')
        self.assertEqual(reused.status_code, 400)

    def test_restore_preview_is_bound_to_its_user(self):
        preview = self.upload(self.backup())
        other = User.objects.create_user('other', password=PASSWORD, role=self.role, status='active')
        self.client.force_authenticate(other)
        response = self.client.post('/api/system/restore/apply/', {'token': preview.data['token'], 'current_password': PASSWORD}, format='json')
        self.assertIn('another session', str(response.data))

    def test_local_backups_list_download_and_restore_by_name(self):
        path, _ = backups.save_local_backup('auto')
        listing = self.client.get('/api/system/backups/').data['backups']
        self.assertEqual([row['name'] for row in listing], [path.name])
        self.assertEqual(self.client.get(f'/api/system/backups/{path.name}/').content, path.read_bytes())
        self.assertEqual(self.client.get('/api/system/backups/..%5Cregister.sqlite3/').status_code, 404)
        preview = self.client.post('/api/system/restore/', {'name': path.name}, format='json')
        self.assertEqual(preview.status_code, 200, preview.data)

    def test_automatic_backups_one_per_day_keep_newest_seven(self):
        start = date(2026, 9, 1)
        self.owner.status = 'pending'
        self.owner.save()
        self.assertIsNone(backups.automatic_backup_if_due(start))
        self.owner.status = 'active'
        self.owner.save()
        self.assertIsNotNone(backups.automatic_backup_if_due(start))
        self.assertIsNone(backups.automatic_backup_if_due(start))
        for offset in range(1, 10):
            self.assertIsNotNone(backups.automatic_backup_if_due(start + timedelta(days=offset)))
        names = sorted(p.name for p in (self.data / 'backups').glob('auto-*'))
        self.assertEqual(len(names), 7)
        self.assertTrue(names[-1].startswith('auto-20260910-'))


class SetupRestoreTests(BackupTestCase):
    def test_new_installation_can_restore_before_setup(self):
        content = self.backup()
        self.owner.status = 'pending'
        self.owner.save()
        client = APIClient()
        preview = client.post('/api/setup/restore/', {'file': SimpleUploadedFile('d.zerp-backup', content)}, format='multipart')
        self.assertEqual(preview.status_code, 200, preview.data)
        applied = client.post('/api/setup/restore/apply/', {'token': preview.data['token']}, format='json')
        self.assertEqual(applied.status_code, 200, applied.data)
        self.assertEqual(User.objects.get(username='owner').status, 'active')
        self.assertEqual(client.get('/api/setup/').data, {'required': False})

    def test_setup_restore_closes_once_an_account_is_active(self):
        content = self.backup()
        response = APIClient().post('/api/setup/restore/', {'file': SimpleUploadedFile('d.zerp-backup', content)}, format='multipart')
        self.assertEqual(response.status_code, 400)
        self.assertIn('already set up', str(response.data))
