from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.Model):
    name = models.CharField(max_length=80, unique=True)
    description = models.CharField(max_length=250, blank=True)
    permissions = models.JSONField(default=list)


class User(AbstractUser):
    role = models.ForeignKey(Role, null=True, blank=True, on_delete=models.PROTECT)
    phone = models.CharField(max_length=40, blank=True)
    status = models.CharField(max_length=15, default='pending', choices=[('pending', 'Pending'), ('active', 'Active'), ('suspended', 'Suspended')])


class AccessSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    key_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)


class Company(models.Model):
    name = models.CharField(max_length=180, default='Muhammad Zakaria and Sons')
    address = models.TextField(blank=True)
    city = models.CharField(max_length=80, default='Islamabad')
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    ntn = models.CharField(max_length=40, blank=True)
    strn = models.CharField(max_length=40, blank=True)
    ftn = models.CharField(max_length=40, blank=True)
    bank_details = models.TextField(blank=True)
    footer = models.TextField(blank=True)
    accent = models.CharField(max_length=7, default='#176B61')


class Party(models.Model):
    name = models.CharField(max_length=180)
    kind = models.CharField(max_length=12, choices=[('customer', 'Customer'), ('supplier', 'Supplier'), ('both', 'Both'), ('contractor', 'Contractor'), ('employee', 'Employee'), ('other', 'Other')])
    entity_type = models.CharField(max_length=12, default='organization', choices=[('organization', 'Organization'), ('person', 'Person')])
    active = models.BooleanField(default=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    address = models.TextField(blank=True)
    ntn = models.CharField(max_length=40, blank=True)
    strn = models.CharField(max_length=40, blank=True)
    ftn = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Workflow(models.Model):
    kind = models.CharField(max_length=12, unique=True, choices=[('quotation', 'Quotation'), ('invoice', 'Invoice')])
    approver_role = models.ForeignKey(Role, on_delete=models.PROTECT)
    allow_self_approval = models.BooleanField(default=False)
    version = models.PositiveIntegerField(default=1)


class Document(models.Model):
    kind = models.CharField(max_length=12, choices=[('quotation', 'Quotation'), ('invoice', 'Invoice')])
    number = models.CharField(max_length=40, unique=True)
    party = models.ForeignKey(Party, on_delete=models.PROTECT)
    owner = models.ForeignKey(User, on_delete=models.PROTECT, related_name='documents')
    status = models.CharField(max_length=15, default='draft')
    issue_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    reference = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    tax_treatment = models.CharField(max_length=20, default='unspecified')
    subtotal = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    tax_total = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    version = models.PositiveIntegerField(default=1)
    workflow_snapshot = models.JSONField(default=dict)
    issued_snapshot = models.JSONField(default=dict)
    submitted_by = models.ForeignKey(User, null=True, on_delete=models.PROTECT, related_name='submissions')
    submitted_at = models.DateTimeField(null=True)
    approved_by = models.ForeignKey(User, null=True, on_delete=models.PROTECT, related_name='approvals')
    approved_at = models.DateTimeField(null=True)
    issued_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class DocumentLine(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='lines')
    description = models.CharField(max_length=1000)
    unit = models.CharField(max_length=30, default='Each')
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    rate = models.DecimalField(max_digits=14, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=16, decimal_places=2)


class ApprovalEvent(models.Model):
    document = models.ForeignKey(Document, on_delete=models.PROTECT)
    actor = models.ForeignKey(User, on_delete=models.PROTECT)
    action = models.CharField(max_length=30)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class AuditEvent(models.Model):
    actor = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=80)
    target = models.CharField(max_length=100)
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)


class SavedReport(models.Model):
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    definition = models.JSONField(default=dict)


class Account(models.Model):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=160)
    kind = models.CharField(max_length=12, choices=[(x, x.title()) for x in ['asset', 'liability', 'equity', 'income', 'expense']])
    active = models.BooleanField(default=True)
    is_cash = models.BooleanField(default=False)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT, related_name='children')
    is_group = models.BooleanField(default=False)


class Project(models.Model):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=160)
    reference = models.CharField(max_length=120, blank=True)
    active = models.BooleanField(default=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    client = models.ForeignKey(Party, null=True, blank=True, on_delete=models.PROTECT, related_name='contracts')
    location = models.CharField(max_length=250, blank=True)
    contact_name = models.CharField(max_length=180, blank=True)
    email = models.EmailField(blank=True)


class FinancialYear(models.Model):
    name = models.CharField(max_length=60, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()
    closed = models.BooleanField(default=False)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(end_date__gte=models.F('start_date')), name='financial_year_date_order')]


class FinanceSettings(models.Model):
    approver_role = models.ForeignKey(Role, null=True, on_delete=models.PROTECT)
    closed_through = models.DateField(null=True, blank=True)
    require_evidence = models.BooleanField(default=False)


class Voucher(models.Model):
    key = models.UUIDField(unique=True)
    date = models.DateField()
    kind = models.CharField(max_length=12, choices=[(x, x.title()) for x in ['payment', 'receipt', 'transfer', 'journal']])
    narration = models.CharField(max_length=1000)
    party_name = models.CharField(max_length=180, blank=True)
    handled_by = models.CharField(max_length=120, blank=True)
    method = models.CharField(max_length=20, blank=True)
    reference = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=12, default='draft')
    version = models.PositiveIntegerField(default=1)
    owner = models.ForeignKey(User, on_delete=models.PROTECT, related_name='vouchers')
    submitted_by = models.ForeignKey(User, null=True, on_delete=models.PROTECT, related_name='+')
    approver_role = models.ForeignKey(Role, null=True, on_delete=models.PROTECT)
    approved_by = models.ForeignKey(User, null=True, on_delete=models.PROTECT, related_name='+')
    posted_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    feedback = models.CharField(max_length=1000, blank=True)
    reversal_of = models.OneToOneField('self', null=True, on_delete=models.PROTECT, related_name='reversal')

    @property
    def number(self):
        return f'JV-{self.pk:06d}'


class JournalLine(models.Model):
    voucher = models.ForeignKey(Voucher, on_delete=models.CASCADE, related_name='lines')
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.PROTECT)
    debit = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=16, decimal_places=2, default=0)

    class Meta:
        constraints = [models.CheckConstraint(condition=(models.Q(debit__gt=0, credit=0) | models.Q(credit__gt=0, debit=0)), name='one_positive_journal_side')]


class Evidence(models.Model):
    voucher = models.ForeignKey(Voucher, on_delete=models.PROTECT, related_name='evidence')
    name = models.CharField(max_length=200)
    mime = models.CharField(max_length=40)
    content = models.BinaryField()
    digest = models.CharField(max_length=64)
    uploaded_by = models.ForeignKey(User, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)


class PasswordRecovery(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    digest = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class RecoveryLimit(models.Model):
    key = models.CharField(max_length=64, unique=True)
    window = models.DateTimeField()
    attempts = models.PositiveIntegerField(default=0)


class RegisterCategory(models.Model):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=160)
    active = models.BooleanField(default=True)
    description = models.CharField(max_length=500, blank=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT, related_name='children')


class RegisterSource(models.Model):
    name = models.CharField(max_length=160, unique=True)
    kind = models.CharField(max_length=8, choices=[('cash', 'Cash'), ('bank', 'Bank')])
    active = models.BooleanField(default=True)
    account_title = models.CharField(max_length=180, blank=True)
    bank = models.CharField(max_length=120, blank=True)
    branch = models.CharField(max_length=180, blank=True)
    account_number = models.CharField(max_length=40, blank=True)
    iban = models.CharField(max_length=34, blank=True)


class RegisterEntry(models.Model):
    request_key = models.UUIDField(unique=True)
    date = models.DateField()
    direction = models.CharField(max_length=8, choices=[('receipt', 'Receipt'), ('payment', 'Payment')])
    category = models.ForeignKey(RegisterCategory, on_delete=models.PROTECT)
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.PROTECT)
    source = models.ForeignKey(RegisterSource, on_delete=models.PROTECT)
    party = models.CharField(max_length=180)
    counterparty = models.ForeignKey(Party, null=True, blank=True, on_delete=models.PROTECT, related_name='register_entries')
    beneficiary = models.CharField(max_length=180, blank=True)
    reporting_class = models.CharField(max_length=16, default='unclassified', db_default='unclassified', choices=[('unclassified', 'Pending classification'), ('income', 'Income received'), ('expense', 'Expense paid'), ('other', 'Other funds movement')])
    nature = models.CharField(max_length=24, default='unclassified', choices=[(k, v) for k, v in [('unclassified', 'Pending classification'), ('operating', 'Operating receipt / payment'), ('advance', 'Advance'), ('loan', 'Loan principal'), ('deposit', 'Security / refundable deposit'), ('investment', 'Investment principal'), ('capital', 'Capital contribution / distribution'), ('donation', 'Donation')]])
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    method = models.CharField(max_length=20, choices=[(x, x.title()) for x in ['cash', 'transfer', 'cheque', 'card', 'other']])
    reference = models.CharField(max_length=120, blank=True)
    handled_by = models.CharField(max_length=120, blank=True)
    remarks = models.TextField(blank=True)
    status = models.CharField(max_length=12, default='draft')
    version = models.PositiveIntegerField(default=1)
    owner = models.ForeignKey(User, on_delete=models.PROTECT, related_name='+')
    approved_by = models.ForeignKey(User, null=True, on_delete=models.PROTECT, related_name='+')
    approver_role = models.ForeignKey(Role, null=True, on_delete=models.PROTECT, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True)
    cancellation_reason = models.CharField(max_length=1000, blank=True)
    cancelled_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(amount__gt=0), name='positive_register_amount')]


class RegisterRule(models.Model):
    approver_role = models.ForeignKey(Role, on_delete=models.PROTECT)


class RegisterAllocation(models.Model):
    entry = models.ForeignKey(RegisterEntry, on_delete=models.CASCADE, related_name='allocations')
    category = models.ForeignKey(RegisterCategory, on_delete=models.PROTECT)
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=16, decimal_places=2)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(amount__gt=0), name='positive_register_allocation')]


class RegisterAttachment(models.Model):
    # Each document supports exactly one receipt/payment entry or one opening/transfer.
    entry = models.ForeignKey(RegisterEntry, null=True, blank=True, on_delete=models.PROTECT, related_name='attachments')
    position = models.ForeignKey('RegisterPosition', null=True, blank=True, on_delete=models.PROTECT, related_name='attachments')
    name = models.CharField(max_length=180)
    mime = models.CharField(max_length=40)
    size = models.PositiveIntegerField()
    sha256 = models.CharField(max_length=64)
    content = models.BinaryField()
    uploaded_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='+')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    withdrawn_at = models.DateTimeField(null=True)
    withdrawal_reason = models.CharField(max_length=500, blank=True)

    class Meta:
        constraints = [models.CheckConstraint(
            condition=models.Q(entry__isnull=False, position__isnull=True) | models.Q(entry__isnull=True, position__isnull=False),
            name='register_attachment_single_record')]


class RegisterImport(models.Model):
    owner = models.ForeignKey(User, on_delete=models.PROTECT, related_name='+')
    filename = models.CharField(max_length=180)
    file_hash = models.CharField(max_length=64)
    sheet = models.CharField(max_length=100)
    header_row = models.PositiveIntegerField()
    headers = models.JSONField(default=list)
    rows = models.JSONField(default=list)
    warnings = models.JSONField(default=list)
    configuration = models.JSONField(default=dict)
    preview = models.JSONField(default=dict)
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=12, default='staged')
    created_at = models.DateTimeField(auto_now_add=True)
    imported_at = models.DateTimeField(null=True)


class RegisterImportOrigin(models.Model):
    batch = models.ForeignKey(RegisterImport, on_delete=models.PROTECT, related_name='origins')
    entry = models.OneToOneField(RegisterEntry, on_delete=models.PROTECT, related_name='import_origin')
    file_hash = models.CharField(max_length=64)
    sheet = models.CharField(max_length=100)
    source_row = models.PositiveIntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['file_hash', 'sheet', 'source_row'], name='unique_register_source_row')]


class RegisterReportTemplate(models.Model):
    owner = models.ForeignKey(User, on_delete=models.PROTECT, related_name='+')
    name = models.CharField(max_length=100)
    definition = models.JSONField(default=dict)
    active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['owner', 'name'], name='unique_register_report_name')]


class RegisterPosition(models.Model):
    """Reviewed register openings and own-account transfers; no GL postings."""
    request_key = models.UUIDField(unique=True)
    kind = models.CharField(max_length=12, choices=[('opening', 'Opening balance'), ('transfer', 'Internal transfer')])
    date = models.DateField()
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    side = models.CharField(max_length=8, default='receipt', choices=[('receipt', 'Receipt-side opening'), ('payment', 'Payment-side opening')])
    source = models.ForeignKey(RegisterSource, null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    destination = models.ForeignKey(RegisterSource, null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    category = models.ForeignKey(RegisterCategory, null=True, blank=True, on_delete=models.PROTECT)
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.PROTECT)
    counterparty = models.ForeignKey(Party, null=True, blank=True, on_delete=models.PROTECT)
    reference = models.CharField(max_length=180)
    remarks = models.CharField(max_length=2000)
    status = models.CharField(max_length=12, default='draft')
    version = models.PositiveIntegerField(default=1)
    owner = models.ForeignKey(User, on_delete=models.PROTECT, related_name='+')
    approver_role = models.ForeignKey(Role, null=True, on_delete=models.PROTECT, related_name='+')
    approved_by = models.ForeignKey(User, null=True, on_delete=models.PROTECT, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True)
    cancellation_reason = models.CharField(max_length=1000, blank=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(amount__gt=0), name='positive_register_position')]
