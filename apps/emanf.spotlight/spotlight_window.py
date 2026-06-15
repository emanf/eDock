import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from PySide6.QtCore import Qt, QStringListModel, QEvent, QTimer, QThread
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QListView, QApplication, QAbstractItemView, QSizePolicy

from core.theming.theme_manager import Theme

from .search_worker import SearchWorker


class SpotlightWindow(QWidget):
    def __init__(self, app_ref):
        super().__init__(None)
        self.app_ref = app_ref
        self.current_results = []
        self.search_id = 0
        self.search_thread = None
        self.search_worker = None
        self.global_filter_installed = False
        self.input = None
        self.last_focus_hide_time = 0.0
        self.focus_hide_click_block_seconds = 0.7

        self.setObjectName("spotlightWindow")
        self.base_width = 620
        self.base_height = 62
        self.input_height = 34
        self.result_row_height = 46

        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(120)
        self.search_timer.timeout.connect(self.run_async_search)

        self.close_focus_timer = QTimer(self)
        self.close_focus_timer.setSingleShot(True)
        self.close_focus_timer.setInterval(80)
        self.close_focus_timer.timeout.connect(self.close_if_unfocused)

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFixedSize(self.base_width, self.base_height)
        self._build_ui()

        app = QApplication.instance()
        if app is not None and not self.global_filter_installed:
            app.installEventFilter(self)
            self.global_filter_installed = True

        self._apply_style()

    def _build_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setObjectName("mainLayout")
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.layout.setAlignment(Qt.AlignTop)

        self.container = QWidget(self)
        self.container.setObjectName("spotlightContainer")
        self.container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.container.setAttribute(Qt.WA_StyledBackground, True)
        self.container.setAutoFillBackground(True)

        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(16, 12, 16, 12)
        self.container_layout.setSpacing(8)
        self.container_layout.setAlignment(Qt.AlignTop)

        self.input = QLineEdit(self.container)
        self.input.setObjectName("searchInput")
        self.input.setFixedHeight(self.input_height)
        self.input.setPlaceholderText("Search apps, files, commands...")
        self.input.setAttribute(Qt.WA_MacShowFocusRect, False)
        self.input.setFocusPolicy(Qt.StrongFocus)
        self.input.textChanged.connect(self.on_text_changed)
        self.input.installEventFilter(self)

        self.list_view = QListView(self.container)
        self.list_view.setObjectName("searchListView")
        self.list_view.setFrameShape(QListView.NoFrame)
        self.list_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.list_view.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.list_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.list_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.list_view.setUniformItemSizes(True)
        self.list_view.setSpacing(4)
        self.list_view.setMouseTracking(True)
        self.list_view.installEventFilter(self)

        self.list_model = QStringListModel(self)
        self.list_view.setModel(self.list_model)
        self.list_view.clicked.connect(self.activate_index)
        self.list_view.hide()
        self.list_view.setFixedHeight(0)

        self.container_layout.addWidget(self.input)
        self.container_layout.addWidget(self.list_view)
        self.layout.addWidget(self.container)

    def _apply_style(self):
        try:
            Theme.reload()
        except Exception:
            pass
        
        uic = Theme.to_ui_color
        
        colors = Theme.get_colors()
        button = Theme.get_button(Theme.BUTTON_NORMAL)
        
        window_bg_color = uic(colors.get(Theme.Colors.BACKGROUND))
        border_color = uic(colors.get(Theme.Colors.BORDER))

        text_color = uic(colors.get(Theme.Colors.TEXT))
        button_pressed = uic(button.get(Theme.Components.Button.PRESSED_COLOR))

        selected_bg = uic(button.get(Theme.Components.Button.PRESSED_COLOR))
        hover_bg = uic(button.get(Theme.Components.Button.HOVER_COLOR))
        scrollbar_color = uic(button.get(Theme.Components.Button.BORDER_COLOR))
        scrollbar_hover = uic(button.get(Theme.Components.Button.HOVER_COLOR))

        self.setStyleSheet(f"""
            QWidget#spotlightContainer {{
                background: {window_bg_color};
                border: 1px solid {border_color};
                border-radius: 18px;
            }}
            
            QLineEdit#searchInput {{
                background: transparent;
                border: none;
                color: {text_color};
                font-size: 19px;
                padding: 0px 4px;
                selection-background-color: {button_pressed};
            }}
            
            QLineEdit#searchInput:focus {{
                border: none;
            }}
            
            QListView#searchListView {{
                background: transparent;
                border: none;
                color: {text_color};
                outline: none;
                padding: 0px;
                font-size: 14px;
            }}

            QListView#searchListView::item {{
                background: transparent;
                border: none;
                border-radius: 10px;
                padding: 10px 12px;
                margin: 0px;
                color: {text_color};
            }}

            QListView#searchListView::item:selected {{
                background: {selected_bg};
                color: white;
            }}

            QListView#searchListView::item:selected:hover {{
                background: {selected_bg};
                color: white;
            }}

            QListView#searchListView::item:hover {{
                background: {hover_bg};
                color: {text_color};
            }}

            QScrollBar:vertical {{
                background: transparent;
                width: 8px;
                margin: 4px 0px 4px 0px;
                border: none;
            }}

            QScrollBar::handle:vertical {{
                background: {scrollbar_color};
                border-radius: 4px;
                min-height: 28px;
            }}

            QScrollBar::handle:vertical:hover {{
                background: {scrollbar_hover};
            }}

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
                width: 0px;
                background: transparent;
                border: none;
            }}

            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{
                background: transparent;
                border: none;
            }}

            QScrollBar:horizontal {{
                height: 0px;
                background: transparent;
                border: none;
            }}
        """)

    def consume_recent_focus_hide(self):
        if not self.last_focus_hide_time:
            return False

        elapsed = time.monotonic() - self.last_focus_hide_time

        if elapsed <= self.focus_hide_click_block_seconds:
            self.last_focus_hide_time = 0.0
            return True

        return False

    def get_app_context(self):
        return self.app_ref.get_app_context() if hasattr(self.app_ref, "get_app_context") else {}

    def get_project_root(self):
        try:
            from core.paths import get_root_dir
            return Path(get_root_dir())
        except Exception:
            return Path(__file__).resolve().parents[2]

    def get_cache_dir(self):
        try:
            return self.app_ref.get_cache_dir()
        except Exception:
            return Path(__file__).resolve().parents[2] / "cache"

    def get_history_file(self):
        try:
            return self.app_ref.get_cache_file("history.json")
        except Exception:
            return self.get_cache_dir() / "history.json"

    def make_json_safe(self, value):
        if value is None:
            return None

        if isinstance(value, (str, int, float, bool)):
            return value

        if isinstance(value, dict):
            safe = {}
            for key, item in value.items():
                if isinstance(key, (str, int, float, bool)):
                    safe[str(key)] = self.make_json_safe(item)
            return safe

        if isinstance(value, (list, tuple)):
            return [self.make_json_safe(item) for item in value]

        return str(value)

    def normalize_history_item(self, item):
        if not isinstance(item, dict):
            return None

        normalized = {}

        for key in ["id", "title", "subtitle", "path", "kind", "type", "app_id", "action", "icon", "command", "launch_data"]:
            if key not in item:
                continue

            value = self.make_json_safe(item.get(key))

            if value is None:
                continue

            normalized[key] = value

        if not normalized.get("title") and not normalized.get("path") and not normalized.get("id") and not normalized.get("app_id"):
            return None

        normalized.pop("score", None)
        normalized.pop("_history_score", None)
        normalized["last_opened"] = time.time()

        return normalized

    def history_item_key(self, item):
        kind = str(item.get("kind", "")).lower().strip()
        item_type = str(item.get("type", "")).lower().strip()
        item_id = str(item.get("id", "")).lower().strip()
        path = str(item.get("path", "")).lower().strip()
        title = str(item.get("title", "")).lower().strip()
        app_id = str(item.get("app_id", "")).lower().strip()
        action = str(item.get("action", "")).lower().strip()

        if app_id:
            return f"app_id:{app_id}"

        if kind and item_id:
            return f"{kind}:{item_id}"

        if path:
            return f"path:{path}"

        if item_type and title:
            return f"{item_type}:{title}"

        if kind and title:
            return f"{kind}:{title}"

        if action:
            return f"action:{action}"

        return title

    def read_history(self):
        data = []
        try:
            data = self.app_ref.read_json_cache("history.json", default=[]) if hasattr(self.app_ref, "read_json_cache") else []
        except Exception:
            data = []

        if not isinstance(data, list):
            return []

        clean = [item for item in data if isinstance(item, dict)]
        clean.sort(key=lambda item: float(item.get("last_opened", 0)), reverse=True)
        return clean

    def write_history(self, history):
        try:
            if hasattr(self.app_ref, "write_json_cache"):
                self.app_ref.write_json_cache("history.json", history[:50])
            else:
                history_file = self.get_history_file()
                history_file.parent.mkdir(parents=True, exist_ok=True)
                history_file.write_text(json.dumps(history[:50], indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as error:
            print("Spotlight history write error:", error)

    def save_to_cache(self, item):
        clean_item = self.normalize_history_item(item)

        if not clean_item:
            print("Spotlight history save skipped:", item)
            return

        history = self.read_history()
        clean_key = self.history_item_key(clean_item)
        new_history = []

        for old_item in history:
            if self.history_item_key(old_item) != clean_key:
                new_history.append(old_item)

        new_history.insert(0, clean_item)
        self.write_history(new_history)

    def is_child_widget(self, obj):
        if obj is None:
            return False

        if obj is self:
            return True

        try:
            if isinstance(obj, QWidget):
                return obj.window() is self or self.isAncestorOf(obj)
        except Exception:
            pass

        return False

    def eventFilter(self, obj, event):
        if self.isVisible() and event.type() == QEvent.KeyPress and event.key() == Qt.Key_Escape:
            self.hide()
            return True

        if self.isVisible() and event.type() in (QEvent.FocusOut, QEvent.WindowDeactivate):
            if self.is_child_widget(obj) or obj is self:
                self.close_focus_timer.start()
                return False

        if getattr(self, "input", None) is not None and obj is self.input and event.type() == QEvent.KeyPress:
            key = event.key()

            if key in (Qt.Key_Down, Qt.Key_Up):
                if self.list_view.isVisible() and self.list_model.rowCount() > 0:
                    current = self.list_view.currentIndex().row()

                    if current < 0:
                        current = 0
                    elif key == Qt.Key_Down:
                        current += 1
                    else:
                        current -= 1

                    current = max(0, min(self.list_model.rowCount() - 1, current))
                    self.list_view.setCurrentIndex(self.list_model.index(current, 0))
                    return True

            if key in (Qt.Key_Return, Qt.Key_Enter):
                self.activate_current_result()
                return True

        if getattr(self, "list_view", None) is not None and obj is self.list_view and event.type() == QEvent.KeyPress:
            key = event.key()

            if key in (Qt.Key_Return, Qt.Key_Enter):
                self.activate_current_result()
                return True

            if key == Qt.Key_Escape:
                self.hide()
                return True

        return super().eventFilter(obj, event)

    def close_if_unfocused(self):
        if not self.isVisible():
            return

        app = QApplication.instance()
        active_window = app.activeWindow() if app is not None else None
        focused = QApplication.focusWidget()

        if active_window is self:
            return

        if self.is_child_widget(focused):
            return

        self.last_focus_hide_time = time.monotonic()
        self.hide()

    def focus_spotlight_input(self):
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.ActiveWindowFocusReason)
        if self.input is not None:
            self.input.setFocus(Qt.ActiveWindowFocusReason)
            self.input.selectAll()

    def center_top(self):
        screen = QApplication.primaryScreen()

        if not screen:
            return

        rect = screen.availableGeometry()
        x = rect.x() + int((rect.width() - self.width()) / 2)
        y = rect.y() + 72
        self.move(x, y)

    def reset_compact(self, clear_input=True):
        self.search_timer.stop()
        self.close_focus_timer.stop()
        self.stop_current_search()

        if clear_input and self.input is not None:
            self.input.blockSignals(True)
            self.input.clear()
            self.input.blockSignals(False)

        self.current_results = []
        self.list_model.setStringList([])
        self.list_view.hide()
        self.list_view.setFixedHeight(0)
        self.list_view.setMinimumHeight(0)
        self.list_view.setMaximumHeight(0)
        self.setFixedSize(self.base_width, self.base_height)

        if self.layout is not None:
            self.layout.invalidate()
            self.layout.activate()

        self.updateGeometry()
        self.update()

    def toggle(self):
        if self.consume_recent_focus_hide():
            return

        if self.isVisible():
            self.reset_compact()
            self.hide()
            return

        self.reset_compact(clear_input=True)
        self.current_results = self.read_history()[:10]
        self.refresh_list()

        self.center_top()
        self.show()
        QTimer.singleShot(0, self.focus_spotlight_input)
        QTimer.singleShot(40, self.focus_spotlight_input)

    def showEvent(self, event):
        super().showEvent(event)
        self.center_top()
        QTimer.singleShot(0, self.focus_spotlight_input)

    def hideEvent(self, event):
        self.reset_compact()
        super().hideEvent(event)

    def collapse(self):
        self.list_view.hide()
        self.list_view.setFixedHeight(0)
        self.list_view.setMinimumHeight(0)
        self.list_view.setMaximumHeight(0)
        self.setFixedSize(self.base_width, self.base_height)

        if self.layout is not None:
            self.layout.invalidate()
            self.layout.activate()

        self.updateGeometry()
        self.update()
        self.center_top()

    def expand(self):
        rows = min(max(len(self.current_results), 1), 8)
        list_height = (rows * self.result_row_height) + max(0, rows - 1) * 4 + 8
        total_height = self.base_height + list_height + 10

        self.list_view.setMinimumHeight(list_height)
        self.list_view.setMaximumHeight(list_height)
        self.list_view.setFixedHeight(list_height)
        self.list_view.show()

        self.setFixedSize(self.base_width, total_height)

        if self.layout is not None:
            self.layout.invalidate()
            self.layout.activate()

        self.updateGeometry()
        self.update()
        self.center_top()

    def collect_local_apps(self):
        apps = []
        apps_dir = self.get_project_root() / "apps"

        if not apps_dir.exists():
            return apps

        for folder in sorted(apps_dir.iterdir(), key=lambda p: p.name.lower()):
            if not folder.is_dir():
                continue

            manifest_path = folder / "app.json"

            if not manifest_path.exists():
                continue

            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception:
                continue

            app_id = str(data.get("id", folder.name)).strip()
            title = str(data.get("title", app_id)).strip()

            if not app_id:
                continue

            apps.append({
                "id": app_id,
                "title": title,
                "kind": "local",
                "path": "",
                "command": "",
                "launch_data": data,
            })

        return apps

    def on_text_changed(self, text):
        query = str(text or "").strip()
        self.search_timer.stop()

        if not query:
            self.stop_current_search()
            self.current_results = self.read_history()[:10]
            self.refresh_list()
            return

        self.search_timer.start()

    def stop_current_search(self):
        if self.search_thread is not None:
            try:
                self.search_thread.quit()
                self.search_thread.wait(100)
            except Exception:
                pass

        self.search_thread = None
        self.search_worker = None

    def run_async_search(self):
        query = self.input.text().strip() if self.input is not None else ""

        if not query:
            self.current_results = self.read_history()[:10]
            self.refresh_list()
            return

        self.stop_current_search()

        self.search_id += 1
        current_search_id = self.search_id

        local_apps = self.collect_local_apps()
        history = self.read_history()

        self.search_thread = QThread(self)
        self.search_worker = SearchWorker(current_search_id, query, local_apps, history)
        self.search_worker.moveToThread(self.search_thread)

        self.search_thread.started.connect(self.search_worker.run)
        self.search_worker.finished.connect(self.on_search_finished)
        self.search_worker.finished.connect(self.search_thread.quit)
        self.search_worker.finished.connect(self.search_worker.deleteLater)
        self.search_thread.finished.connect(self.search_thread.deleteLater)

        self.search_thread.start()

    def on_search_finished(self, result_search_id, results):
        if result_search_id != self.search_id:
            return

        if not self.isVisible():
            return

        if self.input is None or self.input.text().strip() == "":
            return

        self.current_results = results
        self.refresh_list()

    def display_text(self, item):
        return str(item.get("title", "")).strip()

    def refresh_list(self):
        self.list_model.setStringList([self.display_text(item) for item in self.current_results])

        if self.current_results:
            self.list_view.setCurrentIndex(self.list_model.index(0, 0))
            self.expand()
        else:
            self.collapse()

    def activate_index(self, index):
        row = index.row()

        if row < 0 or row >= len(self.current_results):
            return

        self.activate_result(self.current_results[row])

    def activate_current_result(self):
        row = self.list_view.currentIndex().row()

        if row < 0 and self.current_results:
            row = 0

        if row < 0 or row >= len(self.current_results):
            return

        self.activate_result(self.current_results[row])

    def activate_result(self, item):
        self.save_to_cache(item)

        kind = item.get("kind", "")

        if kind == "local":
            context = self.get_app_context()
            dock = context.get("dock")
            launch_data = item.get("launch_data")

            if dock is not None and hasattr(dock, "launch_app") and launch_data is not None:
                try:
                    dock.launch_app(launch_data)
                except Exception:
                    pass

            self.reset_compact()
            self.hide()
            return

        path = item.get("path", "")
        command = item.get("command", "")

        try:
            if path and Path(path).exists():
                os.startfile(path)
            elif command:
                subprocess.Popen(command, shell=True)
            elif item.get("title"):
                subprocess.Popen(item.get("title"), shell=True)
        except Exception:
            try:
                subprocess.Popen(f'start "" "{path or command or item.get("title", "")}"', shell=True)
            except Exception:
                pass

        self.reset_compact()
        self.hide()
