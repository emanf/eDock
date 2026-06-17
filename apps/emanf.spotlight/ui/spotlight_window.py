import json
import time
from pathlib import Path

from PySide6.QtCore import (
    Qt,
    QTimer,
    QEvent,
)
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QListView,
    QApplication,
    QAbstractItemView,
    QSizePolicy,
)

from ..models import SearchResult
from ..core.constants import (
    QUERY_MODE_APPS,
    SEARCH_DEBOUNCE_MS,
    WINDOW_BASE_WIDTH,
    WINDOW_BASE_HEIGHT,
    INPUT_HEIGHT,
    RESULT_ROW_HEIGHT,
    FOCUS_HIDE_CLICK_BLOCK_SECONDS,
)

from core.theming.theme_manager import Theme

from ..core.query_parser import QueryParser
from .search_input import SearchInput
from .results_list import ResultsListModel, ResultItemDelegate


class SpotlightWindow(QWidget):
    def __init__(self, app_ref, controller=None):
        super().__init__(None)

        self.app_ref = app_ref
        self.controller = controller

        self.current_results = []
        self.global_filter_installed = False
        self.last_focus_hide_time = 0.0
        self.search_in_progress = False

        self.base_width = WINDOW_BASE_WIDTH
        self.base_height = WINDOW_BASE_HEIGHT
        self.input_height = INPUT_HEIGHT
        self.result_row_height = RESULT_ROW_HEIGHT

        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(SEARCH_DEBOUNCE_MS)
        self.search_timer.timeout.connect(self._on_search_timeout)

        self.close_focus_timer = QTimer(self)
        self.close_focus_timer.setSingleShot(True)
        self.close_focus_timer.setInterval(80)
        self.close_focus_timer.timeout.connect(self._close_if_unfocused)

        self.setObjectName("spotlightWindow")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFixedSize(self.base_width, self.base_height)

        self._build_ui()
        self._apply_style()

        app = QApplication.instance()
        if app is not None and not self.global_filter_installed:
            app.installEventFilter(self)
            self.global_filter_installed = True

        self.center_top()

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

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(16, 12, 16, 12)
        container_layout.setSpacing(8)
        container_layout.setAlignment(Qt.AlignTop)

        self.input = SearchInput(self.container)
        self.input.setFixedHeight(self.input_height)
        self.input.query_changed.connect(self._on_query_changed)
        self.input.query_submitted.connect(self._on_query_submitted)
        self.input.installEventFilter(self)
        container_layout.addWidget(self.input)

        self.list_view = QListView(self.container)
        self.list_view.setObjectName("searchListView")
        self.list_view.setFrameShape(QListView.NoFrame)
        self.list_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.list_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.list_view.setContentsMargins(0, 4, 0, 0)
        try:
            self.list_view.setViewportMargins(0, 4, 0, 0)
        except Exception:
            pass
        self.list_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.list_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_view.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.list_view.setUniformItemSizes(True)
        self.list_view.setSpacing(0)
        self.list_view.setMouseTracking(True)

        self.list_view.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.list_view.installEventFilter(self)
        self.list_view.clicked.connect(self._on_result_selected)

        self.list_model = ResultsListModel(self)
        self.list_view.setModel(self.list_model)

        self.result_delegate = ResultItemDelegate(self.list_view)
        self.result_delegate.row_height = self.result_row_height
        self.list_model.row_height = self.result_row_height
        self.list_view.setItemDelegate(self.result_delegate)

        self.list_view.viewport().installEventFilter(self)
        self.list_view.hide()
        self.list_view.setFixedHeight(0)

        container_layout.addWidget(self.list_view)

        self.layout.addWidget(self.container)

    def _apply_style(self):
        uic = Theme.to_ui_color
        colors = Theme.get_colors()

        bg = uic(colors.get(Theme.Colors.BACKGROUND))
        border = uic(colors.get(Theme.Colors.BORDER))
        text = uic(colors.get(Theme.Colors.TEXT))
        hover_bg = uic(colors.get(Theme.Colors.SURFACE_HOVER))
        selected_bg = uic(colors.get(Theme.Colors.SURFACE_PRESSED))
        scrollbar_color = uic(colors.get(Theme.Colors.BORDER))

        stylesheet = f"""
            QWidget#spotlightContainer {{
                background: {bg};
                border: 1px solid {border};
                border-radius: 18px;
            }}
            
            QLineEdit#searchInput {{
                background: transparent;
                border: none;
                color: {text};
                font-size: 19px;
                padding: 0px 4px;
                selection-background-color: {selected_bg};
            }}
            
            QListView#searchListView {{
                background: transparent;
                border: none;
                color: {text};
                outline: none;
                padding: 0px;
                font-size: 14px;
            }}
            
            QListView#searchListView::item {{
                background: transparent;
                border: none;
                border-radius: 10px;
                padding: 6px 12px;
                margin: 0px;
            }}
            
            QListView#searchListView::item:selected {{
                background: {selected_bg};
                color: white;
            }}
            
            QListView#searchListView::item:hover {{
                background: {hover_bg};
            }}
            
            QScrollBar:vertical {{
                background: rgba(0,0,0,0.04);
                width: 10px;
                margin: 4px 0px 4px 0px;
                border: none;
                border-radius: 6px;
            }}
            
            QScrollBar::handle:vertical {{
                background: {scrollbar_color};
                border-radius: 6px;
                min-height: 28px;
                margin: 2px 2px 2px 2px;
            }}

            QScrollBar::sub-line:vertical, QScrollBar::add-line:vertical {{
                height: 0px;
                background: transparent;
                border: none;
            }}

            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
            
            QScrollBar::handle:vertical:hover {{
                background: {hover_bg};
            }}
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
                background: transparent;
            }}

            QListView#searchListView::item:selected:hover {{
                background: {selected_bg};
                color: white;
            }}

            QListView#searchListView::item:hover {{
                background: {hover_bg};
            }}
        """

        self.setStyleSheet(stylesheet)

    def _on_query_changed(self, text: str):

        self.search_timer.stop()
        self.search_timer.start()

    def _on_search_timeout(self):
        if self.controller:
            query = self.input.get_query()
            mode, cleaned_query = QueryParser.parse(query)
            self.controller.search(cleaned_query, mode)

    def _on_query_submitted(self, query: str):

        if self.list_model.rowCount() > 0:
            index = self.list_model.index(0)
            self.list_view.setCurrentIndex(index)
            self._on_result_selected(index)

    def _on_result_selected(self, index):
        if not index.isValid():
            return

        result_dict = index.data(ResultsListModel.ItemRole)
        if result_dict:
            try:
                mode, _ = QueryParser.parse(self.input.get_query())
                if mode != QUERY_MODE_APPS:
                    self.save_to_cache(result_dict)
            except Exception:
                pass

            try:
                self.hide()
            except Exception:
                pass

            if self.controller:
                self.controller.handle_result_action(result_dict)

            self.clear()

    def update_results(self, results: list):
        self.current_results = results

        result_dicts = []
        for result in results:
            if isinstance(result, SearchResult):
                result_dicts.append(result.to_dict())
            else:
                result_dicts.append(result)

        self.list_model.set_results(result_dicts)

        self._update_window_size()

    def _update_window_size(self):
        result_count = len(self.current_results)
        new_height = self.base_height

        if result_count > 0:
            display_rows = min(result_count, 10)
            list_height = display_rows * self.result_row_height
            new_height = self.base_height + list_height + 8

        self.setFixedHeight(new_height)
        if result_count > 0:
            self.list_view.show()
            try:
                self.list_view.raise_()
            except Exception:
                pass
            viewport_height = list_height + 8
            self.list_view.setFixedHeight(viewport_height)
            self.list_view.setMinimumHeight(viewport_height)
            self.list_view.setMaximumHeight(viewport_height)
        else:
            self.list_view.hide()
            self.list_view.setFixedHeight(0)

    def toggle(self):
        if self.consume_recent_focus_hide():
            return

        if self.isVisible():
            self.hide()
        else:
            try:
                self.close_focus_timer.stop()
            except Exception:
                pass

            try:
                self.current_results = self.read_history()[:10]
            except Exception:
                self.current_results = []

            self.refresh_list()

            self.show()
            self.focus_search_input()

    def consume_recent_focus_hide(self):
        if not self.last_focus_hide_time:
            return False

        elapsed = time.monotonic() - self.last_focus_hide_time

        if elapsed <= FOCUS_HIDE_CLICK_BLOCK_SECONDS:
            self.last_focus_hide_time = 0.0
            return True

        return False

    def clear(self):
        self.input.clear()
        self.list_model.set_results([])
        self._update_window_size()

    def make_json_safe(self, value):
        if value is None:
            return None

        if isinstance(value, (str, int, float, bool)):
            return value

        if isinstance(value, dict):
            safe = {}
            for key, item in value.items():
                if isinstance(key, (str, int, float, bool)):
                    safe_value = self.make_json_safe(item)
                    if safe_value is not None:
                        safe[str(key)] = safe_value
            return safe

        if isinstance(value, (list, tuple)):
            safe_list = []
            for item in value:
                safe_value = self.make_json_safe(item)
                if safe_value is not None:
                    safe_list.append(safe_value)
            return safe_list

        return str(value)

    def normalize_history_item(self, item):
        if not isinstance(item, dict):
            return None

        normalized = {}

        allowed_keys = [
            "id",
            "title",
            "subtitle",
            "path",
            "kind",
            "type",
            "app_id",
            "action",
            "icon",
            "command",
            "launch_data",
        ]

        for key in allowed_keys:
            if key not in item:
                continue

            value = self.make_json_safe(item.get(key))

            if value is None:
                continue

            normalized[key] = value

        kind = str(normalized.get("kind", "")).lower().strip()

        if kind == "local":
            if not normalized.get("app_id") and normalized.get("id"):
                normalized["app_id"] = normalized["id"]

            if not normalized.get("id") and normalized.get("app_id"):
                normalized["id"] = normalized["app_id"]

        if (
            not normalized.get("title")
            and not normalized.get("path")
            and not normalized.get("id")
            and not normalized.get("app_id")
        ):
            return None

        normalized.pop("score", None)
        normalized.pop("_history_score", None)
        normalized.pop("_spotlight_status", None)
        normalized.pop("_spotlight_actionable", None)
        normalized["last_opened"] = time.time()

        return normalized

    def history_item_key(self, item):
        kind = str(item.get("kind", "")).lower().strip()
        item_type = str(item.get("type", "")).lower().strip()
        app_id = str(item.get("app_id") or item.get("id") or "").lower().strip()
        item_id = str(item.get("id", "")).lower().strip()
        path = str(item.get("path", "")).lower().strip()
        title = str(item.get("title", "")).lower().strip()
        action = str(item.get("action", "")).lower().strip()

        if app_id and (kind == "local" or bool(item.get("is_online"))):
            return f"app:{app_id}"

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
        try:
            data = (
                self.app_ref.read_json_cache("history.json", default=[])
                if hasattr(self.app_ref, "read_json_cache")
                else []
            )
        except Exception:
            data = []

        if not isinstance(data, list):
            return []

        clean = []
        seen = set()

        for item in data:
            normalized = self.normalize_history_item(item)

            if normalized is None:
                continue

            key = self.history_item_key(normalized)

            if key in seen:
                continue

            seen.add(key)
            clean.append(normalized)

        clean.sort(key=lambda item: float(item.get("last_opened", 0)), reverse=True)
        return clean

    def write_history(self, history):
        try:
            if hasattr(self.app_ref, "write_json_cache"):
                self.app_ref.write_json_cache("history.json", history[:50])
            else:
                history_file = (
                    Path(__file__).resolve().parents[3] / "user" / "history.json"
                )
                history_file.parent.mkdir(parents=True, exist_ok=True)
                history_file.write_text(
                    json.dumps(history[:50], indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
        except Exception:
            pass

    def save_to_cache(self, item):
        clean_item = self.normalize_history_item(item)

        if not clean_item:
            return

        clean_key = self.history_item_key(clean_item)
        history = self.read_history()
        new_history = [clean_item]

        for old_item in history:
            old_clean = self.normalize_history_item(old_item)

            if old_clean is None:
                continue

            if self.history_item_key(old_clean) == clean_key:
                continue

            new_history.append(old_clean)

        self.write_history(new_history)

    def refresh_list(self):
        result_dicts = []
        for result in self.current_results:
            if isinstance(result, SearchResult):
                result_dicts.append(result.to_dict())
            elif isinstance(result, dict):
                result_dicts.append(result)
            else:
                result_dicts.append({"title": str(result)})

        for rd in result_dicts:
            try:
                if isinstance(rd, dict) and rd.get("last_opened") is not None:
                    rd["_from_history"] = True
            except Exception:
                pass

        self.list_model.set_results(result_dicts)
        self._update_window_size()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            key = event.key()

            if key == Qt.Key_Escape:
                if self.isVisible():
                    self.hide()
                    return True

            if obj is self.input or obj is self.list_view:
                if key == Qt.Key_Down:
                    if self.list_view.isVisible():
                        current = self.list_view.currentIndex()
                        if not current.isValid():
                            self.list_view.setCurrentIndex(self.list_model.index(0))
                        else:
                            next_row = current.row() + 1
                            if next_row < self.list_model.rowCount():
                                self.list_view.setCurrentIndex(
                                    self.list_model.index(next_row)
                                )
                        return True

                elif key == Qt.Key_Up:
                    if self.list_view.isVisible():
                        current = self.list_view.currentIndex()
                        if current.isValid():
                            prev_row = current.row() - 1
                            if prev_row >= 0:
                                self.list_view.setCurrentIndex(
                                    self.list_model.index(prev_row)
                                )
                            else:
                                self.input.setFocus()
                        return True

                elif key == Qt.Key_Return and self.list_view.currentIndex().isValid():
                    self._on_result_selected(self.list_view.currentIndex())
                    return True

        elif event.type() in (QEvent.FocusOut, QEvent.WindowDeactivate):
            if self.is_child_widget(obj) or obj is self:
                self.close_focus_timer.start()

        return super().eventFilter(obj, event)

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

    def _close_if_unfocused(self):

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

    def apply_theme_change(self):
        self._apply_style()

    def focus_search_input(self):
        try:
            self.raise_()
            self.activateWindow()
            self.input.setFocus(Qt.ActiveWindowFocusReason)
            self.input.selectAll()
        except Exception:
            try:
                self.input.setFocus()
                self.input.selectAll()
            except Exception:
                pass

    def center_top(self):
        screen = QApplication.primaryScreen()

        if not screen:
            return

        avail = screen.availableGeometry()
        desired_y = avail.top() + int(avail.height() * 0.25)

        input_local_y = self.input.y()
        window_target_y = max(avail.top(), desired_y - input_local_y)

        new_x = max(avail.left(), avail.left() + (avail.width() - self.width()) // 2)
        self.move(new_x, window_target_y)
