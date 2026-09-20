# 8. Reports and statements

Two screens use the same calculation:

- **Activity ledger**, on the Transaction register screen — a quick statement between two
  dates, with an optional CSV export.
- **Report builder**, at **Reports / Print** — the full statement with fields, grouping,
  layout and exports to PDF, Excel, CSV, PNG and JPEG.

Viewing needs `register.view`; every export needs `register.export`.

Only **confirmed** records are included. Drafts, submitted records and cancelled records
never appear in a statement.

## Activity ledger

Filters: **From date**, **To date**, and optionally category, cash/bank source, project or
party. **Generate ledger** shows opening, receipts, payments, transfers and closing above
the rows; **Export CSV** downloads the same thing.

Example for the quarter ([29-ledger.json](examples/29-ledger.json),
[30-ledger.csv](examples/30-ledger.csv)):

```json
{ "count": 13, "opening": "0.00", "receipts": "1325000.00", "payments": "826150.00",
  "closing": "498850.00", "transfers_in": "150000.00", "transfers_out": "150000.00" }
```

Choosing a project without an account switches the ledger to a **Project Activity
Statement**, whose balance is *payments less receipts* — money applied to the job. For the
fit-out ([37b-project-statement.json](examples/37b-project-statement.json)): receipts
400,000, payments 401,500, closing 1,500 spent beyond what the client has paid.

## Report builder

### Reporting period

| Choice | Meaning |
|---|---|
| Custom date range | **From date** and **To date**; either may be empty for open-ended |
| As at date | Everything up to the chosen day |
| Selected day | One day |
| Month containing selected date | Calendar month |
| Fiscal quarter / half-year / financial year containing selected date | Uses **Fiscal year starts in** (July by default) |

### Filters

Category, project, cash/bank source, party record, **Source type** (cash or bank),
**Entries** (receipts only, payments only or both), payment method, transaction nature,
income/expense classification, **Organization / person contains**, **Beneficiary
contains**, **Handled by contains**, **Instrument / reference contains**, minimum and
maximum amount, and **With supporting files** (present or missing).

Text filters match part of a word, case-insensitively. Amount filters apply to the original
transaction total, before any split.

### Report fields

Tick any of these columns, in the order the application lists them:

| Field | Shows |
|---|---|
| Date | Transaction date |
| Register reference | `REG-000001` / `TRF-000002` |
| Organization / person | The party text on the record |
| Category, Project / contract, Cash / bank source | The master records |
| Receipt / payment | Direction |
| Payment method, Instrument / reference | How it moved, and its number |
| Receipts (PKR), Payments (PKR) | The amounts, split into two columns |
| Transfers in (PKR), Transfers out (PKR) | Own-account movements |
| Running balance (PKR) | Cumulative, following the balance basis |
| Remarks, Beneficiary, Handled by | The narration and the people |
| Transaction nature, Income / expense classification | The two classifications |
| Prepared by, Approved by, Confirmation timestamp | Who and when |
| Supporting files | How many active documents the record has |

### View, grouping and balance basis

- **Report view**: *Transaction detail* (one row per record) or *Grouped summary* (one row
  per group with counts and totals).
- **Group chart / summary by**: day, month, fiscal quarter, financial year, category,
  project, cash/bank source, organization/person, payment method, transaction nature,
  income/expense classification, beneficiary, handled by, prepared by, approved by.
- **Balance presentation**: *Cash basis: receipts less payments, including transfers*, or
  *Project activity: payments less receipts*.

Grouped summary by project, from the example
([32-report-by-project.json](examples/32-report-by-project.json)):

| Group | Rows | Receipts | Payments | Net |
|---|---|---|---|---|
| Boundary wall — Phase II | 4 | 650,000.00 | 238,300.00 | 411,700.00 |
| G-11 Markaz office fit-out | 4 | 400,000.00 | 401,500.00 | −1,500.00 |
| Unassigned | 6 | 275,000.00 | 186,350.00 | 88,650.00 |

The split payment appears as 180,000 under the fit-out and 120,000 under the wall — the
allocation, not the whole 300,000 twice.

### Print layout and colours

**Report title**, **Additional header**, **Page footer**, **Paper** (A4 or A3),
orientation, **Report colour (#RRGGBB)** and **Include chart in PDF and Excel**. Saved
layouts keep all of it.

## Openings in a report

An approved opening balance is included only when the report is filtered to exactly that
one account, category, project or party, with no other filters. Otherwise the statement
starts from zero and says so. Compare:

| Report | Opening | Receipts | Payments | Transfers out | Closing |
|---|---|---|---|---|---|
| Whole company ([31](examples/31-report-detail.json)) | 0.00 | 1,325,000.00 | 826,150.00 | 150,000.00 | 498,850.00 |
| Main cash box only ([37a](examples/37a-report-cash-account.json)) | 350,000.00 | 400,000.00 | 487,400.00 | 150,000.00 | 112,600.00 |

The cash-box report carries the note: *"Includes approved opening OP-000001 at start of
2026-07-01. Movements before that cutoff cannot be included."*

## The basis note

Every report, in every format, carries the sentence that says what the figures are:

> Receipts less payments, plus transfers in less transfers out. … Current revision excludes
> cancelled records. This is not profit, debt or a reconciled bank balance. Grouped detail
> can contain allocation rows from the same transaction.

Filtering by income/expense classification or by amount adds: *"Income and expense figures
are explicitly classified cash receipts/payments, not accrual financial statements."*

## Exports

| Format | File | What it contains |
|---|---|---|
| PDF | [33-register-report.pdf](examples/33-register-report.pdf) | Company name, logo, title, period, filters, totals, basis, bar chart, table; A4/A3, portrait or landscape, page numbers and footer |
| Excel | [34-register-report.xlsx](examples/34-register-report.xlsx) | Three sheets — Report details, Report rows (frozen heading, filters, number formats, print setup), Grouped summary with a bar chart — each with the logo banner |
| CSV | [36-register-report.csv](examples/36-register-report.csv) | Metadata block, then the table; UTF-8 with BOM, and text that starts with `=` is escaped so a spreadsheet cannot execute it |
| PNG / JPEG | [35-register-report.png](examples/35-register-report.png) | A one-page chart summary for sharing, 1,600 px wide with the logo and the totals |

The CSV header block is the audit trail of the report itself:

```csv
Company,Muhammad Zakaria and Sons
Report,Transaction activity — July to September 2026
Period,Custom: 2026-07-01 to 2026-09-30
Filters,"All categories, projects, parties and cash/bank sources"
Generated,2026-09-20 19:55:49 PKT
Generated for,finance.officer
Opening (PKR),0.00
Receipts (PKR),1325000.00
Payments (PKR),826150.00
Closing (PKR),498850.00
```

Every export is written to the audit log with its format and row count.

## Saved report layouts

**Save layout** stores the whole definition under a name, per user
([37-saved-report.json](examples/37-saved-report.json)). Saved layouts appear in **Saved
report layouts** to load, **Update saved report** with current settings, or **Archive
layout**. Names must be unique per person; archived layouts can be restored from
[Data management](10-data-management.md).

## Limits

| Limit | Value |
|---|---|
| Records examined per statement | 50,000 |
| Rows in one statement | 10,000 |
| Rows in a PDF | 2,000 — use grouped summary or Excel beyond that |
| Preview page size | 100 rows |
| PDF column width | Too many wide columns are refused with advice to choose A3 landscape or fewer fields |
