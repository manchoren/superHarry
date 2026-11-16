(function () {
  const button = document.getElementById("push-to-talk");
  const cancel = document.getElementById("push-to-talk-cancel");
  const status = document.getElementById("push-to-talk-status");
  const text = document.getElementById("chat-message");
  if (!button || !cancel || !status || !navigator.mediaDevices || !window.MediaRecorder) return;
  let recorder, chunks = [], requestId;
  const csrf = document.querySelector("[name=csrfmiddlewaretoken]").value;
  button.addEventListener("click", async () => {
    if (recorder) { recorder.stop(); return; }
    let stream;
    try { stream = await navigator.mediaDevices.getUserMedia({audio: true}); }
    catch (error) { status.textContent = "Microphone unavailable; use the text box."; return; }
    recorder = new MediaRecorder(stream); chunks = [];
    recorder.ondataavailable = e => { if (e.data.size) chunks.push(e.data); };
    recorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop());
      const form = new FormData();
      const blob = new Blob(chunks, {type: recorder.mimeType || "audio/webm"});
      form.append("audio", blob, "push-to-talk.webm");
      form.append("text_fallback", text.value || "");
      const response = await fetch(button.dataset.url, {method: "POST", body: form, headers: {"X-CSRFToken": csrf}});
      const data = await response.json(); requestId = data.request_id;
      status.textContent = data.state === "unavailable" ? (data.text_fallback || "Local audio is unavailable; use the text box.") : data.state;
      cancel.disabled = !requestId;
      recorder = null;
    };
    button.textContent = "Stop recording"; cancel.disabled = false; status.textContent = "Recording…"; recorder.start();
  });
  cancel.addEventListener("click", async () => {
    if (recorder) recorder.stop();
    if (!requestId) return;
    const url = button.dataset.cancelTemplate.replace("00000000-0000-0000-0000-000000000000", requestId);
    await fetch(url, {method: "POST", headers: {"X-CSRFToken": csrf}}); status.textContent = "Audio cancelled."; cancel.disabled = true;
  });
}());
