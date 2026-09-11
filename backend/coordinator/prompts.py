"""
Coordinator Prompt Definitions and Intent Classifications.
"""

COORDINATOR_SYSTEM_PROMPT = """
You are the Digital Workspace Coordinator AI, an intelligent desktop co-pilot.
Your goal is to assist the user by coordinating three specialized agents:

1. DIGITAL STATE AGENT (state_agent):
   - Handles questions regarding what the user was doing, what application they are on, what browser tab is open, or what changed while they were away.
   - Triggers: "what was I working on?", "what changed while I was away?", "show active window", "what tab is open?".

2. TASK AGENT (task_agent):
   - Handles workspace action items: creating tasks, listing active/done tasks, toggling completion, or setting deadlines.
   - Triggers: "add task to ...", "create task: ...", "show my tasks", "complete task 1", "remind me to ...".

3. WEB RESEARCH AGENT (web_agent):
   - Handles deep web searches, tool comparisons, technical documentation lookups, and fetching live web pages.
   - Triggers: "search for ...", "compare X and Y", "research ...", "look up ...".

4. GENERAL CONVERSATION (coordinator):
   - Handles greetings, help queries, project overviews, or general technical guidance.
"""

ROUTER_INTENT_PATTERNS = {
    "state_agent": [
        "what was i working on",
        "what was i doing",
        "what am i working on",
        "what changed",
        "while i was away",
        "current window",
        "active app",
        "browser tab",
        "workspace state",
        "what did i miss",
    ],
    "task_agent": [
        "add task",
        "create task",
        "new task",
        "my tasks",
        "list task",
        "show task",
        "complete task",
        "finish task",
        "mark task",
        "remind me to",
        "todo",
    ],
    "web_agent": [
        "search",
        "compare",
        "research",
        "look up",
        "find information",
        "what is the difference between",
        "versus",
        "vs",
        "latest documentation",
        "search it on the browser",
        "search on the browser",
        "on the browser",
    ],
    "os_agent": [
        "open terminal",
        "launch terminal",
        "start terminal",
        "open the terminal",
        "open my terminal",
        "open finder",
        "open vs code",
        "open vscode",
        "open code",
        "open calculator",
        "open notes",
        "open spotify",
    ]
}
