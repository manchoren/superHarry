(() => {
    const form = document.getElementById("guest-chat-form");
    if (!form) return;
    const input = document.getElementById("guest-chat-message");
    const status = document.getElementById("guest-chat-status");
    const messages = document.getElementById("guest-chat-messages");
    const history = [];
    form.addEventListener("submit", async event => {
        event.preventDefault();
        const message = input.value.trim();
        if (!message) return;
        input.disabled = true;
        form.querySelector("button").disabled = true;
        status.textContent = form.dataset.working;
        try {
            const response = await fetch(form.dataset.url, {
                method: "POST",
                headers: {"Content-Type": "application/json", "X-CSRFToken": form.querySelector("[name=csrfmiddlewaretoken]").value},
                body: JSON.stringify({message, history: history.slice(-20)}),
                credentials: "same-origin",
            });
            const body = await response.json();
            if (!response.ok) throw new Error(body.code || "unavailable");
            const user = document.createElement("p"); user.textContent = `You: ${message}`;
            const assistant = document.createElement("p"); assistant.textContent = `Assistant: ${body.answer}`;
            messages.append(user, assistant);
            history.push({role: "user", content: message}, {role: "assistant", content: body.answer});
            input.value = ""; status.textContent = "";
        } catch (_) { status.textContent = form.dataset.error; }
        input.disabled = false;
        form.querySelector("button").disabled = false;
        input.focus();
    });
})();
