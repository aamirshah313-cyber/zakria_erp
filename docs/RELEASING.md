# Release checklist

Windows installer, portable package and Android test APK for the V2 register. Commands run from the project folder in PowerShell. Build outputs go to `artifacts/` (not in git); the GitHub repository is private.

## 1. Decide the version

- Windows: `2.1.0.N` for the installer, build number `N` in `scripts/package-v2-windows.ps1` (`--build-number=N`).
- Android: `--build-name=2.1.0 --build-number=N` (Android `versionCode` must increase every release).
- The service health endpoint reports `2.1.0` (`backend/core/views.py`, `backend/core/backups.py` `app_version`); change it only for a new minor version.

## 2. Tests (all must pass)

```powershell
.\.venv\Scripts\python.exe backend\manage.py test core
.\.venv\Scripts\python.exe backend\manage.py makemigrations --check --dry-run
cd apps\client
flutter analyze lib test
flutter test
cd ..\..
```

Golden images change only for intentional visual changes: `flutter test test/layout_test.dart --update-goldens`, then look at the new PNGs before committing. Delete `apps/client/test/failures/` after failed golden runs.

## 3. Brand assets (only if the logo changed)

```powershell
.\.venv\Scripts\python.exe -m pip install -r branding\requirements-branding.txt
.\.venv\Scripts\python.exe branding\build_logo.py
.\.venv\Scripts\python.exe branding\build_assets.py
```

## 4. Windows build

```powershell
.\scripts\run-v2-package-with-log.ps1          # backend bundle + Flutter Windows client + package folder + ZIP
.\scripts\build-v2-installer.ps1 -AppVersion 2.1.0.N
```

- Log: `storage\v2-desktop\native-build.log`. Package: `artifacts\windows-v2\ZakariaERP-V2-<timestamp>\` and `.zip`. Installer: `artifacts\installer\ZakariaERP-Setup-2.1.0.N.exe`.
- `-UseExistingBackend` skips the PyInstaller step when only the Windows client changed.
- **Plugin links:** Flutter needs symbolic links for Windows plugins. Developer Mode is off on the build computer, so if the Flutter plugin list changes, or a failed build empties `apps\client\windows\flutter\ephemeral\.plugin_symlinks`, run one elevated `flutter pub get` after deleting `apps\client\.flutter-plugins-dependencies` (Windows asks for administrator approval). Avoid adding plugins; app-specific Android code can use a method channel instead.
- A PyInstaller analysis subprocess occasionally crashes (0xC0000409); rerun.
- Dev-only packages in `.venv` (e.g. numpy) must stay out of the bundle; the package script excludes numpy. Check `artifacts\installer-stage\backend\_internal` for unexpected libraries.

## 5. Android build

```powershell
cd apps\client
flutter build apk --debug --dart-define=V2_DESKTOP=true --build-name=2.1.0 --build-number=N
copy build\app\outputs\flutter-apk\app-debug.apk ..\..\artifacts\android\ZakariaERP-2.1.0+N-debug.apk
```

Check with `aapt dump badging` (from the Android build-tools) that the package, version, label and icon are right. Debug builds are debug-signed test packages; a release build needs a release key kept outside git.

## 6. Checks before publishing

- [ ] Installer and application icons show the MZS mark (extract with `System.Drawing.Icon.ExtractAssociatedIcon`).
- [ ] The package ZIP opens without CRC errors and contains no `*.sqlite3`, `service-secret.txt` or `.env` files (the installer build script also refuses these).
- [ ] Frozen service check: `.\.venv\Scripts\python.exe scripts\check_bundled_v2_service.py` (new database in a temporary folder, health 200, protected endpoint 401, clean shutdown). Needs port 8765 free; close any running Zakaria ERP first.
- [ ] Launch a copy of the package pointed at an empty data folder (edit its `data-directory.txt`): the Starting window appears after about a second and closes when the main window shows; closing the application stops `zakaria_service.exe`.
- [ ] If backup code changed: backup, wrong-password rejection, preview and restore against the frozen service on a scratch data folder.
- [ ] Never test against `storage\v2-desktop` or `C:\ProgramData\ZakariaERP` without a backup; database upgrades run on launch.

## 7. Publish

1. Update `docs/IMPLEMENTATION_STATUS.md` (current release table, verification, next tasks).
2. Commit and push to `main`.
3. Create the GitHub Release on that exact commit (use the full SHA; `gh` rejects short ones):

```powershell
$sha = git rev-parse HEAD
gh release create v2.1.0.N --repo aamirshah313-cyber/zakria_erp --target $sha --title "Zakaria ERP 2.1.0.N" --notes-file <notes.md> `
  artifacts\installer\ZakariaERP-Setup-2.1.0.N.exe <package>.zip artifacts\android\ZakariaERP-2.1.0+N-debug.apk
gh release view v2.1.0.N --repo aamirshah313-cyber/zakria_erp --json assets
```

Rename the package ZIP to `ZakariaERP-V2-2.1.0+N-windows.zip` when uploading. Release notes list the files, what changed, any permissions to grant after upgrading, and the test counts.

## 8. After release

- Upgrade the installed copy with the new installer and confirm data, accounts and the new features.
- Keep the previous installer for rollback; delete older builds from `artifacts/`.
