# DOCSight CH7465ONE Project Log

This log tracks the user-specific investigation and development work for the Hungarian ONE Compal CH7465ONE. The upstream product documentation remains authoritative for general DOCSight behavior; this log records findings for this modem and firmware only. Historical entries below were assembled on 2026-10-20 from the preserved conversation and audit files. Original completion dates for Phases 1–3 were not retained in the local artifacts.

## Phase 1 — Environment and compatibility assessment

**Report date:** 2026-10-20 (retrospective; original completion date not retained)

**Objective:** Assess the Linux/Python environment and DOCSight native-install compatibility for CH7465ONE firmware `CH7465ONE-NCIP-6.15.20.5-3-SH`.

**Findings:**

- **User-reported:** The native Python installation was subsequently running without errors.
- **Unresolved in preserved local records:** The exact distribution/version and Python/pip/git/venv versions, as well as the detailed evidence used for the initial compatibility assessment, are not preserved in this checkout. Do not reconstruct them from assumptions.
- Firmware compatibility was treated as unconfirmed pending device-specific investigation.

**Changes:** No DOCSight source changes are recorded for this phase.

**Tests:** No test results from this phase are preserved. The user's later confirmation that DOCSight was running without errors is not a substitute for a recorded test report.

**Unresolved issues:** Firmware compatibility and modem-specific Network Log access.

**Next steps:** Read-only investigation of the current CH7465 driver and the modem UI's Network Log request, with explicit approval before authenticated capture.

## Phase 2 — CH7465ONE Network Log API discovery

**Report date:** 2026-10-20 (retrospective; original capture date not retained)

**Objective:** Determine whether the modem's internal Network Log is retrievable through the existing DOCSIS XML interface and whether it shares the current authenticated session.

**Findings:**

- **User-confirmed capture:** The standard CH7465 driver family works with the observed CH7465ONE firmware for the existing DOCSIS path.
- **User-confirmed capture:** The Network Log page issues `POST /xml/getter.xml` with `fun=13`; the XML response contains `eventlog_table` and `eventlog` elements with `prior`, `text`, `time`, and `t` fields.
- **User-confirmed capture:** The browser used the authenticated session cookies. The modem restricts simultaneous administration sessions.
- **Unresolved:** The timezone interpretation of `time` and semantics of `t` were not established. Those values must remain unnormalized/opaque until verified.
- The capture was read-only. Credentials and session tokens are intentionally excluded from project documentation.

**Changes:** No DOCSight source changes or modem configuration changes.

**Tests:** A browser-based UI request/response capture was performed with user approval. No automated retrieval test was run.

**Unresolved issues:** Robust timestamp interpretation, stable deduplication identity, and integration into DOCSight event storage.

**Next steps:** Inspect the module and collector extension APIs and establish whether integration can avoid a second login.

## Phase 3 — Network Log integration plan

**Report date:** 2026-10-20 (retrospective; original plan date not retained)

**Objective:** Prepare an implementation plan without modifying the repository or accessing the modem.

**Findings and proposed design:**

- The existing generic event table can display normalized modem entries, but it has no stable source key for durable deduplication.
- The existing modem poll owns authentication and signal collection. Optional log retrieval must use the same driver/session and be isolated so log failures cannot stop signal monitoring.
- Preserve raw `prior`, `text`, `time`, and `t`; do not infer undocumented values.
- **Proposed:** Add an optional driver event method, call it during the existing core poll after core signal data is acquired, and persist idempotently with a schema/storage change. Defer Smart Capture triggers until event semantics are established.

**Changes:** No source files, dependencies, or modem settings were changed.

**Tests:** No tests were run; this phase delivered a plan only.

**Unresolved issues:** Whether a community module can implement the feature without core changes; timestamp and `t` semantics; final deduplication identity.

**Next steps:** Audit DOCSight's community driver, collector, event-storage, and Smart Capture APIs.

## Phase 4 — Community module and exclusive-session architecture audit

**Report date:** 2026-10-20

**Objective:** Determine whether Network Log retrieval and exclusive-session coordination can be implemented as a community module alone.

**Verified findings:**

- The inspected DOCSight checkout was `84d2ba24f651f030c43444c501fcd7059ff5a862` on `main`. The official community module catalog was inspected at commit `c7d1dbae5eec722b6e1a501b472d46b08fd6aec7`.
- The community module mechanism supports an exact-key driver override, but a driver contribution cannot also contribute a collector. A separate module collector receives configuration, storage, and web services, not the already-authenticated core modem driver/session.
- Module collectors run on their own schedules and do not share the core modem collector's per-instance collect lock. A separate collector that authenticates to the modem risks creating a competing session.
- Generic event storage exists, but has no source-key uniqueness for modem-log deduplication.
- In the inspected core, Smart Capture is explicitly wired to the Connection Monitor collector rather than exposed as a generic community-collector injection.

**Decision:** **Proposed architecture:** community CH7465 driver override plus minimal upstream core support. The core should call an optional modem-event method on the existing driver inside the existing poll, isolate failures, and provide durable idempotent event storage. Smart Capture integration is optional follow-up work. A standalone module does not satisfy the shared-session requirement through current APIs; a full fork is not needed if the minimal upstream hook is accepted.

**Changes:** The audit report was created at the workspace level as `PHASE4_DOCSIGHT_FORK_AUDIT.md`; this repository log records its findings. No DOCSight source code was changed.

**Tests:** Read-only source inspection; no code tests were appropriate or run.

**Unresolved issues:** Upstream acceptance of the optional driver/event storage hook; `time` timezone and `t` semantics; event severity policy; exact firmware-specific behavior over longer observation.

**Next steps:** Review the Step 2 Git connection audit before any remote configuration. Do not fetch, change remotes, implement, commit, or push before the relevant user approval.

## Step 2 — Git connection audit (workflow checkpoint)

**Report date:** 2026-10-20

**Objective:** Inspect repository/workspace structure and propose a safe remote setup for the personal fork without changing Git state.

**Verified findings:** The workspace root is not a Git repository; the DOCSight clone is nested at `docsight/`. At inspection, `main` was clean at `84d2ba24`, tracking `origin/main`; `origin` pointed to `https://github.com/itsDNNS/docsight.git`. The Phase 4 audit is outside the clone. These statements describe the pre-documentation-edit state.

**Proposal:** Rename current `origin` to `upstream`, add `https://github.com/lukumaki/docsight.git` as `origin`, and verify with `git remote -v` and `git branch -vv`.

**Changes/tests:** No Git configuration, branch, ref, commit, fetch, or push was changed/performed. The detailed report is `STEP2_GIT_CONNECTION_AUDIT.md` in the workspace root, outside this clone.

**Status and next step:** **Pending user review.** Do not make the proposed remote change or fetch until approved. The audit's pre-edit clean status no longer describes the working tree after these documentation edits; review current `git status` before any later Git operation.

## Documentation workflow bootstrap (not a numbered project phase)

**Report date:** 2026-10-20

**Objective:** Establish persistent project instructions, status, phase history, and verified architecture records in the DOCSight repository.

**Findings:** The repository had an upstream product `README.md` and a populated `docs/` directory, but no project `AGENTS.md`, `docs/PROJECT_LOG.md`, or `docs/ARCHITECTURE.md`. `.gitignore` excluded Markdown files in `docs/`, which would have kept the requested project records out of a proposed Git commit.

**Changes:** Added `AGENTS.md`, appended a CH7465ONE status section to the existing `README.md` without replacing its content, created this chronological log and `docs/ARCHITECTURE.md`, and added narrow `.gitignore` exceptions for `docs/PROJECT_LOG.md` and `docs/ARCHITECTURE.md`. Existing unrelated Markdown ignore behavior is retained.

**Tests and verification:** `git diff --check` passed; required files and local README links were checked; `git status` shows only the expected documentation and `.gitignore` changes. No application tests were run because no source code changed. Git remotes, branches, and commit history were not changed; no fetch, commit, or push was performed.

**Unresolved issues:** The personal fork has not been fetched or compared. Workspace-level Phase 4 and Step 2 audit files remain outside the DOCSight clone; their findings are summarized here, but the original reports are not part of this repository's proposed commit.

**Next steps:** Review `STEP2_GIT_CONNECTION_AUDIT.md`; wait for approval before changing remotes or contacting GitHub. Continue to keep documentation changes in the proposed commit when development work is approved.


## Step 2 completion — Git remote configuration

**Report date:** 2026-10-20

**Objective:** Configure the local DOCSight clone with the personal fork as `origin` and official DOCSight as `upstream`, preserving the existing documentation work.

**Preconditions verified:** The repository was `/home/ilovelinuxmint/projects/docsight-investigation/docsight`, branch `main`; before configuration, `origin` pointed to `https://github.com/itsDNNS/docsight.git`. The only working-tree changes were the five reviewed documentation-related files: `.gitignore`, `README.md`, `AGENTS.md`, `docs/ARCHITECTURE.md`, and `docs/PROJECT_LOG.md`.

**Changes:** Ran the approved commands `git remote rename origin upstream` and `git remote add origin https://github.com/lukumaki/docsight.git`.

**Verification:** `git remote -v` confirmed `origin` fetch/push URLs as `https://github.com/lukumaki/docsight.git` and `upstream` fetch/push URLs as `https://github.com/itsDNNS/docsight.git`. `git branch -vv` and `git status -sb` confirmed branch `main` tracks `upstream/main`. `git status --short` showed the five documentation changes remained uncommitted. The branch remained at commit `84d2ba24`; no source files or commits changed.

**Tests:** Read-only Git verification only. No fetch, pull, push, staging, commit, modem access, or application tests were performed.

**Unresolved issues:** The personal fork's remote history has not been fetched or compared. Phase 3 Network Log retrieval remains a proposal; no implementation has been started.

**Next steps:** Stop after Step 2 and await further user instructions. Do not proceed to Step 3 or fetch without explicit approval.

## Step 4.7 — Manual Network Log response comparison and design update

**Report date:** 2026-10-20

**Objective:** Record the user's verified manual DevTools observations and update the project design without implementing code or contacting the modem.

**OBSERVED — manual DevTools evidence:**

- The Network Log request is `POST /xml/getter.xml` with form field `fun=13`; the XML root is `eventlog_table`.
- The response contains 20 `eventlog` and 2 `wifieventlog` elements. Each has `prior`, `text`, `time`, and `t` fields.
- Two successive responses were exactly identical in entry values and order. This is a two-observation stability result only.
- `t` is consistent with Unix epoch seconds and `time` with local UTC+2 on 2026-10-20. These representations and stability were observed only in those two responses; uniqueness and future stability are not established.
- The two categories are distinct. Entries ascend within each category, but the combined XML order is not globally chronological. A T3 timeout has native `critical` priority.

**UNKNOWN:** Pagination, retention, whether 20 is a row cap, completeness, timestamp collisions, and reboot behavior remain unverified. No raw pasted XML, SID/sessionToken, sensitive address, or MAC value is retained in this report.

**PROPOSED design:** Retrieval remains optional and default-off, using the existing authenticated CH7465 driver session in the existing poll. Isolate retrieval/parse/storage failures from core polling. Begin any future validation offline with sanitized fixtures only. Preserve the raw event fields and add a UTC ingestion timestamp. For persistent deduplication, scope identity by device and category, fingerprint all raw fields, and account for identical-row multiplicity within a response; treat collisions and reboot behavior as unresolved, never as proof that `t` alone is unique. Keep notifications and Smart Capture out of scope.

**Changes:** Updated `docs/ARCHITECTURE.md` and appended this record. No application code, tests, modem access, or Git state changes were made.

**Tests:** None run, as requested; this was a documentation-only update.

**Next steps:** Review the design specification. Any implementation or live modem retrieval requires a later, explicit task and appropriate authorization.

## Step 4.11 — Offline regression coverage and documentation status

**Report date:** 2026-10-20

**Objective:** Complete synthetic, offline test coverage for the Step 4.9 CH7465ONE native-log implementation and accurately document its implementation and verification status. No live modem access or Git state changes were authorized or performed.

**Inspected baseline:** Step 4.9 application implementation and initial parser/storage tests were present in the checkout. The working tree already contained uncommitted application, test, and documentation changes; those were preserved. This report does not claim that those existing changes were created or verified in this step.

**Changes in this step:** Extended `tests/test_ch7465_native_events.py` with migration and generic-event acknowledgment preservation, backup/restore persistence and deduplication, forced fingerprint-collision detection, authenticated API access and page traversal, an explicit authentication-required case when global auth is unset, and expanded SID/sessionToken/password redaction assertions. The API test checks 200-row pagination and the current endpoint's rejection of `limit=999`; the storage cap itself is also covered by the pre-existing storage test. Updated the architecture record to describe the inspected implementation as present but not fully pytest-verified, while retaining the unknown modem completeness/retention semantics and the earlier proposal rationale.

**CI investigation:** The existing GitHub Actions `test.yml` configures Python 3.13 and installs both `requirements.txt` and `requirements-test.txt` with `pip install --require-hashes`, then invokes pytest. This is sufficient CI configuration for running the regression suite when the workflow is triggered. CI was not triggered or modified. Whether package-index access and the locked artifacts are available in a future run is not established here.

**Checks and results:** Python 3.13.5 compilation of the changed test module succeeded. `git diff --check` succeeded. Pytest was not run: neither the system Python nor the existing repository `.venv` contains pytest. No packages were installed and no dependency environment was modified. The migration/API/collision/backup/redaction assertions therefore remain unverified by execution. No concrete application behavior defect was established by this test/documentation task; no application code was changed.

**Next step:** Run the focused and full pytest suites in the existing Python 3.13 CI environment or an environment with the locked dependencies already available, then review the resulting evidence. This report stops for review.

## Step 4.14 — Built-in CH7465 driver resilience and archive/restore coverage

**Report date:** 2026-10-20

**Objective:** Implement the approved Option A built-in CH7465 native Network Log architecture with safe fallback to the standard CH7465 driver, add focused synthetic regression coverage, and exercise DOCSight's production backup/restore functions without touching user data or the modem.

**Verified registration path:** `ch7465` is discovered as a built-in module; its manifest contributes an exact-key `ch7465` driver; the application registration plan installs that driver into the per-app registry; configured modem type `ch7465` resolves the module driver ahead of the standard registry entry. The extension inherits the standard authentication and DOCSIS methods. Built-in module provenance is now carried into the driver registry.

**Changes:** The optional CH7465 driver contribution now degrades to the standard driver when its import or class validation fails, while built-in manifest validation remains strict. Constructor failure for this built-in extension falls back to the registered standard CH7465 driver. Community override precedence and classification remain unchanged. Static manifest contracts now recognize the CH7465 built-in driver. Regression coverage exercises built-in resolution, invalid/missing optional contribution fallback, constructor fallback, community classification, feature-off polling, retrieval failure isolation, session reuse, and production archive/restore persistence of original fields, categories, endpoint identity salt, and deduplication. Updated stale community-module wording and architecture documentation to record the selected built-in design.

**Checks and results:** `git diff --check` passed. Python AST parsing passed for all 18 changed Python files. The CH7465 built-in manifest contract validation passed. Offline smoke checks passed for normal module discovery and extended-driver selection, missing and incompatible contribution fallback, constructor failure fallback, default-off DOCSIS polling, retrieval-failure isolation, session reuse with the expected variant request data, and production archive/restore persistence including identity salt and repeated-snapshot deduplication. These smoke checks are not pytest. Pytest was unavailable in both `/usr/bin/python3` and the repository `.venv` (`No module named pytest`); no dependencies were installed. No live modem access, Git state operation, or GitHub Actions run was performed.

**Unresolved:** Live modem/firmware compatibility, native-log completeness, pagination, retention, and timestamp/identity behavior remain unverified. Built-in manifest validation intentionally remains fatal if the manifest itself is missing or invalid; only the optional driver contribution is tolerant.

## Step 4.21 — CI failure diagnosis and bounded corrections

**Report date:** 2026-10-20

**Objective:** Diagnose the first GitHub Actions run for the approved built-in CH7465 native-log implementation and correct confirmed regressions without changing the feature scope or weakening contracts.

**CI evidence:** Tests run [39478443513](https://github.com/lukumaki/docsight/actions/runs/39478443513) completed with failure. Ubuntu pytest reported 5,108 passed, 2 skipped, and 10 failed; Windows pytest reported 5,046 passed, 2 skipped, and the same 10 failures. The documentation job reported 58 passed and 2 failed. Mobile E2E passed. Python setup, dependency installation, workflow YAML validation, and actionlint passed. No live modem test was run.

**Root causes and corrections:** The built-in CH7465 driver was loaded through the community driver's isolated synthetic module namespace, so `isinstance` checks against the canonical built-in class failed. Built-in drivers now load by their canonical `app.modules` import; community driver isolation is unchanged. Registering the extension also replaced the standard CH7465 catalog display name and hints in an app-owned registry, which made fallback and isolation regressions fail; built-in extensions with a standard fallback now retain that catalog metadata while the registry still selects the extension implementation. The collision test replaced the shared SHA-256 function only after writing the original row, so the new row never shared its fingerprint; a dedicated fingerprint function is now monkeypatched before both writes, preserving and testing the production collision guard. The defensive scanner matched across a test assertion's quoted `sessionToken=` literal and a later synthetic password; the assertion now constructs that literal in two pieces, and scanner patterns remain unchanged. DOCSight's public product documentation contract requires Markdown user documentation in the Wiki and no Markdown under `docs/`; the project-specific architecture and history records were moved to `investigation/`, and the security scanner was extended to continue scanning that directory.

**Changes:** Updated built-in contribution loading and driver catalog metadata preservation; factored fingerprint generation behind a deterministic internal function; corrected the collision and scanner regression tests; moved the two project records from `docs/` to `investigation/`; updated README and AGENTS links/rules; and removed the `.gitignore` exceptions that previously allowed Markdown under `docs/`.

**Checks:** `git diff --check` passed. Python AST parsing passed for all six modified Python files, and the CH7465 manifest remained valid JSON. A local run of the repository's secret-pattern scan across `docs/`, `investigation/`, `tests/`, and root Markdown passed; the existing documentation-location contract also passed because `docs/` contains no Markdown files. Pytest could not be run locally: default Python 3.13.5 lacks pytest, Flask, and Werkzeug, and the existing repository `.venv` also lacks pytest. No dependencies were installed. GitHub CI results above are the pre-correction baseline and do not validate these changes. No files were staged, no commits were created, and nothing was pushed; no modem access occurred.

**Unresolved:** The corrected branch has not yet been rerun in CI. Live firmware compatibility, log completeness, pagination, retention, and modem timestamp interpretation remain unverified.

**Next step:** Complete local static checks, review the diff, then await approval before any staging, commit, push, or CI rerun.

## Step 4.27 — XML parser security hardening

**Report date:** 2026-10-20

**Objective:** Reject DTD and custom-entity XML declarations independent of UTF-8/UTF-16 encoding, while preserving legitimate CH7465 event parsing. This was an offline-only change; the modem and Git state were not accessed or modified.

**Root cause:** The previous check searched raw bytes for ASCII `<!DOCTYPE` and `<!ENTITY`. UTF-16 interleaves zero bytes, so those byte patterns did not match even though the XML parser accepted the declaration and expanded an internal entity.

**Changes:** `app/modules/ch7465/parser.py` now validates the bounded XML payload with Python's standard-library Expat parser before ElementTree builds the rows. Expat declaration callbacks reject DTDs, entity declarations, and external-entity callbacks; parameter-entity parsing is disabled. This recognizes XML encodings rather than depending on byte substrings. The existing 1 MiB limit, root/field behavior, and native text preservation remain. Synthetic parser regression cases cover DTD declarations in UTF-8 and UTF-16 LE/BE, internal and external entities, an undeclared entity reference, malformed/unexpected XML, predefined `&amp;`, both event categories, and exact raw field values.

**Tests and checks:** The installed Python is 3.13.5. Pytest and `defusedxml` are unavailable, and no dependencies were installed; therefore the pytest suite was not run. Standard-library direct parser checks, AST syntax checks, and `git diff --check` were run for this change; results are reported with this phase's completion response. No live modem test or CI run was performed.

**Local data permissions review:** Source inspection found no explicit restrictive mode for the SQLite database or its containing data directory; actual protection depends on the process umask and directory permissions. Config and key files are explicitly set to owner read/write. Backup archives and restore staging files use `mkstemp`'s owner-only mode, but the backup/data directories do not receive explicit permission enforcement. No actual database or backup contents or filesystem modes were inspected. This is a separate confirmed source-level hardening gap and was not changed in this parser-focused checkpoint.

**Unresolved risks:** Live firmware compatibility, native-log completeness/pagination, and timestamp semantics remain unverified. The test suite and CI have not exercised the new code yet. Existing database and directory permissions depend on deployment context.

**Next step:** Review the local diff and direct security checks, then obtain approval before staging, committing, pushing, or triggering CI.

## Step 4.33 — Sensitive configuration logging review

**Report date:** 2026-10-20

**Objective:** Remove unnecessary modem configuration and arbitrary error-detail exposure from the core CH7465 polling logs without changing authentication or connection behavior. This was an offline-only correction; no modem request, DOCSight startup, or test-data access occurred.

**Findings:** `app/main.py` logged the configured modem URL and username at polling-loop startup. The exact line is present in the PR base commit `04d0c7d5`, so it predates this feature branch. The core polling error paths also logged arbitrary modem exception/result text. `CH7465Driver.get_connection_info()` logged raw exception text, and an unrecognized login response was copied into the authentication exception message. These paths could propagate URL or modem-supplied details into diagnostics. The new CH7465 native-log path itself does not log raw event XML, SID, or `sessionToken` values.

**Changes:** Startup now logs a generic settings-loaded message while preserving the poll interval and selected driver diagnostics. Core modem polling failures log the error class only; non-modem collector diagnostics are unchanged. CH7465 connection-info failures log the exception class only, and unrecognized login responses use a fixed generic message while known safe firmware errors remain readable. Added synthetic tests for startup configuration redaction, polling exception redaction, CH7465 connection-info error logging, and unexpected authentication responses.

**Additional review note:** The bounded source scan found separate session-related or raw exception diagnostics in other modem-driver implementations, including `app/drivers/ultrahub7.py` and `app/drivers/sagemcom.py`. Those drivers are outside this correction and were not changed; a broader logging audit remains a separate task.

**Tests and checks:** Pytest is unavailable in both the repository virtual environment and system Python, and no dependencies were installed. Python AST syntax checks passed for the modified source and test files. Direct synthetic smoke checks passed for startup-log redaction, both core modem error-log paths, an unexpected authentication response, and CH7465 connection-info error logging; they made no network requests. The repository's documentation/fixture secret-pattern scan passed across 449 candidates, and `git diff --check` passed. The pytest regression cases and CI remain unverified.

**Unresolved:** The test suite and GitHub Actions have not verified this correction. The separate driver logging paths noted above remain for review. Live modem compatibility and behavior were not retested.

**Next step:** Review the local diff and checks, then await separate approval before any Git staging, commit, push, or CI run.

## Step 4.50 — Authentic legacy-database migration regression test

**Report date:** 2026-10-21

**Objective:** Correct the native-event migration regression test so it upgrades an authentic pre-native-log schema containing existing synthetic event data, without changing production migrations or behavior.

**Verified defect and baseline:** The previous test ran the first five migrations, then constructed current `SnapshotStorage` before inserting its legacy event. That constructor already applied the native migration, so preservation of pre-upgrade event data was not exercised. Development baseline `04d0c7d5342e79a8d4cf3ebaf504c8a26ed112a5` has the same storage schema and migration source as its official-upstream parent `84d2ba24f651f030c43444c501fcd7059ff5a862`. Source/AST comparison confirmed that the baseline schema and original migration helper functions remain unchanged. The authentic legacy state has core migration stamps 0001 through 0005, `schema_version` equal to `2`, and `events.is_demo`, but no native-event tables or indexes.

**Changes:** Reworked the existing test in `tests/test_ch7465_native_events.py` to build that state using the existing legacy migration sequence, insert two synthetic events directly through SQLite, and verify all preconditions before the first current `SnapshotStorage` construction. Assertions preserve all event fields, explicit IDs, acknowledgment/demo flags, JSON/NULL details, Unicode text, event column definitions and prior migration timestamps; verify both native tables and each named index's columns/uniqueness; and verify the current migration registry and schema-version metadata. The existing synthetic native insert remains. Reopening is checked using the existing schema/data digest helpers, native-row equality, unchanged registry stamps, an empty pending-migration result and SQLite integrity checking. Updated the project README status and architecture verification record. No production source was changed.

**Validation:** Direct execution of the corrected test function passed using the actual production storage, parser and migration helpers against a temporary database under `/tmp`. Network socket creation was blocked during execution, and the temporary database was removed afterward. The function and its synthetic XML fixture were selected from the test AST to avoid importing pytest or starting an application. This is not pytest execution. Python AST checks and `git diff --check` passed. Pytest is unavailable in both system Python and the repository virtual environment; no dependencies were installed and no CI was triggered.

**Findings and unresolved issues:** No production migration defect was demonstrated. Focused pytest execution and independent review remain pending. The native-log total-deadline limitation and browser-validator failure are separate, unchanged issues; this checkpoint did not test or modify either.

**Safety and next step:** No modem access, DOCSight startup, private test-database access, Git mutation, PR update or publication occurred. Review the focused test/documentation diff; await explicit approval before staging, committing, pushing or triggering CI.

## Step 4.52 — Migration-test connection cleanup and legacy index preservation

**Report date:** 2026-10-21

**Objective and preconditions:** Implement only the two test-quality improvements identified in Step 4.51. Verified branch `ch7465one-native-log-ci`, HEAD `930a0cf6819bd97b6fb127098fc0379677d77c4d`, exactly the four expected unstaged modifications, and no staged or untracked files. The complete working diff matched the reviewed Step 4.51 snapshot before editing.

**Changes:** In the existing migration test, wrap each direct SQLite connection with `contextlib.closing` outside its transaction context, preserving commit/rollback before close. Apply the same cleanup to `schema_digest()` and `data_digest()` in `tests/sqlite_helpers.py`; their query and digest behavior is unchanged. Capture all non-internal named legacy indexes before current storage initialization and compare their names, table associations, ordered columns, uniqueness properties and normalized SQL immediately after the real migration. Keep all prior legacy-data, migration-stamp, native-index, reopening and integrity checks intact. Updated README and architecture verification notes. No production code or unrelated test function was changed; the supporting digest-helper file is the fifth modified file.

**Validation:** The hardened test function passed by direct execution against production storage, migration and parser code using a temporary synthetic SQLite database. Socket creation was blocked, and connection instrumentation retained references to every opened connection: all 30 were explicitly closed, none had a pending transaction at close, and each rejected subsequent SQL. The temporary directory was cleaned up. Python AST checks, static index/connection-lifecycle review and `git diff --check` passed. Pytest remains unavailable in both checked environments; no dependency installation or CI execution occurred. This is direct-function verification, not pytest or Windows runtime verification.

**Findings and compatibility:** No production migration defect was demonstrated. Metadata queries, identifier quoting and standard-library context managers are portable to the existing Python 3.13 Ubuntu/Windows lanes; actual CI execution remains pending. The native-log deadline and browser-validator issues are unchanged and outside this checkpoint.

**Safety and next step:** No modem access, DOCSight startup, private test-database access, production migration/storage edit, Git mutation, PR change or CI trigger occurred. The test/helper and documentation changes are ready for review and separately authorized commit/CI. Await explicit approval before staging, committing, pushing or publishing.

## Step 4.54 — Minimal stored Native Network Log viewer

**Report date:** 2026-10-21

**Objective and preconditions:** Add a read-only viewer using the existing authenticated API and frontend conventions. Verified branch `ch7465one-native-log-ci`, HEAD `9f651aed6c4a7aba90b3202ada41358cdd2f4ae2`, and a clean working tree before editing. Read AGENTS.md and inspected navigation, generic module routing, templates, shared table styling, authentication, native-event storage/API pagination and existing frontend tests. Step 4.53's successful Tests run 39621701528 verified the preceding migration-test commit; its outcome does not cover the new viewer.

**Changes:** Extend only the CH7465 module's existing manifest with tab/static/i18n contributions and a Cases navigation item labeled Native Network Log. Add a tab template, small scoped stylesheet, module script and English strings with the existing fallback mechanism. Dashboard rendering supplies a boolean notice value; no sensitive configuration is added. Read raw modem time, priority, full event text and System/Wi-Fi category from stored rows only. First entry loads a bounded 100-row page; manual Refresh returns to newest rows, and Older events follows `next_before_id` as `before_id`. Pages replace one another. Provide empty/error/end-of-history messages, disabled-collection and required-authentication notices, busy controls and a 15-second request-abort timeout. There is no automatic refresh interval. Render all modem fields with textContent, retain the raw time without conversion, wrap complete descriptions, reject redirects/malformed responses, and never display or log error bodies or arbitrary exception text.

**Tests added:** Five Flask tests cover dashboard/API authentication, module navigation/assets, disabled collection and no-password modes, the existing read-only cursor API and module disabling. Twelve JavaScript viewer tests cover lazy activation, complete untrusted text, both categories, raw time, pagination/Refresh, empty states, HTTP/auth/network/JSON failures, invalid responses/cursors, base-path API usage, request timeout and concurrent controls. One test in the existing module-view suite verifies the actual generic deep-link hook. Existing test functions were preserved.

**Validation:** All five new Flask test functions passed by direct execution against a factory-created Flask test client, temporary synthetic configuration and mocked read-only storage, with socket creation blocked. No server, collector or monitoring loop was started. Pytest is unavailable in both checked Python environments; the direct execution is not pytest. On the installed bundled Node 24 runtime, the viewer, module-view and URL-contract suites passed all 32 tests. An initial routing-test fixture lacked an existing dashboard theme element; the fixture was corrected without changing routing/application behavior, and the routing suite passed. Fifteen additional synthetic Playwright/Chrome checks passed for the rendered tab using existing styles: literal text/no HTML execution, raw time, disabled notice, desktop/mobile layout, pagination, Refresh, empty/error states, no sensitive console markers, only approved synthetic requests and completed browser shutdown. Interception was installed before page creation; every approved response was fulfilled offline, and all other traffic/WebSockets were denied. Artifacts are under `/tmp/docsight-step454-browser-zk6nev67/`. AST/JSON, JavaScript syntax, manifest validation and diff checks passed.

**Compatibility and unresolved issues:** Uses the existing module/static/i18n and responsive table components; adds no dependency or framework. English module strings fall back through the existing mechanism; additional translations are not included. This change has no pytest, CI, Windows runtime or live modem verification. The separate native-read deadline and earlier browser-guard issues were not changed or revalidated by this viewer checkpoint.

**Safety and next step:** Native retrieval, deduplication, retention, schema/migrations, event API contracts, modem authentication, scheduling, normal DOCSIS monitoring/analysis/snapshots and existing event flows remain unchanged. No modem access, private live-test database access, ongoing DOCSight monitoring, dependency installation, Git mutation, PR change or CI trigger occurred. Review this local diff and await explicit approval before publication.
