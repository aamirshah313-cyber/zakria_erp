# V2.0 desktop development environment

The controlling scope is V2_DESKTOP_SCOPE.md: single-entry register and linked activity ledgers first; double-entry and larger accounting modules deferred. No finished V2 executable or password-reset feature is claimed by environment preparation.

## Prepared files

- backend/config/desktop.py: private loopback desktop settings, DEBUG=False, separate SQLite database, persistent generated service secret, no browser CORS origins or public media route.
- backend/requirements-desktop.txt: existing backend dependencies plus pinned Waitress server (Windows-compatible; official documentation: https://docs.pylonsproject.org/projects/waitress/en/stable/).
- scripts/prepare-v2-desktop.ps1: initialize isolated data/migrate/check. Optional -CopyPilot preserves pilot users/passwords/roles in a separate development snapshot and clears copied login sessions. Re-running does not overwrite existing V2 data.
- scripts/check-v2-desktop.ps1: local Python/Flutter/compiler/Developer Mode/data readiness summary.
- scripts/start-v2-desktop-service.ps1: serve internal API on 127.0.0.1:8765 only, using desktop settings.
- scripts/build-v2-desktop.ps1: build the native Flutter Windows client with the desktop API URL. Existing screens remain until V2 forms are implemented. It does not produce the final installer or bundle the local service/runtime.

## Developer usage

From the workspace in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-desktop.txt
.\scripts\prepare-v2-desktop.ps1 -CopyPilot
.\scripts\check-v2-desktop.ps1
.\scripts\start-v2-desktop-service.ps1
```

In another terminal, once Windows C++ dependencies are installed:

```powershell
.\scripts\build-v2-desktop.ps1
```

Data is under storage/v2-desktop for development and is excluded from git by the existing storage/ rule. Do not upload its database or service-secret.txt for external review. This is an independent snapshot of the pilot, not a synchronization link. Existing pilot scripts/settings are preserved.

The final installer must use an appropriate writable Windows application-data location, start the local service automatically with no console window, package runtime/DLL dependencies, and preserve data on upgrade/uninstall according to a documented policy. No requirement for users to install Flutter/Python in the final release.

## Native build prerequisites

Initial inspection found Flutter installed and Windows runner source present, but no Visual Studio C++ installation and Developer Mode not enabled. A native executable cannot be built on this machine until the Windows toolchain and plugin symbolic-link capability are available. Installing the toolchain is a separate large system installation; these scripts do not silently install or reboot Windows.

## Verification and remaining work

Preparation results: Waitress 3.0.2 installed; optional pilot copy initialized successfully; Django system check passed. scripts/verify_v2_environment.py passed account/password/role preservation comparison, cleared copied sessions, SQLite integrity, no-overwrite repeat initialization, HTTP health 200 and protected business access 401. No secret values were printed. The private desktop service was started on 127.0.0.1:8765. Flutter doctor confirmed Visual Studio missing; readiness check confirmed Developer Mode off. Native compilation has not been completed.

Record actual command results in IMPLEMENTATION_STATUS.md. Verify settings and database isolation, preservation of existing login accounts, idempotent initialization, local HTTP health and rejection of unauthenticated business access. No screenshot transactions should be seeded.

Update, 12 September: initial register/ledger models and forms, approval controls, CSV export and local password recovery are implemented; see V2_INCREMENT_1.md. Migration 0003 was applied to the isolated V2 database after backup. Native toolchain installation did not complete (Microsoft installer exit 1602). Remaining: native toolchain/build, Excel migration workflow, private evidence, richer register outputs, desktop service bundling/launcher, installer and clean-machine testing. The development service is not a completed standalone application.
