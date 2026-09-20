# Zakaria ERP — complete manual

What the application does, module by module and form by form, with a worked example whose
outputs are included as proof. Written for build **2.1.0.11** (September 2026).

Everything in the `examples/` folder is a real response or export from the code in this
repository, produced by one script against a throwaway database. No company data is used.

## Contents

| # | Chapter | Covers |
|---|---|---|
| 1 | [Overview](01-overview.md) | What the system is, its two modes, where data lives, what it does not do |
| 2 | [Getting started](02-getting-started.md) | Installing, first run, signing in, forgotten passwords, the phone app |
| 3 | [Access control](03-access-control.md) | Roles, the full permission list, user accounts, sessions |
| 4 | [Register setup](04-register-setup.md) | Categories, cash/bank accounts, projects, parties, approval role, setup imports |
| 5 | [Receipts and payments](05-receipts-and-payments.md) | The main form, classification, splits, review workflow, documents, cancellation |
| 6 | [Openings and transfers](06-openings-and-transfers.md) | Opening balances, own-account transfers, cut-off rules |
| 7 | [Spreadsheet import](07-spreadsheet-import.md) | Staging a workbook, mapping columns, control totals, committing drafts |
| 8 | [Reports and statements](08-reports.md) | Activity ledger, report builder, every field and grouping, PDF/Excel/CSV/image |
| 9 | [Dashboard](09-dashboard.md) | Overview figures, approvals queue, monthly and category charts |
| 10 | [Data management](10-data-management.md) | Removing and restoring drafts and setup records |
| 11 | [Backup and restore](11-backup-and-restore.md) | Manual and automatic copies, passwords, restoring, moving to a new computer |
| 12 | [Audit log](12-audit-log.md) | What is recorded, who may read it, exporting |
| 13 | [Quotations and invoices (pilot)](13-documents-pilot.md) | The earlier document module, parties, approval rules, company settings |
| 14 | [Reference](14-reference.md) | Endpoints, statuses, limits, file formats, glossary |

The worked example and its files: [examples/README.md](examples/README.md).

## Keeping this manual current

1. Change or add the feature, with its tests.
2. Extend `scripts/build_manual_examples.py` so the new behaviour appears in the example
   data, then run it:

   ```bash
   .\.venv\Scripts\python.exe scripts\build_manual_examples.py
   ```

   It builds a temporary data folder, drives the real API, rewrites every file in
   `examples/`, and deletes the folder. It never touches `storage\v2-desktop` or
   `C:\ProgramData\ZakariaERP`.
3. Update the chapter that owns the feature, and the [reference](14-reference.md) tables if
   permissions, endpoints or limits changed.
4. Note the build number at the top of this file and in the chapter you changed.

Chapters follow the application's own words: a heading here matches the screen or button
in the app, so a reader can move between the two without translating.
