import React, { useState } from 'react';
import { SlidersHorizontal, Plus, Calendar, CheckCircle2, ExternalLink } from 'lucide-react';

export function TaskPanel({ tasks, onToggleTask, onSetTaskStatus, onCreateTask, onNavigateTask, onLinkTask }) {
  const [filter, setFilter] = useState('active'); // 'all' | 'active' | 'completed'
  const [newTitle, setNewTitle] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const filteredTasks = tasks.filter(task => {
    if (filter === 'active') return !task.done;
    if (filter === 'completed') return task.done;
    return true;
  });

  const handleQuickAdd = async (e) => {
    e.preventDefault();
    if (!newTitle.trim()) return;
    setSubmitting(true);
    await onCreateTask(newTitle.trim());
    setNewTitle('');
    setSubmitting(false);
  };

  const activeCount = tasks.filter(t => !t.done).length;

  return (
    <div className="inspector-card" style={{ flex: 1, minHeight: '340px' }}>
      <div className="inspector-header">
        <div className="inspector-title">
          <SlidersHorizontal size={13} style={{ color: 'var(--hf-lime)' }} />
          <span>Workspace Tasks</span>
        </div>
        <div style={{ display: 'flex', gap: '4px' }}>
          <button
            onClick={() => setFilter('active')}
            className="btn-hf-ghost"
            style={{
              padding: '2px 8px',
              fontSize: '10px',
              backgroundColor: filter === 'active' ? 'var(--hf-lime-badge)' : 'transparent',
              color: filter === 'active' ? 'var(--hf-lime)' : 'var(--hf-text-muted)',
              borderColor: filter === 'active' ? 'rgba(212, 255, 0, 0.4)' : 'transparent'
            }}
          >
            Active ({activeCount})
          </button>
          <button
            onClick={() => setFilter('all')}
            className="btn-hf-ghost"
            style={{
              padding: '2px 8px',
              fontSize: '10px',
              backgroundColor: filter === 'all' ? 'var(--hf-lime-badge)' : 'transparent',
              color: filter === 'all' ? 'var(--hf-lime)' : 'var(--hf-text-muted)',
              borderColor: filter === 'all' ? 'rgba(212, 255, 0, 0.4)' : 'transparent'
            }}
          >
            All ({tasks.length})
          </button>
        </div>
      </div>

      {/* Quick Add Form */}
      <form onSubmit={handleQuickAdd} style={{ display: 'flex', gap: '6px', marginBottom: '12px' }}>
        <input
          type="text"
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
          placeholder="Add pipeline action item..."
          className="input-hf"
          style={{
            backgroundColor: 'rgba(255, 255, 255, 0.03)',
            border: '1px solid var(--hf-border-subtle)',
            borderRadius: 'var(--radius-pill)',
            padding: '6px 12px',
            fontSize: '11.5px'
          }}
        />
        <button
          type="submit"
          disabled={!newTitle.trim() || submitting}
          className="btn-hf-primary"
          style={{ padding: '6px 12px', height: '30px' }}
        >
          <Plus size={13} />
        </button>
      </form>

      {/* Tasks List */}
      <div style={{ flex: 1, overflowY: 'auto', maxHeight: '340px', paddingRight: '2px' }}>
        {filteredTasks.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '36px 10px', color: 'var(--hf-text-muted)', fontSize: '11.5px' }}>
            <CheckCircle2 size={22} style={{ margin: '0 auto 8px', opacity: 0.3, color: 'var(--hf-lime)' }} />
            No {filter} items in queue.
          </div>
        ) : (
          filteredTasks.map(task => (
            <div key={task.id} className={`task-item-hf ${task.done ? 'completed' : ''}`}>
              <input
                type="checkbox"
                checked={task.done}
                onChange={() => onToggleTask(task.id, !task.done)}
                className="checkbox-hf"
              />
              <div style={{ flex: 1, minWidth: 0 }}>
                <button
                  type="button"
                  disabled={!task.has_context}
                  onClick={() => onNavigateTask(task.id)}
                  title={task.has_context ? `Open ${task.source_title || task.source_app || 'saved workspace context'}` : 'This older task has no saved workspace context.'}
                  style={{ background: 'none', border: 0, padding: 0, cursor: task.has_context ? 'pointer' : 'default', textAlign: 'left', display: 'flex', gap: 5, alignItems: 'center', fontSize: '12.5px', fontWeight: 500, color: task.done ? 'var(--hf-text-muted)' : 'var(--hf-text-primary)', textDecoration: task.done ? 'line-through' : 'none' }}
                >
                  <span>{task.title}</span>{task.has_context && <ExternalLink size={11} color="var(--hf-lime)" />}
                </button>
                {task.has_context && <div style={{ fontSize: '10px', color: 'var(--hf-text-muted)', marginTop: '2px' }}>Open context: {task.source_title || task.source_app}</div>}
                {!task.has_context && <button type="button" className="btn-hf-ghost" onClick={() => onLinkTask(task.id)} style={{ marginTop: '3px', padding: '2px 5px', fontSize: '10px' }}>Link current app/tab</button>}
                {task.due_at && (
                  <div style={{ fontSize: '10px', color: 'var(--hf-lime)', fontFamily: 'var(--font-mono)', marginTop: '2px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Calendar size={10} />
                    <span>Due {new Date(task.due_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</span>
                  </div>
                )}
                {!task.done && (
                  <select
                    value={task.status || 'pending'}
                    onChange={(event) => onSetTaskStatus(task.id, event.target.value)}
                    className="input-hf"
                    aria-label={`Status for ${task.title}`}
                    style={{ marginTop: '5px', fontSize: '10px', border: '1px solid var(--hf-border-subtle)', padding: '2px 5px' }}
                  >
                    <option value="pending">Pending</option>
                    <option value="ongoing">Ongoing</option>
                  </select>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
