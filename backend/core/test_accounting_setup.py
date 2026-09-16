from django.test import TestCase
from rest_framework.test import APIClient
from .models import Account, Company, Project, FinancialYear, Role, User, AuditEvent


class AccountingSetupTests(TestCase):
    def setUp(self):
        Company.objects.create(pk=1)
        self.admin = User.objects.create(username='setup', role=Role.objects.create(name='Setup', permissions=['roles.manage']), status='active')
        self.viewer = User.objects.create(username='viewer', role=Role.objects.create(name='Viewer', permissions=['finance.view']), status='active')
        self.other = User.objects.create(username='other', role=Role.objects.create(name='Other', permissions=[]), status='active')
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def create(self, kind, body):
        return self.client.post(f'/api/accounting/setup/{kind}/', body, format='json')

    def test_access_and_no_implicit_audit_right(self):
        self.assertEqual(self.client.get('/api/accounting/setup/').status_code, 200)
        self.assertEqual(self.client.get('/api/logs/').status_code, 403)
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.get('/api/accounting/setup/').status_code, 200)
        self.assertEqual(self.create('accounts', {'code': '1', 'name': 'Cash', 'kind': 'asset'}).status_code, 403)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get('/api/accounting/setup/').status_code, 403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/accounting/setup/').status_code, 401)

    def test_starter_chart_never_overwrites(self):
        self.assertEqual(self.create('template', {}).status_code, 201)
        count = Account.objects.count()
        self.assertGreater(count, 25)
        self.assertEqual(self.create('template', {}).status_code, 400)
        self.assertEqual(Account.objects.count(), count)
        self.assertTrue(AuditEvent.objects.filter(action='accounting.chart_template_created').exists())

    def test_hierarchy_cycle_classification_and_deactivation(self):
        root = Account.objects.create(code='1', name='Assets', kind='asset', is_group=True)
        child = Account.objects.create(code='11', name='Current assets', kind='asset', is_group=True, parent=root)
        url = f'/api/accounting/setup/accounts/{root.pk}/'
        for body in [{'parent': child.pk}, {'kind': 'expense'}, {'is_group': False}, {'active': False}]:
            self.assertEqual(self.client.patch(url, body, format='json').status_code, 400)
        response = self.create('accounts', {'code': '2', 'name': 'Expense', 'kind': 'expense', 'parent': root.pk})
        self.assertEqual(response.status_code, 400)

    def test_cash_account_must_be_individual_asset(self):
        self.assertEqual(self.create('accounts', {'code': 'x', 'name': 'Invalid cash', 'kind': 'expense', 'is_cash': True}).status_code, 400)
        self.assertEqual(self.create('accounts', {'code': 'x', 'name': 'Cash group', 'kind': 'asset', 'is_cash': True, 'is_group': True}).status_code, 400)

    def test_years_reject_invalid_dates_and_overlap(self):
        self.assertEqual(self.create('years', {'name': 'First', 'start_date': '2026-07-01', 'end_date': '2027-06-30'}).status_code, 201)
        self.assertEqual(self.create('years', {'name': 'Overlap', 'start_date': '2027-06-30', 'end_date': '2028-06-30'}).status_code, 400)
        self.assertEqual(self.create('years', {'name': 'Reverse', 'start_date': '2028-07-01', 'end_date': '2027-06-30'}).status_code, 400)
        self.assertEqual(self.create('years', {'name': 'Next', 'start_date': '2027-07-01', 'end_date': '2028-06-30'}).status_code, 201)
        self.assertEqual(FinancialYear.objects.count(), 2)

    def test_project_dates_optional_but_ordered_and_editable(self):
        response = self.create('projects', {'name': 'Test contract', 'code': 'TEST', 'start_date': None, 'end_date': None})
        self.assertEqual(response.status_code, 201)
        url = f"/api/accounting/setup/projects/{response.data['id']}/"
        self.assertEqual(self.client.patch(url, {'start_date': '2026-09-12', 'end_date': '2026-09-11'}, format='json').status_code, 400)
        self.assertEqual(self.client.patch(url, {'reference': 'Test-only reference'}, format='json').status_code, 200)
        self.assertEqual(Project.objects.get().reference, 'Test-only reference')
        self.assertEqual(self.client.delete(url).status_code, 405)
