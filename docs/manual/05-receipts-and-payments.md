# 5. Receipts and payments

Screen: **Transaction register** (permission `register.view`). This is the main working
screen: the list of every record, the **New receipt / payment** form, and the review
actions. Preparing needs `register.create`; confirming needs `register.approve`.

## The list

Newest first, 100 rows per page, with **Previous** and **Next**. Each row shows the
reference (`REG-000001`), date, organization or person, category, cash/bank account,
amount, direction and status, plus the number of supporting documents. Removed drafts are
hidden; cancelled records stay visible.

The row menu offers, depending on status and permission: **View entry details**,
**Supporting documents**, **Edit draft**, **Submit for approval**, **Confirm entry**,
**Return to preparer**, **Cancel with reason**.

Header buttons: **New receipt / payment**, **Refresh**, **Openings / Transfers**,
**Reports / Print**, **Delete / restore**, **Import setup records**, **Import spreadsheet**.

Live list from the worked example: [28-entries-list.json](examples/28-entries-list.json).

## The receipt / payment form

| Field | Required | Notes |
|---|---|---|
| **Entry type** | Yes | Receipt (money in) or Payment (money out) |
| **Transaction date** | Yes | The day the money moved, not the day it was typed |
| **Amount (PKR)** | Yes | Greater than zero, two decimal places |
| **Category** | Yes | Active categories only |
| **Cash / bank account** | Yes | Active accounts only |
| **Organization / person** | Yes | Free text; filled automatically when a party record is chosen |
| **Party record** | No | Link to a master party; optional for older entries |
| **Project / contract** | No | For work that is reported separately |
| **Payment method** | Yes | Cash, transfer, cheque, card or other |
| **Transaction / cheque reference** | No | Cheque number, transfer reference, bill number |
| **Beneficiary / sent to** | No | Who ultimately received the money |
| **Handled by** | No | The person who carried the cash or made the transfer |
| **Income / expense classification** | No | See below; defaults to *Pending classification* |
| **Transaction nature** | No | Operating, advance, loan principal, deposit, investment, capital, donation |
| **Remarks** | No | The narration shown on statements |
| **Split across categories / projects** | No | See allocations below |

A prepared draft, exactly as stored
([13-receipt-draft.json](examples/13-receipt-draft.json)):

```json
{ "id": 1, "date": "2026-07-04", "direction": "receipt", "party": "Capital Builders (Pvt) Ltd",
  "amount": "400000.00", "method": "cheque", "reference": "CHQ-884120",
  "reporting_class": "income", "nature": "operating", "handled_by": "Site office",
  "category_name": "Client receipts", "source_name": "Main cash box",
  "project_name": "G-11 Markaz office fit-out", "status": "draft", "version": 1 }
```

### Income / expense classification

Money moving is not the same as income or expense. The classification says which of the
two, if either, this movement is:

| Choice | Meaning |
|---|---|
| **Pending classification** | Not yet decided (the default) |
| **Income received** | A receipt that is genuinely income — only with nature Operating or Donation |
| **Expense paid** | A payment that is genuinely an expense — same nature rule |
| **Other funds movement** | Loans, advances, deposits, investments, capital — money that moved without being income or expense |

The service refuses a mismatch
([45-refused-requests.json](examples/45-refused-requests.json), second entry):

> Income requires a receipt and expense requires a payment, with Operating or Donation
> nature. Classify principal, advances and deposits as Other funds movement.

Reports can filter on this, so a loan repayment never inflates "expenses".

## Splitting one payment across categories or projects

Tick **Split across categories / projects** when one bill covers more than one job. Each
allocation line takes a category, an optional project and an amount. Rules:

- 1 to 50 lines;
- the lines must add up to the transaction total **exactly**;
- every category and project on a line must be active;
- the header category and project follow the first line;
- when editing a draft, send all the lines, not only the changed one.

The example splits one supplier bill of PKR 300,000 between the two projects
([15-split-payment-draft.json](examples/15-split-payment-draft.json)):

```json
{ "amount": "300000.00", "party": "Al-Rehman Traders", "reference": "INV-2450",
  "allocations": [ { "category": 2, "project": 1, "amount": "180000.00" },
                   { "category": 2, "project": 2, "amount": "120000.00" } ] }
```

Reports use the allocated amounts. Grouping by project shows 180,000 under the fit-out and
120,000 under the wall; grouping any other way keeps one row of 300,000, never the full
amount repeated on each project.

## The review workflow

```
draft ──submit──▶ submitted ──confirm──▶ confirmed ──cancel──▶ cancelled
  ▲                    │                                  ▲
  └────── return ──────┘                 (with a reason, register.cancel)
```

| Status | Who can act | What is possible |
|---|---|---|
| **draft** | The preparer who created it | Edit, submit, attach or withdraw documents, remove (Data management) |
| **submitted** | The approval role, but never the preparer | Confirm or return to the preparer |
| **confirmed** | Anyone with `register.cancel` | Appears in reports and balances; can only be cancelled, never edited |
| **cancelled** | — | Kept in history with its reason; excluded from reports |
| **deleted** | `register.delete` | A removed draft, restorable from Data management |

Other safeguards:

- **Version numbers.** Every record carries a version, and every action sends the version
  it saw. If someone else changed the record first, the action is refused with "Record
  changed. Refresh before trying again."
- **Separation of duties.** Confirming your own submission is refused even when you hold
  both permissions ([45-refused-requests.json](examples/45-refused-requests.json), last
  entry): *"Only the assigned approval role can review another preparer's submission."*
- **Re-checks at confirmation.** Inactive categories, accounts, projects or parties, an
  unbalanced split, or a date before an approved opening all block confirmation, not just
  the original typing.
- **Safe retries.** Each new record carries a one-time request key, so a repeated click or
  a lost reply cannot create the same record twice; sending the same key with different
  content is refused.

The example shows a submission waiting for review
([16-entry-awaiting-approval.json](examples/16-entry-awaiting-approval.json)), returned for
correction ([17-entry-returned.json](examples/17-entry-returned.json)), corrected, resubmitted, and
then confirmed ([14-receipt-confirmed.json](examples/14-receipt-confirmed.json)):

```json
{ "id": 1, "status": "confirmed", "version": 3, "approved_by": 3,
  "confirmed_at": "…" }
```

## Supporting documents

Row menu → **Supporting documents**, on the preparer's own draft.

| Rule | Value |
|---|---|
| File types | PNG, JPEG or PDF — the name **and** the file's own signature must agree |
| Size | Up to 5 MB each |
| Count | Up to 10 per record, including withdrawn ones |
| Duplicates | The same file cannot be attached twice to one record |
| Storage | Inside the database, so backups contain them |

A document can be **withdrawn** with a reason of 1–500 characters. It stops counting and
can no longer be opened, but its name, hash and reason stay in history. Nothing is ever
deleted outright. Uploading or withdrawing a document raises the record's version, so an
approver always reviews the version they were shown.

Upload result and the resulting list
([18-attachment-uploaded.json](examples/18-attachment-uploaded.json),
[19-attachment-list.json](examples/19-attachment-list.json)):

```json
{ "id": 1, "name": "stationery-bill.png", "mime": "image/png", "size": 86,
  "sha256": "f69c4482025aedd6…", "uploaded_by__username": "finance.officer",
  "withdrawn_at": null }
```

Every view of a document is written to the audit log, because scans of bills and cheques
are sensitive.

## Cancelling a confirmed record

Confirmed records are never edited or deleted. Someone with `register.cancel` cancels them
with a reason of 1–1,000 characters. The record keeps its number, amount and history, is
excluded from reports from then on, and the reason is stored and shown
([22-entry-cancelled.json](examples/22-entry-cancelled.json)):

```json
{ "id": 10, "status": "cancelled", "amount": "24300.00", "date": "2026-09-08",
  "cancellation_reason": "Duplicate of REG-000005 (fuel, 9 August). Cancelled after checking the filling-station slip." }
```

If money really did move and the record was wrong, cancel it and prepare the correct one,
so the trail shows what happened.

## The worked example in full

| Reference | Date | Direction | Party | Category | Project | Account | Amount (PKR) |
|---|---|---|---|---|---|---|---|
| REG-000001 | 2026-07-04 | Receipt | Capital Builders (Pvt) Ltd | Client receipts | Fit-out | Cash | 400,000.00 |
| REG-000002 | 2026-07-06 | Payment | Al-Rehman Traders | Materials | Fit-out | Cash | 135,500.00 |
| REG-000003 | 2026-07-18 | Payment | Riaz Masood | Labour and wages | Fit-out | Cash | 86,000.00 |
| REG-000004 | 2026-08-02 | Receipt | Capital Builders (Pvt) Ltd | Client receipts | Wall | Bank | 650,000.00 |
| REG-000005 | 2026-08-09 | Payment | Attock filling station | Fuel and transport | Wall | Cash | 24,300.00 |
| REG-000006 | 2026-08-23 | Payment | Example Utilities | Office and administration | — | Bank | 38,750.00 |
| REG-000007 | 2026-09-05 | Payment | Riaz Masood | Labour and wages | Wall | Cash | 94,000.00 |
| REG-000008 | 2026-09-12 | Payment | Al-Rehman Traders | Materials (split 180,000 / 120,000) | Both | Bank | 300,000.00 |
| REG-000009 | 2026-09-19 | Payment | Blue Area Stationers | Office and administration | — | Cash | 12,400.00 |
| REG-000010 | 2026-09-08 | Payment | Attock filling station | Fuel and transport | Wall | Cash | 24,300.00 **cancelled** |
| REG-000011–13 | 2026-09-22/24/26 | Imported | See [chapter 7](07-spreadsheet-import.md) | | | | 410,200.00 total |
| REG-000014 | 2026-09-20 | Payment | Attock filling station | Fuel and transport | — | Cash | 18,600.00 **awaiting approval** |

Plus one opening balance and one internal transfer, in [chapter 6](06-openings-and-transfers.md).
