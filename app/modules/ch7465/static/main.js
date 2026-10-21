(function() {
    'use strict';

    var root = document.getElementById('native-network-log');
    // Module scripts also load on Settings, where this view is absent.
    if (!root) return;
    var refresh = document.getElementById('native-log-refresh');
    var older = document.getElementById('native-log-older');
    var status = document.getElementById('native-log-status');
    var error = document.getElementById('native-log-error');
    var rows = document.getElementById('native-log-rows');
    var table = document.getElementById('native-log-table-wrap');
    var canRead = root.dataset.authEnabled === 'true';
    var nextBefore = null;
    var busy = false;
    var loaded = false;
    var pageSize = 100;

    function text(key, fallback) {
        return (window.T || {})['ch7465.' + key] || fallback;
    }

    function updateControls() {
        refresh.disabled = busy || !canRead;
        older.disabled = busy || !canRead || nextBefore === null;
        root.setAttribute('aria-busy', busy ? 'true' : 'false');
    }

    function validPage(data, before) {
        return data && Array.isArray(data.events) && data.events.length <= pageSize &&
            (data.next_before_id === null ||
                (Number.isSafeInteger(data.next_before_id) && data.next_before_id > 0 &&
                    (before === null || data.next_before_id < before))) &&
            data.events.every(function(event) {
                return event && (event.category === 'eventlog' || event.category === 'wifieventlog') &&
                    ['time', 'prior', 'text'].every(function(key) { return typeof event[key] === 'string'; });
            });
    }

    async function load(before) {
        if (busy || !canRead) return;
        busy = true;
        updateControls();
        rows.replaceChildren();
        table.hidden = true;
        error.hidden = true;
        error.textContent = '';
        status.textContent = text('loading', 'Loading stored events…');
        var authFailure = false;
        var controller = new AbortController();
        // A request timeout, never a polling or refresh timer.
        var timeout = setTimeout(function() { controller.abort(); }, 15000);
        try {
            var url = '/api/modem-native-events?limit=' + pageSize;
            if (before !== null) url += '&before_id=' + before;
            var response = await fetch(docsightUrl(url), {
                method: 'GET', credentials: 'same-origin', cache: 'no-store',
                redirect: 'error', signal: controller.signal
            });
            authFailure = response.status === 401 || response.status === 403;
            if (!response.ok) throw new Error('native-log-request');
            var data = await response.json();
            if (!validPage(data, before)) throw new Error('native-log-response');
            var fragment = document.createDocumentFragment();
            data.events.forEach(function(event) {
                var row = document.createElement('tr');
                var values = [event.time, event.prior, event.text,
                    event.category === 'eventlog' ? text('system', 'System') : text('wifi', 'Wi-Fi')];
                var labels = [text('time', 'Modem-reported time'), text('priority', 'Priority'),
                    text('description', 'Full event description'), text('category', 'Category')];
                values.forEach(function(value, index) {
                    var cell = document.createElement('td');
                    cell.setAttribute('data-label', labels[index]);
                    // All modem fields are untrusted, including time and priority.
                    cell.textContent = value;
                    row.appendChild(cell);
                });
                fragment.appendChild(row);
            });
            rows.replaceChildren(fragment);
            table.hidden = data.events.length === 0;
            nextBefore = data.next_before_id;
            loaded = true;
            status.textContent = data.events.length
                ? text('loaded', 'Showing {count} stored events.').replace('{count}', String(data.events.length))
                : (before === null ? text('empty', 'No stored native events for the configured modem.')
                    : text('no_older', 'No older stored events. Refresh to return to the newest events.'));
        } catch (_) {
            // Never render or log response bodies or arbitrary exception text.
            status.textContent = '';
            error.textContent = authFailure
                ? text('session_required', 'Authentication is required. Sign in again to view native events.')
                : text('error', 'Could not load stored native events. Try Refresh again.');
            error.hidden = false;
        } finally {
            clearTimeout(timeout);
            busy = false;
            updateControls();
        }
    }

    refresh.addEventListener('click', function() { return load(null); });
    older.addEventListener('click', function() { if (nextBefore !== null) return load(nextBefore); });
    // Existing generic module routing maps mod-ch7465 to initModCh7465.
    window.initModCh7465 = function() { if (!loaded) return load(null); };
    updateControls();
})();
