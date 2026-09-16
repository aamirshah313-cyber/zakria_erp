"""Recoverable removal for V2 working data; financial history is retained."""
import hashlib
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from .auth import require, audit
from .models import (Company, RegisterEntry, RegisterPosition, RegisterImport,
                     RegisterCategory, RegisterSource, Project, Party, RegisterReportTemplate, Document)
from .recovery import desktop_only

KINDS = {'quotations': (Document, 'Quotation drafts'), 'invoices': (Document, 'Invoice drafts'), 'entries': (RegisterEntry, 'Receipt / payment drafts'),
         'positions': (RegisterPosition, 'Opening / transfer drafts'),
         'imports': (RegisterImport, 'Uncommitted spreadsheet batches'),
         'categories': (RegisterCategory, 'Categories'), 'sources': (RegisterSource, 'Cash / bank accounts'),
         'projects': (Project, 'Projects / contracts'), 'parties': (Party, 'Parties'),
         'layouts': (RegisterReportTemplate, 'Personal report layouts')}
STATUS_KINDS = ['entries', 'positions', 'imports', 'quotations', 'invoices']


def state(obj):
    return obj.status if hasattr(obj, 'status') else ('active' if obj.active else 'archived')


def revision(obj):
    if hasattr(obj, 'version'):
        return str(obj.version)
    return hashlib.sha256(repr([(f.name, getattr(obj, f.attname)) for f in obj._meta.fields]).encode()).hexdigest()


def query_for(kind, user):
    if not isinstance(kind,str) or kind not in KINDS:
        raise ValidationError('Select a supported record type.')
    query = KINDS[kind][0].objects.all()
    if kind in ['quotations', 'invoices']:
        require(user, f'{kind[:-1]}.view')
        query = query.filter(kind=kind[:-1])
    if kind == 'layouts':
        query = query.filter(owner=user)
    return query


class RegisterData(APIView):
    def get(self, request):
        desktop_only()
        require(request.user, 'register.delete')
        kind = request.query_params.get('kind', 'entries')
        query = query_for(kind, request.user)
        try:
            page = max(1, int(request.query_params.get('page', 1)))
        except ValueError:
            raise ValidationError('Invalid page.')
        if request.query_params.get('removed') == 'true':
            query = query.filter(status='deleted') if kind in STATUS_KINDS else query.filter(active=False)
        else:
            query = query.exclude(status='deleted') if kind in STATUS_KINDS else query.filter(active=True)
        rows = []
        for obj in query.order_by('-pk')[(page-1)*50:page*50]:
            label = getattr(obj, 'number', None) or getattr(obj, 'name', None) or getattr(obj, 'filename', None) or getattr(obj, 'party', None) or getattr(obj, 'reference', '')
            actions = ['restore'] if state(obj) in ['deleted', 'archived'] else ['remove']
            if kind in ['entries', 'positions', 'quotations', 'invoices'] and obj.status != 'draft' and obj.status != 'deleted':
                actions = []
            if kind == 'imports' and obj.status not in ['staged', 'reviewed', 'deleted']:
                actions = []
            rows.append({'id':obj.pk, 'label':label, 'status':state(obj), 'revision':revision(obj),
                         'date':str(getattr(obj, 'date', getattr(obj,'issue_date',''))), 'amount':str(getattr(obj, 'amount', getattr(obj,'total',''))),
                         'version':getattr(obj,'version',None), 'actions':actions})
        return Response({'kinds':{k:v[1] for k,v in KINDS.items()}, 'rows':rows, 'count':query.count(), 'page':page})

    @transaction.atomic
    def post(self, request):
        desktop_only()
        require(request.user, 'register.delete')
        get_object_or_404(Company.objects.select_for_update(), pk=1)
        kind, action = request.data.get('kind'), request.data.get('action')
        obj = get_object_or_404(query_for(kind, request.user).select_for_update(), pk=request.data.get('id'))
        if request.data.get('revision') != revision(obj):
            raise ValidationError('This record changed. Refresh and review it again.')
        reason = request.data.get('reason', '')
        if not isinstance(reason,str) or not 1 <= len(reason.strip()) <= 1000:
            raise ValidationError('Enter a reason of 1–1,000 characters.')
        before = state(obj)
        if action not in ['remove', 'restore']:
            raise ValidationError('Select Remove or Restore.')
        if kind in STATUS_KINDS:
            if kind in ['quotations', 'invoices']:
                require(request.user, f'{kind[:-1]}.create')
            allowed = ['staged','reviewed'] if kind == 'imports' else ['draft']
            if action == 'remove' and obj.status not in allowed:
                raise ValidationError('Only drafts or uncommitted imports can be removed. Return submitted records for correction, or cancel confirmed records with the authorized permission.')
            if action == 'restore' and obj.status != 'deleted':
                raise ValidationError('Only removed records can be restored.')
            obj.status = 'deleted' if action == 'remove' else ('staged' if kind == 'imports' else 'draft')
            if kind == 'imports':
                obj.preview = {}  # Always review again after restoration.
            obj.version += 1
        else:
            require(request.user, 'register.manage' if kind != 'layouts' else 'register.view')
            if kind == 'categories':
                from .registers import CategorySerializer
                validator = CategorySerializer(obj, data={'active':action == 'restore'}, partial=True)
                validator.is_valid(raise_exception=True)
            if obj.active == (action == 'restore'):
                raise ValidationError('This record is already in the requested state.')
            obj.active = action == 'restore'
        obj.save()
        audit(request.user, 'register.data_'+action, f'{kind}:{obj.pk}', before=before,
              after=state(obj), reason=reason.strip(), revision=revision(obj))
        return Response({'message':'Record removed from active work lists; retained for recovery.' if action == 'remove' else 'Record restored. Drafts still require review.', 'status':state(obj)})
