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

## Phase 5 — OpenWrt feasibility research, router survey, and Speedtest Tracker research

**Report date:** 2026-11-22

**Environment:** Documentation and research were done in a cloud session on branch `lukumaki/inspiring-meitner-y7wb3g` (HEAD `8380b81` when this report was written). The cloud session cannot reach the user's LAN. All router information below was produced by read-only commands the user ran locally and pasted. The assistant did not connect to the router, the modem, or any container.

**Objective:** Decide whether this project can continue without access to a CH7465ONE, by assessing whether DOCSight can be adapted for OpenWrt and for non-cable connections (fiber, DSL, mobile), and by establishing what the user's own OpenWrt router can host.

**Findings:**

- **User-reported:** The user has no access to a CH7465ONE. The CH7465ONE Network Log track (Phases 1–4) is blocked, not abandoned; nothing in those phases is invalidated.
- **User-reported:** Many OpenWrt users sit behind ISP-locked modems that cannot run OpenWrt, so an OpenWrt router cannot read the line's modem status. The user has a fiber (PPPoE) connection and is interested in automated speed/latency checks that document line stability.
- **Verified (public pages read, code not audited):** An OpenWrt project with the same goal exists: `chaffed/luci-app-modemhealth` ("Modem Health"). Its issue #1 spec describes polling a cable modem every few minutes from an OpenWrt/GL.iNet router, de-duplicating the modem event log, pinging the modem and the internet, and generating an ISP evidence report. The author's comment states v1.0.0 was delivered on 2026-11-20 and tested on one setup (Arris SURFboard S34). Only SURFboard S33/S34 are supported; the S33 is untested. Its sibling ISPy (`chaffed/luci-app-ispy`) was referenced but not inspected.
- **Verified (search results, not audited):** Generic OpenWrt monitoring (`luci-app-statistics`/collectd ping, Prometheus node exporter, community Grafana dashboards) exists and records ping/loss but not DOCSIS signal data. Other modem-stat scrapers (`msh100/modem-stats`, `arris-tg3442de-exporter`, `vodafone-station-cli`) exist; none was found that targets the CH7465ONE or runs as an OpenWrt package.
- **Verified in this checkout:** There are no OpenWrt references. `app/drivers/generic.py` is a no-op driver returning empty valid data so modem-independent features work standalone. The Speedtest module (`app/modules/speedtest/manifest.json`) does not run speed tests; it reads results from a separate Speedtest Tracker instance via URL and token. The Connection Monitor module does ICMP/TCP probing inside DOCSight (manifest defaults: poll interval 5000 ms, TCP port 443, outage threshold 5, loss warning 2.0%). `docker-compose.yml` publishes port 8765 and adds the `NET_RAW` capability. `.github/workflows/docker.yml` builds `linux/amd64`, `linux/arm64`, and `linux/arm/v7`.
- **Verified (DOCSight wiki and docsight-modules, read 2026-11-22):** The driver data contract is DOCSIS-shaped (channels, power, SNR, modulation), so DSL or fiber line statistics would not fit a community driver without core changes. A driver module cannot also contribute a collector. `udm-wan-monitor` is an existing `integration` module that collects WAN status from Ubiquiti routers and feeds DOCSight events; it is the closest pattern for an OpenWrt WAN monitor. The wiki asks contributors to open an issue to discuss new driver ideas first.
- **User-reported (pasted command output):** The user's OpenWrt router is OpenWrt 25.12.6 `r33311-981c978eff`, target `x86/64`, kernel 6.12.112, board `msi-ms-7865`, ext4 rootfs. Memory total is about 5.5 GB (5,521,960 kB) with about 4.9 GB available and no swap; this suggests the planned 6 GB upgrade from the earlier hardware profile is installed (inference). `/` is 1006.8 MB with 587.9 MB free. `/mnt/storage` (108.5 GB, 96.1 GB free) holds the Docker data root. `/mnt/nas` is 88% used. Docker 29.6.1, containerd 2.2.5, docker-compose 5.1.4, and `luci-app-dockerman` are installed. WAN is up with `proto pppoe` on `eth4`, interface uptime 28,764 s at survey time. Four unrelated containers are running. No process listens on TCP port 8765.
- **User-reported:** Key-based SSH to the router was set up through LuCI, and the user's test command returned `ubus call system board` output. Removal of the older authorized keys and the absence of a password prompt were not confirmed in this session. No key material, password, or session identifier is recorded here.
- **Speedtest Tracker research (public documentation):** It is supported only as a container (image built by LinuxServer.io) or on NAS platforms. Scheduling uses `SPEEDTEST_SCHEDULE` (cron); old results can be pruned with `PRUNE_RESULTS_OLDER_THAN`. No official CPU or memory figures were found (**Unresolved**). GitHub issue #1316 reports multi-second page loads on Proxmox LXC and a Raspberry Pi 4; the maintainer attributed the original case to LXC performance. The default web port 80 would conflict with LuCI on this router, so a different host port is needed. **Assumption:** a full-speed test can move several GB per run on a gigabit line, so schedule frequency should be chosen deliberately.

**Proposed (not implemented, not approved):**

1. Run DOCSight in Docker on the OpenWrt router in Generic Router mode (data under `/mnt/storage/docsight`, port bound to the LAN address) and use its Connection Monitor for latency and outage evidence.
2. Optionally add Speedtest Tracker as a second container, after measuring resource use on this router.
3. Develop an OpenWrt WAN-monitor `integration` module for the community catalog, modeled on `udm-wan-monitor`, using the router's interface status (up/uptime) to record PPPoE reconnects as DOCSight events. Open an upstream issue before building it.

**Changes:** Documentation only (`docs/PROJECT_LOG.md`, `docs/ARCHITECTURE.md`, `README.md`). No DOCSight source, no router configuration, no containers, and no Git state were changed by the assistant.

**Tests:** None run. No DOCSight, Speedtest Tracker, or module tests were executed. Router commands were read-only and run by the user; their output is reported, not independently reproduced.

**Unresolved issues:** Actual CPU/memory cost of DOCSight and Speedtest Tracker on this router; how much PPPoE history `logread` retains; whether the OpenWrt interface status exposes enough to detect reconnects reliably; whether upstream wants an OpenWrt WAN monitor; whether the router CPU limits PPPoE throughput during tests; the line's contracted speed (needed to size test traffic); whether the older SSH keys were removed.

**Next steps:** Decide whether to deploy DOCSight in Docker on the router (explicit approval required before any container or configuration change). Measure resource use with `docker stats` after deployment. Inspect `udm-wan-monitor` source and the module TEMPLATE before drafting an OpenWrt module. Open an upstream discussion issue. Keep the CH7465ONE track paused until a device is available.
