/** LatticeFlow engineering chatbot (OpenAI). */
const chatPanel = document.getElementById("chat-panel");
const chatFab = document.getElementById("chat-fab");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const chatMessages = document.getElementById("chat-messages");
const chatSettings = document.getElementById("chat-settings");
const chatApiKey = document.getElementById("chat-api-key");

let chatHistory = [];

function getApiKey() {
  return (chatApiKey?.value || localStorage.getItem("latticeOpenAIKey") || "").trim();
}

if (chatApiKey) {
  const saved = localStorage.getItem("latticeOpenAIKey");
  if (saved) chatApiKey.value = saved;
  chatApiKey.addEventListener("change", () => {
    const k = chatApiKey.value.trim();
    if (k) localStorage.setItem("latticeOpenAIKey", k);
  });
}

function appendMsg(text, role) {
  const div = document.createElement("div");
  div.className = `chat-msg ${role}`;
  div.textContent = text;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return div;
}

chatFab?.addEventListener("click", () => {
  chatPanel.classList.toggle("hidden");
  if (!chatPanel.classList.contains("hidden")) chatInput?.focus();
});

document.getElementById("chat-close")?.addEventListener("click", () => {
  chatPanel.classList.add("hidden");
});

document.getElementById("chat-settings-btn")?.addEventListener("click", () => {
  chatSettings.classList.toggle("hidden");
});

chatForm?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const msg = chatInput.value.trim();
  if (!msg) return;

  appendMsg(msg, "user");
  chatInput.value = "";
  chatHistory.push({ role: "user", content: msg });

  const thinking = appendMsg("Thinking…", "bot thinking");
  const btn = chatForm.querySelector("button[type=submit]");
  btn.disabled = true;

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: msg,
        history: chatHistory.slice(0, -1),
        analysis: window.lastReport && window.lastResults
          ? { report: window.lastReport, results: window.lastResults }
          : null,
        api_key: getApiKey() || undefined,
      }),
    });

    let data;
    try {
      data = await res.json();
    } catch {
      data = {};
    }

    thinking.remove();

    if (res.status === 404) {
      appendMsg(
        "Chat API not found — the server is running an old version. "
        + "Close the terminal, run RUN_SITE.bat again, then refresh this page (Ctrl+Shift+R).",
        "bot"
      );
      return;
    }

    if (!res.ok) {
      appendMsg(data.error || `Server error (${res.status}). Restart RUN_SITE.bat and try again.`, "bot");
      return;
    }

    const reply = data.reply || "No response.";
    appendMsg(reply, "bot");
    chatHistory.push({ role: "assistant", content: reply });
  } catch (err) {
    thinking.remove();
    appendMsg(
      "Could not connect to the server. Run RUN_SITE.bat, keep the window open, "
      + "then open http://localhost:5050",
      "bot"
    );
  } finally {
    btn.disabled = false;
  }
});
