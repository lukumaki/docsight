"""Modem collector -- DOCSIS data, analysis, events, MQTT, storage."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from .base import Collector, CollectorResult
from ..analyzer import (
    _recent_spike_active,
    apply_cumulative_error_baseline,
    apply_spike_suppression,
)
from ..gaming_index import compute_gaming_index
from ..types import ConnectionInfo, DeviceInfo

log = logging.getLogger("docsis.collector.modem")


@dataclass(frozen=True)
class NativeLogTelemetry:
    """Aggregate-only outcome for one optional native-log attempt."""

    outcome: Literal[
        "success",
        "empty",
        "retrieval_failed",
        "invalid_response",
        "storage_failed",
        "unsupported",
    ]
    returned_system: int | None = None
    returned_wifi: int | None = None
    inserted: int | None = None
    duplicates: int | None = None

    def emit(self) -> None:
        values = (
            self.outcome,
            *(
                "unknown" if value is None else value
                for value in (
                    self.returned_system,
                    self.returned_wifi,
                    self.inserted,
                    self.duplicates,
                )
            ),
        )
        message = (
            "Optional CH7465 native Network Log: outcome=%s "
            "returned_system=%s returned_wifi=%s inserted=%s duplicates=%s"
        )
        if self.outcome in {
            "retrieval_failed",
            "invalid_response",
            "storage_failed",
            "unsupported",
        }:
            log.warning(message, *values)
        else:
            log.info(message, *values)


def format_uptime(seconds: int) -> str:
    """Format uptime seconds into a human-readable string: Xd Yh Zm."""
    if seconds is None:
        return "unknown"

    days = seconds // (24 * 3600)
    seconds %= (24 * 3600)
    hours = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60

    return f"{days}d {hours}h {minutes}m"


class ModemCollector(Collector):
    """Collects DOCSIS data from a modem driver, runs analysis, detects events,
    publishes to MQTT, and stores snapshots."""

    name = "modem"

    def __init__(
        self, driver, analyzer_fn, event_detector, storage, mqtt_pub, web,
        poll_interval, notifier=None, smart_capture=None, native_events_enabled=False,
    ):
        super().__init__(poll_interval)
        self._driver = driver
        self._analyzer = analyzer_fn
        self._event_detector = event_detector
        self._storage = storage
        self._mqtt_pub = mqtt_pub
        self._web = web
        self._notifier = notifier
        self._smart_capture = smart_capture
        self._native_events_enabled = bool(native_events_enabled)
        self._device_info: DeviceInfo | None = None
        self._connection_info: ConnectionInfo | None = None
        self._discovery_published = False
        self._event_detector.seed(self._storage.get_latest_snapshot())

    def collect(self) -> CollectorResult:
        self._driver.login()

        first_fetch = self._device_info is None
        self._device_info = self._driver.get_device_info()
        if first_fetch:
            log.info(
                "Model: %s (%s, %s)",
                self._device_info.get("model", "?"),
                self._device_info.get("sw_version", "?"),
                self._device_info.get("docsis_status", "?"),
            )
        self._web.update_state(device_info=self._device_info)

        # Device state tracking (reboots, sw updates, IP changes)
        if self._device_info:
            uptime = self._device_info.get("uptime_seconds")
            sw_version = self._device_info.get("sw_version")
            ipv4 = self._device_info.get("wan_ipv4")
            ipv6 = self._device_info.get("wan_ipv6")
            reboot_reason = self._device_info.get("reboot_reason")

            old_state = self._storage.get_device_state()
            now = datetime.now(timezone.utc)
            now_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")

            events_to_log = []

            # Detection: Compare current poll with last known state from DB
            sw_changed = False
            uptime_decreased = False
            ip_changed = False

            old_sw = old_state.get("sw_version") if old_state else None
            if sw_version and old_sw and sw_version != old_sw:
                sw_changed = True

            old_uptime = old_state.get("uptime_seconds") if old_state else None
            if uptime is not None and old_uptime is not None and uptime < old_uptime:
                uptime_decreased = True

            # IP change detection for both IPv4 and IPv6
            old_ipv4 = old_state.get("wan_ipv4") if old_state else None
            old_ipv6 = old_state.get("wan_ipv6") if old_state else None

            ipv4_changed = ipv4 and old_ipv4 and ipv4 != old_ipv4
            ipv6_changed = ipv6 and old_ipv6 and ipv6 != old_ipv6
            if ipv4_changed or ipv6_changed:
                ip_changed = True

            # Format IP change snippet for inclusion in reboot/update messages
            ip_msg = ""
            if ip_changed:
                if ipv4_changed and ipv6_changed:
                    ip_msg = f"WAN IPv4/v6: {old_ipv4} / {old_ipv6} → {ipv4} / {ipv6}"
                elif ipv4_changed:
                    ip_msg = f"WAN IPv4: {old_ipv4} → {ipv4}"
                else:
                    ip_msg = f"WAN IPv6: {old_ipv6} → {ipv6}"

            # Construct parts for inclusion in messages
            uptime_fmt = format_uptime(old_uptime)
            msg_parts = []
            if uptime_fmt != "unknown":
                msg_parts.append(f"Prior uptime: {uptime_fmt}")

            # Priority 1: Software Update (usually implies a reboot)
            if sw_changed:
                msg_parts.append(f"SW: {old_sw} → {sw_version}")
                if ip_changed:
                    msg_parts.append(ip_msg)
                if reboot_reason:
                    msg_parts.append(f"Reason: {reboot_reason}")
                
                events_to_log.append({
                    "timestamp": now_iso,
                    "severity": "info",
                    "event_type": "device_sw_update",
                    "message": ", ".join(msg_parts),
                    "details": {"old_sw": old_sw, "new_sw": sw_version, "reboot_reason": reboot_reason, "prior_uptime": old_uptime, "ip_changed": ip_changed}
                })
            # Priority 2: Standard Reboot (uptime drop without SW change)
            elif uptime_decreased:
                if ip_changed:
                    msg_parts.append(ip_msg)
                if reboot_reason:
                    msg_parts.append(f"Reason: {reboot_reason}")
                
                events_to_log.append({
                    "timestamp": now_iso,
                    "severity": "warning",
                    "event_type": "device_reboot",
                    "message": ", ".join(msg_parts),
                    "details": {"reboot_reason": reboot_reason, "prior_uptime": old_uptime, "ip_changed": ip_changed}
                })
            # Priority 3: Standalone IP change (no reboot detected)
            elif ip_changed:
                events_to_log.append({
                    "timestamp": now_iso,
                    "severity": "info",
                    "event_type": "device_ip_change",
                    "message": ip_msg,
                    "details": {"old_ipv4": old_ipv4, "new_ipv4": ipv4, "old_ipv6": old_ipv6, "new_ipv6": ipv6}
                })

            if events_to_log:
                self._storage.save_events(events_to_log)
                if self._notifier:
                    self._notifier.dispatch(events_to_log)

            # Update the state database to hold the current 'last known' values.
            self._storage.update_device_state(
                uptime if uptime is not None else old_uptime,
                sw_version if sw_version is not None else old_sw,
                ipv4 if ipv4 is not None else old_ipv4,
                ipv6 if ipv6 is not None else old_ipv6,
                now_iso
            )

        if self._connection_info is None:
            self._connection_info = self._driver.get_connection_info()
            if self._connection_info:
                ds = self._connection_info.get("max_downstream_kbps", 0) // 1000
                us = self._connection_info.get("max_upstream_kbps", 0) // 1000
                conn_type = self._connection_info.get("connection_type", "")
                log.info("Connection: %d/%d Mbit/s (%s)", ds, us, conn_type)
                self._web.update_state(connection_info=self._connection_info)

        data = self._driver.get_docsis_data()
        if self._native_events_enabled:
            native_fetch = getattr(self._driver, "get_native_events", None)
            if not callable(native_fetch):
                NativeLogTelemetry("unsupported").emit()
            else:
                try:
                    rows = native_fetch()
                except Exception:
                    # Never include exception text, request details, or modem data.
                    NativeLogTelemetry("retrieval_failed").emit()
                else:
                    # The driver contract mirrors parse_network_log(): a list of
                    # category-tagged rows with the four native fields as text.
                    # Reject malformed results before invoking persistence.
                    valid_rows = isinstance(rows, list) and all(
                        isinstance(row, dict)
                        and row.get("category") in ("eventlog", "wifieventlog")
                        and all(
                            isinstance(row.get(field), str)
                            for field in ("prior", "text", "time", "t")
                        )
                        for row in rows
                    )
                    if not valid_rows:
                        NativeLogTelemetry("invalid_response").emit()
                    else:
                        returned_system = sum(
                            row["category"] == "eventlog" for row in rows
                        )
                        returned_wifi = sum(
                            row["category"] == "wifieventlog" for row in rows
                        )
                        try:
                            inserted = self._storage.save_native_events(
                                self._driver._url, rows
                            )
                            if (
                                type(inserted) is not int
                                or inserted < 0
                                or inserted > len(rows)
                            ):
                                raise ValueError("Invalid native event insertion count")
                        except Exception:
                            NativeLogTelemetry(
                                "storage_failed",
                                returned_system=returned_system,
                                returned_wifi=returned_wifi,
                            ).emit()
                        else:
                            # The storage method returns this transaction's insert
                            # count; subtract from this response, never a DB total.
                            duplicates = len(rows) - inserted
                            outcome = "empty" if not rows else "success"
                            NativeLogTelemetry(
                                outcome,
                                returned_system=returned_system,
                                returned_wifi=returned_wifi,
                                inserted=inserted,
                                duplicates=duplicates,
                            ).emit()
        previous_analysis = self._storage.get_latest_snapshot()
        last_spike_ts = self._storage.get_latest_spike_timestamp()
        analysis = self._analyzer(data)  # Call injected analyzer function
        apply_cumulative_error_baseline(
            analysis,
            previous_analysis,
            recent_spike_active=_recent_spike_active(last_spike_ts),
        )
        apply_spike_suppression(analysis, last_spike_ts)

        # MQTT publishing
        if self._mqtt_pub:
            if not self._discovery_published:
                self._mqtt_pub.publish_discovery(self._device_info)
                self._mqtt_pub.publish_channel_discovery(
                    analysis["ds_channels"], analysis["us_channels"], self._device_info
                )
                self._discovery_published = True
                time.sleep(1)
            speedtest = self._web.get_state().get("speedtest_latest")
            gi = compute_gaming_index(speedtest)
            self._mqtt_pub.publish_data(analysis, gaming_index=gi)

        # Web state + persistent storage
        self._web.update_state(analysis=analysis)
        snapshot_id = self._storage.save_snapshot(analysis, raw_data=data)

        # Event detection
        events = self._event_detector.check(analysis, snapshot_id=snapshot_id)
        if events:
            self._storage.save_events_with_ids(events)
            log.info("Detected %d event(s)", len(events))
            if self._notifier:
                self._notifier.dispatch(events)
            if self._smart_capture:
                self._smart_capture.evaluate(events)

        return CollectorResult(source=self.name, data=analysis)
