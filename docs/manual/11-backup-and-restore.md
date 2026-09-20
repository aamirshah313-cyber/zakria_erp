# 11. Backup and restore

Screen: **Backup & restore**. Saving needs `system.backup`; replacing data needs
`system.restore` and your own password at the moment of the restore.

Supporting documents live inside the database, so one backup file is a complete copy of
records, documents, accounts, roles and passwords. The service's own secret is not included
and is not needed to restore.

The operational detail — folder names, encryption parameters, upload spooling, clean-up of
interrupted work — is in [../V2_BACKUP_RESTORE.md](../V2_BACKUP_RESTORE.md). This chapter
is the working procedure.

## Save a backup

**Save backup…** optionally takes a password (10 characters or more, typed twice), then
asks where to put the file. Save it to a USB drive or another computer, not only to this
one.

While it runs, the dialog shows *Preparing the backup…*, then the amount saved against the
total, with **Cancel**. Cancelling deletes the partly written file.

A backup is a `.zerp-backup` zip holding the database and a manifest
([43-backup-manifest.json](examples/43-backup-manifest.json)):

```json
{ "format": "zakaria-erp-backup", "format_version": 2, "app_version": "2.1.0",
  "kind": "manual", "created_at": "2026-09-20T19:55:51+05:00", "size": 569344,
  "encrypted": false,
  "sha256": "4a6cb4903795a418977111b81a1c24ed5bb1c2ca2fb11bd6deb684c8b3f8d1f8" }
```

A complete backup of the example data is included as
[42-backup-example.zerp-backup](examples/42-backup-example.zerp-backup) (31 KB). It can be
restored into a scratch installation to reproduce every figure in this manual.

### Passwords

- A password protects the file with AES-256-GCM; without it the file is readable by anyone
  who gets the drive.
- The password is never stored, logged or recoverable. **A forgotten password makes that
  backup unusable.** Keep it where the business keeps its other secrets.
- Files made by versions 2.1.0.5 to 2.1.0.8 use the older single-block format and still
  restore.

## Copies on this computer

`C:\ProgramData\ZakariaERP\backups` holds copies the application makes by itself:

| Name | When | Kept |
|---|---|---|
| `auto-…` | First check each day, then hourly while the application is open | Newest 7 |
| `pre-restore-…` | Immediately before every restore | Until deleted by hand |
| `before-upgrade-…` | Before a new version changes the database structure | Until deleted by hand |

The screen lists them with date, type and size ([44-backups-list.json](examples/44-backups-list.json)
— empty in the example, because it was generated on a fresh database), and offers **Save
copy…** to put one on a drive and **Restore** to use it.

These copies are not encrypted and sit on the same disk as the data. They protect against
mistakes, not against a failed disk, fire or theft. Save a manual backup off the computer
regularly.

## Restore

1. **Choose backup file…**, or **Restore** beside a copy on this computer.
2. Enter the backup password if the file has one. A file chosen from disk is uploaded once:
   the service keeps it while it asks for the password, including after a wrong attempt.
3. Read the preview: backup date and version, company, accounts, register entries with the
   latest date, supporting documents, and whether a database upgrade will follow.
4. Type your own current password and choose **Replace all data**.

The service checks the zip, the checksum, the decryption, the database's own integrity, and
that the backup is not from a newer version. It then saves a `pre-restore` copy, replaces
the database, applies any structure upgrades, signs everyone out and records
`system.restored` in the restored audit log.

While the data is being replaced the application shows a dialog saying a safety copy is
being saved first and that it must stay open. That step cannot be cancelled once it starts.

After a restore, **accounts and passwords are the ones in the backup**. Sign in with an
account that existed when the backup was made. To undo a restore, restore the `pre-restore`
copy it saved.

A preview expires after 30 minutes, belongs to the person who created it, and only one
restore runs at a time.

## Moving to another computer, or reinstalling

1. On the old computer: **Save backup…**, with a password, to a USB drive.
2. Install the application on the new computer and start it.
3. On the first-run screen choose **Restore from a backup instead** — this is available
   only while the installation has no account, and needs no sign-in.
4. Enter the password, check the preview, restore, then sign in with the old accounts.

The same route moves the development acceptance data (`storage\v2-desktop`) into an
installed copy.

## A working routine

| When | Do |
|---|---|
| Every day | Nothing — the application keeps its own daily copy |
| Every week | **Save backup…** with a password to a USB drive kept away from the computer |
| Before an upgrade | One manual backup, in addition to the automatic `before-upgrade` copy |
| Before a restore | Note which `pre-restore` copy is created, in case the restore is wrong |
| Every few months | Restore a backup into a scratch installation and check it opens |

## Limits

- Backup size is limited by free disk space, not memory; the service checks space first and
  says how much is needed.
- One restore at a time; everyone else is signed out and must sign in again.
- No scheduled copying to an external drive or to cloud storage: saving off the computer is
  a manual step.
