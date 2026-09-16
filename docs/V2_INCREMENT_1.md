# V2 desktop increment 1 — 12 September 2026

## Delivered in source

The September 12 dashboard reference now guides the shared application theme: navy sidebar, royal-blue actions, pale-grey workspace, white panels, consistent tables, fields and dialogs. It applies to existing pages and new register/setup/recovery forms. The dashboard includes role-scoped approvals, search and type filtering, PKR figures, monthly receipt/payment bars and a category distribution chart. Empty databases show empty states; screenshots use isolated test fixtures, not seeded business records.

New register functionality provides category, cash/bank source and project setup; dated receipt/payment drafts; counterparty, amount, method, reference, handled-by and remarks fields; submission and approval by a configured role; version checks; reasoned cancellation; automatically derived confirmed-entry ledgers; date/category/project/source filters; opening movement from earlier recorded entries; running totals; and permission-controlled CSV export compatible with Excel. Date fields use calendar selection. One category and optional project are supported per entry in this increment.

Forgotten-password recovery supports privately retained recovery codes or a time-limited reset code issued by an explicitly authorized administrator. Issuance requires the issuer's current password. Only code hashes are stored; reset attempts are limited. A successful reset invalidates existing sessions and all recovery codes. Users should generate replacement recovery codes after resetting their password. No email delivery has been configured.

Migration 0003 was applied to the isolated V2 database after a SQLite backup. The original pilot database and existing credentials were preserved. New permissions were not silently assigned to existing roles.

## User acceptance actions after native build is available

Verification: all 34 Django backend tests and all 8 Flutter interface tests passed with the V2 desktop flag. Django reported no system-check issues. Dashboard previews were rendered at 1440 and 390 pixels wide and inspected; these checks do not replace a native executable acceptance test.

1. In Roles & permissions, grant designated Finance users register.view and register.create; grant the selected approving role register.view and register.approve. Assign register.manage, register.cancel, register.export and users.reset only to the relevant authorized roles. Access to the Users screen also requires the existing user-management permission.
2. In Register setup, create categories, cash/bank sources and optional projects, then select the approval role. The preparer cannot approve their own entry.
3. Using separate preparer and approver accounts, save and submit a small test receipt/payment, approve it, and verify the filtered ledger and CSV. Keep acceptance testing separate from real transactions.
4. In My profile, generate recovery codes and retain them privately offline. Do not send passwords, codes or the local database for external review.

## Packaging status and next deliverables

The native Windows EXE and installer are not built. A Microsoft Visual Studio Build Tools installation attempt returned installer exit code 1602 and did not complete. Complete the Desktop development with C++ prerequisites (MSVC, CMake and Windows SDK) and enable the required Windows symbolic-link capability/Developer Mode before native compilation. No APK was built.

Remaining V2 work: private supporting attachments, reviewed Excel import with mapping and duplicate prevention, opening-balance migration, split allocations if required, structured counterparty and bank details, richer print/PDF/XLSX outputs and register report customization, packaged local service/launcher, installer, upgrade/backup/restore and clean-machine acceptance tests. The developer service is not yet a standalone desktop distribution.

Ledger balances currently represent net confirmed recorded receipts minus payments, including earlier recorded movement for a selected period. They are not certified bank balances, profit, receivables, a trial balance or a balance sheet. Cancellation changes the current ledger view while retaining the entry and audit trail. Full double-entry accounting and the wider accounting modules remain deferred under V2_DESKTOP_SCOPE.md.

Design previews: apps/client/test/goldens/dashboard_1440.png and dashboard_390.png render the actual dashboard widget with test data and a simplified navigation fixture. They are not screenshots of a packaged EXE.
