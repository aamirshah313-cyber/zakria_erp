# Independent review — Zakaria ERP accounting design

Reviewer role: independent ERP architect, accounting systems reviewer, application security reviewer.
Date of review: 12 September 2026.
Material reviewed: `CLAUDE_REVIEW_PACKAGE.md` only (INDEPENDENT_REVIEW_BRIEF, ACCOUNTING_CLIENT_REQUIREMENTS, LEDGER_CLIENT_ANALYSIS, ADDITIONAL_FINANCE_SCOPE, IMPLEMENTATION_STATUS).

## Scope and limits of this review

I did not run the software, read source code, inspect a database, or see the client's workbook or screenshots. Every statement about implemented behaviour below is a statement about **what the package claims**, not about verified code. Section 12 lists the precise files and tests I would need to convert those claims into findings.

Arithmetic in the reconciliation example was independently recomputed from the figures supplied (§7.3). It confirms internal consistency of the stated numbers only — not the underlying records.

Pakistan-specific statements are sourced and carry applicability conditions; rates and thresholds change annually and must be confirmed with the company's tax adviser against the current Finance Act and SRO position before anything is configured.

---

## 1. Executive assessment

**Proceed with corrections.** Not a redesign.

The design is better than most first-pass ERP accounting specifications. Three things in particular are right, and they are the things usually got wrong: it refuses to invent data from screenshots; it separates *cash movement* from *income and expense* explicitly and repeatedly; and it identifies the legacy worksheet as a money-movement register rather than a double-entry journal, which is the single most consequential correct call in the package.

The gaps are structural rather than philosophical, and they cluster in one place: **the model is designed to record transactions, not to settle them.** Five findings (A1, A2, A5, B1, B3) must be closed before the first real voucher is posted, because each becomes materially more expensive after posted data exists. None requires abandoning the approach.

What would change my assessment to "redesign needed": posting the first live voucher without a settlement/allocation model (A1), or applying the scaffolding migration to a database that will carry forward (B8).

The honest summary of where this stands: the package is a good *requirements* document and a thin *design* document. It states many correct rules ("do not use suspense", "no duplicate postings", "control accounts separate from subledgers") without specifying the mechanism that enforces them. Most of my findings are of that shape — a correct rule with no enforcement behind it.

---

## 2. Findings summary

Severity: **B** = blocker before any real posting · **H** = high · **M** = medium · **L** = low.

| ID | Sev | Area | Problem in one line |
|---|---|---|---|
| A1 | B | Accounting model | No settlement/allocation entity; aging and outstanding balances are not computable |
| A2 | B | Accounting model | No year-end close or retained-earnings policy; balance sheet will not balance in year 2 |
| A3 | H | Accounting model | Deductions at settlement (withholding, retention, charges) not modelled |
| A4 | H | Compliance | FBR digital invoicing is a live constraint, not a future connector |
| A5 | B | Accounting model | Control-account ↔ subledger integrity asserted but not enforced |
| A6 | H | Fixed assets | Asset register ↔ GL reconciliation and depreciation posting unspecified |
| A7 | M | Payroll | Employee-benefit provisions (gratuity, leave) absent from scope |
| A8 | M | Accounting model | Decimal precision, rounding mode and remainder allocation unspecified |
| A9 | M | Accounting model | Reversal date policy undefined for closed periods and settled items |
| A10 | M | Accounting model | Document / accounting / value date model contradictory between documents |
| A11 | M | Accounting model | Currency columns omitted from schema despite PKR-only being a policy, not a design |
| A12 | M | Migration | Cutover vs opening-balance exclusivity is a rule with no mechanism |
| A13 | M | Reporting | Cash-flow statement method not chosen; supporting data not planned |
| B1 | B | Architecture | Voucher number assigned at draft creation; gaps and races guaranteed |
| B2 | B | Architecture | Concurrency and idempotency guarantees are untestable on SQLite, the only tested environment |
| B3 | B | Architecture | Posted-record immutability enforced only in the service layer |
| B4 | H | Access | Role administration not separated from financial master data or audit access |
| B5 | H | Access | No amount thresholds and no delegation, in a one-GM approval chain |
| B6 | H | Architecture | No aggregation strategy; ledgers inherit a 5,000-row pilot cap |
| B7 | M | Architecture | Business date derived from server time lands on the wrong day before 05:00 PKT |
| B8 | M | Architecture | Unapplied scaffolding migration should be squashed, not applied |
| B9 | M | Security | Evidence-in-database conflicts with the stated backup and private-storage design |
| B10 | M | Architecture | No legal-entity dimension; retrofitting one after posting is expensive |
| B11 | L | Security | Permission revocation against live sessions unverified |
| B12 | L | Security | Field masking conflated with permission scope; exports unrated and unlogged |
| C1 | H | Migration | Blanket "no suspense" leaves the importer unable to post a single-entry register |
| C2 | H | Migration | Journal/project duplicate detection has no deterministic key |
| C3 | M | Migration | No batch-level reversal of a posted import |
| C4 | M | Migration | Spreadsheet edge cases beyond dates (hidden rows, text numbers, stale cached formulas) |
| C5 | M | Migration | Embedded-object extraction scoped optimistically |
| C6 | M | Migration | The 4,409,259 exception needs candidate explanations tested, not just recorded |
| D2 | M | Reporting | No standing journal-integrity control report |
| D3 | M | Reporting | Prior-period adjustment and comparative restatement unaddressed |
| D4 | M | Reporting | Legacy Dr/Cr project caption is a live misreading risk |
| E1 | — | Scope | Committed surface is multi-year for a single-bookkeeper firm |

Details follow in §3–§9. Each carries problem, realistic failure, correction, stage and acceptance test.

---

## 3. Accounting model findings

### A1 — Blocker — No settlement/allocation entity

**Affects:** architecture model list (Account, Project, CashBankAccount, AccountingPeriod, Voucher, JournalLine, Evidence); transaction form "original invoice/voucher link for settlement"; reports 3 and 4; receivable/payable aging in ADDITIONAL_FINANCE_SCOPE.

**Problem.** Settlement appears only as a *conditional header field* linking one voucher to one source document. A header link cannot express: partial settlement; one receipt against several invoices; several receipts against one invoice; an advance later applied to an invoice; a credit note applied; or a receipt that clears an invoice while part of it went to tax withheld and retention. Without a first-class allocation table there is no concept of an *open item*, and every promised open-item report — party ledger "genuine outstanding balance", customer statement, receivable and payable aging, advance aging, overdue settlements — is not derivable. A control-account balance tells you the total; it cannot tell you which invoice is 90 days overdue.

**Realistic failure.** Invoice to the institute for 12,208,127. The buyer pays 11,658,762, having deducted tax at source. The receipt is entered with a header link to the invoice. The AR control account shows 549,365 still outstanding against that customer, permanently. The aging report shows a customer overdue balance that is in fact a recoverable tax credit. The accountant clears it with a manual journal to expense, and the company loses a tax credit it was entitled to claim — silently, and repeatedly, on every government receipt.

**Correction.** Add `SettlementAllocation(from_line, to_line, amount, allocated_on, allocated_by, reversal_of)`. Enforce that allocations against a line never exceed its amount, in the same transaction as posting. Compute open items, statements and aging from *unallocated line balances*, never from control-account totals. Make allocation reversible as its own authorised operation.

**Stage.** 2 — before any receivable or payable is posted.

**Acceptance test.** Invoice 100 settled by receipt 60, then receipt 30, then a 10 withholding line → open balance exactly 0 and nothing on the aging report. Reversing the 30 receipt restores 30 open, aged from the *original invoice date*, not the reversal date. Over-allocating to 110 is rejected.

### A2 — Blocker — No year-end close or retained-earnings policy

**Affects:** everything in the reporting sections that implies a balance sheet; Statement of Changes in Equity; comparative periods; trial balance opening balances.

**Problem.** No document describes how income and expense balances reach equity. There is no closing-entry process, and no statement that retained earnings are computed dynamically. This is not a detail; it determines whether the balance sheet balances at all after the first year-end, and it determines what "opening balance" means for a P&L account on the trial balance.

**Realistic failure.** Statement of financial position as at 30 June 2027. Assets minus liabilities exceeds equity by exactly the 2025-26 result, because nothing ever moved it. The accountant plugs the difference, and from then on the equity section is a manual figure that nobody can trace.

**Correction.** Choose explicitly and document it:

- **(a) Dynamic (recommended for this system).** No closing entries. Retained earnings as at date *D* = opening retained earnings + Σ(income − expense) for all posted lines up to *D*. The balance sheet shows prior retained earnings and current-year result as separate derived lines. Simplest to keep correct, and immune to a reopened period.
- **(b) Posted closing journal** per fiscal year to Retained Earnings, system-generated, flagged as such, automatically reversed and regenerated if the year is reopened.

Whichever is chosen, the trial balance report must state which, and income/expense accounts must show zero opening balance at the start of each fiscal year.

**Stage.** 3, but the decision must be made in stage 1 because it affects the account master (a Retained Earnings account with a system role) and the period model.

**Acceptance test.** Two-year fixture. Balance sheet balances at each year-end to the cent. Reopening year 1, posting an adjustment and re-running produces a consistent year 1 result *and* year 2 opening equity, with no manual step.

### A3 — High — Deductions at settlement not modelled

**Affects:** transaction form allocation rows; "Tax/withholding splits require reviewed mappings"; party ledger.

**Problem.** The form supports allocation rows plus a system-generated balancing cash/bank line. It has no supported shape for: *cash 95.5 + withholding tax receivable 4.5, together clearing receivable 100*. The package correctly refuses to hard-code a tax rate, but refusing a rate is not the same as providing the structure. The same gap exists on the payables side, where the company itself must deduct tax when paying suppliers and then remit it — creating a withholding-tax-payable liability with a remittance and challan evidence trail that appears nowhere in the scope.

This is not hypothetical for this client. Section 153 of the Income Tax Ordinance 2001 obliges prescribed persons — which include federal, provincial and local government — to deduct tax when paying for goods, services and contracts. The counterparty in the supplied project ledger is a provincial government research institute. **Receipts on that contract will not equal invoice amounts.** Rates are set annually by the Finance Act and must be confirmed with the company's tax adviser; do not configure any rate from this review.

**Realistic failure.** As A1, plus: at year end the company cannot produce the schedule of tax deducted at source, cannot claim the credit against its own liability, and has no reconciliation between the tax-credit asset and the CPRs/challans it holds.

**Correction.** Add a deduction-type master (name, account, direction, whether it clears the source document, required evidence reference such as CPR number and date, effective-dated and reviewed). Allow deduction lines on a settlement voucher. Maintain two distinct control accounts with party subledgers: *tax deducted from us* (asset, recoverable subject to advice) and *tax deducted by us* (liability, pending remittance). Handle contract retention the same way — retention receivable is not an overdue debt and must not age as one.

**Stage.** 2 (structure) / 5 (full document integration).

**Acceptance test.** Receipt of 95.5 against invoice 100 with a 4.5 withholding line clears the receivable fully, creates 4.5 in the tax-credit subledger tagged with the CPR reference, leaves nothing on the aging report, and the tax-credit subledger reconciles to its control account.

### A4 — High — FBR digital invoicing is a live constraint, not a future connector

**Affects:** "add accountant-approved taxes and required FBR connector before enabling live invoices"; voucher numbering; immutability.

**Problem.** The package treats FBR integration as step 4 of a future sequence. Under SRO 69(I)/2025 and the phased schedule set by SRO 1852(I)/2025, electronic invoicing — structured JSON, an FBR-assigned invoice reference number, QR code and digital signature, submitted through PRAL or a licensed integrator — applies to sales-tax-registered persons, with the rollout completing at the end of December 2025. **If this company is sales-tax registered, it cannot lawfully issue a sales tax invoice from this ERP at all until integrated.** Applicability turns on registration status, which is not stated in the package and must be confirmed.

There is a design consequence beyond compliance: the invoice identifier becomes **externally assigned**. An invoice that FBR rejects must not leave a posted GL entry behind, and a submission that times out and is retried must not produce two accepted invoices.

**Realistic failure.** Live issuance is switched on because the ledgers look ready. The first invoice posts to the GL and is handed to the customer. It has no IRN, no QR code, and is not a valid tax invoice. The customer's own compliance rejects it; the revenue is posted; and reversing it means reversing a document already in the customer's system.

**Correction.** Confirm sales-tax registration status as a priority question (§11). If registered: model the lifecycle as Draft → Approved → Submitted → Accepted (IRN returned) → Posted, with **GL posting gated on acceptance**, an idempotent submission queue keyed on the draft reference, and an explicit operator path for rejection and timeout. Keep live issuance disabled until this passes its own test. Endorse the package's existing decision to keep it disabled.

**Stage.** Gate before any live invoice; do not bundle it into general reporting work.

**Acceptance test.** A simulated FBR rejection leaves no posted GL entry and consumes no voucher number. A simulated timeout followed by success produces exactly one accepted invoice and one IRN. An accepted invoice cannot be edited.

### A5 — Blocker — Control-account ↔ subledger integrity not enforced

**Affects:** "Separate control accounts and party subledgers"; Account field "optional required party/project"; reconciliation list.

**Problem.** The rule is stated; nothing enforces it. There is no flag marking an account as a control account, no rule that postings to one *must* carry a party, no restriction on manual journals into control accounts, and no report proving that the sum of party subledgers equals the control balance. The scope lists customer/supplier control reconciliation as a feature — a reconciliation you run after the fact, rather than a constraint that prevents the drift.

**Realistic failure.** A correcting journal posts 500,000 to Trade receivables with no party, to balance a mis-keyed bank line. The control account reads 8.5m; the sum of all customer ledgers reads 8.0m. Both the trial balance and the balance sheet look fine. Every customer statement is understated, in aggregate, by half a million rupees, and there is no report that would surface it.

**Correction.** Add `Account.is_control_account` and `Account.requires_party` / `requires_project`, enforced both as a service-layer validation *and* a database check constraint. Block control accounts from the simple and advanced journal forms unless a specific permission is held. Ship a control-versus-subledger variance report that must return zero rows, and run it in the nightly integrity job (D2).

**Stage.** 2.

**Acceptance test.** Posting to a control account without a party is rejected at the API, and rejected again by raw SQL. The variance report returns zero rows across the full fixture including reversals and settlements.

### A6 — High — Fixed-asset register ↔ GL reconciliation and depreciation posting unspecified

**Affects:** fixed assets and valuation section.

**Problem.** The reconciliation list covers customers, suppliers, payroll payable and advances — but not fixed assets, which is the subledger most likely to drift because it has its own independent calculation. More basically: the scope never says whether depreciation is *posted* as journal vouchers or merely *computed for the report*. If the latter, depreciation expense never reaches the general ledger.

**Realistic failure.** The asset register reports carrying amount 4.2m. The GL reports cost 6.0m less accumulated depreciation 1.5m, i.e. 4.5m. The balance sheet and the fixed-asset note disagree by 300,000 and nobody can say which is right, because the two were never derived from the same records.

**Correction.** Depreciation runs generate a reviewable, approvable, **posted** journal voucher per period, with a per-asset detail table linked to the voucher lines. Add an asset-register-to-GL reconciliation by asset class. Block a period close while an unrun depreciation period exists for that period. Define the start convention explicitly (from available-for-use date; pro-rata by days or full month — an accountant decision) and the remainder rule, so accumulated depreciation never exceeds cost less residual.

**Stage.** 6.

**Acceptance test.** Cost 1,000,000, residual 100,000, three years, monthly: after 36 periods accumulated depreciation is exactly 900,000 with no rounding drift, and the GL agrees with the register to the cent. Disposal in month 20 posts proceeds, carrying amount and gain or loss, and removes the asset from register and GL identically.

### A7 — Medium — Employee-benefit provisions absent

Payroll scope covers pay, allowances, deductions and employer contributions, but no gratuity, severance or leave-encashment provision. For a registered Pakistani company with employees these are commonly recognised liabilities that accrue every year. Omitting them understates liabilities on every balance sheet the system produces.

**Correction.** Do not attempt actuarial computation in software. Provide the accrual route (adjusting journal voucher plus a supporting schedule) and record the provision as an explicit accountant input with its basis documented. Flag it on the balance-sheet readiness checklist so the omission is visible rather than silent.

**Stage.** Manual from stage 2; scheduled in 6.

### A8 — Medium — Decimal precision, rounding and remainders unspecified

"All money calculations use decimals on the server" is a reassurance, not a specification. Unspecified: stored scale, rounding mode, whether the debit-equals-credit test is exact or tolerant, and where an allocation remainder goes.

**Realistic failure.** 1,000,000 split across three projects gives 333,333.33 three times — 999,999.99. Either the voucher is rejected as unbalanced and the user invents a fourth line, or the system accepts a 0.01 tolerance, which then accumulates silently across tens of thousands of imported rows until the trial balance is out by a few hundred rupees with no traceable cause.

**Correction.** PKR amounts as `NUMERIC(18,2)`; rates and quantities at `NUMERIC(18,6)`; ROUND_HALF_UP; the balance test **exact at stored scale, never epsilon-tolerant**; allocation remainders assigned by a stated convention (largest line) and shown in the pre-submission preview so the user sees where the cent went.

**Acceptance test.** A three-way split posts with the total exactly equal to the header. A voucher out by 0.01 is rejected with a message naming the difference.

### A9 — Medium — Reversal date policy undefined

"Correct through a linked balanced reversal" does not say what date the reversal carries, what happens when the original period is closed, or whether a voucher with settlements against it can be reversed at all.

**Realistic failure.** An April voucher is found wrong in August. April is closed and its trial balance has already gone to the bank. Reversing at the April date silently changes a statement already issued. Reversing at the August date leaves April overstated. Without a rule, whichever the developer chose becomes the policy.

**Correction.** Default the reversal to the original date when its period is open; otherwise the earliest open date, shown explicitly and never silently substituted. Require a reason. Block reversal of any line carrying settlement allocations until those allocations are reversed first. Forbid reversing a reversal — use a fresh correcting entry, so the chain stays readable.

**Acceptance test.** An as-of trial balance for a date before the reversal reproduces the original figures exactly. A settled invoice cannot be reversed while allocations exist.

### A10 — Medium — The date model contradicts itself between documents

ACCOUNTING_CLIENT_REQUIREMENTS gives the voucher one "transaction date" plus server timestamps. ADDITIONAL_FINANCE_SCOPE requires document, posting and bank value dates to be distinguished. These are different schemas.

Beyond reconciling them, as-of reporting needs a second axis: the difference between "what does the April trial balance look like now" and "what did it look like when we printed it in May". Back-dated postings into a reopened period make these different numbers, and an auditor will ask.

**Correction.** Three explicit fields — `document_date` (business), `accounting_date` (drives the period and the general ledger; normally equal to document date), `value_date` (bank clearing; reconciliation only) — plus the immutable `posted_at`. Support "as at *D*, as known on *K*" for the trial balance and general ledger. Update both requirement documents to agree.

### A11 — Medium — Currency columns omitted from the schema

"One transaction is PKR in the first release" is a correct *policy* and a poor *schema decision*. Add `currency`, `rate` and functional-amount columns now, constrained to PKR at rate 1. Adding them later is a migration of every posted row plus a rewrite of every report query. The cost now is close to zero.

### A12 — Medium — Cutover vs opening balances has no mechanism

"Import requires a cutover date to avoid importing history plus the same balances twice" is stated as a rule that a human must remember.

**Correction.** One `cutover_date` per book. The opening-balance journal must be dated `cutover_date − 1` and is the only voucher permitted before the cutover. The importer rejects any transaction dated before cutover unless the book is explicitly in full-history mode, which in turn disables the opening-balance journal. The two modes are mutually exclusive in code, not in documentation.

**Acceptance test.** Attempting both modes on one book is rejected. The trial balance at cutover equals the approved opening balance sheet exactly.

### A13 — Medium — Cash-flow statement method not chosen

IAS 7 is cited but neither direct nor indirect is selected, and the data to support the indirect method (full accruals, movements in working capital) will not exist for some time. A single account-level cash-flow tag cannot classify a payable whose movements are part operating and part investing.

**Correction.** For the pilot, produce a **direct** cash movement summary from cash and bank lines, classified by the counter-account's tag, labelled "Cash movement summary — not a statutory IAS 7 statement". Defer the statutory statement until accruals exist. Do not label any output IAS 7 compliant.

---

## 4. Accounting walkthroughs

Illustrative only. Account names are indicative; the approved chart, classifications and policies are accountant decisions. Every walkthrough names its double-counting risk, because that is where this design is load-bearing.

### 4.1 Supplier bill, then payment

| Step | Dr | Cr |
|---|---|---|
| Bill received | Expense *or* Inventory *or* Asset (per nature) | Trade payable — supplier subledger |
| Payment | Trade payable — supplier subledger | Bank |

**Double-counting risk.** The dominant one in this system. The legacy register records only the *payment*. If the payment is coded to expense while the bill was already booked, the cost is recognised twice. The transaction form must make "settle an existing bill" a distinct, obvious action that clears the payable and cannot post to an expense account. **Depends on A1**: a partial payment must leave a correctly aged open balance.

**Policy-dependent.** Whether the purchase is expense, inventory or asset. Feed purchased for a supply contract is likely inventory under IAS 2 and is expensed when the related revenue is recognised — not when paid. The package states this correctly; the form must make it easy to do.

### 4.2 Customer invoice, then receipt

| Step | Dr | Cr |
|---|---|---|
| Invoice issued | Trade receivable — customer subledger | Revenue (+ output tax payable if applicable) |
| Receipt (net of deduction) | Bank *net amount* · Tax deducted at source — receivable · Retention receivable | Trade receivable — customer subledger *gross* |

**Double-counting risk.** Coding the receipt to revenue when the invoice already recognised it. The package calls this out; A1 and A3 supply the mechanism.

**Policy-dependent.** Revenue recognition timing is an IFRS 15 question about performance obligations, not about when cash arrived. Retention is not an overdue receivable and must not age as one.

### 4.3 Customer advance

| Step | Dr | Cr |
|---|---|---|
| Advance received | Bank | Customer advance / contract liability — customer subledger |
| Later invoice | Trade receivable | Revenue |
| Application | Customer advance | Trade receivable |

**Double-counting risk.** Treating the advance as revenue on receipt and again on invoice. **Depends on A1** — the application step *is* an allocation; without an allocation table the advance sits on the balance sheet forever and the receivable never clears.

**Policy-dependent.** Advance versus contract liability presentation; whether it is current.

### 4.4 Staff advance and settlement

| Step | Dr | Cr |
|---|---|---|
| Advance issued | Staff advance — employee subledger | Bank / Cash |
| Settlement: supported expenditure | Expense / Project cost | Staff advance |
| Settlement: unused cash returned | Cash | Staff advance |
| Settlement: further amount due to employee | Expense | Employee payable |

**Double-counting risk.** Two of them. First, expensing the advance on issue *and* again on settlement. Second — the one the package flags and is right to — the same receipt claimed against both an advance settlement and a separate reimbursement claim. Enforce a uniqueness rule on evidence: an evidence record may support exactly one settlement or claim line.

**Policy-dependent.** Whether an unsettled advance past its due date becomes a payroll recovery.

### 4.5 Imprest replenishment

| Step | Dr | Cr |
|---|---|---|
| Float established | Petty cash (imprest) | Bank |
| Expenditure recognised on submission of vouchers | Expense — by account and project | Petty cash (imprest) |
| Replenishment | Petty cash (imprest) | Bank |

**Double-counting risk.** Expensing at replenishment when expenditure was already recognised from the vouchers. The replenishment entry **touches no expense account at all** — it restores the float. Constrain the replenishment form so it cannot reach an expense account.

**Policy-dependent.** Whether expenditure is recognised as vouchers are submitted or only at replenishment. Choose one and enforce it; both are defensible, mixing them is not. Shortages and excesses need an approved adjustment account, never a plug.

### 4.6 Employee reimbursement

| Step | Dr | Cr |
|---|---|---|
| Approved claim | Expense / Project cost | Employee payable — employee subledger |
| Payment | Employee payable | Bank / Cash |

**Double-counting risk.** As 4.4 — the same receipt against both an advance and a claim. Also: a claim approved in part must record the approved amount with the reason, not a silently edited original, so the employee-visible record and the ledger agree.

**Policy-dependent.** Policy limits; whether a personally funded business payment creates an employee payable or an owner's current account (this is one of the unresolved "Paid By" questions, and it matters — the two land in different sections of the balance sheet).

### 4.7 Payroll accrual and payment

| Step | Dr | Cr |
|---|---|---|
| Accrual | Salaries and wages (gross) · Employer contributions (expense) | Net salary payable · Tax deducted from employees — payable · Employee contributions — payable · Employer contributions — payable · Staff advance (recoveries) |
| Payment of net pay | Net salary payable | Bank |
| Remittance of deductions | Respective payable accounts | Bank |

**Double-counting risk.** Expensing gross at accrual and again at payment; and — specifically — treating an advance recovery as a *reduction of salary expense*. It is not. The recovery clears the advance asset; the expense is the full gross.

**Policy-dependent.** Statutory rates and effective dates are configuration requiring review, never defaults. Gratuity and leave provisions (A7) are additional to this entry. A payroll period must be re-runnable only through a controlled reversal, not by editing a posted run.

### 4.8 Asset acquisition, depreciation, disposal

| Step | Dr | Cr |
|---|---|---|
| Acquisition | Fixed asset — cost | Trade payable / Bank |
| Depreciation (each period) | Depreciation expense | Accumulated depreciation |
| Disposal | Bank (proceeds) · Accumulated depreciation · Loss on disposal (if any) | Fixed asset — cost · Gain on disposal (if any) |

**Double-counting risk.** Expensing the acquisition *and* depreciating it. Also: recognising the full proceeds as income instead of the gain or loss — a 3m sale of an asset with 2.6m carrying amount is 400,000 of gain, not 3m of income.

**Policy-dependent.** Land is not depreciated. Capitalisation threshold, useful lives, method, and whether the cost or revaluation model applies are all accountant decisions. The system must not estimate a fair value. Depreciation begins from the available-for-use date, not the purchase date.

### 4.9 Transfer between own accounts

| Step | Dr | Cr |
|---|---|---|
| Transfer | Destination bank / cash | Source bank / cash |
| Charges | Bank charges (expense) | Source bank |

**Double-counting risk.** The reporting one the package already names: counting both legs as business receipts and payments. The transfer voucher type must tag both lines as internal, and every receipts/payments report and chart must exclude them by default and say so in the filter summary. A cash-in-transit account is worth having when the two legs settle on different days.

### 4.10 Donations

| Step | Dr | Cr |
|---|---|---|
| Donation paid | Donation expense | Bank / Cash |
| Donation received (unrestricted) | Bank / Cash | Donation income |
| Donation received (restricted) | Bank / Cash | Deferred income / restricted liability |
| Non-cash donation | Asset or expense at supported value | Donation income |

**Double-counting risk.** Recognising a restricted donation as income on receipt and again when the condition is met.

**Policy-dependent.** Deductibility of donations paid depends on the recipient's status and the applicable tax rules and is never automatic — the package is right to say so. Non-cash valuation needs supporting evidence, not an estimate. Donations may warrant confidential access.

### 4.11 Tax and withholding split

Covered in A3. The one addition worth stating as a rule: **a deduction at source is a settlement line, not a separate voucher.** Recording the net receipt in one voucher and the withholding in another, later, is how the two lose their link and the receivable stops clearing.

---

## 5. Architecture findings

### B1 — Blocker — Voucher number assigned at draft creation

**Problem.** The header field list places "voucher number" on the draft form, while the rules require server-generated uniqueness with no duplicates under competing approvers. Assigning at draft creation guarantees gaps from abandoned drafts; a database sequence gaps on rollback; an application-level `max()+1` races.

**Realistic failure.** Two approvers post simultaneously and both compute PV-2026-0412. One fails on the unique constraint after its journal lines are written, and the retry path either duplicates or leaves a partial voucher. Separately, a user abandons thirty drafts and the payment voucher book jumps from 0411 to 0441 — a gap an auditor will ask about and nobody can explain.

**Correction.** Two identifiers. A non-accounting `draft_reference` (UUID) at creation, shown in the UI. The accounting `voucher_number` assigned **at posting time** from a per-(book, fiscal year) counter row locked with `SELECT … FOR UPDATE` inside the posting transaction, with a unique constraint on (book, fiscal_year, number). Ship a gap report as a standing control.

**Acceptance test.** Fifty concurrent posts produce fifty contiguous numbers, no duplicates, no gaps. A post that fails validation consumes no number.

### B2 — Blocker — The concurrency guarantees cannot be tested where they are being tested

**Problem.** The design's integrity rests on atomic transactions, row locking, a unique source-posting constraint and idempotency keys. **SQLite has no row-level locking** — `select_for_update()` is a no-op there, and writers serialise at the database level. Every race test will pass locally and prove nothing. The package reports 22 passing backend tests and lists "PostgreSQL concurrency verification" as an outstanding *deployment* prerequisite, which understates it: it is a prerequisite for believing the posting engine works at all.

**Realistic failure.** The test suite is green throughout development. On the first multi-user day in production, a double-clicked approve produces two posted vouchers for one payment, and the bug is found by the bank reconciliation a month later.

**Correction.** The posting, idempotency and number-allocation tests run against PostgreSQL in CI and are a merge gate. Keep SQLite for unrelated tests only. Include one test that asserts the lock actually blocks a competing transaction — it will fail on SQLite, which is exactly the signal you want.

**Acceptance test.** CI shows the accounting suite green on PostgreSQL; removing the lock makes a named test fail.

### B3 — Blocker — Immutability enforced only in the service layer

**Problem.** "Posted transactions cannot be edited or deleted" is the central integrity claim, and the stated defence is that posting logic lives in service functions rather than unrestricted model CRUD. That defends against the application's own API. It does not defend against Django admin, a future viewset, a management command, a data migration, or a support session in `manage.py shell` — and none of those leave a workflow trail.

**Realistic failure.** A well-meaning fix in a shell session corrects one posted amount on both sides. The trial balance still balances. No audit event exists. A year later a customer disputes a statement, and there is no way to establish what the ledger said on any past date or when it changed.

**Correction.** Defence in depth, all four:

1. Database triggers rejecting UPDATE and DELETE on journal lines and on vouchers in Posted state.
2. The application database role is not the table owner and holds no DELETE on those tables.
3. A per-voucher content hash, chained, with a periodic integrity check whose result is exported outside the database.
4. Accounting models never registered in Django admin with write access.

**Acceptance test.** A raw SQL UPDATE on a posted journal line, as the application role, is rejected. The integrity check detects a row tampered with in a restored copy.

### B6 — High — No aggregation strategy; ledgers inherit the 5,000-row cap

**Problem.** Reading reports directly from posted journal lines is the right call for integrity. But the existing report layer carries a 5,000-document pilot cap, and there is no period-balance structure. A general ledger across three years, a trial balance with opening balances computed from inception, or an export of a migrated history of tens of thousands of rows will truncate or time out.

**Correction.** (1) An `AccountPeriodBalance` aggregate (account, party, project, period, debit, credit) maintained in the same transaction as posting, with a recompute-and-verify job — reports read the aggregate for openings and journal lines only for the selected window. (2) Explicit indexes on (accounting_date, account), (account, party, accounting_date), (project, accounting_date), (voucher). (3) Chunked/streaming exports whose cap **errors loudly** rather than truncating silently.

**Acceptance test.** Trial balance over a 100,000-line, three-year book returns within a stated budget. The recompute job reports zero variance against the journal. An export beyond the cap fails with a message rather than producing a short file.

### B7 — Medium — Business date from server time

"Default to today's date in Asia/Karachi" is correct; the standard implementation bug is `timezone.now().date()`, which returns the **UTC** date. Between 00:00 and 05:00 PKT that is yesterday — including across a period close or a year end.

**Correction.** `TIME_ZONE='Asia/Karachi'`, `USE_TZ=True`, `timezone.localdate()` everywhere a business date defaults; date-only fields as DATE, never DATETIME. Test with time frozen at `2026-06-30T20:00Z` asserting a default business date of 1 July 2026.

### B8 — Medium — Squash the scaffolding migration; do not apply it

The package states the accounting migration has been generated but not applied, **and** that the scaffolding is explicitly not the approved schema — party as free text, no source-document identity, no cash/bank master, evidence as database binary. Applying it creates a migration history every future environment must replay and then undo, and turns the party-text-to-foreign-key change into a data migration.

**Correction.** Delete the unapplied migration. Correct the models first — structured party FK, source-document identity, cash/bank master, evidence pointing at private storage, currency columns (A11), control-account flags (A5), the three dates (A10), settlement allocations (A1). Then generate one initial accounting migration. This is the cheapest item on this list today and among the more expensive in two weeks.

**Acceptance test.** `makemigrations --check` clean; a fresh database migrates in one pass; no accounting table has a party-name text column.

### B10 — Medium — No legal-entity dimension

If "Muhammad Zakaria and Sons" is one of several associated concerns — a common shape for this kind of business — there is no entity dimension on accounts or vouchers, and adding one after posting is a migration of every row plus every report. Either record an explicit decision that this system holds exactly one legal entity's books, or add a nullable entity foreign key now. This is a client question, not a build item.

---

## 6. Access and security findings

### B4 — High — Role administration not separated from financial master data or audit access

Two concrete problems, both in the current implementation as described:

**(a)** Accounting master data is maintained by `finance.manage` **or** `roles.manage`. The person who administers roles can therefore create accounts and change the chart. That coupling appears to be a convenience during bootstrap; it is a separation-of-duties failure and should not survive into the pilot.

**(b)** "Audit logs are available only through explicitly assigned permissions, with no automatic administrator bypass" is a genuinely good decision — and it is only meaningful if the administrator cannot assign that permission to themselves. The package does not say that they cannot.

**Realistic failure.** An administrator grants themselves posting and audit rights, posts a payment to a supplier they control, and removes the permissions again. The permission changes are recorded — in a log they now control. Every individual control in the design held; the combination did not.

**Correction.** Remove `roles.manage` from the accounting master-data check. Prohibit self-assignment of any permission outright (a user may never grant a permission to their own account). Require a second approver for grants of posting, reversal, period-close and audit-view. Stream permission changes and posting events to an append-only sink outside the administrator's control.

**Acceptance test.** `roles.manage` alone cannot create an account. A user cannot grant themselves audit or posting rights by any route including the API. A permission grant appears in the external log.

### B5 — High — No amount thresholds, no delegation

Thresholds and delegation are listed as outstanding for documents; the accounting workflow inherits the same one-stage Finance→GM model. With a single GM and no delegation, absence means either payments stop or the GM's credentials get shared. Shared credentials are the most common real-world control failure in small ERPs, and they void the entire audit trail.

**Correction.** Amount bands mapping to required approver roles, evaluated server-side at submission and **re-evaluated at posting** — a voucher whose amount changed after approval must re-route. Time-boxed delegation with an explicit delegated-by record shown on the voucher and in the audit trail. Self-approval stays blocked, including via delegation.

**Acceptance test.** A voucher of 5,000,001 against a 5,000,000 band requires the higher approver. Editing the amount after approval invalidates it. A delegate cannot approve their own submission.

### B9 — Medium — Evidence storage and backup coupling

The package flags evidence-in-database as unresolved. The consequence is not stated: database backups grow to file-store size, and the later move to private storage creates a restore-consistency window where the database is restored to time *T* and the files to *T′*.

**Correction, before any evidence ships.** Private filesystem or object storage with generated names; a database row holding SHA-256, size, declared *and* sniffed content type, uploader and timestamp; an authenticated download view re-checking the originating record's scope; `Content-Disposition: attachment` and `X-Content-Type-Options: nosniff` for PDFs; a backup procedure snapshotting database and files together, with a documented and *tested* restore and a stated recovery point objective. Bank evidence makes an untested restore a business risk, not an IT one.

### B11 — Low — Session and permission revocation

Bearer sessions that are database-backed, hashed and expiring is a sound choice, and keeping tokens in app memory only is a reasonable trade. Two things to confirm and test rather than assume: permissions are read from the database per request rather than embedded in the token, and demoting or deactivating a user invalidates active sessions immediately. Add administrator-visible session listing and revocation.

### B12 — Low — Masking is not scope

"Exports never bypass permission scopes" governs *which records* a user sees. Account-number masking governs *which fields*, and needs its own rule applied identically to the API, report drill-down, CSV/XLSX/PDF exports and print layouts — masking a column in the list view while the XLSX export carries the full IBAN is the usual outcome. Add rate limiting and volume logging on exports: a single authorised user exporting the full party and evidence set is the realistic data-loss path in a system this size.

**Also missing from the package entirely** and worth a deployment checklist rather than findings: `DEBUG=False`, `ALLOWED_HOSTS`, HSTS and secure cookie flags, secret management outside source control, encrypted and offsite backups, dependency vulnerability scanning with a Django LTS upgrade path, and an audit-log retention decision. The package's Android cleartext note (debug-only) shows the right instinct; extend it into a written pre-production checklist.

---

## 7. Excel migration review

### C1 — High — "No suspense" is impractical and will be worked around

The design forbids silent suspense and invented balancing bank entries. That instinct is right. But the source is, by the package's own correct analysis, a money-movement register rather than a balanced journal — so a large share of rows will have no counterpart account. With suspense forbidden outright and posting blocked, the realistic outcome is that someone abandons the importer and keys the history in by hand, losing every control the design built.

**Correction.** One visible, named **Migration suspense (unclassified)** account that is: postable only by the import service; reported on its own standing exception schedule with drill-down to the source workbook cell; and subject to a hard go-live gate — the account must be zero and the batch signed off before the book leaves migration mode. That is a *controlled* suspense, which is a different thing from a silent one, and it is the difference between a migration that finishes and one that stalls.

**Acceptance test.** An unmapped row posts to suspense carrying its workbook, sheet and row reference. The go-live check fails while suspense is non-zero.

### C2 — High — Duplicate detection has no deterministic key

The spec says compare reference, date, amount, direction and project, and route ambiguities to review. But the legacy rows have clipped descriptions, at least one missing date, and no reliable reference number. A large fraction will be ambiguous, and the review queue becomes the project.

**Correction — structural, not statistical.** Make the general journal the **only** importable source of transactions. Import project sheets solely as project tags and legacy-description enrichment, matched onto journal rows, never posted independently. A project row with no journal match becomes an exception to investigate, not a candidate posting. This converts an N×M fuzzy-matching problem into one-way enrichment, and it directly implements the client's own description of their process: they enter in the journal *and then also* enter in the project sheet.

**Acceptance test.** Importing the journal plus every project sheet produces exactly the journal's row count in postings. An unmatched project row posts nothing and appears as an exception.

### C3 — Medium — No batch-level reversal

"Posted imports require controlled reversals rather than deletion" — for a 40,000-row batch that must be one authorised operation producing one linked reversal batch, not 40,000 manual reversals. Specify it.

### C4 — Medium — Parsing edge cases beyond dates

Serial dates and explicit day/month/year mapping are covered. Add explicitly: numbers stored as text with thousand separators; trailing or parenthesised negatives; Arabic-Indic and Urdu digits; non-breaking spaces; merged cells; multi-row headers; **hidden rows and columns**; and formula cells whose cached value is stale. Read cell values, never displayed text, and reject a workbook whose cached values cannot be trusted.

**Realistic failure.** A row of 1,250,000 that the client "deleted" by hiding it is imported as a live payment, because `openpyxl` reads hidden rows like any other.

### C5 — Medium — Embedded-object extraction scoped optimistically

Embedded objects are extractable from the workbook package's embeddings and media parts, but mapping each back to its originating cell depends on drawing anchor XML and is frequently ambiguous for floating objects. Plan for **manual re-upload as the primary path** with extraction as a best-effort assist, and size the effort accordingly. Planning an automatic extraction that turns out 60% accurate is worse than planning a manual one.

### 7.3 — The reconciliation exception (C6)

I recomputed the supplied figures independently:

- 5,009,642 + 12,208,127 + 22,705,104 + 19,279,929 = **59,202,802** — equals the stated main-table credit total. ✓
- 70,438,638 − 59,202,802 = **11,235,836** — equals the stated balance. ✓
- 59,202,802 + 4,409,259 = **63,612,061**; 70,438,638 − 63,612,061 = **6,826,577**. ✓

**The package's arithmetic is correct.** What it does not do is generate candidate explanations, and a reconciliation exception without hypotheses tends to sit unresolved until go-live. Four worth testing mechanically against the workbook before assuming omission:

1. **Scope difference** — receipt 5 belongs to a different contract year, sheet or entity. Plausible given the contract is a 2025–26 framework agreement and the receipt is dated 22 June 2026.
2. **Transcription gap in the copy, not the books** — recorded in the general journal but never copied to the project sheet. This is *precisely* the failure mode the client described as their reason for wanting the software, which makes it a strong candidate.
3. **Status difference** — received but uncleared, or recorded against a different project.
4. **Deduction or retention** — worth checking, with a caution: 4,409,259 is 7.45% of 59,202,802, close enough to a common contract withholding rate to be worth *testing* but nowhere near conclusive, and the arithmetic does not compose naturally against the other four receipts. **Do not treat this observation as a finding**; it is a query to put to the accountant with the workbook in hand.

Whatever the answer, the package's core position stands and I endorse it: this is an exception to resolve, not a licence to post a balancing entry. Keep both figures as labelled test controls, and make "all migration exceptions resolved and signed off" a go-live gate rather than a report nobody owns.

---

## 8. Reporting review

The report set (daybook, general ledger, party ledger, project statement, cash/bank book, trial balance) is the right first six and in a sensible order. Three additions and two cautions.

**D2 — Add a standing journal-integrity control report.** Nightly, one page: global and per-period debits equal credits; every posted voucher balanced and with at least two lines; no postings to group or inactive accounts; no orphan lines; control-versus-subledger variance (A5); aggregate-versus-journal variance (B6); voucher-number gaps (B1). Alert on any non-zero. This is the cheapest assurance in the entire system and it is not in the plan.

**D3 — Prior-period adjustments and comparatives.** A Statement of Changes in Equity and comparative columns are promised. Restating a prior period, and the "as at *D* as known on *K*" problem in A10, are not addressed. Decide the policy before the first year-end, not during it.

**D4 — The legacy Dr/Cr project caption is a live misreading risk.** The package flags it; strengthen the guard. Never print "Trial Balance" or "Profit" on a project cash statement. Require a legend block stating the convention and that the balance is *net cash movement into the project*. Make the caption configuration administrator-only with standard accounting labels as the default. The client's existing habit of reading that balance as a project result is exactly what a new system will appear to endorse.

**On aging, customer statements and outstanding balances** — see A1. These cannot be built on the model as specified, and they are among the reports the client will judge the system by.

**D5 — The custom report and chart builder is a scope trap.** Ship eight or ten fixed, parameterised reports with saved definitions first. Builders consume disproportionate effort and are usually used to rebuild the fixed reports slightly differently.

Strong points worth preserving as written: excluding both legs of internal transfers from receipts/payments by default; neutralising spreadsheet formula injection; preserving bank and reference values as text; colour never being the sole meaning indicator; and the draft/final label on every export.

---

## 9. Scope assessment

**E1.** The committed surface — payroll, fixed assets with revaluation and impairment, donations, reimbursements, imprest, bank reconciliation with split and group matching, custom report and chart builders, image exports, A3 layouts, Excel migration, FBR integration, across web, Windows and Android — is multi-year work for what the material suggests is a single-bookkeeper firm.

**Defer explicitly** (each is a decision to record, not a gap to close):

- **Android and Windows native.** Keep paused; web-first until the accounting core is stable. The package already pauses Android; extend the same reasoning to Windows and stop treating the Visual Studio toolchain blocker as a task.
- **Donations as a module.** Handle as ordinary vouchers with a donation tag and a filtered register plus confidential access. A separate module is not justified by the requirements described.
- **Fixed-asset revaluation and impairment.** Cost model only. Revaluation is rarely worth building and never worth building before a policy exists to implement.
- **Image (JPEG/PNG) export, A3 layouts, custom-field administration, the chart builder.**
- **Automated bank-statement matching.** Start with manual tick-off against posted entries plus a saved reconciliation snapshot, which delivers most of the value at a fraction of the cost.

**Add to scope** — two items, both small relative to what they protect: the settlement/allocation model (A1) and the integrity control job (D2).

---

## 10. Revised delivery plan

### Production blockers — before any real transaction is posted

| # | Item | Findings |
|---|---|---|
| 1 | Correct the models and **squash the unapplied migration** | B8, A1, A5, A10, A11 |
| 2 | Settlement/allocation model and open-item computation | A1, A3 |
| 3 | Year-end close / retained-earnings policy decided and implemented | A2 |
| 4 | Control-account flags and constraints; subledger variance report | A5 |
| 5 | Voucher numbering at posting time, per book per year, locked | B1 |
| 6 | Posting suite running on PostgreSQL in CI as a merge gate | B2 |
| 7 | Database-level immutability for posted records | B3 |
| 8 | Access corrections: drop `roles.manage`, no self-assignment, external log | B4 |
| 9 | Precision, rounding and remainder rules | A8 |
| 10 | Evidence moved to private storage; backup and restore tested | B9 |
| 11 | Reversal date policy | A9 |
| 12 | Nightly integrity control report | D2 |

### Can follow the pilot

Approval thresholds and delegation (B5) — needed before more than a handful of users, not before the first voucher. Aggregation and indexing (B6) — needed before migration volume. Advances, imprest and reimbursement. Supplier bills and customer documents. Excel migration. Payroll, then fixed assets. Financial statements. Extended custom reporting.

### Gates that are not schedule items

- **No live invoice issuance** until FBR applicability is confirmed and, if applicable, integration passes its own rejection and timeout tests (A4).
- **No go-live on migrated data** until migration suspense is zero and every exception is signed off (C1, C6).
- **No financial statement labelled as such** until opening balances, account mappings, accruals and the applicable framework are confirmed.

Each increment ships its own useful reports, as the package already proposes. That is the right instinct and worth holding to.

---

## 11. Deferred questions, prioritised

**Blocking — needed before the corresponding build step, not before prototyping:**

1. **Is the company sales-tax registered?** Determines whether FBR digital invoicing (A4) is a live legal constraint. Highest-value single question in this list.
2. **Which counterparties deduct tax at source, and does this contract carry retention?** Determines whether A3 is required in stage 2 or can wait. Given a provincial government buyer, assume yes until told otherwise.
3. **Financial year start and end**, and the **cutover date**.
4. **Approved chart of accounts and reconciled opening balances.**
5. **Does this system hold one legal entity's books, or several?** (B10.)

**Needed before the relevant module, not before the core:**

6. Company size classification and therefore the applicable reporting framework. Under the Companies Act 2017 Third Schedule, companies are classified — public interest, large, medium, small — by criteria including paid-up capital, turnover and employee numbers, with the applicable framework following from that classification; SECP has permitted medium and small entities to opt for IFRS. **Registered-company status alone does not determine the framework**, exactly as the package says. Confirm the classification with the company's auditor; I could not retrieve the current primary text of the Schedule (see §13) and the criteria and options have been amended more than once.
7. Meaning of "Sent to" and "Paid By", and how personally funded business payments are treated — employee payable or owner's current account (4.6).
8. Whether the BANK and AC No. columns consistently identify the *company's* account or sometimes the recipient's.
9. Classification and terms of loans, investments, land and performance securities.
10. Payroll structure, statutory deductions, and whether gratuity or leave provisions are recognised (A7).
11. Depreciation policy, useful lives, capitalisation threshold, cost versus revaluation model.
12. Approver assignments, amount bands, evidence requirements, and who may see full bank details.
13. Retention and deletion policy for evidence and audit logs.

**The reconciliation questions** (§7.3) go to whoever maintains the workbook, with the workbook open, not to the client in the abstract.

None of these blocks prototype development. Several block *go-live*, and the distinction should be written into the plan rather than held in someone's head.

---

## 12. What I would need to verify source-level claims

I have reviewed a design bundle. To convert the implementation claims into verified findings I would need:

- The accounting app: `models.py`, the posting/reversal service module, and the generated-but-unapplied migration.
- The permission layer: permission definitions, DRF permission classes, role model, and the specific check that grants accounting master-data access (to confirm B4(a)).
- The role-assignment view or serializer (to confirm whether self-assignment is possible — B4(b)).
- `settings.py`: `TIME_ZONE`, `USE_TZ`, `DEBUG`, `ALLOWED_HOSTS`, `DATABASES`, file storage, session and token configuration.
- The existing `Party`, `AuditEvent` and workflow models, to assess the extension path.
- Evidence upload and download views.
- The report query layer and wherever the 5,000-row cap is applied.
- The full test suite, specifically the six accounting-setup tests, plus the CI configuration — to determine whether **any** test runs against PostgreSQL (B2).
- `requirements.txt` or lockfile, for dependency currency and Django support status.

No production passwords, tokens, databases or client data are needed for any of this.

---

## 13. Sources

- Federal Board of Revenue, [S.R.O. 69(I)/2025](https://download1.fbr.gov.pk/Docs/202541712407495sro69(I)2025.pdf) — electronic invoicing requirements, licensed integrator, invoice reference number and QR code. Applicability depends on sales-tax registration status and the phased schedule; confirm the current position with the company's tax adviser.
- Federal Board of Revenue, [FAQs on digital invoicing](https://fbr.gov.pk/faqs/173967/173969).
- Income Tax Ordinance 2001, section 153 (tax deduction on goods, services and contracts by prescribed persons, including federal, provincial and local government). Rates are set annually by the Finance Act — no rate in this review should be configured. Secondary summary consulted: [TaxationPk, s.153 rates](https://taxationpk.com/insights/wht-on-goods-services-contracts/).
- Securities and Exchange Commission of Pakistan, [amendments to the third, fourth and fifth schedules of the Companies Act 2017](https://secp.gov.pk/wp-content/uploads/2017/11/SECP-amends-third-fourth-and-fifth-schedules-of-Companies-Act-.pdf). **I was unable to retrieve the primary text** (HTTP 403) and relied on secondary summaries for the classification structure; the criteria have been amended since 2017. Confirm the current Third Schedule with the company's auditor before relying on any classification.
- IFRS Foundation: [IAS 2](https://www.ifrs.org/issued-standards/list-of-standards/ias-2-inventories/), [IAS 7](https://www.ifrs.org/issued-standards/list-of-standards/ias-7-statement-of-cash-flows/), [IFRS 15](https://www.ifrs.org/issued-standards/list-of-standards/ifrs-15-revenue-from-contracts-with-customers/) — as cited in the package, supporting design principles. Whether full IFRS, IFRS for SMEs or an AFRS applies to this entity is the open question in §11.6.

These sources support the design principles and identify applicability conditions. They do not establish this entity's statutory obligations and certify nothing.

---

## 14. Cross-document inconsistencies

The brief asks that inconsistencies be reported rather than silently resolved.

| # | Inconsistency |
|---|---|
| 1 | Three of the four appended documents carry "implementation paused" status headers; the brief states the pause was lifted and foundation work resumed. The package flags this as historical, but the stale headers remain on the documents themselves. Use one dated status header per document. |
| 2 | Date model: ACCOUNTING_CLIENT_REQUIREMENTS specifies one "transaction date" plus server timestamps; ADDITIONAL_FINANCE_SCOPE requires document, posting and value dates distinguished (A10). |
| 3 | Access: ACCOUNTING_CLIENT_REQUIREMENTS specifies independent permissions for accounts, project and bank maintenance; the implemented behaviour described in the brief grants it to `finance.manage` **or** `roles.manage` (B4). |
| 4 | Party: the requirements say reuse and extend the existing Party model; the scaffolding uses free-text party names (B8). |
| 5 | Evidence: the requirements mandate private storage with authenticated downloads; the scaffolding stores binary data in the database (B9). The package acknowledges this; it remains a contradiction in the shipped scaffolding. |
| 6 | Reporting capacity: reports are to be read from posted journal lines, while the existing report layer carries a 5,000-document pilot cap (B6). |

---

## 15. What the package gets right

Recorded deliberately, because a review that lists only defects gives a false picture of where this stands.

The refusal to invent opening balances, bank details, rates or company registrations is consistent across every document, including under pressure from a specific unexplained figure. The distinction between cash movement and income or expense is made repeatedly and correctly, including the harder cases — loans, deposits, advances, transfers. Identifying the legacy worksheet as a money-movement register rather than a journal is the most consequential correct call in the package. Blocking live invoice issuance, keeping self-approval disabled, giving the administrator no implicit audit-log access, snapshotting workflow rules at submission, neutralising spreadsheet formula injection, and refusing to treat a project funding gap as a receivable or a loss are all decisions that inexperienced designs get wrong.

The corrections above are a list of mechanisms to put behind rules that are already correctly stated. That is a much better position to be in than the reverse.
