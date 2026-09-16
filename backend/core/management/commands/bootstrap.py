import getpass
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from core.models import Company, Role, User, Workflow
from core.auth import PERMISSIONS, audit

class Command(BaseCommand):
    help = 'Create the first administrator interactively, without a default password.'
    @transaction.atomic
    def handle(self, *args, **kwargs):
        if User.objects.filter(status='active').exists():
            raise CommandError('An active account already exists. Use the application to manage access.')
        username = input('Administrator username: ').strip().lower()
        email = input('Administrator email: ').strip()
        password = getpass.getpass('Password (at least 10 characters): ')
        if password != getpass.getpass('Confirm password: '):
            raise CommandError('Passwords do not match.')
        user = User(username=username, email=email, status='active')
        try:
            validate_password(password, user)
            user.full_clean(exclude=['password'])
        except Exception as exc:
            raise CommandError(str(exc))
        admin, _ = Role.objects.get_or_create(name='Administrator', defaults={'permissions': [p for p in PERMISSIONS if not p.startswith('logs.')]})
        finance, _ = Role.objects.get_or_create(name='Finance Manager', defaults={'permissions': ['parties.view', 'parties.edit', 'quotation.view', 'quotation.create', 'quotation.issue', 'invoice.view', 'invoice.create', 'invoice.issue', 'reports.view', 'reports.export']})
        gm, _ = Role.objects.get_or_create(name='General Manager', defaults={'permissions': ['parties.view', 'quotation.view', 'quotation.approve', 'quotation.issue', 'invoice.view', 'invoice.approve', 'invoice.issue', 'reports.view', 'reports.export']})
        Role.objects.get_or_create(name='Coordinator', defaults={'permissions': ['parties.view', 'quotation.view', 'invoice.view']})
        Role.objects.get_or_create(name='Audit Reviewer', defaults={'permissions': ['logs.view', 'logs.export']})
        Company.objects.get_or_create(pk=1)
        for kind in ['quotation', 'invoice']:
            Workflow.objects.get_or_create(kind=kind, defaults={'approver_role': gm})
        user.role = admin
        user.set_password(password)
        user.save()
        audit(user, 'setup.completed', user.id)
        self.stdout.write(self.style.SUCCESS('Administrator created. Audit access belongs only to the designated Audit Reviewer role by default.'))
