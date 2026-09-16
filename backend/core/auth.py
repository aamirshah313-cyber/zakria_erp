import hashlib
from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from .models import AccessSession, AuditEvent

PERMISSIONS = {
    'system.backup': 'Save and download full data backups',
    'system.restore': 'Replace all data, accounts and passwords from a backup; signs everyone out',
    'register.delete': 'Remove and restore register drafts; archive and restore setup records',
    'register.bank_details': 'View and maintain sensitive bank account identifiers',
    'register.import': 'Stage and review spreadsheet imports into register drafts',
    'users.reset': 'Issue one-time password reset codes after identity verification',
    'register.view': 'View transaction register and activity ledgers',
    'register.manage': 'Maintain register categories and cash/bank sources',
    'register.create': 'Prepare and submit receipts/payments',
    'register.approve': 'Confirm submitted register entries',
    'register.cancel': 'Cancel confirmed register entries with a reason',
    'register.export': 'Export register activity ledgers',
    'finance.view': 'View accounting transactions and account lists',
    'finance.manage': 'Manage accounting accounts, projects and settings',
    'finance.create': 'Prepare and submit accounting vouchers',
    'finance.approve': 'Approve accounting vouchers',
    'finance.post': 'Post approved accounting vouchers',
    'finance.reverse': 'Prepare correcting reversals',
    'finance.evidence': 'Upload and download private accounting evidence',
    'finance.reports': 'View accounting ledgers and trial balance',
    'finance.export': 'Export accounting reports',
    'users.manage': 'Manage user accounts', 'roles.manage': 'Manage roles and permissions',
    'workflows.manage': 'Configure approval workflows', 'company.manage': 'Edit company details',
    'parties.view': 'View customers and suppliers', 'parties.edit': 'Create and edit parties',
    'quotation.view': 'View quotations', 'quotation.create': 'Prepare quotations',
    'quotation.approve': 'Approve quotations', 'quotation.issue': 'Issue quotations',
    'invoice.view': 'View invoices', 'invoice.create': 'Prepare invoices',
    'invoice.approve': 'Approve invoices', 'invoice.issue': 'Issue invoices',
    'reports.view': 'View and build reports', 'reports.export': 'Export reports and documents',
    'logs.view': 'View audit logs', 'logs.export': 'Export audit logs',
}

def permissions(user):
    # No implicit administrator or superuser bypass for audit access.
    return set(user.role.permissions) if user.role_id else set()

def require(user, permission):
    if permission not in permissions(user):
        raise PermissionDenied('Your assigned role does not allow this action.')

def audit(user, action, target='', **details):
    AuditEvent.objects.create(actor=user, action=action, target=str(target), details=details)

class SessionAuthentication(BaseAuthentication):
    def authenticate(self, request):
        header = request.headers.get('Authorization', '')
        if not header:
            return None
        if not header.startswith('Bearer '):
            raise AuthenticationFailed('Invalid authorization header.')
        digest = hashlib.sha256(header[7:].encode()).hexdigest()
        session = AccessSession.objects.select_related('user__role').filter(key_hash=digest, expires_at__gt=timezone.now()).first()
        if not session or not session.user.is_active or session.user.status != 'active':
            raise AuthenticationFailed('Session expired or account is not active.')
        return session.user, session

    def authenticate_header(self, request):
        return 'Bearer'
