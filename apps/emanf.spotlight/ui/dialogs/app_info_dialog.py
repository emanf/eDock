import json
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
    QFrame,
    QWidget,
    QGridLayout,
    QSizePolicy,
)

from core.theming.theme_manager import Theme
from core.rendering.material_icons import MaterialIcons
from PySide6.QtGui import QFont


class AppInfoDialog(QDialog):
    def __init__(self, app_data: dict, parent=None):
        super().__init__(parent)

        self.app_data = dict(app_data or {})
        self.manifest_data = {}

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

        try:
            self._update_action_button(self._get_merged_data())
        except Exception:
            pass
        self._saved_description = None

        manifest_url = self._get_manifest_url()
        if manifest_url:
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
        try:
            self._update_action_button(self._get_merged_data())
        except Exception:
            pass

        layout.addStretch(1)
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        buttons_layout.addStretch(1)

        self.close_info_button = QPushButton("Close", self)
        self.close_info_button.setObjectName("actionButton")
        self.close_info_button.clicked.connect(self.reject)

        self.action_button = QPushButton("Install", self)
        self.action_button.setObjectName("actionButton")
        self.action_button.clicked.connect(self._on_action_clicked)

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
        normal_button = Theme.get_button(Theme.BUTTON_NORMAL)
        close_button = Theme.get_button(Theme.BUTTON_CLOSE)
        icon_theme = Theme.get_icon(Theme.ICON_NORMAL)
        title_text = Theme.get_text(Theme.TEXT_TITLE)
        normal_text = Theme.get_text(Theme.TEXT_NORMAL)
        muted_text = Theme.get_text(Theme.TEXT_MUTED)
        dialog_theme = Theme.get_dialog()
        input_theme = Theme.get_input()
        colors = Theme.get_colors()

        container_background = uic(
            dialog_theme.get(Theme.Components.Dialog.BACKGROUND_COLOR)
        )
        container_border = uic(dialog_theme.get(Theme.Components.Dialog.BORDER_COLOR))
        container_border_width = dialog_theme.get(Theme.Components.Dialog.BORDER_WIDTH)
        container_border_radius = dialog_theme.get(
            Theme.Components.Dialog.BORDER_RADIUS
        )
        icon_background = uic(colors.get(Theme.Colors.PANEL))
        icon_border = uic(input_theme.get(Theme.Components.Input.BORDER_COLOR))
        icon_border_width = input_theme.get(Theme.Components.Input.BORDER_WIDTH)
        icon_border_radius = input_theme.get(Theme.Components.Input.BORDER_RADIUS)
        icon_color = uic(icon_theme.get(Theme.Components.Icon.COLOR))
        title_color = uic(title_text.get(Theme.Components.Text.COLOR))
        description_color = uic(muted_text.get(Theme.Components.Text.COLOR))
        divider_color = uic(dialog_theme.get(Theme.Components.Dialog.BORDER_COLOR))
        field_label_color = uic(muted_text.get(Theme.Components.Text.COLOR))
        field_value_color = uic(normal_text.get(Theme.Components.Text.COLOR))
        close_background = uic(
            close_button.get(Theme.Components.Button.BACKGROUND_COLOR)
        )
        close_hover = uic(close_button.get(Theme.Components.Button.HOVER_COLOR))
        close_pressed = uic(close_button.get(Theme.Components.Button.PRESSED_COLOR))
        close_border = uic(close_button.get(Theme.Components.Button.BORDER_COLOR))
        close_text = uic(close_button.get(Theme.Components.Button.TEXT_COLOR))
        close_border_width = close_button.get(Theme.Components.Button.BORDER_WIDTH)
        close_border_radius = close_button.get(Theme.Components.Button.BORDER_RADIUS)
        normal_button_background = uic(
            normal_button.get(Theme.Components.Button.BACKGROUND_COLOR)
        )
        normal_button_hover = uic(
            normal_button.get(Theme.Components.Button.HOVER_COLOR)
        )
        normal_button_pressed = uic(
            normal_button.get(Theme.Components.Button.PRESSED_COLOR)
        )
        normal_button_border = uic(
            normal_button.get(Theme.Components.Button.BORDER_COLOR)
        )
        normal_button_text = uic(normal_button.get(Theme.Components.Button.TEXT_COLOR))

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

            QPushButton#closeInfoButton:hover {{
                background-color: {close_hover};
            }}

            QPushButton#closeInfoButton:pressed {{
                background-color: {close_pressed};
            }}

            QPushButton#actionButton {{
                background-color: {normal_button_background};
                color: {normal_button_text};
                border: 1px solid {normal_button_border};
                padding: 8px;
                border-radius: 8px;
                font-size: 13px;
            }}

            QPushButton#actionButton:hover {{
                background-color: {normal_button_hover};
            }}

            QPushButton#actionButton:pressed {{
                background-color: {normal_button_pressed};
            }}

            QPushButton#actionButton:disabled {{
                background-color: transparent;
                color: {field_label_color};
                border: 1px solid {container_border};
            }}

            QCheckBox#enabledCheck {{
                color: {field_value_color};
                font-size: 13px;
            }}

            /* reserve stable indicator space and spacing so text doesn't shift */
            QCheckBox#enabledCheck::indicator {{
                width: 16px;
                height: 16px;
                margin-right: 0px;
                border: 1px solid {container_border};
                border-radius: 3px;
                background: transparent;
            }}

            QCheckBox#enabledCheck::indicator:checked {{
                background: {_safe(uic(Theme.get_button(Theme.BUTTON_POSITIVE).get("background_color")), "#2fa84f")};
                border: 1px solid {_safe(uic(Theme.get_button(Theme.BUTTON_POSITIVE).get("background_color")), "#2fa84f")};
            }}

            QCheckBox#enabledCheck:disabled {{
                color: {field_label_color};
            }}

            QCheckBox#enabledCheck:disabled::indicator {{
                border-color: {container_border};
                background: transparent;
                opacity: 0.7;
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

    def _start_fetch(self):
        manifest_url = self._get_manifest_url()
        if not manifest_url:
            return

        try:
            self._network = QNetworkAccessManager(self)
            req = QNetworkRequest()
            req.setUrl(QUrl(str(manifest_url)))
            req.setRawHeader(b"User-Agent", b"eDock-Spotlight/0.1")
            req.setRawHeader(b"Accept", b"application/json")
            reply = self._network.get(req)

            def _on_finished(rply):
                try:
                    try:
                        url = rply.url().toString()
                    except Exception:
                        url = str(manifest_url)
                    try:
                        code = rply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
                    except Exception:
                        code = None
                    err_code = rply.error()
                    err_str = rply.errorString() if hasattr(rply, "errorString") else ""

                    err_num = None
                    err_name = None
                    try:
                        err_num = int(err_code)
                    except Exception:
                        try:
                            err_name = getattr(err_code, "name", None) or str(err_code)
                        except Exception:
                            err_name = str(err_code)

                    is_error = False
                    if err_num is not None:
                        if err_num != 0:
                            is_error = True
                    else:
                        if err_name and "NoError" not in err_name:
                            is_error = True

                    if is_error:
                        err_code_repr = err_num if err_num is not None else err_name
                        msg = f"Network error {err_code_repr}: {err_str} | url={url} | http_status={code}"
                        self._on_manifest_failed(msg)
                        self._on_manifest_loaded({})
                        return

                    data = rply.readAll().data()
                    try:
                        parsed = json.loads(data.decode("utf-8")) if data else {}
                    except Exception:
                        parsed = {}
                    self._on_manifest_loaded(parsed if isinstance(parsed, dict) else {})
                except Exception as e:
                    msg = f"Exception handling network reply: {e} | url={manifest_url}"
                    self._on_manifest_failed(msg)
                    self._on_manifest_loaded({})

            reply.finished.connect(lambda: _on_finished(reply))
        except Exception:
            QTimer.singleShot(0, lambda: self._on_manifest_loaded({}))

    def closeEvent(self, event):
        try:
            super().closeEvent(event)
        except Exception:
            event.accept()

    def _on_action_clicked(self):
        try:
            if not getattr(self, "action_button", None):
                return
            if not self.action_button.isEnabled():
                return
            self.accept()
        except Exception:
            return

    def _on_manifest_failed(self, message: str):
        if message:
            pass
        try:
            try:
                self.description_label.setText(f"Manifest fetch error: {message}")
            except Exception:
                pass
        except Exception:
            pass

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

        try:
            self._update_action_button(merged)
        except Exception:
            pass

        try:
            try:
                if not self.manifest_data:
                    self.description_label.setText("Manifest loaded (no manifest data)")
            except Exception:
                pass
        except Exception:
            pass

    def _get_merged_data(self) -> dict:
        merged = {}
        merged.update(self.app_data)
        merged.update(self.manifest_data)
        return merged

    def _update_action_button(self, merged: dict):
        try:
            meta = merged.get("metadata", {}) or {}
            online_v = meta.get("online_version") or merged.get("version")
            local_v = meta.get("local_version")
            action_label = "Install"
            try:
                app_meta = self.app_data.get("metadata", {}) or {}
                installed = bool(
                    app_meta.get("installed")
                    or self.app_data.get("installed")
                    or meta.get("installed")
                    or merged.get("installed")
                    or False
                )
            except Exception:
                installed = bool(
                    meta.get("installed") or merged.get("installed") or False
                )

            if online_v and local_v:
                try:
                    from packaging.version import Version

                    ov = Version(str(online_v))
                    lv = Version(str(local_v))
                    if ov > lv:
                        action_label = "Update"
                    elif lv > ov:
                        action_label = "Installed"
                except Exception:
                    if str(online_v) != str(local_v):
                        action_label = "Update"
                    else:
                        if installed:
                            action_label = "Installed"

            if installed and action_label == "Install":
                action_label = "Installed"

            try:
                self.action_button.setText(action_label)
            except Exception:
                pass

            try:
                if action_label == "Installed":
                    self.action_button.setEnabled(False)
                else:
                    self.action_button.setEnabled(True)

                if action_label == "Update":
                    btn_theme = Theme.get_button(Theme.BUTTON_POSITIVE)
                    bg = Theme.to_ui_color(btn_theme.get("background_color"))
                    textc = Theme.to_ui_color(btn_theme.get("text_color"))
                    self.action_button.setStyleSheet(
                        f"background-color: {bg}; color: {textc}; border: none; padding: 8px 14px; border-radius: 8px; min-height: 36px; font-size: 13px;"
                    )
                else:
                    self.action_button.setStyleSheet("")
            except Exception:
                pass
        except Exception:
            pass

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

    def _on_enabled_toggled(self, app_id: str, state: int):
        try:
            from core.paths import get_user_config_path

            p = Path(get_user_config_path())
            cfg = {}
            if p.exists():
                try:
                    cfg = json.loads(p.read_text(encoding="utf-8")) or {}
                except Exception:
                    cfg = {}

            apps = cfg.get("apps", {}) if isinstance(cfg, dict) else {}
            if not isinstance(apps, dict):
                apps = {}

            entry = apps.get(app_id) or {}
            entry["enabled"] = bool(state)
            apps[app_id] = entry
            cfg["apps"] = apps

            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(
                json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception:
            pass

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
            if item[0] == "Version":
                self.info_grid.addWidget(val, row_index, 1)
            else:
                self.info_grid.addWidget(val, row_index, 1)
