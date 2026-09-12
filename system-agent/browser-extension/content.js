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

// ---------------------------------------------------------------------------
// Writing Activity Watcher
// Debounces active typing in textareas / inputs / contenteditable regions,
// then sends a snapshot of what's being written to the background worker.
// ---------------------------------------------------------------------------

const WRITING_DEBOUNCE_MS = 2500;
const MIN_TEXT_LENGTH = 40;

let writingDebounceTimer = null;
let lastSentText = "";

function getEditableText(el) {
  if (!el) return "";
  if (el.tagName === "TEXTAREA" || el.tagName === "INPUT") {
    return el.value || "";
  }
  if (el.isContentEditable) {
    return el.innerText || el.textContent || "";
  }
  return "";
}

function isEditableTarget(el) {
  if (!el) return false;
  const tag = el.tagName;
  if (tag === "TEXTAREA") return true;
  if (tag === "INPUT") {
    const type = (el.getAttribute("type") || "text").toLowerCase();
    return ["text", "search", "email", "url", ""].includes(type);
  }
  return !!el.isContentEditable;
}

document.addEventListener("input", (event) => {
  const target = event.target;
  if (!isEditableTarget(target)) return;

  clearTimeout(writingDebounceTimer);
  writingDebounceTimer = setTimeout(() => {
    const text = getEditableText(target).trim();
    if (text.length < MIN_TEXT_LENGTH) return;
    if (text === lastSentText) return;
    lastSentText = text;

    const snippet = text.length > 2000 ? text.slice(0, 2000) : text;

    chrome.runtime.sendMessage({
      action: "writing_activity",
      title: document.title || "Untitled Page",
      url: window.location.href,
      text: snippet
    });
  }, WRITING_DEBOUNCE_MS);
}, true);
