(function () {
    "use strict";
    var STORAGE_KEY = "superharry-theme";
    var THEMES = ["light", "dark", "system"];
    function normalizeTheme(value) { return THEMES.indexOf(value) === -1 ? "system" : value; }
    function systemTheme() { return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"; }
    function applyTheme(theme) {
        var resolved = theme === "system" ? systemTheme() : theme;
        document.documentElement.dataset.theme = resolved;
        document.documentElement.style.colorScheme = resolved;
    }
    function readTheme() {
        try { return normalizeTheme(window.localStorage.getItem(STORAGE_KEY)); }
        catch (error) { return "system"; }
    }
    function saveTheme(theme) {
        try { window.localStorage.setItem(STORAGE_KEY, theme); }
        catch (error) { /* Theme switching still works when storage is blocked. */ }
    }
    var theme = readTheme();
    applyTheme(theme);
    document.addEventListener("DOMContentLoaded", function () {
        var selector = document.getElementById("theme-select");
        if (!selector) return;
        selector.value = theme;
        selector.addEventListener("change", function () {
            theme = normalizeTheme(selector.value);
            selector.value = theme;
            saveTheme(theme);
            applyTheme(theme);
        });
        window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function () {
            if (theme === "system") applyTheme(theme);
        });
    });
}());
