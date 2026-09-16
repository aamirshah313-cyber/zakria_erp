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

At the review snapshot, 22 backend tests passed, including six new accounting-setup tests. The Flutter calendar test and two access tests also passed (25 tests overall). The web rebuild is in progress. The new accounting migration was applied after a local SQLite backup; active users remain and new accounting master tables are empty. No sample transactions or opening balances were inserted. No production readiness is claimed.

The preliminary Voucher/JournalLine/Evidence models are scaffolding only, with no exposed posting API. They are not an approved final schema: the party-name text must evolve to structured party relationships; transaction/source identity, cash/bank masters, complete workflow history, private file storage and posting/reversal invariants need further work. Current Evidence scaffolding stores binary data in the database; the target private-storage design must be resolved before evidence functionality ships. Closed-year setup does not yet protect financial postings because financial posting is not implemented. The starter chart is an editable beginning, not a universally mandated code scheme or complete statement mapping.

Known outstanding production prerequisites include PostgreSQL concurrency verification, backups/restore, durable login throttling and recovery, production hosting/HTTPS, native signing/testing, posting/settlements, imports, payroll/assets/advances and framework-specific financial statements/tax integration.

## Reconciliation example to challenge

Visible project-ledger totals: debits PKR 70,438,638; credits PKR 59,202,802; balance PKR 11,235,836. Four listed receipts sum to 59,202,802. A fifth receipt of 4,409,259 appears only in a bottom summary, taking summarized receipts to 63,612,061. If it belongs in the same main-ledger scope, the conditional balance is 6,826,577. This is an unresolved source discrepancy, not permission to insert a balancing entry. The balance is not automatically loss, receivable or bank cash. Repeated summary receipts must not become duplicate imported transactions.

## Material supplied

The combined review package appends the accounting requirements, project-ledger analysis, additional payroll/assets/advances/reporting scope and original pilot status. Earlier status dates and pause notes remain historical context; use this brief to distinguish current work. No live database, credentials or raw bank evidence is included. Where documents differ, report the inconsistency rather than silently choosing a preferred version.
