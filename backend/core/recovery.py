import hashlib
import secrets
from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, Throttled
from .models import User, PasswordRecovery, RecoveryLimit, AccessSession
from .auth import require, audit
from .views import password_check


def desktop_only():
    if not getattr(settings, 'V2_DESKTOP', False):
        raise Http404


def rate_limit(request):
    # Commit attempts independently of a rejected recovery transaction.
    now = timezone.now()
    key = hashlib.sha256(str(request.META.get('REMOTE_ADDR', 'local')).encode()).hexdigest()
    with transaction.atomic():
        limit, _ = RecoveryLimit.objects.get_or_create(key=key, defaults={'window': now})
        if limit.window <= now - timedelta(minutes=15):
            RecoveryLimit.objects.filter(pk=limit.pk, window=limit.window).update(window=now, attempts=0)
        allowed = RecoveryLimit.objects.filter(pk=limit.pk, attempts__lt=10).update(attempts=F('attempts') + 1)
    if not allowed:
        raise Throttled(wait=900, detail='Too many recovery attempts. Try again later.')


def digest(value):
    return hashlib.sha256(value.strip().encode()).hexdigest()


class RecoveryCodes(APIView):
    def post(self, request, pk=None):
        desktop_only()
        rate_limit(request)
        if pk is not None:
            require(request.user, 'users.reset')
        if not request.user.check_password(str(request.data.get('current_password', ''))):
            raise ValidationError('Current password is incorrect.')
        with transaction.atomic():
            user = get_object_or_404(User.objects.select_for_update(), pk=pk or request.user.pk)
            if pk == request.user.pk:
                raise ValidationError('Use your own recovery-code setup instead.')
            if not user.is_active or user.status != 'active':
                raise ValidationError('Recovery does not activate pending or suspended users.')
            PasswordRecovery.objects.filter(user=user).delete()
            codes = [secrets.token_urlsafe(24) for _ in range(1 if pk else 5)]
            expires = timezone.now() + timedelta(minutes=30) if pk else None
            PasswordRecovery.objects.bulk_create([PasswordRecovery(user=user, digest=digest(code), expires_at=expires) for code in codes])
            audit(request.user, 'password.reset_code_issued' if pk else 'password.recovery_codes_regenerated', user.pk)
        response = Response({'codes': codes, 'expires_at': expires, 'message': 'Store these codes securely. They are displayed once. A successful reset invalidates all existing codes.'})
        response['Cache-Control'] = 'no-store'
        return response


class ResetPassword(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = []

    def post(self, request):
        desktop_only()
        rate_limit(request)
        username = str(request.data.get('username', '')).strip().lower()
        code = str(request.data.get('code', ''))
        if len(code) > 256:
            raise ValidationError('Invalid or expired recovery details.')
        with transaction.atomic():
            user = User.objects.select_for_update().filter(username=username, is_active=True, status='active').first()
            recovery = PasswordRecovery.objects.filter(user=user, digest=digest(code)).first() if user else None
            if not recovery or (recovery.expires_at and recovery.expires_at <= timezone.now()):
                raise ValidationError('Invalid or expired recovery details.')
            password = str(request.data.get('new_password', ''))
            password_check(password, user)
            # Conditional consumption also prevents a token replay outside row-lock DBs.
            deleted, _ = PasswordRecovery.objects.filter(pk=recovery.pk).delete()
            if not deleted:
                raise ValidationError('Invalid or expired recovery details.')
            user.set_password(password)
            user.save(update_fields=['password'])
            PasswordRecovery.objects.filter(user=user).delete()
            AccessSession.objects.filter(user=user).delete()
            audit(user, 'password.recovered', user.pk)
        return Response({'message': 'Password reset. Sign in with your new password.'})
