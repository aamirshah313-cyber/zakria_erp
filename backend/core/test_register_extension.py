from decimal import Decimal
from io import BytesIO
import uuid
from django.test import TestCase, override_settings
from . import test_v2 as fixtures
from .models import Party, Project, RegisterCategory, RegisterSource, RegisterEntry, RegisterPosition
from .register_reports import date_range


@override_settings(V2_DESKTOP=True, PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class RegisterExtensionTests(TestCase):
    setUp = fixtures.V2Tests.setUp
    payload = fixtures.V2Tests.payload
    create = fixtures.V2Tests.create
    action = fixtures.V2Tests.action
    confirm = fixtures.V2Tests.confirm

    def report(self, **extra):
        response = self.client.post('/api/register/reports/', extra, format='json')
        self.assertEqual(response.status_code, 200, getattr(response, 'data', 'export error'))
        return response

    def position(self, **extra):
        self.client.force_authenticate(self.maker)
        payload = {'request_key': str(uuid.uuid4()), 'kind':'opening', 'date':'2026-09-01', 'amount':'1000.00', 'source':self.source.pk, 'reference':'TEST statement', 'remarks':'Reviewed synthetic opening for test only', **extra}
        response = self.client.post('/api/register/positions/', payload, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        row = response.data
        row = self.client.post(f"/api/register/positions/{row['id']}/", {'action':'submit','version':row['version']}, format='json').data
        self.client.force_authenticate(self.reviewer)
        response = self.client.post(f"/api/register/positions/{row['id']}/", {'action':'confirm','version':row['version']}, format='json')
        return response

    def test_party_bank_privacy_and_hierarchy(self):
        self.source.account_number = '0001234567'
        self.source.save()
        self.assertNotIn('account_number', self.client.get('/api/register/masters/').data['sources'][0])
        self.client.force_authenticate(self.admin)
        body = {'id':self.source.pk,'name':self.source.name,'kind':'bank','account_number':'0001234567'}
        self.assertEqual(self.client.post('/api/register/masters/sources/',body,format='json').status_code,403)
        self.admin_role.permissions += ['register.bank_details']
        self.admin_role.save()
        self.assertEqual(self.client.post('/api/register/masters/sources/',body,format='json').status_code,200)
        self.assertEqual(self.client.get('/api/register/masters/').data['sources'][0]['account_number'],'0001234567')
        body['iban'] = 'PK001234'
        self.assertEqual(self.client.post('/api/register/masters/sources/',body,format='json').status_code,400)
        child = RegisterCategory.objects.create(code='CHILD', name='Child', parent=self.category)
        self.assertEqual(self.client.post('/api/register/masters/categories/', {'id':self.category.pk, 'code':'TEST', 'name':'Test', 'parent':child.pk},format='json').status_code,400)

    def test_split_totals_project_basis_and_retry(self):
        other = RegisterCategory.objects.create(code='OTHER',name='Other')
        project = Project.objects.create(code='P',name='Test contract')
        allocations = [{'category':self.category.pk,'amount':'60.10','project':project.pk},{'category':other.pk,'amount':'40.00'}]
        row = self.confirm(allocations=allocations)
        self.assertEqual(self.report().data['payments'],'100.10')
        scoped = self.report(project=project.pk,balance_basis='payments_less_receipts').data
        self.assertEqual(scoped['closing'],'60.10')
        grouped = self.report(group='category').data
        self.assertEqual(sum(Decimal(r['payment']) for r in grouped['summary']),Decimal('100.10'))
        self.assertEqual(grouped['count'],2)
        self.client.force_authenticate(self.maker)
        invalid = self.client.post('/api/register/entries/',self.payload(allocations=allocations,amount='100'),format='json')
        self.assertEqual(invalid.status_code,400)
        draft,payload = self.create(allocations=allocations)
        self.assertEqual(self.client.post('/api/register/entries/',payload,format='json').status_code,200)
        payload['allocations'][0]['amount']='60.09'
        payload['allocations'][1]['amount']='40.01'
        self.assertEqual(self.client.post('/api/register/entries/',payload,format='json').status_code,400)

    def test_opening_cutoff_and_transfer_do_not_inflate_receipts(self):
        opening = self.position()
        self.assertEqual(opening.status_code,200,opening.data)
        cash = RegisterSource.objects.create(name='Test cash',kind='cash')
        transfer = self.position(kind='transfer',date='2026-09-03',amount='250.10',destination=cash.pk)
        self.assertEqual(transfer.status_code,200,transfer.data)
        self.confirm(amount='100.10')
        report = self.report(source=self.source.pk).data
        self.assertEqual(report['opening'],'1000.00')
        self.assertEqual(report['transfers_out'],'250.10')
        self.assertEqual(report['closing'],'649.80')
        self.assertEqual(report['receipts'],'0.00')
        self.assertEqual(self.report(source=cash.pk).data['closing'],'250.10')
        self.assertEqual(self.report().data['closing'],'-100.10')
        self.client.force_authenticate(self.maker)
        self.assertEqual(self.client.post('/api/register/entries/', self.payload(date='2026-08-31'),format='json').status_code,400)
        self.assertEqual(self.position().status_code,400)

    def test_opening_conflict_with_history_and_draft_race(self):
        old,_ = self.create(date='2026-08-01')
        self.assertEqual(self.position().status_code,200)
        self.client.force_authenticate(self.maker)
        submitted = self.action(old,'submit').data
        self.client.force_authenticate(self.reviewer)
        self.assertEqual(self.action(submitted,'confirm').status_code,400)
        other = RegisterSource.objects.create(name='Second bank',kind='bank')
        self.confirm(date='2026-08-01',source=other.pk)
        self.assertEqual(self.position(source=other.pk).status_code,400)

    def test_used_account_identity_cannot_be_replaced(self):
        self.assertEqual(self.position().status_code,200)
        self.client.force_authenticate(self.admin)
        self.admin_role.permissions += ['register.bank_details']
        self.admin_role.save()
        body={'id':self.source.pk,'name':self.source.name,'kind':'cash'}
        self.assertEqual(self.client.post('/api/register/masters/sources/',body,format='json').status_code,400)
        body.update(kind='bank',account_number='00012345')
        self.assertEqual(self.client.post('/api/register/masters/sources/',body,format='json').status_code,200)
        body['account_number']='00067890'
        self.assertEqual(self.client.post('/api/register/masters/sources/',body,format='json').status_code,400)

    def test_structured_party_history_and_inactive_approval(self):
        party = Party.objects.create(name='Test contractor',kind='contractor')
        self.confirm(counterparty=party.pk,party=party.name,beneficiary='Test beneficiary',nature='advance')
        party.name='Renamed contractor'
        party.save()
        report=self.report(counterparty=party.pk).data
        self.assertEqual(report['rows'][0]['party'],'Test contractor')
        self.assertEqual(report['rows'][0]['nature'],'Advance')
        self.client.force_authenticate(self.maker)
        row,_=self.create(counterparty=party.pk)
        row=self.action(row,'submit').data
        party.active=False;party.save()
        self.client.force_authenticate(self.reviewer)
        self.assertEqual(self.action(row,'confirm').status_code,400)

    def test_report_exports_permissions_and_saved_ownership(self):
        self.confirm(party='=TEST()',amount='100.10')
        for fmt in ['csv','xlsx','pdf','png','jpeg']:
            response=self.report(format=fmt,chart=False)
            self.assertGreater(len(response.content),100)
            if fmt == 'csv':
                self.assertIn("'=TEST()",response.content.decode('utf-8-sig'))
            if fmt == 'xlsx':
                from openpyxl import load_workbook
                book=load_workbook(BytesIO(response.content))
                self.assertEqual(book['Report rows']['F2'].value,100.1)
                self.assertEqual(book['Report rows']['C2'].data_type,'s')
                self.assertEqual(book['Report rows'].page_setup.orientation,'landscape')
        saved=self.client.post('/api/register/report-templates/',{'name':'Personal report','definition':{'columns':['date','payment']}},format='json')
        self.assertEqual(saved.status_code,200)
        self.client.force_authenticate(self.maker)
        self.assertEqual(self.client.post('/api/register/reports/',{'format':'csv'},format='json').status_code,403)
        self.assertEqual(self.client.post('/api/register/report-templates/',{'id':saved.data['id'],'action':'archive'},format='json').status_code,404)
        self.assertEqual(self.client.post('/api/register/reports/',{'columns':['date','date']},format='json').status_code,400)

    def test_fiscal_period_and_filtered_opening(self):
        start,end=date_range({'period':'quarter','anchor':'2026-01-15','fiscal_start_month':7})
        self.assertEqual(str(start),'2026-01-01')
        self.assertEqual(str(end),'2026-03-31')
        self.confirm(direction='receipt',date='2026-09-01',amount='200')
        self.confirm(amount='50.10')
        report=self.report(period='day',anchor='2026-09-12').data
        self.assertEqual(report['opening'],'200.00')
        self.assertEqual(report['closing'],'149.90')
        self.assertEqual(self.report(evidence='missing').data['payments'],'50.10')
