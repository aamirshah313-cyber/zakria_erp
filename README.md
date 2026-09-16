# Muhammad Zakaria and Sons — ERP pilot

**Current direction: V2.0 Windows desktop register and linked ledgers.** See [V2 scope](docs/V2_DESKTOP_SCOPE.md), [desktop environment](docs/V2_ENVIRONMENT.md) , [Windows installer](docs/V2_INSTALLER.md) and [backup and restore](docs/V2_BACKUP_RESTORE.md). Full double-entry accounting is deferred by user request. The instructions below describe the existing pilot; they do not mean the V2 features or installer are already complete.

Windows/Android Flutter client with a Django API. Start with **docs/IMPLEMENTATION_STATUS.md** for exactly what is implemented and what remains. This is not ready for production financial use.

## First setup on this computer

From PowerShell in this project directory:

```powershell
.\.venv\Scripts\python.exe backend\manage.py migrate
.\.venv\Scripts\python.exe backend\manage.py bootstrap
```

The bootstrap command securely prompts for the first administrator's username, email and password. There are no default passwords. It creates Administrator, Finance Manager, General Manager, Coordinator and Audit Reviewer roles, and one-stage quotation/invoice approval rules. It refuses to run if an active account exists. No business sample records are created.

Start the local backend:

```powershell
.\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000
```

Then, in another terminal:

```powershell
cd apps/client
flutter pub get
flutter run -d windows
```

Windows builds require Visual Studio's Desktop development with C++ workload and Windows SDK. If unavailable, use the browser preview:

```powershell
flutter run -d chrome --web-port 5173
```

Choose **Connection settings** on the login screen if the API URL differs. Default: `http://127.0.0.1:8000/api`. Browser preview CORS accepts localhost/127.0.0.1 on port 5173 only in development.

The compiled browser pilot is also available in `apps/client/build/web`. Run `scripts/start-preview.ps1` and open `http://127.0.0.1:5173` while the backend is running. This avoids rebuilding Flutter merely to review the pilot.

## Android pilot

```powershell
cd apps/client
flutter build apk --debug --dart-define=API_URL=http://10.0.2.2:8000/api
```

The emulator uses `10.0.2.2` for the host computer. A physical phone needs a reachable API server: use an HTTPS test server, or explicitly configure a private LAN development endpoint and firewall. `127.0.0.1` on the phone is the phone itself. Never expose Django's development server publicly. No firewall rules are changed by this project.

Debug APK output: `apps/client/build/app/outputs/flutter-apk/app-debug.apk`. This is a debug-signed test package, not a production release. Keep Android release keystores outside version control. Windows build output must be distributed with its required DLL/data files, not as a lone exe.

## User acceptance checks

1. Bootstrap the administrator, sign in and enter verified company details.
2. Register separate Finance, General Manager and Audit Reviewer accounts. Activate and assign roles through Users.
3. Confirm Finance cannot open Roles or Audit logs. Confirm even Administrator cannot open logs until explicitly designated.
4. Add a test customer and a quotation. Pick an explicit tax treatment. Submit as Finance.
5. Sign in as GM, return it with a comment; edit/resubmit as Finance; approve as GM.
6. Issue the quotation as an authorized role. Confirm editing is blocked and PDF output is correct.
7. Run a custom report, choose columns, filters, grouping, colour, A4/A3 and orientation; export PDF/XLSX/CSV.
8. Change a role or suspend an account; confirm subsequent API actions are blocked.

## Tests

```powershell
.\.venv\Scripts\python.exe backend\manage.py test core
cd apps/client
flutter analyze
flutter test
```

API paths are in `backend/config/urls.py`. The initial backend uses SQLite locally; production database settings use POSTGRES_HOST, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD and POSTGRES_PORT. Set ERP_DEBUG=0, a strong ERP_SECRET_KEY, explicit ERP_ALLOWED_HOSTS and HTTPS deployment settings before production. A complete production deployment runbook and backup tests are still required.

## Fresh developer environment

Install supported Python 3.12+, create `.venv`, and install `backend/requirements.txt`. Flutter dependencies are in `apps/client/pubspec.yaml` with a checked-in lockfile. Use the stable Flutter SDK matching the project's Dart constraint. No production credentials belong in source control.
