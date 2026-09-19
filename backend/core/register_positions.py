"""Reviewed openings and transfers. Shared company lock serializes cutoff checks."""
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Company, RegisterPosition, RegisterEntry, RegisterRule
from .auth import require, audit
from .recovery import desktop_only

DIMENSIONS = ['source', 'category', 'project', 'counterparty']


def entry_scope(key, value):
    clause = Q(**{key+'_id': value})
    if key in ['category', 'project']:
        # Header category/project is the first allocation for compatibility.
        clause |= Q(**{'allocations__'+key+'_id': value})
    return clause


def check_cutoffs(date, source, category=None, project=None, counterparty=None, allocations=()):
    refs = {'source': {source.pk}, 'category': {category.pk} if category else set(), 'project': {project.pk} if project else set(), 'counterparty': {counterparty.pk} if counterparty else set()}
    for line in allocations:
        for key in ['category', 'project']:
            record = line.get(key) if isinstance(line, dict) else getattr(line, key)
            if record:
                refs[key].add(record.pk)
    for key, values in refs.items():
        if values and RegisterPosition.objects.filter(kind='opening', status='confirmed', date__gt=date, **{key+'_id__in': values}).exists():
            raise ValidationError('This date precedes a reviewed opening balance. Import movements from the opening date onward; do not duplicate earlier history.')


class PositionSerializer(serializers.ModelSerializer):
    # Active supporting documents; present when the list query annotates it.
    documents = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = RegisterPosition
        fields = '__all__'
        read_only_fields = ['owner','status','version','approver_role','approved_by','created_at','confirmed_at','cancellation_reason']

    def validate(self, data):
        if data['amount'] <= 0:
            raise ValidationError('Amount must be positive.')
        for key in DIMENSIONS + ['destination']:
            if data.get(key) and not data[key].active:
                raise ValidationError('Select active setup records.')
        if data['kind'] == 'transfer':
            if not data.get('source') or not data.get('destination') or data['source'] == data['destination']:
                raise ValidationError('Choose two different own cash/bank accounts.')
            if any(data.get(k) for k in ['category', 'project', 'counterparty']):
                raise ValidationError('Own-account transfers do not allocate external expense or project activity.')
            for key in ['source', 'destination']:
                check_cutoffs(data['date'], data[key])
        elif sum(bool(data.get(k)) for k in DIMENSIONS) != 1 or data.get('destination'):
            raise ValidationError('Opening balances must identify exactly one account, category, project or party.')
        return data


def validate_opening(item):
    key = next(k for k in DIMENSIONS if getattr(item, k+'_id'))
    value = getattr(item, key+'_id')
    if RegisterPosition.objects.filter(kind='opening', status='confirmed', **{key+'_id': value}).exclude(pk=item.pk).exists():
        raise ValidationError('This scope already has a confirmed opening balance.')
    if RegisterEntry.objects.filter(status='confirmed', date__lt=item.date).filter(entry_scope(key, value)).exists():
        raise ValidationError('Earlier confirmed history exists for this scope. Use full history instead of adding a duplicate opening.')
    if key == 'source' and RegisterPosition.objects.filter(kind='transfer', status='confirmed', date__lt=item.date).filter(Q(source_id=value) | Q(destination_id=value)).exists():
        raise ValidationError('Earlier confirmed transfers exist for this account.')


class Positions(APIView):
    def get(self, request):
        desktop_only()
        require(request.user, 'register.view')
        query = RegisterPosition.objects.exclude(status='deleted').annotate(documents=Count('attachments', filter=Q(attachments__withdrawn_at__isnull=True)))
        return Response(PositionSerializer(query.order_by('-date','-pk')[:1000], many=True).data)

    @transaction.atomic
    def post(self, request, pk=None):
        desktop_only()
        require(request.user, 'register.view')
        get_object_or_404(Company.objects.select_for_update(), pk=1)
        if pk is None:
            require(request.user, 'register.create')
            serializer = PositionSerializer(data=request.data)
            serializer.fields['request_key'].validators = []
            serializer.is_valid(raise_exception=True)
            previous = RegisterPosition.objects.filter(request_key=serializer.validated_data['request_key']).first()
            if previous:
                if previous.owner_id != request.user.pk:
                    raise PermissionDenied()
                if any(getattr(previous,k) != v for k,v in serializer.validated_data.items()):
                    raise ValidationError('Request reference already used for different content.')
                return Response(PositionSerializer(previous).data)
            item = serializer.save(owner=request.user)
            audit(request.user, 'register.position_created', item.pk)
            return Response(serializer.data, status=201)
        item = get_object_or_404(RegisterPosition.objects.select_for_update(), pk=pk)
        if request.data.get('version') != item.version:
            raise ValidationError('Record changed. Refresh before continuing.')
        action = request.data.get('action')
        if action == 'submit':
            require(request.user, 'register.create')
            if item.owner_id != request.user.pk or item.status != 'draft':
                raise ValidationError('Only the preparer can submit a draft.')
            rule = get_object_or_404(RegisterRule, pk=1)
            item.approver_role, item.status = rule.approver_role, 'submitted'
        elif action in ['confirm', 'return']:
            require(request.user, 'register.approve')
            if item.status != 'submitted' or item.owner_id == request.user.pk or item.approver_role_id != request.user.role_id:
                raise PermissionDenied('Only the assigned separate reviewer can approve this submission.')
            if action == 'confirm':
                validator = PositionSerializer(data={k: v for k,v in PositionSerializer(item).data.items() if k != 'id'})
                validator.fields['request_key'].validators = []
                validator.is_valid(raise_exception=True)
                if item.kind == 'opening':
                    validate_opening(item)
                item.status, item.approved_by, item.confirmed_at = 'confirmed', request.user, timezone.now()
            else:
                item.status = 'draft'
        elif action == 'cancel':
            require(request.user, 'register.cancel')
            reason = str(request.data.get('reason', '')).strip()
            if item.status not in ['draft','submitted','confirmed'] or not 1 <= len(reason) <= 1000:
                raise ValidationError('Supply a cancellation reason for an eligible record.')
            item.status, item.cancellation_reason = 'cancelled', reason
        else:
            raise ValidationError('Unsupported action.')
        item.version += 1
        item.save()
        audit(request.user, 'register.position_'+action, item.pk, version=item.version)
        return Response(PositionSerializer(item).data)
