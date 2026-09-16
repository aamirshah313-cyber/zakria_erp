from decimal import Decimal, ROUND_HALF_UP
from rest_framework import serializers
from .models import Company, Party, Document, DocumentLine, Role, Workflow
from .auth import PERMISSIONS

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = '__all__'
    def validate_accent(self, value):
        import re
        if not re.fullmatch(r'#[0-9a-fA-F]{6}', value):
            raise serializers.ValidationError('Use a six-digit hex colour.')
        return value

class PartySerializer(serializers.ModelSerializer):
    class Meta:
        model = Party
        fields = '__all__'

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = '__all__'
    def validate_permissions(self, value):
        if not isinstance(value, list) or any(not isinstance(p, str) or p not in PERMISSIONS for p in value):
            raise serializers.ValidationError('Select valid permissions.')
        if 'logs.export' in value and 'logs.view' not in value:
            raise serializers.ValidationError('Log export requires log view permission.')
        return sorted(set(value))

class WorkflowSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source='approver_role.name', read_only=True)
    class Meta:
        model = Workflow
        fields = '__all__'
        read_only_fields = ['version']
    def validate(self, data):
        role = data.get('approver_role', getattr(self.instance, 'approver_role', None))
        kind = data.get('kind', getattr(self.instance, 'kind', None))
        if role and f'{kind}.approve' not in role.permissions:
            raise serializers.ValidationError('The selected role needs approval permission for this document type.')
        return data

class LineSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentLine
        exclude = ['document']
        read_only_fields = ['amount', 'tax_amount']
    def validate(self, data):
        if data['quantity'] <= 0 or data['rate'] < 0 or not 0 <= data.get('tax_rate', 0) <= 100:
            raise serializers.ValidationError('Quantity must be positive; rate nonnegative; tax between 0 and 100.')
        return data

class DocumentSerializer(serializers.ModelSerializer):
    lines = LineSerializer(many=True)
    feedback = serializers.SerializerMethodField()
    party_name = serializers.CharField(source='party.name', read_only=True)
    owner_name = serializers.CharField(source='owner.username', read_only=True)
    class Meta:
        model = Document
        fields = ['id', 'kind', 'number', 'party', 'party_name', 'owner', 'owner_name', 'status', 'issue_date', 'due_date', 'reference', 'notes', 'tax_treatment', 'subtotal', 'tax_total', 'total', 'version', 'lines', 'feedback', 'created_at', 'updated_at', 'approved_at', 'issued_at']
        read_only_fields = ['number', 'owner', 'status', 'subtotal', 'tax_total', 'total', 'version', 'created_at', 'updated_at', 'approved_at', 'issued_at']
    def get_feedback(self, obj):
        # Operational correction instructions, not the restricted audit history.
        if obj.status not in ['returned', 'rejected']:
            return ''
        event = obj.approvalevent_set.filter(action__in=['return', 'reject']).order_by('-id').first()
        return event.comment if event else ''
    def validate(self, data):
        if not data.get('lines'):
            raise serializers.ValidationError('Add at least one line.')
        if len(data['lines']) > 200:
            raise serializers.ValidationError('A document can contain at most 200 lines.')
        if data.get('due_date') and data['due_date'] < data['issue_date']:
            raise serializers.ValidationError('Due/valid-until date cannot precede issue date.')
        if data['party'].kind not in ['customer', 'both'] or not data['party'].active:
            raise serializers.ValidationError('Select a customer or a party with both roles.')
        treatment = data.get('tax_treatment', 'unspecified')
        if treatment not in ['unspecified', 'exclusive', 'exempt', 'zero_rated']:
            raise serializers.ValidationError('Unsupported tax treatment.')
        if treatment != 'exclusive' and any(l.get('tax_rate', 0) for l in data['lines']):
            raise serializers.ValidationError('Tax rates require tax-exclusive treatment.')
        return data

def save_lines(document, lines):
    cent = Decimal('0.01')
    subtotal = tax = Decimal('0')
    document.lines.all().delete()
    for line in lines:
        amount = (line['quantity'] * line['rate']).quantize(cent, rounding=ROUND_HALF_UP)
        tax_amount = (amount * line.get('tax_rate', Decimal(0)) / 100).quantize(cent, rounding=ROUND_HALF_UP)
        if amount > Decimal('99999999999999.99'):
            raise serializers.ValidationError('Line amount exceeds the supported limit.')
        DocumentLine.objects.create(document=document, amount=amount, tax_amount=tax_amount, **line)
        subtotal += amount
        tax += tax_amount
    if subtotal + tax > Decimal('99999999999999.99'):
        raise serializers.ValidationError('Document total exceeds the supported limit.')
    document.subtotal, document.tax_total, document.total = subtotal, tax, subtotal + tax
    document.save()
