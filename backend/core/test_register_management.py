from decimal import Decimal
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from . import test_v2 as fixtures
from .models import RegisterEntry, RegisterCategory, AuditEvent
from .register_reports import build_report


@override_settings(V2_DESKTOP=True, PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class RegisterManagementTests(TestCase):
    setUp = fixtures.V2Tests.setUp
    payload = fixtures.V2Tests.payload
    create = fixtures.V2Tests.create
    action = fixtures.V2Tests.action
    confirm = fixtures.V2Tests.confirm

    def admin_access(self):
        self.admin_role.permissions += ['register.view','register.delete','register.import']
        self.admin_role.save()
        self.client.force_authenticate(self.admin)

    def test_delete_restore_permission_version_history(self):
        row,_ = self.create()
        path='/api/register/data-management/'
        self.assertEqual(self.client.get(path).status_code,403)
        self.admin_access()
        item=self.client.get(path).data['rows'][0]
        payload={'kind':'entries','id':row['id'],'revision':item['revision'],'action':'remove','reason':'Duplicate test draft'}
        self.assertEqual(self.client.post(path,{**payload,'revision':'0'},format='json').status_code,400)
        self.assertEqual(self.client.post(path,payload,format='json').status_code,200)
        self.assertTrue(RegisterEntry.objects.filter(pk=row['id'],status='deleted').exists())
        self.assertEqual(self.client.get('/api/register/entries/').data['count'],0)
        self.assertTrue(AuditEvent.objects.filter(action='register.data_remove').exists())
        item=self.client.get(path+'?removed=true').data['rows'][0]
        self.assertEqual(self.client.post(path,{**payload,'revision':item['revision'],'action':'restore'},format='json').status_code,200)
        self.assertEqual(RegisterEntry.objects.get(pk=row['id']).status,'draft')

    def test_confirmed_records_cannot_be_erased_or_removed(self):
        row=self.confirm()
        self.admin_access()
        item=self.client.get('/api/register/data-management/').data['rows'][0]
        response=self.client.post('/api/register/data-management/',{'kind':'entries','id':row['id'],'revision':item['revision'],'action':'remove','reason':'test'},format='json')
        self.assertEqual(response.status_code,400)
        self.assertEqual(build_report({})['payments'],'100.10')

    def test_category_archive_preserves_child_and_statement(self):
        self.confirm()
        self.admin_access()
        RegisterCategory.objects.create(code='CHILD',name='Child',parent=self.category)
        rows=self.client.get('/api/register/data-management/?kind=categories').data['rows']
        parent=next(r for r in rows if r['id']==self.category.pk)
        self.assertEqual(self.client.post('/api/register/data-management/',{'kind':'categories','id':parent['id'],'revision':parent['revision'],'action':'remove','reason':'test'},format='json').status_code,400)
        self.assertEqual(build_report({})['payments'],'100.10')

    def test_classification_and_new_report_filters(self):
        self.assertEqual(self.client.post('/api/register/entries/',self.payload(reporting_class='income',nature='loan',direction='receipt'),format='json').status_code,400)
        self.assertEqual(self.client.post('/api/register/entries/',self.payload(reporting_class='expense',nature='operating',direction='receipt'),format='json').status_code,400)
        self.confirm(reporting_class='expense',nature='operating',handled_by='TEST clerk',beneficiary='TEST supplier',reference='TEST-123')
        report=build_report({'reporting_class':'expense','handled_by':'clerk','beneficiary':'supplier','reference':'123','min_amount':'100','max_amount':'101','group':'quarter','fiscal_start_month':7})
        self.assertEqual(report['payments'],'100.10')
        self.assertEqual(report['summary'][0]['label'],'FY 2026/2027 Q1')
        self.assertEqual(build_report({'reporting_class':'income'})['receipts'],'0.00')
        self.assertEqual(build_report({'min_amount':'101'})['count'],0)

    def master_upload(self, action, text, **extra):
        return self.client.post('/api/register/master-import/',{'kind':'categories','action':action,'sheet':'CSV','header_row':'1','file':SimpleUploadedFile('masters.csv',text.encode(),content_type='text/csv'),**extra},format='multipart')

    def test_master_preview_commit_and_no_overwrite(self):
        self.admin_access()
        text='code,name,active\nNEW,New category,true\n'
        preview=self.master_upload('preview',text)
        self.assertEqual(preview.status_code,200,preview.data)
        self.assertTrue(preview.data['ready'])
        self.assertFalse(RegisterCategory.objects.filter(code='NEW').exists())
        bad=self.master_upload('commit',text.replace('New category','Changed'),token=preview.data['token'],acknowledge='true')
        self.assertEqual(bad.status_code,400)
        result=self.master_upload('commit',text,token=preview.data['token'],acknowledge='true')
        self.assertEqual(result.status_code,201,result.data)
        self.assertFalse(self.master_upload('preview',text).data['ready'])
        duplicate=self.master_upload('preview','code,name\nSAME,One\nSAME,Two\n')
        self.assertFalse(duplicate.data['ready'])

    def test_master_commit_rejects_changed_parent_resolution(self):
        self.admin_access()
        text=f'code,name,parent\nNEW,New child,{self.category.code}\n'
        preview=self.master_upload('preview',text)
        self.assertEqual(preview.status_code,200,preview.data)
        self.assertTrue(preview.data['ready'],preview.data)
        previous_code=self.category.code
        self.category.code='RENAMED'
        self.category.save()
        RegisterCategory.objects.create(code=previous_code,name='Replacement parent')
        result=self.master_upload('commit',text,token=preview.data['token'],acknowledge='true')
        self.assertEqual(result.status_code,400,result.data)
        self.assertFalse(RegisterCategory.objects.filter(code='NEW').exists())

    def test_delivered_workbook_imports_into_real_forms_as_drafts(self):
        from pathlib import Path
        from django.conf import settings
        self.source.name='Fixture bank'
        self.source.save()
        self.admin_access()
        self.admin_role.permissions += ['register.create']
        self.admin_role.save()
        content=(Path(settings.BASE_DIR)/'resources/V2-Testing-and-Import.xlsx').read_bytes()
        for kind,sheet in [('categories','Categories'),('parties','Parties'),('sources','Accounts'),('projects','Projects')]:
            def upload(action, **extra):
                return self.client.post('/api/register/master-import/',{'kind':kind,'sheet':sheet,'header_row':'1','action':action,'file':SimpleUploadedFile('kit.xlsx',content),**extra},format='multipart')
            preview=upload('preview')
            self.assertEqual(preview.status_code,200,preview.data)
            self.assertTrue(preview.data['ready'],preview.data)
            result=upload('commit',token=preview.data['token'],acknowledge='true')
            self.assertEqual(result.status_code,201,result.data)
        for sheet,mode,receipts,payments in [('Transactions','single','2110000','1548000'),('Client ledger excerpt','separate','5009642','521500')]:
            staged=self.client.post('/api/register/imports/',{'file':SimpleUploadedFile('kit.xlsx',content),'sheet':sheet,'header_row':'1'},format='multipart')
            self.assertEqual(staged.status_code,201,staged.data)
            batch=staged.data
            config={'columns':{v:i for i,v in enumerate(batch['headers'])},'defaults':{},'amount_mode':mode,'date_format':'iso','control_receipt':receipts,'control_payment':payments}
            preview=self.client.post(f"/api/register/imports/{batch['id']}/",{'action':'preview','version':batch['version'],'configuration':config},format='json')
            self.assertEqual(preview.status_code,200,preview.data)
            self.assertTrue(preview.data['preview']['ready'],preview.data['preview'])
            committed=self.client.post(f"/api/register/imports/{batch['id']}/",{'action':'commit','version':preview.data['version'],'acknowledge':True},format='json')
            self.assertEqual(committed.status_code,200,committed.data)
        self.assertEqual(RegisterEntry.objects.filter(status='draft').count(),12)
        self.assertEqual(RegisterEntry.objects.filter(reporting_class='expense').count(),3)
        self.assertEqual(RegisterEntry.objects.filter(reporting_class='income').count(),2)
        self.assertEqual(build_report({})['count'],0)

    def test_draft_document_removal_and_approved_protection(self):
        from .models import Document, Party
        self.admin_access()
        self.admin_role.permissions += ['quotation.view','quotation.create']
        self.admin_role.save()
        party=Party.objects.create(name='Document client',kind='customer')
        doc=Document.objects.create(kind='quotation',number='TEST-Q-1',party=party,owner=self.admin,issue_date='2026-09-15')
        path='/api/register/data-management/'
        item=self.client.get(path+'?kind=quotations').data['rows'][0]
        payload={'kind':'quotations','id':doc.pk,'revision':item['revision'],'action':'remove','reason':'Duplicate draft'}
        self.assertEqual(self.client.post(path,payload,format='json').status_code,200)
        self.assertEqual(len(self.client.get('/api/documents/?kind=quotation').data),0)
        item=self.client.get(path+'?kind=quotations&removed=true').data['rows'][0]
        self.assertEqual(self.client.post(path,{**payload,'action':'restore','revision':item['revision']},format='json').status_code,200)
        doc.refresh_from_db()
        doc.status='approved';doc.save()
        self.assertEqual(self.client.post(path,{**payload,'revision':str(doc.version)},format='json').status_code,400)
