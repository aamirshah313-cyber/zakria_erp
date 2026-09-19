# Implementation status — 19 September 2026

## Current release

| Item | Location | State |
|---|---|---|
| Windows installer | artifacts/installer/ZakariaERP-Setup-2.1.0.8.exe (41,686,687 bytes) | Built; startup window checked on a scratch copy; not yet installed over the existing installation |
| Windows app folder | artifacts/windows-v2/ZakariaERP-V2-20260919-212353/ (+ .zip) | Built; runs against storage/v2-desktop test data |
| Android APK (debug) | artifacts/android/ZakariaERP-2.1.0+8-debug.apk | Built and package-checked; cannot sign in until a reachable server exists |
| Downloads | https://github.com/aamirshah313-cyber/zakria_erp/releases/tag/v2.1.0.8 (private) | Installer, portable ZIP and APK uploaded; tag v2.1.0.8 = 80f1b77 |

Tests at this release: 87 backend tests and all 24 Flutter tests pass. Artifacts are not in git. Do not distribute ZakariaERP-Setup-2.1.0.6.exe or earlier: 2.1.0.6 carries the rejected first logo redraw, and 2.1.0 / 2.1.0.5 predate the logo.

## Next tasks

Current priority order. Sections below record what is already delivered; the older "Next development order" further down is historical pilot planning.

### 1. Verify the latest release on this computer (user and developer)
- Upgrade the installed application with artifacts/installer/ZakariaERP-Setup-2.1.0.8.exe; confirm the upgrade keeps C:\ProgramData\ZakariaERP data and accounts (migration 0010 runs after an automatic backup) and that the Starting window appears while it upgrades.
- Check the MZS logo in the installer wizard, the Start menu/taskbar icon, the sign-in screen, the workspace sidebar, and a PDF, Excel and PNG report header.
- Grant system.backup and system.restore to Administrator in Roles & permissions (installations from the 2.1.0 setup lack them), then Refresh.
- Exercise backup and restore in the installed (frozen) service: password-protected backup to USB, small change, restore, confirm the change is undone and a pre-restore copy exists.
- Close the application and confirm zakaria_service.exe stops with it.
- Attach a statement to a draft opening and a draft transfer (record menu: Supporting documents), submit them, and confirm the documents lock and remain viewable to the reviewer.
- Install the debug APK on a test phone: check the launcher icon, sign-in logo and that Connection settings opens (sign-in waits for task 7).

### 2. Move acceptance data into the installed application
- Decide whether storage/v2-desktop test data should be kept. If yes: grant system.backup in the acceptance package, save a backup, and restore it through Backup & restore in the installed copy (the installed copy is already set up, so the first-run restore route no longer applies).

### 3. Client acceptance of V2.1 (user)
- Activate an independent General Manager account; assign cancellation, import and bank-identifier permissions deliberately.
- Work through V2_INCREMENT_5.md with the testing workbook: setup-record imports, transaction import, approval, reports, PDF/XLSX export, draft removal/restore.
- Record usability issues found during acceptance as the next development input.

### 4. Release hardening (developer)
- Clean-computer test: install, first-run setup, restore from backup, upgrade and uninstall on a Windows PC without Python or Flutter.
- Two Windows accounts: confirm shared data and the one-session-at-a-time message.
- Remove superseded local artifacts (installers 2.1.0 to 2.1.0.7 and older package folders) after the 2.1.0.8 upgrade is confirmed, keeping one previous release for rollback.
- This computer became very slow after its restart on 19 September (Windows build ~20 minutes instead of 1–2, application window ~30 s after launch instead of ~10 s). Check Windows Update and antivirus activity before timing startup again or judging performance on client hardware.
- Flutter plugin links need Developer Mode or one elevated `flutter pub get` whenever the Flutter plugin list changes (or the links folder is cleared by a failed build). Decide whether to enable Developer Mode on this build computer.
- Build and publish 2.1.0.9 with streamed backups and document counts, following docs/RELEASING.md.

### 5. Branding decisions (user)
- Approve the rebuilt logo (branding/mzs-logo.png) against the original branding/original/MZS.jpg.
- Confirm the company spelling: the logo says "Mohammad", company records and screens say "Muhammad". Align whichever is wrong.
- If a higher-resolution or vector original is found later, replace branding/original/MZS.jpg and rerun the branding scripts.

### 6. Distribution (user decisions required)
- Obtain a code-signing certificate so SmartScreen does not warn; sign setup and application executables.
- Choose how updates reach the client computer (manual installer copy vs. download/update check).
- Deliver an emergency owner recovery procedure for when every administrator is locked out (V2_DESKTOP_SCOPE.md requires it before release).

### 7. Android access (user decisions required)
- Decide how phones reach data: a LAN server mode on the Windows PC (needs deliberate network exposure and a firewall rule on trusted Wi-Fi) or an HTTPS-hosted server. Until then the APK cannot sign in.
- Adapt the service for the chosen route: listen beyond 127.0.0.1 only when explicitly configured, allowed hosts for that address, HTTPS or trusted-network rules, and login rate limits suited to network exposure.
- For wider distribution: create a release signing key (backed up outside git), build a release APK or AAB split per ABI (the debug APK is 164 MB), and test on real phones.

### 8. Remaining V2 scope
- Full historical migration once the client supplies original workbooks; reconcile the PKR 4,409,259 difference between the main receipts total (59,202,802) and the receipt summary (63,612,061) first.
- Client answers still open: meaning of "Sent to" and "Paid By", category list, report naming, computer/share arrangement.

### Deferred until the client authorizes
Double-entry posting, trial balance and statutory statements; payroll, fixed assets, tax/FBR integration and live tax invoices; Play Store publication, multi-computer or cloud sync and PostgreSQL production hosting. (A debug Android test APK exists; production Android access depends on task 7.)

## V2.1 — current increment

Data management, cash-basis income/expense classification, expanded report filters/groupings and reviewed setup-record spreadsheet imports are implemented. A downloadable Excel testing kit imports into the actual setup and receipt/payment forms as drafts. See V2_INCREMENT_5.md for fields, permissions, import sequence, acceptance checks and limits. All 62 backend tests pass and no model migrations are missing.

## Streamed backups, document counts, release checklist — 19 September 2026 (not yet released)

- **Streamed backup and restore:** backups stream through files on disk in the service and the application, removing the 2 GB in-memory limit; free disk space is checked first with a readable message. Backup format 2 encrypts in authenticated 4 MB chunks (chunk number and final-chunk flag bound into each tag) plus a whole-file SHA-256; format 1 backups from 2.1.0.5–2.1.0.8 still restore. The local service accepts restore uploads up to 64 GB, spooled to the data drive.
- **Supporting-document counts** for openings and transfers: shown on the openings/transfers list and in data management (also for receipts and payments), and transfer rows in register reports now count their active documents instead of 0. Withdrawn documents are not counted.
- **Release checklist:** docs/RELEASING.md. scripts/check_bundled_v2_service.py now uses a temporary empty data folder instead of storage/v2-desktop, so it never migrates real data.

Verification: 92 backend tests (4 new format-2 tests: multi-chunk round trip; truncated, reordered and shortened chunks rejected; format 1 compatibility; low disk space; plus 1 document-count test) and 28 Flutter tests (streamed download, failed download leaves no file, streamed upload; document-count wording). A live run through the waitress service with a 40.6 MB database: encrypted format-2 backup in 11 chunks downloaded in 1.5 s, restore preview in 1.2 s, all 40 MB restored byte-for-byte, staging cleaned. Not yet built into an installer.

## Supporting documents on openings and transfers, startup window — 17 September 2026

Openings and internal transfers now take supporting documents like receipts and payments: each record's menu has **Supporting documents** (PNG, JPEG or PDF up to 5 MB, 10 per record including withdrawn files, only the preparer on the current draft, withdrawal with reason, private authenticated download, audit events carrying the position and kind). Migration 0010 links attachments to either one entry or one position, enforced by a database constraint; the service backs up the database before applying it.

The Windows launcher shows a small "Starting Zakaria ERP…" window with the logo and elapsed seconds when launch takes more than a second (first run, database upgrade, slow computer). It stays until the main window is actually visible (Flutter shows it only after its first frame), and closes before any error message. The launcher now checks the Windows listening-port table before HTTP health checks, because a refused loopback connection blocks for about two seconds; this also removed a two-second delay from every launch. Windows sources compile as UTF-8.

Also: the workspace sidebar uses a Material background, fixing the long-failing workspace_admin_test at 1100 px without changing golden images; branding tools are listed in branding/requirements-branding.txt.

Verification: 87 backend tests (6 new position-document tests including the database constraint) and all 24 Flutter tests pass (1 new supporting-documents screen test). The startup window was captured from a scratch copy of the 2.1.0.8 build: shown at 1.2–1.4 s, closed only once the main window was visible, service stopped when the application closed. Backup and restore were exercised end to end inside the frozen service (encrypted backup, wrong-password rejection, preview, restore, old session rejected, pre-restore copy, staging cleaned). The Android server address uses an app method channel instead of shared_preferences; adding that plugin had required recreating Flutter plugin links with one elevated flutter pub get, since Developer Mode is off.

## Android test APK — 17 September 2026

Debug-signed APK artifacts/android/ZakariaERP-2.1.0+7-debug.apk (package pk.zakariasons.zakaria_erp, version 2.1.0 build 7, Android 7.0+, arm64-v8a/armeabi-v7a/x86_64) with the register screens (V2_DESKTOP=true), the MZS launcher icon and logo. Phones have no bundled service, so the server address is entered under Connection settings (shown automatically until one is saved) and remembered after a successful sign-in or registration; Windows keeps its packaged service address. Verification: the APK label, version, icon and logo asset were checked inside the package; 22 of 23 Flutter tests pass (2 new server-address tests; known workspace_admin_test failure unchanged).

Limit: no network-reachable V2 server exists yet. The desktop service accepts only loopback connections, so the APK cannot sign in to the Windows installation. Debug builds allow plain HTTP; a release build needs HTTPS and a release signing key kept outside git.

## MZS branding — 17 September 2026

See branding/README.md. The first redraw changed the logo's M, icon and tagline and was replaced. The logo is now rebuilt from the supplied original (branding/original/MZS.jpg, 204 x 80 px) in the same coordinate space: the three-piece orange M measured from its pixels, Z and S traced with JPEG noise smoothed, the glossy drop mark (black ring, silver band, amber drop, leaf cluster) redrawn against side-by-side overlays, and the tagline "Mohammad Zakaria & Sons" set in Century Gothic fitted to the original's position and width. Assets generated from branding/mzs-logo.svg appear as the application, shortcut and setup icon, installer wizard artwork, the sign-in screen and workspace sidebar logo, and the header of every PDF page (register reports, document reports, quotation/invoice PDFs), Excel report sheets and PNG/JPEG chart exports. CSV exports remain plain.

Verification: 81 backend tests (Excel test checks the four logo rows above each table header and a logo on every sheet) and 20 of 21 Flutter tests pass (known workspace_admin_test failure unchanged); login golden images were regenerated after waiting for the logo to decode. A sample PDF page header and chart export were rendered and inspected. One PyInstaller analysis subprocess crashed (0xC0000409) during packaging and succeeded on retry; numpy, installed for asset tracing, is now excluded from the bundled backend. Installer: artifacts/installer/ZakariaERP-Setup-2.1.0.7.exe (41,673,281 bytes) from package ZakariaERP-V2-20260917-041523 (2.1.0+7); icons extracted from the built application and setup executables show the rebuilt drop mark, and the bundled backend contains no numpy. Note: the logo says "Mohammad", while company records and screens say "Muhammad".

## Backup and restore — 17 September 2026

See V2_BACKUP_RESTORE.md. Backup & restore page (permissions system.backup / system.restore) saves complete .zerp-backup files, optionally AES-256-GCM password-protected; daily automatic copies keep the newest 7; safety copies are made before every restore and schema upgrade. Restore previews the backup's contents, requires the current password, validates checksum/integrity/version, applies upgrades and signs everyone out. New installations can restore from the first-run screen, which is also the route for moving storage/v2-desktop acceptance data into an installed copy.

Verification: 81 backend tests (12 new) and 20 of 21 Flutter tests pass (3 new; the known workspace_admin_test 1100px failure is unchanged). An end-to-end run against a real data folder and the unfrozen service passed: startup automatic copy, encrypted manual backup, wrong-password rejection, preview, restore of changed data, old session rejected (401), safety copy saved, staging cleaned. Installer ZakariaERP-Setup-2.1.0.5.exe (41,395,188 bytes) built from package ZakariaERP-V2-20260917-021100 (2.1.0+5); the frozen archive contains the backup module and cryptography bindings. Backup/restore has not yet been exercised inside the frozen service, because the installed application was running on port 8765. Installations created from the earlier 2.1.0 setup need system.backup and system.restore granted to Administrator in Roles & permissions after upgrading.

## Windows installer — 17 September 2026

See V2_INSTALLER.md. Inno Setup installer artifacts/installer/ZakariaERP-Setup-2.1.0.exe (39,532,246 bytes) built from package ZakariaERP-V2-20260917-013441 (2.1.0+4). Installs for all users; shared data in C:\ProgramData\ZakariaERP, kept on uninstall. New installations show a one-time Set up this computer screen for the first Administrator; database upgrades are backed up and integrity-checked before migration; startup errors go to logs\service.log.

Verification: 69 backend tests (7 new first-run tests) and 17 of 18 Flutter tests pass. The failing workspace_admin_test case at 1100px fails identically on the previous commit (sidebar ListTile Material assertion) and is tracked separately. Unfrozen service checks passed for a fresh folder and for an upgrade from migration 0008 (backup created, users/passwords unchanged). The frozen backend from the installer staging initialized an empty folder in 8 seconds, completed first-run setup, Administrator login and register access, then closed setup; the existing-data smoke check still passes. The installer itself has not yet been run: install/upgrade/uninstall on a clean Windows computer, SmartScreen behaviour of the unsigned setup and a two-account shared-data check remain acceptance steps. Existing storage/v2-desktop acceptance data is not migrated automatically.

## V2.1 Windows acceptance package — 17 September 2026

Native Windows V2.1 package (version 2.1.0+3) built with scripts/package-v2-windows.ps1 at artifacts/windows-v2/ZakariaERP-V2-20260917-005938/ZakariaERP.exe, with ZIP artifacts/windows-v2/ZakariaERP-V2-20260917-005938.zip (57,319,324 bytes). It supersedes the 15 September V2.0 package recorded below, which predates migration 0009.

Verification: packaging exited 0; scripts/check_bundled_v2_service.py confirmed the frozen backend reports version 2.1.0 desktop-register health (200), rejects unauthenticated business access (401) and stops only its own process. All 6,333 archive entries passed CRC verification; no database, service-secret or .env files are included; the V2 testing workbook is bundled. data-directory.txt points to the existing isolated storage/v2-desktop folder. Interactive client acceptance and application-close lifecycle checks remain outstanding. This is still an unsigned package for this computer, not a general-purpose installer.

Source control: the project is now under git on branch main, with a private GitHub remote (aamirshah313-cyber/zakria_erp). Local databases, storage/, artifacts/ and node_modules/ are excluded.

## V2 feature visibility and explicit role activation

The browser at http://127.0.0.1:5174/ serves the latest V2 release, verified by comparing its JavaScript hash with the local release and checking the new screen markers. The isolated backend at http://127.0.0.1:8766/api/health/ returns 200. Existing role permissions had initially been preserved, leaving the new register navigation hidden. This was an incomplete acceptance setup, not a missing frontend build.

After the user's visibility report, scripts/enable_v2_register_roles.py explicitly activated the approved workflow: Administrator gets register view/setup/create/import/export; Finance Manager gets view/create/import/export; General Manager gets view/approve/export. Existing permissions are retained. The General Manager is configured as register reviewer. No user account, password, audit access or bank-identifier access was added or changed. No General Manager account was active at activation; a separate registered reviewer still needs activation and assignment by the Administrator.

This configuration change has system-attributed audit events and backup storage/backups/before-v2-role-activation-20260914-194034-953001.sqlite3. SQLite integrity, unchanged user/password records, business-record fingerprints and original pilot hash passed. The setup script previews by default and is never run automatically on startup or migration.

Read-only request-factory checks against the existing V2 profile passed for Administrator and Finance Manager: profile, register masters, entries, openings/transfers, report definitions and imports all return 200. Unauthenticated register access returns 401. These checks created no login tokens or test business records. Both running browser acceptance endpoints also return 200. Script: scripts/check_v2_register_access.py.

User action: click the application Refresh button or sign out/in. Administrator should see Register setup and Transaction register. Inside the register are Openings / Transfers, Import spreadsheet and Reports / Print. Configure categories, projects and cash/bank sources before entering test transactions. Assign sensitive bank-identifier access only to the designated staff through Roles & permissions.

Historical (superseded by the 17 September V2.1 package above): native Windows V2 client built successfully at artifacts/windows-v2/ZakariaERP-V2-20260915-060559/ZakariaERP.exe (version 2.0.0+2). Microsoft C++ Build Tools and Windows SDK installation completed successfully; Flutter doctor reports no issues. The build used elevation for plugin links without enabling Developer Mode globally. PyInstaller bundled the backend; scripts/check_bundled_v2_service.py verified health (200), protected business endpoint (401) and owned-process shutdown. The packaged native EXE was launched and its bundled service returned health 200 on port 8765. Full interactive acceptance and application-close lifecycle checks remain for testing.

Keep the complete package folder together, including backend, data and DLLs. Its data-directory.txt points to the existing isolated storage/v2-desktop folder; company database/passwords/secret files are not bundled. This is an unsigned acceptance package for this computer, not a general-purpose installer. Packaging completed with exit code 0. The ZIP at artifacts/windows-v2/ZakariaERP-V2-20260915-060559.zip is 57,267,132 bytes; all 6,330 archive entries passed CRC verification and the database/service-secret exclusion check. Moving to another computer still requires reviewed V2 data setup.

## Current increment — client register, openings, transfers and custom reports

See V2_INCREMENT_4.md for the delivered forms, acceptance steps and explicit limits. Extended shared party/project/category/bank masters, bank-identifier permission, transaction nature/beneficiary, exact split allocations, reviewed single-scope openings, linked own-account transfers and one shared movement calculation are implemented. The import workflow accepts the new party/nature/beneficiary mappings. Detailed read-only receipt/payment review is available before approval. Register reports support saved personal layouts, field selection, filters, calendar/fiscal-month periods, charts and PDF/XLSX/CSV/PNG/JPEG exports.

Verification: all 54 backend tests and 12 Flutter tests pass. Tests include exact allocation/cutoff/transfer totals, bank access and identifier preservation, party snapshots, export permissions, saved-report ownership, decimal display and reviewer access to full allocation details. Synthetic A4 landscape multi-page PDFs, A3 portrait summary and chart output were rendered and visually inspected. The shared panel Material rendering issue detected by the new interface test was fixed without changing golden baselines.

Migrations 0006–0008 were applied to the isolated V2 database after an integrity-checked backup. Existing users, passwords, roles and register entry count were preserved; the pilot database hash stayed unchanged. No sample business transactions or guessed opening balances were inserted. New bank-details permission must be granted explicitly by the authorized administrator.

The final browser build is served and local frontend/backend checks pass. A native Windows acceptance EXE is now built and launched as recorded above; a general-purpose installer, user-facing backup/restore and clean-machine acceptance remain outstanding. Opening/transfer evidence currently uses a supporting reference/location; binary file attachments remain on receipt/payment entries. Full double-entry and wider accounting modules remain deferred. Historical milestones below do not supersede this current status.

## Latest increment — private register supporting documents

See V2_INCREMENT_2.md. Attachments, authenticated retrieval, versioned draft-only changes, withdrawal history and links from transaction/ledger/dashboard review are implemented. Migration 0004 was applied to the isolated V2 database after an integrity-checked backup. All 36 backend tests passed. Windows build prerequisites remain missing.

## Latest increment — spreadsheet import

See V2_INCREMENT_3.md. Controlled XLSX/CSV staging, field and master mapping, date interpretation, duplicate/exclusion review, control-total reconciliation and draft-only commit are implemented. Migration 0005 was applied to the isolated V2 database after backup. All 46 backend tests and 8 Flutter interface tests pass. The updated browser build is generated; native Windows packaging remains outstanding.

## Latest increment — register, recovery and application design

See V2_INCREMENT_1.md for the current delivered source, role-setup actions, limitations and remaining deliverables. Register/setup/ledger and password-recovery forms are now implemented, and the user's navy/blue dashboard reference has been applied through shared page/form styling. Migration 0003 is applied to the isolated V2 database only, after backup. Windows packaging remains incomplete; the Build Tools installer attempt exited 1602. Earlier preparation and broad pilot milestones below are historical context.

## Current direction — V2.0 desktop register preparation

The user narrowed the second phase to the two client register/ledger examples and their input/output forms, plus forgotten-password recovery, delivered first as a Windows desktop application. Full double-entry accounting and the broader accounting review gates are deferred to future client-authorized work. V2_DESKTOP_SCOPE.md is the controlling scope; historical milestones below remain background.

Prepared and verified: separate config.desktop settings (DEBUG=False, private secret, loopback-only service), Windows-compatible Waitress 3.0.2 installed in the project environment, isolated storage/v2-desktop database copied from the pilot without changing the original, existing users/passwords/roles retained, copied bearer sessions cleared, initialization/build/preflight scripts and native Flutter runner retained. Desktop service runs on 127.0.0.1:8765; it is an internal backend, not the final user interface.

Verification passed: Django configuration check, SQLite integrity, account-preservation comparison, repeat initialization without database changes, HTTP health 200 and unauthenticated business endpoint 401. No screenshot transactions or invented opening balances inserted. Details and commands: V2_ENVIRONMENT.md.

Native build readiness: Flutter SDK and Python are present; Flutter doctor confirms Visual Studio is absent and the readiness script reports Developer Mode off. EXE compilation remains blocked until the Desktop development with C++ workload (MSVC, CMake, Windows SDK) and symbolic-link support are available. No V2 native executable or installer has been produced.

Next deliverables: single-entry register/category/project models and forms, automatically linked ledgers, private evidence, Excel import/reconciliation, report layouts and local recovery-code/administrator-assisted password reset, followed by automatic service startup/runtime bundling and Windows installation testing. Password reset is specified, not yet implemented. Preliminary double-entry models remain unused scaffolding and must not be exposed as a completed V2 feature.

User action: arrange the Windows compiler/Developer Mode prerequisites before native build testing. Existing client questions stay saved for later; no new credentials or financial opening balances are required for environment preparation.

Latest review update — 12 September 2026: Claude's design review was received as INDEPENDENT_REVIEW_RESPONSE.md and assessed against selected current source. REVIEW_DECISIONS.md records accepted corrections, qualified recommendations and revised pre-posting gates. It supersedes earlier review-pending statements below. No application changes were made as part of that assessment.

## Update — 12 September 2026: accounting foundation

Implementation resumed following the user's go-ahead. Added role-controlled Accounting setup with Chart of Accounts, Projects & Contracts and Financial Years; account group/cycle/classification checks; non-overlapping fiscal dates; optional empty-chart starter template; and calendar pickers for setup, document and report dates. Access administrators (roles.manage) and finance.manage can maintain setup, while finance.view can read it. No new role permissions were automatically assigned and no audit-log bypass was added.

Migration 0002 applied after an SQLite backup to storage/backups/before-accounting-20260912-010946.sqlite3. Existing active users remain; accounting master tables are empty until the user configures them. No example data, opening balances or financial transactions were inserted. Preliminary voucher/evidence tables remain unexposed scaffolding, not functional posting or attachment features.

Validation: 22 backend tests passed, plus the new Flutter calendar test and two existing access tests (25 tests). Updated web build is in progress at this update. Local web/backend endpoints responded HTTP 200. Accounting setup is not a substitute for a posting engine, ledgers, bank masters or complete financial reporting.

User action when the web build is available: refresh/sign in, open Accounting setup, optionally create and review the starter Chart of Accounts, then configure the confirmed financial-year dates and test project. Use Roles & permissions to explicitly grant finance.view/finance.manage to designated staff. Keep opening balances out until posting and reconciliation are implemented.

Independent review: docs/CLAUDE_REVIEW_PACKAGE.md bundles the design and review instructions. No Claude review has yet been received. No direct Claude connector was found and browser access timed out. The package excludes live database contents, credentials and raw bank evidence.

Remaining: all later accounting milestones in ADDITIONAL_FINANCE_SCOPE.md, plus production prerequisites below. Historical pause/status notes in requirements documents predate the latest go-ahead.

This is a development pilot, not a production ERP. The supplied invoice is a layout reference only. No example party, tax, bank or product data has been imported into the business database.

## Milestone 1 — backend foundation
Implemented Django API, SQLite local database, PostgreSQL environment configuration and schema migrations. All money calculations use decimals on the server. Local SQLite is for single-machine pilot development; production PostgreSQL concurrency and backup validation remain outstanding.

User action: verify the company legal name, address and tax registrations in Company settings after initial setup. Do not enter financial opening balances yet.

## Milestone 2 — accounts and approvals
Implemented password hashing, pending registration, administrator activation, one editable role per user, permission-controlled navigation and API access, profile editing, password change, expiring sessions, editable one-stage quotation/invoice approval rules, blocked self-approval by default, and restricted read-only audit logs. Rule versions are snapshotted on submission. Users cannot edit submitted, approved or issued documents. Audit access has no implicit administrator bypass.

User action: create the first administrator using bootstrap; have Finance, GM and audit staff register; assign and activate roles from Users. Test the intended permission matrix. Administrator initially has no log access. Assign Audit Reviewer only to the designated person, or explicitly configure another designated role.

Outstanding: email verification and self-service forgotten-password recovery, durable distributed login throttling for production, optional MFA, approved delegation and approval thresholds. Profile photo is not yet included. Login tokens are kept only in app memory; users sign in again after closing the app.

## Milestone 3 — contacts, documents and reporting
Implemented customer/supplier records; quotation and invoice drafts with multiple lines; explicit tax treatment; return/reject comments; quotation issuance after approval; preserved issued company/customer snapshots; PDF preview/printing; field-selected reports, filters, grouping, horizontal bar summaries, saved personal report definitions and CSV/XLSX/PDF exports. Reports are document registers, not posted sales or financial statements. Maximum pilot report size: 5,000 documents. Contact/document lists have bounded pilot limits.

User action: create a clearly labelled test contact and quotation after setup. Submit as Finance, approve as GM, export and check the layout. Confirm report fields and terminology. Use only test records during this pilot.

Outstanding: ledger, purchases, expenses, payments, reconciliation, tax/FBR integration, standard financial statements, document conversion, quotation revision after issuance, custom field administration, Excel import previews, additional chart types/drill-down, JPEG/PNG export, shared dashboards, full template designer and wider document fields.

Live invoice issuance is deliberately disabled until accounting and tax readiness are implemented and tested. Do not use draft PDFs as tax invoices.

## Milestone 4 — deployment and apps
Flutter application source targets Windows, Android and a browser preview. Android cleartext networking is enabled only for debug builds; production must use HTTPS. The browser preview and local API are development servers. Windows and Android release signing, installer/update delivery, real-device tests, production hosting and recovery drills remain release prerequisites.

User action: retain control of release-signing keys, hosting and domain accounts. Configure external integrations only after the corresponding connectors are implemented. No external integration credentials are needed for this milestone.

## Next development order
1. Complete real-device pilot checks and correct any usability issues.
2. Add validated Excel contact imports and password recovery/verification.
3. Add chart of accounts, purchases, expenses and settlements with reconciled ledger tests.
4. Add accountant-approved taxes and required FBR connector before enabling live invoices.
5. Extend reports, graphical exports, template settings and custom fields.
6. Harden PostgreSQL deployment, backups, signed releases and updates.

## Verified results and packaging prerequisites

- Database migrations and Django system checks passed.
- 16 backend tests passed, including password/session controls, restricted logs, approval guards, exact totals, document snapshots and PDF/Excel exports.
- 2 Flutter access/registration tests passed.
- 2 responsive layout tests passed at 1440×900 and 390×844. Readable render images are in `apps/client/test/goldens`.
- Flutter browser build completed successfully; the local preview responded HTTP 200.
- Windows build is blocked by disabled Developer Mode / symlink support. Flutter doctor also confirms Visual Studio is missing. User action: enable Developer Mode and install Visual Studio's Desktop development with C++ workload, including the Windows SDK.
- Android debug packaging is a separate test deliverable; release signing and physical-device verification are still outstanding.

Build images and browser bundles are development outputs. No production administrator password, bank details, tax registrations or integration credentials have been invented or stored.
