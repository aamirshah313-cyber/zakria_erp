# Additional accounting scope — 12 September 2026

Status updated 12 September 2026: this document specifies requirements, not completed functionality. Foundation implementation subsequently resumed after user authorization. See IMPLEMENTATION_STATUS.md for delivered work and REVIEW_DECISIONS.md for independent-review corrections. These requirements extend, rather than replace, ACCOUNTING_CLIENT_REQUIREMENTS.md and LEDGER_CLIENT_ANALYSIS.md. Registered-company status is confirmed; detailed framework, policies and financial year remain deferred inputs.

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
