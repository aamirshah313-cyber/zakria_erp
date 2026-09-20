# 9. Dashboard

Screen: **Overview**, the first screen after signing in. It answers two questions: what has
the business received and paid, and what is waiting for me.

Everything on it is built from the same confirmed records as the reports, so the figures
match. Live example, as the reviewer sees it
(27-dashboard.json).

## Register summary

Three totals across all confirmed records, with no date limit:

| Tile | Example (PKR) | Meaning |
|---|---|---|
| Receipts | 1,325,000.00 | Every confirmed receipt |
| Payments | 826,150.00 | Every confirmed payment |
| Net movement | 498,850.00 | Receipts less payments — not profit |

Internal transfers are left out of all three: moving money between the company's own
accounts changes neither figure.

## Waiting for approval

Shown only to someone who holds `register.approve`, and listing only submissions sent to
their role by **somebody else**. Up to 20 rows, oldest date first, with the count above:

```json
{ "pending_count": 1,
  "pending": [ { "id": 14, "date": "2026-09-20", "direction": "payment",
                 "party": "Attock filling station", "amount": "18600.00",
                 "version": 2, "owner__username": "finance.officer" } ] }
```

A preparer sees their own submissions as zero here, because they cannot review them. Open
the record from the Transaction register to **Confirm entry** or **Return to preparer**.

## Last six months

A bar per month for the six months ending with the current month, receipts against
payments:

| Month | Receipts (PKR) | Payments (PKR) |
|---|---|---|
| Apr 2026 | 0 | 0 |
| May 2026 | 0 | 0 |
| Jun 2026 | 0 | 0 |
| Jul 2026 | 400,000 | 221,500 |
| Aug 2026 | 650,000 | 63,050 |
| Sep 2026 | 0 | 406,400 |

The chart covers dates up to **today**, so records dated later than today — the example was
generated on 20 September, and three imported receipts are dated 22 to 26 September — are
counted in the totals above but not yet in the chart. Use a report with an explicit period
when the exact month matters.

## Where payments went

The five largest payment categories, with everything else collapsed into "Other
categories":

| Category | Payments (PKR) |
|---|---|
| Materials | 499,700 |
| Labour and wages | 251,000 |
| Office and administration | 51,150 |
| Fuel and transport | 24,300 |

Split payments are counted by their allocation, so the 300,000 supplier bill contributes
its 180,000 and 120,000 to Materials rather than appearing under the header category alone.

## Document tiles (pilot module)

When quotation or invoice permissions are held, the same screen adds counts of quotations
and invoices, documents awaiting the viewer's approval, their own submitted documents, and
the eight most recently changed documents. In the desktop register build these are
normally empty; see [chapter 13](chapter:13-documents-pilot).

## Refreshing

The header **Refresh** button reloads the dashboard *and* the signed-in person's
permissions, so screens appear or disappear after an administrator changes a role without
signing out and in again.
