# 2. Getting started

## Installing on Windows

Run `ZakariaERP-Setup-2.1.0.11.exe` from the release page and accept the administrator
prompt. The installer:

- installs the application and the bundled service for **all Windows accounts**;
- creates the shared data folder `C:\ProgramData\ZakariaERP` if it does not exist;
- keeps existing data when upgrading, and saves a `before-upgrade-…` backup first if the
  new version changes the database structure;
- adds Start-menu and optional desktop shortcuts.

Windows SmartScreen warns that the publisher is unknown because the build is not yet
code-signed. Choose **More info → Run anyway**. Full details, including the silent-install
switches and the uninstall behaviour, are in ../V2_INSTALLER.md.

When the application starts, a small **Starting Zakaria ERP…** window appears if the
service needs more than about a second (first run, or a database upgrade). It closes by
itself when the main window is ready. Closing the application stops `zakaria_service.exe`.

## First run: creating the first administrator

A new installation has no accounts and no default password. The first screen offers two
routes.

**Set up this installation** creates the first administrator. The form asks for username,
full name, email, password and password confirmation. The password must pass the standard
strength checks; a weak or repeated password is refused with the reason.

Response (03-first-run-setup.json):

```json
{ "message": "Administrator created. Sign in to continue setup.", "username": "zakaria.admin" }
```

Creating that account also creates, once:

- the five default roles (chapter 3);
- the company record;
- the approval rules for quotations and invoices;
- the register approval rule, set to General Manager.

The setup screen closes permanently as soon as one active account exists
(02-first-run-required.json shows the check that
drives it). After that, new people are added by an administrator.

**Restore from a backup instead** replaces the empty installation with the contents of a
`.zerp-backup` file, before any account exists. This is how an existing database is moved
to a new computer; see [chapter 11](chapter:11-backup-and-restore).

## Signing in

The sign-in screen asks for username and password. On success the service issues a session
token valid for **8 hours**; the application keeps it in memory only, so closing the
application signs you out. Accounts that are pending or suspended, or have no role, are
refused with "Your account is pending approval or suspended."

The screen also offers:

- **Forgot password?** — reset with a recovery code (below).
- **Connection settings** — on Android only, the address of the server to use.
- **Restore from a backup instead** — only while the installation has no account.

## Forgotten passwords

There is no email in the system, so recovery uses codes.

| Situation | What to do |
|---|---|
| You have your own recovery codes | Sign-in screen → **Forgot password?** → username, one code, new password. |
| You have no codes | Ask an administrator (permission `users.reset`) to issue a one-time code, which expires after **30 minutes**. |
| Every administrator is locked out | Nothing in the application can help. Restore a backup to a state whose password is known. An emergency owner procedure is still an open item. |

Codes are shown once and stored only as hashes. A successful reset cancels every remaining
code for that person and signs their sessions out. Both routes are rate-limited to 10
attempts per 15 minutes per computer, and every issue and use is written to the audit log.

To create your own codes: **My profile → Recovery codes**, confirming with your current
password. Five codes are issued and never expire until used or replaced.

## Changing your own details

**My profile** shows your username, role and permissions, and lets you edit first name,
last name, phone and email, and change your password. Changing your password signs out
every session, including other devices, and (on the desktop) clears your recovery codes.

## The phone application

`ZakariaERP-2.1.0+11-debug.apk` installs on Android for testing. The launcher icon,
sign-in screen and **Connection settings** all work, and the address entered there is
remembered on the device.

It cannot sign in yet: the desktop service listens only on the computer's own loopback
address, so nothing on the network can reach it. Making phones work needs a decision —
either a deliberate Wi-Fi server mode on the office computer, or a hosted HTTPS server —
and the matching security work. Until then the APK is a build and branding check only.

## Help inside the application

**Help & manual** in the sidebar opens this manual inside the application. Every signed-in
person can see it, whatever their role. It carries the chapters for the installed build, so
it stays correct even when the computer has no internet, and the search box finds the
chapters that mention a word — "control total", "opening balance", "recovery code".

Links between chapters work there. Links to the example files do not: those are published
with the source, not installed with the application.

## Where the data is

| Item | Location |
|---|---|
| Database (all records and documents) | `C:\ProgramData\ZakariaERP\register.sqlite3` |
| Automatic and safety backups | `C:\ProgramData\ZakariaERP\backups` |
| Service log | `C:\ProgramData\ZakariaERP\logs\service.log` |
| Application | `C:\Program Files\Zakaria ERP` |

The portable development package keeps the same layout under `storage\v2-desktop` and is
for the build computer only.
