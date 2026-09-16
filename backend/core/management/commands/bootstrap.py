import getpass
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from rest_framework.exceptions import ValidationError
from core.first_run import create_first_administrator, setup_required

class Command(BaseCommand):
    help = 'Create the first administrator interactively, without a default password.'
    def handle(self, *args, **kwargs):
        if not setup_required():
            raise CommandError('An active account already exists. Use the application to manage access.')
        username = input('Administrator username: ').strip().lower()
        email = input('Administrator email: ').strip()
        password = getpass.getpass('Password (at least 10 characters): ')
        if password != getpass.getpass('Confirm password: '):
            raise CommandError('Passwords do not match.')
        try:
            create_first_administrator(username, email, password, desktop=getattr(settings, 'V2_DESKTOP', False))
        except ValidationError as exc:
            raise CommandError(str(exc.detail))
        self.stdout.write(self.style.SUCCESS('Administrator created. Audit access belongs only to the designated Audit Reviewer role by default.'))
