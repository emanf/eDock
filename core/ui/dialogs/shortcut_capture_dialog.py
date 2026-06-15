from PySide6.QtCore import Qt, QKeyCombination
from PySide6.QtGui import QKeySequence, QFont
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QKeySequenceEdit, QWidget, QFrame

from core.rendering.material_icons import MaterialIcons
from core.theming.theme_manager import Theme

class ShortcutCaptureDialog(QDialog):
    def __init__(self, current_shortcut="", parent=None):
        super().__init__(parent)

        self.current_shortcut = current_shortcut or ""
        self.shortcut_value = current_shortcut or ""

        MaterialIcons.ensure_font()

        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(500)

        self.setup_ui()

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)

        self.container = QFrame()
        self.container.setObjectName("container")
        root.addWidget(self.container)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(18)

        hero = QWidget()
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(0, 0, 0, 0)
        hero_layout.setSpacing(16)

        icon_label = QLabel(MaterialIcons.get("keyboard"))
        icon_label.setObjectName("shortcutIcon")
        icon_label.setFixedSize(68, 68)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setFont(QFont(MaterialIcons.font_family(), 34))

        title_area = QWidget()
        title_layout = QVBoxLayout(title_area)
        title_layout.setContentsMargins(0, 2, 0, 0)
        title_layout.setSpacing(6)

        title = QLabel("Set Shortcut")
        title.setObjectName("dialogTitle")
        title.setWordWrap(True)

        desc = QLabel("Press the keyboard combination you want to assign")
        desc.setObjectName("dialogDescription")
        desc.setWordWrap(True)

        title_layout.addWidget(title)
        title_layout.addWidget(desc)

        close_btn = QPushButton(MaterialIcons.get("close"))
        close_btn.setObjectName("closeButton")
        close_btn.setFixedSize(24, 24)
        close_btn.setFont(QFont(MaterialIcons.font_family(), 14))
        close_btn.clicked.connect(self.reject)

        hero_layout.addWidget(icon_label)
        hero_layout.addWidget(title_area, 1)
        hero_layout.addWidget(close_btn, 0, Qt.AlignTop)

        layout.addWidget(hero)

        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFixedHeight(1)
        layout.addWidget(divider)

        self.shortcut_edit = QKeySequenceEdit()
        self.shortcut_edit.setObjectName("shortcutEdit")
        self.shortcut_edit.setMinimumHeight(72)
        self.shortcut_edit.setMaximumSequenceLength(1)
        self.shortcut_edit.setFocusPolicy(Qt.NoFocus)

        if self.current_shortcut:
            self.shortcut_edit.setKeySequence(QKeySequence(self.current_shortcut))

        layout.addWidget(self.shortcut_edit)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setObjectName("secondaryButton")

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("secondaryButton")

        self.btn_save = QPushButton("Save")
        self.btn_save.setObjectName("primaryButton")

        buttons.addWidget(self.btn_clear)
        buttons.addWidget(self.btn_cancel)
        buttons.addStretch()
        buttons.addWidget(self.btn_save)

        layout.addLayout(buttons)

        self.btn_clear.clicked.connect(self.clear_shortcut)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save.clicked.connect(self.save_shortcut)

        self.apply_theme_style()

    def get_theme_name(self):
        widget = self.parent()

        while widget:
            config_manager = getattr(widget, "config_manager", None)

            if config_manager:
                data = getattr(config_manager, "data", None)
                if isinstance(data, dict):
                    return data.get("theme", "dark")

                config = getattr(config_manager, "config", None)
                if isinstance(config, dict):
                    return config.get("theme", "dark")

            dock_window = getattr(widget, "dock_window", None)

            if dock_window:
                config_manager = getattr(dock_window, "config_manager", None)

                if config_manager:
                    data = getattr(config_manager, "data", None)
                    if isinstance(data, dict):
                        return data.get("theme", "dark")

                    config = getattr(config_manager, "config", None)
                    if isinstance(config, dict):
                        return config.get("theme", "dark")

            parent = getattr(widget, "parent", None)

            if callable(parent):
                widget = parent()
            else:
                widget = None

        return "dark"

    def _theme_data(self):
        widget = self.parent()

        while widget:
            dock_window = getattr(widget, "dock_window", None)
            if dock_window is not None:
                active_theme = getattr(dock_window, "active_theme", None)
                if isinstance(active_theme, dict):
                    return active_theme

            parent = getattr(widget, "parent", None)

            if callable(parent):
                widget = parent()
            else:
                widget = None

        return Theme.get_theme(self.get_theme_name())

    def get_theme_colors(self):
        uic = Theme.to_ui_color
        
        colors = Theme.get_colors()
        normal_button = Theme.get_button(Theme.BUTTON_NORMAL)
        primary_button = Theme.get_button(Theme.BUTTON_POSITIVE)
        close_button = Theme.get_button(Theme.BUTTON_CLOSE)

        icon_theme = Theme.get_icon(Theme.ICON_NORMAL)
        title_text = Theme.get_text(Theme.TEXT_TITLE)
        subtitle_text = Theme.get_text(Theme.TEXT_SUBTITLE)
        dialog_theme = Theme.get_dialog()
        input_theme = Theme.get_input()

        container_background = dialog_theme.get(Theme.Components.Dialog.BACKGROUND_COLOR)
        container_border = dialog_theme.get(Theme.Components.Dialog.BORDER_COLOR)
        container_border_width = dialog_theme.get(Theme.Components.Dialog.BORDER_WIDTH)
        container_border_radius = dialog_theme.get(Theme.Components.Dialog.BORDER_RADIUS)

        icon_background = colors.get(Theme.Colors.PANEL)
        icon_border = input_theme.get(Theme.Components.Input.BORDER_COLOR)
        icon_border_width = input_theme.get(Theme.Components.Input.BORDER_WIDTH)
        icon_border_radius = input_theme.get(Theme.Components.Input.BORDER_RADIUS)

        divider_color = dialog_theme.get(Theme.Components.Dialog.BORDER_COLOR)

        shortcut_background = input_theme.get(Theme.Components.Input.BACKGROUND_COLOR)
        shortcut_border = input_theme.get(Theme.Components.Input.BORDER_COLOR)
        shortcut_border_width = input_theme.get(Theme.Components.Input.BORDER_WIDTH)
        shortcut_border_radius = input_theme.get(Theme.Components.Input.BORDER_RADIUS)

        return {
            "container_background": uic(container_background),
            "container_border": uic(container_border),
            "container_border_width": container_border_width,
            "container_border_radius": container_border_radius,
            "icon_background": uic(icon_background),
            "icon_border": uic(icon_border),
            "icon_border_width": icon_border_width,
            "icon_border_radius": icon_border_radius,
            "icon_color": uic(icon_theme.get(Theme.Components.Icon.COLOR)),
            "title_color": uic(title_text.get(Theme.Components.Text.COLOR)),
            "description_color": uic(subtitle_text.get(Theme.Components.Text.COLOR)),
            "divider_color": uic(divider_color),
            "shortcut_background": uic(shortcut_background),
            "shortcut_border": uic(shortcut_border),
            "shortcut_border_width": shortcut_border_width,
            "shortcut_border_radius": shortcut_border_radius,
            "shortcut_text": uic(input_theme.get(Theme.Components.Input.TEXT_COLOR)),
            "normal_background": uic(normal_button.get(Theme.Components.Button.BACKGROUND_COLOR)),
            "normal_hover": uic(normal_button.get(Theme.Components.Button.HOVER_COLOR)),
            "normal_pressed": uic(normal_button.get(Theme.Components.Button.PRESSED_COLOR)),
            "normal_border": uic(normal_button.get(Theme.Components.Button.BORDER_COLOR)),
            "normal_text": uic(normal_button.get(Theme.Components.Button.TEXT_COLOR)),
            "normal_border_width": normal_button.get(Theme.Components.Button.BORDER_WIDTH),
            "normal_border_radius": normal_button.get(Theme.Components.Button.BORDER_RADIUS),
            "primary_background": uic(primary_button.get(Theme.Components.Button.BACKGROUND_COLOR)),
            "primary_hover": uic(primary_button.get(Theme.Components.Button.HOVER_COLOR)),
            "primary_pressed": uic(primary_button.get(Theme.Components.Button.PRESSED_COLOR)),
            "primary_border": uic(primary_button.get(Theme.Components.Button.BORDER_COLOR)),
            "primary_text": uic(primary_button.get(Theme.Components.Button.TEXT_COLOR)),
            "primary_border_width": primary_button.get(Theme.Components.Button.BORDER_WIDTH),
            "primary_border_radius": primary_button.get(Theme.Components.Button.BORDER_RADIUS),
            "close_background": uic(close_button.get(Theme.Components.Button.BACKGROUND_COLOR)),
            "close_hover": uic(close_button.get(Theme.Components.Button.HOVER_COLOR)),
            "close_pressed": uic(close_button.get(Theme.Components.Button.PRESSED_COLOR)),
            "close_border": uic(close_button.get(Theme.Components.Button.BORDER_COLOR)),
            "close_text": uic(close_button.get(Theme.Components.Button.TEXT_COLOR)),
            "close_border_width": close_button.get(Theme.Components.Button.BORDER_WIDTH),
            "close_border_radius": close_button.get(Theme.Components.Button.BORDER_RADIUS),
        }


    def apply_theme_style(self):
        colors = self.get_theme_colors()

        container_background = colors["container_background"]
        container_border = colors["container_border"]
        container_border_width = colors["container_border_width"]
        container_border_radius = colors["container_border_radius"]
        icon_background = colors["icon_background"]
        icon_border = colors["icon_border"]
        icon_border_width = colors["icon_border_width"]
        icon_border_radius = colors["icon_border_radius"]
        icon_color = colors["icon_color"]
        title_color = colors["title_color"]
        description_color = colors["description_color"]
        divider_color = colors["divider_color"]
        shortcut_background = colors["shortcut_background"]
        shortcut_border = colors["shortcut_border"]
        shortcut_border_width = colors["shortcut_border_width"]
        shortcut_border_radius = colors["shortcut_border_radius"]
        shortcut_text = colors["shortcut_text"]
        normal_background = colors["normal_background"]
        normal_hover = colors["normal_hover"]
        normal_pressed = colors["normal_pressed"]
        normal_border = colors["normal_border"]
        normal_text = colors["normal_text"]
        normal_border_width = colors["normal_border_width"]
        normal_border_radius = colors["normal_border_radius"]
        primary_background = colors["primary_background"]
        primary_hover = colors["primary_hover"]
        primary_pressed = colors["primary_pressed"]
        primary_border = colors["primary_border"]
        primary_text = colors["primary_text"]
        primary_border_width = colors["primary_border_width"]
        primary_border_radius = colors["primary_border_radius"]
        close_background = colors["close_background"]
        close_hover = colors["close_hover"]
        close_pressed = colors["close_pressed"]
        close_border = colors["close_border"]
        close_text = colors["close_text"]
        close_border_width = colors["close_border_width"]
        close_border_radius = colors["close_border_radius"]


        self.setStyleSheet(f"""
            QDialog {{
                background: transparent;
            }}

            QFrame#container {{
                background-color: {container_background};
                border: {container_border_width}px solid {container_border};
                border-radius: {container_border_radius}px;
            }}

            QLabel#shortcutIcon {{
                background-color: {icon_background};
                color: {icon_color};
                border: {icon_border_width}px solid {icon_border};
                border-radius: {icon_border_radius}px;
            }}

            QLabel#dialogTitle {{
                color: {title_color};
                font-size: 22px;
                font-weight: 700;
            }}

            QLabel#dialogDescription {{
                color: {description_color};
                font-size: 13px;
                line-height: 18px;
            }}

            QFrame#divider {{
                background-color: {divider_color};
                border: none;
            }}

            QKeySequenceEdit#shortcutEdit {{
                background-color: {shortcut_background};
                color: {shortcut_text};
                border: {shortcut_border_width}px solid {shortcut_border};
                border-radius: {shortcut_border_radius}px;
                padding: 10px;
                font-size: 22px;
            }}

            QKeySequenceEdit#shortcutEdit QLineEdit {{
                background: transparent;
                border: none;
                color: {shortcut_text};
                font-size: 22px;
            }}

            QPushButton {{
                background-color: {normal_background};
                color: {normal_text};
                border: {normal_border_width}px solid {normal_border};
                border-radius: {normal_border_radius}px;
                padding: 7px 16px;
                min-height: 30px;
                font-size: 13px;
            }}

            QPushButton:hover {{
                background-color: {normal_hover};
            }}

            QPushButton:pressed {{
                background-color: {normal_pressed};
            }}

            QPushButton#primaryButton {{
                background-color: {primary_background};
                border: {primary_border_width}px solid {primary_border};
                border-radius: {primary_border_radius}px;
                color: {primary_text};
                font-weight: 600;
            }}

            QPushButton#primaryButton:hover {{
                background-color: {primary_hover};
            }}

            QPushButton#primaryButton:pressed {{
                background-color: {primary_pressed};
            }}

            QPushButton#secondaryButton {{
                background-color: {normal_background};
                color: {normal_text};
                border: {normal_border_width}px solid {normal_border};
                border-radius: {normal_border_radius}px;
            }}

            QPushButton#secondaryButton:hover {{
                background-color: {normal_hover};
            }}

            QPushButton#secondaryButton:pressed {{
                background-color: {normal_pressed};
            }}

            QPushButton#closeButton {{
                min-width: 24px;
                max-width: 24px;
                min-height: 24px;
                max-height: 24px;
                background-color: {close_background};
                color: {close_text};
                border: {close_border_width}px solid {close_border};
                border-radius: {close_border_radius}px;
                padding: 0;
                margin: 0;
                font-family: "{MaterialIcons.font_family()}";
                font-size: 14pt;
                font-weight: normal;
            }}

            QPushButton#closeButton:hover {{
                background-color: {close_hover};
            }}

            QPushButton#closeButton:pressed {{
                background-color: {close_pressed};
            }}
        """)

    def showEvent(self, event):
        super().showEvent(event)
        self.activateWindow()
        self.raise_()

    def keyPressEvent(self, event):
        key = event.key()

        if key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta):
            event.accept()
            return

        if key in (Qt.Key_Return, Qt.Key_Enter):
            self.save_shortcut()
            event.accept()
            return

        if key == Qt.Key_Escape:
            self.reject()
            event.accept()
            return

        try:
            qt_key = Qt.Key(key)
        except Exception:
            super().keyPressEvent(event)
            return

        modifiers = event.modifiers()

        has_modifier = bool(
            modifiers & Qt.ControlModifier
            or modifiers & Qt.ShiftModifier
            or modifiers & Qt.AltModifier
            or modifiers & Qt.MetaModifier
        )

        if not has_modifier:
            event.accept()
            return

        combination = QKeyCombination(modifiers, qt_key)
        sequence = QKeySequence(combination)
        self.shortcut_edit.setKeySequence(sequence)
        event.accept()

    def clear_shortcut(self):
        self.shortcut_edit.clear()
        self.shortcut_value = ""

    def save_shortcut(self):
        seq = self.shortcut_edit.keySequence()

        if seq.isEmpty():
            self.shortcut_value = ""
            self.accept()
            return

        text = seq.toString(QKeySequence.NativeText).strip()

        if not text:
            self.shortcut_value = ""
            self.accept()
            return

        self.shortcut_value = text
        self.accept()

    def get_value(self):
        return self.shortcut_value
