import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Bot, RefreshCw, ShieldCheck } from 'lucide-react';
import { ChatWindow } from './components/ChatWindow';
import { StatusIndicator } from './components/StatusIndicator';
import { TaskPanel } from './components/TaskPanel';
import { WorkspaceInsightsPanel } from './components/WorkspaceInsightsPanel';
import {
  analyzeWriting, createTask, dismissPlannerSuggestion, fetchWorkspaceOverview,
  reviewNotification, reviewWritingSuggestion, sendMessage, toggleTask, deleteNotification, updateTask,
  navigateToTask,
  linkTaskToCurrentContext,
} from './api/client';

export default function App() {
  const [messages, setMessages] = useState([{ role: 'assistant', content: 'Workspace Assistant ready. I observe, plan, validate, and only then execute approved actions.', metadata: { routed_agent: 'coordinator' } }]);
  const [tasks, setTasks] = useState([]);
  const [snapshot, setSnapshot] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [writingSuggestions, setWritingSuggestions] = useState([]);
  const [planner, setPlanner] = useState({ status: null, suggestions: [] });
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const [error, setError] = useState('');
  const refreshInFlight = useRef(false);

  const loadData = useCallback(async () => {
    if (refreshInFlight.current) return;
    refreshInFlight.current = true;
    try {
      const overview = await fetchWorkspaceOverview();
      setTasks(overview.tasks); setSnapshot(overview.snapshot); setNotifications(overview.notifications); setWritingSuggestions(overview.writing_suggestions);
      setPlanner(overview.planner); setSettings(overview.settings); setError('');
    } catch (err) { setError(err.message); }
    finally { refreshInFlight.current = false; }
  }, []);
  useEffect(() => { loadData(); const id = setInterval(loadData, 5000); return () => clearInterval(id); }, [loadData]);

  const handleSendMessage = async (text) => {
    setMessages((items) => [...items, { role: 'user', content: text }]); setLoading(true);
    try {
      const result = await sendMessage(text);
      setMessages((items) => [...items, { role: 'assistant', content: result.response, metadata: { routed_agent: result.routed_agent, tasks_created: result.tasks_created, browser_info: result.browser_info, plan: result.plan, confirmation_id: result.confirmation_id } }]);
      if (voiceEnabled && 'speechSynthesis' in window) window.speechSynthesis.speak(new SpeechSynthesisUtterance(result.response.slice(0, 300)));
      await loadData();
    } catch (err) { setMessages((items) => [...items, { role: 'assistant', content: `Request blocked: ${err.message}`, metadata: { routed_agent: 'coordinator' } }]); }
    finally { setLoading(false); }
  };
  const runWorkspaceAction = async (action) => {
    try {
      setError('');
      await action();
      await loadData();
      return true;
    } catch (err) {
      setError(err.message);
      return false;
    }
  };
  const handleWriting = (text, operation) => runWorkspaceAction(() => analyzeWriting(text, operation));

  return <div className="app-container">
    <aside className="studio-rail"><div className="rail-logo"><Bot size={20} /></div><div className="rail-bottom"><ShieldCheck size={17} color="var(--hf-emerald)" /></div></aside>
    <main className="studio-main">
      <header className="studio-header"><div className="header-left"><div className="studio-title-badge">Digital Workspace Agent</div><span className="studio-pill-tag">STATE → PLAN → VALIDATE → EXECUTE</span></div><button className="btn-hf-ghost" onClick={loadData}><RefreshCw size={13} /> Refresh</button></header>
      {error && <div style={{ padding: '8px 24px', color: '#fda4af', fontSize: 12 }}>Connection: {error}</div>}
      <div className="studio-body">
        <ChatWindow messages={messages} onSendMessage={handleSendMessage} loading={loading} voiceEnabled={voiceEnabled} onToggleVoice={() => setVoiceEnabled((value) => !value)} />
        <aside className="studio-inspector">
          <StatusIndicator snapshot={snapshot} onRefresh={loadData} onTriggerDiff={() => handleSendMessage('What changed while I was away?')} />
          <TaskPanel tasks={tasks} onToggleTask={(id, done) => runWorkspaceAction(() => toggleTask(id, done))} onSetTaskStatus={(id, taskStatus) => runWorkspaceAction(() => updateTask(id, { status: taskStatus }))} onCreateTask={(title) => runWorkspaceAction(() => createTask(title))} onNavigateTask={(id) => runWorkspaceAction(() => navigateToTask(id))} onLinkTask={(id) => runWorkspaceAction(() => linkTaskToCurrentContext(id))} />
          <WorkspaceInsightsPanel notifications={notifications} writingSuggestions={writingSuggestions} planner={planner} settings={settings} onReviewNotification={(id) => runWorkspaceAction(() => reviewNotification(id))} onDeleteNotification={(id) => { if (window.confirm('Permanently delete this notification?')) return runWorkspaceAction(() => deleteNotification(id)); return Promise.resolve(); }} onAnalyzeWriting={handleWriting} onReviewWriting={(id) => runWorkspaceAction(() => reviewWritingSuggestion(id))} onDismissSuggestion={(id) => runWorkspaceAction(() => dismissPlannerSuggestion(id))} onResearch={(query) => handleSendMessage(`Research ${query}`)} />
        </aside>
      </div>
    </main>
  </div>;
}
