// Digital Workspace Agent — Browser Content Script
// Extracts readable main content for AI synthesis while stripping layout junk

function extractCleanPageContent() {
  const title = document.title || "Untitled Page";
  const url = window.location.href;

  // Clone document body to sanitize without modifying the live DOM
  const clone = document.body ? document.body.cloneNode(true) : null;
  if (!clone) {
    return { title, url, content: "" };
  }

  // Remove scripts, styles, navigation, footer, and ads
  const selectorsToRemove = [
    "script", "style", "noscript", "iframe", "svg",
    "nav", "header", "footer", "aside",
    ".ad", ".advertisement", "#comments", ".comments"
  ];
  selectorsToRemove.forEach(selector => {
    clone.querySelectorAll(selector).forEach(el => el.remove());
  });

  // Prefer main or article if available
  const mainEl = clone.querySelector("main") || clone.querySelector("article") || clone;
  let text = mainEl.innerText || mainEl.textContent || "";

  // Normalize whitespace
  text = text.replace(/\s+/g, " ").trim();

  // Cap at 3,500 characters for fast, crisp AI processing
  if (text.length > 3500) {
    text = text.slice(0, 3500) + "...";
  }

  return {
    title,
    url,
    content: text
  };
}

// Listen for requests from background worker or popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "extract_page_content") {
    const data = extractCleanPageContent();
    sendResponse(data);
  }
  return true;
});
