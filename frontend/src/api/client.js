// Digital Workspace Agent - API Client

const API_BASE = '/api';

export async function sendMessage(message, sessionId = 'default_session', includeState = true) {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      session_id: sessionId,
      include_state: includeState
    })
  });
  if (!response.ok) {
    throw new Error(`Chat request failed with HTTP ${response.status}`);
  }
  return await response.json();
}

export async function fetchTasks(done = null) {
  let url = `${API_BASE}/tasks`;
  if (done !== null) {
    url += `?done=${done}`;
  }
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch tasks: ${response.status}`);
  }
  return await response.json();
}

export async function createTask(title, description = null, dueAt = null) {
  const response = await fetch(`${API_BASE}/tasks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      title,
      description,
      due_at: dueAt
    })
  });
  if (!response.ok) {
    throw new Error(`Failed to create task: ${response.status}`);
  }
  return await response.json();
}

export async function toggleTask(taskId, done) {
  const response = await fetch(`${API_BASE}/tasks/${taskId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ done })
  });
  if (!response.ok) {
    throw new Error(`Failed to update task: ${response.status}`);
  }
  return await response.json();
}

export async function fetchLatestSnapshot() {
  const response = await fetch(`${API_BASE}/snapshot/latest`);
  if (!response.ok) {
    throw new Error(`Failed to fetch latest snapshot: ${response.status}`);
  }
  return await response.json();
}

export async function fetchSnapshotDiff(limit = 5) {
  const response = await fetch(`${API_BASE}/snapshot/diff?limit=${limit}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch snapshot diff: ${response.status}`);
  }
  return await response.json();
}

export async function reseedDemoData() {
  const response = await fetch(`${API_BASE}/demo/seed`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  });
  if (!response.ok) {
    throw new Error(`Failed to reseed demo data: ${response.status}`);
  }
  return await response.json();
}

export async function openBrowserUrl(url) {
  const response = await fetch(`${API_BASE}/browser/open`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url })
  });
  if (!response.ok) {
    throw new Error(`Failed to open URL: ${response.status}`);
  }
  return await response.json();
}
