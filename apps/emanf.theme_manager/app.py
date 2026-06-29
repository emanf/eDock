import json
from copy import deepcopy
from pathlib import Path
from typing import List, Optional, Tuple

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QColorDialog,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.app.app_base import AppBase
from core.rendering.material_icons import MaterialIcons
from core.theming.theme_manager import Theme, ThemeRegistry, ThemePathResolver
from core.ui.dialogs.confirm_dialog import ConfirmDialog
from core.ui.dialogs.input_dialog import InputDialog
from core.ui.dialogs.message_dialog import MessageDialog


class ThemeEntry:
    SOURCE_USER = "user"
    SOURCE_BUILTIN = "built-in"
    SOURCE_THEME_MANAGER = "theme-manager"

    def __init__(self, theme_id: str, source: str, path: Optional[Path] = None):
        self.theme_id = theme_id
        self.source_type = source
        self.path = Path(path) if path is not None else None

    @property
    def editable(self) -> bool:
        return self.source_type == self.SOURCE_USER

    @property
    def removable(self) -> bool:
        return self.source_type == self.SOURCE_USER

    @property
    def subtitle(self) -> str:
        return self.source_type

    @property
    def reference(self) -> str:
        if self.source_type == self.SOURCE_BUILTIN:
            return self.theme_id
        return str(self.path) if self.path is not None else self.theme_id

    @property
    def display_name(self) -> str:
        return str(self.theme_id)


class ThemeJsonEditor:
    @staticmethod
    def parse(text: str) -> Tuple[Optional[dict], Optional[str]]:
        text = (text or "").strip()
        if not text:
            return {}, None
        try:
            value = json.loads(text)
        except Exception as e:
            return None, str(e)
        if not isinstance(value, dict):
            return None, "Theme JSON must be a JSON object."
        return value, None

    @staticmethod
    def parse_silent(text: str) -> dict:
        v, err = ThemeJsonEditor.parse(text)
        return v or {}

    @staticmethod
    def dump(value) -> str:
        try:
            return json.dumps(value or {}, indent=4, ensure_ascii=False)
        except Exception:
            return "{}"

    @staticmethod
    def get_nested(data, path, default=None):
        cur = data
        for p in path:
            if not isinstance(cur, dict):
                return default
            cur = cur.get(p)
        return default if cur is None else cur

    @staticmethod
    def set_nested(data, path, value):
        cur = data
        for p in path[:-1]:
            if p not in cur or not isinstance(cur.get(p), dict):
                cur[p] = {}
            cur = cur[p]
        cur[path[-1]] = value


class ThemeManagerApp(AppBase):
    def on_init(self):
        self.window = None

    def on_load(self):
        self.window = ThemeManagerWindow(self)

    def on_unload(self):
        if self.window is not None:
            self.window.hide()

        self.window = None

    def run(self):
        if self.window is None:
            return

        self.window.toggle()


class ThemeManagerWindow(QDialog):
    ROLE_THEME_ID = Qt.UserRole
    ROLE_THEME_SOURCE = Qt.UserRole + 1

    def __init__(self, app):
        super().__init__()

        Theme.reload()
        MaterialIcons.ensure_font()

        self.app = app
        self.context = getattr(app, "context", {})
        self.config_manager = self._context_get("config_manager")
        self.dock = self._context_get("dock")

        self.setWindowTitle("Theme Manager")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self.setMinimumSize(760, 700)
        self.resize(820, 720)

        self.drag_position = None
        self.entries: List[ThemeEntry] = []
        self.current_theme_id = Theme.normalize_theme_id(Theme.get_current_theme_id())

        self._build_ui()
        self._reload_theme_entries()
        self._load_theme_list()
        self._select_current_theme()
        self._load_selected_theme_editor()
        self._refresh_preview()

    def toggle(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()

    def _context_get(self, key, default=None):
        if isinstance(self.context, dict):
            return self.context.get(key, default)
        return getattr(self.context, key, default)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.container = QFrame()
        self.container.setObjectName("container")
        root.addWidget(self.container)

        main = QVBoxLayout(self.container)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        self.title_bar = QFrame()
        self.title_bar.setObjectName("titleBar")
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(16, 10, 10, 8)
        title_layout.setSpacing(10)

        icon = QLabel(MaterialIcons.get("palette"))
        icon.setObjectName("materialIcon")
        icon.setFixedSize(30, 30)
        icon.setAlignment(Qt.AlignCenter)
        icon.setFont(QFont(MaterialIcons.font_family(), 21))

        title_box = QVBoxLayout()
        title_box.setContentsMargins(0, 0, 0, 0)
        title_box.setSpacing(1)

        title = QLabel("Theme Manager")
        title.setObjectName("titleLabel")
        subtitle = QLabel("Create custom themes, edit JSON, and apply them live.")
        subtitle.setObjectName("subtitleLabel")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        close_btn = QPushButton(MaterialIcons.get("close"))
        close_btn.setObjectName("closeButton")
        close_btn.setFixedSize(30, 30)
        close_btn.setFont(QFont(MaterialIcons.font_family(), 21))
        close_btn.clicked.connect(self.close)

        title_layout.addWidget(icon)
        title_layout.addLayout(title_box)
        title_layout.addStretch()
        title_layout.addWidget(close_btn)

        body = QHBoxLayout()
        body.setContentsMargins(12, 8, 12, 12)
        body.setSpacing(10)

        left_panel = QFrame()
        left_panel.setObjectName("panel")
        left_panel.setFixedWidth(220)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(8)

        self.theme_list = QListWidget()
        self.theme_list.setObjectName("themeList")
        self.theme_list.currentItemChanged.connect(self._on_theme_selected)

        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)

        self.create_btn = QPushButton("Create")
        self.create_btn.setObjectName("normalButton")
        self.create_btn.clicked.connect(self._create_theme)

        self.clone_btn = QPushButton("Clone")
        self.clone_btn.setObjectName("normalButton")
        self.clone_btn.clicked.connect(self._clone_theme)

        actions_row.addWidget(self.create_btn)
        actions_row.addWidget(self.clone_btn)

        self.remove_btn = QPushButton("Remove")
        self.remove_btn.setObjectName("warningButton")
        self.remove_btn.clicked.connect(self._remove_theme)

        left_layout.addWidget(self.theme_list)
        left_layout.addLayout(actions_row)
        left_layout.addWidget(self.remove_btn)

        right_panel = QFrame()
        right_panel.setObjectName("panel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(12, 10, 12, 10)
        right_layout.setSpacing(10)

        preview_header = QHBoxLayout()
        preview_header.setSpacing(8)
        preview_title = QLabel("Preview")
        preview_title.setObjectName("sectionTitle")
        self.active_badge = QLabel("ACTIVE")
        self.active_badge.setObjectName("badge")
        self.active_badge.setProperty("inactive", True)
        preview_header.addWidget(preview_title)
        preview_header.addStretch()
        preview_header.addWidget(self.active_badge)

        self.preview_card = QFrame()
        self.preview_card.setObjectName("previewCard")
        self.preview_card.setFixedHeight(168)
        preview_card_layout = QVBoxLayout(self.preview_card)
        preview_card_layout.setContentsMargins(12, 12, 12, 12)
        preview_card_layout.setSpacing(0)

        self.preview_dock = QFrame()
        self.preview_dock.setObjectName("previewDock")
        self.preview_dock.setFixedHeight(92)
        preview_dock_layout = QHBoxLayout(self.preview_dock)
        preview_dock_layout.setContentsMargins(18, 14, 18, 14)
        preview_dock_layout.setSpacing(14)

        self.preview_icon_1 = QPushButton(MaterialIcons.get("search"))
        self.preview_icon_1.setObjectName("previewIconButton")
        self.preview_icon_1.setFixedSize(64, 64)
        self.preview_icon_1.setFont(QFont(MaterialIcons.font_family(), 28))

        self.preview_icon_2 = QPushButton(MaterialIcons.get("settings"))
        self.preview_icon_2.setObjectName("previewIconButton")
        self.preview_icon_2.setFixedSize(64, 64)
        self.preview_icon_2.setFont(QFont(MaterialIcons.font_family(), 28))

        self.preview_action = QPushButton("Sample Button")
        self.preview_action.setObjectName("previewActionButton")
        self.preview_action.setFixedSize(132, 44)

        preview_dock_layout.addWidget(self.preview_icon_1, 0, Qt.AlignVCenter)
        preview_dock_layout.addWidget(self.preview_icon_2, 0, Qt.AlignVCenter)
        preview_dock_layout.addStretch()
        preview_dock_layout.addWidget(self.preview_action, 0, Qt.AlignVCenter)

        preview_card_layout.addStretch()
        preview_card_layout.addWidget(self.preview_dock)
        preview_card_layout.addStretch()

        tools_title = QLabel("Quick Colors")
        tools_title.setObjectName("sectionTitle")

        self.quick_colors = QFrame()
        self.quick_colors.setObjectName("quickColors")
        self.quick_colors.setFixedHeight(118)
        quick_layout = QGridLayout(self.quick_colors)
        quick_layout.setContentsMargins(0, 0, 0, 4)
        quick_layout.setHorizontalSpacing(6)
        quick_layout.setVerticalSpacing(8)

        quick_items = [
            ("Background", ["colors", "background"]),
            ("Dock BG", ["components", "dock", "background_color"]),
            ("Dock Border", ["components", "dock", "border_color"]),
            (
                "Button BG",
                ["components", "button", Theme.BUTTON_NORMAL, "background_color"],
            ),
            (
                "Button Hover",
                ["components", "button", Theme.BUTTON_NORMAL, "hover_color"],
            ),
            (
                "Button Pressed",
                ["components", "button", Theme.BUTTON_NORMAL, "pressed_color"],
            ),
            (
                "Button Border",
                ["components", "button", Theme.BUTTON_NORMAL, "border_color"],
            ),
            ("Icon Color", ["components", "icon", Theme.ICON_NORMAL, "color"]),
        ]

        self.quick_color_buttons = []
        for index, (label, path) in enumerate(quick_items):
            button = QPushButton(label)
            button.setObjectName("normalButton")
            button.setFixedHeight(30)
            button.clicked.connect(lambda checked=False, p=path: self._pick_color(p))
            quick_layout.addWidget(button, index // 3, index % 3)
            self.quick_color_buttons.append(button)

        quick_layout.setColumnStretch(0, 1)
        quick_layout.setColumnStretch(1, 1)
        quick_layout.setColumnStretch(2, 1)

        editor_header = QHBoxLayout()
        editor_header.setSpacing(8)
        editor_title = QLabel("Theme JSON")
        editor_title.setObjectName("sectionTitle")
        editor_header.addWidget(editor_title)
        editor_header.addStretch()

        self.override_editor = QPlainTextEdit()
        self.override_editor.setObjectName("overrideEditor")
        self.override_editor.textChanged.connect(self._refresh_preview)

        footer = QHBoxLayout()
        footer.setContentsMargins(0, 2, 0, 0)
        footer.setSpacing(8)

        self.cancel_btn = QPushButton("Close")
        self.cancel_btn.setObjectName("normalButton")
        self.cancel_btn.clicked.connect(self.close)

        self.save_theme_btn = QPushButton("Save Theme")
        self.save_theme_btn.setObjectName("infoButton")
        self.save_theme_btn.clicked.connect(self._save_theme)

        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setObjectName("warningButton")
        self.apply_btn.clicked.connect(self._apply_theme)

        footer.addStretch()
        footer.addWidget(self.cancel_btn)
        footer.addWidget(self.save_theme_btn)
        footer.addWidget(self.apply_btn)

        right_layout.addLayout(preview_header)
        right_layout.addWidget(self.preview_card, 0, Qt.AlignTop)
        right_layout.addSpacing(24)
        right_layout.addWidget(tools_title, 0, Qt.AlignTop)
        right_layout.addWidget(self.quick_colors, 0, Qt.AlignTop)
        right_layout.addSpacing(8)
        right_layout.addLayout(editor_header)
        right_layout.addWidget(self.override_editor, 1)
        right_layout.addLayout(footer)

        body.addWidget(left_panel)
        body.addWidget(right_panel, 1)

        main.addWidget(self.title_bar)
        main.addLayout(body, 1)

        self._apply_style()

    def _reload_theme_entries(self):
        self.entries = []
        records = ThemeRegistry.get_all_theme_records() or []
        seen = set()
        for rec in records:
            tid = rec.get("id")
            source = rec.get("source", ThemePathResolver.SOURCE_BUILTIN)
            entry_source = (
                ThemeEntry.SOURCE_BUILTIN
                if source == ThemePathResolver.SOURCE_BUILTIN
                else ThemeEntry.SOURCE_USER
            )
            self.entries.append(ThemeEntry(tid, entry_source, rec.get("path")))
            if tid:
                seen.add(Theme.normalize_theme_id(tid))

        try:
            app_themes_dir = Path(__file__).resolve().parent / "themes"
            if app_themes_dir.exists() and app_themes_dir.is_dir():
                for path in sorted(app_themes_dir.glob("*.json")):
                    if not path.is_file():
                        continue
                    theme_id = Theme.normalize_theme_id(path.stem)
                    if theme_id in seen:
                        continue
                    self.entries.append(
                        ThemeEntry(theme_id, ThemeEntry.SOURCE_THEME_MANAGER, path)
                    )
                    seen.add(theme_id)
        except Exception:
            pass

    def _load_theme_list(self):
        self._reload_theme_entries()
        self.theme_list.blockSignals(True)
        self.theme_list.clear()
        builtin = [
            e for e in self.entries if e.source_type == ThemeEntry.SOURCE_BUILTIN
        ]
        theme_manager = [
            e for e in self.entries if e.source_type == ThemeEntry.SOURCE_THEME_MANAGER
        ]
        user = [e for e in self.entries if e.source_type == ThemeEntry.SOURCE_USER]

        for e in builtin:
            self._add_theme_item(e)
        if builtin and theme_manager:
            self._add_separator_item()
        for e in theme_manager:
            self._add_theme_item(e)
        if (builtin or theme_manager) and user:
            self._add_separator_item()
        for e in user:
            self._add_theme_item(e)
        self.theme_list.blockSignals(False)

    def _create_theme_item_widget(self, entry: ThemeEntry) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(9, 6, 9, 6)
        layout.setSpacing(1)
        title = QLabel(entry.display_name)
        title.setObjectName("themeItemTitle")
        subtitle = QLabel(entry.subtitle)
        subtitle.setObjectName("themeItemSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        return widget

    def _add_separator_item(self):
        item = QListWidgetItem()
        item.setFlags(Qt.NoItemFlags)
        item.setData(self.ROLE_THEME_ID, None)
        item.setData(self.ROLE_THEME_SOURCE, None)
        item.setSizeHint(QSize(1, 16))
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 7, 12, 7)
        layout.setSpacing(0)
        line = QFrame()
        line.setObjectName("themeSeparatorLine")
        line.setFixedHeight(1)
        layout.addWidget(line)
        self.theme_list.addItem(item)
        self.theme_list.setItemWidget(item, widget)

    def _add_theme_item(self, entry: ThemeEntry):
        item = QListWidgetItem()
        item.setData(self.ROLE_THEME_ID, entry.theme_id)
        item.setData(self.ROLE_THEME_SOURCE, entry.source_type)
        item.setSizeHint(QSize(1, 48))
        self.theme_list.addItem(item)
        self.theme_list.setItemWidget(item, self._create_theme_item_widget(entry))

    def _select_current_theme(self):
        current_id = Theme.normalize_theme_id(self.current_theme_id)
        for i in range(self.theme_list.count()):
            item = self.theme_list.item(i)
            if item.data(self.ROLE_THEME_ID) == current_id:
                self.theme_list.setCurrentItem(item)
                return

    def _on_theme_selected(self, current, previous):
        if current is None:
            return
        theme_id = current.data(self.ROLE_THEME_ID)
        if not theme_id:
            if previous is not None and previous.data(self.ROLE_THEME_ID):
                self.theme_list.blockSignals(True)
                self.theme_list.setCurrentItem(previous)
                self.theme_list.blockSignals(False)
            return
        self.current_theme_id = Theme.normalize_theme_id(theme_id)
        self._load_selected_theme_editor()
        self._update_editor_state()
        self._refresh_preview()

    def _get_selected_entry(self) -> Optional[ThemeEntry]:
        current = self.theme_list.currentItem() if hasattr(self, "theme_list") else None
        if current is None:
            for e in self.entries:
                if Theme.normalize_theme_id(e.theme_id) == Theme.normalize_theme_id(
                    self.current_theme_id
                ):
                    return e
            return None
        theme_id = current.data(self.ROLE_THEME_ID)
        if not theme_id:
            return None
        for e in self.entries:
            if Theme.normalize_theme_id(e.theme_id) == Theme.normalize_theme_id(
                theme_id
            ):
                return e
        return None

    def _get_selected_theme_data(self) -> dict:
        entry = self._get_selected_entry()
        if entry is None:
            return {}
        try:
            if entry.source_type == ThemeEntry.SOURCE_BUILTIN:
                return deepcopy(Theme.load_builtin_theme(entry.theme_id) or {})
            if entry.path is not None:
                return deepcopy(Theme.load_theme_file(entry.path) or {})
        except Exception:
            return {}
        return {}

    def _get_merged_theme(self) -> dict:
        entry = self._get_selected_entry()
        if entry is None:
            return Theme.ensure_theme_defaults({})
        base = Theme.resolve_theme(entry.reference)
        editor = self._read_override_or_empty() if entry and entry.editable else None
        if editor:
            merged = Theme.deep_merge_dict(base, editor)
            return Theme.ensure_theme_defaults(merged)
        return Theme.ensure_theme_defaults(base)

    def _load_selected_theme_editor(self):
        self._set_override_text(self._get_selected_theme_data())
        self._update_editor_state()
        self._refresh_preview()

    def _update_editor_state(self):
        entry = self._get_selected_entry()
        is_editable = bool(entry and entry.editable)
        selected_type = self._selected_meta_type()
        self.override_editor.setReadOnly(not is_editable)
        for b in self.quick_color_buttons:
            b.setEnabled(is_editable)
        self.save_theme_btn.setEnabled(is_editable)
        self.clone_btn.setEnabled(entry is not None)
        self.apply_btn.setEnabled(entry is not None)
        self.remove_btn.setEnabled(
            bool(entry and entry.removable and selected_type == "user")
        )

    def _selected_meta_type(self) -> str:
        data = self._get_selected_theme_data()
        meta = data.get("meta", {}) if isinstance(data.get("meta"), dict) else {}
        return str(meta.get("type", "")).strip().lower()

    def _create_theme(self):
        name = InputDialog.show(
            self,
            title="Create Theme",
            message="Enter a name for the new theme.",
            icon="add",
            placeholder="Theme name",
            confirm_button_text="Create",
            cancel_button_text="Cancel",
        )
        if name is None:
            return
        theme_id = Theme.normalize_theme_id(name)
        if not theme_id:
            MessageDialog.warning(
                self,
                "Invalid Name",
                "Theme name cannot be empty."
            )
            return
        if Theme.theme_exists(theme_id):
            MessageDialog.warning(
                self,
                "Duplicate Theme",
                "A theme with this name already exists."
            )
            return
        Theme.create_user_theme(theme_id, str(name), Theme.get_current_theme_id())
        Theme.reload()
        self.current_theme_id = theme_id
        self._load_theme_list()
        self._select_current_theme()
        self._set_override_text(Theme.load_user_theme(theme_id) or {})
        self._update_editor_state()
        self._refresh_preview()

    def _clone_theme(self):
        src = self._get_selected_entry()
        if src is None:
            return
        name = InputDialog.show(
            self,
            title="Clone Theme",
            message="Enter a name for the cloned theme.",
            icon="content_copy",
            placeholder="Theme name",
            confirm_button_text="Clone",
            cancel_button_text="Cancel",
        )
        if name is None:
            return
        theme_id = Theme.normalize_theme_id(name)
        if not theme_id:
            MessageDialog.warning(
                self,
                "Invalid Name",
                "Theme name cannot be empty."
            )
            return
        if Theme.theme_exists(theme_id):
            MessageDialog.warning(
                self,
                "Duplicate Theme",
                "A theme with this name already exists."
            )
            return
        data = deepcopy(self._get_merged_theme())
        data.setdefault("meta", {})
        if not isinstance(data.get("meta"), dict):
            data["meta"] = {}
        data["meta"]["id"] = theme_id
        data["meta"]["name"] = str(name)
        data["meta"]["type"] = "user"
        Theme.save_user_theme(theme_id, data)
        Theme.reload()
        self.current_theme_id = theme_id
        self._load_theme_list()
        self._select_current_theme()
        self._set_override_text(Theme.load_user_theme(theme_id) or data)
        self._update_editor_state()
        self._refresh_preview()

    def _remove_theme(self):
        entry = self._get_selected_entry()
        if entry is None or not entry.removable:
            return
        theme_data = self._get_selected_theme_data()
        meta = (
            theme_data.get("meta", {})
            if isinstance(theme_data.get("meta"), dict)
            else {}
        )
        if str(meta.get("type", "")).strip().lower() != "user":
            return
        if self._is_entry_active(entry):
            MessageDialog.warning(
                self,
                "Cannot Remove Active Theme",
                "Apply another theme before removing the active user theme."
            )
            return
        title = meta.get("name") or entry.display_name
        confirmed = False
        try:
            confirmed = bool(
                ConfirmDialog.show(
                    self,
                    title="Remove Theme",
                    message=f'Are you sure you want to remove "{title}"?',
                    confirm_button_text="Remove",
                    confirm_button_style=getattr(Theme, "BUTTON_DANGER", "danger"),
                    cancel_button_text="Cancel",
                )
            )
        except Exception:
            try:
                dialog = ConfirmDialog(
                    self,
                    title="Remove Theme",
                    message=f'Are you sure you want to remove "{title}"?',
                )
                confirmed = bool(dialog.exec())
            except Exception:
                confirmed = False
        if not confirmed:
            return
        try:
            if entry.path is None or not Path(entry.path).exists():
                MessageDialog.warning(
                    self,
                    "Remove Failed",
                    "Could not find the selected theme file."
                )
                return
            Path(entry.path).unlink()
            Theme.reload()
        except Exception as e:
            MessageDialog.warning(self, "Remove Failed", str(e))
            return
        self._load_theme_list()
        self.current_theme_id = Theme.get_current_theme_id()
        self._select_current_theme()
        self._load_selected_theme_editor()
        self._update_editor_state()
        self._refresh_preview()
        MessageDialog.success(
            self,
            "Removed", "Theme removed successfully."
        )

    def _save_theme(self):
        entry = self._get_selected_entry()
        if entry is None or not entry.editable:
            MessageDialog.warning(
                self,
                "Read Only Theme",
                "Only user themes can be saved."
            )
            return
        data = self._read_override_or_alert()
        if data is None:
            return
        Theme.save_user_theme(entry.theme_id, data)
        Theme.reload()
        self._load_theme_list()
        self._select_current_theme()
        MessageDialog.success(
            self,
            "Saved", "Theme saved successfully."
        )

    def _apply_theme(self):
        entry = self._get_selected_entry()
        if entry is None:
            return
        if entry.editable:
            data = self._read_override_or_alert()
            if data is None:
                return
            Theme.save_user_theme(entry.theme_id, data)
            Theme.reload()
        try:
            self.config_manager.data["theme"] = entry.reference
            self.config_manager.data.pop("theme_override", None)
            self.config_manager.save()
        except Exception:
            pass
        Theme.set_current_theme(entry.reference)
        Theme.reload()
        self.current_theme_id = entry.theme_id
        self._reload_dock()
        self._apply_style()
        self._refresh_preview()

    def _pick_color(self, path):
        entry = self._get_selected_entry()
        if entry is None or not entry.editable:
            return
        theme = self._get_merged_theme()
        current_value = ThemeJsonEditor.get_nested(theme, path, "#ffffff")
        initial_color = Theme.to_ui_qcolor(current_value)
        color = QColorDialog.getColor(
            initial_color, self, "Select Color", QColorDialog.ShowAlphaChannel
        )
        if not color.isValid():
            return
        override = self._read_override_or_empty()
        ThemeJsonEditor.set_nested(override, path, self._qcolor_to_theme_hex(color))
        self._set_override_text(override)
        self._refresh_preview()

    def _apply_style(self):
        uic = Theme.to_ui_color
        colors = Theme.get_colors()
        button = Theme.get_button(Theme.BUTTON_NORMAL)
        muted_button = Theme.get_button(Theme.BUTTON_MUTED)
        warning_button = Theme.get_button(Theme.BUTTON_WARNING)
        info_button = Theme.get_button(Theme.BUTTON_INFO)
        title_text = Theme.get_text(Theme.TEXT_TITLE)
        subtitle_text = Theme.get_text(Theme.TEXT_SUBTITLE)
        close_button = Theme.get_button(Theme.BUTTON_CLOSE)

        window_bg = uic(colors.get(Theme.Colors.BACKGROUND))
        panel_bg = uic(colors.get(Theme.Colors.PANEL))
        editor_bg = uic(colors.get(Theme.Colors.PANEL))
        surface_color = uic(colors.get(Theme.Colors.SURFACE))
        border_color = uic(colors.get(Theme.Colors.BORDER))
        button_bg = uic(button.get(Theme.Components.Button.BACKGROUND_COLOR))
        button_hover = uic(button.get(Theme.Components.Button.HOVER_COLOR))
        button_pressed = uic(button.get(Theme.Components.Button.PRESSED_COLOR))
        button_border = uic(button.get(Theme.Components.Button.BORDER_COLOR))
        button_text_color = uic(button.get(Theme.Components.Button.TEXT_COLOR))
        title_text_color = uic(title_text.get(Theme.Components.Text.COLOR))
        subtitle_text_color = uic(subtitle_text.get(Theme.Components.Text.COLOR))

        warning_button_bg = uic(
            warning_button.get(Theme.Components.Button.BACKGROUND_COLOR)
        )
        warning_button_hover = uic(
            warning_button.get(Theme.Components.Button.HOVER_COLOR)
        )
        warning_button_pressed = uic(
            warning_button.get(Theme.Components.Button.PRESSED_COLOR)
        )
        warning_button_border = uic(
            warning_button.get(Theme.Components.Button.BORDER_COLOR)
        )
        warning_button_text_color = uic(
            warning_button.get(Theme.Components.Button.TEXT_COLOR)
        )

        info_button_bg = uic(info_button.get(Theme.Components.Button.BACKGROUND_COLOR))
        info_button_hover = uic(info_button.get(Theme.Components.Button.HOVER_COLOR))
        info_button_pressed = uic(
            info_button.get(Theme.Components.Button.PRESSED_COLOR)
        )
        info_button_border = uic(info_button.get(Theme.Components.Button.BORDER_COLOR))
        info_button_text_color = uic(
            info_button.get(Theme.Components.Button.TEXT_COLOR)
        )

        selected_bg = button_pressed
        accent_bg = button_hover
        close_text = uic(close_button.get(Theme.Components.Button.TEXT_COLOR))
        close_bg = uic(close_button.get(Theme.Components.Button.BACKGROUND_COLOR))
        close_border = uic(close_button.get(Theme.Components.Button.BORDER_COLOR))
        close_hover = uic(close_button.get(Theme.Components.Button.HOVER_COLOR))
        close_pressed = uic(close_button.get(Theme.Components.Button.PRESSED_COLOR))
        disabled_button_bg = uic(
            muted_button.get(Theme.Components.Button.BACKGROUND_COLOR)
        )
        disabled_button_border = uic(
            muted_button.get(Theme.Components.Button.BORDER_COLOR)
        )
        disabled_button_text = uic(muted_button.get(Theme.Components.Button.TEXT_COLOR))

        scrollbar_style = f"""
            QScrollBar:vertical {{
                background: rgba(255, 255, 255, 16);
                width: 12px;
                margin: 8px 0px 8px 0px;
                border: none;
                border-radius: 6px;
            }}

            QScrollBar::handle:vertical {{
                background: {button_border};
                min-height: 40px;
                border: none;
                border-radius: 6px;
            }}

            QScrollBar::handle:vertical:hover {{
                background: {button_hover};
            }}

            QScrollBar::handle:vertical:pressed {{
                background: {button_pressed};
            }}

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
                background: transparent;
                border: none;
            }}

            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{
                background: transparent;
            }}

            QScrollBar:horizontal {{
                background: rgba(255, 255, 255, 16);
                height: 12px;
                margin: 0px 8px 0px 8px;
                border: none;
                border-radius: 6px;
            }}

            QScrollBar::handle:horizontal {{
                background: {button_border};
                min-width: 40px;
                border: none;
                border-radius: 6px;
            }}

            QScrollBar::handle:horizontal:hover {{
                background: {button_hover};
            }}

            QScrollBar::handle:horizontal:pressed {{
                background: {button_pressed};
            }}

            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {{
                width: 0px;
                background: transparent;
                border: none;
            }}

            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {{
                background: transparent;
            }}
            """

        self.setStyleSheet(
            scrollbar_style
            + f"""
            QDialog {{
                background: {window_bg};
            }}
            QFrame#container {{
                background: {window_bg};
                border: 1px solid {border_color};
                border-radius: 0px;
            }}
            QFrame#titleBar {{
                background: {panel_bg};
                border-bottom: 1px solid {border_color};
            }}
            
            QLabel#materialIcon {{
                font-family: Material Icons;
                font-size: 21px;
                color: {title_text_color};
                border-radius: 15px;
            }}
            
            QPushButton#closeButton {{
                font-family: Material Icons;
                font-size: 21px;
                color: {close_text};
                background: {close_bg};
                border: 1px solid {close_border};
                border-radius: 15px;
            }}
            
            QPushButton#closeButton:hover {{
                background: {close_hover};
                border-color: {close_border};
            }}
            QPushButton#closeButton:pressed {{
                background: {close_pressed};
                border-color: {close_border};
            }}
            QLabel#titleLabel {{
                color: {title_text_color};
                font-size: 17px;
                font-weight: 700;
            }}
            QLabel#subtitleLabel {{
                color: {subtitle_text_color};
                font-size: 12px;
            }}
            QFrame#panel {{
                background: {panel_bg};
                border: 1px solid {border_color};
                border-radius: 14px;
            }}
            QLabel#sectionTitle {{
                color: {title_text_color};
                font-size: 13px;
                font-weight: 700;
            }}
            QLabel#badge {{
                color: {title_text_color};
                background: {accent_bg};
                border: 1px solid {button_border};
                border-radius: 8px;
                padding: 1px 6px;
                font-size: 9px;
                font-weight: 700;
            }}
            QLabel#badge[inactive="true"] {{
                color: transparent;
                background: transparent;
                border: 1px solid transparent;
            }}
            QListWidget#themeList {{
                background: {window_bg};
                border: 1px solid {border_color};
                border-radius: 12px;
                color: {title_text_color};
                padding: 5px;
                outline: none;
            }}
            QListWidget#themeList::item {{
                padding: 0px;
                border-radius: 9px;
                margin: 2px;
            }}
            QListWidget#themeList::item:hover {{
                background: {button_hover};
            }}
            QListWidget#themeList::item:selected {{
                background: {selected_bg};
                color: {title_text_color};
            }}
            QLabel#themeItemTitle {{
                color: {title_text_color};
                font-size: 12px;
                font-weight: 700;
            }}
            QLabel#themeItemSubtitle {{
                color: {subtitle_text_color};
                font-size: 10px;
                font-weight: 500;
            }}
            QFrame#themeSeparatorLine {{
                background: {border_color};
                border: none;
                border-radius: 1px;
                max-height: 1px;
            }}
            QFrame#previewCard {{
                background: {panel_bg};
                border: 1px solid {border_color};
                border-radius: 14px;
            }}
            QPlainTextEdit#overrideEditor {{
                background: {window_bg};
                border: 1px solid {border_color};
                border-radius: 12px;
                color: {title_text_color};
                selection-background-color: {selected_bg};
                padding: 10px;
                font-family: Consolas, Menlo, Monaco, monospace;
                font-size: 12px;
            }}
            QPushButton#normalButton,
            QPushButton#infoButton,
            QPushButton#warningButton,
            QPushButton#previewActionButton,
            QPushButton#previewIconButton {{
                min-height: 30px;
                border-radius: 10px;
                padding: 0 12px;
                font-size: 12px;
                font-weight: 700;
            }}
            
            QPushButton#warningButton {{
                color: {warning_button_text_color};
                background: {warning_button_bg};
                border: 1px solid {warning_button_border};
            }}
            QPushButton#warningButton:hover {{
                background: {warning_button_hover};
            }}
            QPushButton#warningButton:pressed {{
                background: {warning_button_pressed};
            }}
            
            QPushButton#normalButton {{
                color: {button_text_color};
                background: {button_bg};
                border: 1px solid {button_border};
            }}
            QPushButton#normalButton:hover {{
                background: {button_hover};
            }}
            QPushButton#normalButton:pressed {{
                background: {button_pressed};
            }}
            
            QPushButton#infoButton {{
                color: {info_button_text_color};
                background: {info_button_bg};
                border: 1px solid {info_button_border};
            }}
            QPushButton#infoButton:hover {{
                background: {info_button_hover};
            }}
            QPushButton#infoButton:pressed {{
                background: {info_button_pressed};
            }}
            
            QPushButton#warningButton:disabled,
            QPushButton#infoButton:disabled,
            QPushButton#normalButton:disabled {{
                color: {disabled_button_text};
                background: {disabled_button_bg};
                border: 1px solid {disabled_button_border};
            }}
            QPushButton#previewIconButton {{
                min-width: 64px;
                max-width: 64px;
                min-height: 64px;
                max-height: 64px;
                padding: 0px;
            }}
            QPushButton#previewActionButton {{
                min-width: 132px;
                max-width: 132px;
                min-height: 44px;
                max-height: 44px;
            }}
        """
        )

    def _refresh_preview(self):
        if not hasattr(self, "preview_card"):
            return
        uic = Theme.to_ui_color
        theme = self._get_merged_theme()
        entry = self._get_selected_entry()
        is_active = self._is_entry_active(entry)
        self.active_badge.setText("ACTIVE")
        self.active_badge.setProperty("inactive", not is_active)
        self.active_badge.style().unpolish(self.active_badge)
        self.active_badge.style().polish(self.active_badge)

        colors = Theme.get_colors(theme)
        dock = Theme.get_dock(theme)
        button = Theme.get_button(Theme.BUTTON_NORMAL, theme)
        icon = Theme.get_icon(Theme.ICON_NORMAL, theme)
        layout = Theme.get_component("layout", theme_data=theme, default={})

        color_bg = uic(colors.get("background", "#1e1e1eff"))
        dock_bg = uic(dock.get("background_color", "#1e1e1eff"))
        dock_border = uic(dock.get("border_color", "#ffffff33"))
        dock_border_width = dock.get("border_width", 1)
        dock_radius = min(
            int(dock.get("border_radius", Theme.get_size("dock_radius", 12, theme))), 16
        )

        button_bg = uic(
            button.get("background_color", dock.get("background_color", "#2a2a2aff"))
        )
        button_hover = uic(
            button.get("hover_color", button.get("background_color", "#333333ff"))
        )
        button_pressed = uic(
            button.get("pressed_color", button.get("background_color", "#242424ff"))
        )
        button_border = uic(
            button.get("border_color", dock.get("border_color", "#ffffff33"))
        )
        button_border_width = button.get("border_width", 1)
        button_radius = min(int(button.get("border_radius", 10)), 14)

        icon_color = uic(icon.get("color", "#ffffffff"))
        icon_size = min(
            int(icon.get("size", Theme.get_size("icon_size", 28, theme))), 30
        )

        spacing = min(int(layout.get("spacing", 10)), 14)
        padding = min(int(layout.get("padding", 10)), 14)

        self.preview_dock.layout().setSpacing(spacing)
        self.preview_dock.layout().setContentsMargins(padding + 8, 14, padding + 8, 14)

        self.preview_card.setStyleSheet(f"""
            QFrame#previewCard {{
                background: {color_bg};
            }}
        """)

        self.preview_dock.setStyleSheet(f"""
            QFrame#previewDock {{
                background: {dock_bg};
                border: {dock_border_width}px solid {dock_border};
                border-radius: {dock_radius}px;
            }}
        """)

        preview_icon_style = f"""
            QPushButton#previewIconButton {{
                color: {icon_color};
                background: {button_bg};
                border: {button_border_width}px solid {button_border};
                border-radius: {button_radius}px;
                font-family: Material Icons;
                font-size: {icon_size}px;
                font-weight: 700;
                min-width: 64px;
                max-width: 64px;
                min-height: 64px;
                max-height: 64px;
                padding: 0px;
            }}
            QPushButton#previewIconButton:hover {{
                background: {button_hover};
            }}
            QPushButton#previewIconButton:pressed {{
                background: {button_pressed};
            }}
        """
        self.preview_icon_1.setStyleSheet(preview_icon_style)
        self.preview_icon_2.setStyleSheet(preview_icon_style)

        self.preview_action.setStyleSheet(f"""
            QPushButton#previewActionButton {{
                color: {icon_color};
                background: {button_bg};
                border: {button_border_width}px solid {button_border};
                border-radius: {button_radius}px;
                min-width: 132px;
                max-width: 132px;
                min-height: 44px;
                max-height: 44px;
                padding: 0px 14px;
                font-size: 11px;
                font-weight: 700;
            }}
            QPushButton#previewActionButton:hover {{
                background: {button_hover};
            }}
            QPushButton#previewActionButton:pressed {{
                background: {button_pressed};
            }}
        """)

    def _read_override_or_empty(self) -> dict:
        text = (
            self.override_editor.toPlainText()
            if hasattr(self, "override_editor")
            else ""
        )
        return ThemeJsonEditor.parse_silent(text)

    def _read_override_or_alert(self) -> Optional[dict]:
        value, error = ThemeJsonEditor.parse(self.override_editor.toPlainText())
        if error is not None:
            title = (
                "Invalid Theme"
                if error == "Theme JSON must be a JSON object."
                else "Invalid JSON"
            )
            MessageDialog.warning(self, title, error)
            return None
        return value

    def _set_override_text(self, value):
        self.override_editor.blockSignals(True)
        self.override_editor.setPlainText(ThemeJsonEditor.dump(value))
        self.override_editor.blockSignals(False)

    def _qcolor_to_theme_hex(self, color: QColor) -> str:
        return "#{:02x}{:02x}{:02x}{:02x}".format(
            color.red(), color.green(), color.blue(), color.alpha()
        )

    def _is_entry_active(self, entry: Optional[ThemeEntry]) -> bool:
        if entry is None:
            return False
        current = Theme.get_current_theme_id()
        if ThemePathResolver.looks_like_theme_path(current):
            try:
                resolved = ThemePathResolver.resolve_theme_path_input(current)
                if resolved is not None and entry.path is not None:
                    return Path(entry.path).resolve() == Path(resolved).resolve()
            except Exception:
                return False
            return False
        return Theme.normalize_theme_id(current) == Theme.normalize_theme_id(
            entry.theme_id
        )

    def _reload_dock(self):
        if self.dock is None:
            return
        theme_value = self.config_manager.data.get(
            "theme", Theme.get_current_theme_id()
        )
        if hasattr(self.dock, "current_theme_name"):
            try:
                self.dock.current_theme_name = Theme.get_current_theme_id()
            except Exception:
                pass
        if hasattr(self.dock, "active_theme"):
            try:
                self.dock.active_theme = Theme.get_theme(theme_value)
            except Exception:
                pass

        if hasattr(self.dock, "apply_theme"):
            try:
                self.dock.apply_theme()
                return
            except Exception:
                pass

        if hasattr(self.dock, "update"):
            try:
                self.dock.update()
            except Exception:
                pass

    def _display_name(self, value):
        return str(value).replace("-", " ").replace("_", " ").title()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self.drag_position is not None:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_position = None
        event.accept()


App = ThemeManagerApp
