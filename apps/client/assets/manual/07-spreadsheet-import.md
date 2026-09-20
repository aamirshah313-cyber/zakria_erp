# 7. Spreadsheet import

Screen: **Transaction register → Import spreadsheet** ("Import register transactions").
Needs `register.view`, `register.create` **and** `register.import`.

Import turns rows of an existing cash book into **drafts**. Nothing is confirmed by
importing: every draft still goes through the normal review, so an import cannot put an
unchecked figure into the accounts.

## What files are accepted

| Limit | Value |
|---|---|
| Formats | `.xlsx` or UTF-8 `.csv` (convert older `.xls` first) |
| File size | Up to 5 MB |
| Sheets | Up to 20 per workbook |
| Rows | 1 to 1,000 transaction rows staged at a time |
| Columns | Up to 40 |
| Cell length | Up to 4,000 characters |

Refused outright: macros (`vbaProject`), XML document types or entities, encrypted
workbooks, and any **formula** in a mapped cell — a formula is not evidence, so the row
must carry the verified value or be excluded. Embedded images are ignored with a warning;
attach documents to the resulting drafts instead.

## Step 1 — Choose the file and sheet

The application reads the file and shows the sheets with their first rows
(24-import-inspect.json), so you can see which sheet
holds the cash book and which line is the heading. Then you give the **header row number
(1–50)** and stage the batch. Blank rows are skipped; rows below the header become the
batch.

The example file, a four-line September cash book
(23-import-source.csv):

```csv
Date,Description,Category,Cash/bank,Paid,Received,Voucher,How paid
2026-09-22,Capital Builders (Pvt) Ltd,Client receipts,Bank current account,,275000.00,IBFT-81004,transfer
2026-09-24,Al-Rehman Traders,Materials,Main cash box,64200.00,,INV-2477,cash
2026-09-26,Riaz Masood,Labour and wages,Main cash box,71000.00,,WS-09-4,cash
TOTAL,,,,135200.00,275000.00,,
```

## Step 2 — Map the columns

For each field, choose the spreadsheet column or a default value for the whole batch.

| Setting | Choices |
|---|---|
| **Amount columns** | *One amount + receipt/payment type*, or separate **Payment amount** and **Receipt amount** columns |
| **Date format** | ISO year-month-day only, Day/month/year, or Month/day/year |
| Transaction date, Organization / person | Required mappings |
| Category, Cash/bank source, Project, Party record | Map a column, or choose one default for the batch |
| Payment method, Transaction nature, Income/expense classification | Map a column or set a default |
| Instrument / reference, Handled by, Beneficiary, Remarks | Optional |

With separate amount columns, exactly one of the two must be positive on each row. With a
single amount column, the direction column must say receipt or payment — debit and credit
are not guessed.

Category, account, project and party names are matched to master records by name or code,
case-insensitively. Anything that does not match exactly one **active** record is an error;
**Map spreadsheet values** lets you point a spelling in the file at the right master record
without editing the file.

## Step 3 — Preview, exclude and explain

**Create register drafts** produces a row-by-row preview
(25-import-preview.json). Each row shows the values it
would create, the master records it matched, and any errors:

```json
{ "row": 2, "errors": [], "duplicates": [],
  "payload": { "date": "2026-09-22", "direction": "receipt", "amount": "275000.00",
               "party": "Capital Builders (Pvt) Ltd", "method": "transfer",
               "reference": "IBFT-81004", "category": 1, "source": 2 },
  "labels": { "category": "Client receipts", "source": "Bank current account" } }
```

Decisions you can record:

- **Exclude with reason** — for control totals, headings and subtotals. The reason (5–500
  characters) is kept. In the example, row 5 is excluded as *"Spreadsheet control total
  row, not a transaction."*
- **Explain separate transaction** — when a row looks like a duplicate of an existing entry
  (same date, direction and amount) or of another row in the batch, it must either be
  excluded or explained.

**Control totals** are required: type the receipt and payment totals from the source
document (0 where there are none). The preview compares them with the rows it would import
and refuses to go further if they differ, naming the difference. This is what catches a
mis-mapped column or a missed row. The example matches:

```json
{ "ready": true, "included": 3, "excluded": 1,
  "totals": { "receipt": "275000.00", "payment": "135200.00" } }
```

## Step 4 — Commit

Committing needs the preview to be clean and the **acknowledgement** tick. The service then
re-runs the whole preview and compares it with what you saw; if matching register entries
have changed in the meantime, it stops and asks you to review again.

Result (26-import-committed.json):

```json
{ "id": 1, "filename": "september-cash-book.csv", "sheet": "CSV", "status": "imported",
  "entries": [ { "source_row": 2, "entry_id": 11 },
               { "source_row": 3, "entry_id": 12 },
               { "source_row": 4, "entry_id": 13 } ] }
```

Each created draft remembers the file hash, sheet and source row it came from, and the
entry screen shows that origin. Importing the same workbook, sheet and row again is refused
— *"This exact workbook/sheet/source row was already imported, including cancelled
entries."* — so the same cash book cannot be loaded twice by mistake.

An imported batch is read-only. Drafts it created are ordinary drafts: review them, attach
documents, submit and confirm as usual. In the worked example the three imported drafts
were confirmed and appear as REG-000011 to REG-000013, adding 275,000 in receipts and
135,200 in payments to the September figures.

## My recent import batches

The screen lists your last 50 batches with file name, sheet, status and date. Statuses are
**staged** (read but not previewed), **reviewed** (previewed, ready or with errors),
**imported** (committed, read-only) and **deleted** (removed through Data management; it
must be restored before it can be used again, and it must be previewed again).

## Importing setup records instead

**Import setup records** loads categories, cash/bank accounts, projects or parties. It
never overwrites an existing record, and it is described in
[chapter 4](chapter:04-register-setup).
