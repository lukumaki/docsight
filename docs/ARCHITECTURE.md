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
