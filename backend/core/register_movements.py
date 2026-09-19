"""One movement calculation for register statements and exports; Decimal only."""
from decimal import Decimal
from django.utils import timezone
from django.db.models import Q
from rest_framework.exceptions import ValidationError
from .models import RegisterEntry, RegisterPosition

ZERO = Decimal('0')


def movement_rows(d, start, end):
    query = RegisterEntry.objects.filter(status='confirmed').select_related('source', 'category', 'project', 'counterparty', 'owner', 'approved_by').prefetch_related('allocations__category', 'allocations__project', 'attachments')
    if end:
        query = query.filter(date__lte=end)
    for key in ['source', 'counterparty']:
        if d.get(key):
            query = query.filter(**{key+'_id': d[key]})
    if d.get('source_kind'):
        query = query.filter(source__kind=d['source_kind'])
    for key in ['direction', 'method', 'nature', 'reporting_class']:
        if d.get(key):
            query = query.filter(**{key: d[key]})
    if d.get('party', '').strip():
        query = query.filter(party__icontains=d['party'].strip())
    for key in ['beneficiary', 'handled_by', 'reference']:
        if d.get(key, '').strip():
            query = query.filter(**{key+'__icontains': d[key].strip()})
    for key, lookup in [('min_amount', 'amount__gte'), ('max_amount', 'amount__lte')]:
        if d.get(key) not in [None, '']:
            query = query.filter(**{lookup: Decimal(d[key])})
    if query.count() > 50000:
        raise ValidationError('This statement exceeds 50,000 historical records. Narrow its account or party scope.')
    items = []
    for entry in query.order_by('date', 'pk'):
        evidence = sum(a.withdrawn_at is None for a in entry.attachments.all())
        if d.get('evidence') == 'missing' and evidence or d.get('evidence') == 'present' and not evidence:
            continue
        allocations = list(entry.allocations.all())
        parts = [{'category': a.category, 'project': a.project, 'amount': a.amount} for a in allocations] or [{'category': entry.category, 'project': entry.project, 'amount': entry.amount}]
        parts = [p for p in parts if all(not d.get(k) or (p[k] and p[k].pk == d[k]) for k in ['category', 'project'])]
        if not parts:
            continue
        # Expand only when grouping by allocations. Other views retain one row
        # per transaction with the sum of matching allocations, never the full
        # transaction amount repeated on each project.
        if d.get('group') not in ['category', 'project']:
            groups = [parts]
        else:
            grouped = {}
            for p in parts:
                master = p[d['group']]
                grouped.setdefault(master.pk if master else None, []).append(p)
            groups = list(grouped.values())
        for group in groups:
            amount = sum(p['amount'] for p in group)
            labels = lambda key: ', '.join(dict.fromkeys(p[key].name if p[key] else 'Unassigned' for p in group))
            items.append({'id': entry.pk, 'reference': f'REG-{entry.pk:06d}', 'date': str(entry.date), 'party': entry.party, 'category': labels('category'), 'project': labels('project'), 'source': entry.source.name, 'direction': entry.direction, 'nature': entry.get_nature_display(), 'reporting_class': entry.get_reporting_class_display(), 'beneficiary': entry.beneficiary, 'method': entry.method, 'instrument': entry.reference, 'handled_by': entry.handled_by, 'receipt': amount if entry.direction == 'receipt' else ZERO, 'payment': amount if entry.direction == 'payment' else ZERO, 'transfer_in': ZERO, 'transfer_out': ZERO, 'remarks': entry.remarks, 'prepared_by': entry.owner.username, 'approved_by': entry.approved_by.username if entry.approved_by_id else '', 'confirmed_at': timezone.localtime(entry.confirmed_at).isoformat() if entry.confirmed_at else '', 'evidence': evidence})
    # Transfers affect own-account books, never external receipts/payments.
    if not any(d.get(k) for k in ['category','project','counterparty','party','direction','method','nature','evidence','reporting_class','beneficiary','handled_by','reference','min_amount','max_amount']):
        transfers = RegisterPosition.objects.filter(kind='transfer', status='confirmed').select_related('source', 'destination', 'owner', 'approved_by').prefetch_related('attachments')
        if end:
            transfers = transfers.filter(date__lte=end)
        if d.get('source'):
            transfers = transfers.filter(Q(source_id=d['source']) | Q(destination_id=d['source']))
        for item in transfers:
            evidence = sum(a.withdrawn_at is None for a in item.attachments.all())
            legs = [(item.source, ZERO, item.amount), (item.destination, item.amount, ZERO)]
            legs = [leg for leg in legs if (not d.get('source') or leg[0].pk == d['source']) and (not d.get('source_kind') or leg[0].kind == d['source_kind'])]
            groups = [[leg] for leg in legs] if d.get('group') == 'source' else [legs] if legs else []
            for group in groups:
                items.append({'id': None, 'reference': f'TRF-{item.pk:06d}', 'date': str(item.date), 'party': 'Own-account transfer', 'category': 'Internal transfer', 'project': 'Unassigned', 'source': ' → '.join(leg[0].name for leg in group), 'direction': 'transfer', 'nature': 'Internal transfer', 'reporting_class': 'Other funds movement', 'beneficiary': item.destination.name, 'method': '', 'instrument': item.reference, 'handled_by': '', 'receipt': ZERO, 'payment': ZERO, 'transfer_in': sum(leg[1] for leg in group), 'transfer_out': sum(leg[2] for leg in group), 'remarks': item.remarks, 'prepared_by': item.owner.username, 'approved_by': item.approved_by.username, 'confirmed_at': timezone.localtime(item.confirmed_at).isoformat(), 'evidence': evidence})
    items.sort(key=lambda r: (r['date'], r['reference']))
    scope = [(k, d[k]) for k in ['source', 'category', 'project', 'counterparty'] if d.get(k)]
    opening = ZERO
    note = 'Opening includes earlier recorded movement. Independent openings apply only to one selected account/category/project/party without additional filters; openings from different dimensions are never added together.'
    if len(scope) == 1 and not any(d.get(k) for k in ['source_kind','direction','method','nature','party','evidence','reporting_class','beneficiary','handled_by','reference','min_amount','max_amount']):
        key, value = scope[0]
        position = RegisterPosition.objects.filter(kind='opening', status='confirmed', **{key+'_id': value}).first()
        if position:
            if (start and start < position.date) or (end and end < position.date):
                raise ValidationError(f'This scope starts with an approved opening on {position.date}. Select that date or later.')
            opening = position.amount if position.side == 'receipt' else -position.amount
            note = f'Includes approved opening OP-{position.pk:06d} at start of {position.date}. Movements before that cutoff cannot be included.'
    earlier = [r for r in items if start and r['date'] < str(start)]
    opening += sum(r['receipt']-r['payment']+r['transfer_in']-r['transfer_out'] for r in earlier)
    rows = [r for r in items if not start or r['date'] >= str(start)]
    if len(rows) > 10000:
        raise ValidationError('Select a range of 10,000 statement rows or fewer.')
    return rows, opening, note
