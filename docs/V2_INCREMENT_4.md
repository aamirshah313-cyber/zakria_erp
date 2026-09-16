# V2 increment 4 — client register and project statements

Approved scope: the two client worksheets, implemented as a controlled single-entry receipts/payments register. Full double-entry accounting remains deferred. Screenshot names, items and balances remain examples; this increment inserts no sample business records.

## Delivered functionality

- Category descriptions and cycle-checked parent hierarchy.
- Existing Party master reused for customers, suppliers, contractors, employees and others; organization/person type and active status. Register entries can link a party while preserving their transaction-name snapshot.
- Project client, contract reference, location, contact and email fields.
- Bank account title, bank, branch, account number and IBAN; identifiers remain text, IBAN format/checksum validated. `register.bank_details` controls viewing and editing bank fields; existing roles are not silently granted this permission.
- Separate transaction nature and beneficiary fields. Loans, advances, deposits and investments are distinguished from operating receipts/payments without inventing a full accounting treatment.
- Up to 50 category/project allocation lines per receipt/payment; positive amounts must equal the transaction total exactly. Reports and dashboard distributions use allocated amounts without repeating the transaction total.
- Reviewed opening balances for one account/category/project/party scope. Existing earlier confirmed history prevents an overlapping opening; confirmation/import rechecks dates against reviewed cutoffs. Scope-specific openings are never added across independent dimensions.
- Linked own-account transfers, excluded from external receipt/payment totals; internal transfer columns explain cash/bank balance changes. Charges remain separate payments.
- Separate preparer/reviewer controls, version checks, idempotent creation, return and reasoned cancellation for openings/transfers. References use OP/TRF prefixes; their dedicated screen shows the pending records.
- Extended import mapping for party records, transaction nature and beneficiary; original party text and source-row origin retained. Existing controls and duplicate checks remain; imports create drafts only.
- One movement calculation for ledgers and report exports. Project statements can display payments less receipts; cash books show receipts less payments plus transfer movement. Party/project filters do not assert debt, profit or reconciled bank balances.
- Report field selection/order, filters, missing-file review, grouping, calendar/date and fiscal-month presets, personal saved layouts, colours, headers/footers, A4/A3 portrait/landscape PDF, Excel/CSV and PNG/JPEG chart export.
- Browser/native amount formatting preserves decimal cents without converting server money strings to binary floating point.

## Acceptance sequence

1. Open http://127.0.0.1:5174/ and use the application Refresh button or sign out/in to reload role permissions. Administrator and Finance Manager register access was explicitly activated on 15 September after the user reported missing V2 screens; see IMPLEMENTATION_STATUS.md. The Administrator sidebar now includes Register setup and Transaction register. In Roles & permissions, explicitly grant `register.bank_details` to designated staff who also have `register.manage` when editing. Bank-identifier access and audit access were not granted by this activation.
2. In Register setup, review category/party/project records and bank fields. Keep real identifiers out of synthetic tests. Existing party names have not been automatically matched or classified from screenshots.
3. Have the separate reviewer register, then activate that account with the General Manager role in Users. The General Manager register approval rule is configured; there was no active General Manager account at activation. Prepare one small TEST payment split between two projects. Attach its supporting file, submit as Finance and confirm using the assigned separate reviewer. Check that the overall payment occurs once and each project receives only its allocated amount.
4. Under Openings / Transfers, test an opening on a new TEST scope with no earlier confirmed entries. Enter the supporting reference and review it before confirmation. Test an internal transfer: source decreases, destination increases and external totals remain unchanged.
5. Generate the activity ledger and Reports / Print. Select a single project and payments-less-receipts presentation to reproduce the client's project convention. Select a single bank account for its opening and movements. Review grouped/detail totals, saved layouts and exports.
6. Import a copy of a client workbook. Map beneficiary and handled-by separately; select or map the optional party master. Use independently verified control totals. Review duplicated receipt schedules before committing drafts. Attach embedded supporting images separately.

## Explicit limits and remaining work

- Openings are included only for one selected scope with no extra method/direction/nature/evidence/text filters. More restrictive reports show filtered movement with a basis explanation, not a fabricated opening. Query periods before an approved cutoff are rejected.
- Opening/transfer forms currently store an evidence reference and location, not binary attachments. Correct these drafts by reasoned cancellation and replacement. Receipt/payment entries retain private binary supporting files.
- Historical reports use current revision: cancellations change the current view while audit history remains. They are not frozen past-issued statement snapshots.
- Current Party classification is one selected class (with a customer/supplier Both option), not arbitrary simultaneous tags. Project status uses active/inactive plus dates.
- Fiscal-month report presets require selecting the confirmed company year-start month; July is clearly identified as an initial option, not a confirmed tax policy.
- Report details have a 10,000-row limit and a 50,000-record historical query limit. PDF detail is limited to 2,000 rows and rejects unreadably wide selections; use A3 landscape, fewer fields, summary, or Excel. Opening/transfer worklist shows latest 1,000 records.
- PNG/JPEG exports are charts, not images of every table page. Embedded Excel objects are not extracted. Split allocations can be edited on imported drafts; import does not infer multi-line allocations across duplicate sheets.
- A native Windows acceptance EXE with automatic bundled-service startup is built; see IMPLEMENTATION_STATUS.md for its path and launch verification. A clean-machine installer, user-facing backup/restore and maintenance recovery remain outstanding. Android is paused. Both native and browser acceptance use the isolated V2 database.
- Full double-entry, payroll, assets, statutory statements, complete bank reconciliation and FBR remain deferred.

## Verification

Backend full suite: 54 tests passed, including 8 extension tests covering scope totals, cutoffs, transfer treatment, bank access/identifier preservation, party snapshots, export formats and report ownership. All 12 Flutter tests pass, including detailed approval review, report permissions, narrow chart layout and decimal money formatting. A4 landscape multi-page output, A3 portrait summary and chart images were rendered with synthetic records and inspected. Final build and local-service results are recorded in IMPLEMENTATION_STATUS.md.

Migrations 0006–0008 were applied only to `storage/v2-desktop/register.sqlite3` after backup `storage/backups/before-register-extension-20260914-153414-082625.sqlite3`. SQLite integrity, user/password/role preservation, register count and unchanged pilot-file hash were verified.
