// Digital Workspace Agent - Chrome Extension Background Service Worker (MV3)

const BACKEND_SNAPSHOT_URL = "http://localhost:8000/api/snapshot";
const BACKEND_SUMMARIZE_URL = "http://localhost:8000/api/browser/summarize";

let debounceTimer = null;
let lastPostedUrl = null;

// Helper to send snapshot to backend
async function sendSnapshot(tab) {
  if (!tab || !tab.url || tab.url.startsWith("chrome://") || tab.url.startsWith("edge://") || tab.url.startsWith("about:")) {
    return;
  }

  const payload = {
    active_app: "Google Chrome",
    active_window_title: tab.title || "Browser Window",
    browser_url: tab.url,
    browser_tab_title: tab.title || "Untitled Tab",
    captured_at: new Date().toISOString(),
    metadata: {
      source: "browser-extension",
      tab_id: tab.id,
      window_id: tab.windowId
    }
  };

  try {
    const response = await fetch(BACKEND_SNAPSHOT_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (response.ok) {
      lastPostedUrl = tab.url;
      await chrome.storage.local.set({
        lastSync: new Date().toISOString(),
        status: "connected",
        activeTab: { title: tab.title, url: tab.url }
      });
      console.log("[WorkspaceExtension] Snapshot synced:", tab.url);
    } else {
      console.warn("[WorkspaceExtension] Backend returned status:", response.status);
      await chrome.storage.local.set({ status: "backend_error" });
    }
  } catch (err) {
    console.info("[WorkspaceExtension] Backend unreachable:", err.message);
    await chrome.storage.local.set({
      status: "disconnected",
      activeTab: { title: tab.title, url: tab.url }
    });
  }
}

// Debounce state push
function handleTabChange(tabId) {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(async () => {
    try {
      const tab = await chrome.tabs.get(tabId);
      if (tab && tab.url && tab.url !== lastPostedUrl) {
        await sendSnapshot(tab);
      }
    } catch (e) {
      // Tab might have closed
    }
  }, 1200);
}

// Listen for tab activation (switch tab)
chrome.tabs.onActivated.addListener((activeInfo) => {
  handleTabChange(activeInfo.tabId);
});

// Listen for tab updates (URL change / finished loading)
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete" && tab.active) {
    handleTabChange(tabId);
  }
});

// Message listener from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  // Action 1: Manual Tab Sync
  if (request.action === "sync_now") {
    chrome.tabs.query({ active: true, currentWindow: true }, async (tabs) => {
      if (tabs.length > 0) {
        await sendSnapshot(tabs[0]);
        sendResponse({ success: true, tab: tabs[0] });
      } else {
        sendResponse({ success: false, error: "No active tab found" });
      }
    });
    return true;
  }

  // Action 2: AI Page Summarization
  if (request.action === "summarize_active_tab") {
    chrome.tabs.query({ active: true, currentWindow: true }, async (tabs) => {
      if (!tabs || tabs.length === 0) {
        sendResponse({ success: false, error: "No active tab found" });
        return;
      }
      const activeTab = tabs[0];

      try {
        // Request extracted content from content script
        let pageData = null;
        try {
          pageData = await chrome.tabs.sendMessage(activeTab.id, { action: "extract_page_content" });
        } catch (scriptErr) {
          // Fallback: execute script dynamically if tab was opened before extension load
          const injection = await chrome.scripting.executeScript({
            target: { tabId: activeTab.id },
            func: () => {
              const clone = document.body ? document.body.cloneNode(true) : null;
              if (clone) {
                ["script", "style", "noscript", "nav", "footer"].forEach(s => {
                  clone.querySelectorAll(s).forEach(e => e.remove());
                });
                return clone.innerText.slice(0, 3000);
              }
              return "";
            }
          });
          pageData = {
            title: activeTab.title,
            url: activeTab.url,
            content: (injection && injection[0] && injection[0].result) || ""
          };
        }

        // Post to backend AI summarizer
        const res = await fetch(BACKEND_SUMMARIZE_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            url: activeTab.url,
            title: activeTab.title,
            content: pageData ? pageData.content : ""
          })
        });

        if (!res.ok) {
          throw new Error(`AI Backend returned ${res.status}`);
        }

        const summaryResult = await res.json();
        await chrome.storage.local.set({ lastSummary: summaryResult });
        sendResponse({ success: true, data: summaryResult });
      } catch (err) {
        console.error("[WorkspaceExtension] Summarize failed:", err);
        sendResponse({ success: false, error: err.message });
      }
    });
    return true; // Keep channel open for async response
  }
});
