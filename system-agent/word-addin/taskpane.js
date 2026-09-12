/* global Office */
const API = "http://localhost:8000/api/writing/analyze";
const BROWSER_API = "http://localhost:8000/api/browser/open";
const $ = (id) => document.getElementById(id);
const setStatus = (message) => { $("status").textContent = message; };

function renderRelatedQueries(queries, token) {
  const related = $("related");
  related.replaceChildren();
  if (!queries?.length) { related.hidden = true; return; }
  const heading = document.createElement("h3");
  heading.textContent = "Related document searches";
  related.appendChild(heading);
  queries.forEach((topic) => {
    if (!topic?.query) return;
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = `Search Chrome: ${topic.label || topic.query}`;
    button.addEventListener("click", async () => {
      try {
        const url = `https://www.google.com/search?q=${encodeURIComponent(topic.query)}`;
        const response = await fetch(BROWSER_API, { method: "POST", headers: { "Content-Type": "application/json", "X-Workspace-Token": token }, body: JSON.stringify({ url }) });
        const data = await response.json();
        if (!response.ok || data.status !== "success") throw new Error(data.detail || "Chrome could not be opened");
        setStatus("Opened this related search in Chrome.");
      } catch (error) { setStatus(error.message); }
    });
    related.appendChild(button);
  });
  related.hidden = related.children.length === 0;
}

Office.onReady(() => {
  $("token").value = localStorage.getItem("workspaceApiToken") || "";
  $("analyze").addEventListener("click", () => {
    const token = $("token").value.trim();
    if (!token) return setStatus("Paste the local API token from .env first.");
    localStorage.setItem("workspaceApiToken", token);
    setStatus("Reading only the current Word selection…");
    Office.context.document.getSelectedDataAsync(Office.CoercionType.Text, async (result) => {
      const text = (result.value || "").trim();
      if (result.status !== Office.AsyncResultStatus.Succeeded || !text) return setStatus("Select a paragraph or sentence in Word, then try again.");
      try {
        const response = await fetch(API, { method: "POST", headers: { "Content-Type": "application/json", "X-Workspace-Token": token }, body: JSON.stringify({ title: "Microsoft Word selection", text, operation: $("operation").value, consent: true }) });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Analysis failed");
        $("result").hidden = false; $("result").textContent = data.suggestion_text;
        renderRelatedQueries(data.related_queries, token);
        setStatus("Improvement and related-document searches are ready.");
      } catch (error) { setStatus(error.message); }
    });
  });
});
