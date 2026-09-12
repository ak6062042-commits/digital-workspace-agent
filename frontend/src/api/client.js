const API_BASE = '/api';
const token = import.meta.env.VITE_API_TOKEN || '';

async function request(path, options = {}) {
  if (!token) throw new Error('VITE_API_TOKEN is not configured. Run the setup script and restart Vite.');
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', 'X-Workspace-Token': token, ...(options.headers || {}) },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed with HTTP ${response.status}`);
  }
  return response.status === 204 ? null : response.json();
}

export const sendMessage = (message, session_id = 'default_session', include_state = true) => request('/chat', { method: 'POST', body: JSON.stringify({ message, session_id, include_state }) });
export const confirmAction = (id, approved) => request(`/actions/${id}/confirm`, { method: 'POST', body: JSON.stringify({ approved }) });
export const fetchTasks = (done = null) => request(`/tasks${done === null ? '' : `?done=${done}`}`);
export const createTask = (title, description = null, due_at = null, status = 'pending') => request('/tasks', { method: 'POST', body: JSON.stringify({ title, description, due_at, status }) });
export const updateTask = (id, update) => request(`/tasks/${id}`, { method: 'PATCH', body: JSON.stringify(update) });
export const toggleTask = (id, done) => updateTask(id, { done });
export const fetchLatestSnapshot = () => request('/snapshot/latest');
export const fetchSnapshotDiff = (limit = 5) => request(`/snapshot/diff?limit=${limit}`);
export const openBrowserUrl = (url) => request('/browser/open', { method: 'POST', body: JSON.stringify({ url }) });
export const fetchNotifications = (reviewed = null) => request(`/notifications${reviewed === null ? '' : `?reviewed=${reviewed}`}`);
export const reviewNotification = (id) => request(`/notifications/${id}/review`, { method: 'PATCH' });
export const deleteNotification = (id) => request(`/notifications/${id}`, { method: 'DELETE' });
export const fetchWritingSuggestions = (reviewed = null) => request(`/writing/suggestions${reviewed === null ? '' : `?reviewed=${reviewed}`}`);
export const analyzeWriting = (text, operation = 'summarize') => request('/writing/analyze', { method: 'POST', body: JSON.stringify({ text, operation, consent: true }) });
export const reviewWritingSuggestion = (id) => request(`/writing/suggestions/${id}/review`, { method: 'PATCH' });
export const fetchPlannerStatus = () => request('/planner/status');
export const fetchPlannerSuggestions = () => request('/planner/suggestions');
export const dismissPlannerSuggestion = (id) => request(`/planner/suggestions/${id}/dismiss`, { method: 'POST' });
export const fetchSettings = () => request('/settings');
