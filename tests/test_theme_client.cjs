const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { test } = require("node:test");

const script = fs.readFileSync(path.join(__dirname, "../home/static/home/theme.js"), "utf8");

function page(saved, systemDark = false, hasSelector = true, accountTheme = undefined, scriptTheme = undefined) {
    let stored = saved;
    let mediaChange;
    let ready;
    let selectChange;
    const media = { matches: systemDark, addEventListener: (_, fn) => { mediaChange = fn; } };
    const selector = { value: "", addEventListener: (_, fn) => { selectChange = fn; } };
    const root = { dataset: accountTheme === undefined ? {} : { accountTheme }, style: {} };
    const window = {
        localStorage: { getItem: () => stored, setItem: (_, value) => { stored = value; } },
        matchMedia: () => media,
    };
    const document = {
        documentElement: root,
        currentScript: scriptTheme === undefined ? null : { dataset: { accountTheme: scriptTheme } },
        addEventListener: (_, fn) => { ready = fn; },
        getElementById: () => hasSelector ? selector : null,
    };
    vm.runInNewContext(script, { window, document });
    ready();
    return { root, selector, media, change: () => selectChange(), systemChange: () => mediaChange(), stored: () => stored };
}

test("preference persists across page loads and explicit choice ignores system changes", () => {
    const first = page(null);
    first.selector.value = "dark";
    first.change();
    assert.equal(first.stored(), "dark");
    const next = page(first.stored());
    assert.equal(next.selector.value, "dark");
    assert.equal(next.root.dataset.theme, "dark");
    next.media.matches = false;
    next.systemChange();
    assert.equal(next.root.dataset.theme, "dark");
});

test("invalid stored preference falls back to system and tracks OS changes", () => {
    const view = page("invalid");
    assert.equal(view.selector.value, "system");
    assert.equal(view.root.dataset.theme, "light");
    view.media.matches = true;
    view.systemChange();
    assert.equal(view.root.dataset.theme, "dark");
});

test("system preference follows OS changes on pages without a selector", () => {
    const view = page("system", false, false);
    assert.equal(view.root.dataset.theme, "light");
    view.media.matches = true;
    view.systemChange();
    assert.equal(view.root.dataset.theme, "dark");
});

test("account preference takes precedence over device storage", () => {
    const view = page("light", false, true, "dark");
    assert.equal(view.root.dataset.theme, "dark");
    assert.equal(view.selector.value, "dark");
    view.selector.value = "system";
    view.change();
    assert.equal(view.stored(), "light");
    view.media.matches = true;
    view.systemChange();
    assert.equal(view.root.dataset.theme, "dark");
});

test("admin script data applies account preference before page setup", () => {
    const view = page("light", false, false, undefined, "dark");
    assert.equal(view.root.dataset.accountTheme, "dark");
    assert.equal(view.root.dataset.theme, "dark");
});
