# V2 increment 2 — supporting documents — 12 September 2026

## Delivered

Register entries accept PNG/JPEG bank screenshots and PDF supporting documents, accessible from the transaction menu, ledger row and dashboard approval review. The new page follows the shared application design.

Preparers with register.view and register.create may upload or withdraw files only on their own current draft. Submission, confirmation and cancellation lock attachments. An approver may return a submitted entry for correction. Each mutation increments the entry version, preventing stale approval. Withdrawals require a reason and retain metadata and bytes. Reads, uploads and withdrawals generate audit events visible under the existing designated log permission.

Readers with register.view can view images and save PDFs for review. This permission includes access to original supporting files; it does not prevent copying evidence. Image Save copy is additionally offered to register.export users. PDFs are saved for the user's installed reader.

Limits: 5 MB per file; 10 files per entry including withdrawn files; active duplicates rejected. Extension and signature checks reject unsupported types, but are not antivirus scanning or complete file-format validation. Private authenticated responses use no-store and nosniff headers. No public file route exists.

## Storage and verification

Migration 0004 was applied to the isolated V2 database after a SQLite backup whose integrity check passed. Django system checks passed. The original pilot database is unchanged. Supporting files are database blobs and participate in consistent database backups; this increases database and backup sizes. Managed file storage can replace this modest pilot arrangement later behind the same private API.

All 36 backend tests passed, including attachment access, stale versions, duplicate detection, approval locks, type/size limits and withdrawal retention. All 8 existing Flutter interface tests passed after integration. Static analysis found informational lint findings, with no error or warning diagnostics; it was not a clean lint run. Native file-picker, PDF-save and clean-machine acceptance tests remain outstanding until Windows compilation is available.

## Your acceptance steps

1. Save a test draft. Open its menu → Supporting documents → Attach document and select a test image/PDF.
2. Submit it, then sign in as the assigned approver. Review the supporting document before confirming; verify that edits are locked.
3. Open the confirmed entry's ledger row and use its paperclip to access the same evidence.
4. For a mistake, return the submission to the preparer, withdraw the wrong file with a reason, attach a replacement and resubmit.

No new permissions, users or sample transactions are inserted automatically. Keep acceptance testing separate from live records.

## Remaining

Excel import with mapping/duplicate checks/review; opening-balance migration; split allocations if required; structured bank/counterparty details; richer printable and custom register reports; desktop packaging, installer and clean-machine testing. Full double-entry remains deferred.

The readiness check still reports the Windows C++ toolchain missing and Developer Mode disabled. This source update is not a packaged EXE. No Android APK was built.
