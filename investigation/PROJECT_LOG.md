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
