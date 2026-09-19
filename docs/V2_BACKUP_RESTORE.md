# V2 backup and restore

Desktop installations only. Supporting documents are stored inside the database, so one database snapshot is a complete backup of records, documents, accounts, roles and passwords. The service secret is not needed to restore.

## Permissions

- `system.backup` — save backups, list and copy the automatic copies on this computer.
- `system.restore` — replace all data from a backup. Also requires the user's current password at the moment of restore.

New installations give both to Administrator. On existing data (for example the acceptance database) nobody has them until an authorized administrator grants them in **Roles & permissions**; the application then shows **Backup & restore** after refreshing permissions.

## Backup file

`*.zerp-backup` is a zip with `manifest.json` (format, app version, kind, creation time, database size and SHA-256) and the database. Sign-in sessions are removed from the copy.

Backups stream through files on disk in both directions (service and application), so size is limited by free disk space, not memory. The service checks free space on the data drive before writing a backup or staging a restore and reports how much is needed. Uploads for restore spool to `restore-staging` on the data drive; the local service accepts request bodies up to 64 GB.

Saving a backup, saving a copy and uploading a backup for restore show the amount transferred against the total, with **Cancel**. Cancelling a save deletes the partly written file. Cancelling during "Preparing the backup…" or "Checking the backup…" stops the application waiting; the service finishes that step and discards the result.

Files left by an interrupted backup or restore (for example when the application is closed during an upload) are removed when the service next starts: everything in `restore-staging`, and unfinished `*.snapshot` and `*.partial` files in `backups`. While the service runs, the same files are removed hourly once untouched for an hour; files still in use are skipped.

Manual backups can be password-protected: AES-256-GCM with a key derived by scrypt (N=2^15, r=8, p=1). Format 2 (from 2.1.0.9) encrypts in 4 MB chunks; each chunk's number and a final-chunk flag are authenticated, so truncated, reordered or shortened files are rejected, and the whole database is also checked against its SHA-256. Format 1 backups made by 2.1.0.5–2.1.0.8 (one encrypted block) remain restorable. The password must be at least 10 characters and is never stored, logged or recoverable. A forgotten password makes that backup unusable. Automatic and safety copies are not encrypted; they stay inside `C:\ProgramData\ZakariaERP\backups`, which only accounts on this computer can reach.

## Automatic copies

In `C:\ProgramData\ZakariaERP\backups`:

| Name | When | Kept |
|---|---|---|
| `auto-…` | First check each day (startup, then hourly), after the first account exists | Newest 7 |
| `pre-restore-…` | Immediately before every restore | Until removed manually |
| `before-upgrade-…` | Before a new version changes the database schema | Until removed manually |

Automatic copies protect against mistakes, not disk failure or theft of the computer. Save manual backups to a USB drive or another computer regularly.

## Restore

1. **Backup & restore → Choose backup file…**, or **Restore** beside a copy on this computer.
2. Enter the backup password if the file is protected.
3. Review the preview: backup date and version, company, accounts, register entries with the latest date, supporting documents, and whether an upgrade will follow.
4. Enter your current password and choose **Replace all data**.

The service validates the zip, checksum, decryption, SQLite integrity and that the backup is not from a newer version, then saves a `pre-restore` copy, replaces the database, applies any schema upgrades, ends every session and records `system.restored` in the restored audit log. Accounts and passwords become those in the backup. A preview expires after 30 minutes and belongs to the user who created it. To undo, restore the `pre-restore` copy.

## New computer or reinstall

On a new installation, the first-run screen offers **Restore from a backup instead** next to administrator setup. It is available only while no account is active, and needs no sign-in. This is also the supported way to move the existing `storage/v2-desktop` acceptance data into an installed copy: save a backup from the acceptance package (after granting `system.backup`), then restore it on the installed application's first-run screen.

## Limits

- Backup size is limited by free disk space (roughly twice the database size is needed while writing or restoring). Format 1 encrypted backups are still decrypted in one piece; they were created in memory and are small.
- One restore at a time. Other users are signed out and must sign in again with backup accounts.
- No scheduled copying to external drives or cloud storage.
