# 6. Openings and internal transfers

Screen: **Transaction register → Openings / Transfers** ("Opening balances & internal
transfers"). Both kinds of record go through the same prepare-and-review workflow as
receipts and payments, and neither is an income or an expense.

List with document counts: 21-positions-list.json.

## Opening balances

An opening balance says: *history starts here, and this is what was already in hand.*
Use it when the business starts using the application part-way through, instead of typing
years of old vouchers.

**New opening balance** asks for:

| Field | Notes |
|---|---|
| **Opening scope** | Exactly one of: a cash/bank account, a category, a project, or a party |
| **Opening effective date (start of day)** | The cut-off: the figure is true at the start of this day |
| **Amount (PKR)** | Greater than zero |
| **Opening side** | *Receipts exceed payments / positive cash balance*, or *Payments exceed receipts / negative cash balance* |
| **Supporting record / statement reference** | Where the figure comes from — a counted cash sheet, a bank statement |
| **Explanation and evidence location** | How it was established and who checked it |

The same record as prepared is 11-opening-draft.json; after
review it reads (12-opening-confirmed.json):

```json
{ "id": 1, "kind": "opening", "date": "2026-07-01", "amount": "350000.00", "side": "receipt",
  "source": 1, "reference": "Counted cash at 1 July 2026", "status": "confirmed",
  "approved_by": 3 }
```

### The rules that keep openings honest

- **Exactly one scope.** An opening names one account, category, project or party — never
  a combination — so two openings can never be added together into a meaningless total.
- **One confirmed opening per scope.** A second one for the same account is refused.
- **No earlier history.** If confirmed movements (or transfers, for an account) already
  exist before the opening date, the opening is refused: use the real history instead of a
  duplicate starting figure.
- **Nothing before the cut-off.** Once an opening is confirmed, any receipt, payment or
  transfer dated before it is refused, at typing and again at confirmation
  (45-refused-requests.json, third entry):

  > This date precedes a reviewed opening balance. Import movements from the opening date
  > onward; do not duplicate earlier history.

- **Openings apply to one scope at a time in reports.** A statement filtered to that one
  account, category, project or party (with no other filters) starts from the opening; a
  wider report starts from zero and says so in its basis note. Chapter 8 shows both.

## Internal transfers

An internal transfer moves the company's own money between its own accounts — cash banked,
or a bank withdrawal for the site. It is not a receipt and not a payment: total receipts
and payments do not change, only the two account balances.

**New internal transfer** asks for:

| Field | Notes |
|---|---|
| **Transfer date** | The day the money moved |
| **From own account** | Any active cash/bank account |
| **To own account** | A different active account |
| **Amount (PKR)** | Greater than zero |
| **Supporting record / statement reference** | Deposit slip, transfer reference |
| **Explanation** | Why the money was moved |

A transfer never carries a category, project or party: *"Own-account transfers do not
allocate external expense or project activity."* Both accounts are checked against opening
cut-offs.

Confirmed example (20-transfer-confirmed.json):

```json
{ "id": 2, "kind": "transfer", "date": "2026-09-15", "amount": "150000.00",
  "source": 1, "destination": 2, "reference": "DEP-9912", "status": "confirmed" }
```

### How transfers appear in reports

| Report scope | What is shown |
|---|---|
| No account filter | One row, reference `TRF-000002`, party "Own-account transfer", with 150,000 in both *Transfers in* and *Transfers out* |
| Filtered to the cash box | One leg only: transfers out 150,000, reducing that account's closing balance |
| Filtered to the bank account | The other leg: transfers in 150,000 |
| Any report filtered by category, project, party, direction or method | Transfers are left out entirely, because they are not external activity |

In the worked example, the cash box closes at 112,600 —
350,000 opening + 400,000 receipts − 487,400 payments − 150,000 transferred out
(37a-report-cash-account.json) — while the
company-wide report still shows receipts of 1,325,000 and payments of 826,150, with
transfers listed separately.

## Supporting documents and review

Openings and transfers take the same supporting documents as receipts and payments: up to
ten PNG, JPEG or PDF files of 5 MB each, on the preparer's own draft, withdrawable with a
reason. The list screen shows the count per record.

The workflow is identical: **Submit for approval**, then **Confirm** or **Return to
preparer** by the approval role, and **Cancel with reason** afterwards. A preparer cannot
confirm their own record.

## Reference numbers

| Prefix | Record |
|---|---|
| `REG-000001` | Receipt or payment |
| `OP-000001` | Confirmed opening balance, quoted in report basis notes |
| `TRF-000002` | Internal transfer |
