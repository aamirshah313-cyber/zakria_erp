# V2.1 — data management, reporting and Excel imports

This increment extends the client's single-entry receipt/payment register and linked ledgers. It does not introduce double-entry financial statements. The original pilot database remains outside this deployment.

## Delivered behavior

- **Transaction register → Data management:** remove and restore receipt/payment drafts, opening/transfer drafts, uncommitted import batches and quotation/invoice drafts. Archive and restore categories, cash/bank accounts, projects, parties and personal report layouts. Every action requires a reason and a current record revision. Evidence, import provenance and audit history remain retained. Submitted items must first be returned; confirmed transactions use the existing authorized cancellation workflow. Approved/issued documents cannot be erased. User accounts are suspended through user management.
- **Receipt/payment entry → Reporting classification:** Income received, Expense paid, Other funds movement or Pending classification. Direction and transaction nature are validated. Loan principal, advances, deposits, investments and capital movements must not be classified as operating income/expense. Existing records default to Pending classification; no historical meanings were guessed.
- **Reports / Print:** income, expense and pending-classification presets; beneficiary, handler, reference and amount filters; grouping by day, fiscal quarter/year, payment method, nature, classification, preparer and approver in addition to existing groupings. Saved layouts, selectable fields, charts and PDF/XLSX/CSV/PNG/JPEG exports remain available with the existing page size/orientation options. Amount filters select the original voucher before allocations. These are cash-basis register reports, not an accrual profit-and-loss account or statutory balance sheet.
- **Import setup records:** inspect, preview and commit new categories, parties, cash/bank accounts and projects from XLSX or CSV. Exact template headers are required. Existing records are never overwritten. Import parents/clients before dependent records. Signed previews expire after 30 minutes and bind the file, selection, user and resolved references; changes require a fresh preview. Commits are atomic and audited.
- **Import spreadsheet → Download testing workbook:** seven sheets contain guidance, four setup templates, eight synthetic transactions and four adapted client-ledger example rows. Identifiers use text formatting; dates use date cells. Transaction imports retain field mapping, duplicates/exclusions, control totals and draft-only commit. Split allocations can be completed on imported drafts. Opening balances and transfers still use their dedicated forms.

## Testing workbook and sequence

File: `outputs/v2-import-kit/V2-Testing-and-Import.xlsx`; the same workbook is bundled in `backend/resources` for authenticated download.

1. Import Categories, Parties, Accounts, then Projects through **Import setup records**, reviewing each preview before commit.
2. Import Transactions through **Import spreadsheet** with single amount/direction mapping. Control totals: receipts PKR 2,110,000; payments PKR 1,548,000.
3. Optionally import Client ledger excerpt using separate receipt/payment columns. Control totals: receipts PKR 5,009,642; payments PKR 521,500. This is an incomplete example, not a migration of the full screenshot ledger.
4. Review imported drafts in the normal forms, attach supporting evidence if needed, then use the configured independent approval process. Unconfirmed drafts do not enter confirmed ledger totals.
5. Remove an unwanted draft with a reason; enable the removed-record view and restore it. Test confirmed cancellation only through an authorized role.
6. Compare income/expense and grouped reports with the confirmed entries; check a PDF and an Excel export.

The screenshot's separate receipt schedule includes PKR 4,409,259 not reflected in its main receipt total. Obtain the original workbook and reconcile the difference before a complete historical migration. Embedded screenshot objects are not imported as evidence automatically; upload the original supporting files to the relevant entries.

## Permissions and data deployment

`register.delete` controls data management; setup record changes also require `register.manage`. Quotation/invoice removal additionally requires the corresponding view/create permission. Confirmed cancellation retains the separate `register.cancel` permission. Sensitive bank identifiers require `register.bank_details`; master imports require both `register.manage` and `register.import`. Audit-log visibility remains restricted to its designated permission.

Migration 0009 and the explicit Administrator `register.delete` activation were applied to `storage/v2-desktop/register.sqlite3` after an integrity-checked backup at `storage/backups/before-register-extension-20260915-164701-038765.sqlite3`. Existing users, passwords and transaction count were preserved; no example business records were seeded. The pilot database hash was unchanged during migration verification.

## Verification and remaining acceptance

62 backend tests and 13 Flutter interface tests pass, including actual delivered-workbook imports, classification/filter calculations, permission checks, recoverable removal, protected confirmed records, changed-reference rejection between import preview and commit, and removal of stale action buttons after a failed record selection. Django reports no missing model migrations. Automated imports use a temporary test database. Static analysis of the changed application files reports no issues; a broader scan reports 16 pre-existing informational lint findings in unrelated files.

The browser build is version 2.1.0+3 at http://127.0.0.1:5174/, with the isolated backend on port 8766. The served JavaScript was compared byte for byte with the new build. Existing Administrator/Finance Manager endpoint checks passed, including Administrator access to data management and workbook download. The frozen backend also passed versioned health and unauthenticated-access checks, and contains the testing workbook.

User action: sign out/in after updating to refresh permissions. The administrator should assign cancellation, import and sensitive-bank access deliberately, and activate an independent approver account before transaction acceptance. An active General Manager account was not found during the preceding deployment checks.

Remaining deliverables beyond this increment: client manual acceptance; a general-purpose Windows installer and reviewed transfer to another computer; user-facing backup/restore; binary evidence for openings/transfers; fuller historical workbook migration once originals are supplied. Android and full double-entry/payroll/assets/statutory accounting remain deferred pending client authorization.
