from typing import Callable, Dict, Optional, Union, Any
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot, Qt, QRectF
from PySide6.QtGui import QAction, QIcon, QCursor, QPixmap, QPainter, QFont, QColor, QPainterPath
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QWidget, QProxyStyle, QStyle

from core.rendering.material_icons import MaterialIcons
from core.theming.theme_manager import Theme


MenuValue = Union[Callable, Dict[str, Any], None]


class TrayMenuIconStyle(QProxyStyle):
    def __init__(self, base_style=None, icon_size=20, arrow_size=8):
        super().__init__(base_style)
        self.icon_size = icon_size
        self.arrow_size = arrow_size

    def pixelMetric(self, metric, option=None, widget=None):
        if metric == QStyle.PixelMetric.PM_SmallIconSize:
            return self.icon_size
        if metric == QStyle.PixelMetric.PM_SubMenuOverlap:
            return 0
        return super().pixelMetric(metric, option, widget)

    def drawPrimitive(self, element, option, painter, widget=None):
        if element == QStyle.PrimitiveElement.PE_IndicatorArrowRight:
            painter.save()
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setPen(Qt.NoPen)

            color = QColor("#ffffff")
            if widget is not None:
                color = widget.palette().color(widget.foregroundRole())

            painter.setBrush(color)

            rect = QRectF(option.rect)
            w = float(self.arrow_size)
            h = float(self.arrow_size)
            x = rect.center().x() - (w / 2.0) + 0.5
            y = rect.center().y() - (h / 2.0)

            path = QPainterPath()
            path.moveTo(x, y)
            path.lineTo(x + w, y + (h / 2.0))
            path.lineTo(x, y + h)
            path.closeSubpath()

            painter.drawPath(path)
            painter.restore()
            return

        super().drawPrimitive(element, option, painter, widget)


class TrayManager(QObject):
    activated = Signal(QSystemTrayIcon.ActivationReason)

    def __init__(
        self,
        app: QApplication,
        parent: Optional[QWidget] = None,
        icon: Optional[QIcon] = None,
        tooltip: str = "eDock",
    ):
        super().__init__(parent)

        self.app = app
        self.parent = parent
        self._actions: Dict[str, QAction] = {}
        self._menus: Dict[str, QMenu] = {}
        self._menu_icon_size = 20
        self._submenu_arrow_size = 7
        self._menu_icon_style = TrayMenuIconStyle(None, self._menu_icon_size, self._submenu_arrow_size)

        MaterialIcons.ensure_font()

        self._tray = QSystemTrayIcon(parent)
        self._menu = QMenu(parent)

        self._menu.setStyle(self._menu_icon_style)
        self._menu.setWindowFlags(
            self._menu.windowFlags() | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint
        )
        self._menu.setAttribute(Qt.WA_TranslucentBackground, True)
        self._apply_menu_theme()

        self._tray.setToolTip(str(tooltip or "eDock"))
        self._tray.setIcon(self._resolve_icon(icon))
        self._tray.setContextMenu(self._menu)
        self._tray.activated.connect(self._on_activated)

    def show(self) -> None:
        self._ensure_icon()
        self._apply_menu_theme()
        self._tray.show()

    def hide(self) -> None:
        self._tray.hide()

    def is_visible(self) -> bool:
        return self._tray.isVisible()

    def set_tray_visible(self, visible: bool) -> None:
        self._ensure_icon()
        self._apply_menu_theme()
        self._tray.setVisible(bool(visible))

    def set_icon(self, icon: QIcon) -> None:
        if isinstance(icon, QIcon):
            self._tray.setIcon(icon)

    def set_tooltip(self, text: str) -> None:
        self._tray.setToolTip(str(text or ""))

    def tray(self) -> QSystemTrayIcon:
        return self._tray

    def menu(self) -> QMenu:
        return self._menu

    def build_menu(self, data: Optional[Dict[str, MenuValue]]) -> QMenu:
        self.clear_menu()

        if not isinstance(data, dict):
            return self._menu

        self._add_items(self._menu, data)
        return self._menu

    def clear_menu(self) -> None:
        self._menu.clear()
        self._actions.clear()
        self._menus.clear()

    def add_action(
        self,
        label: str,
        callback: Optional[Callable] = None,
        key: Optional[str] = None,
        menu: Optional[QMenu] = None,
        before: Optional[Union[str, QAction]] = None,
        enabled: bool = True,
        visible: bool = True,
        icon: Optional[Union[QIcon, str]] = None,
    ) -> QAction:
        target_menu = menu or self._menu
        action_key = self._normalize_key(key or label)

        action = QAction(str(label or ""), target_menu)
        action.setEnabled(bool(enabled))
        action.setVisible(bool(visible))

        resolved_icon = self._resolve_menu_item_icon(icon)
        if isinstance(resolved_icon, QIcon) and not resolved_icon.isNull():
            action.setIcon(resolved_icon)

        if callable(callback):
            action.triggered.connect(
                lambda checked=False, act=action, cb=callback: self._call_callback(cb, act)
            )

        reference = self._resolve_action(before)
        if reference is not None:
            target_menu.insertAction(reference, action)
        else:
            target_menu.addAction(action)

        if action_key:
            self._actions[action_key] = action

        return action

    def add_separator(
        self,
        menu: Optional[QMenu] = None,
        before: Optional[Union[str, QAction]] = None,
    ) -> QAction:
        target_menu = menu or self._menu
        reference = self._resolve_action(before)

        if reference is not None:
            return target_menu.insertSeparator(reference)

        return target_menu.addSeparator()

    def add_menu(
        self,
        label: str,
        items: Optional[Dict[str, MenuValue]] = None,
        key: Optional[str] = None,
        menu: Optional[QMenu] = None,
        before: Optional[Union[str, QAction]] = None,
        icon: Optional[Union[QIcon, str]] = None,
    ) -> QMenu:
        target_menu = menu or self._menu
        menu_key = self._normalize_key(key or label)

        submenu = QMenu(str(label or ""), target_menu)
        submenu.setStyle(self._menu_icon_style)
        submenu.setWindowFlags(
            submenu.windowFlags() | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint
        )
        submenu.setAttribute(Qt.WA_TranslucentBackground, True)
        resolved_icon = self._resolve_menu_item_icon(icon)

        reference = self._resolve_action(before)
        if reference is not None:
            target_menu.insertMenu(reference, submenu)
        else:
            target_menu.addMenu(submenu)

        if isinstance(resolved_icon, QIcon) and not resolved_icon.isNull():
            submenu.setIcon(resolved_icon)

        if menu_key:
            self._menus[menu_key] = submenu
            self._actions[menu_key] = submenu.menuAction()

        if isinstance(items, dict):
            self._add_items(submenu, items)

        return submenu

    def update_label(self, key_or_action: Union[str, QAction], new_label: str) -> Optional[QAction]:
        action = self._resolve_action(key_or_action)

        if action is None:
            return None

        old_key = self._find_action_key(action)
        new_key = self._normalize_key(new_label)

        action.setText(str(new_label or ""))

        if old_key:
            self._actions.pop(old_key, None)

        if new_key:
            self._actions[new_key] = action

        return action

    def set_visible(self, key_or_action: Union[str, QAction], visible: bool) -> Optional[QAction]:
        action = self._resolve_action(key_or_action)

        if action is not None:
            action.setVisible(bool(visible))

        return action

    def show_action(self, key_or_action: Union[str, QAction]) -> Optional[QAction]:
        return self.set_visible(key_or_action, True)

    def hide_action(self, key_or_action: Union[str, QAction]) -> Optional[QAction]:
        return self.set_visible(key_or_action, False)

    def set_enabled(self, key_or_action: Union[str, QAction], enabled: bool) -> Optional[QAction]:
        action = self._resolve_action(key_or_action)

        if action is not None:
            action.setEnabled(bool(enabled))

        return action

    def enable_action(self, key_or_action: Union[str, QAction]) -> Optional[QAction]:
        return self.set_enabled(key_or_action, True)

    def disable_action(self, key_or_action: Union[str, QAction]) -> Optional[QAction]:
        return self.set_enabled(key_or_action, False)

    def remove_action(self, key_or_action: Union[str, QAction]) -> Optional[QAction]:
        action = self._resolve_action(key_or_action)

        if action is None:
            return None

        parent = action.parent()

        if isinstance(parent, QMenu):
            parent.removeAction(action)
        else:
            self._menu.removeAction(action)

        action_key = self._find_action_key(action)

        if action_key:
            self._actions.pop(action_key, None)
            self._menus.pop(action_key, None)

        return action

    def get_action(self, key: str) -> Optional[QAction]:
        return self._actions.get(self._normalize_key(key))

    def get_menu(self, key: str) -> Optional[QMenu]:
        return self._menus.get(self._normalize_key(key))

    def refresh_theme(self) -> None:
        self._apply_menu_theme()
        self._refresh_action_icons()

    def show_menu(self) -> None:
        self.refresh_theme()
        self._menu.exec(QCursor.pos())

    def toggle_parent(self) -> None:
        if self.parent is None:
            return

        try:
            if self.parent.isVisible():
                self.parent.hide()
            else:
                self.parent.show()
                self.parent.raise_()
                self.parent.activateWindow()
        except Exception:
            pass

    def _get_theme_name(self):
        parent = self.parent

        config_manager = getattr(parent, "config_manager", None)
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

        active_theme = getattr(parent, "active_theme", None)
        if isinstance(active_theme, dict):
            meta = active_theme.get("meta", {})
            theme_name = meta.get("id")
            if theme_name:
                return theme_name

        theme_name = getattr(parent, "theme_name", None)
        if theme_name:
            return theme_name

        theme_name = getattr(parent, "current_theme", None)
        if theme_name:
            return theme_name

        return "dark"

    def _get_theme_colors(self):
        menu_theme = Theme.get_menu()
        dialog_theme = Theme.get_dialog()
        dock_theme = Theme.get_dock()
        normal_button = Theme.get_button(Theme.BUTTON_NORMAL)
        text_theme = Theme.get_text(Theme.TEXT_NORMAL)

        text_color = (
            menu_theme.get("text_color")
            or text_theme.get("color")
            or "#ffffff"
        )

        disabled_text = Theme.get_text_color(Theme.TEXT_MUTED) or text_color

        try:
            text_qcolor = Theme.to_ui_qcolor(text_color)
            if text_qcolor.isValid():
                if (
                    (text_qcolor.red() * 299)
                    + (text_qcolor.green() * 587)
                    + (text_qcolor.blue() * 114)
                ) / 1000 < 140:
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

        item_hover = (
            menu_theme.get("hover_color")
            or normal_button.get("hover_color")
            or "#3a3a3a"
        )

        item_pressed = (
            normal_button.get("pressed_color")
            or item_hover
            or "#454545"
        )

        return {
            "menu_background": menu_background,
            "item_hover": item_hover,
            "item_pressed": item_pressed,
            "text_color": text_color,
            "separator_color": separator_color,
            "disabled_text": disabled_text,
            "border_radius": border_radius,
        }

    def _apply_menu_theme(self) -> None:
        try:
            Theme.get_theme(self._get_theme_name())
        except Exception:
            pass

        colors = self._get_theme_colors()

        menu_background = Theme.to_ui_color(colors["menu_background"])
        item_hover = Theme.to_ui_color(colors["item_hover"])
        item_pressed = Theme.to_ui_color(colors["item_pressed"])
        text_color = Theme.to_ui_color(colors["text_color"])
        separator_color = Theme.to_ui_color(colors["separator_color"])
        disabled_text = Theme.to_ui_color(colors["disabled_text"])
        border_radius = colors["border_radius"]

        stylesheet = f"""
            QMenu {{
                background-color: {menu_background};
                color: {text_color};
                border: 0px;
                border-radius: {border_radius}px;
                padding: 12px;
                margin: 0px;
            }}
            QMenu::item {{
                min-width: 170px;
                padding: 6px 12px 6px 12px;
                border: 0px;
                border-radius: 6px;
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
                margin: 4px 6px;
            }}
            QMenu::icon {{
                left: 4px;
                width: {self._menu_icon_size}px;
                height: {self._menu_icon_size}px;
            }}
            QMenu::right-arrow {{
                width: {self._submenu_arrow_size}px;
                height: {self._submenu_arrow_size}px;
                margin-right: 12px;
            }}
        """

        self._menu.setStyleSheet(stylesheet)

        for submenu in self._menus.values():
            submenu.setStyle(self._menu_icon_style)
            submenu.setStyleSheet(stylesheet)

    def _create_material_icon(self, icon_name, size=None, color=None):
        glyph = MaterialIcons.get(icon_name)
        if not glyph:
            return QIcon()

        icon_size = int(size or self._menu_icon_size)
        icon_color = color or self._get_menu_icon_color()

        pixmap = QPixmap(icon_size, icon_size)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        painter.setPen(icon_color)

        font = QFont(MaterialIcons.font_family())
        font.setPixelSize(icon_size - 1)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignCenter, glyph)
        painter.end()

        return QIcon(pixmap)

    def _get_menu_icon_color(self):
        colors = self._get_theme_colors()
        return Theme.to_ui_qcolor(colors["text_color"])

    def _resolve_menu_item_icon(self, icon: Optional[Union[QIcon, str]]) -> QIcon:
        if isinstance(icon, QIcon):
            return icon

        if isinstance(icon, str) and icon.strip():
            icon_name = icon.strip()

            file_icon = QIcon(icon_name)
            if not file_icon.isNull():
                return file_icon

            return self._create_material_icon(icon_name)

        return QIcon()

    def _refresh_action_icons(self) -> None:
        for action in self._actions.values():
            icon_data = action.data()

            if isinstance(icon_data, dict) and icon_data.get("material_icon"):
                action.setIcon(self._create_material_icon(icon_data["material_icon"]))

    def _add_items(self, menu: QMenu, data: Dict[str, MenuValue]) -> None:
        for label, value in data.items():
            key = self._normalize_key(label)

            if self._is_separator(label, value):
                self.add_separator(menu=menu)
                continue

            if isinstance(value, dict):
                item_type = str(value.get("type", "")).strip().lower()

                if item_type == "separator":
                    self.add_separator(menu=menu)
                    continue

                if item_type == "menu":
                    title = str(value.get("label") or value.get("title") or label)
                    children = value.get("items", {})
                    submenu = self.add_menu(
                        title,
                        children if isinstance(children, dict) else {},
                        key=key,
                        menu=menu,
                        icon=value.get("icon"),
                    )
                    submenu.setStyleSheet(self._menu.styleSheet())
                    continue

                callback = value.get("action") or value.get("callback")
                title = str(value.get("label") or value.get("title") or label)
                enabled = bool(value.get("enabled", True))
                visible = bool(value.get("visible", True))
                icon = value.get("icon")

                action = self.add_action(
                    title,
                    callback=callback if callable(callback) else None,
                    key=key,
                    menu=menu,
                    enabled=enabled,
                    visible=visible,
                    icon=icon,
                )

                if isinstance(icon, str) and icon.strip():
                    action.setData({"material_icon": icon.strip()})

                continue

            self.add_action(str(label), callback=value if callable(value) else None, key=key, menu=menu)

    def _resolve_icon(self, icon: Optional[QIcon]) -> QIcon:
        if isinstance(icon, QIcon) and not icon.isNull():
            return icon

        for path in self._candidate_icon_paths():
            qicon = QIcon(path)
            if not qicon.isNull():
                return qicon

        try:
            app_icon = self.app.windowIcon()
            if isinstance(app_icon, QIcon) and not app_icon.isNull():
                return app_icon
        except Exception:
            pass

        try:
            if self.parent is not None:
                parent_icon = self.parent.windowIcon()
                if isinstance(parent_icon, QIcon) and not parent_icon.isNull():
                    return parent_icon
        except Exception:
            pass

        return QIcon()

    def _candidate_icon_paths(self):
        base_dir = Path(__file__).resolve().parents[2]
        candidates = [
            base_dir / "assets" / "icon.png",
            base_dir / "assets" / "main.png",
        ]

        for candidate in candidates:
            if candidate.exists():
                yield str(candidate)

    def _ensure_icon(self) -> None:
        if self._tray.icon().isNull():
            self._tray.setIcon(self._resolve_icon(None))

    def _resolve_action(self, key_or_action: Optional[Union[str, QAction]]) -> Optional[QAction]:
        if isinstance(key_or_action, QAction):
            return key_or_action

        if key_or_action is None:
            return None

        return self._actions.get(self._normalize_key(key_or_action))

    def _find_action_key(self, action: QAction) -> Optional[str]:
        for key, stored_action in self._actions.items():
            if stored_action is action:
                return key

        return None

    def _normalize_key(self, value: Any) -> str:
        return str(value or "").strip()

    def _is_separator(self, label: Any, value: Any) -> bool:
        key = self._normalize_key(label).lower()
        return key in {"-", "--", "---", "separator"} or value == "-"

    def _call_callback(self, callback: Callable, action: QAction) -> None:
        try:
            callback(action, self)
            return
        except TypeError:
            pass

        try:
            callback(action)
            return
        except TypeError:
            pass

        try:
            callback(self)
            return
        except TypeError:
            pass

        callback()

    @Slot(QSystemTrayIcon.ActivationReason)
    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        self.activated.emit(reason)

        if reason == QSystemTrayIcon.Trigger:
            self.toggle_parent()
        elif reason == QSystemTrayIcon.Context:
            self.show_menu()


__all__ = ["TrayManager"]
