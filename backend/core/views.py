import hashlib
import secrets
from datetime import timedelta
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle
from .models import User, Role, AccessSession, Company, Party, Workflow, Document, AuditEvent, ApprovalEvent, SavedReport
from .auth import PERMISSIONS, permissions, require, audit
from .serializers import CompanySerializer, PartySerializer, RoleSerializer, WorkflowSerializer, DocumentSerializer, save_lines

def identity(user):
    return {'id': user.id, 'username': user.username, 'email': user.email, 'first_name': user.first_name, 'last_name': user.last_name, 'phone': user.phone, 'status': user.status, 'role': user.role_id, 'role_name': user.role.name if user.role_id else 'Unassigned', 'permissions': sorted(permissions(user))}

def password_check(password, user):
    try:
        validate_password(password, user)
    except DjangoValidationError as exc:
        raise ValidationError({'password': list(exc.messages)})

class LoginThrottle(AnonRateThrottle):
    scope = 'login'

class Health(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    def get(self, request):
        desktop = getattr(settings, 'V2_DESKTOP', False)
        return Response({'service': 'Zakaria ERP', 'version': '2.1.0' if desktop else '0.1.0', 'mode': 'desktop-register' if desktop else 'development-pilot', 'time': timezone.now()})

class Register(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [LoginThrottle]
    @transaction.atomic
    def post(self, request):
        username = str(request.data.get('username', '')).strip().lower()
        email = str(request.data.get('email', '')).strip()
        password = request.data.get('password', '')
        if not username or not email or User.objects.filter(username__iexact=username).exists():
            raise ValidationError('Provide an email and an available username.')
        user = User(username=username, email=email, first_name=str(request.data.get('first_name', '')), status='pending')
        password_check(password, user)
        try:
            user.full_clean(exclude=['password'])
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict)
        user.set_password(password)
        user.save()
        audit(user, 'account.registered', user.id)
        return Response({'message': 'Registration received. An administrator must activate your account and assign a role.'}, status=201)

class Login(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [LoginThrottle]
    def post(self, request):
        user = authenticate(username=str(request.data.get('username', '')).strip().lower(), password=request.data.get('password', ''))
        if not user:
            raise ValidationError('Invalid username or password.')
        if user.status != 'active' or not user.role_id:
            raise PermissionDenied('Your account is pending approval or suspended.')
        key = secrets.token_urlsafe(40)
        AccessSession.objects.create(user=user, key_hash=hashlib.sha256(key.encode()).hexdigest(), expires_at=timezone.now() + timedelta(hours=8))
        audit(user, 'account.login', user.id)
        return Response({'token': key, 'user': identity(user)})

class Logout(APIView):
    def post(self, request):
        request.auth.delete()
        audit(request.user, 'account.logout', request.user.id)
        return Response({'message': 'Signed out.'})

class Profile(APIView):
    def get(self, request):
        return Response(identity(request.user))
    def patch(self, request):
        user = request.user
        for key in ['first_name', 'last_name', 'phone', 'email']:
            if key in request.data:
                setattr(user, key, request.data[key])
        try:
            user.full_clean()
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict)
        user.save()
        audit(user, 'profile.updated', user.id)
        return Response(identity(user))

class ChangePassword(APIView):
    @transaction.atomic
    def post(self, request):
        user = User.objects.select_for_update().get(pk=request.user.pk)
        if not user.check_password(request.data.get('current_password', '')):
            raise ValidationError('Current password is incorrect.')
        password = request.data.get('new_password', '')
        password_check(password, user)
        user.set_password(password)
        user.save()
        AccessSession.objects.filter(user=user).delete()
        from .models import PasswordRecovery
        from django.conf import settings
        if getattr(settings, 'V2_DESKTOP', False):
            PasswordRecovery.objects.filter(user=user).delete()
        audit(user, 'password.changed', user.id)
        return Response({'message': 'Password changed. Sign in again on your devices.'})

class Users(APIView):
    def get(self, request):
        require(request.user, 'users.manage')
        return Response([identity(u) for u in User.objects.select_related('role').order_by('username')])
    @transaction.atomic
    def patch(self, request, pk):
        require(request.user, 'users.manage')
        user = get_object_or_404(User.objects.select_for_update(), pk=pk)
        if user.pk == request.user.pk:
            raise ValidationError('Use another authorized administrator to change your own access.')
        status = request.data.get('status', user.status)
        if status not in ['pending', 'active', 'suspended']:
            raise ValidationError('Invalid account status.')
        role_id = request.data.get('role', user.role_id)
        role = get_object_or_404(Role, pk=role_id) if role_id else None
        if role and not set(role.permissions).issubset(permissions(request.user)) and 'roles.manage' not in permissions(request.user):
            raise PermissionDenied('Role assignment requires role-management permission for these privileges.')
        if status == 'active' and not role:
            raise ValidationError('Assign a role before activation.')
        user.role, user.status = role, status
        user.save()
        AccessSession.objects.filter(user=user).delete()
        audit(request.user, 'user.access_changed', user.id, status=status, role=role_id)
        return Response(identity(user))

class Roles(APIView):
    def get(self, request):
        if not permissions(request.user).intersection({'roles.manage', 'users.manage', 'workflows.manage'}):
            raise PermissionDenied()
        return Response({'roles': RoleSerializer(Role.objects.order_by('name'), many=True).data, 'permissions': PERMISSIONS})
    @transaction.atomic
    def post(self, request):
        require(request.user, 'roles.manage')
        serializer = RoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = serializer.save()
        audit(request.user, 'role.created', role.id, name=role.name)
        return Response(serializer.data, status=201)
    @transaction.atomic
    def patch(self, request, pk):
        require(request.user, 'roles.manage')
        role = get_object_or_404(Role.objects.select_for_update(), pk=pk)
        serializer = RoleSerializer(role, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        new_permissions = serializer.validated_data.get('permissions', role.permissions)
        if role.pk == request.user.role_id and ('roles.manage' not in new_permissions or 'users.manage' not in new_permissions):
            raise ValidationError('You cannot remove your own access-management permissions.')
        for workflow in Workflow.objects.filter(approver_role=role):
            if f'{workflow.kind}.approve' not in new_permissions:
                raise ValidationError('Reassign the workflow before removing its approval permission.')
        serializer.save()
        audit(request.user, 'role.updated', role.id, permissions=new_permissions)
        return Response(serializer.data)

class CompanyView(APIView):
    def get(self, request):
        return Response(CompanySerializer(Company.objects.get(pk=1)).data)
    def patch(self, request):
        require(request.user, 'company.manage')
        serializer = CompanySerializer(Company.objects.get(pk=1), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        audit(request.user, 'company.updated', 1)
        return Response(serializer.data)

class Parties(APIView):
    def get(self, request):
        require(request.user, 'parties.view')
        queryset = Party.objects.order_by('name')
        if request.query_params.get('search'):
            queryset = queryset.filter(name__icontains=request.query_params['search'])
        return Response(PartySerializer(queryset[:1000], many=True).data)
    def post(self, request):
        require(request.user, 'parties.edit')
        serializer = PartySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        party = serializer.save()
        audit(request.user, 'party.created', party.id)
        return Response(serializer.data, status=201)
    def patch(self, request, pk):
        require(request.user, 'parties.edit')
        serializer = PartySerializer(get_object_or_404(Party, pk=pk), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        audit(request.user, 'party.updated', pk)
        return Response(serializer.data)

class Workflows(APIView):
    def get(self, request):
        require(request.user, 'workflows.manage')
        return Response(WorkflowSerializer(Workflow.objects.all(), many=True).data)
    @transaction.atomic
    def post(self, request):
        require(request.user, 'workflows.manage')
        instance = Workflow.objects.select_for_update().filter(kind=request.data.get('kind')).first()
        serializer = WorkflowSerializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        workflow = serializer.save(version=instance.version + 1 if instance else 1)
        audit(request.user, 'workflow.updated', workflow.kind, version=workflow.version)
        return Response(serializer.data)

class Documents(APIView):
    def get(self, request, pk=None):
        queryset = Document.objects.select_related('party', 'owner').prefetch_related('lines')
        if pk:
            doc = get_object_or_404(queryset, pk=pk)
            require(request.user, f'{doc.kind}.view')
            return Response(DocumentSerializer(doc).data)
        kind = request.query_params.get('kind', 'quotation')
        if kind not in ['quotation', 'invoice']:
            raise ValidationError('Invalid document type.')
        require(request.user, f'{kind}.view')
        return Response(DocumentSerializer(queryset.filter(kind=kind).exclude(status='deleted').order_by('-id')[:500], many=True).data)
    @transaction.atomic
    def post(self, request):
        kind = request.data.get('kind')
        require(request.user, f'{kind}.create')
        serializer = DocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        lines = data.pop('lines')
        # Lock singleton company to serialize numbering under PostgreSQL.
        Company.objects.select_for_update().get(pk=1)
        doc = Document.objects.create(owner=request.user, number='TMP-' + secrets.token_hex(12), **data)
        doc.number = f"{'QUO' if kind == 'quotation' else 'INV'}-{doc.issue_date.year}-{doc.id:06d}"
        save_lines(doc, lines)
        audit(request.user, 'document.created', doc.number)
        return Response(DocumentSerializer(doc).data, status=201)
    @transaction.atomic
    def put(self, request, pk):
        doc = get_object_or_404(Document.objects.select_for_update(), pk=pk)
        require(request.user, f'{doc.kind}.create')
        if doc.owner_id != request.user.id:
            raise PermissionDenied('Only the preparer can edit this draft.')
        if doc.status not in ['draft', 'returned']:
            raise ValidationError('Only draft or returned documents can be edited.')
        if request.data.get('version') != doc.version:
            raise ValidationError('This document changed. Refresh before saving.')
        if request.data.get('kind') != doc.kind:
            raise ValidationError('Document type cannot change.')
        serializer = DocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        lines = data.pop('lines')
        for key, value in data.items():
            setattr(doc, key, value)
        doc.version += 1
        save_lines(doc, lines)
        audit(request.user, 'document.updated', doc.number, version=doc.version)
        return Response(DocumentSerializer(doc).data)

class DocumentAction(APIView):
    @transaction.atomic
    def post(self, request, pk):
        doc = get_object_or_404(Document.objects.select_for_update(), pk=pk)
        action = request.data.get('action')
        comment = str(request.data.get('comment', '')).strip()[:2000]
        require(request.user, f'{doc.kind}.view')
        if request.data.get('version') != doc.version:
            raise ValidationError('This document changed. Refresh before taking action.')
        if action == 'submit':
            require(request.user, f'{doc.kind}.create')
            if doc.owner_id != request.user.id or doc.status not in ['draft', 'returned']:
                raise ValidationError('Only the preparer can submit an editable document.')
            if doc.tax_treatment == 'unspecified':
                raise ValidationError('Choose an explicit tax treatment before submission.')
            rule = Workflow.objects.filter(kind=doc.kind).first()
            if not rule:
                raise ValidationError('An administrator must configure this approval workflow first.')
            doc.workflow_snapshot = {'role_id': rule.approver_role_id, 'allow_self_approval': rule.allow_self_approval, 'version': rule.version}
            doc.submitted_by = request.user
            doc.submitted_at = timezone.now()
            doc.status = 'submitted'
        elif action in ['approve', 'return', 'reject']:
            require(request.user, f'{doc.kind}.approve')
            if doc.status != 'submitted' or request.user.role_id != doc.workflow_snapshot.get('role_id'):
                raise PermissionDenied('This document is not assigned to your approving role.')
            if doc.owner_id == request.user.id and not doc.workflow_snapshot.get('allow_self_approval'):
                raise PermissionDenied('Self-approval is disabled.')
            if action in ['return', 'reject'] and not comment:
                raise ValidationError('Provide a reason for returning or rejecting this document.')
            doc.status = {'approve': 'approved', 'return': 'returned', 'reject': 'rejected'}[action]
            if action == 'approve':
                doc.approved_by, doc.approved_at = request.user, timezone.now()
        elif action == 'issue':
            require(request.user, f'{doc.kind}.issue')
            if doc.status != 'approved':
                raise ValidationError('Approval is required before issuing.')
            # Live invoice issuance stays blocked until accounting and tax integration are implemented.
            if doc.kind == 'invoice':
                raise ValidationError('Live invoice issuance is not enabled in this pilot. Accounting and tax readiness must be completed first.')
            company = Company.objects.get(pk=1)
            if not company.address:
                raise ValidationError('Complete the company address before issuing documents.')
            doc.issued_at = timezone.now()
            doc.status = 'issued'
            doc.issued_snapshot = {'company': CompanySerializer(company).data, 'party': PartySerializer(doc.party).data, 'template_version': 1}
        else:
            raise ValidationError('Unknown action.')
        doc.version += 1
        doc.save()
        ApprovalEvent.objects.create(document=doc, actor=request.user, action=action, comment=comment)
        audit(request.user, 'document.' + action, doc.number, comment=comment, version=doc.version)
        return Response(DocumentSerializer(doc).data)

class Dashboard(APIView):
    def get(self, request):
        kinds = [k for k in ['quotation', 'invoice'] if f'{k}.view' in permissions(request.user)]
        docs = Document.objects.filter(kind__in=kinds).exclude(status='deleted')
        pending = [d for d in docs.filter(status='submitted').select_related('party', 'owner') if d.workflow_snapshot.get('role_id') == request.user.role_id and f'{d.kind}.approve' in permissions(request.user) and (d.owner_id != request.user.id or d.workflow_snapshot.get('allow_self_approval'))]
        result = {'quotations': docs.filter(kind='quotation').count(), 'invoices': docs.filter(kind='invoice').count(), 'pending_approvals': len(pending), 'my_submitted': docs.filter(owner=request.user, status='submitted').count(), 'pending': DocumentSerializer(pending, many=True).data, 'recent': DocumentSerializer(docs.select_related('party', 'owner').prefetch_related('lines').order_by('-updated_at')[:8], many=True).data}
        from django.conf import settings
        if getattr(settings, 'V2_DESKTOP', False) and 'register.view' in permissions(request.user):
            from .registers import dashboard_summary
            result['register'] = dashboard_summary(request.user)
        return Response(result)

class Logs(APIView):
    def get(self, request):
        require(request.user, 'logs.view')
        rows = list(AuditEvent.objects.select_related('actor').order_by('-id')[:500].values('id', 'created_at', 'actor__username', 'action', 'target', 'details'))
        if request.query_params.get('export') == 'csv':
            require(request.user, 'logs.export')
            from .reports import csv_response
            audit(request.user, 'audit.exported', 'latest-500')
            return csv_response(rows, ['id', 'created_at', 'actor__username', 'action', 'target', 'details'], 'audit-log.csv')
        audit(request.user, 'audit.viewed', 'latest-500')
        return Response(rows)
