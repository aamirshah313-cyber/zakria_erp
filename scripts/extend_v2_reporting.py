"""One-time source patch for V2 reporting increment; does not access a database."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def patch(path, changes):
    file = ROOT / path
    text = file.read_text(encoding='utf-8')
    for old, new in changes:
        if old not in text:
            raise RuntimeError(f'Missing source marker in {path}: {old[:60]}')
        text = text.replace(old, new)
    file.write_text(text, encoding='utf-8')

patch('backend/core/register_reports.py', [
 ("GROUPS = {'month':'Month',", "GROUPS = {'day':'Day', 'quarter':'Fiscal quarter', 'financial_year':'Financial year', 'method':'Payment method', 'nature':'Transaction nature', 'reporting_class':'Income / expense classification', 'beneficiary':'Beneficiary', 'handled_by':'Handled by', 'prepared_by':'Prepared by', 'approved_by':'Approved by', 'month':'Month',"),
 ("FIELDS = {'reference'", "FIELDS = {'reporting_class':'Income / expense classification', 'reference'"),
 ("'evidence','balance_basis']", "'evidence','balance_basis','reporting_class','beneficiary','handled_by','reference','min_amount','max_amount']"),
 ("[('balance_basis'", "[('reporting_class',['','unclassified','income','expense','other'],''), ('balance_basis'"),
 ("('party',180,'')]", "('party',180,''),('beneficiary',180,''),('handled_by',120,''),('reference',120,'')]"),
 ("    date_range(d)\n    return d", "    from .register_imports import exact_amount\n    for key in ['min_amount', 'max_amount']:\n        if d.get(key) not in [None, '']:\n            try:\n                d[key] = str(exact_amount(d[key]))\n            except ValueError as error:\n                raise ValidationError(str(error))\n    if d.get('min_amount') and d.get('max_amount') and Decimal(d['min_amount']) > Decimal(d['max_amount']):\n        raise ValidationError('Minimum amount cannot exceed maximum amount.')\n    date_range(d)\n    return d"),
 ("['source_kind','direction','method','party','nature','evidence']", "['source_kind','direction','method','party','nature','evidence','reporting_class','beneficiary','handled_by','reference','min_amount','max_amount']"),
 ("        group = row['date'][:7] if d['group'] == 'month' else row[d['group']]", "        group = report_group(row, d)"),
 ("    basis = (", "    basis = ('Income and expense figures are explicitly classified cash receipts/payments, not accrual financial statements. Amount filters apply to the original voucher total before allocations. ' if d.get('reporting_class') or d.get('min_amount') or d.get('max_amount') else '') + ("),
 ("def build_report(definition", "def report_group(row, d):\n    day = date.fromisoformat(row['date'])\n    fiscal = d.get('fiscal_start_month', 7)\n    if type(fiscal) is not int or not 1 <= fiscal <= 12:\n        raise ValidationError('Select a fiscal-year start month from 1 to 12.')\n    year = day.year - (day.month < fiscal)\n    label = f'FY {year}' if fiscal == 1 else f'FY {year}/{year + 1}'\n    if d['group'] == 'quarter':\n        return f'{label} Q{((day.month-fiscal) % 12)//3 + 1}'\n    if d['group'] == 'financial_year':\n        return label\n    if d['group'] == 'day':\n        return row['date']\n    return row['date'][:7] if d['group'] == 'month' else row[d['group']] or 'Unassigned'\n\n\ndef build_report(definition")
])
patch('backend/core/register_movements.py', [
 ("['direction', 'method', 'nature']", "['direction', 'method', 'nature', 'reporting_class']"),
 ("    if query.count() > 50000:", "    for key in ['beneficiary', 'handled_by', 'reference']:\n        if d.get(key, '').strip():\n            query = query.filter(**{key+'__icontains': d[key].strip()})\n    for key, lookup in [('min_amount', 'amount__gte'), ('max_amount', 'amount__lte')]:\n        if d.get(key) not in [None, '']:\n            query = query.filter(**{lookup: Decimal(d[key])})\n    if query.count() > 50000:"),
 ("'nature': entry.get_nature_display(),", "'nature': entry.get_nature_display(), 'reporting_class': entry.get_reporting_class_display(),"),
 ("'nature': 'Internal transfer',", "'nature': 'Internal transfer', 'reporting_class': 'Other funds movement',"),
 ("'nature','evidence']", "'nature','evidence','reporting_class','beneficiary','handled_by','reference','min_amount','max_amount']"),
 ("'nature','party','evidence']", "'nature','party','evidence','reporting_class','beneficiary','handled_by','reference','min_amount','max_amount']")
])
patch('backend/core/register_imports.py', [
 ("            payload['nature'] =", "            payload['reporting_class'] = value('reporting_class').casefold() if 'reporting_class' in columns else defaults.get('reporting_class', 'unclassified')\n            payload['nature'] ="),
 ("RegisterImport.objects.filter(owner=request.user).order_by", "RegisterImport.objects.filter(owner=request.user).exclude(status='deleted').order_by")
])
patch('backend/core/registers.py', [("query = RegisterEntry.objects.select_related", "query = RegisterEntry.objects.exclude(status='deleted').select_related")])
patch('backend/core/register_positions.py', [("RegisterPosition.objects.order_by('-date'", "RegisterPosition.objects.exclude(status='deleted').order_by('-date'"), ("if item.status == 'cancelled' or", "if item.status not in ['draft','submitted','confirmed'] or")])
patch('apps/client/lib/registers.dart', [
 ("    String nature =", "    String reportingClass = existing?['reporting_class'] ?? 'unclassified';\n    String nature ="),
 ("          calendarField(context, 'Transaction date', date),", "          calendarField(context, 'Transaction date', date),\n          select('Income / expense classification', reportingClass, ['unclassified', 'income', 'expense', 'other'], (v) => s(() => reportingClass = v), name: (v) => {'unclassified':'Pending classification','income':'Income received','expense':'Expense paid','other':'Other funds movement'}[v]!),\n          const Text('Cash-basis classification. Principal, advances and deposits belong to Other funds movement.'),"),
 ("            'nature': nature,", "            'reporting_class': reportingClass,\n            'nature': nature,"),
 ("      SelectableText('Organization / person:", "      SelectableText('Income / expense classification: ${row['reporting_class'] ?? 'unclassified'}'),\n      SelectableText('Organization / person:")
])
patch('apps/client/lib/register_imports.dart', [("  'nature': 'Transaction nature code',", "  'nature': 'Transaction nature code',\n  'reporting_class': 'Income / expense classification code',")])
patch('apps/client/lib/register_reports.dart', [
 ("  int counterparty = 0;", "  String reportingClass = '';\n  int counterparty = 0;"),
 ("      party = TextEditingController();", "      party = TextEditingController(),\n      beneficiary = TextEditingController(), handledBy = TextEditingController(), reference = TextEditingController(), minAmount = TextEditingController(), maxAmount = TextEditingController();"),
 ("    party,\n    from,", "    party, beneficiary, handledBy, reference, minAmount, maxAmount,\n    from,"),
 ("    'nature': nature,", "    'reporting_class': reportingClass,\n    'beneficiary': beneficiary.text, 'handled_by': handledBy.text, 'reference': reference.text, 'min_amount': minAmount.text, 'max_amount': maxAmount.text,\n    'nature': nature,"),
 ("      nature = d['nature'] ?? '';", "      reportingClass = d['reporting_class'] ?? '';\n      beneficiary.text = d['beneficiary'] ?? ''; handledBy.text = d['handled_by'] ?? ''; reference.text = d['reference'] ?? ''; minAmount.text = d['min_amount'] ?? ''; maxAmount.text = d['max_amount'] ?? '';\n      nature = d['nature'] ?? '';"),
 ("                            'Receipts',", "                            'Income received', 'Expenses paid', 'Unclassified', 'By beneficiary', 'By payment method',\n                            'Receipts',"),
 ("                                      direction = preset", "                                      reportingClass = preset == 'Income received' ? 'income' : preset == 'Expenses paid' ? 'expense' : preset == 'Unclassified' ? 'unclassified' : '';\n                                      nature = ''; evidence = ''; beneficiary.clear(); handledBy.clear(); reference.clear(); minAmount.clear(); maxAmount.clear(); party.clear(); category = 0; project = 0; source = 0; counterparty = 0; method = '';\n                                      group = preset == 'By beneficiary' ? 'beneficiary' : preset == 'By payment method' ? 'method' : 'month';\n                                      view = preset.startsWith('By ') ? 'summary' : 'detail';\n                                      direction = preset"),
 ("                      field('Report title', title),", "                      field('Report title', title),\n                      select('Income / expense classification', reportingClass, ['', 'unclassified', 'income', 'expense', 'other'], (v) => change(() => reportingClass = v), name: (v) => {'':'All classifications','unclassified':'Pending classification','income':'Income received','expense':'Expense paid','other':'Other funds movement'}[v]!),\n                      const Text('Income and expenses use explicitly classified cash receipts/payments. They are not accrual financial statements.'),\n                      field('Beneficiary contains', beneficiary), field('Handled by contains', handledBy), field('Instrument / reference contains', reference),\n                      field('Minimum voucher amount (PKR)', minAmount), field('Maximum voucher amount (PKR)', maxAmount),")
])
patch('apps/client/lib/main.dart', [("badge('pilot')", "badge(v2Desktop ? 'V2.1' : 'pilot')")])
print('Reporting source updated.')
