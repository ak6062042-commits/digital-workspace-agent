"""Interactive personal command center for the local Workspace Agent."""
import html
import os
import sys
import webbrowser
from pathlib import Path
from urllib.parse import urlparse

import requests
from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QBrush, QFont, QPainter
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

ROOT = Path(__file__).resolve().parents[2]


def _load_project_env():
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_project_env()
BACKEND_URL = os.getenv("WORKSPACE_BACKEND_URL", "http://localhost:8000").rstrip("/")
API_TOKEN = os.getenv("API_TOKEN", "")
POLL_INTERVAL_MS = 3000


def api_headers():
    return {"X-Workspace-Token": API_TOKEN, "Content-Type": "application/json"}


def _safe_external_url(url):
    parsed = urlparse(url or "")
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"} or not host or parsed.username or parsed.password:
        return ""
    if host in {"localhost", "127.0.0.1", "::1"} or host.endswith(".local"):
        return ""
    return url


class DataFetcher(QThread):
    result_ready = pyqtSignal(object)

    def run(self):
        try:
            response = requests.get(f"{BACKEND_URL}/api/workspace/overview", headers=api_headers(), timeout=3)
            if response.ok:
                self.result_ready.emit(response.json())
                return
            self.result_ready.emit({"_error": f"Backend returned {response.status_code}"})
        except (requests.RequestException, ValueError) as error:
            self.result_ready.emit({"_error": str(error)})


class ActionThread(QThread):
    result_ready = pyqtSignal(object)

    def __init__(self, method, url, body=None):
        super().__init__()
        self.method = method
        self.url = url
        self.body = body

    def run(self):
        try:
            response = requests.request(self.method, self.url, headers=api_headers(), json=self.body, timeout=15)
            payload = response.json() if response.content else {}
            if not response.ok:
                payload = {"error": payload.get("detail", f"Request failed: {response.status_code}")}
        except requests.RequestException as error:
            payload = {"error": str(error)}
        self.result_ready.emit(payload)


class FloatingIcon(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Digital Workspace Command Center")
        self.setToolTip("Open Personal Workspace Command Center")
        self.badge_count = 0
        self.drag_pos = None
        self.click_start = None
        self.panel = None
        self._suggestions, self._tasks, self._notifications, self._snapshot, self._writing = [], [], [], None, []
        self._fetcher, self._pending_actions = None, []
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(84, 84)
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.right() - 96, screen.center().y() - 42)
        self.timer = QTimer()
        self.timer.timeout.connect(self.start_fetch)
        self.timer.start(POLL_INTERVAL_MS)
        self.start_fetch()

    def start_fetch(self):
        if self._fetcher and self._fetcher.isRunning():
            return
        self._fetcher = DataFetcher()
        self._fetcher.result_ready.connect(self.on_data_ready)
        self._fetcher.start()

    def on_data_ready(self, overview):
        if overview.get("_error"):
            if self.panel and self.panel.isVisible():
                self.panel.set_status(f"Offline: {overview['_error']}", error=True)
            return
        self._suggestions = overview.get("planner", {}).get("suggestions", [])
        self._tasks = overview.get("tasks", [])
        self._notifications = overview.get("notifications", [])
        self._snapshot = overview.get("snapshot")
        self._writing = overview.get("writing_suggestions", [])
        active_tasks = sum(1 for task in self._tasks if not task.get("done"))
        self.badge_count = len(self._suggestions) + active_tasks + len(self._notifications)
        self.update()
        if self.panel and self.panel.isVisible():
            self.panel.populate(self._suggestions, self._tasks, self._notifications, self._snapshot, self._writing)
            self.panel.set_status("Connected")

    def run_action(self, method, url, body=None, callback=None):
        thread = ActionThread(method, url, body)
        thread.result_ready.connect(self.start_fetch)
        if callback:
            thread.result_ready.connect(callback)
        self._pending_actions.append(thread)
        thread.finished.connect(lambda: self._pending_actions.remove(thread) if thread in self._pending_actions else None)
        thread.start()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor(20, 20, 25, 235)))
        painter.setPen(QColor(212, 255, 0))
        painter.drawEllipse(2, 2, 80, 80)
        painter.setPen(QColor(212, 255, 0))
        painter.setFont(QFont("Segoe UI", 26))
        painter.drawText(self.rect(), Qt.AlignCenter, "A")
        if self.badge_count:
            painter.setBrush(QBrush(QColor(255, 88, 88)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(58, 2, 24, 24)
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
            painter.drawText(58, 2, 24, 24, Qt.AlignCenter, str(min(self.badge_count, 99)))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            self.click_start = event.globalPos()

    def mouseMoveEvent(self, event):
        if self.drag_pos:
            self.move(event.globalPos() - self.drag_pos)

    def mouseReleaseEvent(self, event):
        if self.drag_pos and self.click_start and (event.globalPos() - self.click_start).manhattanLength() < 5:
            self.toggle_panel()
        self.drag_pos = None

    def toggle_panel(self):
        if self.panel and self.panel.isVisible():
            self.panel.close()
            return
        self.panel = PopupPanel(self)
        available = QApplication.primaryScreen().availableGeometry()
        x = max(available.left() + 12, min(self.x() - self.panel.width() + 30, available.right() - self.panel.width() - 12))
        y = max(available.top() + 12, min(self.y() - 160, available.bottom() - self.panel.height() - 12))
        self.panel.move(x, y)
        self.panel.populate(self._suggestions, self._tasks, self._notifications, self._snapshot, self._writing)
        self.panel.show()
        self.panel.raise_()
        self.panel.activateWindow()


class PopupPanel(QWidget):
    def __init__(self, icon_ref):
        super().__init__()
        self.icon_ref = icon_ref
        self.setWindowTitle("Digital Workspace Command Center")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setMinimumSize(540, 560)
        self.resize(680, 720)
        self.setStyleSheet("background:#0d0f11;color:#e5e5e5;border:1px solid #d4ff00;border-radius:10px;")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 14, 16, 16)
        outer.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Personal Workspace")
        title.setStyleSheet("color:#d4ff00;font-weight:bold;font-size:20px;")
        self.status = QLabel("Connecting…")
        self.status.setStyleSheet("color:#a5f3fc;font-size:11px;")
        close = QPushButton("×")
        close.setToolTip("Close command center")
        close.setFixedSize(28, 28)
        close.setStyleSheet("background:#1b1f23;color:#e5e5e5;border:1px solid #30363d;border-radius:14px;font-size:18px;")
        close.clicked.connect(self.close)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.status)
        header.addWidget(close)
        outer.addLayout(header)

        self.current_work = QLabel("No workspace context yet")
        self.current_work.setWordWrap(True)
        self.current_work.setStyleSheet("color:#dbeafe;background:#15181b;border:1px solid #26313a;padding:10px;border-radius:7px;font-size:13px;")
        outer.addWidget(self.current_work)

        command_row = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Ask, research, create a task, or open an app…")
        self.chat_input.returnPressed.connect(self.send_chat)
        self.chat_input.setStyleSheet("background:#15181b;border:1px solid #30363d;border-radius:6px;padding:8px;color:#f8fafc;")
        send = self._button("Send", accent=True)
        send.clicked.connect(self.send_chat)
        command_row.addWidget(self.chat_input, 1)
        command_row.addWidget(send)
        outer.addLayout(command_row)

        quick = QHBoxLayout()
        for label, action in [("Research current", self.send_current_research), ("What changed?", lambda: self.send_chat("What changed while I was away?")), ("Open dashboard", self.open_dashboard)]:
            button = self._button(label)
            button.clicked.connect(action)
            quick.addWidget(button)
        quick.addStretch(1)
        outer.addLayout(quick)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("QTabWidget::pane{border:1px solid #2b3036;border-radius:6px;background:#111417;}QTabBar::tab{background:#161a1d;color:#94a3b8;padding:7px 14px;margin-right:4px;border-top-left-radius:5px;border-top-right-radius:5px;}QTabBar::tab:selected{background:#d4ff00;color:#111;font-weight:bold;}")
        self.today_tab, self.today_layout = self._scroll_tab()
        self.research_tab = QWidget()
        research_layout = QVBoxLayout(self.research_tab)
        research_layout.setContentsMargins(10, 10, 10, 10)
        self.chat_log = QTextBrowser()
        self.chat_log.setOpenExternalLinks(False)
        self.chat_log.setReadOnly(True)
        self.chat_log.setHtml("<p>Ask a question or use <b>Research current</b>. Source pages remain unopened until you choose a source button.</p>")
        self.chat_log.setStyleSheet("background:#111417;border:0;color:#dbeafe;font-size:13px;")
        self.source_area, self.source_layout = self._scroll_tab()
        research_layout.addWidget(self.chat_log, 2)
        research_layout.addWidget(self.source_area, 1)
        self.inbox_tab, self.inbox_layout = self._scroll_tab()
        self.tabs.addTab(self.today_tab, "Today")
        self.tabs.addTab(self.research_tab, "Research")
        self.tabs.addTab(self.inbox_tab, "Inbox & Writing")
        outer.addWidget(self.tabs, 1)

        footer = QHBoxLayout()
        refresh = self._button("Refresh")
        refresh.clicked.connect(self.icon_ref.start_fetch)
        dashboard = self._button("Open full dashboard", accent=True)
        dashboard.clicked.connect(self.open_dashboard)
        footer.addWidget(refresh)
        footer.addStretch(1)
        footer.addWidget(dashboard)
        outer.addLayout(footer)

    def _scroll_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:none;background:#111417;")
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(7)
        layout.addStretch(1)
        scroll.setWidget(content)
        return scroll, layout

    @staticmethod
    def _button(text, accent=False):
        button = QPushButton(text)
        if accent:
            button.setStyleSheet("background:#d4ff00;color:#111;border:0;border-radius:5px;padding:7px 11px;font-weight:bold;")
        else:
            button.setStyleSheet("background:#1b1f23;color:#dbeafe;border:1px solid #30363d;border-radius:5px;padding:7px 10px;")
        return button

    @staticmethod
    def _label(text, muted=False):
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet(f"color:{'#94a3b8' if muted else '#e5e7eb'};font-size:12px;line-height:1.4;")
        return label

    @staticmethod
    def _section(text):
        label = QLabel(text)
        label.setStyleSheet("color:#38bdf8;font-weight:bold;font-size:14px;margin-top:4px;")
        return label

    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def set_status(self, text, error=False):
        self.status.setText(text)
        self.status.setStyleSheet(f"color:{'#fda4af' if error else '#a5f3fc'};font-size:11px;")

    def send_chat(self, command=None):
        message = command or self.chat_input.text().strip()
        if not message:
            return
        self.chat_input.clear()
        self.set_status("Working…")
        self.chat_log.setHtml(f"<p><b>You</b><br>{html.escape(message)}</p><p><b>Assistant</b><br>Working on it…</p>")
        self.tabs.setCurrentWidget(self.research_tab)
        self.icon_ref.run_action("POST", f"{BACKEND_URL}/api/chat", {"message": message}, self.show_chat_result)

    def send_current_research(self):
        snapshot = self.icon_ref._snapshot or {}
        topic = snapshot.get("browser_tab_title") or snapshot.get("active_window_title") or snapshot.get("active_app")
        if not topic:
            self.tabs.setCurrentWidget(self.research_tab)
            self.chat_log.setHtml("<p>No current context is available yet. Start the watcher or enable Chrome active-tab sync, then try again.</p>")
            return
        self.send_chat(f"Research {topic}")

    def show_chat_result(self, payload):
        if payload.get("error"):
            self.set_status("Request failed", error=True)
            self.chat_log.setHtml(f"<p><b>Request failed</b><br>{html.escape(payload['error'])}</p>")
            return
        self.set_status("Ready")
        response = html.escape(payload.get("response") or "No response returned.").replace("\n", "<br>")
        self.chat_log.setHtml(f"<p><b>Assistant</b></p><p>{response}</p>")
        self._clear_layout(self.source_layout)
        sources = payload.get("research_sources") or []
        if sources:
            self.source_layout.addWidget(self._section("Open a source when you are ready"))
            self.source_layout.addWidget(self._label("Research pages are untrusted. Check the domain before opening one.", muted=True))
            for source in sources[:6]:
                self.source_layout.addWidget(self._source_button(source))
        else:
            self.source_layout.addWidget(self._label("No source list was returned for this request.", muted=True))
        self.source_layout.addStretch(1)

    def open_dashboard(self):
        webbrowser.open("http://localhost:5173")

    def populate(self, suggestions, tasks, notifications, snapshot, writing):
        app = (snapshot or {}).get("active_app", "No active app")
        title = (snapshot or {}).get("active_window_title") or "No active window reported"
        timestamp = (snapshot or {}).get("captured_at") or "waiting for first sync"
        self.current_work.setText(f"<b>Current work</b> · {html.escape(app)}<br>{html.escape(title)}<br><span style='color:#94a3b8'>Last sync: {html.escape(timestamp)}</span>")

        self._clear_layout(self.today_layout)
        active_tasks = [task for task in tasks if not task.get("done")]
        self.today_layout.addWidget(self._section(f"Tasks ({len(active_tasks)} active)"))
        if active_tasks:
            for task in active_tasks[:10]:
                self.today_layout.addWidget(self._task_row(task))
        else:
            self.today_layout.addWidget(self._label("All caught up. Add a task from the command box whenever a new idea arrives.", muted=True))
        if suggestions:
            self.today_layout.addWidget(self._section("Suggestions"))
            for suggestion in suggestions[:4]:
                self.today_layout.addWidget(self._suggestion_row(suggestion))
        self.today_layout.addStretch(1)

        self._clear_layout(self.inbox_layout)
        self.inbox_layout.addWidget(self._section(f"Notifications ({len(notifications)})"))
        if notifications:
            for note in notifications[:6]:
                self.inbox_layout.addWidget(self._notification_row(note))
        else:
            self.inbox_layout.addWidget(self._label("No notifications waiting.", muted=True))
        self.inbox_layout.addWidget(self._section("Writing improvements"))
        if writing:
            for item in writing[:4]:
                self.inbox_layout.addWidget(self._writing_row(item))
        else:
            self.inbox_layout.addWidget(self._label("Writing analysis will appear here after you submit text from the dashboard, browser companion, or Word add-in.", muted=True))
        self.inbox_layout.addStretch(1)

    def _task_row(self, task):
        frame = QFrame()
        frame.setStyleSheet("QFrame{background:#161a1d;border:1px solid #2b3036;border-radius:6px;}")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(8, 7, 8, 7)
        detail = QVBoxLayout()
        status = task.get("status", "pending").upper()
        detail.addWidget(self._label(f"[{status}] {task.get('title', '')}"))
        context = task.get("source_title") or task.get("source_app")
        if context:
            detail.addWidget(self._label(f"Context: {context}", muted=True))
        layout.addLayout(detail, 1)
        done = self._button("Done")
        done.clicked.connect(lambda _checked=False, task_id=task["id"]: self.icon_ref.run_action("PATCH", f"{BACKEND_URL}/api/tasks/{task_id}", {"done": True}, lambda _payload: self.set_status("Task completed")))
        action = self._button("Open" if task.get("has_context") else "Link")
        if task.get("has_context"):
            action.clicked.connect(lambda _checked=False, task_id=task["id"]: self.icon_ref.run_action("POST", f"{BACKEND_URL}/api/tasks/{task_id}/navigate", callback=lambda _payload: self.set_status("Opening context")))
        else:
            action.clicked.connect(lambda _checked=False, task_id=task["id"]: self.icon_ref.run_action("POST", f"{BACKEND_URL}/api/tasks/{task_id}/link-current-context", callback=lambda _payload: self.set_status("Context linked")))
        layout.addWidget(done)
        layout.addWidget(action)
        return frame

    def _suggestion_row(self, suggestion):
        frame = QFrame()
        frame.setStyleSheet("QFrame{background:#161a1d;border:1px solid #2b3036;border-radius:6px;}")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 7, 8, 7)
        layout.addWidget(self._label(f"{suggestion.get('context', '')}: {suggestion.get('response', '')}"))
        buttons = QHBoxLayout()
        dismiss = self._button("Dismiss")
        dismiss.clicked.connect(lambda _checked=False, suggestion_id=suggestion["id"]: self.icon_ref.run_action("POST", f"{BACKEND_URL}/api/planner/suggestions/{suggestion_id}/dismiss", callback=lambda _payload: self.set_status("Suggestion dismissed")))
        buttons.addWidget(dismiss)
        for topic in suggestion.get("related_queries", [])[:2]:
            query = str(topic.get("query", "")).strip()
            if query:
                research = self._button("Research")
                research.clicked.connect(lambda _checked=False, value=query: self.send_chat(f"Research {value}"))
                buttons.addWidget(research)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        return frame

    def _notification_row(self, note):
        row = QFrame()
        row.setStyleSheet("QFrame{background:#161a1d;border:1px solid #2b3036;border-radius:6px;}")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(8, 7, 8, 7)
        layout.addWidget(self._label(f"{note.get('source', 'Notification')}\n{note.get('summary', '')}"), 1)
        review = self._button("Review")
        review.clicked.connect(lambda _checked=False, note_id=note["id"]: self.icon_ref.run_action("PATCH", f"{BACKEND_URL}/api/notifications/{note_id}/review", callback=lambda _payload: self.set_status("Notification reviewed")))
        layout.addWidget(review)
        return row

    def _writing_row(self, item):
        frame = QFrame()
        frame.setStyleSheet("QFrame{background:#161a1d;border:1px solid #2b3036;border-radius:6px;}")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 7, 8, 7)
        layout.addWidget(self._label(item.get("suggestion_text", "")))
        keywords = item.get("keywords", [])
        if keywords:
            layout.addWidget(self._label(f"Keywords: {', '.join(keywords)}", muted=True))
        queries = QHBoxLayout()
        for topic in item.get("related_queries", [])[:2]:
            query = str(topic.get("query", "")).strip()
            if query:
                research = self._button("Research")
                research.clicked.connect(lambda _checked=False, value=query: self.send_chat(f"Research {value}"))
                queries.addWidget(research)
        if queries.count():
            queries.addStretch(1)
            layout.addLayout(queries)
        return frame

    def _source_button(self, source):
        url = _safe_external_url(source.get("url", ""))
        title = source.get("title", "Untitled source")
        summary = source.get("summary") or source.get("snippet") or ""
        domain = source.get("domain") or "source"
        button = self._button(f"Open {domain}: {title[:52]}")
        button.setToolTip(f"{title}\n\n{summary}")
        button.setEnabled(bool(url))
        button.clicked.connect(lambda _checked=False, value=url: webbrowser.open(value))
        return button


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    icon = FloatingIcon()
    icon.show()
    sys.exit(app.exec_())
