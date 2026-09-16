# Client ledger analysis and deferred requirements

Date: 11 September 2026; status updated 12 September 2026. This is requirements analysis; subsequent foundation implementation resumed after user authorization. See IMPLEMENTATION_STATUS.md and REVIEW_DECISIONS.md for current delivery status and independent-review corrections. No test data was inserted and no application source or database was changed by the original ledger analysis.

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
