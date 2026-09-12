// Popup controls are explicit user gestures; no typed text is collected in the background.
document.addEventListener("DOMContentLoaded", async () => {
  const byId = (id) => document.getElementById(id);
  const statusText = byId("status-text");
  const statusBadge = byId("status-badge");
  const tabTitle = byId("tab-title");
  const tabUrl = byId("tab-url");
  const tokenInput = byId("api-token");
  const stateSync = byId("state-sync-enabled");
  let suggestedTask = "";

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  tabTitle.textContent = tab?.title || "No active tab";
  tabUrl.textContent = tab?.url || "-";
  const stored = await chrome.storage.local.get(["apiToken", "stateSyncEnabled", "lastSummary"]);
  tokenInput.value = stored.apiToken || "";
  stateSync.checked = stored.stateSyncEnabled === true;

  function setStatus(text, offline = false) {
    statusText.textContent = text;
    statusBadge.classList.toggle("disconnected", offline);
  }
  function send(action, extra = {}) {
    return new Promise((resolve) => chrome.runtime.sendMessage({ action, ...extra }, resolve));
  }
  function renderSummary(data) {
    byId("ai-results").style.display = "block";
    const isWritingImprovement = Boolean(data.suggestion_text);
    byId("ai-tag").textContent = isWritingImprovement ? "Writing improvement" : (data.work_context || "Local analysis");
    byId("ai-summary").textContent = data.suggestion_text || data.summary || "No analysis returned.";
    const list = byId("ai-takeaways"); list.replaceChildren();
    const takeaways = data.key_takeaways || (data.keywords?.length ? [`Keywords: ${data.keywords.join(", ")}`] : []);
    takeaways.forEach((item) => { const li = document.createElement("li"); li.textContent = item; list.appendChild(li); });
    const relatedSearches = byId("related-searches"); relatedSearches.replaceChildren();
    (data.related_queries || []).forEach((topic) => {
      if (!topic?.query) return;
      const button = document.createElement("button");
      button.type = "button"; button.className = "btn-sync";
      button.textContent = `Search Chrome: ${topic.label || topic.query}`;
      button.addEventListener("click", () => chrome.tabs.create({ url: `https://www.google.com/search?q=${encodeURIComponent(topic.query)}` }));
      relatedSearches.appendChild(button);
    });
    suggestedTask = data.suggested_task || "";
    byId("add-task-btn").style.display = suggestedTask ? "flex" : "none";
  }
  if (stored.lastSummary?.url === tab?.url) renderSummary(stored.lastSummary);

  byId("save-settings-btn").addEventListener("click", async () => {
    await send("save_settings", { apiToken: tokenInput.value.trim(), stateSyncEnabled: stateSync.checked });
    setStatus("Settings saved");
  });
  byId("sync-btn").addEventListener("click", async () => {
    if (!stateSync.checked) return setStatus("Enable metadata sync first", true);
    const response = await send("sync_now");
    setStatus(response?.success ? "Synced" : (response?.error || "Offline"), !response?.success);
  });
  byId("ai-btn").addEventListener("click", async () => {
    byId("ai-btn").disabled = true; byId("ai-btn-text").textContent = "Analyzing locally...";
    const response = await send("summarize_active_tab");
    byId("ai-btn").disabled = false; byId("ai-btn-text").textContent = "Summarize Tab";
    if (response?.success) { renderSummary(response.data); setStatus("Analyzed"); }
    else setStatus(response?.error || "Analysis failed", true);
  });
  byId("selection-btn").addEventListener("click", async () => {
    byId("selection-btn").disabled = true;
    const originalText = byId("selection-btn").textContent;
    byId("selection-btn").textContent = "Improving selected text...";
    const response = await send("analyze_selection", { operation: "improve" });
    byId("selection-btn").disabled = false;
    byId("selection-btn").textContent = originalText;
    if (response?.success) { renderSummary(response.data); setStatus("Selection analyzed"); }
    else setStatus(response?.error || "Analysis failed", true);
  });
  byId("add-task-btn").addEventListener("click", async () => {
    if (!suggestedTask) return;
    // Task creation stays a deliberate UI action. The dashboard is preferred for detailed task fields.
    setStatus("Create this task in the dashboard");
  });
  setStatus(stored.apiToken ? "Ready" : "Token required", !stored.apiToken);
});
