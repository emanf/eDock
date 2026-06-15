import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from PySide6.QtCore import Qt, QStringListModel, QEvent, QObject, QThread, Signal, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QListView, QApplication, QAbstractItemView, QSizePolicy

from core.app.app_base import AppBase
from core.paths import get_app_cache_dir
from core.theming.theme_manager import Theme


class SearchWorker(QObject):
    finished = Signal(int, list)

    def __init__(self, search_id, query, local_apps, history):
        super().__init__()
        self.search_id = search_id
        self.query = str(query or "").strip()
        self.local_apps = local_apps if isinstance(local_apps, list) else []
        self.history = history if isinstance(history, list) else []

    def normalize(self, text):
        return str(text or "").strip().lower()

    def words_from_text(self, text):
        text = self.normalize(text)
        for char in ["-", "_", ".", ",", "(", ")", "[", "]", "{", "}", "+", "&", "@", "#"]:
            text = text.replace(char, " ")
        return [word for word in text.split() if word]

    def initials(self, text):
        words = self.words_from_text(text)
        return "".join(word[0] for word in words if word)

    def compact(self, text):
        text = self.normalize(text)
        return "".join(ch for ch in text if ch.isalnum())

    def is_subsequence(self, query, text):
        query = self.compact(query)
        text = self.compact(text)

        if not query or not text:
            return False

        index = 0

        for char in text:
            if index < len(query) and query[index] == char:
                index += 1

        return index == len(query)

    def abbreviation_score(self, query, title):
        query_norm = self.compact(query)
        title_norm = self.compact(title)
        words = self.words_from_text(title)
        initials = self.initials(title)

        if not query_norm:
            return 0

        score = 0

        if initials == query_norm:
            score += 1200
        elif initials.startswith(query_norm):
            score += 900
        elif query_norm in initials:
            score += 650

        if self.is_subsequence(query_norm, initials):
            score += 500

        if self.is_subsequence(query_norm, title_norm):
            score += 260

        if words:
            joined_first_letters = "".join(word[0] for word in words)
            if joined_first_letters.startswith(query_norm):
                score += 700

        return score

    def score(self, query, title, path=""):
        query = self.normalize(query)
        title_norm = self.normalize(title)
        path_norm = self.normalize(path)

        if not query:
            return 0

        score = 0

        if title_norm == query:
            score += 1000
        if title_norm.startswith(query):
            score += 800
        if query in title_norm:
            score += 500

        words = self.words_from_text(title_norm)

        for word in words:
            if word == query:
                score += 350
            elif word.startswith(query):
                score += 250
            elif query in word:
                score += 120

        score += self.abbreviation_score(query, title_norm)

        if path_norm:
            file_stem = self.normalize(Path(path).stem)

            if file_stem == query:
                score += 900
            elif file_stem.startswith(query):
                score += 650
            elif query in file_stem:
                score += 400
            elif query in path_norm:
                score += 80

            score += self.abbreviation_score(query, file_stem)

        return score

    def source_priority(self, item):
        kind = str(item.get("kind", "")).lower().strip()

        if kind == "local":
            return 4
        if kind == "shortcut":
            return 3
        if kind == "executable":
            return 2
        return 1

    def canonical_key(self, item):
        kind = self.normalize(item.get("kind", ""))
        item_id = self.normalize(item.get("id", ""))
        path = self.normalize(item.get("path", ""))
        title = self.normalize(item.get("title", ""))

        if kind == "local" and item_id:
            return f"local:{item_id}"

        if path:
            stem = self.normalize(Path(path).stem)

            if stem in ("notepad", "calc", "mspaint", "cmd", "powershell", "explorer", "regedit", "taskmgr", "control"):
                return f"system:{stem}"

            return f"pathstem:{stem}"

        if item_id:
            return f"id:{item_id}"

        return f"title:{title}"

    def better_item(self, old_item, new_item, old_score, new_score):
        old_priority = self.source_priority(old_item)
        new_priority = self.source_priority(new_item)

        if new_score > old_score:
            return new_item, new_score

        if new_score == old_score and new_priority > old_priority:
            return new_item, new_score

        return old_item, old_score

    def start_menu_dirs(self):
        dirs = []

        program_data = os.environ.get("PROGRAMDATA")
        app_data = os.environ.get("APPDATA")

        if program_data:
            dirs.append(Path(program_data) / "Microsoft" / "Windows" / "Start Menu" / "Programs")

        if app_data:
            dirs.append(Path(app_data) / "Microsoft" / "Windows" / "Start Menu" / "Programs")

        return [x for x in dirs if x.exists()]

    def collect_start_menu_apps(self):
        results = []
        seen = set()

        for root in self.start_menu_dirs():
            try:
                files = []
                files.extend(root.rglob("*.lnk"))
                files.extend(root.rglob("*.url"))
                files.extend(root.rglob("*.appref-ms"))
            except Exception:
                files = []

            for path in files:
                title = path.stem.strip()
                score = self.score(self.query, title, str(path))

                if score <= 0:
                    continue

                key = str(path).lower()

                if key in seen:
                    continue

                seen.add(key)

                results.append({
                    "id": key,
                    "title": title,
                    "kind": "shortcut",
                    "path": str(path),
                    "command": ""
                })

        return results

    def collect_path_executables(self):
        results = []
        seen = set()
        query_norm = self.normalize(self.query)

        direct = shutil.which(query_norm)
        if direct:
            path = Path(direct)
            results.append({
                "id": str(path).lower(),
                "title": path.stem,
                "kind": "executable",
                "path": str(path),
                "command": str(path)
            })
            seen.add(str(path).lower())

        path_env = os.environ.get("PATH", "")

        for folder in path_env.split(os.pathsep):
            if not folder:
                continue

            folder_path = Path(folder)

            if not folder_path.exists() or not folder_path.is_dir():
                continue

            try:
                children = list(folder_path.iterdir())
            except Exception:
                continue

            for file_path in children:
                if not file_path.is_file():
                    continue

                if file_path.suffix.lower() not in (".exe", ".bat", ".cmd", ".ps1"):
                    continue

                score = self.score(self.query, file_path.stem, str(file_path))

                if score <= 0:
                    continue

                key = str(file_path).lower()

                if key in seen:
                    continue

                seen.add(key)

                results.append({
                    "id": key,
                    "title": file_path.stem,
                    "kind": "executable",
                    "path": str(file_path),
                    "command": str(file_path)
                })

        return results

    def collect_common_windows_locations(self):
        results = []
        seen = set()
        windir = os.environ.get("WINDIR", "C:\\Windows")

        folders = [
            Path(windir),
            Path(windir) / "System32",
            Path(windir) / "SysWOW64"
        ]

        for folder in folders:
            if not folder.exists():
                continue

            try:
                children = list(folder.glob("*.exe"))
            except Exception:
                continue

            for file_path in children:
                score = self.score(self.query, file_path.stem, str(file_path))

                if score <= 0:
                    continue

                key = str(file_path).lower()

                if key in seen:
                    continue

                seen.add(key)

                results.append({
                    "id": key,
                    "title": file_path.stem,
                    "kind": "executable",
                    "path": str(file_path),
                    "command": str(file_path)
                })

        return results

    def search_history(self):
        results = []

        for item in self.history:
            if not isinstance(item, dict):
                continue

            score = self.score(self.query, item.get("title", ""), item.get("path", ""))

            if score > 0:
                copy = dict(item)
                copy["_history_score"] = 2000
                results.append(copy)

        return results

    def run(self):
        if not self.query:
            self.finished.emit(self.search_id, self.history)
            return

        pool = []
        pool.extend(self.search_history())
        pool.extend(self.local_apps)
        pool.extend(self.collect_start_menu_apps())
        pool.extend(self.collect_path_executables())
        pool.extend(self.collect_common_windows_locations())

        merged = {}

        for item in pool:
            if not isinstance(item, dict):
                continue

            title = item.get("title", "")
            path = item.get("path", "")
            score = self.score(self.query, title, path) + int(item.get("_history_score", 0))

            if score <= 0:
                continue

            key = self.canonical_key(item)

            if key not in merged:
                merged[key] = (score, item)
            else:
                old_score, old_item = merged[key]
                best_item, best_score = self.better_item(old_item, item, old_score, score)
                merged[key] = (best_score, best_item)

        scored = [(score, item) for score, item in merged.values()]
        scored.sort(key=lambda x: (-x[0], self.normalize(x[1].get("title", ""))))
        self.finished.emit(self.search_id, [item for _, item in scored[:40]])





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
        for name in ("app_context", "context"):
            if hasattr(self.app_ref, name):
                value = getattr(self.app_ref, name)
                if isinstance(value, dict):
                    return value
        return {}

    def get_project_root(self):
        try:
            from core.paths import get_root_dir
            return Path(get_root_dir())
        except Exception:
            return Path(__file__).resolve().parents[2]

    def get_cache_dir(self):
        return get_app_cache_dir("emanf.spotlight")

    def get_history_file(self):
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
        history_file = self.get_history_file()

        try:
            if not history_file.exists():
                return []

            data = json.loads(history_file.read_text(encoding="utf-8"))

            if not isinstance(data, list):
                return []

            clean = []

            for item in data:
                if isinstance(item, dict):
                    clean.append(item)

            clean.sort(key=lambda item: float(item.get("last_opened", 0)), reverse=True)

            return clean
        except Exception as error:
            print("Spotlight history read error:", error)
            return []

    def write_history(self, history):
        history_file = self.get_history_file()

        try:
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
        context = self.get_app_context()
        app_loader = context.get("app_loader")

        if app_loader is not None and hasattr(app_loader, "load_apps"):
            try:
                loaded = app_loader.load_apps()
            except Exception:
                loaded = []

            for app in loaded:
                if not isinstance(app, dict):
                    continue

                app_id = str(app.get("id", "")).strip()
                title = str(app.get("title", app_id)).strip()

                if not app_id:
                    continue

                apps.append({
                    "id": app_id,
                    "title": title,
                    "kind": "local",
                    "path": "",
                    "command": "",
                    "launch_data": app
                })

            return apps

        apps_dir = self.get_project_root() / "apps"

        if not apps_dir.exists():
            return apps

        for folder in apps_dir.iterdir():
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

            apps.append({
                "id": app_id,
                "title": title,
                "kind": "local",
                "path": "",
                "command": "",
                "launch_data": data
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



class App(AppBase):
    def __init__(self, app_context=None, manifest=None, app_dir=None):
        super().__init__(app_context, manifest, app_dir)
        self.window = None

    def on_init(self):
        if self.window is None:
            self.window = SpotlightWindow(self)

    def on_load(self):
        self.on_init()

    def on_click(self):
        self.on_init()
        self.window.toggle()

    def clear_search_history(self):
        history_file = get_app_cache_dir("emanf.spotlight") / "history.json"

        try:
            history_file.parent.mkdir(parents=True, exist_ok=True)
            history_file.write_text("[]", encoding="utf-8")
        except Exception:
            pass

        if self.window is not None:
            self.window.current_results = []
            if self.window.input is not None:
                self.window.input.clear()
            self.window.refresh_list()

    def on_unload(self):
        if self.window is not None:
            self.window.hide()

    def on_theme_changed(self):
        if self.window is not None and hasattr(self.window, '_apply_style'):
            self.window._apply_style()
