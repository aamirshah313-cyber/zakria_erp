# 1. Overview

Zakaria ERP is a Windows desktop application for Muhammad Zakaria and Sons. It records the
money the business receives and pays, who approved each record, and what evidence supports
it, then produces statements and reports from those records.

## The two modes

The same code runs in two modes. The health endpoint reports which one is active
(01-health.json):

```json
{ "service": "Zakaria ERP", "version": "2.1.0", "mode": "desktop-register" }
```

| Mode | Where | What it offers |
|---|---|---|
| `desktop-register` (V2.1) | The installed Windows application, and the portable package | Transaction register, openings and transfers, spreadsheet import, reports, backups, data management, users and roles, audit log |
| `development-pilot` (V1) | The earlier web/pilot deployment | Quotations, invoices, customers and suppliers, approval rules, company settings, document reports, accounting setup |

Chapters 3 to 12 describe the desktop register. Chapter 13 describes the pilot document
module, which is still in the code and still reachable when the pilot is deployed. The
desktop application hides the pilot screens that do not apply.

## How the parts fit together

- **The application window** (Flutter) draws every screen and talks only to the local
  service over `http://127.0.0.1:8765`.
- **The bundled service** (`zakaria_service.exe`, Django and waitress) holds the rules,
  the audit trail and the database. It listens on the loopback address only, so nothing on
  the office network or the internet can reach it.
- **The database** is one SQLite file, `register.sqlite3`. Supporting documents are stored
  inside it, so one file is a complete copy of the business records.
- **The launcher** starts the service when the application opens and stops it when the
  application closes, showing a "Starting Zakaria ERP…" window while the database is
  prepared or upgraded.

Installed layout, shared by every Windows account on the computer:

```
C:\ProgramData\ZakariaERP\
  register.sqlite3        the database: records, documents, accounts, roles, passwords
  service-secret.txt      the service's own key; never copied into a backup
  backups\                automatic daily copies, plus copies made before restores/upgrades
  evidence\               reserved
  logs\service.log        service log, rotated
  restore-staging\        temporary space while a restore is checked
```

## What the register records

One record per movement of money, in one direction, from or into one cash or bank account:

- a **receipt** (money in) or a **payment** (money out), with its date, amount, party,
  category, optional project, method and reference;
- an optional split of that amount across several categories or projects;
- an **opening balance** where history starts, and **own-account transfers** between the
  company's own cash and bank accounts;
- supporting documents (PNG, JPEG or PDF) attached to the record;
- who prepared it, who reviewed it, and when.

Every figure the application reports is the sum of those movements.

## What it deliberately does not do

- **No double entry.** There is no general ledger, trial balance, profit and loss or
  balance sheet. The register is single-entry cash movement. Report totals are labelled
  accordingly: *"This is not profit, debt or a reconciled bank balance."*
- **No tax filing or e-invoicing.** Live invoice issuance is blocked in the pilot module
  until accounting and tax work is done.
- **No payroll, fixed assets or inventory.**
- **No multi-computer or cloud sync.** One computer holds the data; other computers get a
  copy only through a backup file.
- **No phone access yet.** An Android test build exists but cannot sign in until a decision
  is made about how phones reach the data (see [chapter 2](chapter:02-getting-started)).

## The worked example used throughout

Chapters quote one invented dataset for Muhammad Zakaria and Sons covering July to
September 2026: two cash/bank accounts, five categories, two projects, three parties, an
opening balance, thirteen confirmed movements, one cancelled entry, one internal transfer,
one spreadsheet import of three rows, and one attached document.

Its headline figures, taken from 31-report-detail.json:

| Figure | Value (PKR) |
|---|---|
| Statement rows | 13 |
| Receipts | 1,325,000.00 |
| Payments | 826,150.00 |
| Closing (receipts less payments) | 498,850.00 |
| Internal transfers in / out | 150,000.00 / 150,000.00 |

All example files are listed in examples/README.md.
