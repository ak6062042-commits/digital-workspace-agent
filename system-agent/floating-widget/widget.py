import sys
import os
from pathlib import Path
import webbrowser
import requests
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QScrollArea
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPainter, QBrush

BACKEND_URL = "http://localhost:8000"
ROOT = Path(__file__).resolve().parents[2]


def _load_project_env():
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_project_env()
API_TOKEN = os.getenv("API_TOKEN", "")
POLL_INTERVAL_MS = 20000  # 20 seconds


def api_headers():
    return {"X-Workspace-Token": API_TOKEN}


class DataFetcher(QThread):
    """Runs all network calls off the UI thread."""
    result_ready = pyqtSignal(list, list, list)  # suggestions, tasks, notifications

    def run(self):
        suggestions, tasks, notifications = [], [], []
        try:
            r = requests.get(f"{BACKEND_URL}/api/planner/suggestions", headers=api_headers(), timeout=2)
            if r.ok:
                suggestions = r.json()
        except Exception:
            pass
        try:
            r = requests.get(f"{BACKEND_URL}/api/tasks", params={"done": False}, headers=api_headers(), timeout=2)
            if r.ok:
                tasks = r.json()
        except Exception:
            pass
        try:
            r = requests.get(f"{BACKEND_URL}/api/notifications", params={"reviewed": False}, headers=api_headers(), timeout=2)
            if r.ok:
                notifications = r.json()
        except Exception:
            pass
        self.result_ready.emit(suggestions, tasks, notifications)


class ActionThread(QThread):
    """Fire-and-forget background call for button actions (dismiss/review)."""
    done = pyqtSignal()

    def __init__(self, method, url):
        super().__init__()
        self.method = method
        self.url = url

    def run(self):
        try:
            if self.method == "POST":
                requests.post(self.url, headers=api_headers(), timeout=3)
            elif self.method == "PATCH":
                requests.patch(self.url, headers=api_headers(), timeout=3)
        except Exception:
            pass
        self.done.emit()


class FloatingIcon(QWidget):
    def __init__(self):
        super().__init__()
        self.badge_count = 0
        self.drag_pos = None
        self.panel = None
        self._suggestions = []
        self._tasks = []
        self._notifications = []
        self._fetcher = None
        self._pending_actions = []  # keep references so threads aren't garbage collected

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(64, 64)

        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - 80, screen.height() // 2 - 32)

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

    def on_data_ready(self, suggestions, tasks, notifications):
        self._suggestions = suggestions
        self._tasks = tasks
        self._notifications = notifications
        self.badge_count = len(suggestions) + len(tasks) + len(notifications)
        self.update()
        if self.panel and self.panel.isVisible():
            self.panel.populate(self._suggestions, self._tasks, self._notifications)

    def run_action(self, method, url):
        """Called by the popup panel when a button is clicked."""
        t = ActionThread(method, url)
        t.done.connect(self.start_fetch)  # refresh after action completes
        self._pending_actions.append(t)
        t.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor(20, 20, 25, 230)))
        painter.setPen(QColor(212, 255, 0))
        painter.drawEllipse(2, 2, 60, 60)

        painter.setPen(QColor(212, 255, 0))
        painter.setFont(QFont("Segoe UI", 20))
        painter.drawText(self.rect(), Qt.AlignCenter, "A")

        if self.badge_count > 0:
            painter.setBrush(QBrush(QColor(255, 60, 60)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(42, 2, 20, 20)
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
            painter.drawText(42, 2, 20, 20, Qt.AlignCenter, str(self.badge_count))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            self.click_start = event.globalPos()

    def mouseMoveEvent(self, event):
        if self.drag_pos:
            self.move(event.globalPos() - self.drag_pos)

    def mouseReleaseEvent(self, event):
        if self.drag_pos and (event.globalPos() - self.click_start).manhattanLength() < 5:
            self.toggle_panel()
        self.drag_pos = None

    def toggle_panel(self):
        if self.panel and self.panel.isVisible():
            self.panel.close()
            self.panel = None
            return
        self.panel = PopupPanel(self)
        px = self.x() - 340
        py = max(20, self.y() - 100)
        self.panel.move(px, py)
        self.panel.populate(self._suggestions, self._tasks, self._notifications)
        self.panel.show()


class PopupPanel(QWidget):
    def __init__(self, icon_ref):
        super().__init__()
        self.icon_ref = icon_ref
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setFixedSize(340, 460)
        self.setStyleSheet("""
            background-color: #0d0f11;
            color: #e5e5e5;
            border: 1px solid #d4ff00;
            border-radius: 8px;
        """)

        self.outer_layout = QVBoxLayout(self)
        title = QLabel("Digital Workspace Agent")
        title.setStyleSheet("color: #d4ff00; font-weight: bold; font-size: 14px;")
        self.outer_layout.addWidget(title)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("border: none;")
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.scroll.setWidget(self.content)
        self.outer_layout.addWidget(self.scroll)

        open_btn = QPushButton("Open Dashboard")
        open_btn.clicked.connect(lambda: webbrowser.open("http://localhost:5173"))
        open_btn.setStyleSheet("background: #d4ff00; color: black; padding: 6px; border-radius: 4px;")
        self.outer_layout.addWidget(open_btn)

    def populate(self, suggestions, tasks, notifications):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if notifications:
            self.content_layout.addWidget(self._section_label("Notifications"))
            for n in notifications:
                self.content_layout.addWidget(
                    self._action_row(
                        text=n.get("summary") or n.get("raw_title", ""),
                        button_text="Reviewed",
                        method="PATCH",
                        url=f"{BACKEND_URL}/api/notifications/{n['id']}/review",
                    )
                )

        if suggestions:
            self.content_layout.addWidget(self._section_label("Suggestions"))
            for s in suggestions:
                self.content_layout.addWidget(
                    self._action_row(
                        text=s.get("context", ""),
                        button_text="Dismiss",
                        method="POST",
                        url=f"{BACKEND_URL}/api/planner/suggestions/{s['id']}/dismiss",
                    )
                )

        if tasks:
            self.content_layout.addWidget(self._section_label("Pending Tasks"))
            for t in tasks[:10]:
                self.content_layout.addWidget(self._item_label(f"• {t.get('title', '')}"))

        if not suggestions and not tasks and not notifications:
            self.content_layout.addWidget(self._item_label("All caught up."))

    def _action_row(self, text, button_text, method, url):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 2, 0, 2)

        lbl = QLabel(f"• {text}")
        lbl.setWordWrap(True)
        lbl.setStyleSheet("color: #e5e5e5; font-size: 12px;")
        layout.addWidget(lbl, stretch=1)

        btn = QPushButton(button_text)
        btn.setStyleSheet("background: #222; color: #38bdf8; border: 1px solid #38bdf8; border-radius: 3px; padding: 2px 6px; font-size: 10px;")
        btn.clicked.connect(lambda: self.icon_ref.run_action(method, url))
        layout.addWidget(btn)

        return row

    def _section_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #38bdf8; font-weight: bold; margin-top: 8px;")
        return lbl

    def _item_label(self, text):
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("color: #e5e5e5; font-size: 12px;")
        return lbl


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    icon = FloatingIcon()
    icon.show()
    sys.exit(app.exec_())
