import React, { useMemo, useState } from 'react';
import { Bot, User, Check, Copy, CheckSquare, Globe, ExternalLink, Zap, Volume2 } from 'lucide-react';
import DOMPurify from 'dompurify';
import { marked } from 'marked';
import { openBrowserUrl } from '../api/client';

marked.setOptions({
  gfm: true,
  breaks: true,
});

function renderMarkdown(content) {
  return DOMPurify.sanitize(marked.parse(content || ''), {
    FORBID_TAGS: ['base', 'embed', 'form', 'iframe', 'object', 'script', 'style'],
    FORBID_ATTR: ['style'],
  });
}

export function MessageBubble({ message }) {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);
  const [openingBrowser, setOpeningBrowser] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const renderedContent = useMemo(() => renderMarkdown(message.content), [message.content]);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const handleSpeak = () => {
    if (!('speechSynthesis' in window)) {
      alert('Speech synthesis is not supported in your browser.');
      return;
    }

    if (speaking) {
      window.speechSynthesis.cancel();
      setSpeaking(false);
    } else {
      window.speechSynthesis.cancel();
      // Clean markdown symbols for cleaner speech
      const cleanText = message.content
        .replace(/[*#`_>]/g, '')
        .replace(/\[(.*?)\]\(.*?\)/g, '$1')
        .trim();

      const utterance = new SpeechSynthesisUtterance(cleanText);
      utterance.rate = 1.05;
      utterance.pitch = 1.0;
      utterance.onend = () => setSpeaking(false);
      utterance.onerror = () => setSpeaking(false);

      setSpeaking(true);
      window.speechSynthesis.speak(utterance);
    }
  };

  const handleOpenBrowser = async (url) => {
    try {
      const parsed = new URL(url);
      if (!['http:', 'https:'].includes(parsed.protocol)) throw new Error('Unsupported URL');
    } catch {
      return;
    }
    setOpeningBrowser(true);
    try {
      await openBrowserUrl(url);
    } catch (e) {
      window.open(url, '_blank');
    } finally {
      setTimeout(() => setOpeningBrowser(false), 500);
    }
  };

  const getAgentLabel = (agent) => {
    switch (agent) {
      case 'state':
      case 'state_agent':
        return { label: 'Digital State Agent', class: 'state_agent' };
      case 'task':
      case 'task_agent':
        return { label: 'Task Pipeline Agent', class: 'task_agent' };
      case 'web':
      case 'web_agent':
        return { label: 'Web Research Agent', class: 'web_agent' };
      case 'desktop':
      case 'browser':
      case 'os_agent':
        return { label: 'Desktop OS Agent', class: 'os_agent' };
      default:
        return { label: 'Workspace Coordinator', class: 'coordinator' };
    }
  };

  const agentInfo = !isUser ? getAgentLabel(message.metadata?.routed_agent) : null;
  const tasksCreated = message.metadata?.tasks_created || [];
  const browserInfo = message.metadata?.browser_info;
  const researchSources = message.metadata?.research_sources || [];

  return (
    <div className={`bubble-row ${isUser ? 'user' : 'assistant'}`}>
      <div className={`avatar ${isUser ? 'user' : 'coordinator'}`}>
        {isUser ? <User size={15} /> : <Zap size={16} strokeWidth={2.5} />}
      </div>

      <div className="bubble-content" style={{ position: 'relative' }}>
        {!isUser && agentInfo && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span className={`agent-tag ${agentInfo.class}`}>
              {agentInfo.label}
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              {/* Voice Readout Button */}
              <button
                onClick={handleSpeak}
                className="btn-hf-ghost"
                style={{ padding: '2px 8px', fontSize: '10px', height: '22px', border: 'none', background: 'transparent', color: speaking ? 'var(--hf-lime)' : 'inherit' }}
                title={speaking ? 'Stop Speaking' : 'Read Aloud (Voice)'}
              >
                <Volume2 size={12} className={speaking ? 'animate-pulse' : ''} />
              </button>
              {/* Copy Button */}
              <button
                onClick={handleCopy}
                className="btn-hf-ghost"
                style={{ padding: '2px 8px', fontSize: '10px', height: '22px', border: 'none', background: 'transparent' }}
                title="Copy message"
              >
                {copied ? <Check size={12} style={{ color: 'var(--hf-emerald)' }} /> : <Copy size={12} />}
              </button>
            </div>
          </div>
        )}

        <div
          className="bubble-markdown"
          dangerouslySetInnerHTML={{ __html: renderedContent }}
        />

        {/* Live Desktop Browser Action Card */}
        {browserInfo && browserInfo.search_url && (
          <div style={{
            marginTop: '12px',
            padding: '10px 14px',
            background: 'rgba(212, 255, 0, 0.05)',
            border: '1px solid rgba(212, 255, 0, 0.25)',
            borderRadius: 'var(--radius-md)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '12px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
              <Globe size={15} style={{ color: 'var(--hf-lime)', flexShrink: 0 }} />
              <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--hf-lime)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Desktop Browser Action
                </div>
                <div style={{ fontSize: '11px', color: 'var(--hf-text-secondary)', fontFamily: 'var(--font-mono)', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {browserInfo.search_url}
                </div>
              </div>
            </div>
            <button
              onClick={() => handleOpenBrowser(browserInfo.search_url)}
              disabled={openingBrowser}
              className="btn-hf-primary"
              style={{ padding: '4px 12px', fontSize: '11px', flexShrink: 0, height: '26px' }}
            >
              <ExternalLink size={12} />
              <span>{openingBrowser ? 'Opening...' : 'Open in Browser'}</span>
            </button>
          </div>
        )}

        {researchSources.length > 0 && (
          <div style={{ marginTop: '12px', padding: '10px 12px', background: 'rgba(96, 165, 250, 0.06)', border: '1px solid rgba(96, 165, 250, 0.24)', borderRadius: 'var(--radius-md)' }}>
            <div style={{ fontSize: '10.5px', color: '#93c5fd', fontWeight: 700, marginBottom: 3, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Research sources</div>
            <div style={{ fontSize: 10, color: 'var(--hf-text-muted)', marginBottom: 7 }}>Retrieved content can be inaccurate or malicious. Inspect the domain before opening a source.</div>
            {researchSources.slice(0, 6).map((source) => (
              <button key={source.url} onClick={() => handleOpenBrowser(source.url)} disabled={openingBrowser} className="btn-hf-ghost" title={`Open ${source.domain || source.url} in your browser`} style={{ width: '100%', padding: '7px 0', border: 'none', borderBottom: '1px solid var(--hf-border-subtle)', borderRadius: 0, textAlign: 'left', display: 'block' }}>
                <span style={{ display: 'block', color: 'var(--hf-text-primary)', fontSize: 11, fontWeight: 650 }}>{source.title}</span>
                <span style={{ display: 'block', color: 'var(--hf-text-muted)', fontSize: 10, marginTop: 2 }}>{source.domain || source.url}</span>
                {source.summary && <span style={{ display: 'block', color: 'var(--hf-text-secondary)', fontSize: 10, marginTop: 3, lineHeight: 1.35 }}>{source.summary}</span>}
              </button>
            ))}
          </div>
        )}

        {/* Created Tasks Cards */}
        {tasksCreated.length > 0 && (
          <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px solid var(--hf-border-subtle)' }}>
            <div style={{ fontSize: '10.5px', color: 'var(--hf-lime)', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '5px', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              <CheckSquare size={12} />
              <span>Action Items Created</span>
            </div>
            {tasksCreated.map(t => (
              <div key={t.id} style={{
                background: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid var(--hf-border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '6px 12px',
                fontSize: '12px',
                marginBottom: '4px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}>
                <span style={{ color: 'var(--hf-lime)', fontWeight: 700 }}>#{t.id}</span>
                <span>{t.title}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
