import React, { useState } from 'react';
import { Bell, BrainCircuit, FileText, ShieldCheck, Check, Trash2 } from 'lucide-react';

export function WorkspaceInsightsPanel({ notifications, writingSuggestions, planner, settings, onReviewNotification, onDeleteNotification, onAnalyzeWriting, onReviewWriting, onDismissSuggestion, onResearch }) {
  const [text, setText] = useState('');
  const [operation, setOperation] = useState('improve');
  const [busy, setBusy] = useState(false);
  const analyze = async (event) => {
    event.preventDefault();
    if (!text.trim()) return;
    setBusy(true);
    await onAnalyzeWriting(text.trim(), operation);
    setText(''); setBusy(false);
  };
  return (
    <>
      <div className="inspector-card">
        <div className="inspector-header"><div className="inspector-title"><ShieldCheck size={13} style={{ color: 'var(--hf-lime)' }} /> Privacy status</div></div>
        <div style={{ fontSize: '11px', color: 'var(--hf-text-secondary)', lineHeight: 1.5 }}>
          Browser typing capture: <strong style={{ color: settings?.capture_enabled ? 'var(--hf-amber)' : 'var(--hf-emerald)' }}>{settings?.capture_enabled ? 'enabled' : 'disabled by default'}</strong>.<br />
          Writing and page analysis require an explicit action. Stored snapshots expire automatically.
        </div>
      </div>
      <div className="inspector-card">
        <div className="inspector-header"><div className="inspector-title"><Bell size={13} style={{ color: 'var(--hf-lime)' }} /> Notifications</div><span className="studio-pill-tag">{notifications.length}</span></div>
        {notifications.slice(0, 3).map((note) => <div key={note.id} className="task-item-hf"><div style={{ flex: 1, fontSize: '11px' }}><strong>{note.source}</strong><br />{note.summary}</div><button className="btn-hf-ghost" onClick={() => onReviewNotification(note.id)}><Check size={12} /></button><button className="btn-hf-ghost" onClick={() => onDeleteNotification(note.id)}><Trash2 size={12} /></button></div>)}
        {!notifications.length && <div style={{ fontSize: '11px', color: 'var(--hf-text-muted)' }}>No unread notifications.</div>}
      </div>
      <div className="inspector-card">
        <div className="inspector-header"><div className="inspector-title"><FileText size={13} style={{ color: 'var(--hf-lime)' }} /> Writing improvements</div></div>
        <form onSubmit={analyze}><textarea value={text} onChange={(event) => setText(event.target.value)} maxLength={2000} placeholder="Paste text you want analyzed. Nothing is captured automatically." className="input-hf" style={{ width: '100%', minHeight: 72, border: '1px solid var(--hf-border-subtle)', padding: 8, marginBottom: 8 }} />
          <div style={{ display: 'flex', gap: 6 }}><select value={operation} onChange={(event) => setOperation(event.target.value)} className="input-hf" style={{ border: '1px solid var(--hf-border-subtle)', padding: 6 }}><option value="improve">Improve</option><option value="summarize">Summarize</option><option value="explain">Explain</option><option value="ideas">Ideas</option></select><button className="btn-hf-primary" disabled={busy || !text.trim()}>{busy ? 'Analyzing…' : 'Analyze locally'}</button></div>
        </form>
        {writingSuggestions.slice(0, 2).map((item) => <div key={item.id} style={{ fontSize: '11px', marginTop: 10, color: 'var(--hf-text-secondary)', whiteSpace: 'pre-wrap' }}>{item.suggestion_text}<button className="btn-hf-ghost" onClick={() => onReviewWriting(item.id)} style={{ marginLeft: 6 }}><Check size={11} /></button>{item.keywords?.length > 0 && <div style={{ marginTop: 5, color: 'var(--hf-text-muted)' }}>Keywords: {item.keywords.join(', ')}</div>}{item.related_queries?.length > 0 && <div style={{ marginTop: 5, display: 'flex', flexDirection: 'column', gap: 3 }}>{item.related_queries.map((topic) => <button key={topic.query} className="btn-hf-ghost" onClick={() => onResearch(topic.query)} style={{ textAlign: 'left', fontSize: '10px', color: 'var(--hf-lime)' }}>Search Chrome: {topic.label}</button>)}</div>}</div>)}
      </div>
      <div className="inspector-card">
        <div className="inspector-header"><div className="inspector-title"><BrainCircuit size={13} style={{ color: 'var(--hf-lime)' }} /> Planner</div><span className="studio-pill-tag">{planner?.status?.last_decision || 'idle'}</span></div>
        {(planner?.suggestions || []).slice(0, 2).map((item) => <div key={item.id} className="task-item-hf" style={{ display: 'block' }}><div style={{ display: 'flex', gap: 8, alignItems: 'start' }}><span style={{ fontSize: '11px', flex: 1 }}>{item.context}: {item.response}</span><button className="btn-hf-ghost" onClick={() => onDismissSuggestion(item.id)}>Dismiss</button></div>{item.related_queries?.length > 0 && <div style={{ marginTop: 7, display: 'flex', flexDirection: 'column', gap: 3 }}>{item.related_queries.map((topic) => <button key={topic.query} className="btn-hf-ghost" onClick={() => onResearch(topic.query)} style={{ textAlign: 'left', fontSize: '10px', color: 'var(--hf-lime)' }}>Search Chrome: {topic.label}</button>)}</div>}</div>)}
        {!planner?.suggestions?.length && <div style={{ fontSize: '11px', color: 'var(--hf-text-muted)' }}>No suggestions. The planner observes without interrupting.</div>}
      </div>
    </>
  );
}
