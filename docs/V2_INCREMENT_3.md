# V2 increment 3 — spreadsheet import — 13 September 2026

The transaction register now includes a controlled Excel/CSV import workflow for the client’s journal and project ledger workbooks.

## Delivered

- Inspect an XLSX worksheet or UTF-8 CSV without writing register records.
- Select the worksheet and header row; retain the original source rows.
- Map dates, organization/person, amount or separate receipt/payment columns, direction, category, cash/bank source, project, method, reference, handled-by and remarks.
- Interpret Pakistani day/month dates, ISO dates, or explicitly selected month/day dates using calendar-safe date values.
- Select active categories, sources and projects, with explicit aliases for legacy names/codes.
- Enter independently verified receipt and payment control totals.
- Exclude summary, total or copied receipt-schedule rows with a reason.
- Flag same-batch and cross-file duplicate candidates. A reason is required before treating a possible match as a separate transaction.
- Reject formulas in mapped transaction cells, macro workbooks, unsupported XLS files, unsafe XML declarations, invalid amounts, invalid dates, inactive masters and ambiguous mappings.
- Recheck the preview against the latest database state at commit. Only after acknowledgement are register drafts created; no import directly confirms or posts ledger movement.
- Retain batch, workbook hash, worksheet and source-row origin on each imported draft. Repeat import of the same exact source row is blocked even if the previous entry was cancelled.

Limits are 5 MB per workbook, 1,000 non-empty rows per batch, 40 columns per worksheet and 20 worksheets per workbook. Embedded workbook images/objects are not imported; attach bank evidence to the resulting draft through Supporting documents.

## Acceptance steps

1. Grant `register.view`, `register.import` and `register.create` to the designated Finance role; retain `register.view` and `register.approve` for the separate approving role. Existing roles are not automatically granted the new import permission.
2. Open Transaction register → Import spreadsheet and select a copy of the client workbook. Keep the live workbook unchanged during testing.
3. Select the correct worksheet/header, map the columns, map category/source names, choose date interpretation and enter verified receipt/payment totals.
4. Review every duplicate and summary row. Exclude copied schedules or totals with a clear reason. For a real separate transaction, record why it is separate.
5. Validate and preview. Confirm row count and control totals. Acknowledge the source scope and create register drafts.
6. Review the generated drafts, attach supporting bank evidence where needed, then submit through the existing approval workflow.

Use the two client screenshots as examples only. Their sample values must not be imported as live company balances without client approval and a controlled import file.

## Verification and remaining work

The full Django suite passes 46 tests, including 10 import-specific checks. The existing 8 Flutter interface tests pass. The updated browser build is generated in `apps/client/build/v2-acceptance` and points to the V2 loopback service. The isolated V2 database migration 0005 was applied after an integrity-checked backup; the original pilot database remains unchanged.

Remaining V2 work: richer bank/account and structured party forms, opening positions, transfers and split allocations if required, configurable printable register reports and PDF/XLSX exports, packaged Windows launcher/installer, backup/restore and clean-machine testing. Full double-entry accounting and the broader modules remain deferred under V2_DESKTOP_SCOPE.md.
