from decimal import Decimal
from datetime import date
import csv
import io
from django.db import transaction
from django.db.models import Sum, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from .models import RegisterCategory, RegisterSource, RegisterEntry, RegisterRule, Project, Role, Company, Party, RegisterAllocation
from .serializers import PartySerializer
from .accounting_setup import ProjectSerializer
from .auth import require, audit, permissions
from .recovery import desktop_only


def dashboard_summary(user):
    from django.db.models.functions import TruncMonth
    confirmed = RegisterEntry.objects.filter(status='confirmed')
    receipts = confirmed.filter(direction='receipt').aggregate(value=Sum('amount'))['value'] or Decimal('0')
    payments = confirmed.filter(direction='payment').aggregate(value=Sum('amount'))['value'] or Decimal('0')
    today = timezone.localdate()
    months = []
    for offset in range(5, -1, -1):
        index = today.year * 12 + today.month - 1 - offset
        months.append(date(index // 12, index % 12 + 1, 1))
    totals = confirmed.filter(date__gte=months[0], date__lte=today).annotate(month=TruncMonth('date')).values('month', 'direction').annotate(amount=Sum('amount'))
    lookup = {(row['month'].strftime('%Y-%m'), row['direction']): row['amount'] for row in totals}
    series = [{'label': month.strftime('%b'), 'period': month.strftime('%Y-%m'), 'receipts': str(lookup.get((month.strftime('%Y-%m'), 'receipt'), 0)), 'payments': str(lookup.get((month.strftime('%Y-%m'), 'payment'), 0))} for month in months]
    # Use allocated amounts for split transactions, not their first category.
    from collections import defaultdict
    category_totals = defaultdict(lambda: Decimal('0'))
    for row in confirmed.filter(direction='payment', allocations__isnull=True).values('category__name').annotate(amount=Sum('amount')):
        category_totals[row['category__name']] += row['amount']
    for row in RegisterAllocation.objects.filter(entry__status='confirmed', entry__direction='payment').values('category__name').annotate(amount=Sum('amount')):
        category_totals[row['category__name']] += row['amount']
    categories = [{'category__name': name, 'amount': amount} for name, amount in sorted(category_totals.items(), key=lambda r: (-r[1], r[0]))]
    distribution = [{'label': row['category__name'], 'amount': str(row['amount'])} for row in categories[:5]]
    if len(categories) > 5:
        distribution.append({'label': 'Other categories', 'amount': str(sum(row['amount'] for row in categories[5:]))})
    pending = RegisterEntry.objects.none()
    if 'register.approve' in permissions(user):
        pending = RegisterEntry.objects.filter(status='submitted', approver_role=user.role).exclude(owner=user).order_by('date', 'pk')
    return {'receipts': f'{receipts:.2f}', 'payments': f'{payments:.2f}', 'net': f'{receipts-payments:.2f}', 'pending_count': pending.count(), 'pending': list(pending.values('id', 'date', 'direction', 'party', 'amount', 'version', 'owner__username')[:20]), 'monthly': series, 'categories': distribution}


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = RegisterCategory
        fields = '__all__'

    def validate(self, data):
        parent = data.get('parent', getattr(self.instance, 'parent', None))
        seen = {self.instance.pk} if self.instance else set()
        ancestor = parent
        while ancestor:
            if ancestor.pk in seen:
                raise ValidationError('Category hierarchy cannot contain a cycle.')
            seen.add(ancestor.pk)
            ancestor = ancestor.parent
        if parent and not parent.active:
            raise ValidationError('Select an active parent category.')
        if self.instance and data.get('active') is False and self.instance.children.filter(active=True).exists():
            raise ValidationError('Deactivate child categories first.')
        return data


class SourceSerializer(serializers.ModelSerializer):
    sensitive = ['account_title', 'bank', 'branch', 'account_number', 'iban']
    class Meta:
        model = RegisterSource
        fields = '__all__'

    def to_representation(self, instance):
        result = super().to_representation(instance)
        request = self.context.get('request')
        if not request or 'register.bank_details' not in permissions(request.user):
            for key in self.sensitive:
                result.pop(key, None)
        return result

    def validate(self, data):
        request = self.context.get('request')
        if any(key in data for key in self.sensitive) and (not request or 'register.bank_details' not in permissions(request.user)):
            raise PermissionDenied('Bank details require the designated bank-details permission.')
        kind = data.get('kind', getattr(self.instance, 'kind', None))
        if self.instance:
            from .models import RegisterPosition
            used = self.instance.registerentry_set.exists() or RegisterPosition.objects.filter(Q(source=self.instance) | Q(destination=self.instance)).exists()
            if used and kind != self.instance.kind:
                raise ValidationError('A used cash/bank account cannot change type.')
            if used and any(getattr(self.instance,k) and k in data and data[k] != getattr(self.instance,k) for k in ['account_number','iban']):
                raise ValidationError('Create a new bank account instead of replacing identifiers on an account with recorded activity.')
        if kind == 'cash' and any(data.get(k, getattr(self.instance, k, '')) for k in self.sensitive):
            raise ValidationError('Bank fields must be empty for a cash account.')
        if data.get('iban'):
            iban = ''.join(data['iban'].split()).upper()
            import re
            if not re.fullmatch(r'[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}', iban):
                raise ValidationError('Enter a valid IBAN, or leave it empty until verified.')
            digits = ''.join(str(ord(c)-55) if c.isalpha() else c for c in iban[4:]+iban[:4])
            if int(digits) % 97 != 1 or (iban.startswith('PK') and len(iban) != 24):
                raise ValidationError('IBAN length or checksum is invalid.')
            data['iban'] = iban
        return data


class AllocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegisterAllocation
        fields = ['category', 'project', 'amount']

    def validate(self, data):
        if data['amount'] <= 0 or not data['category'].active or (data.get('project') and not data['project'].active):
            raise ValidationError('Each allocation needs a positive amount and active category/project.')
        return data


class EntrySerializer(serializers.ModelSerializer):
    allocations = AllocationSerializer(many=True, required=False)
    import_source = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='category.name', read_only=True)
    source_name = serializers.CharField(source='source.name', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True, default='')
    counterparty_name = serializers.CharField(source='counterparty.name', read_only=True, default='')

    def get_import_source(self, obj):
        origin = getattr(obj, 'import_origin', None)
        return {'batch': origin.batch_id, 'filename': origin.batch.filename, 'sheet': origin.sheet, 'row': origin.source_row} if origin else None
    class Meta:
        model = RegisterEntry
        fields = '__all__'
        read_only_fields = ['owner', 'status', 'version', 'approved_by', 'approver_role', 'confirmed_at', 'cancelled_at', 'cancellation_reason', 'created_at']

    def validate(self, data):
        if data.get('amount', Decimal('0')) <= 0:
            raise ValidationError('Amount must be positive.')
        reporting_class = data.get('reporting_class', getattr(self.instance, 'reporting_class', 'unclassified'))
        if reporting_class in ['income', 'expense']:
            expected = 'receipt' if reporting_class == 'income' else 'payment'
            if data.get('direction') != expected or data.get('nature', 'unclassified') not in ['operating', 'donation']:
                raise ValidationError('Income requires a receipt and expense requires a payment, with Operating or Donation nature. Classify principal, advances and deposits as Other funds movement.')
        for key in ['category', 'source', 'project', 'counterparty']:
            record = data.get(key)
            if record and not record.active:
                raise ValidationError(f'Select an active {key}.')
        # The party text is a transaction snapshot. Selecting a master initially
        # fills the snapshot; later master renames do not rewrite recorded entries.
        party = data.get('counterparty')
        if party and not data.get('party', '').strip():
            data['party'] = party.name
        allocations = data.get('allocations')
        if allocations is not None:
            if not 1 <= len(allocations) <= 50 or sum(a['amount'] for a in allocations) != data['amount']:
                raise ValidationError('Use 1–50 allocation lines whose amounts equal the transaction total exactly.')
            data['category'] = allocations[0]['category']
            data['project'] = allocations[0].get('project')
        elif self.instance and self.instance.allocations.exists():
            raise ValidationError('Include all allocation lines when editing this draft.')
        from .register_positions import check_cutoffs
        check_cutoffs(data['date'], data['source'], data.get('category'), data.get('project'), data.get('counterparty'), allocations or ())
        return data

    def create(self, data):
        allocations = data.pop('allocations', None)
        entry = super().create(data)
        if allocations:
            RegisterAllocation.objects.bulk_create([RegisterAllocation(entry=entry, **a) for a in allocations])
        return entry

    def update(self, instance, data):
        allocations = data.pop('allocations', None)
        entry = super().update(instance, data)
        if allocations is not None:
            entry.allocations.all().delete()
            RegisterAllocation.objects.bulk_create([RegisterAllocation(entry=entry, **a) for a in allocations])
        return entry


class RegisterMasters(APIView):
    def get(self, request):
        desktop_only()
        if not permissions(request.user).intersection({'register.view', 'register.manage'}):
            raise PermissionDenied()
        rule = RegisterRule.objects.filter(pk=1).first()
        return Response({'categories': CategorySerializer(RegisterCategory.objects.order_by('code'), many=True).data,
                         'sources': SourceSerializer(RegisterSource.objects.order_by('name'), many=True, context={'request': request}).data,
                         'parties': PartySerializer(Party.objects.order_by('name', 'pk'), many=True).data,
                         'natures': list(RegisterEntry._meta.get_field('nature').choices),
                         'projects': ProjectSerializer(Project.objects.order_by('code'), many=True).data,
                         'approver_role': rule.approver_role_id if rule else None,
                         'roles': list(Role.objects.values('id', 'name')) if 'register.manage' in permissions(request.user) else [],
                         'today': timezone.localdate().isoformat()})

    @transaction.atomic
    def post(self, request, kind):
        desktop_only()
        require(request.user, 'register.manage')
        get_object_or_404(Company.objects.select_for_update(), pk=1)
        if kind == 'rule':
            role = get_object_or_404(Role, pk=request.data.get('approver_role'))
            if 'register.approve' not in role.permissions:
                raise ValidationError('The selected role needs register approval permission.')
            RegisterRule.objects.update_or_create(pk=1, defaults={'approver_role': role})
            audit(request.user, 'register.approval_rule_changed', role.pk)
            return Response({'message': 'Approval role updated for new submissions.'})
        choices = {'categories': (RegisterCategory, CategorySerializer), 'sources': (RegisterSource, SourceSerializer), 'projects': (Project, ProjectSerializer), 'parties': (Party, PartySerializer)}
        if kind not in choices:
            raise ValidationError('Unknown register setup record.')
        model, serializer_type = choices[kind]
        instance = get_object_or_404(model, pk=request.data['id']) if request.data.get('id') else None
        serializer = serializer_type(instance, data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        audit(request.user, 'register.master_updated' if instance else 'register.master_created', f'{kind}:{obj.pk}')
        return Response(serializer.data, status=200 if instance else 201)


class Entries(APIView):
    def get(self, request):
        desktop_only()
        require(request.user, 'register.view')
        try:
            page = max(1, int(request.query_params.get('page', 1)))
        except ValueError:
            raise ValidationError('Invalid page.')
        query = RegisterEntry.objects.exclude(status='deleted').select_related('category', 'source', 'project', 'import_origin__batch').order_by('-date', '-pk')
        return Response({'count': query.count(), 'page': page, 'rows': EntrySerializer(query[(page-1)*100:page*100], many=True).data})

    @transaction.atomic
    def post(self, request):
        desktop_only()
        require(request.user, 'register.create')
        get_object_or_404(Company.objects.select_for_update(), pk=1)
        serializer = EntrySerializer(data=request.data)
        # Disable serializer's unique validator only for explicit idempotent retry handling.
        serializer.fields['request_key'].validators = []
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        previous = RegisterEntry.objects.filter(request_key=values['request_key']).first()
        if previous:
            if previous.owner_id != request.user.pk:
                raise PermissionDenied()
            for key, value in values.items():
                stored = list(previous.allocations.order_by('pk').values('category_id', 'project_id', 'amount')) if key == 'allocations' else getattr(previous, key)
                if key == 'allocations':
                    value = [{'category_id': a['category'].pk, 'project_id': a['project'].pk if a.get('project') else None, 'amount': a['amount']} for a in value]
                if stored != value:
                    raise ValidationError('This request reference was already used for different content.')
            return Response(EntrySerializer(previous).data)
        obj = serializer.save(owner=request.user)
        audit(request.user, 'register.draft_created', obj.pk)
        return Response(serializer.data, status=201)


class EntryAction(APIView):
    @transaction.atomic
    def put(self, request, pk):
        desktop_only()
        require(request.user, 'register.create')
        get_object_or_404(Company.objects.select_for_update(), pk=1)
        obj = get_object_or_404(RegisterEntry.objects.select_for_update(), pk=pk)
        if obj.owner_id != request.user.pk or obj.status != 'draft' or request.data.get('version') != obj.version:
            raise ValidationError('Only your current draft can be edited.')
        payload = dict(request.data)
        payload['request_key'] = str(obj.request_key)
        serializer = EntrySerializer(obj, data=payload)
        serializer.is_valid(raise_exception=True)
        serializer.save(version=obj.version + 1)
        audit(request.user, 'register.draft_updated', obj.pk)
        return Response(serializer.data)

    @transaction.atomic
    def post(self, request, pk):
        desktop_only()
        require(request.user, 'register.view')
        get_object_or_404(Company.objects.select_for_update(), pk=1)
        obj = get_object_or_404(RegisterEntry.objects.select_for_update(), pk=pk)
        if request.data.get('version') != obj.version:
            raise ValidationError('Record changed. Refresh before trying again.')
        action = request.data.get('action')
        if action == 'submit':
            require(request.user, 'register.create')
            if obj.owner_id != request.user.pk or obj.status != 'draft':
                raise ValidationError('Only the preparer can submit a draft.')
            rule = RegisterRule.objects.filter(pk=1).first()
            if not rule:
                raise ValidationError('Configure the register approval role first.')
            obj.approver_role = rule.approver_role
            obj.status = 'submitted'
        elif action in ['confirm', 'return']:
            require(request.user, 'register.approve')
            if obj.status != 'submitted' or obj.owner_id == request.user.pk or obj.approver_role_id != request.user.role_id:
                raise PermissionDenied('Only the assigned approval role can review another preparer\'s submission.')
            if action == 'confirm':
                if not obj.category.active or not obj.source.active or (obj.project_id and not obj.project.active) or (obj.counterparty_id and not obj.counterparty.active):
                    raise ValidationError('Reactivate or correct the selected master records before confirmation.')
                allocations = list(obj.allocations.select_related('category', 'project'))
                if allocations and (sum(a.amount for a in allocations) != obj.amount or any(not a.category.active or (a.project_id and not a.project.active) for a in allocations)):
                    raise ValidationError('Correct inactive or unbalanced allocation lines before confirmation.')
                from .register_positions import check_cutoffs
                check_cutoffs(obj.date, obj.source, obj.category, obj.project, obj.counterparty, allocations)
                obj.status, obj.approved_by, obj.confirmed_at = 'confirmed', request.user, timezone.now()
            else:
                obj.status = 'draft'
        elif action == 'cancel':
            require(request.user, 'register.cancel')
            reason = str(request.data.get('reason', '')).strip()
            if obj.status not in ['draft', 'submitted', 'confirmed'] or not reason or len(reason) > 1000:
                raise ValidationError('Cancellation needs an eligible entry and a reason of 1–1000 characters.')
            obj.status, obj.cancellation_reason, obj.cancelled_at = 'cancelled', reason, timezone.now()
        else:
            raise ValidationError('Unsupported action.')
        obj.version += 1
        obj.save()
        audit(request.user, f'register.{action}', obj.pk, version=obj.version)
        return Response(EntrySerializer(obj).data)


class ActivityLedger(APIView):
    def get(self, request):
        desktop_only()
        require(request.user, 'register.view')
        from .register_reports import build_report, csv_bytes
        definition = {'from': request.query_params.get('from', ''), 'to': request.query_params.get('to', ''), 'columns': ['reference','date','party','category','project','source','receipt','payment','transfer_in','transfer_out','balance','remarks']}
        for key in ['category','source','project','counterparty']:
            if request.query_params.get(key):
                try:
                    definition[key] = int(request.query_params[key])
                except ValueError:
                    raise ValidationError('Invalid ledger filter.')
        if definition.get('project') and not definition.get('source'):
            definition['balance_basis'] = 'payments_less_receipts'
            definition['title'] = 'Project Activity Statement'
        report = build_report(definition, request.user.username)
        if request.query_params.get('export') == 'csv':
            require(request.user, 'register.export')
            audit(request.user, 'register.ledger_exported', 'csv', count=report['count'])
            response = HttpResponse(csv_bytes(report), content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = 'attachment; filename="register-ledger.csv"'
            return response
        return Response(report)
