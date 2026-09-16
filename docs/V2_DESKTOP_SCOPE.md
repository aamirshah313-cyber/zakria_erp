# Version 2.0 — desktop transaction register and linked ledgers

Current scope decision: user explicitly narrowed V2.0 to the two client screenshots, their forms/inputs/outputs and forgotten-password recovery. This document supersedes the broader accounting delivery sequence for V2.0 only. The earlier financial accounting scope and independent-review findings remain reserved for a later client-authorized version. Preparing this environment is not a claim that V2.0 business features are already implemented.

## Product boundary

Native Windows desktop application, not a browser window or a hosted website. Retain Flutter Windows and reuse Django authentication/permissions behind a private loopback-only local service. The local service is an internal implementation detail; the eventual desktop launcher must start it automatically without asking the user to run terminal commands. No external web hosting or public network listener is required.

Initial assumption: one company's register on one Windows computer, with separate registered application users sharing the same local database. Multi-computer simultaneous access, cloud sync and Android are deferred. A second computer's independent database must not be represented as synchronized.

Use a distinct V2 development database and private evidence directory. Preserve the original pilot database and passwords. Optional developer initialization can copy the pilot database using SQLite's backup mechanism, retaining accounts/roles but clearing copied bearer sessions. The preparation script must refuse to overwrite existing V2 data. Application updates must not replace business data, passwords or attachments.

## In scope

1. Categories and project/contract records; structured persons/organizations; cash/bank sources and methods. Categories can organize receipts and payments without implying formal chart-of-accounts classification.
2. Transaction Register with receipts/payments, multiple allocation rows where needed, supporting files and configurable approval before confirmation.
3. Automatically generated category/project/party activity statements and cash/bank movement books. No manual duplicate ledger entry.
4. Search, date filters, basic saved field selections, totals, running balances, receipt schedules and receipt/payment charts. Reuse existing PDF/XLSX/CSV capabilities; support practical print layouts for these reports. Additional exports are incremental backlog, not silent removal of original requests.
5. Excel import staging/preview, column and category mapping, explicit duplicate review and reconciliation of source totals. Journal and ledger copies must not both become new transactions.
6. Local password recovery, registered user activation, profiles, editable roles, restricted logs, backup/restore and a native desktop launch/build path.

Existing quotations/invoice drafts remain available unless the user later asks to remove them. They must not automatically create register receipts/payments. Live tax-invoice issuance remains disabled; this scope change does not remove that separate readiness gate.

## Deferred

Double-entry journal posting, trial balance, statutory financial statements, general-ledger control accounts, invoice open-item accounting, depreciation/valuation, payroll calculations, accrual accounting, tax engines/FBR transmission, full imprest/claims accounting, and PostgreSQL financial-posting controls. A transaction can still be labelled Loan, Advance or Donation for categorization, but V2 does not calculate their complete accounting treatment or assert profitability.

Do not expose preliminary accounting scaffolding as a working double-entry module in the V2 navigation. Retain applied migration history; no schema deletion or reset. Its existence is not evidence of completed accounting.

## Compact forms

| Form | Fields and behaviour |
|---|---|
| Category | Unique code, name, description, optional parent/category group, active status. Category names independent of party and funding source. |
| Project / Contract | Code, title, client, contract reference, start/end calendar dates, status, optional locations. |
| Party | Name, organization/person type, contact details; optional customer/supplier/employee/other tags. |
| Cash / Bank source | Name, cash/bank type, account title, bank/branch, optional account number/IBAN as text, active status; restrict sensitive fields. |
| Transaction | Immutable record ID/reference; receipt or payment; calendar date; party; total amount in PKR; cash/bank source; method; instrument/reference; handled-by; beneficiary; remarks; attachments. Allocation lines select category/project and amount. Sum of allocations equals total exactly. |
| Transfer | Source/destination own cash/bank accounts, date, amount, reference; one linked transfer rather than two unrelated records. Exclude from external receipt/payment totals; record charges separately. |
| Supporting evidence | Multiple JPG/PNG/PDF files, filename, uploader, timestamp, size/hash; private authenticated access and no public media URLs. |
| Opening position | Explicit dated opening balance by relevant report dimension, entered through reviewed setup. Do not add independent category/project openings together as though they are separate cash. Prefer reconciled full history when available. |
| Import review | Workbook/sheet/row identity, mapped fields, proposed direction, duplicates, attachment references, missing data and totals. Approve only reconciled rows; preserve excluded summaries as controls. |

The meanings of Sent to and Paid By remain deferred client questions. Keep beneficiary, handled-by user/person, project and funding source distinct, with optional fields so one guessed interpretation does not determine the data model.

Every new date input uses a calendar, including report From/To and As at Date controls. Preserve date-only values. Generated timestamps are read-only. Defaults must use company-local date, not arbitrary device timezone. No guessed fiscal-year dates are prefilled as confirmed configuration.

## Data flow and safeguards retained

Form or staged import → Draft → Submitted → Approved/Confirmed → one transaction and its allocations → read-only derived registers/ledgers/reports.

No double-entry accounting is generated. Derive cash/bank balances from receipts minus payments; the legacy project view may display payments minus receipts only with an explicit label and legend. Separate transfer effects. Define opening balance and date range on every statement. Do not call a project funding gap a customer debt or a loss.

Retain decimal arithmetic, stable IDs, duplicate-request protection, approval version checks, maker/approver separation, private attachments, role checks and audit history. These remain relevant even without double-entry. Confirmed transaction corrections require a traced cancellation/replacement or revision model, never invisible overwriting. Reporting must have an explicit current-versus-historical revision policy.

Suggested entities for the later implementation: RegisterCategory, RegisterTransaction, RegisterAllocation, RegisterEvidence, RegisterRevision/Approval, ImportBatch/ImportRow and scoped OpeningPosition; extend/reuse Party and Project rather than silently duplicating identities. Keep module tables separate from preliminary Voucher/JournalLine accounting scaffolding. No speculative GL entries are created from register transactions.

## Outputs

- Transaction Register, Receipt Register and Payment Register.
- Category Ledger / Project Activity Statement / Party Activity Statement.
- Cash Book and Bank Book (recorded movements, not a claim of bank reconciliation).
- Receipt summary derived from the same transaction records as the detailed ledger.
- Cash movement charts and category/project breakdowns with drill-down.
- Pending approvals, missing-evidence and import-exception reports.
- Daily, selected-date, monthly, quarterly, half-yearly and configured fiscal-year filters; appropriate opening/movement/closing values.

Carry the sample receipt discrepancy as an import exception: main ledger receipts 59,202,802 versus summary 63,612,061. Do not silently insert 4,409,259. Test data is isolated and clearly labelled; no real balances are inferred from screenshots.

## Forgotten-password recovery (V2 implementation requirement)

Provide Forgot password on sign-in. Desktop operation must not depend on unconfigured email or an internet service.

1. Authenticated users can create/regenerate high-entropy, single-use recovery codes after entering their current password. Display codes once for offline storage; store only hashes. Regeneration invalidates old codes. Recovery requires username, valid code and a new password satisfying policy; no username-only reset or security-question bypass.
2. A separately authorized password-reset administrator may issue a short-lived, single-use reset token after identity verification. Deliver it locally outside audit logs; do not set a universal/default password or expose the user's current password. Reset tokens must be hashed, scoped and expire.
3. Successful recovery consumes the token/code atomically, changes the password, invalidates all sessions and outstanding reset tokens, and writes an audit event without secret values. Recovery does not activate a suspended/pending account or change its role. User existence and invalid-code errors are generic; rate-limit persistent attempts.
4. If all administrators lose access and no code exists, use a documented owner-controlled maintenance recovery path with interactive local verification, not a hidden application backdoor. It requires a separately designed procedure before release.

Email reset can be added later when a verified address and configured mail service exist. Role changes and access activation remain separate operations.

## Environment and release stages

Preparation: V2 scope and separate desktop settings/data path, prerequisite check, safe database initialization, dependency list and native Windows source/build path. This is the current task.

Implementation 1: register/category/project forms, private attachments, confirmation/permissions and generated ledger views.

Implementation 2: imports, report filters/layouts/exports and recovery workflows with regression tests.

Desktop release: bundle the local Python service and runtime with the Flutter executable; use a Windows-compatible WSGI server; automatic hidden startup, single-instance/service ownership handling, readiness checks, controlled shutdown and per-user writable data location. Package the complete Flutter release directory with required DLLs/data, not the EXE alone. Test on a clean Windows computer without Python/Flutter installed. Configure backup/restore and update behaviour. Signing/installer choices remain delivery requirements.

Internal localhost HTTP does not make the user experience web-based, but the service still needs authentication and must never bind all network interfaces by default. DEBUG=False, a persistent private secret and localhost-only allowed hosts are required. Existing browser development remains separate from this desktop profile.

## User actions later

Confirm Windows deployment/share arrangement, report naming and category list when convenient; these do not block environment preparation. Preserve recovery codes and backups when implemented. No credentials, tax numbers, sample imports or financial opening balances are required for this preparation step.
