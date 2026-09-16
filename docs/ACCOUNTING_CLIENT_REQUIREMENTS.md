# Accounting extension — client requirements and implementation specification

Date: 11 September 2026

Status updated 12 September 2026: requirements retained; foundation development resumed after the user's go-ahead. Accounting setup/calendar forms and migration 0002 were added; a financial posting engine is not yet implemented. See IMPLEMENTATION_STATUS.md for implementation evidence and REVIEW_DECISIONS.md for the independent review corrections and current delivery gates. Android builds remain paused.

Confirmed by user: this is a registered company. Exact registered company type, applicable reporting framework and financial year remain to be confirmed later. Questions are retained for later review, not prerequisites to continuing requirements analysis. See LEDGER_CLIENT_ANALYSIS.md for the second screenshot and historical migration requirements.

## Client's message translated into English

“This is our general journal. We record every payment, expense, loan, profit, income—in short, all money coming in and going out—here. We have separate sheets for the important expense categories or accounts. For example, if a company's tender is in progress, we maintain all its financial account details on a separate sheet, and after entering the transaction here we have to enter it there as well.

“This is an informal arrangement. The fourth column is Category. In the software, the categories/accounts should be created first. When we open the journal entry form, we should be able to select a category, and entering the transaction once should also post it to the relevant ledger. The trial balance and complete accounts should then be generated automatically.

“In the screenshot, the white box in the Type column is a bank screenshot/supporting document attached as an object. There should be an option to upload that supporting evidence in the software too.

“This sheet meets our minimum requirements; the entry form can be made more comprehensive.”

The opening word is interpreted as “general journal” in context. The worksheet is more accurately a money movement register; it is not yet a balanced double-entry journal. The statement about the white object comes from the client's explanation; its contents cannot be verified from the screenshot.

## Intended result

Enter a transaction once, select its accounting purpose and optional project/tender, attach evidence, submit it for approval, and post it once. The daybook, general ledger, party ledger, project report and trial balance all read the same posted journal lines. There is no second entry into a separate project sheet.

The screenshot is a requirements reference. No names, amounts, dates, bank accounts or transactions from it will be imported automatically. An actual workbook and a reviewed import mapping are needed for historical migration. Embedded Excel objects require extraction/re-upload; they are not ordinary cell values.

## Compact menu and forms

Add one Finance section with Transactions, Accounts, Projects/Tenders, Cash & Banks, and Financial Reports. Reuse existing contacts, profiles, editable roles and workflow administration. Avoid a separate subsystem for each type of payment.

| Spreadsheet column | ERP field | Interpretation and rule |
|---|---|---|
| SR No | Voucher number; legacy reference | Server-generated unique voucher number; preserve old row reference separately during import. |
| Date | Transaction date | Editable business date in an open accounting period; default to today's date in Asia/Karachi. Creation, approval and posting timestamps are separate and server-generated. |
| Organization/Person | Party | Customer, supplier, employee, lender, borrower, investor or other party; a party can have multiple classifications. Reuse and extend the current Party model. |
| Category | Account plus Project/Tender | Separate economic classification from the job that it relates to. Existing category labels can become aliases/default mappings after review. |
| Amount (Rs) | Amount (PKR) | Decimal amounts; positive amount with explicit receipt/payment type. Do not infer direction from text colour or a minus sign. |
| Sent to | Beneficiary or project | Client must clarify. Use separate beneficiary and project fields if both meanings exist. |
| BANK | Company cash/bank account | Structured master linked to one ledger account; distinguish company account from beneficiary account. |
| AC No. | Selected account details | Account number/IBAN stored as text, preserving leading zeros. Mask on general lists; authorize full viewing separately. |
| Type | Payment method; instrument/reference | Separate Cash, Bank Transfer, Cheque, Card and Other from cheque/transaction reference numbers. Evidence is a separate attachment field. |
| Paid By | Handled by; funding source where relevant | Do not assume the staff member handling payment supplied the money. Personal payments on behalf of the business need a payable/owner account. |
| Remarks | Description/narration | Required explanation, with optional internal notes. |

### Accounts

Fields: unique account code, name, class (Asset, Liability, Equity, Income, Expense), parent account, active flag, posting/group flag, optional required party/project, financial statement mapping and cash-flow classification policy. Parent groups cannot receive postings. Referenced accounts may be deactivated but cannot be deleted; changing the class of an account with postings requires a controlled migration.

Initial account families should cover cash and banks, receivables, payables, customer advances, supplier/staff advances, loans receivable/payable, refundable deposits/bid securities, investments, fixed assets, equity, income and operating/project expenses. Exact codes and classifications require accountant review. No opening values are invented.

### Projects and tenders

Fields: unique code, name, client/party, tender/contract reference, dates, status and notes. Optional budget can follow later. Assign project per allocation line so one payment can be split between jobs. Closed projects reject new postings unless reopened by an authorized person. A project is a reporting dimension, not inherently an expense account.

### Transaction form

Start with an understandable transaction type: Money Paid, Money Received, Transfer Between Own Accounts, or Accountant's Journal. The advanced journal is restricted to authorized finance staff.

Header: voucher number, transaction date, type, party/beneficiary, description, external reference, handled-by person, supporting attachments and workflow status. Cash/bank method and instrument date/reference appear when relevant. One transaction is PKR in the first release; foreign-currency conversion is deferred rather than silently treated as PKR.

Allocation rows: account, optional party override, project/tender, line description and amount. The simple form generates the balancing cash/bank line. Advanced journals expose debit and credit columns. Show a plain-language preview of which accounts increase/decrease before submission.

Conditional fields: due date for an advance/loan where applicable; original invoice/voucher link for settlement; original transaction link for refunds/reversals. Tax/withholding splits require reviewed mappings and effective dates; do not add a universal hard-coded tax rate. Posted invoice settlements must clear receivables/payables rather than recognize income/expense a second time.

Cheque pending/cleared/bounced status and bank value date belong to settlement/reconciliation tracking. A bank balance from posted entries is not a claim that every cheque has cleared. Detailed reconciliation is a later milestone.

## Accounting rules and examples

These are illustrative entries, not imported client transactions or final classification advice.

| Event | Debit | Credit | Reporting consequence |
|---|---|---|---|
| Pay an immediately consumed office expense | Relevant expense | Bank/cash | Expense and cash movement. |
| Pay a previously recorded supplier bill | Supplier payable | Bank/cash | Clears a liability; do not expense it again. |
| Receive settlement of an existing customer invoice | Bank/cash | Customer receivable | Clears an asset; do not recognize income again. |
| Lend money | Loan receivable | Bank/cash | Creates an asset, not an expense. |
| Receive repayment of loan principal lent out | Bank/cash | Loan receivable | Not income; interest, if any, is a separate allocation. |
| Receive borrowed funds | Bank/cash | Loan payable | Liability, not income. |
| Repay borrowed principal | Loan payable | Bank/cash | Not an expense; interest separately classified. |
| Pay a refundable tender security | Refundable deposit | Bank/cash | Normally an asset; terms determine classification. A guarantee instrument may require different treatment. |
| Advance funds to staff/supplier | Staff/supplier advance | Bank/cash | Asset until settled against supported costs or refunded. |
| Transfer between company banks | Destination bank | Source bank | No income or expense; fees separately allocated. |

Land, investments, security payments, investor withdrawals and returned investments cannot be classified correctly from spreadsheet labels alone. Profit is calculated from recognized income less expenses; an amount described as “profit received” must be classified by its economic substance. Cash received is not always income, and cash paid is not always expense.

Income/expense and project profitability require accruals, bills, revenue recognition and other relevant adjustments, not just bank movements. A balanced trial balance alone does not establish completeness or correct classification.

## Posting, approval and update controls

Draft → Submitted → Approved → Posted, with Returned/Rejected branches. Administrator configures the approver role and whether approval triggers posting or posting requires a separate authorized action. Snapshot applicable workflow rules when submitted. Self-approval remains disabled by default.

Only Posted transactions feed official ledger totals. Drafts may appear in a clearly labelled pending register. Posted transactions cannot be edited or deleted. Correct them through a linked balanced reversal and replacement, preserving the original and the reason. Reversal is itself subject to authorization/approval. Report original and reversing lines together according to dates; never remove the original retrospectively.

Server validation: at least two lines; each line has exactly one positive debit or credit; decimal debit total equals credit total; active posting accounts; required party/project present; date in an open period; valid currency; mandatory evidence if configured; matching approved version. Revalidate at posting time, including periods/accounts closed after submission.

Use an atomic database transaction, locking, a unique source-posting constraint and an idempotency key. Double clicks, retries and competing approvers must not produce duplicate journal lines or voucher numbers. Reject edits to submitted/approved content; returning for edits invalidates approval and requires resubmission. Opening balances also use a reviewed, balanced journal.

Roles expose independent permissions for accounts/project/bank maintenance, transaction viewing/creation/editing/submission, approval, posting, reversal, period closing/reopening, evidence access, financial reports and export. Report drill-down and attachment downloads enforce the same record scope as the originating transaction. Existing users receive no silent new privileges. Audit logs remain available only through explicitly assigned log permissions, with no automatic administrator bypass.

## Supporting evidence

Allow multiple JPG/JPEG, PNG and PDF files per transaction, with original filename, evidence description, uploader, upload timestamp, size and content hash. Provisional pilot limit: 10 MB per file, configurable by administrator within server limits.

Use private storage with authenticated downloads; never expose bank evidence through public media URLs. Validate actual file content as well as extension, reject executable/active formats, use generated storage names and configure malware scanning for deployment. PDF downloads should use safe disposition. Attachment changes after submission require return/reapproval; posted evidence must not be silently replaced. Later supplemental evidence is separately attributed and logged. Back up database and evidence together and test restoration. Retention/deletion periods await the applicable business/legal policy.

## Reports and representation

First accounting outputs:

1. Transaction/daybook register: business date, voucher, party, account, project, money in/out, method, reference, status and evidence indicator.
2. General ledger: account, opening balance before selected start date, debit/credit movements, running and closing balance; stable date/voucher/line ordering.
3. Party ledger: receivables, payables, loans and advances distinguishable; avoid netting unrelated balances silently.
4. Project/tender statement: receipts/payments and balances by account; separate actual income/expense and profitability from cash movements.
5. Cash/bank book: each account's opening/movements/closing balance; reconciliation status distinctly labelled when implemented.
6. Trial balance: opening debit/credit, period debit/credit and closing debit/credit; includes nonzero opening balances with no period movement. Global totals reconcile to posted journals. A project-filtered analysis is not presented as the entity's statutory trial balance.

Next outputs: income statement, statement of financial position, cash-flow statement and other required statements/disclosures after account mappings, opening balances, accruals, accounting policies and the applicable reporting framework are confirmed. Management reports are not labelled audited or fully IFRS compliant.

Extend existing field-selection reports with date ranges, accounts, projects, parties, payment methods, statuses, sorting/grouping, saved definitions and authorized drill-down. Add monthly receipts/payments, expense by account, project cash movements and income/expense comparison charts. No double counting both sides of internal transfers as business receipts/payments. Colours are configurable and supported by labels/legends, not the sole meaning indicator.

Reuse CSV/XLSX/PDF export foundations; add A4/A3, portrait/landscape, repeated table headers, page numbering, company title, period, filter summary, generation timestamp and draft/final label. JPEG/PNG chart/report image export remains a distinct implementation deliverable; multi-page reports need numbered images. Excel exports preserve bank/reference values as text and neutralize spreadsheet formula injection in imported user text. Exports never bypass permission scopes.

## Architecture and integration with current source

Keep Django/DRF and Flutter; no additional service architecture is needed. Add a focused accounting package with Account, Project, CashBankAccount, AccountingPeriod, Voucher, JournalLine and Evidence models. Reuse Role, User, Party and AuditEvent; extend approval infrastructure without changing existing quotation/invoice behaviour. Introduce a source-document relationship for future invoice/bill settlement and unique posting identity.

Put all financial posting/reversal logic in server-side service functions, not Flutter or unrestricted model CRUD. Read reports from posted journal lines; do not store manually editable separate ledger-sheet copies. PostgreSQL is the target for production concurrency; SQLite remains local development only. Use database constraints and migration tests. Existing Company.bank_details is currently free text: introduce bank masters through a reviewed mapping, without guessing account data from that field.

Current baseline verified by source review: models cover users, roles, parties, quotations/invoices, workflow events, audit events and saved document reports. Accounting models and financial statements do not yet exist. Current Party kinds and Workflow kinds need extension; existing quotations do not post money. Keep live invoice issuance blocked until its own accounting/tax prerequisites are met.

## Delivery steps and acceptance evidence

1. Foundation: account/project/bank masters, periods, permission definitions and migrations. Check existing administrator login and unchanged existing records. User supplies approved account structure, company legal form and selected finance roles.
2. Transactions: simple and advanced forms, allocation lines, private evidence and approval/posting services. Test balanced/unbalanced entries, unauthorized access, immutable approved/posted content, attachments, period locks, retries, races and reversal. User tests one labelled synthetic receipt, payment, advance and transfer through Finance → GM.
3. Ledgers: daybook, party/project/cash ledgers and trial balance with opening balances, filters and exports. Verify totals against an independently calculated fixture, including no-movement opening accounts, reversals and transfers. User/accountant checks selected known examples and report layouts.
4. Statements and migration: reviewed account mappings, accrual/settlement integration, statement outputs and Excel import preview/deduplication. Import requires real source workbook, reviewed opening balances and a cutover date to avoid importing history plus the same balances twice. User approves mappings and reconciliation before live use.

No production bank, FBR, Excel-account or hosting credentials are needed for this analysis step. Tests above are acceptance requirements, not claims of completed validation.

## Unresolved client inputs

- Exact registered company type, reporting framework and financial year (registered-company status confirmed by user).
- Meaning of Sent to and Paid By, including personally funded business payments.
- Whether the bank/AC columns consistently identify the business account or sometimes the recipient account.
- Approved account list, project/tender list, bank/cash accounts, cutover date and reconciled opening balances.
- Classification/terms of loans, investments, land and performance securities; applicable tax/withholding treatment.
- Approver/poster assignments, evidence requirements and visibility of bank information.

These affect configuration/classification; they do not justify inventing entries from the screenshot.

## Reference basis

- IFRS Foundation, IAS 7: https://www.ifrs.org/issued-standards/list-of-standards/ias-7-statement-of-cash-flows/ — distinguishes operating, investing and financing cash flows; cash movements require appropriate classification.
- IFRS Foundation, IAS 1: https://www.ifrs.org/issued-standards/list-of-standards/ias-1-presentation-of-financial-statements.html/ — describes a complete financial statement set; a trial balance or daybook is not that set. Applicability and transition to newer requirements must be confirmed for the entity and reporting period.

These references support the accounting design principles, not a conclusion about which standards legally apply to this Pakistan-based entity. No tax rates or statutory compliance certification are inferred.
