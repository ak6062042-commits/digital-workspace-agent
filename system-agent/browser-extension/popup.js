// Digital Workspace Agent — Browser Companion Popup Controller

document.addEventListener("DOMContentLoaded", async () => {
  const statusBadge = document.getElementById("status-badge");
  const statusText = document.getElementById("status-text");
  const tabTitleEl = document.getElementById("tab-title");
  const tabUrlEl = document.getElementById("tab-url");
  const lastSyncEl = document.getElementById("last-sync");
  const syncBtn = document.getElementById("sync-btn");

  const aiBtn = document.getElementById("ai-btn");
  const aiBtnText = document.getElementById("ai-btn-text");
  const aiResultsBox = document.getElementById("ai-results");
  const aiTagEl = document.getElementById("ai-tag");
  const aiSummaryEl = document.getElementById("ai-summary");
  const aiTakeawaysEl = document.getElementById("ai-takeaways");
  const addTaskBtn = document.getElementById("add-task-btn");
  const taskBtnText = document.getElementById("task-btn-text");

  let currentSuggestedTask = "";
  let currentActiveTab = null;

  // Read current active tab
  try {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tabs && tabs.length > 0) {
      currentActiveTab = tabs[0];
      tabTitleEl.textContent = currentActiveTab.title || "Untitled Tab";
      tabUrlEl.textContent = currentActiveTab.url || "about:blank";
    } else {
      tabTitleEl.textContent = "No active tab";
      tabUrlEl.textContent = "-";
    }
  } catch (err) {
    tabTitleEl.textContent = "Unable to inspect tab";
    tabUrlEl.textContent = err.message;
  }

  // Check cached status & summary
  chrome.storage.local.get(["lastSync", "status", "lastSummary"], (data) => {
    if (data.lastSync) {
      const date = new Date(data.lastSync);
      lastSyncEl.textContent = date.toLocaleTimeString();
    }
    if (data.status === "disconnected" || data.status === "backend_error") {
      statusBadge.classList.add("disconnected");
      statusText.textContent = "Offline";
    } else {
      statusBadge.classList.remove("disconnected");
      statusText.textContent = "Connected";
    }

    // Restore last summary if for current URL
    if (data.lastSummary && currentActiveTab && data.lastSummary.url === currentActiveTab.url) {
      renderSummary(data.lastSummary);
    }
  });

  function renderSummary(summaryData) {
    aiResultsBox.style.display = "block";
    aiTagEl.textContent = summaryData.work_context || "Technical Research";
    aiSummaryEl.textContent = summaryData.summary || "No summary available.";

    aiTakeawaysEl.innerHTML = "";
    if (summaryData.key_takeaways && summaryData.key_takeaways.length > 0) {
      summaryData.key_takeaways.forEach(item => {
        const li = document.createElement("li");
        li.textContent = item;
        aiTakeawaysEl.appendChild(li);
      });
    }

    if (summaryData.suggested_task) {
      currentSuggestedTask = summaryData.suggested_task;
      taskBtnText.textContent = `Add: "${summaryData.suggested_task.slice(0, 32)}..."`;
      addTaskBtn.style.display = "flex";
    } else {
      addTaskBtn.style.display = "none";
    }
  }

  // 1. Trigger AI Page Summarization
  aiBtn.addEventListener("click", () => {
    aiBtn.disabled = true;
    aiBtnText.textContent = "⚡ Analyzing Page with AI...";

    chrome.runtime.sendMessage({ action: "summarize_active_tab" }, (response) => {
      aiBtn.disabled = false;
      aiBtnText.textContent = "✨ Re-Analyze Tab with AI";

      if (response && response.success && response.data) {
        renderSummary(response.data);
        lastSyncEl.textContent = new Date().toLocaleTimeString();
        statusBadge.classList.remove("disconnected");
        statusText.textContent = "Analyzed";
      } else {
        alert("Failed to generate AI summary: " + (response ? response.error : "Backend error"));
      }
    });
  });

  // 2. Convert AI Takeaway into Workspace Task
  addTaskBtn.addEventListener("click", async () => {
    if (!currentSuggestedTask) return;
    addTaskBtn.disabled = true;
    taskBtnText.textContent = "Adding to Task Pipeline...";

    try {
      const res = await fetch("http://localhost:8000/api/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: currentSuggestedTask,
          description: `Extracted via Browser AI Companion from: ${currentActiveTab ? currentActiveTab.url : "Browser"}`
        })
      });

      if (res.ok) {
        taskBtnText.textContent = "✅ Saved to Agent Tasks!";
        setTimeout(() => {
          taskBtnText.textContent = `Task Saved: "${currentSuggestedTask.slice(0, 24)}..."`;
        }, 2000);
      } else {
        taskBtnText.textContent = "Failed to save task";
        addTaskBtn.disabled = false;
      }
    } catch (err) {
      taskBtnText.textContent = "Error saving task";
      addTaskBtn.disabled = false;
    }
  });

  // 3. Manual Tab Sync to Agent
  syncBtn.addEventListener("click", () => {
    syncBtn.disabled = true;
    syncBtn.textContent = "Syncing...";

    chrome.runtime.sendMessage({ action: "sync_now" }, (response) => {
      syncBtn.disabled = false;
      syncBtn.textContent = "⟳ Sync Tab State to Agent";
      if (response && response.success) {
        lastSyncEl.textContent = new Date().toLocaleTimeString();
        statusBadge.classList.remove("disconnected");
        statusText.textContent = "Synced";
      } else {
        statusBadge.classList.add("disconnected");
        statusText.textContent = "Offline";
      }
    });
  });
});
