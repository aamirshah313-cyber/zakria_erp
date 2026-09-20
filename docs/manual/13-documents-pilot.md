# 13. Quotations and invoices (pilot module)

These screens come from the earlier pilot (V1) and are still in the code: **Quotations**,
**Invoices**, **Approvals**, **Customers & suppliers**, **Approval rules**, **Company
settings**, **Reports** and **Accounting setup**. They appear when the matching permissions
are held; the desktop register build hides **Accounting setup**.

Nothing here writes to the transaction register, and the register does not write here. A
document is a piece of paper for a customer; a register entry is money that moved.

## Customers & suppliers

The party list shared with the register ([chapter 4](04-register-setup.md)). `parties.view`
to see it, `parties.edit` to add or change. A document can only be addressed to a party
whose classification is **customer** or **both**, and which is active.

## Quotations and invoices

Both use one form and one workflow; only the number prefix and the permissions differ.

| Field | Notes |
|---|---|
| Customer | Active customer party |
| Issue date | Required |
| Due / valid until | Optional; cannot precede the issue date |
| Reference | Optional, e.g. the customer's enquiry number |
| Tax treatment | *Unspecified*, *Tax exclusive*, *Exempt* or *Zero rated* — must be decided before submission |
| Notes | Free text printed on the document |
| Lines | 1 to 200 lines: description, unit, quantity, rate, tax rate |

Each line's amount is quantity × rate, rounded to two decimals, and its tax is that amount
× tax rate. A tax rate is only allowed when the treatment is tax exclusive. Totals are
computed by the service, never sent by the screen: subtotal, tax and total.

Numbers are allocated on creation as `QUO-2026-000012` or `INV-2026-000013`.

### Workflow

```
draft ──submit──▶ submitted ──approve──▶ approved ──issue──▶ issued
  ▲                    │                                        
  └── return/reject ───┘
```

- **Submit** — the preparer only, on a draft or a returned document, with an explicit tax
  treatment. The approval rule in force is copied onto the document at that moment, so
  later changes to the rule do not move documents already in review.
- **Approve / Return / Reject** — only the role named in that snapshot. Returning or
  rejecting needs a comment, which the preparer sees as feedback. Self-approval is refused
  unless the rule allows it.
- **Issue** — needs `quotation.issue` / `invoice.issue`, an approved document, and a
  completed company address. Issuing stores a snapshot of the company and customer details
  as they were, so a reprint years later shows what was sent.
- **Live invoice issuance is blocked**: the service refuses it with "Live invoice issuance
  is not enabled in this pilot. Accounting and tax readiness must be completed first."
  Quotations issue normally.

Every action is version-checked and written to the audit log.

### Printing

**PDF** renders the document with the company header, logo, customer details, lines, totals
and notes, from the issued snapshot where there is one.

## Approvals

One screen listing documents waiting for the signed-in person's role, with the same
Approve, Return and Reject actions.

## Approval rules

Per document type (`workflows.manage`): which role approves, and whether the preparer may
approve their own document (off by default). The chosen role must hold the matching
approval permission, and a role cannot lose that permission while a rule points at it.
Each change raises the rule's version, which is what gets snapshotted onto documents.

## Company settings

`company.manage`. Name, address, city, phone, email, NTN, STRN, FTN, bank details, footer
text and the accent colour. These appear on document PDFs and on register report headers
([07-company.json](examples/07-company.json)).

## Reports (documents)

A separate builder for quotations and invoices: date range, status filter, columns
(document number, customer, issue date, due date, status, reference, subtotal, tax, total,
prepared by) and grouping by status, customer or month, with CSV and PDF export. Limited to
5,000 documents per report. Register statements are a different screen
([chapter 8](08-reports.md)).

## Accounting setup (foundation only)

Visible in the pilot deployment to `finance.view`, `finance.manage` or `roles.manage`.
It holds master data for a future double-entry ledger:

- **Chart of accounts** — code, name, classification (asset, liability, equity, income,
  expense), group or individual account, cash/bank flag, parent. A **starter chart** can be
  created once, on an empty chart: five groups and about thirty accounts.
- **Projects** — the same records the register uses.
- **Financial years** — name, start and end date; years cannot overlap, and a year
  containing vouchers cannot be redated.

Rules already enforced: a parent must be an active group of the same classification, no
cycles, cash accounts must be individual asset accounts, and an account that has been used
cannot be reclassified or renumbered.

**No posting exists.** There are no vouchers, no ledgers, no trial balance and no financial
statements. Everything the business reports today comes from the register. The remaining
accounting work is listed in [../V2_DESKTOP_SCOPE.md](../V2_DESKTOP_SCOPE.md) and
[../ADDITIONAL_FINANCE_SCOPE.md](../ADDITIONAL_FINANCE_SCOPE.md).
