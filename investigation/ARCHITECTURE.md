# DOCSight CH7465ONE Integration Architecture

This document records the current technical model for integrating the Hungarian ONE Compal CH7465ONE's native Network Log with DOCSight. It applies to the firmware investigated in this project, `CH7465ONE-NCIP-6.15.20.5-3-SH`, and must not be read as a compatibility claim for other firmware builds.

## Evidence labels

- **VERIFIED (in source):** confirmed by inspection of the current local source. Source inspection is distinct from automated test verification.
- **OBSERVED:** present in the user's manual, read-only DevTools captures on the investigated modem/firmware; not a general firmware guarantee.
- **PROPOSED:** a design recommendation, not implemented or accepted upstream.
- **UNKNOWN:** evidence is insufficient for a reliable conclusion.

## Current verified model

### Modem endpoint and response

**OBSERVED:** Opening the Network Log page triggers `POST /xml/getter.xml` with form field `fun=13`. The XML root is `eventlog_table`. A response has 20 `eventlog` elements and 2 `wifieventlog` elements; each has `prior`, `text`, `time`, and `t`. Two successive responses were exactly identical in entries and order. The `eventlog` and `wifieventlog` categories are distinct; entries ascend by time within each category, while the combined XML is not globally chronological. A T3 timeout entry is reported with native `critical` priority. Do not merge the categories or infer a total chronological order from document order.

**OBSERVED:** For these two observations on 2026-10-20, `t` values are consistent with Unix epoch seconds and the displayed `time` values are consistent with local time at UTC+2. The values remained stable across these two identical responses. This does not establish that `t` is always unique, immutable, or stable across reboot, clock adjustment, or log replacement. Preserve original `prior`, `text`, `time`, and `t`; retain an ingestion timestamp separately in UTC.

**UNKNOWN:** Whether retrieval is paginated; retention and completeness; whether 20 `eventlog` rows is a cap or merely the observed response size; collision behavior; and behavior across reboot. No claim is made beyond the captured responses. Severity semantics beyond the observed native T3 priority are also unknown. The modem restricts simultaneous administration sessions, so any future retrieval must reuse the existing authenticated session.

### DOCSight driver and poll lifecycle

**Verified in source:** `app/drivers/ch7465.py` owns the CH7465 `requests.Session` and handles login and authenticated XML requests. The standard driver currently implements signal/device retrieval, not vendor Network Log retrieval. `app/drivers/base.py` defines the required driver methods and has no modem-event API.

**Verified in source:** `app/collectors/modem.py` calls `login()` on its driver and then obtains device and DOCSIS data from that driver instance. This is the existing owner of the modem authentication session and is the appropriate place to coordinate an optional Network Log request.

### Built-in CH7465 module and session sharing

**VERIFIED in source:** The approved architecture is Option A: the CH7465 native-log extension is a built-in DOCSight module under `app/modules/ch7465/`, listed in `app/builtin_modules.py`. Its manifest contributes a driver under the exact `ch7465` key. The application module loader resolves it into the per-app driver registry, where module drivers take precedence over the standard driver for that key. The extension subclasses the standard `CH7465Driver`, so login and ordinary DOCSIS methods remain inherited.

The collector calls the optional native-log method only when `ch7465_network_log_enabled` is true, and it uses the driver instance already used for DOCSIS polling. It does not create another login or polling schedule. Failures from the optional fetch or native-event storage are isolated from the normal DOCSIS collection path.

**VERIFIED implementation correction in this phase:** CH7465 driver contribution import or class-validation failure now omits only that optional override while keeping the standard driver registered. If the extension constructor fails, the per-app driver registry falls back to the standard CH7465 driver. Built-in module provenance is retained for driver classification; community overrides remain classified as community drivers. Built-in manifest discovery remains strict. The built-in CH7465 implementation uses its canonical Python import so module/type identity is stable; isolated dynamic imports remain in place for community drivers. The extension retains the existing standard CH7465 display name and hints in the application-owned registry.

**Historical design note:** Earlier Phase 4 analysis proposed a community driver override plus minimal core support. The user subsequently selected the built-in DOCSight module architecture. The standalone community-collector limitation remains true, but is no longer the selected architecture.

### Event storage and Smart Capture

**Verified in source:** DOCSight's generic event table and APIs can store/display event records. The current schema has no generic idempotency/source key for Network Log rows, so repeated polling would need storage support to deduplicate persistently. `save_events_with_ids()` makes event IDs available to Smart Capture-oriented collectors.

**Verified in source:** In the inspected checkout, Smart Capture is explicitly wired in `app/main.py` to the Connection Monitor collector. The generic module collector construction in `app/collectors/__init__.py` does not inject the Smart Capture engine into community collectors.

## Implemented integration status (source inspection)

**VERIFIED by source inspection in this checkout:** Step 4.9 integration and the Step 4.14 resilience changes are present. Retrieval is controlled by `ch7465_network_log_enabled` and defaults off. The built-in `ch7465` module driver subclasses the existing driver and fetches `fun=13` using its authenticated session; streamed XML is bounded to 1 MiB and parsed into separate `eventlog` and `wifieventlog` rows while preserving the native fields.

The optional collector hook runs in the existing poll and isolates fetch/storage exceptions. Native rows use dedicated SQLite tables, endpoint-scoped salted HMAC identity, a versioned category-aware fingerprint with duplicate occurrence ordinals and collision checking, and `history_days` retention. The authenticated `GET /api/modem-native-events` endpoint is read-only and caps returned pages at 200 records. Native rows are not routed through generic DOCSight events, acknowledgments, notifications, or Smart Capture. CH7465 logging redacts SID and `sessionToken` values.

**Verification boundary:** Source inspection and static checks are not pytest verification. The regression suite includes registration/fallback, poll isolation, session reuse, migration, API authorization/pagination, collision, retention, and production archive/restore cases. The first remote CI run and its failures are recorded in Step 4.21 of the investigation log. No live modem verification was performed; firmware compatibility and log completeness remain unverified.

The design below records the original community-module proposal and rationale as historical context. It is superseded by the approved built-in architecture above; unresolved modem behavior and the requirement to use synthetic offline fixtures remain applicable.

## Original proposed architecture

The earlier **community CH7465 driver override plus minimal upstream core support** proposal was superseded by the user's selection of the built-in module architecture. Its technical rationale is retained here as historical context:

1. An explicit configuration setting controls retrieval and defaults to off. When enabled, the `ch7465` extension preserves the standard authentication/session behavior and issues `fun=13` through that already-authenticated session.
2. The core `ModemCollector` invokes the optional method during its existing poll, after successful acquisition of core signal data. It must not re-login, create another session, or run an independent schedule.
3. The core catches Network Log request/parse/storage failures locally so ordinary signal monitoring continues; these failures must not be reported as core polling failures.
4. Initially test parsing and deduplication offline with sanitized fixtures only. Fixtures must be synthetic or irreversibly redacted and contain no pasted raw XML, credentials, SID/sessionToken values, personal addresses, or MAC addresses. No automated or live modem test is part of this documentation phase.
5. Preserve the category (`eventlog` versus `wifieventlog`) and device scope as independent identity dimensions. A proposed persistent identity is a deterministic fingerprint over device scope, category, and the exact raw `prior`, `text`, `time`, and `t` values, plus an occurrence ordinal among identical rows in one category/response. Retain raw values alongside the key, and record a separate UTC ingestion timestamp. This makes unchanged repeated snapshots idempotent while preserving identical rows within one response. It is still **PROPOSED**: `t` collisions and reboot behavior are unknown, so do not assume the fingerprint is globally unique; preserve collision evidence and avoid destructive merges. Confirm schema and retention behavior before implementation.
6. Do not connect these events to notifications or Smart Capture. Any later request would require a separate design decision after event semantics and false-positive behavior are validated.

Authentication/session material must never be persisted or logged: redact SID and `sessionToken` fields from diagnostics and examples. Redact sensitive addresses, including IP and MAC values, from stored fixtures, reports, and logs. This specification contains no raw pasted XML or personal address/MAC values.

The proposal was implemented in Step 4.9 as described above. The integration remains default-off. The implementation and its failure isolation still require the focused regression suite and normal CI verification; this project has not established completeness or retention behavior of the modem's log.

## Source map

- `app/drivers/ch7465.py` — CH7465 authentication and HTTP session ownership.
- `app/drivers/base.py` — modem driver interface.
- `app/builtin_modules.py`, `app/module_registry.py`, `app/module_contributions.py`, `app/registration.py`, `app/drivers/registry.py` — built-in module discovery, driver contribution resolution, registration, provenance, and fallback.
- `app/collectors/modem.py` — core modem polling lifecycle.
- `app/collectors/__init__.py`, `app/collectors/base.py`, `app/main.py` — module collector construction and scheduling.
- `app/storage/schema.py`, `app/storage/events.py`, `app/storage/migrations.py` — event schema, writes, and migrations.
- `app/smart_capture/engine.py`, `app/main.py` — event evaluation and current Smart Capture wiring.
- `investigation/PROJECT_LOG.md` — phase chronology and status.
- Workspace-level historical reports, currently outside this Git clone: `PHASE4_DOCSIGHT_FORK_AUDIT.md` and `STEP2_GIT_CONNECTION_AUDIT.md`.
