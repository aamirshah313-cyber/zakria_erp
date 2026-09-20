# 12. Audit log

Screen: **Audit logs** (permission `logs.view`; exporting needs `logs.export`).

The log answers "who did what, and when" for every action that changes data or reads
something sensitive. It is written by the service itself, not by the screens, so an action
cannot happen without its entry.

## Who may read it

Only a role holding `logs.view`. The **Administrator** role deliberately does **not** have
it: the person who configures the system is not the person who reviews the trail. First run
creates an **Audit Reviewer** role with `logs.view` and `logs.export` and nothing else.

Reading the log is itself recorded, as `audit.viewed`, and exporting it as
`audit.exported`.

## What a row contains

| Column | Example |
|---|---|
| Id | 87 |
| Time | 2026-09-20 14:55:51 UTC |
| Who | `audit.reviewer` |
| Action | `account.login` |
| Target | the record's id or number |
| Details | action-specific JSON: version, reason, file hash, row count, … |

From the example log ([40-audit-log.json](examples/40-audit-log.json)):

```json
{ "id": 87, "created_at": "2026-09-20 14:55:51+00:00", "actor__username": "audit.reviewer",
  "action": "account.login", "target": "4", "details": {} }
```

The screen shows the most recent 500 events, newest first.

## Actions recorded

The example run produced these, which is most of the register vocabulary:

| Group | Actions |
|---|---|
| Access | `account.registered`, `account.login`, `account.logout`, `user.access_changed`, `role.created`, `role.updated`, `setup.completed` |
| Passwords | `password.changed`, `password.recovery_codes_regenerated`, `password.reset_code_issued`, `password.recovered` |
| Register work | `register.draft_created`, `register.draft_updated`, `register.submit`, `register.confirm`, `register.return`, `register.cancel` |
| Openings and transfers | `register.position_created`, `register.position_submit`, `register.position_confirm`, `register.position_return`, `register.position_cancel` |
| Documents | `register.evidence_uploaded`, `register.evidence_withdrawn`, `register.evidence_read` |
| Setup | `register.master_created`, `register.master_updated`, `register.approval_rule_changed`, `register.master_imported`, `register.master_import_completed` |
| Spreadsheet import | `register.import_staged`, `register.import_reviewed`, `register.draft_imported`, `register.import_completed` |
| Reports | `register.report_exported`, `register.report_saved`, `register.report_archived`, `register.ledger_exported` |
| Data management | `register.data_remove`, `register.data_restore` |
| Backups | `system.backup_created`, `system.backup_downloaded`, `system.restored` |
| Company and documents | `company.updated`, `party.created`, `party.updated`, `document.created`, `document.updated`, `document.submit`, `document.approve`, `document.return`, `document.reject`, `document.issue`, `workflow.updated` |
| Audit | `audit.viewed`, `audit.exported` |

Details worth knowing:

- Cancellations and data-management actions store the **reason** the user typed.
- Import events store the **file hash**, sheet and row, so a figure can be traced back to
  the exact spreadsheet row it came from.
- Document events store the file's **SHA-256**, so a saved copy can be proved identical.
- Every **read** of a supporting document is recorded, because scans of bills and cheques
  are sensitive.

## Exporting

**Export CSV** downloads the same 500 rows with their details column, for filing or review
outside the application ([41-audit-log.csv](examples/41-audit-log.csv)).

## What the log is not

- It is not a version history: it records that a draft was updated, not the old and new
  values of each field.
- It does not survive a restore of an older backup — after a restore, the log is the one
  inside that backup, plus a `system.restored` entry describing the restore.
- It has no retention limit and no deletion route: entries stay in the database for as long
  as the database exists.
