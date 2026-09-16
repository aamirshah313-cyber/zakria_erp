# V2 Windows installer

`installer/ZakariaERP.iss` (Inno Setup 6) produces `artifacts/installer/ZakariaERP-Setup-<version>.exe`, a general-purpose installer for a computer shared by several Windows accounts.

## Build

```powershell
.\scripts\package-v2-windows.ps1       # bundled backend + native client package
.\scripts\build-v2-installer.ps1       # stages the newest package and compiles setup
```

Requires Inno Setup 6 (`winget install JRSoftware.InnoSetup`). The build script refuses incomplete packages and any staged database, service secret or `.env` file. It excludes the developer `data-directory.txt`, so installed copies use shared data instead of `storage/v2-desktop`.

## What the installer does

- Installs for all users under `C:\Program Files\Zakaria ERP` (administrator approval once) with a Start menu shortcut and optional desktop shortcut.
- Creates `C:\ProgramData\ZakariaERP` with modify permission for local Users, so every Windows account on the computer shares one register. The launcher allows the application to run in only one Windows session at a time.
- Upgrades in place: asks to close a running copy, removes the previous bundled runtime, and never touches the data folder.
- Uninstall removes program files only and states where the kept data is.

## First run and upgrades

The launcher starts the bundled service with the data folder. On an empty folder the service creates `evidence`, `backups`, `logs`, a private service secret and a new database. The application then shows **Set up this computer** to create the first Administrator; staff register afterwards and the Administrator approves them. Setup is available only in desktop mode and closes permanently once any account is active. Default roles match the approved register workflow: Finance Manager prepares/imports/exports, General Manager approves/exports and is the register approver. Cancellation, bank identifiers and audit access remain unassigned until the Administrator grants them.

When a newer version needs database changes, the service saves `backups\before-upgrade-<timestamp>.zerp-backup` (restorable from Backup & restore), verifies the copy's integrity, and only then applies the changes. Startup problems are written to `logs\service.log`, and the launcher shows that path.

## Limits and remaining work

- Unsigned: Windows SmartScreen warns until the setup and application are code-signed with the company's certificate.
- The existing acceptance data in `storage/v2-desktop` is not moved automatically. Save a backup from the acceptance package and restore it on the installed application's first-run screen; see V2_BACKUP_RESTORE.md.
- Automatic update delivery and clean-computer acceptance (no Python/Flutter installed) remain outstanding.
- One Windows session at a time; simultaneous use from several computers is out of V2 scope.
