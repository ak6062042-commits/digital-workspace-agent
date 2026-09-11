import React, { useState, useEffect, useCallback } from 'react';
import {
  MessageSquare,
  Crosshair,
  CheckSquare,
  RotateCcw,
  Wifi,
  Sparkles
} from 'lucide-react';
import { ChatWindow } from './components/ChatWindow';
import { StatusIndicator } from './components/StatusIndicator';
import { TaskPanel } from './components/TaskPanel';
import {
  sendMessage,
  fetchTasks,
  createTask,
  toggleTask,
  fetchLatestSnapshot,
  reseedDemoData
} from './api/client';

export default function App() {
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' | 'radar' | 'tasks'
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Digital Workspace Agent online. Ready to assist with your active tasks, technical research, and desktop context.',
      metadata: { routed_agent: 'coordinator' }
    }
  ]);
  const [tasks, setTasks] = useState([]);
  const [latestSnapshot, setLatestSnapshot] = useState(null);
  const [chatLoading, setChatLoading] = useState(false);
  const [reseedLoading, setReseedLoading] = useState(false);

  // Initial Load & Continuous Heartbeat Polling
  const loadData = useCallback(async () => {
    try {
      const [tasksData, snapData] = await Promise.all([
        fetchTasks(),
        fetchLatestSnapshot()
      ]);
      setTasks(tasksData);
      setLatestSnapshot(snapData);
    } catch (err) {
      console.warn('Polling warning:', err.message);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 3000);
    return () => clearInterval(interval);
  }, [loadData]);

  // Voice Speech Output (Siri-like Text-To-Speech)
  const speakText = (text) => {
    if (!voiceEnabled || !('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const cleanText = text
      .replace(/[*#`_>]/g, '')
      .replace(/\[(.*?)\]\(.*?\)/g, '$1')
      .slice(0, 300) // Keep voice summary concise like Siri
      .trim();

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.rate = 1.05;
    utterance.pitch = 1.0;
    window.speechSynthesis.speak(utterance);
  };

  // Handle Chat submit
  const handleSendMessage = async (text) => {
    const userMsg = { role: 'user', content: text };
    setMessages(prev => [...prev, userMsg]);
    setChatLoading(true);

    try {
      const result = await sendMessage(text);
      const assistantMsg = {
        role: 'assistant',
        content: result.response,
        metadata: {
          routed_agent: result.routed_agent,
          tasks_created: result.tasks_created,
          state_snapshot: result.state_snapshot,
          browser_info: result.browser_info
        }
      };
      setMessages(prev => [...prev, assistantMsg]);

      // Speak response aloud if voice enabled
      speakText(result.response);

      // If tasks were created, refresh immediately
      if (result.tasks_created && result.tasks_created.length > 0) {
        const freshTasks = await fetchTasks();
        setTasks(freshTasks);
      }
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: `Error coordinating request: ${err.message}. Ensure backend is active on http://127.0.0.1:8000.`,
          metadata: { routed_agent: 'coordinator' }
        }
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  // Toggle Task Completion
  const handleToggleTask = async (taskId, done) => {
    setTasks(prev => prev.map(t => t.id === taskId ? { ...t, done } : t));
    try {
      await toggleTask(taskId, done);
    } catch (err) {
      const fresh = await fetchTasks();
      setTasks(fresh);
    }
  };

  // Quick Add Task
  const handleCreateTask = async (title) => {
    try {
      const newTask = await createTask(title);
      setTasks(prev => [newTask, ...prev]);
    } catch (err) {
      console.error('Failed to create task:', err);
    }
  };

  // Trigger Diff
  const handleTriggerDiff = () => {
    handleSendMessage("What changed while I was away?");
  };

  // Reset Demo Data
  const handleReseed = async () => {
    if (confirm('Reset workspace tasks and state snapshots to clean demo baseline?')) {
      setReseedLoading(true);
      try {
        await reseedDemoData();
        await loadData();
        setMessages([
          {
            role: 'assistant',
            content: 'Workspace state refreshed to baseline demo configuration. Ready for presentation.',
            metadata: { routed_agent: 'coordinator' }
          }
        ]);
      } catch (err) {
        alert(`Reseed failed: ${err.message}`);
      } finally {
        setReseedLoading(false);
      }
    }
  };

  return (
    <div className="app-container">
      {/* 1. Left Slim Studio Rail */}
      <nav className="studio-rail">
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '20px' }}>
          <div className="rail-logo" title="Digital Workspace Agent">
            ◈
          </div>

          <div className="rail-nav">
            <button
              onClick={() => setActiveTab('chat')}
              className={`rail-btn ${activeTab === 'chat' ? 'active' : ''}`}
              title="Assistant Chat"
            >
              <MessageSquare size={18} />
            </button>
            <button
              onClick={() => setActiveTab('radar')}
              className={`rail-btn ${activeTab === 'radar' ? 'active' : ''}`}
              title="Workspace Radar"
            >
              <Crosshair size={18} />
            </button>
            <button
              onClick={() => setActiveTab('tasks')}
              className={`rail-btn ${activeTab === 'tasks' ? 'active' : ''}`}
              title="Workspace Tasks"
            >
              <CheckSquare size={18} />
            </button>
          </div>
        </div>

        <div className="rail-bottom">
          <div style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: 'var(--hf-lime)',
            boxShadow: '0 0 10px var(--hf-lime)'
          }} title="Multi-Agent Mesh Online"></div>
        </div>
      </nav>

      {/* 2. Main Studio Viewport */}
      <div className="studio-main">
        {/* Top Header */}
        <header className="studio-header">
          <div className="header-left">
            <div className="studio-title-badge">
              <span style={{ color: 'var(--hf-lime)' }}>◈</span>
              <span>DIGITAL WORKSPACE AGENT</span>
            </div>
            <span className="studio-pill-tag">
              ⚡ DESKTOP ASSISTANT MESH
            </span>
          </div>

          <div className="header-right">
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--hf-text-secondary)' }}>
              <Wifi size={13} style={{ color: 'var(--hf-emerald)' }} />
              <span>12ms</span>
            </div>

            <button
              onClick={handleReseed}
              disabled={reseedLoading}
              className="btn-hf-ghost"
              title="Reset state to initial demo"
            >
              <RotateCcw size={12} className={reseedLoading ? 'animate-spin' : ''} />
              <span>Reset Demo</span>
            </button>
          </div>
        </header>

        {/* Studio Stage Layout */}
        <div className="studio-body">
          {/* Main Conversational Stream & Floating Dock with Voice Command */}
          <ChatWindow
            messages={messages}
            onSendMessage={handleSendMessage}
            loading={chatLoading}
            voiceEnabled={voiceEnabled}
            onToggleVoice={() => setVoiceEnabled(!voiceEnabled)}
          />

          {/* Right Inspector: Radar Viewport + Tasks */}
          <aside className="studio-inspector">
            <StatusIndicator
              snapshot={latestSnapshot}
              onRefresh={loadData}
              onTriggerDiff={handleTriggerDiff}
            />

            <TaskPanel
              tasks={tasks}
              onToggleTask={handleToggleTask}
              onCreateTask={handleCreateTask}
            />
          </aside>
        </div>
      </div>
    </div>
  );
}
