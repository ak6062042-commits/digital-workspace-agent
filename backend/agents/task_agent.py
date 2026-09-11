import re
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

from backend.db.db import get_session
from backend.db.models import Task

logger = logging.getLogger("TaskAgent")


class TaskAgent:
    """
    Specialized agent for managing workspace tasks in SQLite.
    Supports natural language parsing for task creation, completion, and listing.
    """

    @staticmethod
    def _extract_due_date(text: str) -> Optional[datetime]:
        """Simple regex and relative time parsing for due dates."""
        text_lower = text.lower()
        now = datetime.now(timezone.utc)

        if "tomorrow" in text_lower:
            return now + timedelta(days=1)
        if "today" in text_lower or "tonight" in text_lower:
            return now + timedelta(hours=6)
        if "next week" in text_lower:
            return now + timedelta(days=7)
        if "in 2 days" in text_lower or "in two days" in text_lower:
            return now + timedelta(days=2)
        if "by friday" in text_lower:
            days_ahead = (4 - now.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            return now + timedelta(days=days_ahead)
        return None

    def handle(self, query: str) -> Dict[str, Any]:
        """
        Process task-related query and perform database operations.
        """
        q_lower = query.lower().strip()
        tasks_created = []
        tasks_modified = []

        # 1. Mark task as done / complete
        # e.g., "complete task 2", "mark task 1 as done", "finish task 3"
        done_match = re.search(r"(?:complete|done|finish|mark)\s+(?:task\s+)?#?(\d+)", q_lower)
        if done_match:
            task_id = int(done_match.group(1))
            with get_session() as session:
                task = session.query(Task).filter(Task.id == task_id).first()
                if task:
                    task.done = True
                    session.commit()
                    session.refresh(task)
                    tasks_modified.append(task.to_dict())
                    return {
                        "agent": "task_agent",
                        "response": f"Marked task #{task.id} (**{task.title}**) as completed.",
                        "tasks_modified": tasks_modified,
                        "tasks_created": []
                    }
                else:
                    return {
                        "agent": "task_agent",
                        "response": f"Could not find task #{task_id} in your workspace.",
                        "tasks_modified": [],
                        "tasks_created": []
                    }

        # 2. List tasks query
        # e.g., "what are my tasks?", "list pending tasks", "show tasks"
        if any(keyword in q_lower for keyword in ["list task", "show task", "what are my task", "view task", "my tasks"]):
            with get_session() as session:
                pending_tasks = session.query(Task).filter(Task.done == False).order_by(Task.created_at.desc()).all()
                if not pending_tasks:
                    return {
                        "agent": "task_agent",
                        "response": "You currently have **no pending tasks** on your board. Workspace is clean!",
                        "tasks_modified": [],
                        "tasks_created": []
                    }
                
                task_items = "\n".join([f"- **#{t.id}**: {t.title}" + (f" *(Due: {t.due_at.strftime('%b %d')} )*" if t.due_at else "") for t in pending_tasks])
                return {
                    "agent": "task_agent",
                    "response": f"Here are your active workspace tasks:\n\n{task_items}",
                    "tasks_modified": [],
                    "tasks_created": []
                }

        # 3. Create task intent
        # e.g., "add task: review pull request", "create task to research deployment", "remind me to write tests"
        title = query
        for prefix in ["add task to", "create a task to", "create task to", "add task:", "new task:", "add a task to", "remind me to", "add task"]:
            if q_lower.startswith(prefix):
                title = query[len(prefix):].strip()
                break

        title = title.strip(": -")
        if not title:
            title = query

        due_date = self._extract_due_date(query)

        with get_session() as session:
            new_task = Task(
                title=title,
                description=f"Generated via Workspace Coordinator on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
                done=False,
                due_at=due_date
            )
            session.add(new_task)
            session.commit()
            session.refresh(new_task)
            tasks_created.append(new_task.to_dict())

        due_str = f" with due date **{due_date.strftime('%A, %b %d')}**" if due_date else ""
        return {
            "agent": "task_agent",
            "response": f"Created new task #{new_task.id}: **{new_task.title}**{due_str}.",
            "tasks_created": tasks_created,
            "tasks_modified": []
        }
