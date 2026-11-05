const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');

const source = fs.readFileSync(path.join(__dirname, '../home/static/home/chat.js'), 'utf8');

function setup(fetch, initial = {}) {
    const timers = [];
    const elements = {};
    function element() {
        return { disabled: false, readOnly: false, value: '', textContent: '', listeners: {}, children: [],
            addEventListener(name, handler) { this.listeners[name] = handler; },
            appendChild(child) { this.children.push(child); } };
    }
    for (const name of ['chat-form', 'chat-message', 'chat-messages', 'composer-status', 'chat-cancel']) {
        elements[name] = element();
    }
    const send = element();
    const form = elements['chat-form'];
    form.dataset = {url: '/turns/', error: 'error', cancelled: 'cancelled', working: 'working', ...initial};
    form.querySelector = selector => selector.startsWith('button') ? send : {value: 'csrf-token'};
    const document = { getElementById: name => elements[name], createElement: () => element() };
    let uuidCounter = 0;
    const context = { document, fetch, crypto: {randomUUID: () => `test-uuid-${++uuidCounter}`},
        setTimeout: callback => timers.push(callback) };
    vm.runInNewContext(source, context);
    const submit = () => form.listeners.submit({preventDefault() {}});
    const clickCancel = () => elements['chat-cancel'].listeners.click();
    return { elements, send, timers, submit, clickCancel };
}
const ok = payload => ({ok: true, status: 202, json: async () => payload});
const stream = body => ({ok: true, status: 200, text: async () => body});
const flush = () => new Promise(resolve => setImmediate(resolve));

test('uncertain creation is retried only on user action with same key and payload', async () => {
    const calls = [];
    let attempt = 0;
    const ui = setup(async (url, opts) => {
        calls.push({url, opts});
        if (url === '/turns/') {
            if (++attempt === 1) throw new TypeError('network failed');
            return ok({events_url: '/turns/one/events/'});
        }
        return stream('');
    });
    ui.elements['chat-message'].value = 'hello';
    await ui.submit();
    assert.equal(calls.length, 1);
    assert.equal(ui.send.disabled, false);
    assert.equal(ui.elements['chat-message'].readOnly, true);
    await ui.submit();
    await flush();
    assert.equal(calls[0].opts.headers['Idempotency-Key'], calls[1].opts.headers['Idempotency-Key']);
    assert.equal(calls[0].opts.body, calls[1].opts.body);
    assert.equal(calls[1].opts.headers['X-CSRFToken'], 'csrf-token');
    assert.equal(ui.elements['chat-cancel'].disabled, false);
});

test('poll failures preserve cursor, active turn, and cancellation', async () => {
    const calls = [];
    let polls = 0;
    const ui = setup(async (url, opts = {}) => {
        calls.push({url, opts});
        if (url === '/turns/') return ok({events_url: '/turns/one/events/'});
        if (url.endsWith('/cancel/')) return ok({status: 'cancel_requested'});
        if (++polls === 1) return stream('id: signed-one\nevent: message.delta\ndata: {"text":"hello"}\n\n');
        if (polls === 2) throw new TypeError('network failure');
        return stream('id: signed-two\nevent: turn.completed\ndata: {}\n\n');
    });
    ui.elements['chat-message'].value = 'question';
    await ui.submit();
    await flush();
    assert.equal(ui.timers.length, 1);
    await ui.timers.shift()();
    await flush();
    assert.equal(ui.elements['chat-cancel'].disabled, false);
    assert.equal(ui.send.disabled, true);
    assert.equal(ui.timers.length, 1);
    await ui.timers.shift()();
    await flush();
    const requests = calls.filter(call => call.url.endsWith('/events/'));
    assert.equal(requests[1].opts.headers['Last-Event-ID'], 'signed-one');
    assert.equal(requests[2].opts.headers['Last-Event-ID'], 'signed-one');
    assert.equal(ui.elements['chat-messages'].children[1].textContent, 'hello');
    assert.equal(ui.send.disabled, false);
});

test('definitive polling denial does not retry or unlock new turns', async () => {
    const ui = setup(async url => url === '/turns/'
        ? ok({events_url: '/turns/one/events/'})
        : {ok: false, status: 403});
    ui.elements['chat-message'].value = 'question';
    await ui.submit();
    await flush();
    assert.equal(ui.timers.length, 0);
    assert.equal(ui.send.disabled, true);
    assert.equal(ui.elements['composer-status'].textContent, 'error');
});

test('cancel remains actionable after a transient stream error', async () => {
    const calls = [];
    const ui = setup(async (url, opts = {}) => {
        calls.push({url, opts});
        if (url === '/turns/') return ok({events_url: '/turns/one/events/'});
        if (url.endsWith('/cancel/')) return ok({status: 'cancel_requested'});
        return {ok: false, status: 503};
    });
    ui.elements['chat-message'].value = 'question';
    await ui.submit();
    await flush();
    assert.equal(ui.elements['chat-cancel'].disabled, false);
    await ui.clickCancel();
    const cancelRequest = calls.find(call => call.url.endsWith('/cancel/'));
    assert.equal(cancelRequest.opts.method, 'POST');
    assert.equal(cancelRequest.opts.headers['X-CSRFToken'], 'csrf-token');
    assert.equal(ui.send.disabled, true);
});

test('definitive initial rejection releases the composer without a retry', async () => {
    let calls = 0;
    const ui = setup(async () => { calls++; return {ok: false, status: 400}; });
    ui.elements['chat-message'].value = 'question';
    await ui.submit();
    assert.equal(calls, 1);
    assert.equal(ui.timers.length, 0);
    assert.equal(ui.send.disabled, false);
    assert.equal(ui.elements['chat-message'].readOnly, false);
    assert.equal(ui.elements['chat-message'].value, 'question');
});

test('after uncertain create, later denial does not discard original request', async () => {
    const calls = [];
    const ui = setup(async (url, opts) => {
        calls.push(opts);
        if (calls.length === 1) throw new TypeError('lost response');
        return {ok: false, status: 403};
    });
    ui.elements['chat-message'].value = 'question';
    await ui.submit();
    await ui.submit();
    assert.equal(ui.elements['chat-message'].readOnly, true);
    assert.equal(ui.send.disabled, false);
    assert.equal(calls[0].headers['Idempotency-Key'], calls[1].headers['Idempotency-Key']);
    assert.equal(calls[0].body, calls[1].body);
});

test('HTTP 408 on creation preserves the request key until user retry', async () => {
    const calls = [];
    const ui = setup(async (url, opts) => {
        calls.push({url, opts});
        if (url !== '/turns/') return stream('');
        if (calls.length === 1) return {ok: false, status: 408};
        return ok({events_url: '/turns/one/events/'});
    });
    ui.elements['chat-message'].value = 'question';
    await ui.submit();
    assert.equal(ui.elements['chat-message'].readOnly, true);
    await ui.submit();
    assert.equal(calls[0].opts.headers['Idempotency-Key'], calls[1].opts.headers['Idempotency-Key']);
    assert.equal(calls[0].opts.body, calls[1].opts.body);
});

test('HTTP 408 while polling preserves cursor and schedules a retry', async () => {
    let count = 0;
    const calls = [];
    const ui = setup(async (url, opts = {}) => {
        calls.push({url, opts});
        if (url === '/turns/') return ok({events_url: '/turns/one/events/'});
        if (++count === 1) return stream('id: signed-one\nevent: message.delta\ndata: {"text":"hello"}\n\n');
        if (count === 2) return {ok: false, status: 408};
        return stream('id: signed-two\nevent: turn.completed\ndata: {}\n\n');
    });
    ui.elements['chat-message'].value = 'question';
    await ui.submit();
    await flush();
    await ui.timers.shift()();
    await flush();
    assert.equal(ui.timers.length, 1);
    assert.equal(ui.elements['chat-cancel'].disabled, false);
    await ui.timers.shift()();
    await flush();
    const polls = calls.filter(call => call.url.endsWith('/events/'));
    assert.equal(polls[2].opts.headers['Last-Event-ID'], 'signed-one');
    assert.equal(ui.elements['chat-messages'].children[1].textContent, 'hello');
});


test('reload replays the existing active turn and keeps cancellation available', async () => {
    const calls = [];
    const ui = setup(async (url, opts = {}) => {
        calls.push({url, opts});
        if (url.endsWith('/cancel/')) return ok({status: 'cancel_requested'});
        return stream('id: signed-one\nevent: message.delta\ndata: {"text":"hello"}\n\n');
    }, {activeEventsUrl: '/turns/one/events/', activeState: 'running'});
    await flush();
    assert.equal(calls[0].url, '/turns/one/events/');
    assert.equal(ui.send.disabled, true);
    assert.equal(ui.elements['chat-cancel'].disabled, false);
    assert.equal(ui.elements['chat-messages'].children.length, 1);
    assert.equal(ui.elements['chat-messages'].children[0].textContent, 'hello');
    await ui.clickCancel();
    assert.equal(calls[1].url, '/turns/one/cancel/');
    assert.equal(calls[1].opts.headers['X-CSRFToken'], 'csrf-token');
});

test('turn completing after page rendering is replayed once and enables composer', async () => {
    const ui = setup(async () => stream('id: signed-one\nevent: message.delta\ndata: {"text":"answer"}\n\nid: signed-two\nevent: turn.completed\ndata: {}\n\n'),
        {activeEventsUrl: '/turns/one/events/', activeState: 'running'});
    await flush();
    assert.equal(ui.elements['chat-messages'].children.length, 1);
    assert.equal(ui.elements['chat-messages'].children[0].textContent, 'answer');
    assert.equal(ui.send.disabled, false);
    assert.equal(ui.elements['chat-cancel'].disabled, true);
});

test('reattached cancellation in progress does not allow repeated cancellation', async () => {
    const ui = setup(async () => stream(''),
        {activeEventsUrl: '/turns/one/events/', activeState: 'cancel_requested'});
    await flush();
    assert.equal(ui.send.disabled, true);
    assert.equal(ui.elements['chat-cancel'].disabled, true);
});


test('reattached terminal event without deltas displays canonical assistant message', async () => {
    const ui = setup(async () => stream('id: signed-one\nevent: turn.completed\ndata: {"assistant_message":{"content":"answer"}}\n\n'),
        {activeEventsUrl: '/turns/one/events/', activeState: 'running'});
    await flush();
    assert.equal(ui.elements['chat-messages'].children.length, 1);
    assert.equal(ui.elements['chat-messages'].children[0].textContent, 'answer');
    assert.equal(ui.send.disabled, false);
});


test('replayed cancellation request disables cancellation while waiting for terminal', async () => {
    const ui = setup(async () => stream('id: signed-one\nevent: turn.cancel_requested\ndata: {"status":"cancel_requested"}\n\n'),
        {activeEventsUrl: '/turns/one/events/', activeState: 'running'});
    await flush();
    assert.equal(ui.elements['chat-cancel'].disabled, true);
    assert.equal(ui.send.disabled, true);
});


test('interrupted request shows uncertain outcome and does not retry', async () => {
    const calls = [];
    const ui = setup(async url => {
        calls.push(url);
        if (url === '/turns/') return ok({events_url: '/turns/one/events/'});
        return stream('id: signed-one\nevent: turn.failed\ndata: {"error":{"code":"UNAVAILABLE","retryable":false},"reason":"interrupted_unknown"}\n\n');
    }, {interrupted: 'interrupted and not resent'});
    ui.elements['chat-message'].value = 'question';
    await ui.submit();
    await flush();
    assert.equal(ui.elements['composer-status'].textContent, 'interrupted and not resent');
    assert.equal(calls.filter(url => url === '/turns/').length, 1);
    assert.equal(ui.timers.length, 0);
});
