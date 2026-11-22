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
