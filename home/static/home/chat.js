(() => {
    const form = document.getElementById("chat-form");
    const input = document.getElementById("chat-message");
    const messages = document.getElementById("chat-messages");
    const status = document.getElementById("composer-status");
    const cancel = document.getElementById("chat-cancel");
    const send = form.querySelector('button[type="submit"]');
    const csrf = form.querySelector('[name="csrfmiddlewaretoken"]').value;
    let active = null;

    function addMessage(text) {
        const item = document.createElement("p");
        item.textContent = text;
        messages.appendChild(item);
        return item;
    }
    function finish(message) {
        status.textContent = message;
        active = null;
        send.disabled = false;
        cancel.disabled = true;
    }
    async function poll(turn, cursor, output) {
        try {
            const headers = cursor ? {"Last-Event-ID": cursor} : {};
            const response = await fetch(turn.events_url, {headers, cache: "no-store"});
            if (!response.ok) throw new Error("stream unavailable");
            const body = await response.text();
            for (const frame of body.split("\n\n")) {
                if (!frame.trim()) continue;
                const lines = frame.split("\n");
                const id = lines.find(line => line.startsWith("id: "));
                const type = lines.find(line => line.startsWith("event: "));
                const data = lines.find(line => line.startsWith("data: "));
                if (!id || !type || !data) throw new Error("invalid frame");
                cursor = id.slice(4);
                const event = type.slice(7);
                const payload = JSON.parse(data.slice(6));
                if (event === "message.delta") output.textContent += payload.text;
                if (event === "turn.completed") { finish(""); return; }
                if (event === "turn.cancelled") { finish(form.dataset.cancelled); return; }
                if (event === "turn.failed") { finish(form.dataset.error); return; }
            }
            if (active === turn) setTimeout(() => poll(turn, cursor, output), 500);
        } catch (_) { finish(form.dataset.error); }
    }
    form.addEventListener("submit", async event => {
        event.preventDefault();
        if (active || !input.value.trim()) return;
        send.disabled = true;
        status.textContent = form.dataset.working;
        const message = input.value;
        try {
            const response = await fetch(form.dataset.url, {
                method: "POST",
                headers: {"Content-Type": "application/json", "X-CSRFToken": csrf, "Idempotency-Key": crypto.randomUUID()},
                body: JSON.stringify({message}),
            });
            if (!response.ok) throw new Error("turn unavailable");
            const turn = await response.json();
            active = turn;
            addMessage(message);
            const output = addMessage("");
            input.value = "";
            cancel.disabled = false;
            poll(turn, "", output);
        } catch (_) { finish(form.dataset.error); }
    });
    cancel.addEventListener("click", async () => {
        if (!active) return;
        cancel.disabled = true;
        try {
            const url = active.events_url.replace(/events\/$/, "cancel/");
            const response = await fetch(url, {method: "POST", headers: {"X-CSRFToken": csrf}});
            if (!response.ok) throw new Error("cancel unavailable");
        } catch (_) { status.textContent = form.dataset.error; cancel.disabled = false; }
    });
})();
