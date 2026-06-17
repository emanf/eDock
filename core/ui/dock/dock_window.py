import json
from enum import Enum
from PySide6.QtCore import (
    Qt,
    QRectF,
    QTimer,
    QPropertyAnimation,
    QEasingCurve,
    QPoint,
    Signal,
    QEvent,
)
from PySide6.QtGui import QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QBoxLayout, QScrollArea, QVBoxLayout, QWidget

from core.ui.widget import eD_Widget
from core.ui.tooltip import eD_Tooltip
from core.ui.dock.dock_button import DockButton
from core.paths import get_user_dir, get_user_config_path
from core.theming.theme_manager import Theme, build_default_config
from core.services.app_runtime_service import AppRuntimeService
from core.ui.dock.dock_window_geometry import (
    current_screen_geometry,
    max_dock_length,
    dock_size_for_icon_size,
    update_effective_icon_size,
    apply_button_sizes,
    update_dock_geometry,
    reposition_dock,
)
from core.services.shortcut_service import ShortcutService


class ResizeMode(str, Enum):
    RESIZABLE_BUTTON = "resizable-button"
    SCROLLABLE = "scroll-able"

    @classmethod
    def from_value(cls, value):
        try:
            return cls(value)
        except ValueError:
            return cls.RESIZABLE_BUTTON


class DockWindow(eD_Widget):
    shortcut_launch_requested = Signal(object)

    def __init__(
        self, config_manager=None, app_loader=None, app=None, context=None, parent=None
    ):
        super().__init__(app=app, context=context, parent=parent)

        self.config_manager = config_manager
        self.app_loader = app_loader
        self.loaded_apps = []
        self.buttons = []
        self._launch_in_progress = set()

        self.shortcut_launch_requested.connect(
            self._handle_shortcut_launch, Qt.QueuedConnection
        )

        try:
            self.shortcut_service = ShortcutService(self.shortcut_launch_requested.emit)
        except Exception:
            self.shortcut_service = None

        self.app_api = context
        self.context = {
            "config_manager": self.config_manager,
            "app_loader": self.app_loader,
            "dock": self,
        }

        if self.app_api is not None:
            try:
                if hasattr(self.app_api, "set_dock"):
                    self.app_api.set_dock(self)
                else:
                    self.app_api.dock = self
            except Exception:
                pass

        self.runtime_service = AppRuntimeService(
            self.app_api if self.app_api is not None else self.context
        )
        self.context["runtime_service"] = self.runtime_service

        if self.app_loader is not None and self.app_api is not None:
            try:
                self.app_loader.app_context = self.app_api
            except Exception:
                pass

        self.min_dock_width = 84
        self.min_dock_height = 96

        self.dock_position = "right"
        self.peek_width = 20
        self.edge_guard = 4
        self.hover_visible = False

        self.shown_pos = QPoint()
        self.hidden_pos = QPoint()

        self.inner_padding = 12
        self.spacing = 10
        self.icon_size = 56
        self.effective_icon_size = 56
        self.icon_padding = 20
        self.corner_radius = 28
        self.dock_border_width = 1.2
        self.resize_mode = ResizeMode.RESIZABLE_BUTTON
        self.button_min_size = 24
        self.button_max_size = 64
        self.scroll_enabled = False

        self.drag_scroll_pressed = False
        self.drag_scroll_active = False
        self.drag_scroll_start_pos = QPoint()
        self.drag_scroll_start_h = 0
        self.drag_scroll_start_v = 0
        self.drag_scroll_threshold = 4

        self.tooltip_widget = eD_Tooltip(
            app=self.app, context=self.context, parent=None
        )
        self.tooltip_hide_timer = QTimer(self)
        self.tooltip_hide_timer.setSingleShot(True)
        self.tooltip_hide_timer.timeout.connect(self.tooltip_widget.hide)

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)
        self.setStyleSheet("background: transparent;")

        self.slide_anim = QPropertyAnimation(self, b"pos")
        self.slide_anim.setDuration(250)
        self.slide_anim.setEasingCurve(QEasingCurve.OutCubic)

        self.hover_timer = QTimer(self)
        self.hover_timer.setSingleShot(True)
        self.hover_timer.timeout.connect(self.animate_hide)

        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setFrameShape(QScrollArea.NoFrame)
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")
        self.scroll_area.viewport().setStyleSheet("background: transparent;")
        self.scroll_area.setAttribute(Qt.WA_TranslucentBackground, True)
        self.scroll_area.viewport().setAttribute(Qt.WA_TranslucentBackground, True)
        self.scroll_area.viewport().installEventFilter(self)

        self.content_widget = QWidget()
        self.content_widget.setAttribute(Qt.WA_TranslucentBackground, True)
        self.content_widget.setStyleSheet("background: transparent;")
        self.content_widget.installEventFilter(self)

        self.main_layout = QBoxLayout(QBoxLayout.TopToBottom, self.content_widget)
        self.main_layout.setAlignment(Qt.AlignCenter)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area.setWidget(self.content_widget)
        self.root_layout.addWidget(self.scroll_area)

        self.ensure_default_config()
        self.load_settings()
        self.load_apps()
        self.build_buttons()
        self.register_all_shortcuts()
        self.update_dock_geometry()

    def apply_theme(self):
        self.load_settings()
        if self.tooltip_widget is not None:
            self.tooltip_widget.apply_theme()
        self.notify_apps_theme_changed()
        self.update()

    def notify_apps_theme_changed(self):
        runtime_service = (
            self.context.get("runtime_service")
            if isinstance(self.context, dict)
            else None
        )
        if runtime_service is not None and hasattr(
            runtime_service, "broadcast_theme_changed"
        ):
            try:
                runtime_service.broadcast_theme_changed()
            except Exception:
                pass

    def event_global_pos(self, event):
        if hasattr(event, "globalPosition"):
            return event.globalPosition().toPoint()
        if hasattr(event, "globalPos"):
            return event.globalPos()
        return QPoint()

    def eventFilter(self, source, event):
        if isinstance(source, DockButton):
            if event.type() == QEvent.ToolTip:
                return True

            if event.type() == QEvent.Enter:
                self.show_custom_tooltip(source)
                return False

            if event.type() == QEvent.Leave:
                self.tooltip_hide_timer.start(50)
                return False

            if event.type() == QEvent.MouseMove:
                if source.underMouse():
                    self.show_custom_tooltip(source)
                return False

        if not self.scroll_enabled:
            return super().eventFilter(source, event)

        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            if source is self.scroll_area.viewport() or source is self.content_widget:
                self.drag_scroll_pressed = True
                self.drag_scroll_active = False
                self.drag_scroll_start_pos = self.event_global_pos(event)
                self.drag_scroll_start_h = (
                    self.scroll_area.horizontalScrollBar().value()
                )
                self.drag_scroll_start_v = self.scroll_area.verticalScrollBar().value()
                return False

        if event.type() == QEvent.MouseMove and self.drag_scroll_pressed:
            current_pos = self.event_global_pos(event)
            delta = current_pos - self.drag_scroll_start_pos

            if not self.drag_scroll_active:
                if (
                    abs(delta.x()) >= self.drag_scroll_threshold
                    or abs(delta.y()) >= self.drag_scroll_threshold
                ):
                    self.drag_scroll_active = True
                    self.scroll_area.viewport().setCursor(Qt.ClosedHandCursor)
                    self.content_widget.setCursor(Qt.ClosedHandCursor)

            if self.drag_scroll_active:
                if self.dock_position in ("top", "bottom"):
                    bar = self.scroll_area.horizontalScrollBar()
                    bar.setValue(self.drag_scroll_start_h - delta.x())
                else:
                    bar = self.scroll_area.verticalScrollBar()
                    bar.setValue(self.drag_scroll_start_v - delta.y())
                return True

        if (
            event.type() == QEvent.MouseButtonRelease
            and event.button() == Qt.LeftButton
        ):
            was_dragging = self.drag_scroll_active
            self.drag_scroll_pressed = False
            self.drag_scroll_active = False
            self.scroll_area.viewport().unsetCursor()
            self.content_widget.unsetCursor()
            if was_dragging and (
                source is self.scroll_area.viewport() or source is self.content_widget
            ):
                return True

        if event.type() == QEvent.Wheel:
            delta = event.angleDelta()
            pixel_delta = event.pixelDelta()

            if self.dock_position in ("top", "bottom"):
                bar = self.scroll_area.horizontalScrollBar()
                amount = pixel_delta.x() or pixel_delta.y() or delta.x() or delta.y()

                if amount:
                    bar.setValue(bar.value() - amount)
                    return True
            else:
                bar = self.scroll_area.verticalScrollBar()
                amount = pixel_delta.y() or delta.y()

                if amount:
                    bar.setValue(bar.value() - amount)
                    return True

        return super().eventFilter(source, event)

    def _config_data(self):
        if self.config_manager is None:
            return None

        if hasattr(self.config_manager, "config") and isinstance(
            self.config_manager.config, dict
        ):
            return self.config_manager.config

        if hasattr(self.config_manager, "data") and isinstance(
            self.config_manager.data, dict
        ):
            return self.config_manager.data

        return None

    def _config_get_nested(self, path, default=None):
        data = self._config_data()
        if not isinstance(data, dict):
            return default

        current = data
        for part in str(path).split("."):
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]

        return current

    def _config_get(self, key, default=None):
        value = self._config_get_nested(key, None)
        if value is not None:
            return value

        if self.config_manager is None:
            return default

        if hasattr(self.config_manager, "get"):
            try:
                return self.config_manager.get(key, default)
            except Exception:
                return default

        return default

    def config_file_path(self):
        return get_user_config_path()

    def user_dir(self):
        return get_user_dir()

    def ensure_default_config(self):
        user_dir = self.user_dir()
        config_path = self.config_file_path()

        user_dir.mkdir(parents=True, exist_ok=True)

        default_config = build_default_config()

        if not config_path.exists():
            if "dock" not in default_config or not isinstance(
                default_config["dock"], dict
            ):
                default_config["dock"] = {}

            default_config["dock"].setdefault(
                "resize-mode", ResizeMode.RESIZABLE_BUTTON
            )
            default_config["dock"].setdefault("button-min-size", 24)
            default_config["dock"].setdefault("button-max-size", 64)

            config_path.write_text(
                json.dumps(default_config, indent=4, ensure_ascii=False),
                encoding="utf-8",
            )
        else:
            try:
                current_data = json.loads(config_path.read_text(encoding="utf-8"))
                if not isinstance(current_data, dict):
                    current_data = {}
            except Exception:
                current_data = {}

            repaired = False

            if "theme" not in current_data:
                current_data["theme"] = default_config.get("theme", "dark")
                repaired = True

            if "dock" not in current_data or not isinstance(current_data["dock"], dict):
                current_data["dock"] = default_config.get("dock", {})
                repaired = True

            if "dock" not in current_data or not isinstance(current_data["dock"], dict):
                current_data["dock"] = {}
                repaired = True

            if "resize-mode" not in current_data["dock"]:
                current_data["dock"]["resize-mode"] = ResizeMode.RESIZABLE_BUTTON
                repaired = True

            if "button-min-size" not in current_data["dock"]:
                current_data["dock"]["button-min-size"] = 24
                repaired = True

            if "button-max-size" not in current_data["dock"]:
                current_data["dock"]["button-max-size"] = 64
                repaired = True

            if "themes" in current_data:
                current_data.pop("themes", None)
                repaired = True

            if "pinned_apps" in current_data:
                current_data.pop("pinned_apps", None)
                repaired = True

            if (
                "apps" not in current_data
                or not isinstance(current_data["apps"], dict)
                or not current_data["apps"]
            ):
                current_data["apps"] = default_config.get("apps", {})
                repaired = True

            if repaired:
                config_path.write_text(
                    json.dumps(current_data, indent=4, ensure_ascii=False),
                    encoding="utf-8",
                )

        if self.config_manager is not None and hasattr(self.config_manager, "load"):
            try:
                self.config_manager.load()
            except Exception:
                pass

    def apply_tooltip_style(self):
        if self.tooltip_widget is not None:
            self.tooltip_widget.apply_theme()

    def show_custom_tooltip(self, button):
        self.tooltip_hide_timer.stop()

        text = button.toolTip()
        if not text:
            self.tooltip_widget.hide()
            return

        self.tooltip_widget.set_text(text)
        self.tooltip_widget.apply_theme()
        self.tooltip_widget.adjustSize()

        button_rect = button.rect()
        global_center = button.mapToGlobal(button_rect.center())

        margin = 10
        x = global_center.x() - self.tooltip_widget.width() // 2
        y = global_center.y() - self.tooltip_widget.height() // 2

        if self.dock_position == "left":
            x = button.mapToGlobal(button.rect().topRight()).x() + margin
            y = global_center.y() - self.tooltip_widget.height() // 2
        elif self.dock_position == "right":
            x = (
                button.mapToGlobal(button.rect().topLeft()).x()
                - self.tooltip_widget.width()
                - margin
            )
            y = global_center.y() - self.tooltip_widget.height() // 2
        elif self.dock_position == "top":
            x = global_center.x() - self.tooltip_widget.width() // 2
            y = button.mapToGlobal(button.rect().bottomLeft()).y() + margin
        elif self.dock_position == "bottom":
            x = global_center.x() - self.tooltip_widget.width() // 2
            y = (
                button.mapToGlobal(button.rect().topLeft()).y()
                - self.tooltip_widget.height()
                - margin
            )

        self.tooltip_widget.move(x, y)
        self.tooltip_widget.clamp_to_screen()
        self.tooltip_widget.show()
        self.tooltip_widget.raise_()

    def update_layout_direction(self):
        if self.dock_position in ("top", "bottom"):
            self.main_layout.setDirection(QBoxLayout.LeftToRight)
        else:
            self.main_layout.setDirection(QBoxLayout.TopToBottom)

    def load_settings(self):
        dock_theme = Theme.get_dock()
        icon_theme = Theme.get_icon(Theme.ICON_NORMAL)
        sizes = Theme.get_sizes()

        self.spacing = int(sizes.get(Theme.Sizes.Space.SM, 10))
        self.inner_padding = int(sizes.get(Theme.Sizes.Space.MD, 12))
        self.icon_size = int(icon_theme.get(Theme.Components.Icon.SIZE, 64))
        self.effective_icon_size = self.icon_size
        self.icon_padding = int(icon_theme.get(Theme.Components.Icon.PADDING, 20))
        self.corner_radius = int(
            dock_theme.get(Theme.Components.Dock.BORDER_RADIUS, 28)
        )
        self.dock_border_width = float(
            dock_theme.get(Theme.Components.Dock.BORDER_WIDTH, 1.2)
        )
        self.dock_position = str(self._config_get("dock.position", "right")).lower()

        resize_mode = ResizeMode.from_value(self._config_get("dock.resize-mode"))
        self.resize_mode = resize_mode

        try:
            self.button_min_size = int(self._config_get("dock.button-min-size", 24))
        except Exception:
            self.button_min_size = 24

        try:
            self.button_max_size = int(self._config_get("dock.button-max-size", 64))
        except Exception:
            self.button_max_size = 64

        self.button_min_size = max(12, self.button_min_size)
        self.button_max_size = max(self.button_min_size, self.button_max_size)
        self.icon_size = min(
            max(self.icon_size, self.button_min_size), self.button_max_size
        )
        self.effective_icon_size = self.icon_size

        self.update_layout_direction()

        self.main_layout.setContentsMargins(
            self.inner_padding,
            self.inner_padding,
            self.inner_padding,
            self.inner_padding,
        )
        self.main_layout.setSpacing(self.spacing)
        self.apply_tooltip_style()

    def get_dock_colors(self):
        dock_theme = Theme.get_dock()

        bg = Theme.to_ui_qcolor(dock_theme.get("background_color"))
        border = Theme.to_ui_qcolor(dock_theme.get("border_color"))

        return bg, border

    def available_app_ids(self):
        if self.app_loader is None:
            return []

        try:
            apps = self.app_loader.load_apps()
        except Exception:
            return []

        return [
            str(app.get("id", "")).strip()
            for app in apps
            if str(app.get("id", "")).strip()
        ]

    def default_app_id(self):
        app_ids = self.available_app_ids()
        if "emanf.spotlight" in app_ids:
            return "emanf.spotlight"
        if app_ids:
            return app_ids[0]
        return "emanf.spotlight"

    def get_app_id(self, app_data):
        return str(app_data.get("id", "")).strip()

    def get_app_config(self, app_id):
        value = self._config_get(f"apps.{app_id}", {})
        return value if isinstance(value, dict) else {}

    def is_app_enabled(self, app_data):
        app_id = self.get_app_id(app_data)
        if not app_id:
            return False

        app_config = self.get_app_config(app_id)
        enabled_value = app_config.get("enabled", None)
        if enabled_value is not None:
            return bool(enabled_value)

        return bool(app_data.get("enabled", True))

    def get_app_shortcut(self, app_data):
        app_id = self.get_app_id(app_data)
        app_config = self.get_app_config(app_id)
        shortcut_value = app_config.get("shortcut", None)
        if shortcut_value is not None:
            return shortcut_value
        return app_data.get("shortcut", "")

    def get_app_sort(self, app_data):
        app_id = self.get_app_id(app_data)
        app_config = self.get_app_config(app_id)
        sort_value = app_config.get("sort", None)

        try:
            return int(sort_value)
        except Exception:
            return 0

    def load_apps(self):
        if self.app_loader is None:
            self.loaded_apps = []
            return

        try:
            self.loaded_apps = self.app_loader.load_apps()
        except Exception:
            self.loaded_apps = []

    def reload_apps(self):
        self.unregister_all_shortcuts()
        old_ids = [
            str(a.get("id", "")).strip()
            for a in (self.loaded_apps or [])
            if str(a.get("id", "")).strip()
        ]
        self.ensure_default_config()
        self.load_settings()
        self.load_apps()

        new_ids = [
            str(a.get("id", "")).strip()
            for a in (self.loaded_apps or [])
            if str(a.get("id", "")).strip()
        ]
        removed_ids = [rid for rid in old_ids if rid and rid not in new_ids]

        if (
            removed_ids
            and hasattr(self, "runtime_service")
            and self.runtime_service is not None
        ):
            for rid in removed_ids:
                try:
                    instance_ids = getattr(
                        self.runtime_service, "instance_ids_by_app", {}
                    ).get(rid, [])
                    if instance_ids:
                        continue

                    if hasattr(self.runtime_service, "unload_app"):
                        self.runtime_service.unload_app(rid)
                except Exception:
                    pass
        self.build_buttons()
        self.register_all_shortcuts()
        self.update_dock_geometry()
        self.update()

    def clear_layout(self):
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.buttons = []

    def call_unload_all(self):
        if hasattr(self, "runtime_service") and self.runtime_service is not None:
            self.runtime_service.unload_all()

    def build_buttons(self):
        self.clear_layout()
        self.update_effective_icon_size()

        self.loaded_apps = [
            app_data for app_data in self.loaded_apps if self.is_app_enabled(app_data)
        ]

        for app_data in self.loaded_apps:
            button = self.create_button(app_data)
            self.buttons.append(button)
            self.main_layout.addWidget(button, 0, Qt.AlignCenter)

        self.update_dock_geometry()

    def create_button(self, app_data):
        button = DockButton(
            icon_value=app_data.get("icon", ""),
            app_dir=app_data.get("folder_path") or app_data.get("app_dir"),
            icon_size=self.effective_icon_size,
            icon_padding=self.icon_padding,
            on_click=self.make_launch_handler(app_data),
            parent=self.content_widget,
        )

        button.set_loaded_app(app_data)
        button.set_dock_window(self)
        button.set_shortcut(self.get_app_shortcut(app_data))
        button.setToolTip(app_data.get("title", app_data.get("id", "App")))

        instance = None
        if hasattr(self, "runtime_service") and self.runtime_service is not None:
            instance = self.runtime_service.get_instance(app_data)
        button.set_app_instance(instance)

        button.installEventFilter(self)
        return button

    def make_launch_handler(self, app_data):
        return lambda: self.launch_app(app_data)

    def _handle_shortcut_launch(self, app_data):
        self.launch_app(app_data)

    def launch_app(self, app_data):
        if not app_data:
            return
        app_id = self.get_app_id(app_data)
        if app_id and app_id in self._launch_in_progress:
            return

        if app_id:
            self._launch_in_progress.add(app_id)

        try:
            instance = None
            if hasattr(self, "runtime_service") and self.runtime_service is not None:
                if self.app_api is not None:
                    instance = self.app_api.safe_app_call(
                        None,
                        "runtime_service.launch",
                        lambda: self.runtime_service.launch(app_data),
                        default=None,
                    )
                else:
                    try:
                        instance = self.runtime_service.launch(app_data)
                    except Exception:
                        instance = None

            if instance is not None:
                self._sync_button_instance(app_id, app_data, instance)
        finally:
            if app_id:
                self._launch_in_progress.discard(app_id)

    def _sync_button_instance(self, app_id, app_data, instance):
        if not instance:
            return

        for button in self.buttons:
            loaded = getattr(button, "loaded_app", None)
            if not isinstance(loaded, dict):
                continue

            loaded_id = self.get_app_id(loaded)
            if loaded_id != app_id:
                continue

            if self.app_api is not None:
                allow_multi = self.app_api.safe_app_call(
                    instance,
                    "allow_multiple_instance",
                    lambda: (
                        bool(instance.allow_multiple_instance())
                        if hasattr(instance, "allow_multiple_instance")
                        else False
                    ),
                    default=False,
                )
            else:
                try:
                    allow_multi = (
                        bool(instance.allow_multiple_instance())
                        if hasattr(instance, "allow_multiple_instance")
                        else False
                    )
                except Exception:
                    allow_multi = False

            if not allow_multi:
                button.set_app_instance(instance)
            break

    def refresh_shortcuts(self):
        self.load_apps()

        for button in self.buttons:
            app_data = getattr(button, "loaded_app", None)
            if not isinstance(app_data, dict):
                continue

            app_id = self.get_app_id(app_data)
            if not app_id:
                continue

            updated_shortcut = self.get_app_shortcut(app_data)
            app_data["shortcut"] = updated_shortcut
            button.set_shortcut(updated_shortcut)

        self.register_all_shortcuts()

    def normalize_shortcut_for_keyboard(self, shortcut):
        if self.shortcut_service is None:
            return ""
        return self.shortcut_service.normalize(shortcut)

    def register_all_shortcuts(self):
        if self.shortcut_service is None:
            return
        try:
            self.shortcut_service.register_apps(self.loaded_apps)
        except Exception:
            pass

    def register_shortcut(self, app_id, shortcut, app_data):
        if self.shortcut_service is None:
            return
        try:
            self.shortcut_service.register(app_id, shortcut, app_data)
        except Exception:
            pass

    def unregister_shortcut(self, app_id):
        if self.shortcut_service is None:
            return
        try:
            self.shortcut_service.unregister(app_id)
        except Exception:
            pass

    def unregister_all_shortcuts(self):
        if self.shortcut_service is None:
            return
        try:
            self.shortcut_service.unregister_all()
        except Exception:
            pass

    def current_screen_geometry(self):
        return current_screen_geometry(self)

    def max_dock_length(self):
        return max_dock_length(self)

    def dock_size_for_icon_size(self, icon_size):
        return dock_size_for_icon_size(self, icon_size)

    def update_effective_icon_size(self):
        return update_effective_icon_size(self)

    def apply_button_sizes(self):
        return apply_button_sizes(self)

    def update_dock_geometry(self):
        return update_dock_geometry(self)

    def reposition_dock(self):
        return reposition_dock(self)

    def animate_to(self, pos):
        self.slide_anim.stop()
        self.slide_anim.setStartValue(self.pos())
        self.slide_anim.setEndValue(pos)
        self.slide_anim.start()

    def animate_hide(self):
        if not self.hover_visible:
            self.animate_to(self.hidden_pos)

    def enterEvent(self, event):
        self.hover_visible = True
        self.hover_timer.stop()
        self.animate_to(self.shown_pos)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hover_visible = False
        self.hover_timer.start(150)
        self.tooltip_widget.hide()
        super().leaveEvent(event)

    def dock_path(self):
        rect = QRectF(0.5, 0.5, self.width() - 1.0, self.height() - 1.0)
        radius = float(self.corner_radius)

        path = QPainterPath()

        if self.dock_position == "left":
            path.moveTo(rect.left(), rect.top())
            path.lineTo(rect.right() - radius, rect.top())
            path.quadTo(rect.right(), rect.top(), rect.right(), rect.top() + radius)
            path.lineTo(rect.right(), rect.bottom() - radius)
            path.quadTo(
                rect.right(), rect.bottom(), rect.right() - radius, rect.bottom()
            )
            path.lineTo(rect.left(), rect.bottom())
            path.closeSubpath()

        elif self.dock_position == "right":
            path.moveTo(rect.left() + radius, rect.top())
            path.lineTo(rect.right(), rect.top())
            path.lineTo(rect.right(), rect.bottom())
            path.lineTo(rect.left() + radius, rect.bottom())
            path.quadTo(rect.left(), rect.bottom(), rect.left(), rect.bottom() - radius)
            path.lineTo(rect.left(), rect.top() + radius)
            path.quadTo(rect.left(), rect.top(), rect.left() + radius, rect.top())
            path.closeSubpath()

        elif self.dock_position == "top":
            path.moveTo(rect.left(), rect.top())
            path.lineTo(rect.right(), rect.top())
            path.lineTo(rect.right(), rect.bottom() - radius)
            path.quadTo(
                rect.right(), rect.bottom(), rect.right() - radius, rect.bottom()
            )
            path.lineTo(rect.left() + radius, rect.bottom())
            path.quadTo(rect.left(), rect.bottom(), rect.left(), rect.bottom() - radius)
            path.lineTo(rect.left(), rect.top())
            path.closeSubpath()

        elif self.dock_position == "bottom":
            path.moveTo(rect.left() + radius, rect.top())
            path.quadTo(rect.left(), rect.top(), rect.left(), rect.top() + radius)
            path.lineTo(rect.left(), rect.bottom())
            path.lineTo(rect.right(), rect.bottom())
            path.lineTo(rect.right(), rect.top() + radius)
            path.quadTo(rect.right(), rect.top(), rect.right() - radius, rect.top())
            path.lineTo(rect.left() + radius, rect.top())
            path.closeSubpath()

        else:
            path.moveTo(rect.left() + radius, rect.top())
            path.lineTo(rect.right(), rect.top())
            path.lineTo(rect.right(), rect.bottom())
            path.lineTo(rect.left() + radius, rect.bottom())
            path.quadTo(rect.left(), rect.bottom(), rect.left(), rect.bottom() - radius)
            path.lineTo(rect.left(), rect.top() + radius)
            path.quadTo(rect.left(), rect.top(), rect.left() + radius, rect.top())
            path.closeSubpath()

        return path

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(Qt.NoBrush)

        bg, border = self.get_dock_colors()
        path = self.dock_path()

        painter.fillPath(path, bg)
        painter.setPen(QPen(border, self.dock_border_width))
        painter.drawPath(path)

    def showEvent(self, event):
        super().showEvent(event)
        self.update_dock_geometry()

    def closeEvent(self, event):
        self.tooltip_widget.hide()
        self.unregister_all_shortcuts()
        self.call_unload_all()
        super().closeEvent(event)

    def remove_app_button(self, button, app_id):
        if button is None:
            return

        if app_id:
            self.unregister_shortcut(app_id)

        if button in self.buttons:
            self.buttons.remove(button)

        if app_id:
            self.loaded_apps = [
                app for app in self.loaded_apps if self.get_app_id(app) != app_id
            ]

        self.main_layout.removeWidget(button)
        button.removeEventFilter(self)
        button.hide()
        button.setParent(None)

        if self.buttons:
            button.deleteLater()

        self.main_layout.invalidate()
        self.refresh_geometry_after_button_removed()

    def refresh_geometry_after_button_removed(self):
        self.update_effective_icon_size()
        self.apply_button_sizes()

        visible_buttons = [
            button
            for button in self.buttons
            if button is not None and not button.isHidden()
        ]

        real_button_count = len(visible_buttons)
        layout_button_count = max(1, real_button_count)

        if real_button_count:
            button_size = max(
                int(getattr(button, "widget_size", button.sizeHint().height()))
                for button in visible_buttons
            )
        else:
            button_size = int(self.effective_icon_size) + 12

        spacing_total = max(0, layout_button_count - 1) * int(self.spacing)
        length = (
            (int(self.inner_padding) * 2)
            + (layout_button_count * button_size)
            + spacing_total
        )
        thickness = (int(self.inner_padding) * 2) + button_size

        if self.dock_position in ("top", "bottom"):
            dock_width = max(self.min_dock_width, length)
            dock_height = max(self.min_dock_height, thickness)
            content_width = length
            content_height = thickness
        else:
            dock_width = max(self.min_dock_width, thickness)
            dock_height = max(self.min_dock_height, length)
            content_width = thickness
            content_height = length

        self.content_widget.setMinimumSize(0, 0)
        self.content_widget.setMaximumSize(16777215, 16777215)
        self.content_widget.resize(content_width, content_height)
        self.content_widget.setFixedSize(content_width, content_height)

        self.scroll_area.setMinimumSize(0, 0)
        self.scroll_area.setMaximumSize(16777215, 16777215)
        self.scroll_area.resize(dock_width, dock_height)
        self.scroll_area.setFixedSize(dock_width, dock_height)

        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)
        self.resize(dock_width, dock_height)
        self.setFixedSize(dock_width, dock_height)

        self.main_layout.invalidate()
        self.content_widget.updateGeometry()
        self.scroll_area.updateGeometry()
        self.updateGeometry()

        self.reposition_dock()
        self.update()
