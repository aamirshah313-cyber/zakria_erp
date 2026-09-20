# 4. Register setup

Screen: **Register setup** (permission `register.manage`). Four tabs — **Categories**,
**Cash & bank accounts**, **Projects & contracts**, **Parties** — plus the approval role
and two import buttons. Everything an entry form offers comes from here
(10-register-setup.json).

Setup records are never deleted. They are archived and restored through
[Data management](chapter:10-data-management), so past records keep the name they were recorded
against.

## Categories

What the money was for. Categories can be nested one inside another.

| Field | Rules |
|---|---|
| Code | Unique, up to 30 characters, e.g. `MAT` |
| Name | Up to 160 characters |
| Description | Optional, up to 500 characters |
| Parent category | Optional; must be active; a loop is refused |
| Active | Archived categories stay on old records but cannot be chosen for new ones |

A category cannot be archived while it still has active children.

Example (08-category.json):

```json
{ "id": 2, "code": "MAT", "name": "Materials", "active": true,
  "description": "Cement, steel, sanitary and electrical purchases", "parent": null }
```

The worked example uses five: `CLIENT` Client receipts, `MAT` Materials, `LAB` Labour and
wages, `FUEL` Fuel and transport, `OFF` Office and administration.

## Cash & bank accounts

The company's own money containers. Every entry names exactly one.

| Field | Rules |
|---|---|
| Name | Unique, up to 160 characters |
| Type | **Cash** or **Bank**; cannot change once the account has been used |
| Account title, Bank, Branch, Account number, IBAN | Bank accounts only; all five need `register.bank_details` to see or set |
| Active | Archived accounts stay on old records |

Rules that protect identifiers:

- A cash account must leave all five bank fields empty.
- An IBAN is checked for format and checksum, and a Pakistani IBAN must be 24 characters.
  Leave it empty until it is verified rather than storing a guess.
- Once an account has activity, its account number and IBAN cannot be replaced — create a
  new account instead, so old records still point at the account they really used.
- Without `register.bank_details`, the five sensitive fields are stripped from every
  response; the account is still usable and still shows its name and type.

Example, read by a user who has the permission
(09-bank-source.json):

```json
{ "id": 2, "name": "Bank current account", "kind": "bank", "active": true,
  "account_title": "Muhammad Zakaria and Sons", "bank": "Example Bank Limited",
  "branch": "Blue Area, Islamabad", "account_number": "0123456789",
  "iban": "PK36SCBL0000001123456702" }
```

## Projects & contracts

Optional grouping for work the business does for a client.

| Field | Rules |
|---|---|
| Code | Unique, up to 30 characters, e.g. `PRJ-001` |
| Name | Up to 160 characters |
| Contract reference | Optional, e.g. the client's purchase-order number |
| Client | Optional link to an active party |
| Location, Contact name, Email | Optional; printed on the project statement header |
| Start date, End date | Optional; the end cannot precede the start |
| Active | Archived projects stay on old records |

The example has `PRJ-001` G-11 Markaz office fit-out (reference PO-2026-114) and `PRJ-002`
Boundary wall — Phase II (PO-2026-128).

## Parties

Organizations and people the business deals with.

| Field | Rules |
|---|---|
| Name | Up to 180 characters |
| Party classification | Customer, Supplier, Both, Contractor, Employee or Other |
| Type | Organization or Person |
| Phone, Email, Address | Optional |
| NTN, STRN, FTN | Optional tax identifiers |
| Active | Archived parties stay on old records |

Choosing a party on an entry copies its name into the record's own **Organization /
person** text. Renaming the party later does not rewrite entries already recorded: the
record keeps the name that was used at the time, while the link still points at the master.

## Approval role

One setting, shown as **Approval role — self-approval is disabled**: the role whose members
confirm submitted register records. The chosen role must hold `register.approve`. Changing
it affects **new submissions only**; records already submitted keep the role they were sent
to. First run sets it to General Manager.

## Import setup records

**Import setup records** loads many categories, cash/bank accounts, projects or parties
from one spreadsheet. It needs both `register.manage` and `register.import`.

- Column headings must match the field names for that record type exactly; unknown columns
  are refused rather than ignored.
- Existing names or codes are never overwritten — a clash is reported as an error row.
- Parent categories and client parties are matched by name or code and must already exist,
  so import parents first.
- The preview lists every row with its errors. Only a clean preview can be committed, and
  the commit is bound to that exact file and selection by a token that expires in 30
  minutes.
- Up to 1,000 records per file; up to 5 MB; XLSX or UTF-8 CSV; formulas are refused.

**Download testing workbook** provides the prepared workbook (`V2-Testing-and-Import.xlsx`)
with the correct headings for each record type.

## What good setup looks like

- Few enough categories that a reviewer can recognise them, enough that reports answer
  real questions. Five to fifteen is usual.
- One cash account per physical cash box, one bank account per real bank account.
- Projects for work that must be reported separately; leave it empty for general overheads.
- Parties for anyone recurring; casual one-off names can stay as free text in the entry.
