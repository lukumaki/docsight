import sqlite3
from contextlib import closing
from unittest.mock import MagicMock

import pytest

from app.drivers.ch7465 import CH7465Driver
from app.modules.ch7465.driver import CH7465NativeLogDriver
from app.modules.ch7465.parser import MAX_XML_BYTES, parse_network_log
from app.storage import SnapshotStorage
from app.storage.migrations import CORE_MIGRATIONS, SCHEMA_VERSION, run_migrations
from app.modules.backup.backup import create_backup_to_file, restore_backup
from tests.sqlite_helpers import data_digest, schema_digest


SYNTHETIC_XML = b"""<eventlog_table>
<eventlog><prior>critical</prior><text>Synthetic cable event</text><time>2026-01-02 03:04:05</time><t>1767323045</t></eventlog>
<wifieventlog><prior>notice</prior><text>Synthetic wireless event</text><time>2026-01-02 03:04:06</time><t>1767323046</t></wifieventlog>
<eventlog><prior>critical</prior><text>Synthetic cable event</text><time>2026-01-02 03:04:05</time><t>1767323045</t></eventlog>
</eventlog_table>"""


def test_parser_preserves_categories_priority_fields_and_duplicate_rows():
    rows = parse_network_log(SYNTHETIC_XML)
    assert [row["category"] for row in rows] == ["eventlog", "eventlog", "wifieventlog"]
    assert rows[0]["prior"] == "critical"
    assert rows[0]["text"] == "Synthetic cable event"
    assert rows[2]["category"] == "wifieventlog"


@pytest.mark.parametrize("payload", [b"<wrong/>", b"<eventlog_table>"])
def test_parser_rejects_wrong_or_malformed_xml(payload):
    with pytest.raises(ValueError):
        parse_network_log(payload)


def _xml_encoded(text, encoding):
    if encoding == "utf-8":
        return text.encode("utf-8")
    bom = b"\xff\xfe" if encoding == "utf-16-le" else b"\xfe\xff"
    return bom + text.encode(encoding)


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16-le", "utf-16-be"])
def test_parser_rejects_doctype_in_supported_encodings(encoding):
    payload = _xml_encoded("<!DOCTYPE eventlog_table><eventlog_table/>", encoding)
    with pytest.raises(ValueError, match="XML declaration"):
        parse_network_log(payload)


@pytest.mark.parametrize(
    "declaration",
    [
        '<!DOCTYPE eventlog_table [<!ENTITY custom "synthetic">]>',
        '<!DOCTYPE eventlog_table [<!ENTITY custom SYSTEM "file:///synthetic-only">]>',
        '<!DOCTYPE eventlog_table [<!ENTITY custom SYSTEM "https://example.invalid/synthetic">]>',
    ],
)
@pytest.mark.parametrize("encoding", ["utf-8", "utf-16-le", "utf-16-be"])
def test_parser_rejects_internal_and_external_entity_declarations(declaration, encoding):
    payload = _xml_encoded(
        f"{declaration}<eventlog_table><eventlog><text>&custom;</text></eventlog></eventlog_table>",
        encoding,
    )
    with pytest.raises(ValueError, match="XML declaration"):
        parse_network_log(payload)


def test_parser_rejects_undeclared_custom_entity_reference():
    with pytest.raises(ValueError, match="Malformed"):
        parse_network_log(
            b"<eventlog_table><eventlog><text>&custom;</text></eventlog></eventlog_table>"
        )


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16-le", "utf-16-be"])
def test_parser_preserves_event_fields_and_predefined_entities(encoding):
    payload = _xml_encoded(
        "<eventlog_table>"
        "<eventlog><prior>critical</prior><text>Synthetic &amp; cable</text><time>opaque-time</time><t>opaque-t</t></eventlog>"
        "<wifieventlog><prior>notice</prior><text>Synthetic Wi-Fi</text><time>opaque-wifi-time</time><t>opaque-wifi-t</t></wifieventlog>"
        "</eventlog_table>",
        encoding,
    )
    assert parse_network_log(payload) == [
        {
            "category": "eventlog",
            "prior": "critical",
            "text": "Synthetic & cable",
            "time": "opaque-time",
            "t": "opaque-t",
        },
        {
            "category": "wifieventlog",
            "prior": "notice",
            "text": "Synthetic Wi-Fi",
            "time": "opaque-wifi-time",
            "t": "opaque-wifi-t",
        },
    ]


def test_parser_enforces_xml_size_limit():
    with pytest.raises(ValueError):
        parse_network_log(b" " * (MAX_XML_BYTES + 1))


def test_parser_accepts_empty_category_and_missing_optional_fields():
    assert parse_network_log(b"<eventlog_table><wifieventlog><text></text></wifieventlog></eventlog_table>") == [
        {"category": "wifieventlog", "prior": "", "text": "", "time": "", "t": ""}
    ]


def test_authentication_material_is_not_logged(caplog):
    driver = CH7465Driver("http://synthetic-router.local", "synthetic-user", "synthetic-password", play_firmware=False)
    response = MagicMock()
    driver._session.get = MagicMock(return_value=response)
    driver._set_data = MagicMock(return_value="successSID=log-sentinel")
    driver.login()
    assert "log-sentinel" not in caplog.text
    assert "session" + "Token" + "=" not in caplog.text
    driver._finalizer.detach()
    driver._session.close()


def test_unrecognized_authentication_response_is_not_in_error_message():
    marker = "SYNTHETIC_MODEM_RESPONSE_DETAIL_MARKER"
    driver = CH7465Driver(
        "http://synthetic-router.local", "synthetic-user", "synthetic-password",
        play_firmware=False,
    )
    driver._session.get = MagicMock(return_value=MagicMock())
    driver._set_data = MagicMock(return_value=marker)
    try:
        with pytest.raises(RuntimeError) as error:
            driver.login()
        assert marker not in str(error.value)
        assert "unrecognized modem response" in str(error.value)
    finally:
        driver._finalizer.detach()
        driver._session.close()


def test_connection_info_failure_logs_only_exception_type(caplog):
    marker = "SYNTHETIC_MODEM_ERROR_DETAIL_MARKER"
    driver = CH7465Driver(
        "http://synthetic-router.local", "synthetic-user", "synthetic-password",
        play_firmware=False,
    )
    driver._get_data = MagicMock(side_effect=RuntimeError(marker))
    try:
        with caplog.at_level("WARNING", logger="docsis.driver.ch7465"):
            assert driver.get_connection_info() == {}
        assert marker not in caplog.text
        assert "RuntimeError" in caplog.text
    finally:
        driver._finalizer.detach()
        driver._session.close()


def test_native_driver_bounded_request_uses_inherited_session():
    driver = CH7465NativeLogDriver("http://synthetic-router.local", "u", "p", play_firmware=False)
    response = MagicMock()
    response.iter_content.return_value = [b"<eventlog_table/>"]
    driver._session.post = MagicMock(return_value=response)
    assert driver.get_native_events() == []
    kwargs = driver._session.post.call_args.kwargs
    assert kwargs["data"] == {"fun": "13"}
    assert kwargs["stream"] is True
    assert kwargs["allow_redirects"] is False
    response.close.assert_called_once()


@pytest.mark.parametrize(
    ("play_firmware", "expected_data"),
    [(False, {"fun": "13"}), (True, {"token": "synthetic-session-token", "fun": "13"})],
)
def test_native_request_reuses_authenticated_session_without_relogin(
    monkeypatch, play_firmware, expected_data,
):
    import app.drivers.ch7465 as ch7465

    session = MagicMock()
    session.cookies.get.return_value = "synthetic-session-token"
    response = MagicMock()
    response.iter_content.return_value = [b"<eventlog_table/>"]
    session.post.return_value = response
    session_factory = MagicMock(return_value=session)
    monkeypatch.setattr(ch7465.requests, "Session", session_factory)

    driver = CH7465NativeLogDriver(
        "http://synthetic-router.local", "synthetic-user", "synthetic-password",
        play_firmware=play_firmware,
    )
    try:
        assert driver._session is session
        assert driver.get_native_events() == []
        session_factory.assert_called_once_with()
        session.get.assert_not_called()
        session.post.assert_called_once()
        assert session.post.call_args.kwargs["data"] == expected_data
    finally:
        driver._finalizer.detach()
        driver._session.close()


def test_storage_deduplicates_snapshots_but_keeps_duplicate_ordinals_and_endpoint_scope(tmp_path):
    storage = SnapshotStorage(str(tmp_path / "events.db"), max_days=0)
    assert storage.save_native_events("http://router.local", parse_network_log(SYNTHETIC_XML)) == 3
    assert storage.save_native_events("http://router.local/", parse_network_log(SYNTHETIC_XML)) == 0
    assert storage.save_native_events("http://another-router.local", parse_network_log(SYNTHETIC_XML)) == 3
    rows = storage.get_native_events("http://router.local", limit=200)
    assert len(rows) == 3
    assert {row["category"] for row in rows} == {"eventlog", "wifieventlog"}
    assert all(row["ingested_at_utc"].endswith("Z") for row in rows)
    with sqlite3.connect(storage.db_path) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(events)")}
    assert "fingerprint" not in cols


def test_storage_insert_counts_support_accurate_aggregate_retrieval_telemetry(tmp_path):
    storage = SnapshotStorage(str(tmp_path / "telemetry.db"), max_days=0)
    rows = parse_network_log(SYNTHETIC_XML)

    # First observation inserts all rows, including the repeated identical row.
    inserted = storage.save_native_events("http://router.local", rows)
    assert inserted == 3
    assert len(rows) - inserted == 0

    # Replaying the same response recognizes every prior identity.
    inserted = storage.save_native_events("http://router.local", rows)
    assert inserted == 0
    assert len(rows) - inserted == 3

    # A response containing prior rows plus one new row reports an exact split.
    new_row = {
        "category": "eventlog", "prior": "warning", "text": "Synthetic new event",
        "time": "opaque-new-time", "t": "opaque-new-t",
    }
    mixed = [*rows, new_row]
    inserted = storage.save_native_events("http://router.local", mixed)
    assert inserted == 1
    assert len(mixed) - inserted == 3

    # Reordering the same response does not change any event identities.
    reordered = [new_row, *reversed(rows)]
    inserted = storage.save_native_events("http://router.local", reordered)
    assert inserted == 0
    assert len(reordered) - inserted == 4


def test_native_event_read_is_bounded_and_unknown_endpoint_is_empty(tmp_path):
    storage = SnapshotStorage(str(tmp_path / "events.db"), max_days=0)
    rows = parse_network_log(SYNTHETIC_XML)
    storage.save_native_events("http://router.local", rows)
    assert len(storage.get_native_events("http://router.local", limit=999)) == 3
    assert storage.get_native_events("http://other.local") == []


def test_history_retention_uses_ingestion_time_and_allows_reimport(tmp_path):
    storage = SnapshotStorage(str(tmp_path / "retention.db"), max_days=2)
    row = [{"category": "eventlog", "prior": "notice", "text": "Synthetic retained row", "time": "opaque", "t": "opaque"}]
    assert storage.save_native_events("http://router.local", row) == 1
    with sqlite3.connect(storage.db_path) as conn:
        conn.execute("UPDATE modem_native_events SET ingested_at_utc='2000-01-01T00:00:00Z'")
    assert storage.delete_old_native_events(2) == 1
    assert storage.save_native_events("http://router.local", row) == 1


def test_migration_adds_native_tables_and_preserves_generic_event_acknowledgments(tmp_path):
    def named_index_definitions(conn):
        definitions = {}
        for name, table, sql in conn.execute(
            "SELECT name,tbl_name,sql FROM sqlite_master "
            "WHERE type='index' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall():
            quoted_table = table.replace('"', '""')
            quoted_name = name.replace('"', '""')
            unique = next(
                row[2] for row in conn.execute(f'PRAGMA index_list("{quoted_table}")')
                if row[1] == name
            )
            columns = tuple(
                row[2] for row in conn.execute(f'PRAGMA index_info("{quoted_name}")')
            )
            definitions[name] = (table, columns, unique, " ".join(sql.split()))
        return definitions

    db_path = str(tmp_path / "upgrade.db")
    native_migration_id = "core-0006-modem-native-events"
    native_position = next(
        i for i, migration in enumerate(CORE_MIGRATIONS)
        if migration.migration_id == native_migration_id
    )
    legacy_migrations = CORE_MIGRATIONS[:native_position]
    # Verified against baseline 04d0c7d5 (upstream source revision 84d2ba24).
    # These existing helpers produce schema_version 2, including events.is_demo.
    legacy_ids = [
        "core-0001-baseline", "core-0002-incidents-to-journal",
        "core-0003-demo-flags", "core-0004-snapshot-columns", "core-0005-meta-version",
    ]
    assert [migration.migration_id for migration in legacy_migrations] == legacy_ids
    assert run_migrations(db_path, legacy_migrations) == legacy_ids
    legacy_rows = [
        (17, "2026-01-01T00:00:00Z", "warning", "synthetic",
         "Keep acknowledged synthetic event", '{"source":"synthetic","count":2}', 1, 0),
        (29, "2026-01-02T00:00:00Z", "info", "synthetic_demo",
         "Keep unacknowledged synthetic event: \u00e1", None, 0, 1),
    ]
    event_query = (
        "SELECT id,timestamp,severity,event_type,message,details,acknowledged,is_demo "
        "FROM events ORDER BY id"
    )
    registry_query = "SELECT id,applied_at FROM _docsight_migrations ORDER BY id"
    version_query = "SELECT value FROM _docsight_meta WHERE key='schema_version'"
    native_tables = {"modem_native_events", "modem_native_event_identity"}
    native_indexes = {
        "idx_native_events_identity": (1, ["device_scope", "fingerprint_version", "fingerprint"]),
        "idx_native_events_ingested": (0, ["ingested_at_utc"]),
        "idx_native_events_scope_ingested": (0, ["device_scope", "ingested_at_utc"]),
    }
    # Seed genuine legacy rows without invoking current storage initialization.
    # Commit or roll back via conn before the outer closing manager closes it.
    with closing(sqlite3.connect(db_path)) as conn, conn:
        conn.executemany(
            "INSERT INTO events "
            "(id,timestamp,severity,event_type,message,details,acknowledged,is_demo) "
            "VALUES (?,?,?,?,?,?,?,?)", legacy_rows,
        )
        assert conn.execute(event_query).fetchall() == legacy_rows
        assert conn.execute(version_query).fetchone() == ("2",)
        legacy_registry = conn.execute(registry_query).fetchall()
        assert [row[0] for row in legacy_registry] == legacy_ids
        legacy_event_columns = conn.execute("PRAGMA table_info(events)").fetchall()
        objects = {row[0] for row in conn.execute("SELECT name FROM sqlite_master")}
        assert not native_tables.intersection(objects)
        assert not native_indexes.keys() & objects
        legacy_indexes = named_index_definitions(conn)
        assert {"idx_events_ts", "idx_events_ack", "idx_events_type_ts"} <= legacy_indexes.keys()

    # First current SnapshotStorage construction performs the real upgrade.
    upgraded = SnapshotStorage(db_path, max_days=0)
    with closing(sqlite3.connect(db_path)) as conn, conn:
        assert conn.execute(event_query).fetchall() == legacy_rows
        assert conn.execute("PRAGMA table_info(events)").fetchall() == legacy_event_columns
        assert conn.execute(version_query).fetchone() == (str(SCHEMA_VERSION),)
        upgraded_registry = conn.execute(registry_query).fetchall()
        assert upgraded_registry[:len(legacy_registry)] == legacy_registry
        assert [row[0] for row in upgraded_registry] == [
            migration.migration_id for migration in CORE_MIGRATIONS
        ]
        assert sum(row[0] == native_migration_id for row in upgraded_registry) == 1
        assert all(row[1] for row in upgraded_registry)
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"events", *native_tables} <= tables
        indexes = {row[1]: row[2] for row in conn.execute("PRAGMA index_list(modem_native_events)")}
        for name, (unique, columns) in native_indexes.items():
            assert indexes[name] == unique
            assert [row[2] for row in conn.execute(f"PRAGMA index_info({name})")] == columns
        upgraded_indexes = named_index_definitions(conn)
        assert legacy_indexes.keys() <= upgraded_indexes.keys()
        assert all(upgraded_indexes[name] == definition for name, definition in legacy_indexes.items())
    assert upgraded.save_native_events("http://router.local", parse_network_log(SYNTHETIC_XML)) == 3
    native_rows = upgraded.get_native_events("http://router.local")
    upgraded_schema = schema_digest(db_path)
    upgraded_data = data_digest(db_path)

    reopened = SnapshotStorage(db_path, max_days=0)
    assert reopened.get_native_events("http://router.local") == native_rows
    assert run_migrations(db_path, CORE_MIGRATIONS) == []
    assert schema_digest(db_path) == upgraded_schema
    assert data_digest(db_path) == upgraded_data
    with closing(sqlite3.connect(db_path)) as conn, conn:
        assert conn.execute(event_query).fetchall() == legacy_rows
        assert conn.execute(registry_query).fetchall() == upgraded_registry
        assert conn.execute(version_query).fetchone() == (str(SCHEMA_VERSION),)
        assert conn.execute("PRAGMA integrity_check").fetchone() == ("ok",)


def test_native_event_backup_restore_persists_identity_and_deduplication(tmp_path):
    source_dir = tmp_path / "source-data"
    backup_dir = tmp_path / "backups"
    restored_dir = tmp_path / "restored-data"
    db_path = str(source_dir / "docsis_history.db")
    rows = parse_network_log(SYNTHETIC_XML)
    original = SnapshotStorage(db_path, max_days=0)
    original.save_native_events("http://router.local", rows)
    with sqlite3.connect(db_path) as conn:
        original_salt = conn.execute(
            "SELECT salt FROM modem_native_event_identity WHERE id=1"
        ).fetchone()[0]

    archive_name = create_backup_to_file(str(source_dir), str(backup_dir))
    result = restore_backup((backup_dir / archive_name).read_bytes(), str(restored_dir))
    assert "docsis_history.db" in result["restored_files"]

    restored_db = str(restored_dir / "docsis_history.db")
    restored = SnapshotStorage(restored_db, max_days=0)
    restored_rows = restored.get_native_events("http://router.local")
    assert len(restored_rows) == 3
    assert {row["category"] for row in restored_rows} == {"eventlog", "wifieventlog"}
    expected_fields = {
        (row["category"], row["prior"], row["text"], row["time"], row["t"])
        for row in rows
    }
    actual_fields = {
        (row["category"], row["prior"], row["text"], row["time"], row["t"])
        for row in restored_rows
    }
    assert actual_fields == expected_fields
    with sqlite3.connect(restored_db) as conn:
        restored_salt = conn.execute(
            "SELECT salt FROM modem_native_event_identity WHERE id=1"
        ).fetchone()[0]
    assert restored_salt == original_salt
    assert restored.save_native_events("http://router.local", rows) == 0


def test_fingerprint_collision_is_detected_without_overwriting_existing_row(tmp_path, monkeypatch):
    import app.storage.native_events as native_events

    storage = SnapshotStorage(str(tmp_path / "collision.db"), max_days=0)
    rows = [{"category": "eventlog", "prior": "notice", "text": "first", "time": "t", "t": "1"}]
    class SameFingerprint:
        def hexdigest(self):
            return "forced-collision"

    monkeypatch.setattr(
        native_events, "_event_fingerprint",
        lambda _scope, _category, _values, _ordinal: SameFingerprint().hexdigest(),
    )
    storage.save_native_events("http://router.local", rows)
    changed = [{**rows[0], "text": "different"}]
    with pytest.raises(RuntimeError, match="fingerprint collision"):
        storage.save_native_events("http://router.local", changed)
    assert storage.get_native_events("http://router.local")[0]["text"] == "first"


def test_native_events_api_requires_configured_auth_is_read_only_and_caps_pages(tmp_path, make_app):
    from app.runtime import get_runtime

    storage = SnapshotStorage(str(tmp_path / "api.db"), max_days=0)
    sample = [{"category": "eventlog", "prior": "notice", "text": f"row-{i}", "time": "opaque", "t": str(i)} for i in range(205)]
    storage.save_native_events("http://router.local", sample)
    application = make_app(storage=storage)
    runtime = get_runtime(application)
    runtime.config_manager.save({"admin_password": "synthetic-password", "modem_url": "http://router.local"})
    client = application.test_client()

    assert client.get("/api/modem-native-events").status_code == 401
    login_page = client.get("/login")
    import re
    csrf = re.search(rb'name="csrf_token" value="([^"]+)"', login_page.data).group(1).decode()
    assert client.post("/login", data={"csrf_token": csrf, "password": "synthetic-password"}).status_code in (200, 302)

    first = client.get("/api/modem-native-events?limit=999")
    assert first.status_code == 400  # API rejects out-of-range parameters rather than silently widening.
    first = client.get("/api/modem-native-events?limit=200")
    body = first.get_json()
    assert len(body["events"]) == 200
    next_id = body["next_before_id"]
    second = client.get(f"/api/modem-native-events?limit=200&before_id={next_id}")
    assert len(second.get_json()["events"]) == 5
    assert second.get_json()["next_before_id"] is None
    assert len(storage.get_events()) == 0


def test_native_api_requires_admin_password_even_when_global_auth_is_optional(tmp_path, make_app):
    application = make_app(storage=SnapshotStorage(str(tmp_path / "no-auth.db"), max_days=0))
    response = application.test_client().get("/api/modem-native-events")
    assert response.status_code == 401


def test_driver_logs_redact_sid_session_token_and_sensitive_payload(caplog):
    driver = CH7465Driver("http://synthetic-router.local", "synthetic-user", "synthetic-password", play_firmware=False)
    response = MagicMock()
    driver._session.get = MagicMock(return_value=response)
    driver._set_data = MagicMock(return_value="successSID=SID-SECRET sessionToken=TOKEN-SECRET")
    driver.login()
    assert "SID-SECRET" not in caplog.text
    assert "TOKEN-SECRET" not in caplog.text
    assert "synthetic-password" not in caplog.text
    driver._finalizer.detach()
    driver._session.close()
