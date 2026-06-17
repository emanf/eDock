import json
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.rendering.material_icons import MaterialIcons
from core.theming.theme_manager import Theme


class AppInfoDialog(QDialog):
    def __init__(self, parent=None, app_instance=None):
        super().__init__(parent)

        self.parent_button = parent
        self.app_instance = app_instance
        self.app_data = self.load_app_data()

        MaterialIcons.ensure_font()

        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(500)

        self.setup_ui()

    def setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(14, 14, 14, 14)

        container = QFrame()
        container.setObjectName("container")

        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(18)

        hero = QWidget()
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(0, 0, 0, 0)
        hero_layout.setSpacing(16)

        icon_label = QLabel(self.get_app_icon_text())
        icon_label.setObjectName("appIcon")
        icon_label.setFixedSize(68, 68)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setFont(QFont(MaterialIcons.font_family(), 34))

        title_area = QWidget()
        title_layout = QVBoxLayout(title_area)
        title_layout.setContentsMargins(0, 2, 0, 0)
        title_layout.setSpacing(6)

        title = QLabel(self.get_value("title", "Unknown App"))
        title.setObjectName("appTitle")
        title.setWordWrap(True)

        description = QLabel(self.get_value("description", "No description available."))
        description.setObjectName("appDescription")
        description.setWordWrap(True)

        title_layout.addWidget(title)
        title_layout.addWidget(description)

        close_button = QPushButton(MaterialIcons.get("close"))
        close_button.setObjectName("closeButton")
        close_button.setFixedSize(24, 24)
        close_button.setFont(QFont(MaterialIcons.font_family(), 14))
        close_button.clicked.connect(self.close)

        hero_layout.addWidget(icon_label)
        hero_layout.addWidget(title_area, 1)
        hero_layout.addWidget(close_button, 0, Qt.AlignTop)

        layout.addWidget(hero)

        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFixedHeight(1)
        layout.addWidget(divider)

        info_grid = QGridLayout()
        info_grid.setContentsMargins(0, 0, 0, 0)
        info_grid.setHorizontalSpacing(16)
        info_grid.setVerticalSpacing(11)

        rows = self.build_rows()

        for row_index, item in enumerate(rows):
            label = QLabel(item[0])
            label.setObjectName("fieldLabel")
            label.setAlignment(Qt.AlignRight | Qt.AlignTop)

            value = QLabel(item[1])
            value.setObjectName("fieldValue")
            value.setWordWrap(True)
            value.setTextInteractionFlags(Qt.TextSelectableByMouse)

            info_grid.addWidget(label, row_index, 0)
            info_grid.addWidget(value, row_index, 1)

        info_grid.setColumnStretch(0, 0)
        info_grid.setColumnStretch(1, 1)

        layout.addLayout(info_grid)

        root_layout.addWidget(container)

        self.apply_theme()

    def get_theme_colors(self):
        uic = Theme.to_ui_color

        close_button = Theme.get_button(Theme.BUTTON_CLOSE)
        icon_theme = Theme.get_icon(Theme.ICON_NORMAL)
        title_text = Theme.get_text(Theme.TEXT_TITLE)
        normal_text = Theme.get_text(Theme.TEXT_NORMAL)
        muted_text = Theme.get_text(Theme.TEXT_MUTED)
        dialog_theme = Theme.get_dialog()
        input_theme = Theme.get_input()
        colors = Theme.get_colors()

        return {
            "container_background": uic(dialog_theme.get("background_color")),
            "container_border": uic(dialog_theme.get("border_color")),
            "container_border_width": dialog_theme.get("border_width"),
            "container_border_radius": dialog_theme.get("border_radius"),
            "icon_background": uic(colors.get(Theme.Colors.PANEL)),
            "icon_border": uic(input_theme.get("border_color")),
            "icon_border_width": input_theme.get("border_width"),
            "icon_border_radius": input_theme.get("border_radius"),
            "icon_color": uic(icon_theme.get("color")),
            "title_color": uic(title_text.get("color")),
            "description_color": uic(muted_text.get("color")),
            "divider_color": uic(dialog_theme.get("border_color")),
            "field_label_color": uic(muted_text.get("color")),
            "field_value_color": uic(normal_text.get("color")),
            "close_background": uic(close_button.get("background_color")),
            "close_hover": uic(close_button.get("hover_color")),
            "close_pressed": uic(close_button.get("pressed_color")),
            "close_border": uic(close_button.get("border_color")),
            "close_text": uic(close_button.get("text_color")),
            "close_border_width": uic(close_button.get("border_width")),
            "close_border_radius": uic(close_button.get("border_radius")),
        }

    def apply_theme(self):
        theme = self.get_theme_colors()

        container_background = theme["container_background"]
        container_border = theme["container_border"]
        container_border_width = theme["container_border_width"]
        container_border_radius = theme["container_border_radius"]
        icon_background = theme["icon_background"]
        icon_border = theme["icon_border"]
        icon_border_width = theme["icon_border_width"]
        icon_border_radius = theme["icon_border_radius"]
        icon_color = theme["icon_color"]
        title_color = theme["title_color"]
        description_color = theme["description_color"]
        divider_color = theme["divider_color"]
        field_label_color = theme["field_label_color"]
        field_value_color = theme["field_value_color"]
        close_background = theme["close_background"]
        close_hover = theme["close_hover"]
        close_pressed = theme["close_pressed"]
        close_border = theme["close_border"]
        close_text = theme["close_text"]
        close_border_width = theme["close_border_width"]
        close_border_radius = theme["close_border_radius"]

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
            }}

            QLabel#fieldValue {{
                color: {field_value_color};
                font-size: 13px;
            }}
        """)

    def build_rows(self):
        if not self.app_data:
            return [("Status", "No app information available.")]

        field_order = [
            ("id", "App ID"),
            ("version", "Version"),
            ("last_modified", "Last Modified"),
            ("author", "Author"),
            ("author_email", "Email"),
            ("author_website", "Website"),
        ]

        rows = []

        for key, label in field_order:
            value = self.app_data.get(key)
            if value:
                rows.append((label, str(value)))

        for key, value in self.app_data.items():
            if (
                key
                not in (
                    "title",
                    "description",
                    "author",
                    "author_email",
                    "author_website",
                    "version",
                    "last_modified",
                    "id",
                    "icon",
                )
                and value
            ):
                rows.append((self.format_key(key), str(value)))

        if not rows:
            rows.append(("Status", "No app information available."))

        return rows

    def load_app_data(self):
        app_json_path = self.find_app_json_path()

        if not app_json_path:
            return {}

        try:
            with open(app_json_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            if isinstance(data, dict):
                return data
        except Exception:
            return {}

        return {}

    def find_app_json_path(self):
        direct_path = self.find_direct_app_json_path()

        if direct_path:
            return direct_path

        project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..")
        )

        apps_root = os.path.join(project_root, "apps")

        if not os.path.isdir(apps_root):
            return None

        app_folder = self.find_app_folder_name()

        if app_folder:
            path = os.path.join(apps_root, app_folder, "app.json")
            if os.path.exists(path):
                return path

        expected_id = self.find_expected_value("id")
        expected_title = self.find_expected_value("title") or self.find_expected_value(
            "name"
        )

        for folder_name in os.listdir(apps_root):
            path = os.path.join(apps_root, folder_name, "app.json")

            if not os.path.exists(path):
                continue

            try:
                with open(path, "r", encoding="utf-8") as file:
                    data = json.load(file)

                if not isinstance(data, dict):
                    continue

                if expected_id and data.get("id") == expected_id:
                    return path

                if expected_title and data.get("title") == expected_title:
                    return path
            except Exception:
                continue

        return None

    def find_direct_app_json_path(self):
        loaded_app = getattr(self.parent_button, "loaded_app", None)

        paths = []

        if isinstance(loaded_app, dict):
            for key in ("app_json", "app_json_path", "manifest", "manifest_path"):
                value = loaded_app.get(key)
                if value:
                    paths.append(str(value))

            for key in ("app_dir", "folder_path", "path"):
                value = loaded_app.get(key)
                if value:
                    paths.append(os.path.join(str(value), "app.json"))

        app_dir = getattr(self.parent_button, "app_dir", None)
        if app_dir:
            paths.append(os.path.join(str(app_dir), "app.json"))

        if self.app_instance:
            app_dir = getattr(self.app_instance, "app_dir", None)
            if app_dir:
                paths.append(os.path.join(str(app_dir), "app.json"))

        for path in paths:
            normalized = os.path.abspath(path)
            if os.path.exists(normalized):
                return normalized

        return None

    def find_app_folder_name(self):
        loaded_app = getattr(self.parent_button, "loaded_app", None)

        if isinstance(loaded_app, dict):
            for key in ("folder", "folder_name", "app_folder"):
                value = loaded_app.get(key)
                if value:
                    return os.path.basename(os.path.normpath(str(value)))

            for key in ("app_dir", "folder_path", "path"):
                value = loaded_app.get(key)
                if value:
                    return os.path.basename(os.path.normpath(str(value)))

        app_dir = getattr(self.parent_button, "app_dir", None)
        if app_dir:
            return os.path.basename(os.path.normpath(str(app_dir)))

        if self.app_instance:
            for attr in ("folder", "folder_name", "app_folder"):
                value = getattr(self.app_instance, attr, None)
                if value:
                    return os.path.basename(os.path.normpath(str(value)))

            app_dir = getattr(self.app_instance, "app_dir", None)
            if app_dir:
                return os.path.basename(os.path.normpath(str(app_dir)))

        return None

    def find_expected_value(self, key):
        loaded_app = getattr(self.parent_button, "loaded_app", None)

        if isinstance(loaded_app, dict):
            value = loaded_app.get(key)
            if value:
                return str(value)

        if self.app_instance:
            value = getattr(self.app_instance, key, None)
            if value:
                return str(value)

        return None

    def get_value(self, key, fallback):
        value = self.app_data.get(key)

        if value:
            return str(value)

        return fallback

    def get_app_icon_text(self):
        icon = self.app_data.get("icon")

        if isinstance(icon, str) and icon.startswith("m:"):
            icon_name = icon[2:].strip()
            return MaterialIcons.get(icon_name, MaterialIcons.get("apps", ""))

        return MaterialIcons.get("apps", "")

    @staticmethod
    def format_key(key):
        return key.replace("_", " ").title()

    @staticmethod
    def show(parent, app_instance=None):
        dialog = AppInfoDialog(parent, app_instance)
        dialog.exec()
