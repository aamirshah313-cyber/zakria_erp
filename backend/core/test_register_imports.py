import io
from datetime import datetime
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from openpyxl import Workbook
from . import test_v2 as fixtures
from .models import RegisterEntry, RegisterImport, RegisterImportOrigin


@override_settings(V2_DESKTOP=True, PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class RegisterImportTests(TestCase):
    payload = fixtures.V2Tests.payload
    create = fixtures.V2Tests.create

    def setUp(self):
        fixtures.V2Tests.setUp(self)
        self.maker_role.permissions += ['register.import']
        self.maker_role.save()

    def workbook(self, rows=None):
        book = Workbook()
        sheet = book.active
        sheet.title = 'Register'
        for row in rows or [['Date','Party','Debit','Credit','Category'], [datetime(2026,9,12),'Test supplier',100.10,None,'TEST'], [datetime(2026,9,13),'Test customer',None,200,'TEST']]:
            sheet.append(row)
        stream = io.BytesIO()
        book.save(stream)
        return stream.getvalue()

    def stage(self, content=None):
        content = content or self.workbook()
        result = self.client.post('/api/register/imports/', {'file':SimpleUploadedFile('test.xlsx',content), 'sheet':'Register','header_row':'1'}, format='multipart')
        self.assertEqual(result.status_code,201,result.data)
        return result.data

    def config(self, **extra):
        return {'columns':{'date':0,'party':1,'payment':2,'receipt':3,'category':4}, 'defaults':{'source':self.source.pk,'method':'transfer'}, 'amount_mode':'separate', 'date_format':'day_first', 'control_payment':'100.10','control_receipt':'200.00', 'exclude':{},'duplicate_reasons':{},'aliases':{}, **extra}

    def preview(self, batch, config=None):
        result = self.client.post(f"/api/register/imports/{batch['id']}/", {'action':'preview','version':batch['version'],'configuration':config or self.config()}, format='json')
        self.assertEqual(result.status_code,200,result.data)
        return result.data

    def commit(self, batch, **extra):
        return self.client.post(f"/api/register/imports/{batch['id']}/", {'action':'commit','version':batch['version'],'acknowledge':True,**extra}, format='json')

    def test_inspect_has_no_database_effect_and_import_is_drafts_only(self):
        content = self.workbook()
        response = self.client.post('/api/register/imports/inspect/', {'file':SimpleUploadedFile('test.xlsx',content)}, format='multipart')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.data['sheets'][0]['sample'][1][0],'2026-09-12')
        self.assertFalse(RegisterImport.objects.exists())
        batch = self.stage(content)
        self.assertFalse(RegisterEntry.objects.exists())
        batch = self.preview(batch)
        self.assertTrue(batch['preview']['ready'])
        result = self.commit(batch)
        self.assertEqual(result.status_code,200,result.data)
        self.assertEqual(RegisterEntry.objects.count(),2)
        self.assertEqual(RegisterEntry.objects.filter(status='draft',owner=self.maker).count(),2)
        self.assertEqual(RegisterImportOrigin.objects.count(),2)
        self.assertEqual(self.client.get('/api/register/ledger/').data['count'],0)
        self.assertEqual(self.commit(batch).status_code,200)
        self.assertEqual(RegisterEntry.objects.count(),2)

    def test_control_discrepancy_blocks_all_writes(self):
        batch = self.preview(self.stage(), self.config(control_receipt='4409459.00'))
        self.assertFalse(batch['preview']['ready'])
        self.assertTrue(any('differs' in error for error in batch['preview']['errors']))
        self.assertEqual(self.commit(batch).status_code,400)
        self.assertFalse(RegisterEntry.objects.exists())

    def test_exact_source_row_cannot_be_reimported_even_after_cancellation(self):
        content = self.workbook()
        batch = self.preview(self.stage(content))
        self.assertEqual(self.commit(batch).status_code,200)
        RegisterEntry.objects.update(status='cancelled')
        again = self.preview(self.stage(content), self.config(duplicate_reasons={'2':'Different purchase claimed','3':'Different receipt claimed'}))
        self.assertFalse(again['preview']['ready'])
        self.assertIn('already imported',str(again['preview']))
        self.assertEqual(self.commit(again).status_code,400)
        self.assertEqual(RegisterEntry.objects.count(),2)

    def test_cross_file_and_within_batch_duplicates_require_reasons(self):
        self.create(date='2026-09-12',amount='100.10')
        batch = self.preview(self.stage())
        self.assertFalse(batch['preview']['ready'])
        batch = self.preview(batch,self.config(duplicate_reasons={'2':'Separate payment to a different supplier'}))
        self.assertTrue(batch['preview']['ready'])
        self.assertEqual(self.commit(batch).status_code,200)
        rows = [['Date','Party','Debit','Credit','Category'],['14/09/2026','Party one',10,0,'TEST'],['14/09/2026','Party two',10,0,'TEST']]
        batch = self.preview(self.stage(self.workbook(rows)),self.config(control_payment='20',control_receipt='0'))
        self.assertFalse(batch['preview']['ready'])
        self.assertIn('same batch',str(batch['preview']))

    def test_commit_rechecks_new_duplicates_and_master_activity(self):
        batch = self.preview(self.stage())
        self.create(date='2026-09-12',amount='100.10')
        self.assertEqual(self.commit(batch).status_code,400)
        self.assertFalse(RegisterImportOrigin.objects.exists())
        batch = self.preview(batch,self.config(duplicate_reasons={'2':'Separate supplier transfer verified'}))
        self.create(date='2026-09-12',amount='100.10',party='Another supplier')
        self.assertEqual(self.commit(batch).status_code,400)
        batch = self.preview(batch,self.config(duplicate_reasons={'2':'Both existing payments were checked separately'}))
        self.source.active = False
        self.source.save()
        self.assertEqual(self.commit(batch).status_code,400)
        self.assertFalse(RegisterImportOrigin.objects.exists())

    def test_formula_summary_is_retained_and_must_be_excluded(self):
        rows = [['Date','Party','Debit','Credit','Category'],['12/09/26','Supplier',100.10,None,'TEST'],['','TOTAL','=SUM(C2:C2)',None,'']]
        batch = self.preview(self.stage(self.workbook(rows)),self.config(control_receipt='0'))
        self.assertFalse(batch['preview']['ready'])
        self.assertIn('formula',str(batch['preview']))
        batch = self.preview(batch,self.config(control_receipt='0',exclude={'3':'Source control total, not a transaction'}))
        self.assertTrue(batch['preview']['ready'])
        self.assertEqual(batch['preview']['excluded'],1)
        self.assertEqual(self.commit(batch).status_code,200)
        self.assertEqual(RegisterEntry.objects.count(),1)
        self.assertEqual(RegisterImport.objects.get().rows[1]['values'][2],'=SUM(C2:C2)')

    def test_explicit_date_interpretation_amount_precision_and_aliases(self):
        rows = [['Date','Party','Debit','Credit','Category'],['03/04/2026','Supplier','1,000.10','','Legacy feed']]
        batch = self.preview(self.stage(self.workbook(rows)),self.config(control_receipt='0',control_payment='1000.10',aliases={'category':{'Legacy feed':self.category.pk}}))
        self.assertTrue(batch['preview']['ready'])
        self.assertEqual(batch['preview']['rows'][0]['payload']['date'],'2026-04-03')
        batch = self.preview(batch,self.config(date_format='month_first',control_receipt='0',control_payment='1000.10',aliases={'category':{'Legacy feed':self.category.pk}}))
        self.assertEqual(batch['preview']['rows'][0]['payload']['date'],'2026-03-04')
        for value in ['-1','1.001','1,00','NaN','Infinity']:
            rows[1][2] = value
            bad = self.preview(self.stage(self.workbook(rows)),self.config(control_receipt='0',control_payment='0'))
            self.assertFalse(bad['preview']['ready'])

    def test_single_amount_direction_and_nonzero_both_sides(self):
        rows = [['Date','Party','Amount'],['2026-09-12','Supplier',100.10]]
        config = self.config(columns={'date':0,'party':1,'amount':2},amount_mode='single',control_receipt='0',defaults={'category':self.category.pk,'source':self.source.pk,'direction':'payment','method':'cash'})
        batch = self.preview(self.stage(self.workbook(rows)),config)
        self.assertTrue(batch['preview']['ready'])
        self.assertEqual(self.commit(batch).status_code,200)
        both = [['Date','Party','Debit','Credit','Category'],['2026-09-12','Party',10,10,'TEST']]
        batch = self.preview(self.stage(self.workbook(both)),self.config(control_payment='0',control_receipt='0'))
        self.assertFalse(batch['preview']['ready'])

    def test_permissions_ownership_version_and_acknowledgement(self):
        batch = self.stage()
        self.assertEqual(self.commit(batch).status_code,400)
        reviewed = self.preview(batch)
        stale = self.client.post(f"/api/register/imports/{batch['id']}/",{'action':'preview','version':batch['version'],'configuration':self.config()},format='json')
        self.assertEqual(stale.status_code,400)
        self.assertEqual(self.commit(reviewed,acknowledge=False).status_code,400)
        self.review_role.permissions += ['register.import','register.create']
        self.review_role.save()
        self.client.force_authenticate(self.reviewer)
        self.assertEqual(self.client.get(f"/api/register/imports/{batch['id']}/").status_code,404)
        self.assertEqual(self.client.get('/api/register/imports/').data,[])
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get('/api/register/imports/').status_code,403)
        self.client.force_authenticate(self.maker)
        with override_settings(V2_DESKTOP=False):
            self.assertEqual(self.client.get('/api/register/imports/').status_code,404)

    def test_csv_boundaries_invalid_mapping_and_file_types(self):
        result = self.client.post('/api/register/imports/',{'file':SimpleUploadedFile('test.csv',b'\xef\xbb\xbfDate,Party,Amount\n2026-09-12,Client,20\n'),'sheet':'CSV','header_row':'1'},format='multipart')
        self.assertEqual(result.status_code,201,result.data)
        batch = result.data
        invalid = self.client.post(f"/api/register/imports/{batch['id']}/",{'action':'preview','version':1,'configuration':self.config(columns={'date':99,'party':1})},format='json')
        self.assertEqual(invalid.status_code,400)
        for name, content in [('bad.xls',b'old format'),('broken.xlsx',b'not zip'),('large.csv',b'x'*(5*1024*1024+1))]:
            response = self.client.post('/api/register/imports/inspect/',{'file':SimpleUploadedFile(name,content)},format='multipart')
            self.assertEqual(response.status_code,400)
