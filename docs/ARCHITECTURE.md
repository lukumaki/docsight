# DOCSight CH7465ONE Integration Architecture

This document records the current technical model for integrating the Hungarian ONE Compal CH7465ONE's native Network Log with DOCSight. It applies to the firmware investigated in this project, `CH7465ONE-NCIP-6.15.20.5-3-SH`, and must not be read as a compatibility claim for other firmware builds.

## Evidence labels

- **Verified in source:** confirmed by inspection of the DOCSight checkout at `84d2ba24f651f030c43444c501fcd7059ff5a862`.
- **User-confirmed capture:** observed during the approved read-only modem UI capture and reported by the user.
- **Proposed:** a design recommendation, not implemented or accepted upstream.
- **Unresolved:** evidence is insufficient for a reliable conclusion.

## Current verified model

### Modem endpoint and response

**User-confirmed capture:** Opening the modem's Network Log page triggers `POST /xml/getter.xml` with form field `fun=13`. The XML response contains `eventlog_table` and repeated `eventlog` elements. The observed fields are `prior`, `text`, `time`, and `t`. The modem limits or presents a rolling set of 20 records in the captured response. The modem restricts simultaneous administration sessions.

**Unresolved:** The timezone represented by `time`, the meaning/stability of `t`, severity mapping for `prior`, and pagination/retention behavior beyond the observed response have not been verified. Until then preserve the raw field values, keep `t` opaque, and do not make timezone or severity assumptions.

### DOCSight driver and poll lifecycle

**Verified in source:** `app/drivers/ch7465.py` owns the CH7465 `requests.Session` and handles login and authenticated XML requests. The standard driver currently implements signal/device retrieval, not vendor Network Log retrieval. `app/drivers/base.py` defines the required driver methods and has no modem-event API.

**Verified in source:** `app/collectors/modem.py` calls `login()` on its driver and then obtains device and DOCSIS data from that driver instance. This is the existing owner of the modem authentication session and is the appropriate place to coordinate an optional Network Log request.

### Community modules and session sharing

**Verified in source and module documentation:** A community module can replace a built-in modem driver using the exact driver key. The driver implementation is selected through the application driver registry. The module driver contract requires login, DOCSIS data, device info, and connection info.

A separate community collector is independently scheduled and is not given the core modem driver/session through its constructor. Its collect lock is separate from the core modem collector's lock. The community contract also disallows combining a driver contribution and collector contribution in one module. Therefore, a standalone community collector cannot use the existing authenticated session through a supported API; logging in independently conflicts with the modem's exclusive-session constraint.

### Event storage and Smart Capture

**Verified in source:** DOCSight's generic event table and APIs can store/display event records. The current schema has no generic idempotency/source key for Network Log rows, so repeated polling would need storage support to deduplicate persistently. `save_events_with_ids()` makes event IDs available to Smart Capture-oriented collectors.

**Verified in source:** In the inspected checkout, Smart Capture is explicitly wired in `app/main.py` to the Connection Monitor collector. The generic module collector construction in `app/collectors/__init__.py` does not inject the Smart Capture engine into community collectors.

## Proposed architecture

Use a **community CH7465 driver override plus minimal upstream core support**:

1. The community override for key `ch7465` subclasses or otherwise preserves the standard CH7465 authentication/session behavior and implements an optional event-retrieval method issuing `fun=13` over the existing authenticated session.
2. The core `ModemCollector` invokes the optional method during its existing poll, after successful acquisition of core signal data. The invocation must not re-login or instantiate another session.
3. The core catches Network Log request/parse failures locally so ordinary signal monitoring continues.
4. The core storage path persists standard DOCSight events with original modem fields in details and a stable, unique source key (or equivalent idempotent storage mechanism) so repeated 20-entry responses and restarts do not duplicate rows.
5. Add Smart Capture integration only if desired and after event semantics are validated. It should be a generic, explicit core hook rather than a module reaching into private runtime state.

This proposal is not implemented. It preserves the built-in `CH7465Driver` source and allows its normal behavior to remain the fallback when the community override is disabled, subject to verifying the behavior of the DOCSight release selected for implementation.

## OpenWrt deployment track (Phase 5, proposed)

Added 2026-11-22. This track exists because the CH7465ONE is currently unavailable for testing. It does not replace or invalidate the CH7465ONE model above. Evidence labels are as defined at the top of this document, plus **User-reported** for details the user supplied from their own router.

**Verified in source:** DOCSight has no OpenWrt-specific code. The generic driver (`app/drivers/generic.py`) returns empty but valid DOCSIS data, so modem-independent modules (Connection Monitor, Speedtest, Journal, reports) work without a modem. The Speedtest module only reads results from an external Speedtest Tracker instance; it does not run tests. The Connection Monitor probes with ICMP/TCP from the DOCSight process. The official image is built for `linux/amd64`, `linux/arm64`, and `linux/arm/v7`.

**Verified (module documentation):** The driver data contract is DOCSIS-shaped. DSL or fiber line statistics need a core change, not a community driver. A driver module cannot also contribute a collector. `udm-wan-monitor` in `docsight-modules` is a precedent for an `integration` module that records router WAN status as DOCSight events.

**User-reported (router survey, read-only commands run by the user):** The target host is OpenWrt 25.12.6, x86/64, about 5.5 GB RAM, Docker 29.6.1 with compose installed, Docker data on a separate 108.5 GB volume with 96.1 GB free, and a 1 GB root partition. WAN is PPPoE on `eth4`. TCP port 8765 is free. These values are a point-in-time snapshot.

**Proposed deployment (not implemented):**

1. DOCSight in Docker on the router, Generic Router mode, data on the large volume, port published on the LAN address only, `NET_RAW` capability retained for probes.
2. Speedtest Tracker as a second container only after its resource use is measured. Its default web port must not be 80 (LuCI). DOCSight reaches it by LAN address and API token.
3. A community `integration` module, the **OpenWrt WAN monitor**, that polls the router's interface status and records PPPoE reconnects (uptime reset, up/down transitions) as DOCSight events. It must use a read-only account on the router and must not change router configuration. Whether the router's interface status is sufficient for reliable reconnect detection is **Unresolved**.

**Trade-offs and limits:** A monitor hosted on the router observes WAN drops but cannot observe the router itself failing. Speed tests on the router also exercise the router's own PPPoE processing, so a low result needs router load checked before it is attributed to the ISP (**Assumption**). Resource use of DOCSight and Speedtest Tracker on this hardware is **Unresolved** until measured.

**Prior art (public pages read, code not audited):** `chaffed/luci-app-modemhealth` is an OpenWrt package with the same evidence goal for Arris SURFboard S33/S34 cable modems. It is a possible collaboration target or reference design for session handling and event de-duplication, not a dependency.

### WAN-monitor reference design and speed-test options (Phase 6, proposed)

Added 2026-11-22. Evidence labels as above; **Verified (public source read)** means a public repository file was read but not executed.

**Verified (public source read) — `udm-wan-monitor` v3.3.4:** The collector keeps a cached authenticated session behind a lock, polls on a 60 s default interval, and detects changes against an in-memory last-seen state; the first poll after a start only sets the baseline. Events go through `save_event()` with a module-specific event type and severity (`critical` down, `info` restored, `warning` failover). The password is a module-owned secret. Routes are protected with `@require_auth`. Limits relevant to a copy for OpenWrt: state is lost on restart, drops between polls are invisible, and the WAN IP is placed in event text and details.

**Proposed design for an OpenWrt WAN monitor:**

1. Sibling `integration` module with its own config prefix, routes, and event type; no shared code with `udm-wan-monitor`.
2. Detect reconnects from the WAN interface's down/up transition **and** from an interface uptime lower than expected since the previous poll. The availability of these values through the router's web API on the target firmware is **Unresolved** until checked with read-only calls.
3. Persist last-seen state only if upstream confirms a supported mechanism (open question in the draft upstream post).
4. Omit public IP addresses from event text by default.
5. Avoid imports outside the supported community list (`require_auth`, `get_config_manager`, `get_storage`, `get_state`, `get_module_loader`) and avoid relative imports in the routes file.

**Speed-test options on the target router (Proposed; trade-offs only):**

| Option | Integration with DOCSight | Weight on router | Notes |
|---|---|---|---|
| Speedtest Tracker container | Supported by DOCSight's Speedtest module (URL + token) | A second container; resource use **Unresolved** | Needs a non-80 host port on this router |
| ISPy (`chaffed/luci-app-ispy`) | None today | Shell + `curl` package, no container | Own history and report; author-reported ~1.4 GB per test at 1 Gbit/s; built-in engine fits lines up to about 300 Mbit/s |
| `muink`/`sirpdboy` netspeedtest apps | None | Python-based or Ookla CLI dependencies | Interactive diagnostics, no evidence log described |

A DOCSight-side bridge that reads ISPy results (its CSV format or ubus API) is a possible later idea and has not been evaluated. Speed tests that run on the router exercise the router's own CPU and PPPoE handling; ISPy records CPU load per test for this reason (author-reported).

## Source map

- `app/drivers/ch7465.py` — CH7465 authentication and HTTP session ownership.
- `app/drivers/base.py` — modem driver interface.
- `app/drivers/registry.py`, `app/module_contributions.py`, `app/registration.py` — community driver resolution and registration.
- `app/collectors/modem.py` — core modem polling lifecycle.
- `app/collectors/__init__.py`, `app/collectors/base.py`, `app/main.py` — module collector construction and scheduling.
- `app/storage/schema.py`, `app/storage/events.py`, `app/storage/migrations.py` — event schema, writes, and migrations.
- `app/smart_capture/engine.py`, `app/main.py` — event evaluation and current Smart Capture wiring.
- `docs/PROJECT_LOG.md` — phase chronology and status.
- Workspace-level historical reports, currently outside this Git clone: `PHASE4_DOCSIGHT_FORK_AUDIT.md` and `STEP2_GIT_CONNECTION_AUDIT.md`.
