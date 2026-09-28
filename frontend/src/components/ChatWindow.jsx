import React, { useState, useRef, useEffect, useCallback } from 'react';
import { ArrowUp, Sparkles, Mic, MicOff, Volume2, VolumeX, Trash2, Zap } from 'lucide-react';
import { MessageBubble } from './MessageBubble';

const SUGGESTED_PROMPTS = [
  "Research the best notes app for developers",
  "Create task: organize project files",
  "What was I working on?",
  "Open VS Code"
];

// Web Audio API Chimes (Pure JavaScript, zero external asset dependencies)
function playChime(type = 'wake') {
  try {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);

    if (type === 'wake') {
      // Rising Siri-style double tone (D5 -> A5)
      osc.type = 'sine';
      osc.frequency.setValueAtTime(587.33, ctx.currentTime);
      osc.frequency.setValueAtTime(880.00, ctx.currentTime + 0.08);
      gain.gain.setValueAtTime(0.2, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.35);
      osc.start();
      osc.stop(ctx.currentTime + 0.35);
    } else if (type === 'execute') {
      // Clean high-tech confirmation tone (C5 -> E5)
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(523.25, ctx.currentTime);
      osc.frequency.setValueAtTime(659.25, ctx.currentTime + 0.08);
      gain.gain.setValueAtTime(0.18, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
      osc.start();
      osc.stop(ctx.currentTime + 0.3);
    }
  } catch (e) {
    // Audio context may be blocked before first user gesture
  }
}
const WAKE_PHRASES = [
  "hey agent",
  "hi agent",
  "agent,"
];

export function ChatWindow({ messages, onSendMessage, onClearMessages, loading, voiceEnabled, onToggleVoice }) {
  const [input, setInput] = useState('');
  // Microphone capture is opt-in and remains visibly paused until enabled.
  const [isVoiceActive, setIsVoiceActive] = useState(false);
  const [isAwake, setIsAwake] = useState(false);
  const [voiceStatus, setVoiceStatus] = useState('Voice recognition paused. Click the microphone to enable it.');

  const messagesEndRef = useRef(null);
  const recognitionRef = useRef(null);
  const isListeningRef = useRef(false);
  const isWakeActiveRef = useRef(false);
  const wakeExpireTimerRef = useRef(null);
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  // Voice transcription only stages a request. Sending remains a separate user action.
  const stageVoiceCommand = useCallback((command) => {
    const clean = command.trim();
    if (!clean) return;
    clearTimeout(wakeExpireTimerRef.current);
    isWakeActiveRef.current = false;
    setIsAwake(false);
    setInput(clean);
    setVoiceStatus('Voice command captured. Review it and press Send to continue.');
  }, []);

  // Main Speech Recognition Setup (runs ONCE on mount, NEVER re-mounts)
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setVoiceStatus('Speech recognition not supported in this browser (Use Chrome or Edge)');
      setIsVoiceActive(false);
      return;
    }

    const recognizer = new SpeechRecognition();
    recognizer.continuous = true;
    recognizer.interimResults = true;
    recognizer.lang = 'en-US';

    recognizer.onstart = () => {
      isListeningRef.current = true;
      setIsVoiceActive(true);
      if (!isWakeActiveRef.current) {
        setVoiceStatus('Voice recognition active. Say "Hey Agent"...');
      }
    };

    recognizer.onresult = (event) => {
      let fullTranscript = '';
      for (let i = 0; i < event.results.length; i++) {
        fullTranscript += event.results[i][0].transcript + ' ';
      }
      fullTranscript = fullTranscript.trim();
      const lower = fullTranscript.toLowerCase();

      // Check if any wake word phrase is present
      let wakeIndex = -1;
      let wakeLen = 0;
      for (const phrase of WAKE_PHRASES) {
        const idx = lower.indexOf(phrase);
        if (idx !== -1) {
          wakeIndex = idx;
          wakeLen = phrase.length;
          break;
        }
      }

      // Case 1: Wake word detected for the first time
      if (wakeIndex !== -1) {
        if (!isWakeActiveRef.current) {
          playChime('wake');
          isWakeActiveRef.current = true;
          setIsAwake(true);
        }

        // Extract any spoken command following the wake word
        const afterWake = fullTranscript.slice(wakeIndex + wakeLen).replace(/^[,:!.\s]+/, '').trim();

        if (afterWake) {
          stageVoiceCommand(afterWake);
        } else {
          setVoiceStatus('"Hey Agent" heard. Say your command now (for example, "open VS Code").');

          // Reset wake state if user stays silent for 8 seconds
          clearTimeout(wakeExpireTimerRef.current);
          wakeExpireTimerRef.current = setTimeout(() => {
            isWakeActiveRef.current = false;
            setIsAwake(false);
            setVoiceStatus('Voice recognition active. Say "Hey Agent"...');
          }, 8000);
        }
      }
      // Case 2: Already awake, user is speaking the command
      else if (isWakeActiveRef.current) {
        if (fullTranscript) {
          stageVoiceCommand(fullTranscript);
        }
      }
    };

    recognizer.onerror = (event) => {
      console.warn('Speech recognition notice:', event.error);
      if (event.error === 'not-allowed') {
        setIsVoiceActive(false);
        isListeningRef.current = false;
        setVoiceStatus('Microphone access blocked. Click mic to grant permission.');
      }
    };

    recognizer.onend = () => {
      // Auto-restart to ensure it's listening continuously
      if (isListeningRef.current) {
        try {
          recognizer.start();
        } catch (e) {
          setTimeout(() => {
            if (isListeningRef.current) {
              try { recognizer.start(); } catch (err) {}
            }
          }, 400);
        }
      }
    };

    recognitionRef.current = recognizer;

    // Do not start recognition here. The microphone control is the explicit consent boundary.

    return () => {
      isListeningRef.current = false;
      clearTimeout(wakeExpireTimerRef.current);
      try { recognizer.abort(); } catch (e) {}
    };
  }, [stageVoiceCommand]);

  // Toggle Voice Mode manually if desired
  const toggleVoiceMode = () => {
    if (!recognitionRef.current) {
      alert('Speech recognition is not supported in this browser. Please use Chrome or Edge.');
      return;
    }

    if (isVoiceActive) {
      isListeningRef.current = false;
      try { recognitionRef.current.abort(); } catch (e) {}
      setIsVoiceActive(false);
      setIsAwake(false);
      setVoiceStatus('Voice recognition paused. Click mic to re-enable.');
    } else {
      try {
        isListeningRef.current = true;
        recognitionRef.current.start();
        setIsVoiceActive(true);
        playChime('wake');
        setVoiceStatus('Voice recognition active. Say "Hey Agent"...');
      } catch (err) {
        console.warn('Voice restart notice:', err);
      }
    }
  };

  const handleSubmit = (e) => {
    e?.preventDefault();
    if (!input.trim() || loading) return;

    // End the active voice wake state before sending a reviewed command.
    clearTimeout(wakeExpireTimerRef.current);
    isWakeActiveRef.current = false;
    setIsAwake(false);

    onSendMessage(input.trim());
    setInput('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleChipClick = (prompt) => {
    onSendMessage(prompt);
  };

  return (
    <div className="chat-pane">
      {/* Scrollable Messages Stream */}
      <div className="chat-messages">
        {messages.length > 1 && (
          <div style={{ alignSelf: 'center' }}>
            <button className="btn-hf-ghost" onClick={onClearMessages} style={{ padding: '4px 10px', fontSize: 10 }} title="Clear this local chat transcript">
              <Trash2 size={11} /> Clear chat
            </button>
          </div>
        )}
        {messages.map((msg, index) => (
          <MessageBubble key={index} message={msg} />
        ))}

        {loading && (
          <div className="bubble-row assistant">
            <div className="avatar coordinator">
              <Sparkles size={16} />
            </div>
            <div className="bubble-content" style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--hf-text-secondary)' }}>
              <div className="pulse-dot-hf"></div>
              <span>Digital Workspace Assistant coordinating context...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Floating Studio Dock at Bottom */}
      <div className="floating-dock-container">
        {/* Dynamic Voice Status Banner */}
        <div style={{
          background: isAwake ? 'rgba(212, 255, 0, 0.15)' : 'rgba(20, 20, 20, 0.85)',
          border: `1px solid ${isAwake ? 'rgba(212, 255, 0, 0.6)' : 'rgba(255, 255, 255, 0.1)'}`,
          borderRadius: 'var(--radius-pill)',
          padding: '6px 18px',
          fontSize: '11px',
          color: isAwake ? 'var(--hf-lime)' : 'var(--hf-text-secondary)',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          fontFamily: 'var(--font-mono)',
          boxShadow: isAwake ? '0 0 20px rgba(212, 255, 0, 0.3)' : '0 4px 12px rgba(0, 0, 0, 0.4)',
          transition: 'all 0.25s ease',
          pointerEvents: 'auto',
          backdropFilter: 'blur(12px)'
        }}>
          <Zap size={14} className={isAwake ? 'animate-bounce text-lime-400' : 'text-emerald-400'} style={{ color: isAwake ? 'var(--hf-lime)' : '#10b981' }} />
          <span style={{ fontWeight: 600 }}>{voiceStatus}</span>
        </div>

        {/* Suggested Prompt Chips */}
        <div className="prompt-chips-row">
          {SUGGESTED_PROMPTS.map((prompt, idx) => (
            <button
              key={idx}
              onClick={() => handleChipClick(prompt)}
              disabled={loading}
              className="chip-hf"
            >
              {prompt}
            </button>
          ))}
        </div>

        {/* Floating Input Bar */}
        <form onSubmit={handleSubmit} className="floating-input-bar">
          {/* Always-On Voice Toggle (Wake Word 'Hey Agent') */}
          <button
            type="button"
            onClick={toggleVoiceMode}
            className={`btn-voice ${isVoiceActive ? 'listening' : ''}`}
            title={isVoiceActive ? 'Always-On Voice Active (Say "Hey Agent")' : 'Voice Paused - Click to Activate'}
            style={{
              background: isVoiceActive ? 'var(--hf-lime)' : 'rgba(255, 255, 255, 0.05)',
              color: isVoiceActive ? '#000' : 'var(--hf-text-secondary)',
              borderColor: isVoiceActive ? 'var(--hf-lime)' : 'var(--hf-border-subtle)',
              boxShadow: isVoiceActive ? 'var(--shadow-lime-glow)' : 'none'
            }}
          >
            {isVoiceActive ? <Mic size={16} strokeWidth={2.5} /> : <MicOff size={16} />}
          </button>

          <textarea
            rows={1}
            maxLength={4000}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            aria-label="Message to the workspace assistant"
            placeholder={
              isAwake
                ? 'Voice command ready. Review it, then press Send.'
                : 'Ask anything — Enter sends, Shift+Enter adds a line'
            }
            className="input-hf"
            disabled={loading}
            style={{ resize: 'none', minHeight: 24, maxHeight: 84, lineHeight: 1.45, paddingTop: 2 }}
          />

          {/* Text-To-Speech (Voice Output) Toggle */}
          <button
            type="button"
            onClick={onToggleVoice}
            className="btn-voice"
            style={{ color: voiceEnabled ? 'var(--hf-lime)' : 'var(--hf-text-muted)' }}
            title={voiceEnabled ? 'Spoken Voice Output: Enabled' : 'Spoken Voice Output: Muted'}
          >
            {voiceEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
          </button>

          {/* Send Button */}
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="btn-send-hf"
            title="Execute (Enter)"
          >
            <ArrowUp size={16} strokeWidth={2.5} />
          </button>
        </form>
      </div>
    </div>
  );
}
