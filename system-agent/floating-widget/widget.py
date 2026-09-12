"""Compact authenticated command center for the local Workspace Agent."""
import os
import sys
import webbrowser
from pathlib import Path

import requests
from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QBrush, QFont, QPainter
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget

BACKEND_URL = "http://localhost:8000"
ROOT = Path(__file__).resolve().parents[2]


def _load_project_env():
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_project_env()
API_TOKEN = os.getenv("API_TOKEN", "")
POLL_INTERVAL_MS = 3000


def api_headers():
    return {"X-Workspace-Token": API_TOKEN, "Content-Type": "application/json"}


class DataFetcher(QThread):
    result_ready = pyqtSignal(object)

    def run(self):
        overview = {}
        try:
            response = requests.get(f"{BACKEND_URL}/api/workspace/overview", headers=api_headers(), timeout=2)
            if response.ok:
                overview = response.json()
        except Exception:
            pass
        self.result_ready.emit(overview)


class ActionThread(QThread):
    result_ready = pyqtSignal(object)

    def __init__(self, method, url, body=None):
        super().__init__()
        self.method, self.url, self.body = method, url, body

    def run(self):
        try:
            response = requests.request(self.method, self.url, headers=api_headers(), json=self.body, timeout=8)
            payload = response.json() if response.content else {}
            if not response.ok:
                payload = {"error": payload.get("detail", f"Request failed: {response.status_code}")}
        except Exception as error:
            payload = {"error": str(error)}
        self.result_ready.emit(payload)


class FloatingIcon(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Digital Workspace Command Center")
        self.badge_count, self.drag_pos, self.panel = 0, None, None
        self._suggestions, self._tasks, self._notifications, self._snapshot, self._writing = [], [], [], None, []
        self._fetcher, self._pending_actions = None, []
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(84, 84)
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - 104, screen.height() // 2 - 42)
        self.timer = QTimer(); self.timer.timeout.connect(self.start_fetch); self.timer.start(POLL_INTERVAL_MS)
        self.start_fetch()

    def start_fetch(self):
        if self._fetcher and self._fetcher.isRunning(): return
        self._fetcher = DataFetcher(); self._fetcher.result_ready.connect(self.on_data_ready); self._fetcher.start()

    def on_data_ready(self, overview):
        suggestions = overview.get("planner", {}).get("suggestions", [])
        tasks = overview.get("tasks", [])
        notifications = overview.get("notifications", [])
        snapshot = overview.get("snapshot")
        writing = overview.get("writing_suggestions", [])
        self._suggestions, self._tasks, self._notifications, self._snapshot, self._writing = suggestions, tasks, notifications, snapshot, writing
        self.badge_count = len(suggestions) + len(tasks) + len(notifications) + len(writing); self.update()
        if self.panel and self.panel.isVisible(): self.panel.populate(suggestions, tasks, notifications, snapshot, writing)

    def run_action(self, method, url, body=None, callback=None):
        thread = ActionThread(method, url, body)
        thread.result_ready.connect(self.start_fetch)
        if callback: thread.result_ready.connect(callback)
        self._pending_actions.append(thread)
        thread.finished.connect(lambda: self._pending_actions.remove(thread) if thread in self._pending_actions else None)
        thread.start()

    def paintEvent(self, _event):
        painter = QPainter(self); painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor(20, 20, 25, 235))); painter.setPen(QColor(212, 255, 0)); painter.drawEllipse(2, 2, 80, 80)
        painter.setPen(QColor(212, 255, 0)); painter.setFont(QFont("Segoe UI", 26)); painter.drawText(self.rect(), Qt.AlignCenter, "A")
        if self.badge_count:
            painter.setBrush(QBrush(QColor(255, 60, 60))); painter.setPen(Qt.NoPen); painter.drawEllipse(58, 2, 24, 24)
            painter.setPen(QColor(255, 255, 255)); painter.setFont(QFont("Segoe UI", 10, QFont.Bold)); painter.drawText(58, 2, 24, 24, Qt.AlignCenter, str(self.badge_count))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft(); self.click_start = event.globalPos()

    def mouseMoveEvent(self, event):
        if self.drag_pos: self.move(event.globalPos() - self.drag_pos)

    def mouseReleaseEvent(self, event):
        if self.drag_pos and (event.globalPos() - self.click_start).manhattanLength() < 5: self.toggle_panel()
        self.drag_pos = None

    def toggle_panel(self):
        if self.panel and self.panel.isVisible(): self.panel.close(); self.panel = None; return
        self.panel = PopupPanel(self); self.panel.move(max(20, self.x() - 610), max(20, self.y() - 180))
        self.panel.populate(self._suggestions, self._tasks, self._notifications, self._snapshot, self._writing); self.panel.show()


class PopupPanel(QWidget):
    def __init__(self, icon_ref):
        super().__init__(); self.icon_ref = icon_ref; self.setWindowTitle("Digital Workspace Command Center")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool); self.setFixedSize(600, 720)
        self.setStyleSheet("background:#0d0f11;color:#e5e5e5;border:1px solid #d4ff00;border-radius:10px;")
        outer = QVBoxLayout(self); outer.setContentsMargins(16, 16, 16, 16); outer.setSpacing(10)
        title = QLabel("Digital Workspace Command Center"); title.setStyleSheet("color:#d4ff00;font-weight:bold;font-size:20px;"); outer.addWidget(title)
        self.current_work = QLabel("Current work: loading…"); self.current_work.setWordWrap(True); self.current_work.setStyleSheet("color:#a5f3fc;background:#15181b;padding:12px;border-radius:6px;font-size:14px;"); outer.addWidget(self.current_work)
        self.chat_log = QLabel("Type a safe request, e.g. ‘Open this tab’ or ‘Open VS Code’."); self.chat_log.setWordWrap(True); self.chat_log.setStyleSheet("color:#cbd5e1;font-size:14px;padding:7px;"); outer.addWidget(self.chat_log)
        row = QHBoxLayout(); self.chat_input = QLineEdit(); self.chat_input.setPlaceholderText("Ask the workspace assistant…"); self.chat_input.returnPressed.connect(self.send_chat)
        send = QPushButton("Send"); send.clicked.connect(self.send_chat); row.addWidget(self.chat_input); row.addWidget(send); outer.addLayout(row)
        quick = QHBoxLayout()
        for label, command in [("Open this tab", "Open this tab"), ("Open VS Code", "Open VS Code")]:
            button = QPushButton(label); button.clicked.connect(lambda _checked=False, text=command: self.send_chat(text)); quick.addWidget(button)
        research = QPushButton("Research"); research.clicked.connect(self.send_current_research); quick.addWidget(research)
        outer.addLayout(quick)
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True); self.scroll.setStyleSheet("border:none;")
        self.content = QWidget(); self.content_layout = QVBoxLayout(self.content); self.scroll.setWidget(self.content); outer.addWidget(self.scroll)
        dashboard = QPushButton("Open full dashboard"); dashboard.clicked.connect(lambda: webbrowser.open("http://localhost:5173")); dashboard.setStyleSheet("background:#d4ff00;color:#111;padding:8px;border-radius:5px;font-weight:bold;"); outer.addWidget(dashboard)

    def send_chat(self, command=None):
        message = command or self.chat_input.text().strip()
        if not message: return
        self.chat_input.clear(); self.chat_log.setText(f"You: {message}\nAssistant: planning…")
        self.icon_ref.run_action("POST", f"{BACKEND_URL}/api/chat", {"message": message}, self.show_chat_result)

    def send_current_research(self):
        snapshot = self.icon_ref._snapshot or {}
        topic = snapshot.get("browser_tab_title") or snapshot.get("active_window_title") or snapshot.get("active_app")
        if not topic:
            self.chat_log.setText("Assistant: No current workspace context has been captured yet. Start the watcher or enable Chrome active-tab sync first.")
            return
        self.send_chat(f"Research {topic}")

    def show_chat_result(self, payload):
        self.chat_log.setText(f"Assistant: {payload.get('response') or payload.get('error', 'No response')}")

    def populate(self, suggestions, tasks, notifications, snapshot, writing):
        app = (snapshot or {}).get("active_app", "No active app"); title = (snapshot or {}).get("active_window_title") or "No active window reported"
        self.current_work.setText(f"Current work: {app}\n{title}")
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        if notifications:
            self.content_layout.addWidget(self._section("Notifications"))
            for note in notifications[:3]: self.content_layout.addWidget(self._action_row(note.get("summary", ""), "Reviewed", "PATCH", f"{BACKEND_URL}/api/notifications/{note['id']}/review"))
        if writing:
            self.content_layout.addWidget(self._section("Writing improvements"))
            for item in writing[:2]:
                self.content_layout.addWidget(self._label(item.get("suggestion_text", "")))
                keywords = item.get("keywords", [])
                if keywords: self.content_layout.addWidget(self._label(f"Keywords: {', '.join(keywords)}"))
                for topic in item.get("related_queries", [])[:3]: self.content_layout.addWidget(self._related_query(topic))
        if suggestions:
            self.content_layout.addWidget(self._section("Suggestions"))
            for suggestion in suggestions[:3]:
                self.content_layout.addWidget(self._action_row(suggestion.get("context", ""), "Dismiss", "POST", f"{BACKEND_URL}/api/planner/suggestions/{suggestion['id']}/dismiss"))
                for topic in suggestion.get("related_queries", [])[:3]:
                    self.content_layout.addWidget(self._related_query(topic))
        if tasks:
            self.content_layout.addWidget(self._section("Active Tasks"))
            for task in tasks[:8]: self.content_layout.addWidget(self._task_button(task))
        if not suggestions and not tasks and not notifications and not writing: self.content_layout.addWidget(self._label("All caught up."))

    def _action_row(self, text, button_text, method, url):
        row = QWidget(); layout = QHBoxLayout(row); layout.setContentsMargins(0, 2, 0, 2)
        label = self._label(f"• {text}"); layout.addWidget(label, stretch=1)
        button = QPushButton(button_text); button.setStyleSheet("background:#222;color:#38bdf8;border:1px solid #38bdf8;border-radius:3px;padding:3px 7px;font-size:10px;"); button.clicked.connect(lambda: self.icon_ref.run_action(method, url)); layout.addWidget(button)
        return row

    @staticmethod
    def _section(text):
        label = QLabel(text); label.setStyleSheet("color:#38bdf8;font-weight:bold;font-size:15px;margin-top:10px;"); return label

    @staticmethod
    def _label(text):
        label = QLabel(text); label.setWordWrap(True); label.setStyleSheet("color:#e5e5e5;font-size:13px;line-height:1.45;"); return label

    def _related_query(self, topic):
        query = str(topic.get("query", "")).strip()
        button = QPushButton(f"Search Chrome: {topic.get('label', query)}")
        button.setEnabled(bool(query))
        button.setStyleSheet("background:#222;color:#d4ff00;border:1px solid #d4ff00;border-radius:4px;padding:7px 9px;font-size:12px;text-align:left;")
        button.clicked.connect(lambda _checked=False, value=query: self.send_chat(f"Research {value}"))
        return button

    def _task_button(self, task):
        has_context = bool(task.get("has_context"))
        text = f"• [{task.get('status', 'pending')}] {task.get('title', '')}"
        if has_context: text += "  ↗"
        button = QPushButton(text)
        button.setToolTip(task.get("source_title") or task.get("source_app") or "Link this older task to the active app or tab first.")
        button.setStyleSheet("background:transparent;color:#e5e5e5;border:none;padding:6px;text-align:left;font-size:13px;")
        if has_context:
            button.clicked.connect(lambda _checked=False, task_id=task["id"]: self.icon_ref.run_action("POST", f"{BACKEND_URL}/api/tasks/{task_id}/navigate"))
        else:
            button.setText(text + "  (Link current context)")
            button.clicked.connect(lambda _checked=False, task_id=task["id"]: self.icon_ref.run_action("POST", f"{BACKEND_URL}/api/tasks/{task_id}/link-current-context"))
        return button


if __name__ == "__main__":
    app = QApplication(sys.argv); app.setQuitOnLastWindowClosed(True); icon = FloatingIcon(); icon.show(); sys.exit(app.exec_())
