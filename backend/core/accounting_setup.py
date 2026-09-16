"""Accounting master data only. Financial posting is a separate milestone."""
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from .auth import permissions, audit
from .models import Account, Project, FinancialYear, JournalLine, Voucher


def authorize(user, write=False):
    # Access administrators can configure the new foundation without silently
    # receiving transaction, posting, evidence or audit-log privileges.
    allowed = {'finance.manage', 'roles.manage'}
    if not write:
        allowed.add('finance.view')
    if not permissions(user).intersection(allowed):
        raise PermissionDenied('Your role does not allow accounting setup access.')


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = '__all__'

    def validate(self, data):
        def value(key, default=None):
            return data.get(key, getattr(self.instance, key, default))
        parent = value('parent')
        if parent and (not parent.is_group or not parent.active):
            raise ValidationError('The parent must be an active account group.')
        if parent and parent.kind != value('kind'):
            raise ValidationError('Parent and child accounts must have the same classification.')
        seen = {self.instance.pk} if self.instance else set()
        ancestor = parent
        while ancestor:
            if ancestor.pk in seen:
                raise ValidationError('Account hierarchy cannot contain a cycle.')
            seen.add(ancestor.pk)
            ancestor = ancestor.parent
        if value('is_cash', False) and (value('kind') != 'asset' or value('is_group', False)):
            raise ValidationError('Cash/bank accounts must be individual asset accounts.')
        if self.instance:
            children = self.instance.children
            if children.exists() and (not value('is_group') or children.exclude(kind=value('kind')).exists()):
                raise ValidationError('Reassign child accounts before changing this group classification.')
            if not value('active') and children.filter(active=True).exists():
                raise ValidationError('Deactivate child accounts before deactivating their group.')
            if JournalLine.objects.filter(account=self.instance).exists():
                for key in ['kind', 'parent', 'is_group', 'is_cash', 'code']:
                    if value(key) != getattr(self.instance, key):
                        raise ValidationError('Used accounts cannot be reclassified or renumbered.')
        return data


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = '__all__'

    def validate(self, data):
        start = data.get('start_date', getattr(self.instance, 'start_date', None))
        end = data.get('end_date', getattr(self.instance, 'end_date', None))
        if start and end and end < start:
            raise ValidationError('End date cannot precede start date.')
        client = data.get('client')
        if client and not client.active:
            raise ValidationError('Select an active client.')
        return data


class FinancialYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialYear
        fields = '__all__'

    def validate(self, data):
        start = data.get('start_date', getattr(self.instance, 'start_date', None))
        end = data.get('end_date', getattr(self.instance, 'end_date', None))
        if start and end:
            if end < start:
                raise ValidationError('End date cannot precede start date.')
            years = FinancialYear.objects.filter(start_date__lte=end, end_date__gte=start)
            if self.instance:
                years = years.exclude(pk=self.instance.pk)
                if (start != self.instance.start_date or end != self.instance.end_date) and Voucher.objects.filter(date__range=(self.instance.start_date, self.instance.end_date)).exists():
                    raise ValidationError('A financial year containing vouchers cannot be redated.')
            if years.exists():
                raise ValidationError('Financial years cannot overlap.')
        return data


MASTERS = {'accounts': (Account, AccountSerializer), 'projects': (Project, ProjectSerializer), 'years': (FinancialYear, FinancialYearSerializer)}


class AccountingSetup(APIView):
    def get(self, request):
        authorize(request.user)
        return Response({key: serializer(model.objects.order_by('pk'), many=True).data for key, (model, serializer) in MASTERS.items()})

    @transaction.atomic
    def post(self, request, kind):
        authorize(request.user, write=True)
        if kind not in MASTERS and kind != 'template':
            raise ValidationError('Unknown accounting record type.')
        # Serialize setup mutations on the company row, including hierarchy
        # changes and financial-year overlap checks in PostgreSQL.
        from .models import Company
        get_object_or_404(Company.objects.select_for_update(), pk=1)
        if kind == 'template':
            if Account.objects.exists():
                raise ValidationError('The starter chart requires an empty Chart of Accounts. Existing accounts will not be overwritten.')
            groups = [('1000', 'Assets', 'asset'), ('2000', 'Liabilities', 'liability'), ('3000', 'Equity', 'equity'), ('4000', 'Income', 'income'), ('5000', 'Expenses', 'expense')]
            children = {
                'asset': [('1100', 'Cash on Hand'), ('1110', 'Petty Cash / Imprest'), ('1120', 'Bank Accounts', True), ('1200', 'Trade Receivables'), ('1210', 'Staff Advances'), ('1220', 'Supplier Advances'), ('1230', 'Loans Receivable'), ('1240', 'Refundable Deposits'), ('1300', 'Inventory'), ('1400', 'Property, Plant and Equipment', True), ('1490', 'Accumulated Depreciation', True)],
                'liability': [('2100', 'Trade Payables'), ('2200', 'Payroll Payable'), ('2210', 'Employee Reimbursements Payable'), ('2300', 'Customer Advances'), ('2400', 'Loans Payable'), ('2500', 'Tax and Other Statutory Payables', True)],
                'equity': [('3100', 'Share Capital'), ('3200', 'Retained Earnings')],
                'income': [('4100', 'Sales Revenue'), ('4200', 'Other Income')],
                'expense': [('5100', 'Cost of Sales'), ('5200', 'Employee Compensation', True), ('5300', 'Administrative Expenses', True), ('5400', 'Finance Costs'), ('5500', 'Depreciation Expense'), ('5600', 'Donations Paid')],
            }
            for code, name, classification in groups:
                parent = Account.objects.create(code=code, name=name, kind=classification, is_group=True)
                for row in children[classification]:
                    Account.objects.create(code=row[0], name=row[1], kind=classification, parent=parent, is_group=len(row) == 3, is_cash=row[0] in ['1100', '1110'])
            audit(request.user, 'accounting.chart_template_created', 'starter-chart')
            return Response({'message': 'Starter chart created. Review classifications and add individual bank/asset accounts before use.'}, status=201)
        model, serializer_class = MASTERS[kind]
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = serializer.save()
        audit(request.user, f'accounting.{kind}.created', record.pk)
        return Response(serializer.data, status=201)

    @transaction.atomic
    def patch(self, request, kind, pk):
        authorize(request.user, write=True)
        if kind not in MASTERS:
            raise ValidationError('Unknown accounting record type.')
        from .models import Company
        get_object_or_404(Company.objects.select_for_update(), pk=1)
        model, serializer_class = MASTERS[kind]
        record = get_object_or_404(model.objects.select_for_update(), pk=pk)
        serializer = serializer_class(record, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        audit(request.user, f'accounting.{kind}.updated', record.pk, fields=list(serializer.validated_data))
        return Response(serializer.data)
