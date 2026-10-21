"""Private persistence for modem-native events; never routes through event hooks."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit, urlunsplit

from .sqlite import write_transaction

FINGERPRINT_VERSION = 1
_FIELDS = ("prior", "text", "time", "t")


def _event_fingerprint(scope: str, category: str, values: tuple[str, ...], ordinal: int) -> str:
    payload = json.dumps(
        [scope, category, *values, ordinal], ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(b"docsight-native-event-v1\0" + payload).hexdigest()


def _canonical_endpoint(endpoint: str) -> str:
    parts = urlsplit(str(endpoint))
    if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
        raise ValueError("Invalid modem endpoint")
    host = parts.hostname.encode("idna").decode("ascii").lower()
    if ":" in host:
        host = f"[{host}]"
    port = parts.port
    netloc = host + (f":{port}" if port else "")
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), netloc, path, "", ""))


class NativeEventMethods:
    """Dedicated native-event storage and bounded read path."""

    def _native_scope(self, endpoint: str, *, create=False) -> str:
        canonical = _canonical_endpoint(endpoint).encode("utf-8")
        context = write_transaction(self.db_path) if create else self._read()
        with context as conn:
            row = conn.execute(
                "SELECT salt FROM modem_native_event_identity WHERE id=1"
            ).fetchone()
            if row is None:
                if not create:
                    return ""
                salt = secrets.token_bytes(32)
                conn.execute("INSERT INTO modem_native_event_identity(id,salt) VALUES(1,?)", (salt,))
            else:
                salt = bytes(row[0])
        return hmac.new(
            salt, b"docsight-ch7465-endpoint-v1\0" + canonical, hashlib.sha256
        ).hexdigest()

    def save_native_events(self, endpoint: str, rows: list[dict]) -> int:
        """Insert newly observed identities and preserve duplicate row ordinals."""
        scope = self._native_scope(endpoint, create=True)
        seen: dict[tuple[str, ...], int] = {}
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        inserted = 0
        with write_transaction(self.db_path) as conn:
            for row in rows:
                category = row["category"]
                if category not in {"eventlog", "wifieventlog"}:
                    raise ValueError("Invalid native event category")
                values = tuple(str(row.get(field, "")) for field in _FIELDS)
                ordinal = seen.get((category, *values), 0)
                seen[(category, *values)] = ordinal + 1
                fingerprint = _event_fingerprint(scope, category, values, ordinal)
                cur = conn.execute(
                    """INSERT OR IGNORE INTO modem_native_events
                    (device_scope,category,fingerprint_version,fingerprint,occurrence_ordinal,
                     prior,text,time,t,ingested_at_utc) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (scope, category, FINGERPRINT_VERSION, fingerprint, ordinal, *values, now))
                if cur.rowcount:
                    inserted += 1
                    continue
                existing = conn.execute(
                    """SELECT category,occurrence_ordinal,prior,text,time,t
                    FROM modem_native_events WHERE device_scope=? AND fingerprint_version=? AND fingerprint=?""",
                    (scope, FINGERPRINT_VERSION, fingerprint),
                ).fetchone()
                if existing is None or tuple(existing) != (category, ordinal, *values):
                    raise RuntimeError("Native event fingerprint collision")
        return inserted

    def get_native_events(
        self, endpoint: str, *, limit: int = 100, before_id: int | None = None
    ) -> list[dict]:
        limit = max(1, min(int(limit), 200))
        scope = self._native_scope(endpoint)
        if not scope:
            return []
        with self._read() as conn:
            if before_id is None:
                rows = conn.execute(
                    "SELECT id,category,prior,text,time,t,ingested_at_utc "
                    "FROM modem_native_events WHERE device_scope=? ORDER BY id DESC LIMIT ?",
                    (scope, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id,category,prior,text,time,t,ingested_at_utc "
                    "FROM modem_native_events WHERE device_scope=? AND id<? ORDER BY id DESC LIMIT ?",
                    (scope, int(before_id), limit),
                ).fetchall()
        return [dict(row) for row in rows]

    def delete_old_native_events(self, days: int) -> int:
        if int(days) <= 0:
            return 0
        cutoff = (datetime.now(timezone.utc) - timedelta(days=int(days))).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        with write_transaction(self.db_path) as conn:
            return conn.execute("DELETE FROM modem_native_events WHERE ingested_at_utc < ?", (cutoff,)).rowcount
