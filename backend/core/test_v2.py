from datetime import timedelta
from decimal import Decimal
import hashlib
import uuid
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from .models import (User, Role, Company, AccessSession, PasswordRecovery, RecoveryLimit, RegisterCategory, RegisterSource, RegisterEntry, RegisterRule, AuditEvent)


@override_settings(V2_DESKTOP=True, PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class V2Tests(TestCase):
    def setUp(self):
        self.password = 'Original-secure-phrase-846!'
        self.next_password = 'Replacement-secure-phrase-439!'
        self.maker_role = Role.objects.create(name='Maker', permissions=['register.view','register.create'])
        self.review_role = Role.objects.create(name='Reviewer', permissions=['register.view','register.approve','register.cancel','register.export'])
        self.admin_role = Role.objects.create(name='Access', permissions=['users.manage','users.reset','register.manage'])
        self.maker = User.objects.create_user('maker',password=self.password,role=self.maker_role,status='active')
        self.reviewer = User.objects.create_user('reviewer',password=self.password,role=self.review_role,status='active')
        self.admin = User.objects.create_user('admin',password=self.password,role=self.admin_role,status='active')
        Company.objects.create(pk=1)
        self.category = RegisterCategory.objects.create(code='TEST',name='Test category')
        self.source = RegisterSource.objects.create(name='Test bank',kind='bank')
        RegisterRule.objects.create(pk=1,approver_role=self.review_role)
        self.client = APIClient()
        self.client.force_authenticate(self.maker)

    def payload(self, **extra):
        return {'request_key':str(uuid.uuid4()),'date':'2026-09-12','direction':'payment','category':self.category.pk,'source':self.source.pk,'party':'Test party','amount':'100.10','method':'transfer',**extra}

    def create(self, **extra):
        payload=self.payload(**extra)
        response=self.client.post('/api/register/entries/',payload,format='json')
        self.assertEqual(response.status_code,201,response.data)
        return response.data,payload

    def action(self, row, action, **extra):
        return self.client.post(f"/api/register/entries/{row['id']}/action/",{'action':action,'version':row['version'],**extra},format='json')

    def confirm(self, **extra):
        self.client.force_authenticate(self.maker)
        row,_=self.create(**extra)
        submitted=self.action(row,'submit')
        self.assertEqual(submitted.status_code,200,submitted.data)
        self.client.force_authenticate(self.reviewer)
        confirmed=self.action(submitted.data,'confirm')
        self.assertEqual(confirmed.status_code,200,confirmed.data)
        return confirmed.data

    def test_single_entry_feeds_ledger_and_date_opening_exactly(self):
        self.confirm(direction='receipt',amount='1000.00',date='2026-09-01')
        self.confirm(amount='100.10')
        self.confirm(amount='0.20')
        report=self.client.get('/api/register/ledger/?from=2026-09-12&to=2026-09-12').data
        self.assertEqual(Decimal(report['opening']),Decimal('1000'))
        self.assertEqual(Decimal(report['payments']),Decimal('100.30'))
        self.assertEqual(Decimal(report['closing']),Decimal('899.70'))
        self.assertEqual(len(report['rows']),2)
        self.assertEqual(self.client.get('/api/register/ledger/?from=2026-10-01&to=2026-09-01').status_code,400)

    def test_duplicate_and_conflicting_retry(self):
        row,payload=self.create()
        same=self.client.post('/api/register/entries/',payload,format='json')
        self.assertEqual(same.status_code,200)
        self.assertEqual(same.data['id'],row['id'])
        payload['amount']='200'
        self.assertEqual(self.client.post('/api/register/entries/',payload,format='json').status_code,400)
        self.assertEqual(RegisterEntry.objects.count(),1)

    def test_supporting_documents_are_private_versioned_and_locked_for_approval(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from .models import RegisterAttachment
        row, _ = self.create()
        path = f"/api/register/entries/{row['id']}/attachments/"
        content = b'%PDF-1.4\nTest fixture only\n%%EOF'
        def upload(version):
            return self.client.post(path, {'version':version, 'file':SimpleUploadedFile('bank.pdf', content)}, format='multipart')
        added = upload(row['version'])
        self.assertEqual(added.status_code, 200, added.data)
        self.assertEqual(RegisterAttachment.objects.get().sha256, hashlib.sha256(content).hexdigest())
        item_path = f"{path}{added.data['id']}/"
        self.assertEqual(upload(row['version']).status_code, 400)
        self.assertEqual(upload(added.data['version']).status_code, 400)
        self.assertNotIn('content', self.client.get(path).data['rows'][0])
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get(path).status_code, 403)
        self.assertEqual(self.client.get(item_path).status_code, 403)
        self.client.force_authenticate(self.reviewer)
        download = self.client.get(item_path)
        self.assertEqual(download.content, content)
        self.assertEqual(download['Cache-Control'], 'no-store')
        self.assertIn('attachment;', download['Content-Disposition'])
        self.assertEqual(upload(added.data['version']).status_code, 403)
        self.client.force_authenticate(self.maker)
        row['version'] = added.data['version']
        submitted = self.action(row, 'submit').data
        self.assertEqual(upload(submitted['version']).status_code, 400)
        self.assertEqual(self.client.post(item_path, {'version':submitted['version'], 'reason':'Change'}, format='json').status_code,400)
        self.client.force_authenticate(None)
        self.assertIn(self.client.get(item_path).status_code, [401,403])

    def test_attachment_validation_withdrawal_and_limits(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from .models import RegisterAttachment
        row, _ = self.create()
        path = f"/api/register/entries/{row['id']}/attachments/"
        for name, content in [('bad.exe', b'MZbad'), ('fake.png', b'not png'), ('empty.pdf', b''), ('large.pdf', b'%PDF-' + b'x' * (5 * 1024 * 1024))]:
            result = self.client.post(path, {'version':row['version'], 'file':SimpleUploadedFile(name,content)}, format='multipart')
            self.assertEqual(result.status_code,400)
        self.assertFalse(RegisterAttachment.objects.exists())
        added = self.client.post(path, {'version':row['version'], 'file':SimpleUploadedFile('receipt.png',b'\x89PNG\r\n\x1a\nfixture')}, format='multipart').data
        target = f"{path}{added['id']}/"
        self.assertEqual(self.client.post(target, {'version':added['version'],'reason':''}, format='json').status_code,400)
        removed = self.client.post(target, {'version':added['version'],'reason':'Wrong bank receipt'}, format='json')
        self.assertEqual(removed.status_code,200)
        self.assertEqual(self.client.get(target).status_code,404)
        self.assertEqual(self.client.get(path).data['rows'][0]['withdrawal_reason'],'Wrong bank receipt')
        self.assertTrue(RegisterAttachment.objects.get().content)
        for i in range(9):
            RegisterAttachment.objects.create(entry_id=row['id'],name=f'{i}.pdf',mime='application/pdf',size=6,sha256=str(i),content=b'%PDF-x',uploaded_by=self.maker)
        limit = self.client.post(path, {'version':removed.data['version'], 'file':SimpleUploadedFile('new.pdf',b'%PDF-new')}, format='multipart')
        self.assertEqual(limit.status_code,400)
        with override_settings(V2_DESKTOP=False):
            self.assertEqual(self.client.get(path).status_code,404)

    def test_dashboard_has_actual_permission_scoped_register_totals(self):
        self.confirm(direction='receipt',amount='500.00',date=timezone.localdate().isoformat())
        self.confirm(amount='123.45',date=timezone.localdate().isoformat())
        summary=self.client.get('/api/dashboard/').data['register']
        self.assertEqual(Decimal(summary['net']),Decimal('376.55'))
        self.assertEqual(len(summary['monthly']),6)
        self.assertEqual(Decimal(summary['categories'][0]['amount']),Decimal('123.45'))
        self.client.force_authenticate(self.admin)
        self.assertNotIn('register',self.client.get('/api/dashboard/').data)

    def test_self_approval_wrong_role_and_stale_version_rejected(self):
        row,_=self.create()
        submitted=self.action(row,'submit').data
        self.maker_role.permissions+=['register.approve']
        self.maker_role.save()
        self.assertEqual(self.action(submitted,'confirm').status_code,403)
        self.client.force_authenticate(self.reviewer)
        self.assertEqual(self.action(row,'confirm').status_code,400)
        self.assertEqual(self.action(submitted,'confirm').status_code,200)

    def test_confirmed_cannot_edit_and_cancel_is_traceable(self):
        confirmed=self.confirm()
        self.client.force_authenticate(self.maker)
        self.assertEqual(self.client.put(f"/api/register/entries/{confirmed['id']}/action/",self.payload(version=confirmed['version']),format='json').status_code,400)
        self.client.force_authenticate(self.reviewer)
        self.assertEqual(self.action(confirmed,'cancel').status_code,400)
        self.assertEqual(self.action(confirmed,'cancel',reason='Test correction').status_code,200)
        self.assertEqual(self.client.get('/api/register/ledger/').data['count'],0)
        self.assertEqual(RegisterEntry.objects.get().cancellation_reason,'Test correction')

    def test_draft_edit_and_inactive_master_block(self):
        row,payload=self.create()
        payload.update(amount='150',version=row['version'])
        edited=self.client.put(f"/api/register/entries/{row['id']}/action/",payload,format='json')
        self.assertEqual(edited.status_code,200,edited.data)
        submitted=self.action(edited.data,'submit').data
        self.category.active=False;self.category.save()
        self.client.force_authenticate(self.reviewer)
        self.assertEqual(self.action(submitted,'confirm').status_code,400)

    def test_permissions_and_csv_formula_neutralization(self):
        self.assertEqual(self.client.post('/api/register/masters/categories/',{'code':'X','name':'X'},format='json').status_code,403)
        self.confirm(party='=HYPERLINK("example")')
        exported=self.client.get('/api/register/ledger/?export=csv')
        self.assertEqual(exported.status_code,200)
        self.assertIn("'=HYPERLINK",exported.content.decode('utf-8-sig'))
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/register/ledger/').status_code,401)

    def codes(self):
        self.client.force_authenticate(self.maker)
        response=self.client.post('/api/auth/recovery-codes/',{'current_password':self.password},format='json')
        self.assertEqual(response.status_code,200,response.data)
        return response.data['codes']

    def reset(self,code,**extra):
        self.client.force_authenticate(None)
        return self.client.post('/api/auth/reset-password/',{'username':'maker','code':code,'new_password':self.next_password,**extra},format='json')

    def test_password_recovery_hashed_replay_safe_sessions_revoked(self):
        codes=self.codes()
        self.assertNotIn(codes[0],list(PasswordRecovery.objects.values_list('digest',flat=True)))
        AccessSession.objects.create(user=self.maker,key_hash=hashlib.sha256(b'test-session').hexdigest(),expires_at=timezone.now()+timedelta(hours=1))
        self.assertEqual(self.reset(codes[0]).status_code,200)
        self.maker.refresh_from_db()
        self.assertTrue(self.maker.check_password(self.next_password))
        self.assertEqual(self.maker.role_id,self.maker_role.pk)
        self.assertFalse(AccessSession.objects.filter(user=self.maker).exists())
        self.assertFalse(PasswordRecovery.objects.filter(user=self.maker).exists())
        self.assertEqual(self.reset(codes[0]).status_code,400)
        self.assertFalse(any(codes[0] in str(d) for d in AuditEvent.objects.values_list('details',flat=True)))

    def test_invalid_weak_expired_and_suspended_recovery(self):
        code=self.codes()[0]
        self.assertEqual(self.reset(code,new_password='x').status_code,400)
        self.assertTrue(PasswordRecovery.objects.exists())
        PasswordRecovery.objects.update(expires_at=timezone.now()-timedelta(seconds=1))
        self.assertEqual(self.reset(code).status_code,400)
        PasswordRecovery.objects.update(expires_at=None)
        self.maker.status='suspended';self.maker.save()
        self.assertEqual(self.reset(code).status_code,400)

    def test_persistent_recovery_rate_limit_survives_failed_requests(self):
        for _ in range(10):self.assertEqual(self.reset('wrong').status_code,400)
        self.assertEqual(self.reset('wrong').status_code,429)
        self.assertEqual(RecoveryLimit.objects.get().attempts,10)

    def test_admin_reset_requires_explicit_permission_and_password(self):
        self.assertEqual(self.client.post(f'/api/users/{self.reviewer.pk}/reset-code/',{'current_password':self.password},format='json').status_code,403)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.post(f'/api/users/{self.maker.pk}/reset-code/',{'current_password':'wrong'},format='json').status_code,400)
        issued=self.client.post(f'/api/users/{self.maker.pk}/reset-code/',{'current_password':self.password},format='json')
        self.assertEqual(issued.status_code,200,issued.data)
        self.assertIsNotNone(issued.data['expires_at'])
        self.assertEqual(self.reset(issued.data['codes'][0]).status_code,200)

    @override_settings(V2_DESKTOP=False)
    def test_v2_endpoints_unavailable_in_original_pilot(self):
        self.assertEqual(self.client.get('/api/register/ledger/').status_code,404)
        self.assertEqual(self.reset('any').status_code,404)
