'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const test = require('node:test');
const source = fs.readFileSync(path.join(__dirname, '../../app/modules/ch7465/static/main.js'), 'utf8');

function element(fragment = false) {
    const listeners = {};
    return {
        fragment, children: [], dataset: {}, attributes: {}, textContent: '', hidden: false, disabled: false,
        set innerHTML(_) { throw new Error('HTML insertion is forbidden'); },
        setAttribute(key, value) { this.attributes[key] = value; },
        addEventListener(name, fn) { listeners[name] = fn; },
        click() { if (!this.disabled) return listeners.click(); },
        appendChild(child) { this.children.push(child); },
        replaceChildren(...children) {
            this.children = children.flatMap(child => child.fragment ? child.children : [child]);
        },
    };
}

function browser({auth = true, absent = false} = {}) {
    const ids = ['native-network-log', 'native-log-refresh', 'native-log-older', 'native-log-status',
        'native-log-error', 'native-log-rows', 'native-log-table-wrap'];
    const elements = Object.fromEntries(ids.map(id => [id, element()]));
    elements['native-network-log'].dataset.authEnabled = String(auth);
    const requests = [], replies = [], timers = new Map();
    let timerId = 0;
    const context = {
        document: {
            getElementById: id => absent ? null : elements[id],
            createElement: tag => { assert.ok(['tr', 'td'].includes(tag)); return element(); },
            createDocumentFragment: () => element(true),
        },
        AbortController,
        console: {log() { assert.fail('Unexpected log'); }, error() { assert.fail('Unexpected error log'); }},
        docsightUrl: url => '/docsight' + url,
        setTimeout(fn, ms) { assert.equal(ms, 15000); timers.set(++timerId, fn); return timerId; },
        clearTimeout(id) { timers.delete(id); },
        fetch(url, options) {
            assert.match(url, /^\/docsight\/api\/modem-native-events\?limit=100(?:&before_id=[1-9]\d*)?$/);
            assert.equal(options.method, 'GET');
            assert.equal(options.credentials, 'same-origin');
            assert.equal(options.redirect, 'error');
            assert.equal(options.cache, 'no-store');
            assert.equal(options.body, undefined);
            requests.push({url, options});
            assert.ok(replies.length, 'Unapproved extra request');
            const reply = replies.shift();
            return typeof reply === 'function' ? reply(options) : Promise.resolve(reply);
        },
    };
    context.window = context;
    vm.createContext(context);
    vm.runInContext(source, context);
    return {
        context, elements, requests, replies, timers,
        page(events = [], next = null) {
            replies.push({ok: true, status: 200, json: async () => ({events, next_before_id: next})});
        },
        status: () => elements['native-log-status'].textContent,
        error: () => elements['native-log-error'].textContent,
        rows: () => elements['native-log-rows'].children,
        refresh: () => elements['native-log-refresh'].click(),
        older: () => elements['native-log-older'].click(),
    };
}

const event = overrides => ({time: '2026-01-02 03:04:05', prior: 'notice', text: 'Synthetic event',
    category: 'eventlog', ...overrides});

test('loads lazily through the module hook and never starts a refresh interval', async () => {
    const b = browser();
    assert.equal(b.requests.length, 0);
    assert.equal(b.timers.size, 0);
    b.page([event()]);
    await b.context.initModCh7465();
    await b.context.initModCh7465();
    assert.equal(b.requests.length, 1);
    assert.equal(b.timers.size, 0);
    assert.equal(b.elements['native-network-log'].attributes['aria-busy'], 'false');
    assert.equal(browser({absent: true}).context.initModCh7465, undefined);
});

test('preserves full untrusted text and raw modem time, and labels both categories', async () => {
    const b = browser();
    const payload = '<img src="https://synthetic.invalid/" onerror="throw 1">\n' + 'á'.repeat(3000);
    b.page([event({time: '<script>opaque time</script>', prior: '<b>native</b>', text: payload,
        t: 'must not be interpreted', ingested_at_utc: 'must not be displayed'}),
    event({category: 'wifieventlog'})]);
    await b.context.initModCh7465();
    assert.deepEqual(b.rows()[0].children.map(cell => cell.textContent),
        ['<script>opaque time</script>', '<b>native</b>', payload, 'System']);
    assert.equal(b.rows()[1].children[3].textContent, 'Wi-Fi');
    assert.equal(b.rows()[0].children[2].attributes['data-label'], 'Full event description');
    assert.equal(b.elements['native-log-table-wrap'].hidden, false);
    assert.equal(b.requests.length, 1);
});

test('older uses the API cursor and Refresh returns to the newest page', async () => {
    const b = browser();
    b.page(Array.from({length: 100}, () => event()), 102);
    await b.context.initModCh7465();
    b.page([event({text: 'Older synthetic event'})]);
    await b.older();
    assert.equal(b.requests[1].url, '/docsight/api/modem-native-events?limit=100&before_id=102');
    assert.equal(b.rows().length, 1); // Bounded page replacement, no unbounded accumulation.
    assert.equal(b.elements['native-log-older'].disabled, true);
    b.page([event({text: 'Newest synthetic event'})]);
    await b.refresh();
    assert.equal(b.requests[2].url, '/docsight/api/modem-native-events?limit=100');
    assert.equal(b.rows()[0].children[2].textContent, 'Newest synthetic event');
});

test('empty and end-of-history states are explicit', async () => {
    const b = browser();
    b.page();
    await b.context.initModCh7465();
    assert.match(b.status(), /No stored native events/);
    assert.equal(b.elements['native-log-table-wrap'].hidden, true);
    assert.equal(b.elements['native-log-older'].disabled, true);
    b.page(Array.from({length: 100}, () => event()), 12);
    await b.refresh();
    b.page();
    await b.older();
    assert.match(b.status(), /No older stored events/);
});

for (const status of [401, 403, 500]) {
    test(`HTTP ${status} is sanitized without reading the response body`, async () => {
        const b = browser();
        b.replies.push({ok: false, status, json() { assert.fail('Sensitive body read'); }});
        await b.context.initModCh7465();
        assert.match(b.error(), status === 500 ? /Could not load/ : /Authentication is required/);
        assert.equal(b.elements['native-log-error'].hidden, false);
        assert.equal(b.elements['native-log-refresh'].disabled, false);
        assert.equal(b.rows().length, 0);
        assert.equal(b.timers.size, 0);
    });
}

for (const kind of ['network', 'json']) {
    test(`${kind} failures hide stale rows and arbitrary exception text`, async () => {
        const b = browser();
        b.page([event()]);
        await b.context.initModCh7465();
        const fail = () => Promise.reject(new Error('SYNTHETIC-PRIVATE-MARKER'));
        b.replies.push(kind === 'network' ? fail : {ok: true, status: 200, json: fail});
        await b.refresh();
        assert.equal(b.error(), 'Could not load stored native events. Try Refresh again.');
        assert.equal(b.rows().length, 0);
        assert.equal(b.elements['native-log-table-wrap'].hidden, true);
    });
}

test('rejects malformed pages and cursors instead of issuing an unsafe request', async () => {
    for (const data of [null, {events: [], next_before_id: '//synthetic.invalid'},
        {events: [event({category: 'unknown'})], next_before_id: null},
        {events: [event({text: null})], next_before_id: null},
        {events: Array(101).fill(event()), next_before_id: null}]) {
        const b = browser();
        b.replies.push({ok: true, status: 200, json: async () => data});
        await b.context.initModCh7465();
        assert.match(b.error(), /Could not load/);
        assert.equal(b.requests.length, 1);
        assert.equal(b.rows().length, 0);
        assert.equal(b.elements['native-log-older'].disabled, true);
    }
});

test('optional-auth mode never requests native events', async () => {
    const b = browser({auth: false});
    await b.context.initModCh7465();
    await b.refresh();
    assert.equal(b.requests.length, 0);
    assert.equal(b.elements['native-log-refresh'].disabled, true);
    assert.equal(b.elements['native-log-older'].disabled, true);
});

test('request timeout and concurrent clicks cannot leave controls stuck or duplicate requests', async () => {
    const b = browser();
    b.replies.push(options => new Promise((_, reject) => {
        options.signal.addEventListener('abort', () => reject(new Error('synthetic timeout')));
    }));
    const pending = b.context.initModCh7465();
    await b.context.initModCh7465();
    await b.refresh();
    assert.equal(b.requests.length, 1);
    assert.equal(b.elements['native-log-refresh'].disabled, true);
    b.timers.values().next().value();
    await pending;
    assert.equal(b.timers.size, 0);
    assert.equal(b.elements['native-log-refresh'].disabled, false);
    assert.match(b.error(), /Could not load/);
    b.page();
    await b.refresh();
    assert.match(b.status(), /No stored native events/);
});
