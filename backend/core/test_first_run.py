from io import StringIO
from unittest.mock import patch
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from .models import AuditEvent, Company, RegisterRule, Role, User, Workflow

PASSWORD = 'First-install-phrase-5821!'


def payload(**extra):
    return {'username': 'Owner', 'email': 'owner@example.com', 'first_name': 'Test', 'password': PASSWORD, 'confirm_password': PASSWORD, **extra}


@override_settings(V2_DESKTOP=True, PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class FirstRunSetupTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_fresh_install_creates_administrator_roles_and_register_workflow(self):
        self.assertEqual(self.client.get('/api/setup/').data, {'required': True})
        response = self.client.post('/api/setup/', payload(), format='json')
        self.assertEqual(response.status_code, 201, response.data)
        user = User.objects.get(username='owner')
        self.assertEqual((user.status, user.role.name), ('active', 'Administrator'))
        self.assertTrue(user.check_password(PASSWORD))
        self.assertNotIn('logs.view', user.role.permissions)
        finance = Role.objects.get(name='Finance Manager').permissions
        manager = Role.objects.get(name='General Manager').permissions
        self.assertTrue({'register.view', 'register.create', 'register.import'} <= set(finance))
        self.assertTrue({'register.view', 'register.approve'} <= set(manager))
        for role_permissions in (finance, manager):
            self.assertFalse({'register.cancel', 'register.bank_details', 'logs.view'} & set(role_permissions))
        self.assertEqual(RegisterRule.objects.get(pk=1).approver_role.name, 'General Manager')
        self.assertEqual(Workflow.objects.count(), 2)
        self.assertTrue(Company.objects.filter(pk=1).exists())
        event = AuditEvent.objects.get(action='setup.completed')
        self.assertNotIn(PASSWORD, str(event.__dict__))
        self.assertEqual(self.client.get('/api/setup/').data, {'required': False})
        login = self.client.post('/api/auth/login/', {'username': 'owner', 'password': PASSWORD}, format='json')
        self.assertEqual(login.status_code, 200)

    def test_setup_closes_once_an_active_account_exists(self):
        self.assertEqual(self.client.post('/api/setup/', payload(), format='json').status_code, 201)
        second = self.client.post('/api/setup/', payload(username='intruder'), format='json')
        self.assertEqual(second.status_code, 400)
        self.assertFalse(User.objects.filter(username='intruder').exists())

    def test_pending_registrations_do_not_close_setup(self):
        User.objects.create_user('waiting', password=PASSWORD, status='pending')
        self.assertEqual(self.client.get('/api/setup/').data, {'required': True})

    def test_rejects_weak_or_mismatched_passwords_without_changes(self):
        weak = self.client.post('/api/setup/', payload(password='short', confirm_password='short'), format='json')
        mismatch = self.client.post('/api/setup/', payload(confirm_password='Different-phrase-9921!'), format='json')
        self.assertEqual((weak.status_code, mismatch.status_code), (400, 400))
        self.assertIn('password', weak.data)
        self.assertFalse(User.objects.exists())
        self.assertFalse(Role.objects.exists())

    def test_existing_roles_are_not_overwritten(self):
        Role.objects.create(name='Finance Manager', permissions=['parties.view'])
        self.client.post('/api/setup/', payload(), format='json')
        self.assertEqual(Role.objects.get(name='Finance Manager').permissions, ['parties.view'])

    @override_settings(V2_DESKTOP=False)
    def test_endpoint_is_absent_outside_desktop_mode(self):
        self.assertEqual(self.client.get('/api/setup/').status_code, 404)
        self.assertEqual(self.client.post('/api/setup/', payload(), format='json').status_code, 404)
        self.assertFalse(User.objects.exists())


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class BootstrapCommandTests(TestCase):
    def test_pilot_bootstrap_keeps_register_permissions_unassigned(self):
        with patch('builtins.input', side_effect=['admin', 'admin@example.com']), patch('getpass.getpass', side_effect=[PASSWORD, PASSWORD]):
            call_command('bootstrap', stdout=StringIO())
        self.assertEqual(User.objects.get(username='admin').role.name, 'Administrator')
        self.assertNotIn('register.view', Role.objects.get(name='Finance Manager').permissions)
        self.assertFalse(RegisterRule.objects.exists())
