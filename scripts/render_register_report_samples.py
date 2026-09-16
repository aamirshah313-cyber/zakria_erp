"""Synthetic export layout fixtures only. Does not read or write business records."""
import os
import sys
from pathlib import Path
from decimal import Decimal

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root/'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from core.register_reports import clean_definition, pdf_bytes, image_bytes

out = root/'storage/report-qa'
out.mkdir(parents=True, exist_ok=True)
rows = []
running = Decimal(0)
for i in range(60):
    paid = Decimal('100.10') if i % 4 else Decimal(0)
    received = Decimal('200.20') if i % 4 == 0 else Decimal(0)
    running += received-paid
    rows.append({'date':f'2026-09-{i%28+1:02d}','reference':f'TEST-{i+1:06d}','party':'TEST contractor - district supply and installation supporting statement with a deliberately long description' if i%7 == 0 else 'TEST supplier','source':'TEST cash account','receipt':str(received),'payment':str(paid),'balance':str(running)})
report = {'definition':clean_definition({'title':'TEST ONLY - Register activity','footer':'Synthetic layout check - not company accounts','chart':True}), 'columns':['date','reference','party','source','receipt','payment','balance'], 'rows':rows,'summary':[{'label':'TEST September','count':60,'receipt':'3003.00','payment':'4504.50','transfer_in':'0.00','transfer_out':'0.00','net':'-1501.50'}], 'count':60,'opening':'0.00','receipts':'3003.00','payments':'4504.50','closing':'-1501.50','net':'-1501.50','transfers_in':'0.00','transfers_out':'0.00','from':'2026-09-01','to':'2026-09-30','period_label':'September 2026','scope':'TEST project only; all categories; PKR','basis':'Receipts less payments. Synthetic movements only. Not profit, customer debt or a reconciled bank balance.','generated':'2026-09-14 12:00 PKT','prepared_for':'TEST reviewer','company':{'name':'Muhammad Zakaria and Sons - TEST COPY','city':'Islamabad','ntn':'','ftn':'','strn':''}}
(out/'a4-landscape.pdf').write_bytes(pdf_bytes(report))
report['definition'].update(paper='A3',orientation='portrait',view='summary',accent='#0F766E')
(out/'a3-portrait.pdf').write_bytes(pdf_bytes(report))
(out/'chart.png').write_bytes(image_bytes(report,'png'))
(out/'chart.jpeg').write_bytes(image_bytes(report,'jpeg'))
print(out)
