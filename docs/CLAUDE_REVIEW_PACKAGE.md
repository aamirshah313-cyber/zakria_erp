

---

Source document: docs/INDEPENDENT_REVIEW_BRIEF.md


# Independent review request — Zakaria ERP

Review snapshot: 12 September 2026. This is a plan and implementation-status review, not a claim of audited accounting or a complete source-code/security audit.

## Instructions to the reviewer

Act as an independent ERP architect, accounting systems reviewer and application security reviewer. Critically assess the attached design. Do not assume the proposing assistant is correct. Identify concrete gaps, contradictions, unnecessary scope and unsafe accounting assumptions. Distinguish confirmed facts, proposed designs, unverified assumptions and implemented behaviour. If you cannot verify a claim from the material, say so rather than guessing.

Use current primary sources for financial reporting, Pakistan-specific requirements and technology claims. Cite sources and state applicability conditions. Registered-company status alone does not determine the applicable financial reporting framework, tax rules or statutory payroll rates. Do not invent company registrations, bank details, opening balances or rates.

Provide:

1. Executive assessment: suitable to proceed, proceed with corrections, or redesign needed, with reasons.
2. Findings table: ID, severity, affected requirement/section, problem, realistic failure example, recommended correction, implementation stage and acceptance test.
3. Accounting walkthroughs: supplier bill then payment; customer invoice then receipt; customer advance; staff advance and settlement; imprest replenishment; employee reimbursement; payroll accrual and payment; asset acquisition/depreciation/disposal; bank transfer; donations; tax/withholding split. Explain double-counting risks and policy-dependent treatments.
4. Architecture review: model boundaries, posting atomicity/idempotency, concurrency, immutable posted records and reversals, account hierarchy, party/project dimensions, fiscal periods, historical as-of reporting and source-document integration.
5. Access review: registration/activation, editable roles, separation of duties, workflow changes, amount thresholds, audit-only access, sensitive payroll/bank data and report/export/attachment authorization.
6. Excel migration review: multiple sheets, duplicated journal/ledger records, summary rows, opening balances, missing dates/counterpart accounts, attachment extraction, staged approval, idempotence and reconciliation.
7. Reporting review: general ledger/trial balance, receivables/payables, project cash versus profit, financial statements, account mappings, custom filters/fields/charts and exports.
8. A compact revised delivery plan, dividing production blockers from improvements that can follow the pilot.
9. Deferred client/accountant questions, prioritized without turning every unknown into a blocker to prototype development.

Do not claim to have run the software or verified source code from this design bundle. For source-level conclusions, list the precise files/tests you need. Do not ask for production passwords, tokens or databases.

## User context and constraints

- Business: Muhammad Zakaria and Sons, Islamabad; user confirms a registered company. Exact legal subtype, reporting framework, financial year and policies remain unconfirmed.
- Compact, extensible application with shared Windows desktop, Android and web interface. Current work targets the local web pilot; Android builds are paused.
- User wants standard accounting nomenclature, password-protected registered users, editable backend roles and configurable Finance-to-GM approvals. Logs are visible only to designated roles.
- Existing invoice screenshot is a layout/example only. Two later screenshots illustrate the client's general register and project ledger; user permits isolated temporary test use, not insertion into live books.
- One financial event should update all relevant ledgers/reports without duplicate manual entries.
- Custom and standard reports, charts, field selection, fiscal periods, as-of dates, print layouts and PDF/Excel/CSV/image exports are required. Calendar pickers replace mandatory typed dates.
- User requested progress and outstanding tasks after each main stage. A pause was subsequently lifted by “Do anything”; the limited accounting-foundation milestone resumed before this review request. Historical references to “paused” in the appended requirements describe earlier decisions, not a new instruction to the reviewer.

## Verified implementation baseline and current work

Existing pilot uses Django/DRF, local SQLite with PostgreSQL environment support, and Flutter for web/Windows/Android. Existing features include registration and administrator activation, password hashing, expiring hashed bearer sessions, profile editing, role/permission administration, contacts, quotation/invoice drafts, one-stage document approvals, quotation issuance/PDFs, restricted audit logs and saved document reports with field selection/basic charts/CSV/XLSX/PDF exports. Live invoice issuance is disabled. Reports currently summarize documents, not financial ledgers. There is no operational accounting posting engine.

Current foundation work adds account hierarchy, project dates, financial-year setup, an optional starter chart with no balances, and calendar controls in document/report forms. Accounting setup permits finance.manage or roles.manage to maintain master records; finance.view grants read access. This is an explicit access choice requiring review, not an automatic grant of posting or log privileges.

At the review snapshot, 22 backend tests passed, including six new accounting-setup tests. Flutter calendar/access verification and web rebuild are in progress. The new accounting migration has been generated but not yet applied to the live local database. No production readiness is claimed.

The preliminary Voucher/JournalLine/Evidence models are scaffolding only, with no exposed posting API. They are not an approved final schema: the party-name text must evolve to structured party relationships; transaction/source identity, cash/bank masters, complete workflow history, private file storage and posting/reversal invariants need further work. Current Evidence scaffolding stores binary data in the database; the target private-storage design must be resolved before evidence functionality ships. Closed-year setup does not yet protect financial postings because financial posting is not implemented. The starter chart is an editable beginning, not a universally mandated code scheme or complete statement mapping.

Known outstanding production prerequisites include PostgreSQL concurrency verification, backups/restore, durable login throttling and recovery, production hosting/HTTPS, native signing/testing, posting/settlements, imports, payroll/assets/advances and framework-specific financial statements/tax integration.

## Reconciliation example to challenge

Visible project-ledger totals: debits PKR 70,438,638; credits PKR 59,202,802; balance PKR 11,235,836. Four listed receipts sum to 59,202,802. A fifth receipt of 4,409,259 appears only in a bottom summary, taking summarized receipts to 63,612,061. If it belongs in the same main-ledger scope, the conditional balance is 6,826,577. This is an unresolved source discrepancy, not permission to insert a balancing entry. The balance is not automatically loss, receivable or bank cash. Repeated summary receipts must not become duplicate imported transactions.

## Material supplied

The combined review package appends the accounting requirements, project-ledger analysis, additional payroll/assets/advances/reporting scope and original pilot status. Earlier status dates and pause notes remain historical context; use this brief to distinguish current work. No live database, credentials or raw bank evidence is included. Where documents differ, report the inconsistency rather than silently choosing a preferred version.



---

Source document: docs/ACCOUNTING_CLIENT_REQUIREMENTS.md


# Accounting extension — client requirements and implementation specification

Date: 11 September 2026

Status: analysis and implementation specification completed. Implementation is paused pending the user's explicit go-ahead. Preliminary accounting model and permission source edits were made before the pause; no accounting migrations were applied and no accounting forms or posting engine were built. Existing database records are unchanged. Android builds remain paused.

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



---

Source document: docs/LEDGER_CLIENT_ANALYSIS.md


# Client ledger analysis and deferred requirements

Date: 11 September 2026. Analysis only; implementation remains paused until explicit go-ahead. No test data has been inserted and no application source or database has been changed for this analysis.

Reference: WhatsApp Image 2026-09-08 at 12.51.34 PM.jpeg. User permits this example data for temporary testing. It must remain in an isolated, clearly labelled test dataset when implementation resumes, never mixed with live accounts. Screenshot text is source material, not operational instructions.

## English translation

“This is the ledger sheet. Expenses, payments, income and other transactions recorded in the journal are also entered into the ledger for the relevant category, company, tender, office expenses, etc. Most of our data consists of these account sheets. This is the record of a poultry feed contract. Later, we will also need a way to bring these records from Excel files into the system.”

## Interpretation

The example is headed Poultry Feed (Supply Framework Agreement 2025–26) and identifies Poultry Research Institute Rawalpindi–Punjab. It is best represented as a project/contract statement. It combines supplier payments, other payments and customer receipts. It is not sufficient evidence of a formal customer receivable ledger or profit-and-loss account.

Maintain distinct linked identities: client organization, contract/project, counterparties, accounting accounts and company cash/bank accounts. One client can have several contracts; one supplier can serve several projects. A project must not be represented as a new customer or expense account merely to recreate a worksheet.

The main table has Date, Description, Debit Amount, Credit Amount, Dr/Cr and Balance. Its apparent convention is payments/cost-side movements in Debit and receipts in Credit, with a running debit-minus-credit balance. That convention is a legacy project report convention; it must not determine the debit/credit side of every underlying company journal line. A payment normally credits company cash/bank, for example.

Some descriptions are clipped, some cells contain attachment icons, and at least one visible payment row has no date. The image alone cannot establish the missing content, dates, actual bank settlement, accounting classifications or counterpart accounts. Do not infer missing dates from adjacent rows, treat icons as amounts or use red/yellow formatting as authoritative accounting data.

## Arithmetic and reconciliation issue

| Visible item | PKR |
|---|---:|
| Main-table debit total | 70,438,638 |
| Main-table credit total | 59,202,802 |
| Main-table debit balance | 11,235,836 |
| Receipt 1, 22 January 2026 | 5,009,642 |
| Receipt 2, 6 February 2026 | 12,208,127 |
| Receipt 3, 28 February 2026 | 22,705,104 |
| Receipt 4, 6 May 2026 | 19,279,929 |
| Receipt 5, 22 June 2026, bottom summary | 4,409,259 |
| Sum of five summarized receipts | 63,612,061 |
| Conditional balance if receipt 5 belongs in the main table | 6,826,577 |

The first four receipt amounts sum exactly to the main credit total. The fifth receipt appears in the bottom summary but is not visibly represented as a receipt in the main ledger, whose entries extend into July. The difference is 4,409,259. This is a reconciliation exception, not permission to insert a corrective transaction. It could be an omission or a scope/status difference; the workbook and supporting evidence must establish which.

Arithmetic checks confirm the relationships between displayed totals and listed receipts, not an independent audit or transcription of every debit row. The four repeated receipts at the bottom must not be imported again as new transactions.

The balance is a net project movement under the worksheet convention. It is not automatically a loss, a customer debt, available cash or recognized profit. If all debit values are actual project cash payments and all credits cash receipts with zero opening balance, it indicates net cash funded into the project. Those assumptions require confirmation.

## Proposed reports and forms

1. Project/contract master: code, title, customer, contract reference, start/end dates, status and optional delivery locations. Agreement year and accounting financial year are separate fields.
2. Entry form: account classification, project allocation, structured party, transaction date, payment/receipt type, bank/cash account, method/reference, amount, narration and private evidence. Split one payment among projects/accounts when needed. Preserve the full legacy description and source row reference.
3. Project activity statement: familiar date/description/payment/receipt/running-balance layout, configurable legacy Debit/Credit captions with an explicit legend. Separate cash activity from noncash journals and opening positions. Drill down to authorized source voucher and evidence.
4. Customer statement: invoice/debit adjustments, credit notes, receipts allocated to invoices and genuine outstanding balance. Customer money received before revenue is earned may be an advance/liability. A project funding gap must not populate customer receivables.
5. Project financial summary: recognized revenue, cost of sales, other eligible costs, margin, receivables/payables, advances and cash movements separately. Link delivered goods, bills and invoices when these modules are implemented.
6. Receipt schedule: generated from the same underlying receipt records, never a manually entered second table. Its scope/date/status filters must be visible and comparable to the main statement.

Project payments for feed may settle supplier payables, purchase inventory, pay advances or recognize eligible costs. They must not all immediately become expense. Under IAS 2, sold inventory's carrying amount is expensed in the period of related revenue recognition. Under IFRS 15, receipt timing alone does not determine revenue recognition; performance obligations matter. Exact company framework and contract terms remain pending.

Payments labelled “profit” or “share” require supporting agreements: they might be a contractual service cost, settlement, shareholder distribution or another item. Do not automatically classify them as expense. Recoverable tax, withholding credits, retention, bank fees and nonrecoverable tax should be separately allocated when applicable; no rate or recoverability is inferred from this image.

Preserve product/quantity/location descriptions. Optional structured quantity, unit, product and delivery reference fields should link to later procurement/inventory records. Do not parse clipped free text into purportedly verified stock movements.

## Excel migration design

Migration must support multiple ledger sheets, not only one flat journal. Use a staged process:

1. Upload workbook to a restricted import batch; keep a source hash and original file. Never execute workbook macros, formulas or embedded objects.
2. Select sheets and transaction regions; identify headers, opening balances, totals, footers, summaries and evidence objects. Preview full cell text rather than clipped display text. Support Excel serial dates and explicit day/month/year mapping.
3. Map each sheet to its project/account identity and each column to an ERP field. Save reusable mapping profiles. Map parties, banks and classifications through reviewed master matches, not uncontrolled fuzzy auto-creation.
4. Reconcile journal and ledger copies as candidate duplicates. Compare references, date, amount, direction and project; equal dates/amounts alone are insufficient. Choose an authoritative record, link supporting copies and send ambiguities for review.
5. Validate dates, amounts, bank references, opening balances, running balances and totals. Missing counterpart accounts, missing dates and the fifth-receipt discrepancy remain blocking row exceptions for posting. Raw source rows can remain staged without affecting books.
6. Show an import preview with proposed balanced vouchers, matches, exclusions and exception explanations. Summary receipts and totals are control data, not new postings. Where journal data lacks the second side, require a reviewed mapping; do not invent balancing bank entries or silently use suspense.
7. Approve the batch under import-specific permissions, create traceable drafts, then post through the established accounting workflow. Store workbook/sheet/row identity and unique import keys to make retries idempotent. Record history for each decision.
8. Reconcile record counts, payments, receipts, opening/closing balances and bank/party balances. Draft batches can be discarded; posted imports require controlled reversals rather than deletion. Full history and cutover opening balances must not duplicate the same activity.

Embedded bank screenshots need separate extraction into quarantined evidence or a re-upload mapping. An icon in a cell is not the underlying file. Protection, type checks and authorized downloads apply to migrated evidence as well as new uploads.

## Deferred client questions — saved, no immediate response required

- Is receipt 5 omitted from the main ledger, pending, or intentionally outside its scope?
- Which records are authoritative when the general journal and project sheet disagree?
- Do the legacy Debit entries represent actual payments only, or also bills, accruals and adjustments?
- What date belongs to the undated payment, and what are the full clipped descriptions?
- What do “profit/share” payments represent contractually?
- Are there opening balances, unpaid supplier bills, undelivered inventory, customer advances, retention or withholding deductions?
- What is the company's exact registered type, reporting framework and financial year? Registered-company status is already confirmed.
- Original deferred meanings of Sent to, Paid By, bank-account ownership, and evidence/access rules remain on the earlier requirements list.

## Test scenarios once implementation is authorized

- First four receipts total 59,202,802; five total 63,612,061.
- With supplied aggregate debits, display 11,235,836 for the original scope; with confirmed fifth receipt included, display 6,826,577. Label these as test reconciliation controls, not independently verified books.
- Import excludes repeated bottom receipt summaries and totals; re-import does not double post.
- Both summary and detailed report derive from the same records and reconcile when their filters match.
- Missing date/classification and conflicting worksheet copies produce actionable exceptions.
- Ledger opening/movements/closing reconcile; a negative legacy net balance is displayed correctly with its sign/Cr indicator.
- Supplier settlements and customer receipts do not duplicate costs/revenue already posted through invoices/bills.
- Test records and attachments remain isolated from live records, use TEST labels, and are removable without affecting live accounting.

## Sources

- IFRS Foundation, IAS 2: https://www.ifrs.org/issued-standards/list-of-standards/ias-2-inventories/
- IFRS Foundation, IFRS 15: https://www.ifrs.org/issued-standards/list-of-standards/ifrs-15-revenue-from-contracts-with-customers/

These support design principles; they do not establish the company's applicable statutory framework or certify compliance.



---

Source document: docs/ADDITIONAL_FINANCE_SCOPE.md


# Additional accounting scope — 12 September 2026

Status: requirements only. Application implementation remains paused pending explicit authorization. These requirements extend, rather than replace, ACCOUNTING_CLIENT_REQUIREMENTS.md and LEDGER_CLIENT_ANALYSIS.md. Registered-company status is confirmed; detailed framework, policies and financial year remain deferred inputs.

## Standard terminology and chart of accounts

Use Financial Accounting, Chart of Accounts, General Journal, General Ledger, Payment Voucher, Receipt Voucher, Journal Voucher, Cash Book, Bank Book, Bank Reconciliation, Trial Balance, Statement of Financial Position (Balance Sheet), Statement of Profit or Loss, Statement of Cash Flows and Statement of Changes in Equity as applicable. Use Employee Compensation for pay, allowances, benefits, bonuses and other remuneration. Labels must describe actual accounting behaviour; drafts must not be labelled posted and cash funding gaps must not be labelled profit/loss.

Chart hierarchy: assets (current/non-current), liabilities (current/non-current), equity, income and expenses, with reporting mappings and optional subgroups for cost of sales, administrative and other expenses. Codes are configurable internal identifiers, not a claimed universal mandatory numbering standard. Parent/group accounts cannot receive postings. Separate control accounts and party subledgers. Referenced accounts can be deactivated but cannot be deleted or freely reclassified after posting. Track cash/bank accounts individually.

## Employee compensation and payroll

Inputs: employee identifier, designation, employment dates/status, pay period, effective-dated basic salary, allowances, benefits/perquisites, overtime where applicable, bonuses, other remuneration, deductions, recoveries, employer contributions, payment details and accounting/project allocation. Sensitive employee and pay information needs separate permissions.

Distinguish recurring from one-off items; cash from noncash benefits; employer costs from employee deductions; earned remuneration from salary advances. Tax/contribution rules and effective dates require reviewed configuration, not invented rates. Payroll register → review/approval → balanced payroll accrual → payment settlement, without recognizing payroll expense twice. Support payslips, payroll summaries, deduction/payable schedules and reconciliation to ledger. Payroll scope can be delivered incrementally; no unsupported claim of automatic statutory compliance.

## Cash, banks and adjustments

Provide separate cash accounts, petty cash/imprest accounts and bank accounts. Record receipts, payments, bank-to-bank/cash transfers, fees and opening balances. Cash Book and Bank Book show opening balance, movements and closing balance. Adjusting Journal Vouchers cover approved accruals, prepayments, corrections and other supported noncash adjustments; use linked reversals where required. Distinguish document, posting and bank value dates. Period locks apply.

## Reconciliations

Bank reconciliation: statement upload/manual entry, statement period/opening/closing balances, matching including split/group matches, outstanding deposits/payments, uncleared cheques, bank fees and differences. Imported statement lines are evidence, not automatic duplicate postings. A matched statement line cannot be reused without controlled unmatching. Save reviewed reconciliation snapshots.

Also provide cash count reconciliation, customer/supplier control-account reconciliation, payroll payable reconciliation and advance/imprest reconciliation. Differences require an explanation and approved adjustment; no automatic plug entries.

## Fixed assets and valuation

Inputs: asset code/class, description, acquisition and available-for-use dates, supplier/source document, cost, location, custodian, useful life, residual value, depreciation method, accumulated depreciation, impairment, disposal and relevant valuation evidence. Reporting includes cost, accumulated depreciation, impairment and carrying amount as of the selected reporting date, with movement schedules.

Support an accountant-configured policy for depreciation and, where applicable, revaluation/impairment. Historical as-of reports must use effective-dated movements, not today's overwritten asset value. Fair-value/revaluation amounts need approved evidence and policy; the software must not estimate them from unsupported assumptions. Land and depreciable assets require distinct treatment. Disposal entries link proceeds, carrying amount and gain/loss. Full policy-specific treatment and statement mappings must be reviewed before production use.

## Advances, imprest and reimbursement

Separate salary advances, temporary staff advances, supplier advances and standing imprest. Inputs: recipient/custodian, purpose, sanctioned limit, issue date, settlement due date, funding account, project, approvals and evidence. Track issuance, supported expenditure, unused cash refund, further amount payable and outstanding balance. Salary advance recoveries link to payroll.

Imprest register shows authorized float, cash held, supported expenditure awaiting replenishment and shortages/excesses. Replenishment restores the float and must not duplicate already recognized expenditure. Prevent the same receipt being claimed against both an advance and a reimbursement.

Reimbursement Claim: claimant, expense dates, itemized eligible costs, accounts/projects, receipts, policy limits where configured, approval, employee payable and settlement. Support partial approval with reasons and traceable adjustments. Reports include advance aging, overdue settlements, imprest reconciliation and claims awaiting approval/payment.

## Donations

Distinguish donations paid and received, cash/noncash, donor/recipient, purpose, restrictions/conditions where applicable, supporting evidence, approvals and relevant tax classification. Do not assume donations received are immediately unrestricted income or donations paid are automatically deductible. Treatment follows the applicable framework and facts. Provide a donation register and related ledger/report mappings; use confidential access where appropriate.

## Periods and reporting

Fiscal-year start/end dates are configurable and accountant-confirmed. Provide as-of date, custom date range, monthly, quarterly, half-yearly and annual presets aligned to the configured financial year. “Bi-annually” is provisionally interpreted as twice yearly; label the UI Half-yearly to avoid ambiguity.

Point-in-time reports: statement of financial position, outstanding balances, aging and asset carrying amounts. Period reports: profit/loss, cash flows, payroll, donations and transaction movements. Statements must distinguish opening balances, period activity and closing balances; dated adjustments and reversals must preserve historical reproducibility. Comparative period/year options and fiscal-year-to-date reporting are required.

Standard outputs: trial balance, general ledger, cash/bank books, reconciliations, financial statements and supporting schedules, receivable/payable aging, payroll/payslips, advances/imprest, reimbursements, asset register/depreciation/valuation movements and donation register. Financial statement completeness depends on reviewed policies, opening balances and all applicable adjustments/disclosures.

Custom reports: permitted fields, filters, grouping, sorting, totals, saved definitions, comparison periods and chart choices. Apply access restrictions to results, drill-down and exports, including payroll and bank evidence. Support A4/A3, orientation, repeated headers, page numbering, financial period/as-of date, company identity, generated timestamp, draft/final status and user-configurable accessible colours. Retain PDF/XLSX/CSV and planned JPEG/PNG exports. Custom metadata must not bypass posting/accounting validation.

## Revised delivery sequence after authorization

1. Chart of Accounts, fiscal periods, parties/projects, cash/banks and permission foundation.
2. Vouchers, supporting evidence, approvals, posting/reversal and period controls.
3. Ledgers, trial balance, cash/bank books and reconciliation.
4. Advances, imprest and reimbursement claims with settlement controls.
5. Supplier bills, customer documents, settlement and reviewed historical Excel migration.
6. Employee compensation/payroll and fixed assets as separate manageable increments; donations integrated with vouchers/registers.
7. Financial statements, supporting schedules and expanded custom/graphical reporting, validated against the underlying ledgers.

Useful reports should ship with each increment rather than all being deferred to the final stage. Every stage must include relevant tests and clear user verification actions. Implementation may reorder independent increments following priorities, but financial statements cannot claim completeness before their source balances and policies are ready.

## Calendar date selection — user requirement

Use calendar date pickers wherever users select a date, rather than requiring manual typing. Cover voucher/transaction dates, invoice and quotation dates, due dates, project/contract dates, employment dates, payroll periods, advance issue/settlement dates, reimbursement expense dates, asset acquisition/available-for-use/valuation/disposal dates, bank statement and clearance dates, financial-year settings, period closing dates and report filters.

Provide single-date pickers for individual dates and start/end date selection for ranges. Report filters include As at Date and From/To, with monthly, quarterly, half-yearly, annual and financial-year-to-date presets. Use clear display formatting such as 12 Sep 2026, retain date-only values without timezone shifts, and use accessible responsive calendar controls on web, desktop and mobile.

Apply sensible contextual defaults without silently replacing historical dates. Require end dates not to precede start dates; apply field-specific rules and accounting-period locks on the server as well as the interface. Allow legitimate future due dates and historical transactions in open periods. Optional dates remain empty until selected and can be cleared. Created/approved/posted timestamps remain automatic, read-only server values and are not calendar inputs. Historical imports use validated date mappings rather than requiring individual calendar selection.

## Deferred inputs retained for later

Financial year and applicable framework; approved chart and opening balances; payroll structure and statutory rules; asset register and valuation/depreciation policies; advance/imprest limits and settlement rules; donation circumstances; role assignments and approval limits. No immediate client response required for this requirements update.



---

Source document: docs/IMPLEMENTATION_STATUS.md


# Implementation status — 6 September 2026

This is a development pilot, not a production ERP. The supplied invoice is a layout reference only. No example party, tax, bank or product data has been imported into the business database.

## Milestone 1 — backend foundation
Implemented Django API, SQLite local database, PostgreSQL environment configuration and schema migrations. All money calculations use decimals on the server. Local SQLite is for single-machine pilot development; production PostgreSQL concurrency and backup validation remain outstanding.

User action: verify the company legal name, address and tax registrations in Company settings after initial setup. Do not enter financial opening balances yet.

## Milestone 2 — accounts and approvals
Implemented password hashing, pending registration, administrator activation, one editable role per user, permission-controlled navigation and API access, profile editing, password change, expiring sessions, editable one-stage quotation/invoice approval rules, blocked self-approval by default, and restricted read-only audit logs. Rule versions are snapshotted on submission. Users cannot edit submitted, approved or issued documents. Audit access has no implicit administrator bypass.

User action: create the first administrator using bootstrap; have Finance, GM and audit staff register; assign and activate roles from Users. Test the intended permission matrix. Administrator initially has no log access. Assign Audit Reviewer only to the designated person, or explicitly configure another designated role.

Outstanding: email verification and self-service forgotten-password recovery, durable distributed login throttling for production, optional MFA, approved delegation and approval thresholds. Profile photo is not yet included. Login tokens are kept only in app memory; users sign in again after closing the app.

## Milestone 3 — contacts, documents and reporting
Implemented customer/supplier records; quotation and invoice drafts with multiple lines; explicit tax treatment; return/reject comments; quotation issuance after approval; preserved issued company/customer snapshots; PDF preview/printing; field-selected reports, filters, grouping, horizontal bar summaries, saved personal report definitions and CSV/XLSX/PDF exports. Reports are document registers, not posted sales or financial statements. Maximum pilot report size: 5,000 documents. Contact/document lists have bounded pilot limits.

User action: create a clearly labelled test contact and quotation after setup. Submit as Finance, approve as GM, export and check the layout. Confirm report fields and terminology. Use only test records during this pilot.

Outstanding: ledger, purchases, expenses, payments, reconciliation, tax/FBR integration, standard financial statements, document conversion, quotation revision after issuance, custom field administration, Excel import previews, additional chart types/drill-down, JPEG/PNG export, shared dashboards, full template designer and wider document fields.

Live invoice issuance is deliberately disabled until accounting and tax readiness are implemented and tested. Do not use draft PDFs as tax invoices.

## Milestone 4 — deployment and apps
Flutter application source targets Windows, Android and a browser preview. Android cleartext networking is enabled only for debug builds; production must use HTTPS. The browser preview and local API are development servers. Windows and Android release signing, installer/update delivery, real-device tests, production hosting and recovery drills remain release prerequisites.

User action: retain control of release-signing keys, hosting and domain accounts. Configure external integrations only after the corresponding connectors are implemented. No external integration credentials are needed for this milestone.

## Next development order
1. Complete real-device pilot checks and correct any usability issues.
2. Add validated Excel contact imports and password recovery/verification.
3. Add chart of accounts, purchases, expenses and settlements with reconciled ledger tests.
4. Add accountant-approved taxes and required FBR connector before enabling live invoices.
5. Extend reports, graphical exports, template settings and custom fields.
6. Harden PostgreSQL deployment, backups, signed releases and updates.

## Verified results and packaging prerequisites

- Database migrations and Django system checks passed.
- 16 backend tests passed, including password/session controls, restricted logs, approval guards, exact totals, document snapshots and PDF/Excel exports.
- 2 Flutter access/registration tests passed.
- 2 responsive layout tests passed at 1440×900 and 390×844. Readable render images are in `apps/client/test/goldens`.
- Flutter browser build completed successfully; the local preview responded HTTP 200.
- Windows build is blocked by disabled Developer Mode / symlink support. Flutter doctor also confirms Visual Studio is missing. User action: enable Developer Mode and install Visual Studio's Desktop development with C++ workload, including the Windows SDK.
- Android debug packaging is a separate test deliverable; release signing and physical-device verification are still outstanding.

Build images and browser bundles are development outputs. No production administrator password, bank details, tax registrations or integration credentials have been invented or stored.

