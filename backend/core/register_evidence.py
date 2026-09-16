"""Private register supporting documents; bytes participate in database backups."""
import hashlib
from pathlib import PurePosixPath
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.http import content_disposition_header
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from .auth import require, audit
from .models import RegisterEntry, RegisterAttachment
from .recovery import desktop_only

MAX_SIZE = 5 * 1024 * 1024


def editable(request, entry):
    require(request.user, 'register.create')
    try:
        version = int(request.data.get('version', 0))
    except (ValueError, TypeError):
        version = 0
    if entry.owner_id != request.user.pk or entry.status != 'draft' or version != entry.version:
        raise ValidationError('Only the preparer can change supporting documents on the current draft. Refresh and try again.')


class RegisterAttachments(APIView):
    def get(self, request, pk, attachment_id=None):
        desktop_only()
        require(request.user, 'register.view')
        entry = get_object_or_404(RegisterEntry, pk=pk)
        if attachment_id is None:
            rows = list(entry.attachments.order_by('pk').values('id', 'name', 'mime', 'size', 'sha256', 'uploaded_by__username', 'uploaded_at', 'withdrawn_at', 'withdrawal_reason'))
            return Response({'rows': rows, 'version': entry.version, 'status': entry.status, 'owner': entry.owner_id})
        item = get_object_or_404(RegisterAttachment, entry=entry, pk=attachment_id, withdrawn_at__isnull=True)
        audit(request.user, 'register.evidence_read', entry.pk, attachment_id=item.pk)
        response = HttpResponse(bytes(item.content), content_type=item.mime)
        response['Content-Disposition'] = content_disposition_header(True, item.name)
        response['Cache-Control'] = 'no-store'
        response['X-Content-Type-Options'] = 'nosniff'
        return response

    @transaction.atomic
    def post(self, request, pk, attachment_id=None):
        desktop_only()
        require(request.user, 'register.view')
        entry = get_object_or_404(RegisterEntry.objects.select_for_update(), pk=pk)
        editable(request, entry)
        if attachment_id is not None:
            item = get_object_or_404(RegisterAttachment, entry=entry, pk=attachment_id, withdrawn_at__isnull=True)
            reason = str(request.data.get('reason', '')).strip()
            if not reason or len(reason) > 500:
                raise ValidationError('Provide a withdrawal reason of 1–500 characters.')
            item.withdrawn_at, item.withdrawal_reason = timezone.now(), reason
            item.save(update_fields=['withdrawn_at', 'withdrawal_reason'])
            event = 'register.evidence_withdrawn'
        else:
            upload = request.FILES.get('file')
            if not upload or not 0 < upload.size <= MAX_SIZE:
                raise ValidationError('Select one non-empty PNG, JPEG or PDF, up to 5 MB.')
            if entry.attachments.count() >= 10:
                raise ValidationError('Maximum 10 supporting documents per entry, including withdrawn documents.')
            name = PurePosixPath(upload.name.replace('\\', '/')).name
            if not name or len(name) > 180 or any(ord(c) < 32 for c in name):
                raise ValidationError('Use a filename of up to 180 printable characters.')
            content = upload.read(MAX_SIZE + 1)
            extension = PurePosixPath(name).suffix.lower()
            mime = None
            if extension == '.png' and content.startswith(b'\x89PNG\r\n\x1a\n'):
                mime = 'image/png'
            elif extension in ['.jpg', '.jpeg'] and content.startswith(b'\xff\xd8\xff'):
                mime = 'image/jpeg'
            elif extension == '.pdf' and content.startswith(b'%PDF-'):
                mime = 'application/pdf'
            if mime is None or len(content) > MAX_SIZE:
                raise ValidationError('The filename and file signature must match a supported PNG, JPEG or PDF.')
            digest = hashlib.sha256(content).hexdigest()
            if entry.attachments.filter(sha256=digest, withdrawn_at__isnull=True).exists():
                raise ValidationError('This supporting document is already attached.')
            item = RegisterAttachment.objects.create(entry=entry, name=name, mime=mime, size=len(content), sha256=digest, content=content, uploaded_by=request.user)
            event = 'register.evidence_uploaded'
        entry.version += 1
        entry.save(update_fields=['version'])
        audit(request.user, event, entry.pk, attachment_id=item.pk, sha256=item.sha256)
        return Response({'id': item.pk, 'version': entry.version})
