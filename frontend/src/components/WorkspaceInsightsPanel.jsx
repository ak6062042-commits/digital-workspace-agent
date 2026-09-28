import React, { useState } from 'react';
import { Activity, Bell, BrainCircuit, Check, FileText, Search, Trash2 } from 'lucide-react';

export function WorkspaceInsightsPanel({ notifications, writingSuggestions, planner, settings, onReviewNotification, onDeleteNotification, onAnalyzeWriting, onReviewWriting, onDismissSuggestion, onResearch }) {
  const [text, setText] = useState('');
  const [operation, setOperation] = useState('improve');
  const [researchQuery, setResearchQuery] = useState('');
  const [busy, setBusy] = useState(false);

  const analyze = async (event) => {
    event.preventDefault();
    if (!text.trim()) return;
    setBusy(true);
    try {
      if (await onAnalyzeWriting(text.trim(), operation)) setText('');
    } finally {
      setBusy(false);
    }
  };

  const research = (event) => {
    event.preventDefault();
    const query = researchQuery.trim();
    if (!query) return;
    setResearchQuery('');
    onResearch(query);
  };

  return (
    <>
      <div className="inspector-card">
        <div className="inspector-header"><div className="inspector-title"><Activity size={13} style={{ color: 'var(--hf-emerald)' }} /> Workspace status</div></div>
        <div style={{ fontSize: '11px', color: 'var(--hf-text-secondary)', lineHeight: 1.55 }}>
          Context capture: <strong style={{ color: settings?.capture_enabled ? 'var(--hf-lime)' : 'var(--hf-text-muted)' }}>{settings?.capture_enabled ? 'on' : 'off'}</strong>.<br />
          Live research returns sources you can inspect one at a time. Writing and page analysis work from text you explicitly submit.
        </div>
      </div>

      <div className="inspector-card">
        <div className="inspector-header"><div className="inspector-title"><Search size={13} style={{ color: 'var(--hf-amber)' }} /> Quick research</div></div>
        <form onSubmit={research} style={{ display: 'flex', gap: 6 }}>
          <input value={researchQuery} onChange={(event) => setResearchQuery(event.target.value)} className="input-hf" aria-label="Research topic" placeholder="Ask a question or compare options" style={{ border: '1px solid var(--hf-border-subtle)', borderRadius: 'var(--radius-pill)', padding: '7px 10px', minWidth: 0 }} />
          <button type="submit" className="btn-hf-primary" disabled={!researchQuery.trim()} style={{ padding: '6px 10px' }} title="Research topic"><Search size={13} /></button>
        </form>
      </div>

      <div className="inspector-card">
        <div className="inspector-header"><div className="inspector-title"><Bell size={13} style={{ color: 'var(--hf-lime)' }} /> Notifications</div><span className="studio-pill-tag">{notifications.length}</span></div>
        {notifications.slice(0, 4).map((note) => (
          <div key={note.id} className="task-item-hf">
            <div style={{ flex: 1, minWidth: 0, fontSize: '11px' }}><strong>{note.source}</strong><br />{note.summary}</div>
            <button className="btn-hf-ghost" onClick={() => onReviewNotification(note.id)} aria-label={`Mark ${note.source} notification reviewed`} title="Mark reviewed"><Check size={12} /></button>
            <button className="btn-hf-ghost" onClick={() => onDeleteNotification(note.id)} aria-label={`Delete ${note.source} notification`} title="Delete notification"><Trash2 size={12} /></button>
          </div>
        ))}
        {!notifications.length && <div style={{ fontSize: '11px', color: 'var(--hf-text-muted)' }}>No unread notifications.</div>}
      </div>

      <div className="inspector-card">
        <div className="inspector-header"><div className="inspector-title"><FileText size={13} style={{ color: 'var(--hf-lime)' }} /> Writing workbench</div><span style={{ color: 'var(--hf-text-muted)', fontSize: 10 }}>{text.length.toLocaleString()} / 12,000</span></div>
        <form onSubmit={analyze}>
          <textarea value={text} onChange={(event) => setText(event.target.value)} maxLength={12000} aria-label="Text for writing analysis" placeholder="Paste notes, an article, or a draft to summarize, improve, explain, or turn into ideas." className="input-hf" style={{ width: '100%', minHeight: 110, border: '1px solid var(--hf-border-subtle)', borderRadius: 'var(--radius-sm)', padding: 9, marginBottom: 8, resize: 'vertical' }} />
          <div style={{ display: 'flex', gap: 6 }}><select value={operation} onChange={(event) => setOperation(event.target.value)} className="input-hf" aria-label="Writing operation" style={{ border: '1px solid var(--hf-border-subtle)', borderRadius: 'var(--radius-pill)', padding: '6px 8px' }}><option value="improve">Improve</option><option value="summarize">Summarize</option><option value="explain">Explain</option><option value="ideas">Ideas</option></select><button className="btn-hf-primary" disabled={busy || !text.trim()}>{busy ? 'Analyzing…' : 'Analyze text'}</button></div>
        </form>
        {writingSuggestions.slice(0, 2).map((item) => (
          <div key={item.id} style={{ fontSize: '11px', marginTop: 12, color: 'var(--hf-text-secondary)', whiteSpace: 'pre-wrap', borderTop: '1px solid var(--hf-border-subtle)', paddingTop: 10 }}>
            {item.suggestion_text}<button className="btn-hf-ghost" onClick={() => onReviewWriting(item.id)} style={{ marginLeft: 6, padding: '2px 5px' }} title="Mark writing suggestion reviewed"><Check size={11} /></button>
            {item.keywords?.length > 0 && <div style={{ marginTop: 5, color: 'var(--hf-text-muted)' }}>Keywords: {item.keywords.join(', ')}</div>}
            {item.related_queries?.length > 0 && <div style={{ marginTop: 7, display: 'flex', flexDirection: 'column', gap: 3 }}>{item.related_queries.map((topic) => <button key={topic.query} className="btn-hf-ghost" onClick={() => onResearch(topic.query)} style={{ textAlign: 'left', fontSize: '10px', color: 'var(--hf-lime)' }}>Research: {topic.label}</button>)}</div>}
          </div>
        ))}
      </div>

      <div className="inspector-card">
        <div className="inspector-header"><div className="inspector-title"><BrainCircuit size={13} style={{ color: 'var(--hf-lime)' }} /> Planner</div><span className="studio-pill-tag">{planner?.status?.last_decision || 'idle'}</span></div>
        {(planner?.suggestions || []).slice(0, 3).map((item) => (
          <div key={item.id} className="task-item-hf" style={{ display: 'block' }}>
            <div style={{ display: 'flex', gap: 8, alignItems: 'start' }}><span style={{ fontSize: '11px', flex: 1 }}>{item.context}: {item.response}</span><button className="btn-hf-ghost" onClick={() => onDismissSuggestion(item.id)}>Dismiss</button></div>
            {item.related_queries?.length > 0 && <div style={{ marginTop: 7, display: 'flex', flexDirection: 'column', gap: 3 }}>{item.related_queries.map((topic) => <button key={topic.query} className="btn-hf-ghost" onClick={() => onResearch(topic.query)} style={{ textAlign: 'left', fontSize: '10px', color: 'var(--hf-lime)' }}>Research: {topic.label}</button>)}</div>}
          </div>
        ))}
        {!planner?.suggestions?.length && <div style={{ fontSize: '11px', color: 'var(--hf-text-muted)' }}>No suggestions right now. Your workspace remains ready for the next task.</div>}
      </div>
    </>
  );
}
