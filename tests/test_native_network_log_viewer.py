"""Synthetic Flask contracts for the stored native-log module view."""

import re
from unittest.mock import Mock


def _viewer_app(make_config, make_app, builtin_module_loader_factory, **overrides):
    values = {
        "modem_type": "ch7465", "modem_url": "http://synthetic-router.invalid",
        "admin_password": "synthetic-viewer-password", "bnetz_enabled": False,
        "update_check_enabled": False, "ch7465_network_log_enabled": False,
    }
    values.update(overrides)
    manager = make_config(values)
    storage = Mock(spec=["get_native_events"])
    storage.get_native_events.return_value = []
    application = make_app(
        config_manager=manager, storage=storage,
        module_loader_factory=builtin_module_loader_factory(manager),
    )
    return application, storage


def _sign_in(client):
    csrf = re.search(rb'name="csrf_token" value="([^"]+)"', client.get("/login").data)
    assert csrf is not None
    assert client.post("/login", data={
        "csrf_token": csrf.group(1).decode(), "password": "synthetic-viewer-password",
    }).status_code == 302


def test_native_view_requires_existing_authentication(
    make_config, make_app, builtin_module_loader_factory,
):
    application, storage = _viewer_app(make_config, make_app, builtin_module_loader_factory)
    client = application.test_client()
    response = client.get("/")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    assert client.get("/api/modem-native-events?limit=100").status_code == 401
    storage.get_native_events.assert_not_called()


def test_native_view_navigation_assets_and_disabled_collection(
    make_config, make_app, builtin_module_loader_factory,
):
    application, storage = _viewer_app(make_config, make_app, builtin_module_loader_factory)
    client = application.test_client()
    _sign_in(client)
    response = client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'data-view="mod-ch7465"' in html
    assert 'data-nav-title="Native Network Log"' in html
    assert 'id="view-mod-ch7465"' in html
    assert 'id="native-network-log" data-auth-enabled="true"' in html
    assert 'id="native-log-disabled"' in html
    assert "Previously stored events remain available" in html
    assert "no timezone conversion is applied" in html
    assert 'id="native-log-refresh"' in html and 'id="native-log-older" disabled' in html
    assert 'role="status"' in html and 'id="native-log-error" role="alert" hidden' in html
    assert "/modules/ch7465/static/main.js" in html
    assert "/modules/ch7465/static/style.css" in html
    for asset in ("main.js", "style.css"):
        assert client.get(f"/modules/ch7465/static/{asset}").status_code == 200
    storage.get_native_events.assert_not_called()  # Rendering never polls or loads event bodies.


def test_native_view_enabled_notice_and_optional_auth_mode(
    make_config, make_app, builtin_module_loader_factory,
):
    application, storage = _viewer_app(
        make_config, make_app, builtin_module_loader_factory,
        ch7465_network_log_enabled=True,
    )
    client = application.test_client()
    _sign_in(client)
    assert 'id="native-log-disabled"' not in client.get("/").get_data(as_text=True)
    storage.get_native_events.assert_not_called()

    no_auth, storage = _viewer_app(
        make_config, make_app, builtin_module_loader_factory, admin_password="",
    )
    client = no_auth.test_client()
    html = client.get("/").get_data(as_text=True)
    assert 'id="native-network-log" data-auth-enabled="false"' in html
    assert 'id="native-log-auth-required"' in html
    assert 'id="native-log-refresh" disabled' in html
    assert client.get("/api/modem-native-events?limit=100").status_code == 401
    storage.get_native_events.assert_not_called()


def test_native_view_uses_existing_read_only_cursor_api(
    make_config, make_app, builtin_module_loader_factory,
):
    application, storage = _viewer_app(make_config, make_app, builtin_module_loader_factory)
    client = application.test_client()
    _sign_in(client)
    events = [
        {"id": i, "category": "eventlog", "prior": "notice", "time": "opaque modem time",
         "text": "<img src=x onerror=alert(1)> synthetic", "t": "uninterpreted"}
        for i in range(201, 101, -1)
    ]
    storage.get_native_events.side_effect = [events, []]
    first = client.get("/api/modem-native-events?limit=100")
    assert first.status_code == 200
    assert first.get_json() == {"events": events, "next_before_id": 102}
    second = client.get("/api/modem-native-events?limit=100&before_id=102")
    assert second.get_json() == {"events": [], "next_before_id": None}
    assert storage.get_native_events.call_args_list[0].args == ("http://synthetic-router.invalid",)
    assert storage.get_native_events.call_args_list[0].kwargs == {"limit": 100, "before_id": None}
    assert storage.get_native_events.call_args_list[1].kwargs == {"limit": 100, "before_id": 102}
    for method in ("post", "put", "delete"):
        assert getattr(client, method)("/api/modem-native-events").status_code == 405


def test_native_view_follows_module_disabling(
    make_config, make_app, builtin_module_loader_factory,
):
    application, _ = _viewer_app(
        make_config, make_app, builtin_module_loader_factory, disabled_modules="ch7465",
    )
    client = application.test_client()
    _sign_in(client)
    html = client.get("/").get_data(as_text=True)
    assert 'data-view="mod-ch7465"' not in html
    assert 'id="native-network-log"' not in html
