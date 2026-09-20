# 10. Data management

Screen: **Delete / restore** (permission `register.delete`), reached from the shortcut bar
at the top of the workspace or from the Transaction register.

Nothing here erases a record. "Remove" moves a draft out of the working lists, and
"Restore" brings it back; setup records are archived and reactivated the same way.
Confirmed financial history cannot be touched from this screen at all — it is cancelled,
with a reason, from the register itself.

## What can be managed

| Record type | Removable when | Comes back as |
|---|---|---|
| Receipt / payment drafts | Status is **draft** | draft |
| Opening / transfer drafts | Status is **draft** | draft |
| Uncommitted spreadsheet batches | Status is **staged** or **reviewed** | staged — it must be previewed again |
| Quotation drafts, Invoice drafts | Status is **draft** | draft |
| Categories | Always (archive) | active |
| Cash / bank accounts | Always (archive) | active |
| Projects / contracts | Always (archive) | active |
| Parties | Always (archive) | active |
| Personal report layouts | Always (archive); only your own | active |

Submitted records are not removable: return them to the preparer first. Confirmed records
are not removable: cancel them with `register.cancel`.

## The list

Choose the record type; the screen shows 50 rows per page with the label, status, date,
amount, supporting-document count and the actions allowed on that row. A **Removed** switch
lists what was taken out, so it can be restored
(38-data-management.json):

```json
{ "id": 15, "label": "Typing error", "status": "draft", "revision": "1",
  "date": "2026-09-28", "amount": "100.00", "actions": ["remove"], "documents": 0 }
```

Rows that may not be changed come back with an empty `actions` list, so the buttons are not
offered in the first place.

## Removing or restoring

Every action needs a **reason of 1–1,000 characters**. The reason, the state before, the
state after and the revision are written to the audit log, so the trail explains why a
draft disappeared from someone's work list
(39-draft-removed.json).

```json
{ "message": "Record removed from active work lists; retained for recovery.",
  "status": "deleted" }
```

Each row carries a revision. If the record changed after the list was drawn — someone
edited the draft, or attached a document — the action is refused with "This record changed.
Refresh and review it again."

## Archiving setup records

Archiving a category, account, project or party takes it out of the choices on new records
but leaves it on every record that already used it, so old statements keep their labels.
The register-setup rules still apply: a category with active children cannot be archived,
and a cash/bank account keeps its identifiers.

## Recovering data another way

This screen recovers single records. To recover from a larger mistake — a bad import that
was confirmed, or data lost on a broken computer — restore a backup
([chapter 11](chapter:11-backup-and-restore)). A restore replaces everything, so it is the last
resort rather than the first.
