import React, { useState } from 'react';
import { Crosshair, AppWindow, Globe, RefreshCw, Layers, Radio } from 'lucide-react';

export function StatusIndicator({ snapshot, onRefresh, onTriggerDiff }) {
  const [loading, setLoading] = useState(false);

  const handleRefresh = async () => {
    setLoading(true);
    await onRefresh();
    setTimeout(() => setLoading(false), 400);
  };

  const activeApp = snapshot?.active_app || 'Desktop Idle';
  const activeWindow = snapshot?.active_window_title || 'No active window reported';
  const browserUrl = snapshot?.browser_url;
  const browserTitle = snapshot?.browser_tab_title;

  return (
    <div className="inspector-card">
      <div className="inspector-header">
        <div className="inspector-title">
          <Crosshair size={13} style={{ color: 'var(--hf-lime)' }} />
          <span>Workspace Radar</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '5px',
            fontSize: '10px',
            fontFamily: 'var(--font-mono)',
            padding: '2px 8px',
            borderRadius: 'var(--radius-pill)',
            background: 'rgba(0, 240, 118, 0.1)',
            color: 'var(--hf-emerald)',
            border: '1px solid rgba(0, 240, 118, 0.25)'
          }}>
            <span className="pulse-dot-hf"></span>
            <span>LIVE 60FPS</span>
          </div>
          <button
            onClick={handleRefresh}
            className="btn-hf-ghost"
            style={{ padding: '3px 7px', height: '24px' }}
            title="Refresh snapshot"
          >
            <RefreshCw size={11} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* High-tech Viewport Box with Corner Brackets */}
      <div className="radar-viewport">
        <div style={{ marginBottom: '8px' }}>
          <div style={{ fontSize: '9px', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--hf-text-muted)', fontFamily: 'var(--font-mono)', marginBottom: '2px' }}>
            Target Application
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <AppWindow size={13} style={{ color: 'var(--hf-lime)' }} />
            <span style={{ fontWeight: 700, fontSize: '13px', color: 'var(--hf-text-primary)' }}>{activeApp}</span>
          </div>
        </div>

        <div>
          <div style={{ fontSize: '9px', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--hf-text-muted)', fontFamily: 'var(--font-mono)', marginBottom: '2px' }}>
            Active Buffer / Window
          </div>
          <div style={{ fontSize: '11.5px', color: 'var(--hf-text-secondary)', wordBreak: 'break-word', lineHeight: 1.4 }}>
            {activeWindow}
          </div>
        </div>
      </div>

      {browserUrl && (
        <div style={{ marginBottom: '12px', padding: '10px 12px', background: 'rgba(255, 255, 255, 0.02)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--hf-border-subtle)' }}>
          <div style={{ fontSize: '9px', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--hf-lime)', fontFamily: 'var(--font-mono)', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Globe size={11} />
            <span>Active Browser View</span>
          </div>
          <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--hf-text-primary)', marginBottom: '2px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {browserTitle || 'Web Tab'}
          </div>
          <a
            href={browserUrl}
            target="_blank"
            rel="noreferrer"
            style={{ fontSize: '11px', color: 'var(--hf-lime)', textDecoration: 'none', fontFamily: 'var(--font-mono)', display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
          >
            {browserUrl}
          </a>
        </div>
      )}

      <button
        onClick={onTriggerDiff}
        className="btn-hf-ghost"
        style={{ width: '100%', justifyContent: 'center', fontSize: '11px', padding: '8px 12px' }}
      >
        <Layers size={12} style={{ color: 'var(--hf-lime)' }} />
        <span>Analyze Context Shifts</span>
      </button>
    </div>
  );
}
