from PySide6.QtGui import QAction, QIcon, QPixmap, QPainter, QFont
from PySide6.QtWidgets import QMenu, QProxyStyle, QStyle
from PySide6.QtCore import Qt

from core.rendering.material_icons import MaterialIcons
from core.ui.dialogs.confirm_dialog import ConfirmDialog
from core.theming.theme_manager import Theme


class DockButtonMenuIconStyle(QProxyStyle):
    def __init__(self, base_style=None, icon_size=30):
        super().__init__(base_style)
        self.icon_size = icon_size

    def pixelMetric(self, metric, option=None, widget=None):
        if metric == QStyle.PixelMetric.PM_SmallIconSize:
            return self.icon_size
        return super().pixelMetric(metric, option, widget)


class DockButtonMenu(QMenu):
    def __init__(self, parent_button):
        super().__init__(parent_button)
        self.button = parent_button
        self._action_callbacks = {}
        self._menu_icon_size = 24
        self._menu_icon_style = DockButtonMenuIconStyle(self.style(), self._menu_icon_size)
        MaterialIcons.ensure_font()
        self.setStyle(self._menu_icon_style)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setup_style()

    def get_theme_name(self):
        button = getattr(self, "button", None)

        config_manager = getattr(button, "config_manager", None)
        if config_manager is not None:
            if hasattr(config_manager, "get_theme_name"):
                try:
                    theme_name = config_manager.get_theme_name()
                    if theme_name:
                        return theme_name
                except Exception:
                    pass

            if hasattr(config_manager, "get"):
                try:
                    theme_name = config_manager.get("theme")
                    if theme_name:
                        return theme_name
                except Exception:
                    pass

        dock_window = getattr(button, "dock_window", None)
        if dock_window is not None:
            theme_name = getattr(dock_window, "theme_name", None)
            if theme_name:
                return theme_name

            theme_name = getattr(dock_window, "current_theme", None)
            if theme_name:
                return theme_name

            dock_config_manager = getattr(dock_window, "config_manager", None)
            if dock_config_manager is not None:
                if hasattr(dock_config_manager, "get_theme_name"):
                    try:
                        theme_name = dock_config_manager.get_theme_name()
                        if theme_name:
                            return theme_name
                    except Exception:
                        pass

                if hasattr(dock_config_manager, "get"):
                    try:
                        theme_name = dock_config_manager.get("theme")
                        if theme_name:
                            return theme_name
                    except Exception:
                        pass

        return "dark"

    def _theme_data(self):
        button = getattr(self, "button", None)
        dock_window = getattr(button, "dock_window", None)

        if dock_window is not None:
            active_theme = getattr(dock_window, "active_theme", None)
            if isinstance(active_theme, dict):
                return active_theme

        return Theme.get_theme(self.get_theme_name())

    def get_theme_colors(self):
        normal_button = Theme.get_button(Theme.BUTTON_NORMAL)
        text_theme = Theme.get_text(Theme.TEXT_NORMAL)
        menu_theme = Theme.get_menu()
        dialog_theme = Theme.get_dialog()
        dock_theme = Theme.get_dock()

        text_color = text_theme.get("color", "#ffffff")
        disabled_text = Theme.get_text_color(Theme.TEXT_MUTED) or text_color

        try:
            text_qcolor = Theme.to_ui_qcolor(text_color)
            if text_qcolor.isValid():
                if ((text_qcolor.red() * 299) + (text_qcolor.green() * 587) + (text_qcolor.blue() * 114)) / 1000 < 140:
                    disabled_text = "#00000073"
                else:
                    disabled_text = "#FFFFFF73"
        except Exception:
            pass

        menu_background = (
            menu_theme.get("background_color")
            or dialog_theme.get("background_color")
            or dock_theme.get("background_color")
            or "#2b2b2b"
        )

        separator_color = (
            menu_theme.get("separator_color")
            or dialog_theme.get("border_color")
            or dock_theme.get("border_color")
            or "#444444"
        )

        border_radius = (
            menu_theme.get("border_radius")
            or dialog_theme.get("border_radius")
            or dock_theme.get("border_radius")
            or 12
        )

        return {
            "menu_background": menu_background,
            "item_background": menu_background,
            "item_hover": normal_button.get("hover_color", "#3a3a3a"),
            "item_pressed": normal_button.get("pressed_color", "#454545"),
            "text_color": text_color,
            "separator_color": separator_color,
            "disabled_text": disabled_text,
            "border_radius": border_radius
        }

    def get_menu_icon_color(self):
        colors = self.get_theme_colors()
        return Theme.to_ui_qcolor(colors["text_color"])

    def setup_style(self):
        colors = self.get_theme_colors()

        menu_background = Theme.to_ui_color(colors["menu_background"])
        item_hover = Theme.to_ui_color(colors["item_hover"])
        item_pressed = Theme.to_ui_color(colors["item_pressed"])
        text_color = Theme.to_ui_color(colors["text_color"])
        separator_color = Theme.to_ui_color(colors["separator_color"])
        disabled_text = Theme.to_ui_color(colors["disabled_text"])

        border_radius = colors["border_radius"]

        self.setStyleSheet(f"""
            QMenu {{
                background-color: {menu_background};
                color: {text_color};
                border: 0px;
                border-radius: {border_radius}px;
                padding: 7px;
                margin: 0px;
            }}
            QMenu::item {{
                min-width: 190px;
                padding: 8px 14px 8px 14px;
                border: 0px;
                border-radius: 8px;
                background-color: transparent;
                color: {text_color};
                margin: 0px;
            }}
            QMenu::item:selected {{
                background-color: {item_hover};
                color: {text_color};
            }}
            QMenu::item:pressed {{
                background-color: {item_pressed};
                color: {text_color};
            }}
            QMenu::item:disabled {{
                color: {disabled_text};
                background-color: transparent;
            }}
            QMenu::item:disabled:selected {{
                background-color: transparent;
            }}
            QMenu::separator {{
                height: 1px;
                background: {separator_color};
                margin: 6px 8px;
            }}
            QMenu::icon {{
                left: 6px;
                width: {self._menu_icon_size}px;
                height: {self._menu_icon_size}px;
            }}
        """)

    @staticmethod
    def _create_material_icon(icon_name, size=30, color="white"):
        glyph = MaterialIcons.get(icon_name)
        if not glyph:
            return QIcon()

        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        painter.setPen(color)

        font = QFont(MaterialIcons.font_family())
        font.setPixelSize(size - 1)
        painter.setFont(font)

        painter.drawText(pixmap.rect(), Qt.AlignCenter, glyph)
        painter.end()

        return QIcon(pixmap)

    def _create_action(self, title, icon=None, callback=None, enabled=True):
        action = QAction(title, self)
        action.setEnabled(bool(enabled))

        if icon:
            qicon = self._create_material_icon(icon, size=self._menu_icon_size, color=self.get_menu_icon_color())
            action.setIcon(qicon)

        if callable(callback) and enabled:
            self._action_callbacks[action] = callback

        self.addAction(action)
        return action

    @staticmethod
    def _app_name(button):
        app = getattr(button, "loaded_app", None) or {}
        if isinstance(app, dict):
            return str(app.get("title") or app.get("name") or app.get("id") or "App")
        return "App"

    @staticmethod
    def _app_instance(button):
        instance = getattr(button, "app_instance", None)
        if instance:
            return instance
        dock_window = getattr(button, "dock_window", None)
        app_data = getattr(button, "loaded_app", None)
        if dock_window and app_data and hasattr(dock_window, "get_app_instance"):
            try:
                instance = dock_window.get_app_instance(app_data)
                if instance and hasattr(button, "set_app_instance"):
                    button.set_app_instance(instance)
                return instance
            except Exception:
                return None
        return None

    @staticmethod
    def _normalize_custom_menu(menu_data):
        normalized = {"hide_default_menu": False, "items": []}
        if not menu_data:
            return normalized

        if isinstance(menu_data, dict):
            if "items" in menu_data:
                normalized["hide_default_menu"] = bool(menu_data.get("hide_default_menu", False))
                items = menu_data.get("items", [])
                if isinstance(items, list):
                    normalized["items"] = items
                return normalized

            items = []
            for title, callback in menu_data.items():
                if str(title).strip().lower() == "separator":
                    items.append({"type": "separator"})
                else:
                    items.append({"type": "menu", "title": str(title), "action": callback})
            normalized["items"] = items
            return normalized

        if isinstance(menu_data, list):
            normalized["items"] = menu_data
            return normalized
        return normalized

    def add_custom_items(self, items):
        if not items:
            return

        for item in items:
            if not isinstance(item, dict):
                continue

            item_type = str(item.get("type", "menu")).strip().lower()

            if item_type == "separator":
                self.addSeparator()
                continue

            title = str(item.get("title", "")).strip()
            if not title:
                continue

            icon = item.get("icon")
            callback = item.get("action")
            enabled = item.get("enabled", True) if item_type != "disabled-menu" else False

            self._create_action(title=title, icon=icon, callback=callback, enabled=enabled)

    @staticmethod
    def execute(button, pos):
        menu = DockButtonMenu(button)
        app_name = DockButtonMenu._app_name(button)

        title_action = QAction(app_name, menu)
        title_action.setEnabled(False)
        menu.addAction(title_action)
        menu.addSeparator()

        custom_menu_data = None
        app_instance = DockButtonMenu._app_instance(button)

        if app_instance:
            if hasattr(app_instance, "on_right_click"):
                try:
                    custom_menu_data = app_instance.on_right_click()
                except Exception:
                    custom_menu_data = None

        normalized_menu = menu._normalize_custom_menu(custom_menu_data)
        custom_items = normalized_menu.get("items", [])
        hide_default_menu = normalized_menu.get("hide_default_menu", False)

        if custom_items:
            menu.add_custom_items(custom_items)
            if not hide_default_menu:
                menu.addSeparator()

        act_info = act_shortcut = act_open_data_folder = None
        act_clear_cache = act_clear_data = act_remove = None

        if not hide_default_menu:
            act_info = menu._create_action(title="App Info", icon="info")
            act_shortcut = menu._create_action(title="Shortcut", icon="keyboard")
            act_open_data_folder = menu._create_action(title="Open App Data Folder", icon="folder_open")

            menu.addSeparator()

            act_clear_cache = menu._create_action(title="Clear app cache", icon="delete")
            act_clear_data = menu._create_action(title="Clear app data", icon="warning")
            act_remove = menu._create_action(title="Remove App from Dock", icon="remove_circle")

        selected = menu.exec(pos)

        if selected is None:
            return

        custom_callback = menu._action_callbacks.get(selected)
        if callable(custom_callback):
            custom_callback()
            return

        if selected == act_info:
            if hasattr(button, "show_app_info"):
                button.show_app_info()
        elif selected == act_shortcut:
            if hasattr(button, "open_shortcut_dialog"):
                button.open_shortcut_dialog()
        elif selected == act_open_data_folder:
            if hasattr(button, "open_app_data_folder"):
                button.open_app_data_folder()
        elif selected == act_clear_cache:
            if hasattr(button, "clear_app_cache"):
                if ConfirmDialog.show(parent=button, title="Clear App Cache", message="The app cache will be cleared.", icon="delete", confirm_button_text="Clear Cache"):
                    button.clear_app_cache()
        elif selected == act_clear_data:
            if hasattr(button, "clear_app_data"):
                if ConfirmDialog.show(parent=button, title="Clear App Data", message="All saved data will be deleted.", icon="warning", confirm_button_text="Delete Data"):
                    button.clear_app_data()
        elif selected == act_remove:
            if hasattr(button, "remove_button"):
                if ConfirmDialog.show(parent=button, title="Remove App", message=f"Remove {app_name} from the dock?", icon="remove_circle", confirm_button_text="Remove"):
                    button.remove_button()
