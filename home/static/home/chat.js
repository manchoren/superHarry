(() => {
    const form = document.getElementById("chat-form");
    const input = document.getElementById("chat-message");
    const messages = document.getElementById("chat-messages");
    const status = document.getElementById("composer-status");
    const cancel = document.getElementById("chat-cancel");
    const send = form.querySelector('button[type="submit"]');
    const csrf = form.querySelector('[name="csrfmiddlewaretoken"]').value;
    let active = null;
    let pending = null;
    let submitting = false;

    function addMessage(text) {
        const item = document.createElement("p");
        item.textContent = text;
        messages.appendChild(item);
        return item;
    }
    function finish(message) {
        status.textContent = message;
        active = null;
        pending = null;
        send.disabled = false;
        input.readOnly = false;
        cancel.disabled = true;
    }
    function schedulePoll(turn, delay) {
        if (active === turn) setTimeout(() => poll(turn), delay);
    }
    function transientStatus(code) {
        return code === 408 || code === 429 || code >= 500;
    }
    async function poll(turn) {
        if (active !== turn) return;
        let response;
        let body;
        try {
            const headers = turn.cursor ? {"Last-Event-ID": turn.cursor} : {};
            response = await fetch(turn.events_url, {headers, cache: "no-store"});
            if (!response.ok) {
                if (!transientStatus(response.status)) {
                    status.textContent = form.dataset.error;
                    return;
                }
                throw new Error("stream unavailable");
            }
            body = await response.text();
        } catch (_) {
            if (active === turn) {
                status.textContent = form.dataset.error;
                turn.retryDelay = Math.min((turn.retryDelay || 500) * 2, 8000);
                schedulePoll(turn, turn.retryDelay);
            }
            return;
        }
        if (active !== turn) return;
        try {
            for (const frame of body.split("\n\n")) {
                if (!frame.trim()) continue;
                const lines = frame.split("\n");
                const id = lines.find(line => line.startsWith("id: "));
                const type = lines.find(line => line.startsWith("event: "));
                const data = lines.find(line => line.startsWith("data: "));
                if (!id || !type || !data) throw new Error("invalid frame");
                const event = type.slice(7);
                const payload = JSON.parse(data.slice(6));
                if (event === "message.delta") {
                    if (typeof payload.text !== "string") throw new Error("invalid delta");
                    turn.output.textContent += payload.text;
                }
                turn.cursor = id.slice(4);
                if (event === "turn.cancel_requested") cancel.disabled = true;
                if (event === "turn.completed") {
                    if (!turn.output.textContent && typeof payload.assistant_message?.content === "string") {
                        turn.output.textContent = payload.assistant_message.content;
                    }
                    const usage = payload.context_usage;
                    if (usage && Number.isSafeInteger(usage.input_tokens) && Number.isSafeInteger(usage.capacity)
                            && usage.capacity > 0 && usage.input_tokens >= 0 && usage.input_tokens <= usage.capacity) {
                        const container = document.createElement("div");
                        container.className = "context-usage";
                        const label = document.createElement("span");
                        label.textContent = `${form.dataset.contextLabel}: ${usage.input_tokens} / ${usage.capacity} ${form.dataset.contextUnit}`;
                        const meter = document.createElement("meter");
                        meter.min = 0;
                        meter.max = usage.capacity;
                        meter.value = usage.input_tokens;
                        meter.setAttribute("aria-label", form.dataset.contextLabel);
                        container.append(label, meter);
                        turn.output.after(container);
                    }
                    finish("");
                    return;
                }
                if (event === "turn.cancelled") { finish(form.dataset.cancelled); return; }
                if (event === "turn.failed") { finish(payload.reason === "interrupted_unknown" ? form.dataset.interrupted : form.dataset.error); return; }
            }
        } catch (_) {
            status.textContent = form.dataset.error;
            return;
        }
        turn.retryDelay = 500;
        status.textContent = form.dataset.working;
        schedulePoll(turn, 500);
    }
    form.addEventListener("submit", async event => {
        event.preventDefault();
        if (active || submitting || (!pending && !input.value.trim())) return;
        if (!pending) {
            pending = {message: input.value, key: crypto.randomUUID(), uncertain: false};
            input.readOnly = true;
        }
        submitting = true;
        send.disabled = true;
        status.textContent = form.dataset.working;
        try {
            const response = await fetch(form.dataset.url, {
                method: "POST",
                headers: {"Content-Type": "application/json", "X-CSRFToken": csrf, "Idempotency-Key": pending.key},
                body: JSON.stringify({message: pending.message}),
            });
            if (!response.ok) {
                if (!pending.uncertain && !transientStatus(response.status)) {
                    finish(form.dataset.error);
                    return;
                }
                throw new Error("turn unavailable");
            }
            const turn = await response.json();
            if (typeof turn.events_url !== "string" || !turn.events_url.endsWith("/events/")) {
                throw new Error("invalid turn response");
            }
            active = turn;
            turn.cursor = "";
            turn.retryDelay = 500;
            addMessage(pending.message);
            turn.output = addMessage("");
            pending = null;
            input.value = "";
            input.readOnly = false;
            cancel.disabled = false;
            poll(turn);
        } catch (_) {
            pending.uncertain = true;
            status.textContent = form.dataset.error;
            send.disabled = false;
        } finally {
            submitting = false;
        }
    });
    if (form.dataset.activeEventsUrl) {
        active = {
            events_url: form.dataset.activeEventsUrl,
            cursor: "",
            retryDelay: 500,
            output: addMessage(""),
        };
        send.disabled = true;
        cancel.disabled = form.dataset.activeState === "cancel_requested";
        status.textContent = form.dataset.working;
        poll(active);
    }
    cancel.addEventListener("click", async () => {
        if (!active) return;
        const turn = active;
        cancel.disabled = true;
        try {
            const url = turn.events_url.replace(/events\/$/, "cancel/");
            const response = await fetch(url, {method: "POST", headers: {"X-CSRFToken": csrf}});
            if (!response.ok) throw new Error("cancel unavailable");
        } catch (_) {
            if (active === turn) {
                status.textContent = form.dataset.error;
                cancel.disabled = false;
            }
        }
    });
})();
