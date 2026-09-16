from decimal import Decimal
from django.test import TestCase, override_settings
from django.core.cache import cache
from rest_framework.test import APIClient
from .models import Company, Role, User, Party, Workflow, Document, AuditEvent
from .auth import PERMISSIONS

@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class WorkflowTests(TestCase):
    def setUp(self):
        cache.clear()
        self.company = Company.objects.create(pk=1, address='Verified test address')
        self.admin_role = Role.objects.create(name='Admin', permissions=[p for p in PERMISSIONS if not p.startswith('logs.')])
        self.finance_role = Role.objects.create(name='Finance', permissions=['parties.view', 'parties.edit', 'quotation.view', 'quotation.create', 'quotation.issue', 'invoice.view', 'invoice.create', 'invoice.issue', 'reports.view', 'reports.export'])
        self.gm_role = Role.objects.create(name='GM', permissions=['quotation.view', 'quotation.approve', 'invoice.view', 'invoice.approve'])
        self.audit_role = Role.objects.create(name='Audit', permissions=['logs.view'])
        self.admin = self.user('admin', self.admin_role)
        self.finance = self.user('finance', self.finance_role)
        self.gm = self.user('gm', self.gm_role)
        self.reviewer = self.user('reviewer', self.audit_role)
        self.party = Party.objects.create(name='Test customer', kind='customer')
        for kind in ['quotation', 'invoice']:
            Workflow.objects.create(kind=kind, approver_role=self.gm_role)
        self.client = APIClient()
        self.client.force_authenticate(self.finance)

    def user(self, name, role, **kwargs):
        return User.objects.create_user(username=name, password='A-safe-test-passphrase-482!', role=role, status='active', **kwargs)

    def payload(self, **kwargs):
        return {'kind': 'quotation', 'party': self.party.id, 'issue_date': '2026-09-06', 'tax_treatment': 'exclusive', 'lines': [{'description': 'Test line', 'unit': 'Each', 'quantity': '3', 'rate': '100.10', 'tax_rate': '5'}], **kwargs}

    def create(self, **kwargs):
        response = self.client.post('/api/documents/', self.payload(**kwargs), format='json')
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def action(self, document, action, comment=''):
        return self.client.post(f"/api/documents/{document['id']}/action/", {'action': action, 'version': document['version'], 'comment': comment}, format='json')

    def test_decimal_totals_and_server_ignores_forged_total(self):
        doc = self.create(total='0.01')
        self.assertEqual(Decimal(doc['subtotal']), Decimal('300.30'))
        self.assertEqual(Decimal(doc['tax_total']), Decimal('15.02'))
        self.assertEqual(Decimal(doc['total']), Decimal('315.32'))

    def test_approval_then_issue_preserves_identity(self):
        doc = self.create()
        self.assertEqual(self.action(doc, 'issue').status_code, 400)
        submitted = self.action(doc, 'submit').data
        self.client.force_authenticate(self.gm)
        approved = self.action(submitted, 'approve')
        self.assertEqual(approved.status_code, 200, approved.data)
        self.client.force_authenticate(self.finance)
        issued = self.action(approved.data, 'issue')
        self.assertEqual(issued.status_code, 200, issued.data)
        self.party.name = 'Changed later'
        self.party.save()
        stored = Document.objects.get(pk=doc['id'])
        self.assertEqual(stored.issued_snapshot['party']['name'], 'Test customer')
        edit = self.client.put(f"/api/documents/{doc['id']}/", self.payload(version=issued.data['version']), format='json')
        self.assertEqual(edit.status_code, 400)

    def test_self_approval_blocked_even_with_approval_permission(self):
        self.finance_role.permissions += ['quotation.approve']
        self.finance_role.save()
        Workflow.objects.filter(kind='quotation').update(approver_role=self.finance_role)
        submitted = self.action(self.create(), 'submit').data
        self.assertEqual(self.action(submitted, 'approve').status_code, 403)

    def test_workflow_change_does_not_reassign_existing_submission(self):
        submitted = self.action(self.create(), 'submit').data
        Workflow.objects.filter(kind='quotation').update(approver_role=self.admin_role, version=2)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.action(submitted, 'approve').status_code, 403)
        self.client.force_authenticate(self.gm)
        self.assertEqual(self.action(submitted, 'approve').status_code, 200)

    def test_stale_action_cannot_duplicate_transition(self):
        doc = self.create()
        self.assertEqual(self.action(doc, 'submit').status_code, 200)
        self.assertEqual(self.action(doc, 'submit').status_code, 400)

    def test_return_requires_comment_and_allows_revision(self):
        submitted = self.action(self.create(), 'submit').data
        self.client.force_authenticate(self.gm)
        self.assertEqual(self.action(submitted, 'return').status_code, 400)
        returned = self.action(submitted, 'return', 'Please update scope').data
        self.assertEqual(returned['feedback'], 'Please update scope')
        self.client.force_authenticate(self.finance)
        updated = self.client.put(f"/api/documents/{returned['id']}/", self.payload(version=returned['version'], notes='Updated scope'), format='json')
        self.assertEqual(updated.status_code, 200, updated.data)
        self.assertEqual(self.action(updated.data, 'submit').status_code, 200)

    def test_tax_treatment_required_for_submission(self):
        doc = self.create(tax_treatment='unspecified', lines=[{'description': 'Untaxed test', 'quantity': '1', 'rate': '10', 'tax_rate': '0'}])
        self.assertEqual(self.action(doc, 'submit').status_code, 400)

    def test_no_log_access_for_admin_or_superuser_without_permission(self):
        self.admin.is_superuser = True
        self.admin.save()
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get('/api/logs/').status_code, 403)
        self.client.force_authenticate(self.reviewer)
        self.assertEqual(self.client.get('/api/logs/').status_code, 200)
        self.assertEqual(self.client.get('/api/logs/?export=csv').status_code, 403)
        self.assertEqual(self.client.post('/api/logs/', {}, format='json').status_code, 405)

    def test_report_requires_underlying_document_permission(self):
        self.audit_role.permissions += ['reports.view', 'reports.export']
        self.audit_role.save()
        self.client.force_authenticate(self.reviewer)
        self.assertEqual(self.client.post('/api/reports/', {'kind': 'quotation'}, format='json').status_code, 403)

    def test_report_uses_document_grain_and_rejects_unknown_fields(self):
        self.create(lines=[{'description': 'A', 'quantity': '1', 'rate': '10'}, {'description': 'B', 'quantity': '1', 'rate': '20'}])
        result = self.client.post('/api/reports/', {'kind': 'quotation', 'columns': ['number', 'total']}, format='json')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data['count'], 1)
        self.assertEqual(result.data['total'], Decimal('30'))
        bad = self.client.post('/api/reports/', {'columns': ['password']}, format='json')
        self.assertEqual(bad.status_code, 400)

    def test_pdf_and_excel_exports(self):
        doc = self.create()
        pdf = self.client.get(f"/api/documents/{doc['id']}/pdf/")
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.content.startswith(b'%PDF'))
        for output in ['pdf', 'xlsx', 'csv']:
            result = self.client.post('/api/reports/', {'format': output, 'paper': 'A3', 'orientation': 'landscape'}, format='json')
            self.assertEqual(result.status_code, 200)

    def test_invoice_live_issuance_blocked_in_pilot(self):
        doc = self.create(kind='invoice')
        submitted = self.action(doc, 'submit').data
        self.client.force_authenticate(self.gm)
        approved = self.action(submitted, 'approve').data
        self.client.force_authenticate(self.finance)
        self.assertEqual(self.action(approved, 'issue').status_code, 400)

    def test_pending_registration_cannot_login_or_choose_role(self):
        client = APIClient()
        response = client.post('/api/auth/register/', {'username': 'newuser', 'email': 'person@example.com', 'password': 'Different-safe-passphrase-483!', 'status': 'active', 'role': self.admin_role.id}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        user = User.objects.get(username='newuser')
        self.assertEqual(user.status, 'pending')
        self.assertIsNone(user.role_id)
        self.assertNotEqual(user.password, 'Different-safe-passphrase-483!')
        self.assertEqual(client.post('/api/auth/login/', {'username': 'newuser', 'password': 'Different-safe-passphrase-483!'}, format='json').status_code, 403)

    def test_password_change_revokes_sessions(self):
        client = APIClient()
        login = client.post('/api/auth/login/', {'username': 'finance', 'password': 'A-safe-test-passphrase-482!'}, format='json')
        client.credentials(HTTP_AUTHORIZATION='Bearer ' + login.data['token'])
        self.assertEqual(client.get('/api/profile/').status_code, 200)
        result = client.post('/api/auth/password/', {'current_password': 'A-safe-test-passphrase-482!', 'new_password': 'Another-unique-passphrase-183!'}, format='json')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(client.get('/api/profile/').status_code, 401)
        self.assertFalse(AuditEvent.objects.filter(details__icontains='passphrase').exists())

    def test_role_changes_apply_to_existing_session(self):
        client = APIClient()
        login = client.post('/api/auth/login/', {'username': 'finance', 'password': 'A-safe-test-passphrase-482!'}, format='json')
        client.credentials(HTTP_AUTHORIZATION='Bearer ' + login.data['token'])
        self.assertEqual(client.get('/api/parties/').status_code, 200)
        self.finance_role.permissions = []
        self.finance_role.save()
        self.assertEqual(client.get('/api/parties/').status_code, 403)

    def test_unauthorized_cannot_edit_users_roles_or_company(self):
        for endpoint in ['/api/users/1/', '/api/roles/1/', '/api/company/']:
            self.assertEqual(self.client.patch(endpoint, {'name': 'Changed'}, format='json').status_code, 403)
