"""First administrator creation for a new installation. No default passwords.

The terminal bootstrap command and the desktop first-run screen share these
role defaults. The endpoint only exists in desktop mode (loopback service) and
closes permanently once any active account exists.
"""
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from .auth import PERMISSIONS, audit
from .models import Company, RegisterRule, Role, User, Workflow

ROLE_DEFAULTS = {
    'Administrator': [p for p in PERMISSIONS if not p.startswith('logs.')],
    'Finance Manager': ['parties.view', 'parties.edit', 'quotation.view', 'quotation.create', 'quotation.issue', 'invoice.view', 'invoice.create', 'invoice.issue', 'reports.view', 'reports.export'],
    'General Manager': ['parties.view', 'quotation.view', 'quotation.approve', 'quotation.issue', 'invoice.view', 'invoice.approve', 'invoice.issue', 'reports.view', 'reports.export'],
    'Coordinator': ['parties.view', 'quotation.view', 'invoice.view'],
    'Audit Reviewer': ['logs.view', 'logs.export'],
}
# Same approved register workflow as scripts/enable_v2_register_roles.py.
# Cancellation, bank identifiers and audit access are never granted to
# Finance or General Manager by default; the Administrator assigns them.
DESKTOP_REGISTER_GRANTS = {
    'Finance Manager': ['register.view', 'register.create', 'register.import', 'register.export'],
    'General Manager': ['register.view', 'register.approve', 'register.export'],
}


def setup_required():
    return not User.objects.filter(status='active').exists()


@transaction.atomic
def create_first_administrator(username, email, password, first_name='', last_name='', desktop=False):
    # A zero-row UPDATE takes SQLite's write lock before the check, so two
    # simultaneous first-run requests cannot both create an administrator.
    User.objects.filter(pk__lt=0).update(status='active')
    if not setup_required():
        raise ValidationError('This installation is already set up. Sign in or ask an administrator for access.')
    user = User(username=str(username).strip().lower(), email=str(email).strip(), first_name=str(first_name).strip(), last_name=str(last_name).strip(), status='active')
    try:
        validate_password(password, user)
    except DjangoValidationError as exc:
        raise ValidationError({'password': list(exc.messages)})
    try:
        user.full_clean(exclude=['password'])
    except DjangoValidationError as exc:
        raise ValidationError(exc.message_dict)
    roles = {}
    for name, grants in ROLE_DEFAULTS.items():
        extra = DESKTOP_REGISTER_GRANTS.get(name, []) if desktop else []
        roles[name], _ = Role.objects.get_or_create(name=name, defaults={'permissions': sorted(set(grants) | set(extra))})
    Company.objects.get_or_create(pk=1)
    for kind in ['quotation', 'invoice']:
        Workflow.objects.get_or_create(kind=kind, defaults={'approver_role': roles['General Manager']})
    if desktop:
        RegisterRule.objects.get_or_create(pk=1, defaults={'approver_role': roles['General Manager']})
    user.role = roles['Administrator']
    user.set_password(password)
    user.save()
    audit(user, 'setup.completed', user.id, source='desktop first run' if desktop else 'bootstrap command')
    return user


class FirstRunThrottle(AnonRateThrottle):
    scope = 'login'


class FirstRunSetup(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [FirstRunThrottle]

    def initial(self, request, *args, **kwargs):
        if not getattr(settings, 'V2_DESKTOP', False):
            raise NotFound()
        super().initial(request, *args, **kwargs)

    def get(self, request):
        return Response({'required': setup_required()})

    def post(self, request):
        if request.data.get('password') != request.data.get('confirm_password'):
            raise ValidationError({'confirm_password': ['Passwords do not match.']})
        user = create_first_administrator(
            request.data.get('username', ''), request.data.get('email', ''), request.data.get('password', ''),
            request.data.get('first_name', ''), request.data.get('last_name', ''), desktop=True)
        return Response({'message': 'Administrator created. Sign in to continue setup.', 'username': user.username}, status=201)
