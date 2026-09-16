from django.urls import path
from core import views as v
from core.reports import Reports, DocumentPDF
from core.accounting_setup import AccountingSetup
from core.recovery import RecoveryCodes, ResetPassword
from core.registers import RegisterMasters, Entries, EntryAction, ActivityLedger
from core.register_evidence import RegisterAttachments
from core.register_imports import ImportInspect, ImportBatches, ImportReview
from core.register_reports import RegisterReports, RegisterReportTemplates
from core.register_positions import Positions
from core.register_data import RegisterData
from core.register_master_imports import MasterImport, ImportTemplate

urlpatterns = [
    path('api/register/data-management/', RegisterData.as_view()),
    path('api/register/master-import/', MasterImport.as_view()),
    path('api/register/import-template/', ImportTemplate.as_view()),
    path('api/register/positions/', Positions.as_view()),
    path('api/register/positions/<int:pk>/', Positions.as_view()),
    path('api/register/reports/', RegisterReports.as_view()),
    path('api/register/report-templates/', RegisterReportTemplates.as_view()),
    path('api/register/imports/inspect/', ImportInspect.as_view()),
    path('api/register/imports/', ImportBatches.as_view()),
    path('api/register/imports/<int:pk>/', ImportReview.as_view()),
    path('api/auth/recovery-codes/', RecoveryCodes.as_view()),
    path('api/auth/reset-password/', ResetPassword.as_view()),
    path('api/users/<int:pk>/reset-code/', RecoveryCodes.as_view()),
    path('api/register/masters/', RegisterMasters.as_view()),
    path('api/register/masters/<str:kind>/', RegisterMasters.as_view()),
    path('api/register/entries/', Entries.as_view()),
    path('api/register/entries/<int:pk>/attachments/', RegisterAttachments.as_view()),
    path('api/register/entries/<int:pk>/attachments/<int:attachment_id>/', RegisterAttachments.as_view()),
    path('api/register/entries/<int:pk>/action/', EntryAction.as_view()),
    path('api/register/ledger/', ActivityLedger.as_view()),
    path('api/accounting/setup/', AccountingSetup.as_view()),
    path('api/accounting/setup/<str:kind>/', AccountingSetup.as_view()),
    path('api/accounting/setup/<str:kind>/<int:pk>/', AccountingSetup.as_view()),
    path('api/health/', v.Health.as_view()),
    path('api/auth/register/', v.Register.as_view()), path('api/auth/login/', v.Login.as_view()),
    path('api/auth/logout/', v.Logout.as_view()), path('api/auth/password/', v.ChangePassword.as_view()),
    path('api/profile/', v.Profile.as_view()), path('api/dashboard/', v.Dashboard.as_view()),
    path('api/users/', v.Users.as_view()), path('api/users/<int:pk>/', v.Users.as_view()),
    path('api/roles/', v.Roles.as_view()), path('api/roles/<int:pk>/', v.Roles.as_view()),
    path('api/company/', v.CompanyView.as_view()),
    path('api/parties/', v.Parties.as_view()), path('api/parties/<int:pk>/', v.Parties.as_view()),
    path('api/workflows/', v.Workflows.as_view()),
    path('api/documents/', v.Documents.as_view()), path('api/documents/<int:pk>/', v.Documents.as_view()),
    path('api/documents/<int:pk>/action/', v.DocumentAction.as_view()),
    path('api/documents/<int:pk>/pdf/', DocumentPDF.as_view()),
    path('api/reports/', Reports.as_view()), path('api/logs/', v.Logs.as_view()),
]
