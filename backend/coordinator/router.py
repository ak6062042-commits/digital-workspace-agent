import os
import re
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from backend.agents.task_agent import TaskAgent
from backend.agents.state_agent import DigitalStateAgent
from backend.agents.web_agent import WebResearchAgent
from backend.tools.os_tool import open_desktop_app, open_terminal
from backend.coordinator.prompts import ROUTER_INTENT_PATTERNS, COORDINATOR_SYSTEM_PROMPT
from backend.coordinator.context_store import context_store

logger = logging.getLogger("CoordinatorRouter")


class CoordinatorRouter:
    """
    Coordinates and routes requests across TaskAgent, DigitalStateAgent,
    WebResearchAgent, and native OS desktop actions.
    """

    def __init__(self):
        self.task_agent = TaskAgent()
        self.state_agent = DigitalStateAgent()
        self.web_agent = WebResearchAgent()

    def route_intent(self, query: str) -> str:
        """
        Determine target specialized agent from user prompt.
        Returns: 'state_agent', 'task_agent', 'web_agent', 'os_agent', or 'coordinator'.
        """
        q_lower = query.lower().strip()

        # Check for OS / desktop app launches (Terminal, Finder, VS Code, Calculator, etc.)
        os_app_pattern = r'\b(open|launch|start|run)\b.*?\b(terminal|console|iterm|code|vscode|vs\s*code|visual\s*studio|finder|calculator|calc|notes|spotify|slack|chrome|browser)\b'
        if re.search(os_app_pattern, q_lower) or any(phrase in q_lower for phrase in ROUTER_INTENT_PATTERNS.get("os_agent", [])):
            return "os_agent"

        # Check for state agent triggers
        for phrase in ROUTER_INTENT_PATTERNS["state_agent"]:
            if phrase in q_lower:
                return "state_agent"

        # Check for task agent triggers
        for phrase in ROUTER_INTENT_PATTERNS["task_agent"]:
            if phrase in q_lower:
                return "task_agent"

        # Check for web research triggers
        for phrase in ROUTER_INTENT_PATTERNS["web_agent"]:
            if phrase == "vs":
                if re.search(r'\bvs\b', q_lower):
                    return "web_agent"
            elif phrase in q_lower:
                return "web_agent"

        return "coordinator"

    def handle_message(self, message: str, session_id: str = "default_session", include_state: bool = True) -> Dict[str, Any]:
        """
        Process user message, handle wake words, route to right agent, and return standard AgentResponse.
        """
        raw_msg = message.strip()
        clean_msg = raw_msg

        # 1. Wake word detection ("Hey Agent")
        wake_word_triggered = False
        for prefix in ["hey agent", "hey assistant", "agent,"]:
            if clean_msg.lower().startswith(prefix):
                clean_msg = clean_msg[len(prefix):].strip(" ,:!")
                wake_word_triggered = True
                break

        # If user only said the wake word
        if wake_word_triggered and not clean_msg:
            return {
                "response": "Yes! I'm here and listening. What would you like me to do?",
                "routed_agent": "coordinator",
                "tasks_created": [],
                "browser_info": None,
                "state_snapshot": self.state_agent.get_latest_snapshot() if include_state else None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        effective_query = clean_msg if clean_msg else raw_msg

        logger.info("Handling user message [Session: %s]: '%s'", session_id, effective_query)
        context_store.add_message(session_id, "user", raw_msg)

        target_agent = self.route_intent(effective_query)
        logger.info("Routed intent to agent: '%s'", target_agent)

        response_text = ""
        tasks_created = []
        state_snapshot = None
        browser_info = None

        if target_agent == "os_agent":
            # Launch Terminal or Native Desktop App
            eff_lower = effective_query.lower()
            if any(t in eff_lower for t in ["terminal", "console", "iterm"]):
                res = open_terminal()
                response_text = "🖥️ I have opened **Terminal** on your desktop screen."
            elif any(k in eff_lower for k in ["code", "vscode", "vs code", "visual studio code", "visual studio"]):
                res = open_desktop_app("Visual Studio Code")
                response_text = "💻 I have opened **Visual Studio Code** on your desktop."
            elif "finder" in eff_lower:
                res = open_desktop_app("Finder")
                response_text = "📂 I have opened **Finder** on your desktop."
            elif "calculator" in eff_lower or "calc" in eff_lower:
                res = open_desktop_app("Calculator")
                response_text = "🔢 I have opened **Calculator** for you."
            elif "notes" in eff_lower:
                res = open_desktop_app("Notes")
                response_text = "📝 I have opened **Notes** for you."
            elif "chrome" in eff_lower or "google chrome" in eff_lower:
                res = open_desktop_app("Google Chrome")
                response_text = "🌐 I have opened **Google Chrome** on your desktop."
            elif "safari" in eff_lower:
                res = open_desktop_app("Safari")
                response_text = "🧭 I have opened **Safari** on your desktop."
            elif "browser" in eff_lower:
                from backend.tools.browser_tool import open_url_in_browser
                open_url_in_browser("https://www.google.com")
                response_text = "🌐 I have opened your web browser on desktop."
            else:
                clean_name = re.sub(r'^(open|launch|start|run)\s+(the\s+|my\s+)?', '', eff_lower).strip()
                res = open_desktop_app(clean_name if clean_name else effective_query)
                response_text = f"🚀 I have launched **{res.get('app', clean_name)}** on your desktop."

        elif target_agent == "state_agent":
            agent_result = self.state_agent.handle(effective_query)
            response_text = agent_result.get("response", "")
            state_snapshot = agent_result.get("state_snapshot")

        elif target_agent == "task_agent":
            agent_result = self.task_agent.handle(effective_query)
            response_text = agent_result.get("response", "")
            tasks_created = agent_result.get("tasks_created", [])

        elif target_agent == "web_agent":
            agent_result = self.web_agent.handle(effective_query)
            response_text = agent_result.get("response", "")
            browser_info = agent_result.get("browser_info")

        else:
            # General Conversational Assistant response (like Siri / Copilot)
            latest_snap = self.state_agent.get_latest_snapshot() if include_state else None
            state_snapshot = latest_snap

            m_lower = message.lower().strip()
            if any(w in m_lower for w in ["hi", "hello", "hey", "good morning", "good afternoon", "greetings"]):
                active_str = f" in **{latest_snap.get('active_app')}**" if (latest_snap and latest_snap.get('active_app')) else ""
                response_text = (
                    f"Good day! I'm here monitoring your workspace{active_str}. "
                    "You can ask me to track your work, organize tasks, research technical solutions, or search across your tools."
                )
            elif any(w in m_lower for w in ["who are you", "what are you", "your name"]):
                response_text = (
                    "I am your **Digital Workspace Agent** — an intelligent desktop assistant designed to track your context, "
                    "manage action items, and perform technical research directly alongside your work."
                )
            elif any(w in m_lower for w in ["what can you do", "help", "commands", "features"]):
                response_text = (
                    "Here is what I can do for you:\n\n"
                    "1. **Context Awareness**: Ask *'What was I working on?'* or *'What changed while I was away?'*\n"
                    "2. **Task Actions**: Say *'Add task to review PR by 5pm'* or *'Show my pending tasks'*\n"
                    "3. **Technical Research**: Ask *'Compare Railway vs Vercel'* to get synthesized recommendations\n"
                    "4. **Desktop Browser Control**: Say *'Open [topic] in browser'* to launch a live search on your screen\n"
                    "5. **Voice Input**: Tap the microphone icon below to dictate commands directly."
                )
            elif any(w in m_lower for w in ["what should i do", "what's next", "whats next", "summarize my day"]):
                from backend.db.db import get_session
                from backend.db.models import Task
                with get_session() as s:
                    pending = s.query(Task).filter(Task.done == False).order_by(Task.due_at.asc()).all()
                
                app_name = latest_snap.get('active_app') if latest_snap else "your desktop"
                if pending:
                    task_titles = "\n".join([f"- **#{t.id}**: {t.title}" for t in pending[:3]])
                    response_text = (
                        f"You are currently focused on **{app_name}**.\n\n"
                        f"Here are your highest priority tasks:\n{task_titles}\n\n"
                        "Would you like me to mark any of these as completed, or research details for them?"
                    )
                else:
                    response_text = (
                        f"You are currently working in **{app_name}** with a clear task board! "
                        "Let me know if you'd like me to add new action items or research a technical topic."
                    )
            else:
                workspace_info = ""
                if latest_snap and latest_snap.get("active_app"):
                    workspace_info = f"\n\n*Current context: Focused in **{latest_snap.get('active_app')}** ({latest_snap.get('active_window_title') or ''}).*"

                response_text = (
                    f"I understand: *\"{message}\"*. "
                    "I can help you break this down into tasks, pull relevant research, or check your workspace activity."
                    f"{workspace_info}"
                )

        now_iso = datetime.now(timezone.utc).isoformat()

        # Attach active state if not already attached and requested
        if state_snapshot is None and include_state:
            state_snapshot = self.state_agent.get_latest_snapshot()

        context_store.add_message(
            session_id,
            "assistant",
            response_text,
            metadata={
                "routed_agent": target_agent,
                "tasks_created": tasks_created,
                "browser_info": browser_info,
            }
        )

        return {
            "response": response_text,
            "routed_agent": target_agent,
            "tasks_created": tasks_created,
            "browser_info": browser_info,
            "state_snapshot": state_snapshot,
            "timestamp": now_iso,
        }


# Global singleton router
coordinator = CoordinatorRouter()
