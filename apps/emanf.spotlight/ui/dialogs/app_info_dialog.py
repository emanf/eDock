import json
import urllib.request

from PySide6.QtCore import Qt, QTimer, QThread, QObject, Signal, Slot
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
    QProgressBar,
    QFrame,
    QWidget,
    QGridLayout,
    QSizePolicy,
)

from core.theming.theme_manager import Theme
from core.rendering.material_icons import MaterialIcons
from PySide6.QtGui import QFont


class ManifestFetchWorker(QObject):
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self, manifest_url: str, parent=None):
        super().__init__(parent)
        self.manifest_url = str(manifest_url or "").strip()

    @Slot()
    def run(self):
        if not self.manifest_url:
            self.finished.emit({})
            return

        try:
            request = urllib.request.Request(
                self.manifest_url,
                headers={
                    "User-Agent": "eDock-Spotlight/1.0",
                    "Accept": "application/json",
                },
            )

            with urllib.request.urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))

            self.finished.emit(data if isinstance(data, dict) else {})
        except Exception as error:
            self.failed.emit(str(error))
            self.finished.emit({})


class AppInfoDialog(QDialog):
    def __init__(self, app_data: dict, parent=None):
        super().__init__(parent)

        self.app_data = dict(app_data or {})
        self.manifest_data = {}
        self.fetch_thread = None
        self.fetch_worker = None

        MaterialIcons.ensure_font()

        self.setWindowTitle("App Information")
        self.setModal(True)
        self.setMinimumWidth(560)
        self.setMinimumHeight(440)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._build_ui()

        self._drag_pos = None
        self._dragging = False
        self._apply_style()

        manifest_url = self._get_manifest_url()
        if manifest_url:
            self.set_loading(True)
            QTimer.singleShot(0, self._start_fetch)

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(0)

        self.container = QFrame(self)
        self.container.setObjectName("container")
        root_layout.addWidget(self.container)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(14)

        hero = QWidget()
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(0, 0, 0, 0)
        hero_layout.setSpacing(12)

        icon_text = str(self.app_data.get("icon", "m:apps"))
        icon_display = ""
        if isinstance(icon_text, str) and icon_text.startswith("m:"):
            icon_name = icon_text[2:].strip()
            icon_display = MaterialIcons.get(icon_name, MaterialIcons.get("apps", ""))
        else:
            icon_display = icon_text

        self.icon_label = QLabel(icon_display)
        self.icon_label.setObjectName("appIcon")
        self.icon_label.setFixedSize(68, 68)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setFont(QFont(MaterialIcons.font_family(), 34))

        title_area = QWidget()
        title_layout = QVBoxLayout(title_area)
        title_layout.setContentsMargins(0, 2, 0, 0)
        title_layout.setSpacing(6)

        self.title_label = QLabel(self._get_display_title())
        self.title_label.setObjectName("appTitle")
        self.title_label.setWordWrap(True)

        self.description_label = QLabel(
            str(self.app_data.get("subtitle") or self.app_data.get("description") or "")
        )
        self.description_label.setObjectName("appDescription")
        self.description_label.setWordWrap(True)

        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.description_label)

        self.close_button = QPushButton(MaterialIcons.get("close"))
        self.close_button.setObjectName("closeButton")
        self.close_button.setFixedSize(24, 24)
        self.close_button.setFont(QFont(MaterialIcons.font_family(), 14))
        self.close_button.clicked.connect(self.reject)

        hero_layout.addWidget(self.icon_label)
        hero_layout.addWidget(title_area, 1)
        hero_layout.addWidget(self.close_button, 0, Qt.AlignTop)

        layout.addWidget(hero)

        divider = QFrame(self)
        divider.setObjectName("divider")
        divider.setFixedHeight(1)
        layout.addWidget(divider)

        self.progress = QProgressBar(self)
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.info_widget = QWidget(self)
        self.info_grid = QGridLayout(self.info_widget)
        self.info_grid.setContentsMargins(0, 0, 0, 0)
        self.info_grid.setHorizontalSpacing(16)
        self.info_grid.setVerticalSpacing(11)

        try:
            self.info_grid.setColumnStretch(0, 0)
            self.info_grid.setColumnStretch(1, 1)
        except Exception:
            pass

        self.info_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        self.info_widget.setMinimumHeight(300)

        try:
            self.info_widget.setLayout(self.info_grid)
        except Exception:
            pass
        layout.addWidget(self.info_widget)

        self._populate_info_grid(self._get_merged_data())

        layout.addStretch(1)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        buttons_layout.addStretch(1)

        self.close_info_button = QPushButton("Close", self)
        self.close_info_button.clicked.connect(self.reject)
        self.close_info_button.setObjectName("closeInfoButton")

        self.action_button = QPushButton("Install", self)
        self.action_button.setObjectName("actionButton")
        self.action_button.clicked.connect(self.accept)

        try:
            self.action_button.setEnabled(True)
            self.action_button.raise_()
        except Exception:
            pass

        buttons_layout.addWidget(self.close_info_button)
        buttons_layout.addWidget(self.action_button)

        layout.addLayout(buttons_layout)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            self._dragging = True
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging and event.buttons() & Qt.LeftButton:
            try:
                new_pos = event.globalPosition().toPoint() - self._drag_pos
                self.move(new_pos)
            except Exception:
                pass
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False
            self._drag_pos = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def _apply_style(self):

        uic = Theme.to_ui_color
        close_button = Theme.get_button(Theme.BUTTON_CLOSE)
        icon_theme = Theme.get_icon(Theme.ICON_NORMAL)
        title_text = Theme.get_text(Theme.TEXT_TITLE)
        normal_text = Theme.get_text(Theme.TEXT_NORMAL)
        muted_text = Theme.get_text(Theme.TEXT_MUTED)
        dialog_theme = Theme.get_dialog()
        input_theme = Theme.get_input()
        colors = Theme.get_colors()

        container_background = uic(dialog_theme.get("background_color"))
        container_border = uic(dialog_theme.get("border_color"))
        container_border_width = dialog_theme.get("border_width")
        container_border_radius = dialog_theme.get("border_radius")
        icon_background = uic(colors.get(Theme.Colors.PANEL))
        icon_border = uic(input_theme.get("border_color"))
        icon_border_width = input_theme.get("border_width")
        icon_border_radius = input_theme.get("border_radius")
        icon_color = uic(icon_theme.get("color"))
        title_color = uic(title_text.get("color"))
        description_color = uic(muted_text.get("color"))
        divider_color = uic(dialog_theme.get("border_color"))
        field_label_color = uic(muted_text.get("color"))
        field_value_color = uic(normal_text.get("color"))
        close_background = uic(close_button.get("background_color"))
        close_hover = uic(close_button.get("hover_color"))
        close_pressed = uic(close_button.get("pressed_color"))
        close_border = uic(close_button.get("border_color"))
        close_text = uic(close_button.get("text_color"))
        close_border_width = close_button.get("border_width")
        close_border_radius = close_button.get("border_radius")

        def _safe(val, fallback):
            return val if val else fallback

        container_background = _safe(container_background, "#2b2b2b")
        container_border = _safe(container_border, "#3c3c3c")
        title_color = _safe(title_color, "#ffffff")
        description_color = _safe(description_color, "#bfbfbf")
        icon_background = _safe(icon_background, "#3a3a3a")
        icon_color = _safe(icon_color, "#ffffff")
        divider_color = _safe(divider_color, "#444444")
        field_label_color = _safe(field_label_color, "#9e9e9e")
        field_value_color = _safe(field_value_color, "#dddddd")
        close_background = _safe(close_background, "transparent")
        close_text = _safe(close_text, "#ffffff")
        close_border = _safe(close_border, "transparent")
        close_hover = _safe(close_hover, "#444444")
        close_pressed = _safe(close_pressed, "#333333")

        self.setStyleSheet(f"""
            QDialog {{
                background: transparent;
            }}

            QFrame#container {{
                background-color: {container_background};
                border: {container_border_width}px solid {container_border};
                border-radius: {container_border_radius}px;
            }}

            QPushButton#closeButton {{
                background-color: {close_background};
                color: {close_text};
                border: {close_border_width}px solid {close_border};
                border-radius: {close_border_radius}px;
                padding: 0;
            }}

            QPushButton#closeButton:hover {{
                background-color: {close_hover};
            }}

            QPushButton#closeButton:pressed {{
                background-color: {close_pressed};
            }}

            QLabel#appIcon {{
                background-color: {icon_background};
                color: {icon_color};
                border: {icon_border_width}px solid {icon_border};
                border-radius: {icon_border_radius}px;
            }}

            QLabel#appTitle {{
                color: {title_color};
                font-size: 22px;
                font-weight: 700;
            }}

            QLabel#appDescription {{
                color: {description_color};
                font-size: 13px;
                line-height: 18px;
            }}

            QFrame#divider {{
                background-color: {divider_color};
                border: none;
            }}

            QLabel#fieldLabel {{
                color: {field_label_color};
                font-size: 12px;
                font-weight: 600;
                min-width: 92px;
                padding-top: 4px;
                padding-bottom: 4px;
            }}

            QLabel#fieldValue {{
                color: {field_value_color};
                font-size: 13px;
                padding-top: 4px;
                padding-bottom: 4px;
            }}

            QPushButton#closeInfoButton {{
                background-color: transparent;
                color: {field_value_color};
                border: 1px solid {container_border};
                padding: 6px 12px;
                border-radius: 8px;
                min-height: 32px;
                font-size: 13px;
            }}

            QPushButton#actionButton {{
                background-color: {_safe(uic(Theme.get_button(Theme.BUTTON_NORMAL).get("background_color")), "#2d89ff")};
                color: white;
                border: none;
                padding: 8px 14px;
                border-radius: 8px;
                min-height: 36px;
                font-size: 13px;
            }}
        """)

    def _get_display_title(self) -> str:
        return str(
            self.app_data.get("title")
            or self.app_data.get("name")
            or self.app_data.get("id")
            or "Application"
        ).strip()

    def _get_manifest_url(self) -> str:
        return str(
            self.app_data.get("manifest_url")
            or self.app_data.get("manifest")
            or self.app_data.get("app_manifest")
            or ""
        ).strip()

    def set_loading(self, loading: bool):
        self.progress.setVisible(bool(loading))
        try:
            self.action_button.setEnabled(not bool(loading))
        except Exception:
            pass

    def _start_fetch(self):
        manifest_url = self._get_manifest_url()
        if not manifest_url:
            self.set_loading(False)
            return

        self.fetch_thread = QThread(self)
        self.fetch_worker = ManifestFetchWorker(manifest_url)
        self.fetch_worker.moveToThread(self.fetch_thread)

        self.fetch_thread.started.connect(self.fetch_worker.run)
        self.fetch_worker.finished.connect(self._on_manifest_loaded)
        self.fetch_worker.finished.connect(self.fetch_thread.quit)
        self.fetch_worker.failed.connect(self._on_manifest_failed)
        self.fetch_worker.finished.connect(self.fetch_worker.deleteLater)
        self.fetch_thread.finished.connect(self.fetch_thread.deleteLater)

        self.fetch_thread.start()

    def _on_manifest_failed(self, message: str):
        if message:
            print(f"Manifest fetch error: {message}")

    def _on_manifest_loaded(self, data: dict):
        self.manifest_data = data if isinstance(data, dict) else {}
        merged = self._get_merged_data()

        self.title_label.setText(self._get_display_title())
        self.description_label.setText(
            str(merged.get("description") or merged.get("subtitle") or "")
        )

        try:
            self._populate_info_grid(merged)
        except Exception:
            text = self._build_info_text(merged)
            txt = QTextEdit(self.info_widget)
            txt.setReadOnly(True)
            txt.setText(text)

            while self.info_grid.count():
                item = self.info_grid.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self.info_grid.addWidget(txt, 0, 0, 1, 2)
            try:
                self.info_grid.setColumnStretch(0, 0)
                self.info_grid.setColumnStretch(1, 1)
            except Exception:
                pass

        try:
            self.action_button.setEnabled(True)
        except Exception:
            pass
        self.set_loading(False)

        try:
            meta = merged.get("metadata", {}) or {}
            online_v = meta.get("online_version") or merged.get("version")
            local_v = meta.get("local_version")
            action_label = "Install"
            if online_v and local_v:
                try:
                    from packaging.version import Version

                    if Version(str(online_v)) > Version(str(local_v)):
                        action_label = "Update"
                except Exception:
                    if str(online_v) != str(local_v):
                        action_label = "Update"

            self.action_button.setText(action_label)
        except Exception:
            pass

    def _get_merged_data(self) -> dict:
        merged = {}
        merged.update(self.app_data)
        merged.update(self.manifest_data)
        return merged

    def _build_info_text(self, data: dict) -> str:
        keys = [
            "id",
            "app_id",
            "title",
            "version",
            "author",
            "description",
            "category",
            "keywords",
            "homepage",
            "size",
            "minDockVersion",
            "sha256",
        ]

        lines = []
        for key in keys:
            value = data.get(key)
            if value is None or value == "":
                continue

            if isinstance(value, (list, tuple)):
                value = ", ".join(str(v) for v in value)
            elif isinstance(value, dict):
                value = json.dumps(value, indent=2, ensure_ascii=False)

            formatted_key = key.replace("_", " ").title()
            lines.append(f"{formatted_key}: {value}")

        if not lines:
            return json.dumps(data, indent=2, ensure_ascii=False)

        return "\n".join(lines)

    def _populate_info_grid(self, data: dict):

        while self.info_grid.count():
            item = self.info_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        rows = []

        display_keys = [
            ("id", "App ID"),
            ("version", "Version"),
            ("last_modified", "Last Modified"),
            ("author", "Author"),
            ("author_email", "Author Email"),
            ("author_website", "Author Website"),
            ("homepage", "Website"),
            ("category", "Category"),
            ("keywords", "Keywords"),
            ("size", "Size"),
            ("minDockVersion", "Min Dock Version"),
            ("sha256", "SHA256"),
        ]

        for key, label in display_keys:
            v = data.get(key)
            if not v and key == "id":
                v = data.get("app_id")
            if v is None or v == "":
                continue

            if isinstance(v, (list, tuple)):
                v = ", ".join(str(x) for x in v)
            elif isinstance(v, dict):
                v = json.dumps(v, ensure_ascii=False)
            rows.append((label, str(v)))

        for row_index, item in enumerate(rows):
            lbl = QLabel(item[0])
            lbl.setObjectName("fieldLabel")
            lbl.setAlignment(Qt.AlignRight | Qt.AlignTop)

            try:
                lbl.setMinimumHeight(22)
            except Exception:
                pass
            val = QLabel(item[1])
            val.setObjectName("fieldValue")
            val.setWordWrap(True)
            val.setTextInteractionFlags(Qt.TextSelectableByMouse)
            try:
                val.setMinimumHeight(22)
            except Exception:
                pass
            self.info_grid.addWidget(lbl, row_index, 0)
            self.info_grid.addWidget(val, row_index, 1)
