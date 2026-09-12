import React, { useCallback, useEffect, useState } from 'react';
import { Bot, RefreshCw, ShieldCheck } from 'lucide-react';
import { ChatWindow } from './components/ChatWindow';
import { StatusIndicator } from './components/StatusIndicator';
import { TaskPanel } from './components/TaskPanel';
import { WorkspaceInsightsPanel } from './components/WorkspaceInsightsPanel';
import {
  analyzeWriting, createTask, dismissPlannerSuggestion, fetchLatestSnapshot, fetchNotifications,
  fetchPlannerStatus, fetchPlannerSuggestions, fetchSettings, fetchTasks, fetchWritingSuggestions,
  reviewNotification, reviewWritingSuggestion, sendMessage, toggleTask, deleteNotification, updateTask,
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

  const loadData = useCallback(async () => {
    try {
      const [taskData, snapshotData, noteData, writingData, plannerStatus, plannerSuggestions, publicSettings] = await Promise.all([
        fetchTasks(), fetchLatestSnapshot(), fetchNotifications(false), fetchWritingSuggestions(false), fetchPlannerStatus(), fetchPlannerSuggestions(), fetchSettings(),
      ]);
      setTasks(taskData); setSnapshot(snapshotData); setNotifications(noteData); setWritingSuggestions(writingData);
      setPlanner({ status: plannerStatus, suggestions: plannerSuggestions }); setSettings(publicSettings); setError('');
    } catch (err) { setError(err.message); }
  }, []);
  useEffect(() => { loadData(); const id = setInterval(loadData, 10000); return () => clearInterval(id); }, [loadData]);

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
  const handleWriting = async (text, operation) => { try { await analyzeWriting(text, operation); await loadData(); } catch (err) { setError(err.message); } };

  return <div className="app-container">
    <aside className="studio-rail"><div className="rail-logo"><Bot size={20} /></div><div className="rail-bottom"><ShieldCheck size={17} color="var(--hf-emerald)" /></div></aside>
    <main className="studio-main">
      <header className="studio-header"><div className="header-left"><div className="studio-title-badge">Digital Workspace Agent</div><span className="studio-pill-tag">STATE → PLAN → VALIDATE → EXECUTE</span></div><button className="btn-hf-ghost" onClick={loadData}><RefreshCw size={13} /> Refresh</button></header>
      {error && <div style={{ padding: '8px 24px', color: '#fda4af', fontSize: 12 }}>Connection: {error}</div>}
      <div className="studio-body">
        <ChatWindow messages={messages} onSendMessage={handleSendMessage} loading={loading} voiceEnabled={voiceEnabled} onToggleVoice={() => setVoiceEnabled((value) => !value)} />
        <aside className="studio-inspector">
          <StatusIndicator snapshot={snapshot} onRefresh={loadData} onTriggerDiff={() => handleSendMessage('What changed while I was away?')} />
          <TaskPanel tasks={tasks} onToggleTask={async (id, done) => { await toggleTask(id, done); await loadData(); }} onSetTaskStatus={async (id, taskStatus) => { await updateTask(id, { status: taskStatus }); await loadData(); }} onCreateTask={async (title) => { await createTask(title); await loadData(); }} />
          <WorkspaceInsightsPanel notifications={notifications} writingSuggestions={writingSuggestions} planner={planner} settings={settings} onReviewNotification={async (id) => { await reviewNotification(id); await loadData(); }} onDeleteNotification={async (id) => { await deleteNotification(id); await loadData(); }} onAnalyzeWriting={handleWriting} onReviewWriting={async (id) => { await reviewWritingSuggestion(id); await loadData(); }} onDismissSuggestion={async (id) => { await dismissPlannerSuggestion(id); await loadData(); }} />
        </aside>
      </div>
    </main>
  </div>;
}
