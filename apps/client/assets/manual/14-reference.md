# 14. Reference

## Record statuses

| Record | Statuses |
|---|---|
| Receipt / payment, opening, transfer | `draft` → `submitted` → `confirmed` → `cancelled`; `deleted` for a removed draft |
| Spreadsheet batch | `staged` → `reviewed` → `imported`; `deleted` |
| Quotation / invoice | `draft` → `submitted` → `approved` → `issued`; `returned`, `rejected`, `deleted` |
| Account | `pending` → `active` → `suspended` |
| Setup record | active or archived |

## Reference numbers

| Prefix | Meaning |
|---|---|
| `REG-000001` | Receipt or payment |
| `OP-000001` | Confirmed opening balance |
| `TRF-000002` | Internal transfer |
| `QUO-2026-000012` | Quotation |
| `INV-2026-000013` | Invoice |
| `JV-000001` | Accounting voucher (model only; no posting exists) |

## Limits

| Area | Limit |
|---|---|
| Supporting documents | 10 per record, 5 MB each, PNG / JPEG / PDF with matching signature |
| Allocation lines | 1–50, adding exactly to the transaction total |
| Spreadsheet import | 5 MB, 20 sheets, 1,000 transaction rows, 40 columns, 4,000 characters per cell |
| Setup-record import | 1,000 records per file |
| Register list | 100 rows per page |
| Data management list | 50 rows per page |
| Statement | 50,000 records examined, 10,000 rows returned, 2,000 rows in a PDF |
| Document reports | 5,000 documents |
| Documents (pilot) | 200 lines each |
| Cancellation / removal reason | 1–1,000 characters |
| Document withdrawal reason | 1–500 characters |
| Import exclusion reason | 5–500 characters |
| Session | 8 hours |
| Restore preview | 30 minutes |
| Kept restore upload | 1 hour |
| Password recovery | 10 attempts per 15 minutes; administrator-issued code expires in 30 minutes |
| Automatic backups kept | 7 |
| Request body (local service) | 64 GB, for large restores |

## API endpoints

Everything the application does goes through these. All of them require a `Bearer` token
except where noted, and the register endpoints exist only in desktop mode.

| Method and path | Purpose | Permission |
|---|---|---|
| `GET /api/health/` | Service, version, mode | none |
| `GET POST /api/setup/` | First-run check and first administrator | none (desktop, until set up) |
| `POST /api/setup/restore/` `…/apply/` | Restore into a new installation | none (desktop, until set up) |
| `POST /api/auth/register/` | Request an account | none |
| `POST /api/auth/login/` `…/logout/` | Sign in and out | none / session |
| `POST /api/auth/password/` | Change own password | session |
| `POST /api/auth/recovery-codes/` | Create own recovery codes | session |
| `POST /api/users/<id>/reset-code/` | Issue a one-time reset code | `users.reset` |
| `POST /api/auth/reset-password/` | Reset with a code | none |
| `GET PATCH /api/profile/` | Own details | session |
| `GET PATCH /api/users/` `…/<id>/` | Accounts, status and role | `users.manage` |
| `GET POST PATCH /api/roles/` `…/<id>/` | Roles and the permission catalogue | `roles.manage` (read: also `users.manage` / `workflows.manage`) |
| `GET PATCH /api/company/` | Company details | read: session; write: `company.manage` |
| `GET POST PATCH /api/parties/` | Customers and suppliers | `parties.view` / `parties.edit` |
| `GET /api/dashboard/` | Overview figures | session |
| `GET /api/logs/` (`?export=csv`) | Audit log | `logs.view` / `logs.export` |
| `GET POST /api/register/masters/` `…/<kind>/` | Register setup records and approval role | `register.view` / `register.manage` |
| `POST /api/register/master-import/` | Import setup records | `register.manage` + `register.import` |
| `GET /api/register/import-template/` | Download the testing workbook | `register.view` |
| `GET POST /api/register/entries/` | List and create receipts/payments | `register.view` / `register.create` |
| `PUT POST /api/register/entries/<id>/action/` | Edit a draft; submit, confirm, return, cancel | `register.create` / `.approve` / `.cancel` |
| `GET POST /api/register/entries/<id>/attachments/` `…/<doc>/` | Supporting documents | `register.view` / `register.create` |
| `GET POST /api/register/positions/` `…/<id>/` `…/<id>/attachments/` | Openings and transfers | same as entries |
| `GET /api/register/ledger/` (`?export=csv`) | Activity ledger | `register.view` / `register.export` |
| `GET POST /api/register/reports/` | Report options; build and export | `register.view` / `register.export` |
| `POST /api/register/report-templates/` | Save, update, archive a layout | `register.view` |
| `POST /api/register/imports/inspect/` `/api/register/imports/` `…/<id>/` | Spreadsheet staging, preview, commit | `register.view` + `.create` + `.import` |
| `GET POST /api/register/data-management/` | Remove and restore | `register.delete` |
| `GET POST /api/system/backups/` `…/<name>/` | List, save, download backups | `system.backup` |
| `POST /api/system/restore/` `…/apply/` | Preview and apply a restore | `system.restore` |
| `GET POST PUT /api/documents/` `…/<id>/` `…/<id>/action/` `…/<id>/pdf/` | Quotations and invoices | `quotation.*` / `invoice.*` |
| `GET POST /api/workflows/` | Approval rules | `workflows.manage` |
| `GET POST /api/reports/` | Document reports | `reports.view` / `reports.export` |
| `GET POST PATCH /api/accounting/setup/…` | Accounting master data | `finance.view` / `finance.manage` / `roles.manage` |

## File formats

| Purpose | Format |
|---|---|
| Backup | `.zerp-backup` — a zip holding `manifest.json` and the database, optionally AES-256-GCM encrypted |
| Supporting document | PNG, JPEG, PDF (name and signature must match) |
| Import source | XLSX or UTF-8 CSV |
| Report export | PDF, XLSX, CSV (UTF-8 with BOM), PNG, JPEG |
| Ledger and audit export | CSV |

## Concurrency and safety rules

- **Versions.** Every record carries a version; actions send the version they saw and are
  refused if it moved on.
- **Request keys.** New entries and positions carry a one-time key, so a repeated click
  cannot duplicate a record; reusing a key with different content is refused.
- **One writer at a time.** Register writes take a lock on the company row, so two people
  cannot slip past the same cut-off check simultaneously.
- **Separation of duties.** A preparer cannot confirm their own record, even holding both
  permissions.
- **No implicit privilege.** There is no superuser bypass; the Administrator role has no
  audit-log access.

## Glossary

| Term | Meaning |
|---|---|
| **Entry** | One receipt or payment |
| **Position** | An opening balance or an internal transfer |
| **Allocation** | A share of one transaction assigned to a category and project |
| **Master / setup record** | Category, cash-bank account, project or party |
| **Opening balance** | The figure in hand at the moment history starts, for one scope |
| **Internal transfer** | Money moved between the company's own accounts |
| **Reporting class** | Whether a movement is income, expense or neither |
| **Nature** | Why the money moved: operating, advance, loan, deposit, investment, capital, donation |
| **Basis note** | The sentence on every report explaining what the figures are |
| **Batch** | One staged spreadsheet import |
| **Control total** | The verified receipt/payment totals typed from the source document |

## Related documents

| Document | Covers |
|---|---|
| ../V2_INSTALLER.md | Installing, upgrading, uninstalling, silent switches |
| ../V2_BACKUP_RESTORE.md | Backup internals, encryption, staging, clean-up |
| ../RELEASING.md | Building and publishing a release |
| ../IMPLEMENTATION_STATUS.md | What is built, what is next |
| ../V2_DESKTOP_SCOPE.md | The agreed scope of the desktop register |
| ../V2_INCREMENT_5.md | The current increment's acceptance detail |
