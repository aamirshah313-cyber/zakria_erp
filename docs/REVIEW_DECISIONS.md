# Independent review assessment and corrected delivery gates

Scope superseded for V2.0: the user subsequently requested a desktop single-entry register and linked ledgers first. See V2_DESKTOP_SCOPE.md. Preserve this review for future double-entry/accounting work; its full-accounting gates are not prerequisites to implementing the narrowed register. Registration, password security, permissions, evidence protection, exact amounts, traceability and duplicate prevention remain applicable.

Date: 12 September 2026. Reviewer response: INDEPENDENT_REVIEW_RESPONSE.md, supplied by user as Claude's review. Original response is preserved unchanged. This assessment is a review of requirements and selected current source, not a full security audit. No application changes or migration resets are performed by this document.

## Decision

Additional artifact assessed on 12 September 2026: see CLAUDE_ARTIFACT_ASSESSMENT.md and the preserved CLAUDE_ARTIFACT_DETAILS.txt. It restates the prior review; all 36 detailed IDs are covered below. Its detailed register has six blockers and eight High findings, despite executive counters of five and seven. This does not change the dispositions or authorize deleting the applied migration.

Proceed with corrections, retaining the current application and all requested features. Adopt the missing financial mechanisms before live posting. Do not treat the external review's assumptions, estimates, legal conclusions or proposed code mechanisms as automatically authoritative.

Current status takes precedence over historical pause notes in the initial requirements: the user resumed implementation; foundation models/forms and calendar controls were developed. Migration 0002 was applied after backup. No operational accounting posting service has been delivered. Prior test results validate setup/document behaviour, not PostgreSQL posting concurrency or financial statements. The next accounting implementation must incorporate this decision register before real transactions can be posted.

The review package Claude saw was an earlier snapshot. Its statement that migration 0002 was unapplied was true when that snapshot was assembled, but is no longer current. This assessment corrects that handoff discrepancy explicitly.

## Checked against current source

- core/models.py has preliminary Voucher, JournalLine and Evidence models, but no settlement/open-item entity, structured voucher party FK, control-account flags or final posting number. These are genuine design gaps to close before posting.
- core/accounting_setup.py explicitly permits roles.manage as well as finance.manage for maintaining accounting masters. Separate these permissions before real accounting use, with a reviewed transition so administrators are not unexpectedly locked out.
- core/views.py Users.patch blocks changing one's own user access and deletes sessions when access is changed. Roles.patch, however, permits adding privileges to one's own role. Blocking self user-assignment alone therefore does not establish separation of duties.
- core/auth.py SessionAuthentication fetches the current user and role on each request, checks active status, and evaluates current role permissions. Permissions are not embedded in the bearer token. Regression tests for role changes/session revocation should supplement this source evidence.
- core/reports.py applies a 5,000-document cap to document reports and raises an explicit validation error. It does not silently truncate a financial ledger; the financial ledger does not exist yet. Financial reports need their own indexed, scalable queries.
- config/settings.py uses Asia/Karachi and USE_TZ=True. Current document defaults use Flutter DateTime.now(), which follows the device timezone. The review's timezone.now().date() bug was not found in that path; an authoritative business-local date is still a useful correction for devices outside Pakistan.
- showmigrations confirms core.0001 and core.0002 applied. Preserve migration history and use forward migrations; do not delete/reset the database or rewrite an applied migration based on an outdated review snapshot.

## Finding dispositions

| Finding | Decision and intended correction |
|---|---|
| A1 Settlement allocations | Accept as a pre-posting requirement. Add open items and reversible many-to-many settlements with party, book, currency, due date, allocation date and source links. Serialize allocations and prohibit over-allocation. Withholding and retention must be represented by proper journal/reclassification entries; an allocation is not itself a substitute for a balanced journal. |
| A2 Year end | Accept need for explicit policy. Prefer derived current/prior-year results initially, without closing journals. Separate opening retained earnings, prior-year unclosed result and current-year result without counting any component twice. Label raw cumulative trial balance separately from fiscal-year opening/presentation adjustments. Zero P&L openings require a defined report transformation or actual closing process, not silently resetting balances. Test two years, cutover and reopened periods. |
| A3 Settlement deductions | Accept. Add reviewed deduction types, net/gross reconciliation, recoverable tax/withholding liabilities, retention and evidence. Recoverability, timing and applicability depend on facts. Retention should have its own release/due dates and can become overdue; it is not permanently excluded from aging. Do not assume a deduction rate or even actual deduction from this example. |
| A4 FBR | Accept separate compliance gate before live tax-invoice issuance. Reverify current registration-specific requirements and integration rules. Keep internal document ID distinct from external FBR reference. A rejected/timed-out transmission must not create duplicate issuance; fiscal transmission and revenue recognition are related but separate state machines. Do not suppress otherwise required accruals solely because an external service is unavailable. |
| A5 Control accounts | Accept. Explicit control type, required party/project and authorized adjustment rules; reconcile subledgers. A PostgreSQL CHECK cannot read another table's Account flags. Enforce with validated schema design/constraints and database triggers for cross-table rules, including protections on referenced account configuration changes. |
| A6 Fixed assets | Accept. Approved depreciation runs create journals linked to per-asset detail; reconcile cost, accumulated depreciation, impairment and disposals to GL. Period readiness must check required runs and approved policy exceptions. |
| A7 Employee benefit provisions | Accept configurable supporting schedules and accountant-entered adjustments for applicable benefits. Do not presume every company owes every listed provision. |
| A8 Precision | Accept exact balances and deterministic rounding/remainders. Specify PKR stored money scale 2, sufficient working precision, explicit rounding and deterministic remainder tie-breaks. Existing document code already uses Decimal and ROUND_HALF_UP, but the new accounting schema and split rules need their own specification. No epsilon balancing. |
| A9 Reversals | Accept date/allocation controls. User confirms an eligible accounting date; no silent shift to the earliest open date. Preserve original date and all allocation reversals. Closed-period error correction/restatement policy needs accountant input; current-period reversal is not universally sufficient. |
| A10 Dates | Accept document_date, accounting_date, value_date and immutable posted_at; date-only calendars. Historical 'as known at' also requires versioned master/report mappings, allocation history and saved report snapshots, not just a posted_at filter. |
| A11 Currency | Accept explicit functional/document currency identity and enforced PKR/rate-1 pilot policy. Multi-currency calculation is deferred; do not accept arbitrary exchange rates without a complete FX policy. |
| A12 Cutover | Accept book-level mutually exclusive full-history versus opening-balance mode, explicit cutover boundary, reviewed opening journal and source lineage. Define the special opening period/boundary so it does not conflict with normal open-period rules. |
| A13 Cash flows | Accept a clearly labelled management cash movement summary initially. Classify split transactions at allocation level; a single counter-account tag is insufficient for mixed settlements. Defer statutory statement claims until accruals and policies are ready. |
| B1 Numbering | Accept separate immutable draft reference and number allocated atomically at posting by book/year/type. Current ID-derived reference is unique, so 'races guaranteed' is not established. Abandoned draft gaps are not inherently corrupt accounting. Audit posting-number gaps and retain void history; do not promise gaplessness under every recovery scenario as a substitute for traceability. |
| B2 PostgreSQL | Accept PostgreSQL transaction/concurrency tests as a gate before financial posting. Include concurrent settlements, duplicate requests, numbering, period closure races and a test proving locks actually block. SQLite tests do not validate these behaviours. |
| B3 Immutability | Accept database-level guards, least-privilege application DB role and restricted admin paths. Protect INSERT into posted vouchers too, not just UPDATE/DELETE, and protect finalized metadata. Cross-row balance validation needs appropriate transactional checks. External audit checkpoints can improve tamper evidence; hash chaining alone cannot prevent privileged tampering or prove completeness. |
| B4 Privileges | Accept decoupling finance setup from role administration and strengthening privileged-grant approval. Cover own-role edits, shared roles and every assignment route. Design a separately authorized initial security approver/recovery path before enforcing two-person grants. Logs currently have no edit API; the review scenario should not imply audit-view alone grants log deletion. |
| B5 Approvals | Accept amount bands and time-bounded delegation where needed, with maker/checker separation. Snapshot rules and define which later policy changes invalidate pending approvals; recheck actual eligibility/version at posting. Never mutate an approved amount in place. |
| B6 Scale | Accept indexes, DB aggregation, pagination and bounded/streamed exports. Benchmark real journal queries first. Add maintained balance aggregates only if needed, with reconciliation and rebuild; premature duplicate balance stores add integrity risks. Existing document cap is not evidence of a ledger defect. |
| B7 Business date | Accept company-local default plus timezone-boundary test; qualify the review's unverified implementation claim as above. |
| B8 Migration | Do not delete applied migration 0002. Correct through forward migrations, migration tests and backups. Applying an empty additive schema does not by itself require redesign. Reassess any affected existing records before converting columns. |
| B9 Evidence | Accept private file storage, authenticated downloads, hash/type/size metadata, protected preview and coordinated restore verification before evidence functionality is exposed. Database binary storage is not inherently public/insecure, but it differs from the selected target design. |
| B10 Entity | Record one legal entity/book for the first release. No intercompany/consolidation scope is implied. Add explicit non-null book identity to posting/source/settlement uniqueness and query scoping before live data; reject cross-book allocations. |
| B11 Sessions | Core per-request revocation behaviour supported by source; add regression tests and administrative session revocation/listing as planned improvements. |
| B12 Data exposure | Accept consistent field-level permissions, logged exports and sensible resource/rate limits; deployment controls and recovery remain required. |
| C1 Suspense | Keep unresolved rows in staging by default. Controlled migration suspense is an optional accountant-approved isolated migration-mode tool, not automatic balancing. A zero NET suspense balance alone is insufficient: every unmatched debit/credit item and exception must be resolved and signed off, because unrelated errors can offset. |
| C2 Import authority | Do not mandate journal-only import. Client says most data is on ledger sheets and completeness is unverified. Choose a canonical source by reviewed batch/coverage; use counterpart sheets as enrichment where matched. Unmatched legitimate ledger transactions need controlled review, not permanent exclusion. Stable batch/sheet/row keys prevent reimport; separate explicit cross-source duplicate links are still needed. |
| C3 Batch reversal | Accept an authorized, traceable reversal batch with resumable/idempotent processing, period controls and handling of already settled items. |
| C4 Excel edge cases | Accept hidden/merged rows, localized numerals, separators, formulas and stale caches as preview exceptions. Hidden does not mean deleted; neither include nor exclude silently. Never execute untrusted macros/formulas. |
| C5 Embedded objects | Accept re-upload as reliable fallback; extraction only after verified anchoring/type checks. |
| C6 Receipt discrepancy | Preserve source exception and test candidate scope, status and transcription explanations against the workbook. Do not infer a tax rate from the numeric difference or assume the fifth receipt is a withholding adjustment. |
| D2 Integrity report | Accept per-voucher balance, missing dimensions, control/GL variance, duplicate source identities, period checks and sequence exceptions. Check account eligibility at posting; an account deactivated later may legitimately retain historical postings. Periodic execution must be configured at deployment, not silently scheduled now. |
| D3 Comparatives | Accept explicit restatement policy and historical report/mapping versions. |
| D4 Project labels | Accept cash movement labels only for actual cash-filtered views; combined accrual/project activity cannot automatically be called cash movement. Preserve standard accounting labels and clear scope/legends. |
| D5 / E1 Scope | Accept phased delivery and simple initial reconciliation/donation workflows. Retain all user-requested capabilities, including custom reports/charts, image/A3 exports, payroll/assets and eventual native apps. No evidence supports assuming a single bookkeeper or a multi-year schedule; estimate after concrete scope and acceptance tests. |

## Additional corrections to the walkthroughs

- One receipt can support several legitimate expense allocations. Replace 'one evidence record may support exactly one line' with source-document identity plus amounts already claimed/allocated, duplicate detection and an approved-allocation ceiling. This prevents double claims without prohibiting splits or partial settlements.
- Donations with restrictions do not automatically meet the definition of a liability. Recognize according to the actual conditions, agreement and applicable framework. Receipt timing and tax deductibility are separate questions.
- Withholding deductions should normally be captured with the settlement. A later supported adjustment can be valid if linked, approved and reconciled; do not ban all separate adjustment vouchers.
- Aging convention must be explicit: overdue days normally use due dates, while invoice-age analysis uses invoice dates. Reversal restores the original open item's dates, not a newly reset age.
- A receipt/allocation table must define eligibility, currency/book/party consistency and atomic over-allocation checks. The review's suggested schema is a useful sketch, not a complete enforceable design.

## Revised execution gates

1. **Foundation correction:** non-destructive model evolution, structured parties/book identity, control accounts, precise dates/currency, financial access policy, reviewed account mappings and rounding specification.
2. **Posting and settlement:** atomic balanced posting, separate numbering, immutable records, allocations/deductions, reversals and period controls. PostgreSQL concurrency and direct-DB protection tests are mandatory before real posting.
3. **Accounting outputs:** independently calculated two-year fixtures, trial balance/general ledger, subledger reconciliations, integrity reports, management cash summaries and appropriate report-date semantics.
4. **Migration and operational workflows:** controlled source selection, import review/deduplication, opening mode, evidence, claims/advances and reconciliations. All exceptions require ownership and sign-off before live use.
5. **Commercial/regulatory readiness:** customer/supplier document settlement, confirmation of applicable FBR/tax requirements, tested integrations where needed. Live invoice issuance stays disabled until its gate is satisfied.
6. **Requested extensions:** payroll, fixed assets and valuations, donations, extended custom/graphical reporting and native packaging in manageable releases. Existing requirements remain in scope.

No additional client answer is required to complete this review. Saved questions about registration, reporting framework, financial year, cutover, payroll/assets and source authority remain for the appropriate gate.

## Sources checked for this assessment

- Django 5.2 QuerySet documentation: https://docs.djangoproject.com/en/5.2/ref/models/querysets/#select-for-update — SQLite does not implement SELECT FOR UPDATE; transaction tests are needed to test locking meaningfully.
- PostgreSQL constraints: https://www.postgresql.org/docs/current/ddl-constraints.html — CHECK constraints cannot enforce conditions by reading other table rows; use appropriate other mechanisms.
- FBR digital-invoicing FAQs: https://www.fbr.gov.pk/faqs/173967/173969 — confirms integration/applicability questions and invoice requirements need separate attention. This assessment does not adopt unverified rollout dates, rates or a claim that the company is sales-tax registered.

## Review completion status

External review received and assessed. Corrections are incorporated into this decision register and delivery gates; they are not yet implemented or validated by new tests. Original review remains available for traceability. No credentials, database contents or client attachments were sent to an external service by this assessment.
