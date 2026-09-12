// Privacy-first MV3 companion. It never records typing or page content in the background.
const API_BASE = "http://localhost:8000/api";

async function getConfig() {
  const stored = await chrome.storage.local.get(["apiToken", "stateSyncEnabled"]);
  return { apiToken: stored.apiToken || "", stateSyncEnabled: stored.stateSyncEnabled === true };
}

async function apiFetch(path, options = {}) {
  const { apiToken } = await getConfig();
  if (!apiToken) throw new Error("Set your local API token in the extension first.");
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", "X-Workspace-Token": apiToken, ...(options.headers || {}) }
  });
  if (!response.ok) throw new Error(`Backend returned ${response.status}`);
  return response.json();
}

async function sendSnapshot(tab) {
  const { stateSyncEnabled } = await getConfig();
  if (!stateSyncEnabled || !tab?.url || /^(chrome|edge|about):/.test(tab.url)) return;
  await apiFetch("/snapshot", {
    method: "POST",
    body: JSON.stringify({
      active_app: "Google Chrome", active_window_title: tab.title || "Browser Window",
      browser_url: tab.url, browser_tab_title: tab.title || "Untitled Tab",
      captured_at: new Date().toISOString(), metadata: { source: "browser-extension" }
    })
  });
  await chrome.storage.local.set({ lastSync: new Date().toISOString(), status: "connected", activeTab: { title: tab.title, url: tab.url } });
}

// State metadata sync is explicitly enabled in the popup. No content is captured here.
chrome.tabs.onActivated.addListener(async ({ tabId }) => {
  try { await sendSnapshot(await chrome.tabs.get(tabId)); } catch { await chrome.storage.local.set({ status: "disconnected" }); }
});
chrome.tabs.onUpdated.addListener(async (_tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete" && tab.active) {
    try { await sendSnapshot(tab); } catch { await chrome.storage.local.set({ status: "disconnected" }); }
  }
});

function extractPageContent() {
  const clone = document.body?.cloneNode(true);
  if (!clone) return { title: document.title, url: location.href, content: "" };
  clone.querySelectorAll("script,style,noscript,iframe,svg,nav,header,footer,aside").forEach((node) => node.remove());
  const main = clone.querySelector("main,article") || clone;
  return { title: document.title, url: location.href, content: (main.innerText || "").replace(/\s+/g, " ").trim().slice(0, 4000) };
}
function extractSelection() {
  return { title: document.title, url: location.href, text: String(window.getSelection?.() || "").trim().slice(0, 2000) };
}

chrome.runtime.onMessage.addListener((request, _sender, sendResponse) => {
  (async () => {
    try {
      if (request.action === "save_settings") {
        await chrome.storage.local.set({ apiToken: request.apiToken || "", stateSyncEnabled: request.stateSyncEnabled === true });
        sendResponse({ success: true }); return;
      }
      if (request.action === "sync_now") {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        await sendSnapshot(tab); sendResponse({ success: true, tab }); return;
      }
      if (request.action === "summarize_active_tab") {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        const [{ result: page }] = await chrome.scripting.executeScript({ target: { tabId: tab.id }, func: extractPageContent });
        const data = await apiFetch("/browser/summarize", { method: "POST", body: JSON.stringify({ ...page, consent: true }) });
        await chrome.storage.local.set({ lastSummary: data }); sendResponse({ success: true, data }); return;
      }
      if (request.action === "analyze_selection") {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        const [{ result: selection }] = await chrome.scripting.executeScript({ target: { tabId: tab.id }, func: extractSelection });
        if (!selection.text) throw new Error("Select text on the page first. Nothing is captured automatically.");
        const data = await apiFetch("/writing/analyze", { method: "POST", body: JSON.stringify({ ...selection, operation: request.operation || "summarize", consent: true }) });
        sendResponse({ success: true, data }); return;
      }
      sendResponse({ success: false, error: "Unknown action" });
    } catch (error) { sendResponse({ success: false, error: error.message }); }
  })();
  return true;
});
