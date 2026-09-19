import uuid
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from .models import AuditEvent, Company, RegisterAttachment, RegisterRule, RegisterSource, Role, User

PNG = b'\x89PNG\r\n\x1a\nstatement'
PDF = b'%PDF-1.4 opening statement'


@override_settings(V2_DESKTOP=True, PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class PositionTestBase(TestCase):
    def setUp(self):
        maker_role = Role.objects.create(name='Maker', permissions=['register.view', 'register.create'])
        self.review_role = Role.objects.create(name='Reviewer', permissions=['register.view', 'register.approve'])
        self.maker = User.objects.create_user('maker', password='Maker-phrase-83120!', role=maker_role, status='active')
        self.other = User.objects.create_user('other', password='Other-phrase-83120!', role=maker_role, status='active')
        self.reviewer = User.objects.create_user('reviewer', password='Review-phrase-8312!', role=self.review_role, status='active')
        Company.objects.create(pk=1)
        RegisterRule.objects.create(pk=1, approver_role=self.review_role)
        self.cash = RegisterSource.objects.create(name='Test cash', kind='cash')
        self.bank = RegisterSource.objects.create(name='Test bank', kind='bank')
        self.client = APIClient()
        self.client.force_authenticate(self.maker)

    def position(self, **extra):
        payload = {'request_key': str(uuid.uuid4()), 'kind': 'transfer', 'date': '2026-09-10', 'amount': '2500.00',
                   'source': self.cash.pk, 'destination': self.bank.pk, 'reference': 'TEST-TRF-1', 'remarks': 'Test transfer', **extra}
        response = self.client.post('/api/register/positions/', payload, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def upload(self, row, name='statement.png', content=PNG, version=None):
        path = f"/api/register/positions/{row['id']}/attachments/"
        return self.client.post(path, {'version': row['version'] if version is None else version, 'file': SimpleUploadedFile(name, content)}, format='multipart')


@override_settings(V2_DESKTOP=True, PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class PositionEvidenceTests(PositionTestBase):
    def test_transfer_draft_documents_can_be_added_viewed_and_withdrawn(self):
        row = self.position()
        added = self.upload(row)
        self.assertEqual(added.status_code, 200, added.data)
        path = f"/api/register/positions/{row['id']}/attachments/"
        listing = self.client.get(path).data
        self.assertEqual((listing['status'], listing['version'], len(listing['rows'])), ('draft', row['version'] + 1, 1))
        download = self.client.get(f"{path}{added.data['id']}/")
        self.assertEqual((download.content, download['Content-Type'], download['Cache-Control']), (PNG, 'image/png', 'no-store'))
        item = RegisterAttachment.objects.get()
        self.assertEqual((item.entry_id, item.position_id), (None, row['id']))
        withdrawn = self.client.post(f"{path}{added.data['id']}/", {'version': added.data['version'], 'reason': 'Wrong statement page'}, format='json')
        self.assertEqual(withdrawn.status_code, 200)
        self.assertEqual(self.client.get(f"{path}{added.data['id']}/").status_code, 404)
        self.assertEqual(self.client.get(path).data['rows'][0]['withdrawal_reason'], 'Wrong statement page')
        events = AuditEvent.objects.filter(action__startswith='register.evidence_').values_list('action', 'details')
        self.assertTrue(all(details['kind'] == 'transfer' and details['position'] == row['id'] for _, details in events))

    def test_opening_accepts_pdf_and_rejects_forged_or_stale_uploads(self):
        row = self.position(kind='opening', source=self.bank.pk, destination=None, side='receipt')
        self.assertEqual(self.upload(row, 'balance.pdf', PDF).status_code, 200)
        self.assertEqual(self.upload(row, 'fake.png', b'not an image', version=row['version'] + 1).status_code, 400)
        self.assertEqual(self.upload(row, 'balance.pdf', PDF).status_code, 400)  # stale version
        self.assertEqual(self.upload(row, 'balance.pdf', PDF, version=row['version'] + 1).status_code, 400)  # duplicate

    def test_only_preparer_changes_documents_and_only_while_draft(self):
        row = self.position()
        self.client.force_authenticate(self.other)
        self.assertEqual(self.upload(row).status_code, 400)
        self.client.force_authenticate(self.maker)
        submitted = self.client.post(f"/api/register/positions/{row['id']}/", {'action': 'submit', 'version': row['version']}, format='json').data
        self.assertEqual(submitted['status'], 'submitted')
        locked = self.upload(submitted)
        self.assertEqual(locked.status_code, 400)
        self.assertIn('current draft', str(locked.data))
        self.client.force_authenticate(self.reviewer)
        self.assertEqual(self.client.get(f"/api/register/positions/{row['id']}/attachments/").status_code, 200)
        self.assertFalse(RegisterAttachment.objects.exists())

    def test_documents_stay_with_their_own_record(self):
        first, second = self.position(), self.position(reference='TEST-TRF-2')
        added = self.upload(first).data
        self.assertEqual(self.client.get(f"/api/register/positions/{second['id']}/attachments/{added['id']}/").status_code, 404)
        self.assertEqual(self.client.get(f"/api/register/entries/{first['id']}/attachments/{added['id']}/").status_code, 404)

    def test_database_requires_exactly_one_linked_record(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            RegisterAttachment.objects.create(name='orphan.pdf', mime='application/pdf', size=6, sha256='x', content=PDF, uploaded_by=self.maker)

    @override_settings(V2_DESKTOP=False)
    def test_absent_outside_desktop_mode(self):
        self.assertEqual(self.client.get('/api/register/positions/1/attachments/').status_code, 404)


@override_settings(V2_DESKTOP=True, PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class DocumentCountTests(PositionTestBase):
    """Active supporting-document counts for openings and transfers."""

    def test_counts_exclude_withdrawn_documents_everywhere(self):
        row = self.position()
        first = self.upload(row).data
        second = self.upload(row, 'second.pdf', PDF, version=first['version']).data
        path = f"/api/register/positions/{row['id']}/attachments/{first['id']}/"
        self.client.post(path, {'version': second['version'], 'reason': 'Duplicate page'}, format='json')
        listed = next(r for r in self.client.get('/api/register/positions/').data if r['id'] == row['id'])
        self.assertEqual(listed['documents'], 1)
        self.maker.role.permissions += ['register.delete']
        self.maker.role.save()
        data = self.client.get('/api/register/data-management/?kind=positions').data['rows']
        self.assertEqual(next(r for r in data if r['id'] == row['id'])['documents'], 1)
        current = self.client.get(f"/api/register/positions/{row['id']}/attachments/").data['version']
        submitted = self.client.post(f"/api/register/positions/{row['id']}/", {'action': 'submit', 'version': current}, format='json').data
        self.client.force_authenticate(self.reviewer)
        self.reviewer.role.permissions += ['register.export']
        self.reviewer.role.save()
        confirmed = self.client.post(f"/api/register/positions/{row['id']}/", {'action': 'confirm', 'version': submitted['version']}, format='json')
        self.assertEqual(confirmed.status_code, 200, confirmed.data)
        report = self.client.post('/api/register/reports/', {'columns': ['reference', 'evidence']}, format='json')
        self.assertEqual(report.status_code, 200, report.data)
        rows = [r for r in report.data['rows'] if r['reference'] == f"TRF-{row['id']:06d}"]
        self.assertTrue(rows)
        self.assertEqual({r['evidence'] for r in rows}, {1})
