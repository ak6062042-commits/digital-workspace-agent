# Digital Workspace Agent — 3-Minute Hackathon Winning Demo Script

> **Goal**: Present a compelling, flawless 3-minute demonstration for hackathon judges showcasing real-time OS state awareness, autonomous routing, web research, and live task management.

---

## Pre-Demo Checklist (2 Minutes Before Going on Stage)
1. **Terminal 1 (Backend)**:
   ```bash
   source .venv/bin/activate
   uvicorn backend.main:app --port 8000 --reload
   ```
2. **Terminal 2 (Frontend)**:
   ```bash
   cd frontend && npm run dev
   ```
   Open `http://localhost:5173` in your browser.
3. **Terminal 3 (Local OS Watcher)**:
   ```bash
   source .venv/bin/activate
   python system-agent/local-agent/watcher.py
   ```
4. Click the **"Reset Demo"** button in the top right of the frontend to ensure clean initial demo data.

---

## The 3-Minute Pitch Script

### Minute 0:00 – 0:30: The Hook & The Problem
> *"Judges, knowledge workers switch contexts over 1,200 times a day. But current AI assistants like ChatGPT or Claude are completely blind — they sit in a generic chat box, unaware of what you're working on, what windows you have open, or what changed when you stepped away for coffee.*
> 
> *Today, we built the **Digital Workspace Agent**: an autonomous desktop co-pilot that watches your operating system context in real time, routes actions to specialized micro-agents, and manages your work without you ever leaving your flow."*

---

### Minute 0:30 – 1:15: Demo Step 1 — Real-Time Workspace Radar & State Awareness
**Action**: Point to the **Workspace Radar** on the top-right of the screen.
> *"Look at the Workspace Radar on the right panel. It's connected directly to our lightweight native local agent. Right now, it detects that my frontmost window is Chrome, and it extracts the exact URL and documentation tab."*

**Action**: Click the suggested chip or type:
```
What was I working on?
```
> *"Let's ask the agent: 'What was I working on?'. Watch how the Coordinator automatically routes this request to the **Digital State Agent** (marked with the green badge). It pulls the live snapshot, informs us of our focused window, and attaches the active URL without requiring any manual copy-pasting."*

---

### Minute 1:15 – 1:55: Demo Step 2 — "What Changed While I Was Away?" (State Diffing)
**Action**: Click the **"Inspect Context Transitions"** button or type:
```
What changed while I was away?
```
> *"Now imagine you just returned from a 30-minute meeting or lunch. You ask: 'What changed while I was away?'.*
> 
> *Our Digital State Agent performs a time-series diff across recent snapshots, showing a chronological timeline of every application and window transition you made. You never have to spend 10 minutes digging through browser history again."*

---

### Minute 1:55 – 2:25: Demo Step 3 — Voice Command & Desktop Terminal Control
**Action**: Click the microphone icon or type:
```
Hey Agent, open Terminal
```
> *"Next, watch this: I can speak or type: 'Hey Agent, open Terminal'.*
> 
> *Our **Desktop OS Agent** triggers native AppleScript, and **physically launches our macOS Terminal window right in front of us**!*
> 
> *Look at the Workspace Radar on the right panel: within seconds, it catches the state transition and updates the focused application to **Terminal**."*

---

### Minute 2:25 – 2:45: Demo Step 4 — "Search It on the Browser"
**Action**: Click the suggested chip or speak:
```
Hey Agent, search Railway vs Vercel on the browser
```
> *"Now, when I say: 'Hey Agent, search Railway vs Vercel on the browser', watch what happens:*
> 
> *It physically opens Google Chrome to the live comparison tab, extracts the documentation, and synthesizes executive recommendations directly inside our chat interface. If I turn on Voice Output, it will even read the summary aloud like Siri!"*

---

### Minute 2:45 – 3:00: Demo Step 5 — Pipeline Action Extraction & Closing
**Action**: Say or type:
```
Hey Agent, add task to deploy staging database on Railway by Friday
```
> *"Finally, I tell it: 'Hey Agent, add task to deploy staging database on Railway by Friday'. The **Task Agent** extracts the deadline, adds it to our live board, and we check it off with one click.*
> 
> *We didn't build another isolated chat window — we built a true autonomous desktop copilot. Thank you!"*

---

## Judge Q&A Anticipated Answers

### Q1: *"How does privacy work? Is my screen being recorded?"*
**Answer**: *"No. We intentionally avoid heavy screen recording or OCR. The local agent only captures metadata: the frontmost application process name and active window title using native OS APIs (`osascript` on macOS, Win32 on Windows). All data remains on your local machine in SQLite."*

### Q2: *"What happens if the internet goes down or LLM rate-limits hit?"*
**Answer**: *"Our coordinator has a dual-layer routing architecture. If API keys are absent or the network drops, our deterministic intent parser and local knowledge cache take over seamlessly. The system is 100% resilient and offline-capable."*

### Q3: *"How does the browser extension interact with the local agent?"*
**Answer**: *"Both report into the same standardized schema (`shared/schemas/state_snapshot.json`). The browser extension provides high-resolution tab URL events, while the OS agent captures native desktop application context."*
