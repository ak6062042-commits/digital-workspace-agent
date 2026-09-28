import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Bot, PanelRightClose, PanelRightOpen, RefreshCw } from 'lucide-react';
import { ChatWindow } from './components/ChatWindow';
import { StatusIndicator } from './components/StatusIndicator';
import { TaskPanel } from './components/TaskPanel';
import { WorkspaceInsightsPanel } from './components/WorkspaceInsightsPanel';
import {
  analyzeWriting, createTask, deleteNotification, dismissPlannerSuggestion, fetchWorkspaceOverview,
  linkTaskToCurrentContext, navigateToTask, reviewNotification, reviewWritingSuggestion, sendMessage,
  toggleTask, updateTask,
} from './api/client';

const welcomeMessage = {
  role: 'assistant',
  content: 'Personal Workspace Assistant ready. Ask me to research a topic, summarize a page, organize tasks, improve writing, or open an app.',
  metadata: { routed_agent: 'coordinator' },
};

export default function App() {
  const [messages, setMessages] = useState([welcomeMessage]);
  const [tasks, setTasks] = useState([]);
  const [snapshot, setSnapshot] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [writingSuggestions, setWritingSuggestions] = useState([]);
  const [planner, setPlanner] = useState({ status: null, suggestions: [] });
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const [error, setError] = useState('');
  const [toast, setToast] = useState('');
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const refreshInFlight = useRef(false);
  const toastTimer = useRef(null);

  const showToast = useCallback((message) => {
    window.clearTimeout(toastTimer.current);
    setToast(message);
    toastTimer.current = window.setTimeout(() => setToast(''), 2600);
  }, []);

  useEffect(() => () => window.clearTimeout(toastTimer.current), []);

  const loadData = useCallback(async () => {
    if (refreshInFlight.current) return false;
    refreshInFlight.current = true;
    try {
      const overview = await fetchWorkspaceOverview();
      setTasks(overview.tasks || []);
      setSnapshot(overview.snapshot || null);
      setNotifications(overview.notifications || []);
      setWritingSuggestions(overview.writing_suggestions || []);
      setPlanner(overview.planner || { status: null, suggestions: [] });
      setSettings(overview.settings || null);
      setLastUpdated(new Date());
      setError('');
      return true;
    } catch (err) {
      setError(err.message);
      return false;
    } finally {
      refreshInFlight.current = false;
    }
  }, []);

  useEffect(() => {
    loadData();
    const id = window.setInterval(loadData, 5000);
    return () => window.clearInterval(id);
  }, [loadData]);

  const handleSendMessage = async (text) => {
    setMessages((items) => [...items, { role: 'user', content: text }]);
    setLoading(true);
    try {
      const result = await sendMessage(text);
      setMessages((items) => [...items, {
        role: 'assistant',
        content: result.response,
        metadata: {
          routed_agent: result.routed_agent,
          tasks_created: result.tasks_created,
          browser_info: result.browser_info,
          research_sources: result.research_sources,
          plan: result.plan,
          confirmation_id: result.confirmation_id,
        },
      }]);
      if (result.routed_agent === 'web') showToast('Research brief is ready. Review the source domains before opening one.');
      if (voiceEnabled && 'speechSynthesis' in window) {
        window.speechSynthesis.speak(new SpeechSynthesisUtterance(result.response.slice(0, 300)));
      }
      await loadData();
    } catch (err) {
      const message = `Request failed: ${err.message}`;
      setMessages((items) => [...items, { role: 'assistant', content: message, metadata: { routed_agent: 'coordinator' } }]);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const runWorkspaceAction = async (action, successMessage = 'Workspace updated') => {
    try {
      setError('');
      await action();
      await loadData();
      showToast(successMessage);
      return true;
    } catch (err) {
      setError(err.message);
      return false;
    }
  };

  const handleRefresh = async () => {
    if (await loadData()) showToast('Workspace refreshed');
  };

  return (
    <div className="app-container">
      <aside className="studio-rail" aria-label="Workspace navigation">
        <div className="rail-logo" title="Digital Workspace Agent"><Bot size={20} /></div>
      </aside>
      <main className="studio-main">
        <header className="studio-header">
          <div className="header-left">
            <div className="studio-title-badge">Digital Workspace Agent</div>
            <span className="studio-pill-tag">PERSONAL WORKSPACE</span>
            {lastUpdated && <span className="sync-caption">Updated {lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>}
          </div>
          <div className="header-actions">
            <button className="btn-hf-ghost" onClick={handleRefresh}><RefreshCw size={13} /> Refresh</button>
            <button className="btn-hf-ghost inspector-toggle" onClick={() => setInspectorOpen((value) => !value)} aria-expanded={inspectorOpen} aria-label={inspectorOpen ? 'Close workspace panel' : 'Open workspace panel'}>
              {inspectorOpen ? <PanelRightClose size={15} /> : <PanelRightOpen size={15} />}
              <span>Workspace</span>
            </button>
          </div>
        </header>
        {error && <div className="connection-banner" role="alert">Connection: {error}</div>}
        {toast && <div className="toast-message" role="status">{toast}</div>}
        <div className="studio-body">
          <ChatWindow
            messages={messages}
            onSendMessage={handleSendMessage}
            onClearMessages={() => { setMessages([welcomeMessage]); showToast('Chat cleared'); }}
            loading={loading}
            voiceEnabled={voiceEnabled}
            onToggleVoice={() => setVoiceEnabled((value) => !value)}
          />
          {inspectorOpen && <button className="inspector-scrim" aria-label="Close workspace panel" onClick={() => setInspectorOpen(false)} />}
          <aside className={`studio-inspector ${inspectorOpen ? 'is-open' : ''}`} aria-label="Workspace panel">
            <StatusIndicator snapshot={snapshot} onRefresh={handleRefresh} onTriggerDiff={() => handleSendMessage('What changed while I was away?')} />
            <TaskPanel
              tasks={tasks}
              onToggleTask={(id, done) => runWorkspaceAction(() => toggleTask(id, done), done ? 'Task marked complete' : 'Task moved back to active')}
              onSetTaskStatus={(id, taskStatus) => runWorkspaceAction(() => updateTask(id, { status: taskStatus }), `Task marked ${taskStatus}`)}
              onCreateTask={(title) => runWorkspaceAction(() => createTask(title), 'Task added to your workspace')}
              onNavigateTask={(id) => runWorkspaceAction(() => navigateToTask(id), 'Opening saved workspace context')}
              onLinkTask={(id) => runWorkspaceAction(() => linkTaskToCurrentContext(id), 'Current workspace linked to task')}
            />
            <WorkspaceInsightsPanel
              notifications={notifications}
              writingSuggestions={writingSuggestions}
              planner={planner}
              settings={settings}
              onReviewNotification={(id) => runWorkspaceAction(() => reviewNotification(id), 'Notification marked reviewed')}
              onDeleteNotification={(id) => {
                if (window.confirm('Permanently delete this notification?')) return runWorkspaceAction(() => deleteNotification(id), 'Notification deleted');
                return Promise.resolve(false);
              }}
              onAnalyzeWriting={(text, operation) => runWorkspaceAction(() => analyzeWriting(text, operation), 'Writing analysis is ready')}
              onReviewWriting={(id) => runWorkspaceAction(() => reviewWritingSuggestion(id), 'Writing suggestion marked reviewed')}
              onDismissSuggestion={(id) => runWorkspaceAction(() => dismissPlannerSuggestion(id), 'Suggestion dismissed')}
              onResearch={(query) => handleSendMessage(`Research ${query}`)}
            />
          </aside>
        </div>
      </main>
    </div>
  );
}
