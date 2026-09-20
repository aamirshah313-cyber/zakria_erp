r"""Build the worked example used by docs/manual from a throwaway database.

Creates a temporary desktop data folder, drives the real API with the same
endpoints the application calls, and writes the responses and exported files to
docs/manual/examples/. Business data is never read or changed: the folder is
created under the system temporary directory and deleted at the end.

Run after adding features so the manual keeps matching the build:

    .\.venv\Scripts\python.exe scripts\build_manual_examples.py
"""
import json
import os
import secrets
import shutil
import sys
import tempfile
import uuid
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/manual/examples'
DATA = Path(tempfile.mkdtemp(prefix='zakaria-manual-'))
(DATA / 'evidence').mkdir(parents=True, exist_ok=True)
(DATA / 'backups').mkdir(parents=True, exist_ok=True)
(DATA / 'service-secret.txt').write_text(secrets.token_urlsafe(48), encoding='utf-8')
os.environ['ERP_DESKTOP_DATA_DIR'] = str(DATA)
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.desktop'
sys.path.insert(0, str(ROOT / 'backend'))

import django  # noqa: E402

django.setup()
from django.core.management import call_command  # noqa: E402
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402
from rest_framework.test import APIClient  # noqa: E402

call_command('migrate', interactive=False, verbosity=0)

ADMIN, PREPARER, APPROVER, AUDITOR = 'zakaria.admin', 'finance.officer', 'general.manager', 'audit.reviewer'
PASSWORDS = {name: f'Example-passphrase-{i}9741!' for i, name in enumerate([ADMIN, PREPARER, APPROVER, AUDITOR])}
CASH_PNG = bytes.fromhex(
    '89504e470d0a1a0a0000000d4948445200000010000000100802000000900691'
    'e80000001b4944415438cb63fcffff3f032580891a18a9c4c8c0c8000000ffff'
    '030018f70b9d7d5a4a3d0000000049454e44ae426082')
saved = []


def keep(name, payload, note=''):
    """Write one example file and record it for the index."""
    path = OUT / name
    if isinstance(payload, (dict, list)):
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str) + '\n', encoding='utf-8')
    elif isinstance(payload, str):
        path.write_text(payload, encoding='utf-8')
    else:
        path.write_bytes(payload)
    saved.append((name, path.stat().st_size, note))
    print(f'  {name} ({path.stat().st_size:,} bytes)')
    return payload


class Session:
    """One signed-in user, driving the same endpoints as the application."""

    def __init__(self, username=None):
        self.client = APIClient(SERVER_NAME='127.0.0.1')
        self.username = username
        if username:
            result = self.post('/api/auth/login/', {'username': username, 'password': PASSWORDS[username]})
            self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + result['token'])

    def call(self, method, path, body=None, expect=(200, 201), **kwargs):
        response = getattr(self.client, method)(path, body, **kwargs) if body is not None else getattr(self.client, method)(path, **kwargs)
        if expect and response.status_code not in expect:
            raise SystemExit(f'{method.upper()} {path} returned {response.status_code}: {getattr(response, "data", response.content[:400])}')
        if response['Content-Type'].startswith('application/json'):
            return response.data
        return b''.join(response.streaming_content) if response.streaming else response.content

    def get(self, path, **kwargs):
        return self.call('get', path, **kwargs)

    def post(self, path, body, **kwargs):
        return self.call('post', path, body, format=kwargs.pop('format', 'json'), **kwargs)

    def patch(self, path, body, **kwargs):
        return self.call('patch', path, body, format='json', **kwargs)

    def put(self, path, body, **kwargs):
        return self.call('put', path, body, format='json', **kwargs)

    def refused(self, method, path, body=None, **kwargs):
        """Capture a rejection: the rules are part of the documented behaviour."""
        response = getattr(self.client, method)(path, body, format=kwargs.pop('format', 'json'), **kwargs) if body is not None else getattr(self.client, method)(path)
        if response.status_code < 400:
            raise SystemExit(f'{method.upper()} {path} was expected to be refused but returned {response.status_code}')
        return {'request': f'{method.upper()} {path}', 'body': body, 'status': response.status_code, 'response': response.data}


print('Building the example dataset…')
anonymous = Session()
keep('01-health.json', anonymous.get('/api/health/'), 'Service identity and mode')
keep('02-first-run-required.json', anonymous.get('/api/setup/'), 'First-run check before any account exists')
keep('03-first-run-setup.json', anonymous.post('/api/setup/', {
    'username': ADMIN, 'email': 'admin@example.com', 'first_name': 'Zakaria', 'last_name': 'Administrator',
    'password': PASSWORDS[ADMIN], 'confirm_password': PASSWORDS[ADMIN]}), 'Creating the first administrator')

admin = Session(ADMIN)
for name, email in [(PREPARER, 'finance@example.com'), (APPROVER, 'gm@example.com'), (AUDITOR, 'audit@example.com')]:
    anonymous.post('/api/auth/register/', {'username': name, 'email': email, 'password': PASSWORDS[name]})
roles = {row['name']: row['id'] for row in admin.get('/api/roles/')['roles']}
keep('04-roles-and-permissions.json', admin.get('/api/roles/'), 'Default roles and the permission catalogue')
accounts = {PREPARER: 'Finance Manager', APPROVER: 'General Manager', AUDITOR: 'Audit Reviewer'}
from core.models import User  # noqa: E402

for username, role in accounts.items():
    user = User.objects.get(username=username)
    result = admin.patch(f'/api/users/{user.pk}/', {'status': 'active', 'role': roles[role]})
    if username == PREPARER:
        keep('05-user-activated.json', result, 'Activating an account and assigning its role')
keep('06-users.json', admin.get('/api/users/'), 'All accounts with their effective permissions')

admin.patch('/api/company/', {
    'name': 'Muhammad Zakaria and Sons', 'city': 'Islamabad',
    'address': 'Example Plaza, Blue Area, Islamabad', 'phone': '051-0000000',
    'email': 'accounts@example.com', 'ntn': '0000000-0', 'strn': '00-00-0000-000-00',
    'footer': 'Example data only — not real company records.'})
keep('07-company.json', admin.get('/api/company/'), 'Company details used on report headers')

print('Register setup…')
masters = {}
for code, name, description in [
        ('CLIENT', 'Client receipts', 'Money received from customers against work done'),
        ('MAT', 'Materials', 'Cement, steel, sanitary and electrical purchases'),
        ('LAB', 'Labour and wages', 'Daily wages, contractor payments'),
        ('FUEL', 'Fuel and transport', 'Vehicle fuel, delivery charges'),
        ('OFF', 'Office and administration', 'Rent, utilities, stationery')]:
    masters[code] = admin.post('/api/register/masters/categories/', {'code': code, 'name': name, 'description': description, 'active': True})
keep('08-category.json', masters['MAT'], 'One category as stored')

cash = admin.post('/api/register/masters/sources/', {'name': 'Main cash box', 'kind': 'cash', 'active': True})
bank = admin.post('/api/register/masters/sources/', {
    'name': 'Bank current account', 'kind': 'bank', 'active': True, 'account_title': 'Muhammad Zakaria and Sons',
    'bank': 'Example Bank Limited', 'branch': 'Blue Area, Islamabad', 'account_number': '0123456789',
    'iban': 'PK36SCBL0000001123456702'})
keep('09-bank-source.json', bank, 'A bank account; identifiers need register.bank_details')

fitout = admin.post('/api/register/masters/projects/', {'code': 'PRJ-001', 'name': 'G-11 Markaz office fit-out', 'reference': 'PO-2026-114', 'active': True, 'start_date': '2026-07-01'})
wall = admin.post('/api/register/masters/projects/', {'code': 'PRJ-002', 'name': 'Boundary wall — Phase II', 'reference': 'PO-2026-128', 'active': True, 'start_date': '2026-08-01'})
customer = admin.post('/api/register/masters/parties/', {'name': 'Capital Builders (Pvt) Ltd', 'kind': 'customer', 'entity_type': 'organization', 'active': True, 'phone': '051-1111111'})
supplier = admin.post('/api/register/masters/parties/', {'name': 'Al-Rehman Traders', 'kind': 'supplier', 'entity_type': 'organization', 'active': True})
labour = admin.post('/api/register/masters/parties/', {'name': 'Riaz Masood', 'kind': 'contractor', 'entity_type': 'person', 'active': True})
admin.post('/api/register/masters/rule/', {'approver_role': roles['General Manager']})
keep('10-register-setup.json', admin.get('/api/register/masters/'), 'Everything the entry form offers')

print('Openings, receipts and payments…')
preparer, approver = Session(PREPARER), Session(APPROVER)


def submit_and_confirm(path, record, actor=preparer, reviewer=approver):
    submitted = actor.post(path, {'action': 'submit', 'version': record['version']})
    return reviewer.post(path, {'action': 'confirm', 'version': submitted['version']})


opening = preparer.post('/api/register/positions/', {
    'request_key': str(uuid.uuid4()), 'kind': 'opening', 'date': '2026-07-01', 'amount': '350000.00',
    'side': 'receipt', 'source': cash['id'], 'reference': 'Counted cash at 1 July 2026',
    'remarks': 'Opening cash counted and signed by the accountant and the general manager.'})
keep('11-opening-draft.json', opening, 'Opening balance as prepared')
opening = submit_and_confirm(f'/api/register/positions/{opening["id"]}/', opening)
keep('12-opening-confirmed.json', opening, 'The same opening after review')

entries = []
plan = [
    ('2026-07-04', 'receipt', 'CLIENT', cash, 'Capital Builders (Pvt) Ltd', '400000.00', 'cheque', 'CHQ-884120', 'income', 'operating', fitout, customer, 'First running bill against PO-2026-114.'),
    ('2026-07-06', 'payment', 'MAT', cash, 'Al-Rehman Traders', '135500.00', 'cash', 'INV-2291', 'expense', 'operating', fitout, supplier, 'Cement and sanitary items for the fit-out.'),
    ('2026-07-18', 'payment', 'LAB', cash, 'Riaz Masood', '86000.00', 'cash', 'WS-07-3', 'expense', 'operating', fitout, labour, 'Weekly wages for eight workers.'),
    ('2026-08-02', 'receipt', 'CLIENT', bank, 'Capital Builders (Pvt) Ltd', '650000.00', 'transfer', 'IBFT-77120', 'income', 'operating', wall, customer, 'Mobilisation advance for the boundary wall.'),
    ('2026-08-09', 'payment', 'FUEL', cash, 'Attock filling station', '24300.00', 'cash', 'FS-1180', 'expense', 'operating', wall, None, 'Fuel for the site pickup.'),
    ('2026-08-23', 'payment', 'OFF', bank, 'Example Utilities', '38750.00', 'transfer', 'UTIL-08', 'expense', 'operating', None, None, 'Office electricity for August.'),
    ('2026-09-05', 'payment', 'LAB', cash, 'Riaz Masood', '94000.00', 'cash', 'WS-09-1', 'expense', 'operating', wall, labour, 'Wages for the wall foundation week.'),
]
for date, direction, category, source, party, amount, method, reference, klass, nature, project, counterparty, remarks in plan:
    draft = preparer.post('/api/register/entries/', {
        'request_key': str(uuid.uuid4()), 'date': date, 'direction': direction, 'category': masters[category]['id'],
        'source': source['id'], 'party': party, 'amount': amount, 'method': method, 'reference': reference,
        'reporting_class': klass, 'nature': nature, 'handled_by': 'Site office',
        'project': project['id'] if project else None, 'counterparty': counterparty['id'] if counterparty else None,
        'remarks': remarks})
    if date == '2026-07-04':
        keep('13-receipt-draft.json', draft, 'A prepared receipt before submission')
    entries.append(submit_and_confirm(f'/api/register/entries/{draft["id"]}/action/', draft))
keep('14-receipt-confirmed.json', entries[0], 'The same receipt after confirmation')

split = preparer.post('/api/register/entries/', {
    'request_key': str(uuid.uuid4()), 'date': '2026-09-12', 'direction': 'payment', 'source': bank['id'],
    'party': 'Al-Rehman Traders', 'counterparty': supplier['id'], 'amount': '300000.00', 'method': 'transfer',
    'reference': 'INV-2450', 'reporting_class': 'expense', 'nature': 'operating', 'handled_by': 'Head office',
    'remarks': 'One supplier bill covering both sites; split by delivery challan.',
    'category': masters['MAT']['id'],
    'allocations': [
        {'category': masters['MAT']['id'], 'project': fitout['id'], 'amount': '180000.00'},
        {'category': masters['MAT']['id'], 'project': wall['id'], 'amount': '120000.00'}]})
keep('15-split-payment-draft.json', split, 'One payment split across two projects')
split = submit_and_confirm(f'/api/register/entries/{split["id"]}/action/', split)
entries.append(split)

pending = preparer.post('/api/register/entries/', {
    'request_key': str(uuid.uuid4()), 'date': '2026-09-19', 'direction': 'payment', 'category': masters['OFF']['id'],
    'source': cash['id'], 'party': 'Blue Area Stationers', 'amount': '12400.00', 'method': 'cash',
    'reference': 'BILL-556', 'reporting_class': 'expense', 'nature': 'operating', 'handled_by': 'Site office',
    'remarks': 'Printing and stationery for the site office.'})
pending = preparer.post(f'/api/register/entries/{pending["id"]}/action/', {'action': 'submit', 'version': pending['version']})
keep('16-entry-awaiting-approval.json', pending, 'A submission waiting for the reviewer')
returned = approver.post(f'/api/register/entries/{pending["id"]}/action/', {'action': 'return', 'version': pending['version'], 'reason': 'Attach the bill first.'})
keep('17-entry-returned.json', returned, 'Returned to the preparer for correction')

print('Supporting documents…')
uploaded = preparer.post(f'/api/register/entries/{returned["id"]}/attachments/',
                         {'file': SimpleUploadedFile('stationery-bill.png', CASH_PNG, 'image/png'), 'version': str(returned['version'])},
                         format='multipart')
keep('18-attachment-uploaded.json', uploaded, 'Attaching a scanned bill to a draft')
keep('19-attachment-list.json', preparer.get(f'/api/register/entries/{returned["id"]}/attachments/'), 'Documents on that record')
current = preparer.get('/api/register/entries/')['rows']
current = next(row for row in current if row['id'] == returned['id'])
resubmitted = preparer.post(f'/api/register/entries/{returned["id"]}/action/', {'action': 'submit', 'version': current['version']})
entries.append(approver.post(f'/api/register/entries/{returned["id"]}/action/', {'action': 'confirm', 'version': resubmitted['version']}))

print('Internal transfer…')
transfer = preparer.post('/api/register/positions/', {
    'request_key': str(uuid.uuid4()), 'kind': 'transfer', 'date': '2026-09-15', 'amount': '150000.00',
    'source': cash['id'], 'destination': bank['id'], 'reference': 'DEP-9912',
    'remarks': 'Cash banked after the September collection.'})
transfer = submit_and_confirm(f'/api/register/positions/{transfer["id"]}/', transfer)
keep('20-transfer-confirmed.json', transfer, 'Own-account transfer, cash to bank')
keep('21-positions-list.json', preparer.get('/api/register/positions/'), 'Openings and transfers with document counts')

print('Cancellation…')
mistake = preparer.post('/api/register/entries/', {
    'request_key': str(uuid.uuid4()), 'date': '2026-09-08', 'direction': 'payment', 'category': masters['FUEL']['id'],
    'source': cash['id'], 'party': 'Attock filling station', 'amount': '24300.00', 'method': 'cash',
    'reference': 'FS-1180', 'reporting_class': 'expense', 'nature': 'operating', 'handled_by': 'Site office',
    'remarks': 'Duplicate of the 9 August fuel payment, recorded twice by mistake.'})
mistake = submit_and_confirm(f'/api/register/entries/{mistake["id"]}/action/', mistake)
keep('22-entry-cancelled.json', admin.post(f'/api/register/entries/{mistake["id"]}/action/', {
    'action': 'cancel', 'version': mistake['version'],
    'reason': 'Duplicate of REG-000005 (fuel, 9 August). Cancelled after checking the filling-station slip.'}),
     'Cancelling a confirmed entry keeps it in history')

print('Spreadsheet import…')
csv_text = ('Date,Description,Category,Cash/bank,Paid,Received,Voucher,How paid\n'
            '2026-09-22,Capital Builders (Pvt) Ltd,Client receipts,Bank current account,,275000.00,IBFT-81004,transfer\n'
            '2026-09-24,Al-Rehman Traders,Materials,Main cash box,64200.00,,INV-2477,cash\n'
            '2026-09-26,Riaz Masood,Labour and wages,Main cash box,71000.00,,WS-09-4,cash\n'
            'TOTAL,,,,135200.00,275000.00,,\n')
keep('23-import-source.csv', csv_text, 'The spreadsheet used for the import example')
inspected = preparer.post('/api/register/imports/inspect/', {'file': SimpleUploadedFile('september-cash-book.csv', csv_text.encode(), 'text/csv')}, format='multipart')
keep('24-import-inspect.json', inspected, 'What the application reads before staging')
batch = preparer.post('/api/register/imports/', {'file': SimpleUploadedFile('september-cash-book.csv', csv_text.encode(), 'text/csv'), 'sheet': 'CSV', 'header_row': '1'}, format='multipart')
configuration = {
    'columns': {'date': 0, 'party': 1, 'category': 2, 'source': 3, 'payment': 4, 'receipt': 5, 'reference': 6, 'method': 7},
    'defaults': {}, 'amount_mode': 'separate', 'date_format': 'iso',
    'control_receipt': '275000.00', 'control_payment': '135200.00',
    'exclude': {'5': 'Spreadsheet control total row, not a transaction.'}}
reviewed = preparer.post(f'/api/register/imports/{batch["id"]}/', {'action': 'preview', 'version': batch['version'], 'configuration': configuration})
keep('25-import-preview.json', reviewed, 'Row-by-row preview with control totals')
imported = preparer.post(f'/api/register/imports/{batch["id"]}/', {'action': 'commit', 'version': reviewed['version'], 'acknowledge': True})
keep('26-import-committed.json', {k: v for k, v in imported.items() if k != 'rows'}, 'Imported batch and the drafts it created')
for row in imported['entries']:
    draft = next(r for r in preparer.get('/api/register/entries/')['rows'] if r['id'] == row['entry_id'])
    submit_and_confirm(f'/api/register/entries/{draft["id"]}/action/', draft)

print('Dashboard, ledger and reports…')
waiting = preparer.post('/api/register/entries/', {
    'request_key': str(uuid.uuid4()), 'date': '2026-09-20', 'direction': 'payment', 'category': masters['FUEL']['id'],
    'source': cash['id'], 'party': 'Attock filling station', 'amount': '18600.00', 'method': 'cash',
    'reference': 'FS-1226', 'reporting_class': 'expense', 'nature': 'operating', 'handled_by': 'Site office',
    'remarks': 'Fuel for the week; waiting for the general manager to review.'})
preparer.post(f'/api/register/entries/{waiting["id"]}/action/', {'action': 'submit', 'version': waiting['version']})
keep('27-dashboard.json', approver.get('/api/dashboard/'), 'Reviewer dashboard, including what is waiting')
keep('28-entries-list.json', preparer.get('/api/register/entries/'), 'The register list as the application loads it')
keep('29-ledger.json', preparer.get('/api/register/ledger/?from=2026-07-01&to=2026-09-30'), 'Activity ledger for the quarter')
keep('30-ledger.csv', preparer.get('/api/register/ledger/?from=2026-07-01&to=2026-09-30&export=csv'), 'The same ledger exported')

definition = {
    'title': 'Transaction activity — July to September 2026', 'period': 'custom', 'from': '2026-07-01', 'to': '2026-09-30',
    'columns': ['date', 'reference', 'party', 'category', 'project', 'source', 'receipt', 'payment', 'balance'],
    'group': 'month', 'view': 'detail', 'accent': '#176B61', 'chart': True, 'paper': 'A4', 'orientation': 'landscape',
    'header': 'Example data generated by scripts/build_manual_examples.py',
    'footer': 'Example data only — not company accounts.'}
keep('31-report-detail.json', preparer.post('/api/register/reports/', dict(definition)), 'Statement rows, totals and the basis note')
summary = dict(definition, view='summary', group='project', title='Movement by project — July to September 2026')
keep('32-report-by-project.json', preparer.post('/api/register/reports/', summary), 'Grouped summary by project')
for fmt, name in [('pdf', '33-register-report.pdf'), ('xlsx', '34-register-report.xlsx'), ('png', '35-register-report.png'), ('csv', '36-register-report.csv')]:
    keep(name, preparer.post('/api/register/reports/', dict(definition, format=fmt)), f'Exported {fmt.upper()}')
keep('37-saved-report.json', preparer.post('/api/register/report-templates/', {'name': 'Quarterly activity', 'definition': definition}), 'A saved report layout')
cash_only = dict(definition, source=cash['id'], title='Main cash box — July to September 2026')
keep('37a-report-cash-account.json', preparer.post('/api/register/reports/', cash_only), 'One cash account, where the approved opening applies')
keep('37b-project-statement.json', preparer.get(f'/api/register/ledger/?project={fitout["id"]}&from=2026-07-01&to=2026-09-30'), 'Project statement: payments less receipts')

print('Data management, audit log and backup…')
spare = preparer.post('/api/register/entries/', {
    'request_key': str(uuid.uuid4()), 'date': '2026-09-28', 'direction': 'payment', 'category': masters['OFF']['id'],
    'source': cash['id'], 'party': 'Typing error', 'amount': '100.00', 'method': 'cash',
    'reporting_class': 'expense', 'nature': 'operating', 'remarks': 'Draft created by mistake.'})
keep('38-data-management.json', admin.get('/api/register/data-management/?kind=entries'), 'Drafts and their allowed actions')
listing = admin.get('/api/register/data-management/?kind=entries')
row = next(r for r in listing['rows'] if r['id'] == spare['id'])
keep('39-draft-removed.json', admin.post('/api/register/data-management/', {
    'kind': 'entries', 'id': spare['id'], 'action': 'remove', 'revision': row['revision'],
    'reason': 'Created by mistake while testing; no financial effect.'}), 'Removing a draft, with its reason')

auditor = Session(AUDITOR)
keep('40-audit-log.json', auditor.get('/api/logs/')[:40], 'Most recent audit events (first 40)')
keep('41-audit-log.csv', auditor.get('/api/logs/?export=csv'), 'The audit log exported')

backup = admin.post('/api/system/backups/', {'password': '', 'confirm_password': ''})
(OUT / '42-backup-example.zerp-backup').write_bytes(backup)
saved.append(('42-backup-example.zerp-backup', len(backup), 'A complete backup of this example data'))
import zipfile  # noqa: E402
import io  # noqa: E402

with zipfile.ZipFile(io.BytesIO(backup)) as archive:
    keep('43-backup-manifest.json', json.loads(archive.read('manifest.json')), 'What a backup file records about itself')
keep('44-backups-list.json', admin.get('/api/system/backups/'), 'Automatic copies kept on the computer')

print('Rules that refuse bad data…')
refusals = [
    preparer.refused('post', '/api/register/entries/', {
        'request_key': str(uuid.uuid4()), 'date': '2026-09-30', 'direction': 'payment', 'category': masters['CLIENT']['id'],
        'source': cash['id'], 'party': 'Example', 'amount': '-500.00', 'method': 'cash'}),
    preparer.refused('post', '/api/register/entries/', {
        'request_key': str(uuid.uuid4()), 'date': '2026-09-30', 'direction': 'payment', 'category': masters['CLIENT']['id'],
        'source': cash['id'], 'party': 'Example', 'amount': '500.00', 'method': 'cash', 'reporting_class': 'income', 'nature': 'operating'}),
    preparer.refused('post', '/api/register/entries/', {
        'request_key': str(uuid.uuid4()), 'date': '2026-06-15', 'direction': 'payment', 'category': masters['MAT']['id'],
        'source': cash['id'], 'party': 'Example', 'amount': '500.00', 'method': 'cash'}),
    preparer.refused('post', f'/api/register/entries/{entries[0]["id"]}/action/', {'action': 'confirm', 'version': entries[0]['version']}),
    preparer.refused('post', '/api/register/masters/categories/', {'code': 'NEW', 'name': 'Attempted by a preparer'}),
]
own = admin.post('/api/register/entries/', {
    'request_key': str(uuid.uuid4()), 'date': '2026-09-29', 'direction': 'payment', 'category': masters['OFF']['id'],
    'source': cash['id'], 'party': 'Example', 'amount': '5000.00', 'method': 'cash',
    'reporting_class': 'expense', 'nature': 'operating', 'remarks': 'Prepared by someone who also holds the approval permission.'})
own = admin.post(f'/api/register/entries/{own["id"]}/action/', {'action': 'submit', 'version': own['version']})
refusals.append(admin.refused('post', f'/api/register/entries/{own["id"]}/action/', {'action': 'confirm', 'version': own['version']}))
keep('45-refused-requests.json', refusals, 'Six rules, refused with the message the user sees')

index = ['# Example files\n',
         'Generated by `scripts/build_manual_examples.py` from a throwaway database in a temporary folder.',
         'Every file below is a real response or export from that run, not a mock-up. The data is invented.',
         'Re-run the script after changing a feature so the manual keeps matching the build.\n',
         '| File | Size | What it shows |', '|---|---|---|']
index += [f'| [{name}]({name}) | {size:,} bytes | {note} |' for name, size, note in saved]
(OUT / 'README.md').write_text('\n'.join(index) + '\n', encoding='utf-8')
print(f'\n{len(saved)} example files in {OUT}')
shutil.rmtree(DATA, ignore_errors=True)
print('Temporary data folder removed.')
