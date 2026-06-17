from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.rendering.material_icons import MaterialIcons
from core.theming.theme_manager import Theme


class MessageDialog(QDialog):
    class Icon:
        INFO = "info"
        SUCCESS = "check_circle"
        WARNING = "warning"
        ERROR = "error"
        QUESTION = "help"

    def __init__(
        self,
        parent=None,
        title="Message",
        subtitle="",
        icon=None,
        button_text="OK",
        on_close=None,
    ):
        super().__init__(parent)

        self.dialog_title = str(title or "Message")
        self.dialog_message = str(subtitle or "")
        self.dialog_icon = str(icon or self.Icon.INFO)
        self.button_text = str(button_text or "OK")
        self.on_close = on_close
        self.result_value = None

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

        content_layout = QVBoxLayout(container)
        content_layout.setContentsMargins(24, 20, 24, 24)
        content_layout.setSpacing(18)

        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(16)

        icon_label = QLabel(self.get_icon_text())
        icon_label.setObjectName("dialogIcon")
        icon_label.setFixedSize(68, 68)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setFont(QFont(MaterialIcons.font_family(), 34))

        text_container = QWidget()
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 2, 0, 0)
        text_layout.setSpacing(6)

        title_label = QLabel(self.dialog_title)
        title_label.setObjectName("dialogTitle")
        title_label.setWordWrap(True)

        message_label = QLabel(self.dialog_message)
        message_label.setObjectName("dialogMessage")
        message_label.setWordWrap(True)

        text_layout.addWidget(title_label)
        text_layout.addWidget(message_label)

        dismiss_button = QPushButton(MaterialIcons.get("close"))
        dismiss_button.setObjectName("closeButton")
        dismiss_button.setFixedSize(24, 24)
        dismiss_button.setFont(QFont(MaterialIcons.font_family(), 14))
        dismiss_button.clicked.connect(self.handle_close)

        header_layout.addWidget(icon_label)
        header_layout.addWidget(text_container, 1)
        header_layout.addWidget(dismiss_button, 0, Qt.AlignTop)

        content_layout.addWidget(header_widget)

        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFixedHeight(1)
        content_layout.addWidget(divider)

        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(10)

        confirm_button = QPushButton(self.button_text)
        confirm_button.setObjectName("confirmButton")
        confirm_button.setFixedHeight(38)
        confirm_button.clicked.connect(self.handle_close)

        actions_layout.addStretch(1)
        actions_layout.addWidget(confirm_button)

        content_layout.addWidget(actions_widget)

        root_layout.addWidget(container)

        self.apply_theme_style()

    def get_button_variant(self):
        if self.dialog_icon == self.Icon.SUCCESS:
            return Theme.BUTTON_POSITIVE
        if self.dialog_icon == self.Icon.WARNING:
            return Theme.BUTTON_WARNING
        if self.dialog_icon == self.Icon.ERROR:
            return Theme.BUTTON_NEGATIVE
        if self.dialog_icon == self.Icon.INFO:
            return Theme.BUTTON_INFO
        return Theme.BUTTON_NORMAL

    def get_theme_colors(self):
        uic = Theme.to_ui_color

        colors = Theme.get_colors()
        confirm_button = Theme.get_button(self.get_button_variant())
        close_button = Theme.get_button(Theme.BUTTON_CLOSE)

        dialog_theme = Theme.get_dialog()
        icon_theme = Theme.get_icon(Theme.ICON_NORMAL)
        title_text = Theme.get_text(Theme.TEXT_TITLE)
        subtitle_text = Theme.get_text(Theme.TEXT_SUBTITLE)
        input_theme = Theme.get_input()

        container_background = dialog_theme.get(
            Theme.Components.Dialog.BACKGROUND_COLOR
        )
        container_border = dialog_theme.get(Theme.Components.Dialog.BORDER_COLOR)
        container_border_width = dialog_theme.get(Theme.Components.Dialog.BORDER_WIDTH)
        container_border_radius = dialog_theme.get(
            Theme.Components.Dialog.BORDER_RADIUS
        )

        icon_background = colors.get(Theme.Colors.PANEL)
        icon_border = input_theme.get(Theme.Components.Input.BORDER_COLOR)
        icon_border_width = input_theme.get(Theme.Components.Input.BORDER_WIDTH)
        icon_border_radius = input_theme.get(Theme.Components.Input.BORDER_RADIUS)

        divider_color = dialog_theme.get(Theme.Components.Dialog.BORDER_COLOR)

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
            "message_color": uic(subtitle_text.get(Theme.Components.Text.COLOR)),
            "divider_color": uic(divider_color),
            "confirm_background": uic(
                confirm_button.get(Theme.Components.Button.BACKGROUND_COLOR)
            ),
            "confirm_hover": uic(
                confirm_button.get(Theme.Components.Button.HOVER_COLOR)
            ),
            "confirm_pressed": uic(
                confirm_button.get(Theme.Components.Button.PRESSED_COLOR)
            ),
            "confirm_border": uic(
                confirm_button.get(Theme.Components.Button.BORDER_COLOR)
            ),
            "confirm_text": uic(confirm_button.get(Theme.Components.Button.TEXT_COLOR)),
            "confirm_border_width": confirm_button.get(
                Theme.Components.Button.BORDER_WIDTH
            ),
            "confirm_border_radius": confirm_button.get(
                Theme.Components.Button.BORDER_RADIUS
            ),
            "close_background": uic(
                close_button.get(Theme.Components.Button.BACKGROUND_COLOR)
            ),
            "close_hover": uic(close_button.get(Theme.Components.Button.HOVER_COLOR)),
            "close_pressed": uic(
                close_button.get(Theme.Components.Button.PRESSED_COLOR)
            ),
            "close_border": uic(close_button.get(Theme.Components.Button.BORDER_COLOR)),
            "close_text": uic(close_button.get(Theme.Components.Button.TEXT_COLOR)),
            "close_border_width": close_button.get(
                Theme.Components.Button.BORDER_WIDTH
            ),
            "close_border_radius": close_button.get(
                Theme.Components.Button.BORDER_RADIUS
            ),
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
        message_color = colors["message_color"]
        divider_color = colors["divider_color"]

        confirm_background = colors["confirm_background"]
        confirm_hover = colors["confirm_hover"]
        confirm_pressed = colors["confirm_pressed"]
        confirm_border = colors["confirm_border"]
        confirm_text = colors["confirm_text"]
        confirm_border_width = colors["confirm_border_width"]
        confirm_border_radius = colors["confirm_border_radius"]

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

            QLabel#dialogIcon {{
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

            QLabel#dialogMessage {{
                color: {message_color};
                font-size: 13px;
                line-height: 18px;
            }}

            QFrame#divider {{
                background-color: {divider_color};
                border: none;
            }}

            QPushButton#confirmButton {{
                min-width: 92px;
                background-color: {confirm_background};
                color: {confirm_text};
                border: {confirm_border_width}px solid {confirm_border};
                border-radius: {confirm_border_radius}px;
                padding: 0 16px;
                font-size: 13px;
                font-weight: 700;
            }}

            QPushButton#confirmButton:hover {{
                background-color: {confirm_hover};
            }}

            QPushButton#confirmButton:pressed {{
                background-color: {confirm_pressed};
            }}
        """)

    def get_icon_text(self):
        icon_name = self.dialog_icon

        if MaterialIcons.has(icon_name):
            return MaterialIcons.get(icon_name)

        if isinstance(icon_name, str) and icon_name.startswith("m:"):
            return MaterialIcons.get(icon_name, MaterialIcons.get("help", ""))

        return MaterialIcons.get("info", "")

    def handle_close(self):
        self.result_value = True

        if callable(self.on_close):
            self.on_close(self)
            return

        self.accept()

    @staticmethod
    def show(
        parent=None,
        title="Message",
        subtitle="",
        icon=Icon.INFO,
        button_text="OK",
        on_close=None,
    ):
        dialog = MessageDialog(
            parent=parent,
            title=title,
            subtitle=subtitle,
            icon=icon,
            button_text=button_text,
            on_close=on_close,
        )

        dialog.exec()

        return dialog.result_value
