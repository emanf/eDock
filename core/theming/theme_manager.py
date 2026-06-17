import json
from copy import deepcopy
from pathlib import Path
from PySide6.QtGui import QColor
from core import paths as core_paths
from core.paths import (
    ROOT_DIR,
    USER_CONFIG_PATH,
    get_core_themes_dir,
    get_user_themes_dir,
)


DEFAULT_THEME_ID = "dark"
THEME_FILE_EXTENSION = ".json"


class ThemePathResolver:
    SOURCE_BUILTIN = "builtin"
    SOURCE_LOCAL = "local"
    SOURCE_USER = "user"
    SOURCE_FILE = "file"

    PRECEDENCE = (
        SOURCE_BUILTIN,
        SOURCE_LOCAL,
        SOURCE_USER,
    )

    @classmethod
    def get_builtin_themes_dir(cls) -> Path:
        return Path(get_core_themes_dir())

    @classmethod
    def get_local_themes_dir(cls) -> Path | None:
        getter = getattr(core_paths, "get_local_themes_dir", None)
        if callable(getter):
            try:
                path = getter()
                if path:
                    return Path(path)
            except Exception:
                return None

        candidate = Path(ROOT_DIR) / "themes"
        return candidate

    @classmethod
    def get_user_themes_dir(cls) -> Path:
        return Path(get_user_themes_dir())

    @classmethod
    def ensure_theme_dirs(cls):
        cls.get_user_themes_dir().mkdir(parents=True, exist_ok=True)

    @classmethod
    def normalize_theme_id(cls, theme_id):
        if not theme_id:
            return DEFAULT_THEME_ID
        return str(theme_id).strip().lower()

    @classmethod
    def safe_theme_id(cls, theme_id):
        theme_id = cls.normalize_theme_id(theme_id)
        theme_id = theme_id.replace("\\", "").replace("/", "")
        theme_id = theme_id.replace("..", "")
        return theme_id or DEFAULT_THEME_ID

    @classmethod
    def looks_like_theme_path(cls, value):
        if not value:
            return False
        value = str(value).strip()
        if not value:
            return False
        if value.endswith(THEME_FILE_EXTENSION):
            return True
        if "/" in value or "\\" in value:
            return True
        return False

    @classmethod
    def normalize_path_separators(cls, value):
        return str(value).replace("/", "\\").strip()

    @classmethod
    def is_windows_absolute_path(cls, value):
        value = str(value).strip()
        return len(value) > 1 and value[1] == ":"

    @classmethod
    def is_project_relative_path(cls, value):
        value = str(value).strip()
        return value.startswith("\\") or value.startswith("/")

    @classmethod
    def resolve_project_relative_path(cls, value):
        value = str(value).strip().lstrip("\\/")
        if not value:
            return Path(ROOT_DIR)
        return (Path(ROOT_DIR) / Path(value)).resolve()

    @classmethod
    def resolve_theme_path_input(cls, value, base_dir=None):
        if not value:
            return None

        value = str(value).strip()
        if not value:
            return None

        if cls.is_project_relative_path(value):
            try:
                return cls.resolve_project_relative_path(value)
            except Exception:
                return Path(ROOT_DIR) / value.lstrip("\\/")

        path = Path(value).expanduser()

        if not path.is_absolute() and not cls.is_windows_absolute_path(value):
            if base_dir is not None:
                path = Path(base_dir) / path
            else:
                path = Path(ROOT_DIR) / path

        try:
            path = path.resolve()
        except Exception:
            path = path.absolute()

        return path

    @classmethod
    def make_config_theme_value(cls, value):
        if not cls.looks_like_theme_path(value):
            return cls.normalize_theme_id(value)

        path = cls.resolve_theme_path_input(value)
        if path is None:
            return DEFAULT_THEME_ID

        try:
            relative_path = path.resolve().relative_to(Path(ROOT_DIR).resolve())
            return "\\" + str(relative_path).replace("/", "\\")
        except Exception:
            return cls.normalize_path_separators(value)

    @classmethod
    def get_theme_path(cls, theme_id, source):
        theme_id = cls.safe_theme_id(theme_id)
        if source == cls.SOURCE_BUILTIN:
            return cls.get_builtin_themes_dir() / f"{theme_id}{THEME_FILE_EXTENSION}"
        if source == cls.SOURCE_LOCAL:
            local_dir = cls.get_local_themes_dir()
            return (
                None
                if local_dir is None
                else local_dir / f"{theme_id}{THEME_FILE_EXTENSION}"
            )
        if source == cls.SOURCE_USER:
            return cls.get_user_themes_dir() / f"{theme_id}{THEME_FILE_EXTENSION}"
        return None

    @classmethod
    def get_builtin_theme_path(cls, theme_id):
        return cls.get_theme_path(theme_id, cls.SOURCE_BUILTIN)

    @classmethod
    def get_local_theme_path(cls, theme_id):
        return cls.get_theme_path(theme_id, cls.SOURCE_LOCAL)

    @classmethod
    def get_user_theme_path(cls, theme_id):
        return cls.get_theme_path(theme_id, cls.SOURCE_USER)


class ThemeConfigService:
    @classmethod
    def read_json_file(cls, path: Path):
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    @classmethod
    def write_json_file(cls, path: Path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @classmethod
    def load_theme_file(cls, path: Path):
        if path is None or not path.exists() or not path.is_file():
            return None
        try:
            data = cls.read_json_file(path)
            if isinstance(data, dict):
                return data
        except Exception:
            return None
        return None

    @classmethod
    def read_user_config(cls):
        path = Path(USER_CONFIG_PATH)
        if not path.exists() or not path.is_file():
            return {}
        try:
            data = cls.read_json_file(path)
            if isinstance(data, dict):
                return data
        except Exception:
            return {}
        return {}

    @classmethod
    def write_user_config(cls, data):
        cls.write_json_file(Path(USER_CONFIG_PATH), data or {})


class ThemeRegistry:
    @classmethod
    def _list_theme_names_from_dir(cls, themes_dir: Path | None):
        result = []
        if themes_dir and themes_dir.exists() and themes_dir.is_dir():
            for path in sorted(themes_dir.glob(f"*{THEME_FILE_EXTENSION}")):
                if path.is_file():
                    result.append(ThemePathResolver.normalize_theme_id(path.stem))
        return result

    @classmethod
    def list_builtin_themes(cls):
        return cls._list_theme_names_from_dir(
            ThemePathResolver.get_builtin_themes_dir()
        )

    @classmethod
    def list_local_themes(cls):
        return cls._list_theme_names_from_dir(ThemePathResolver.get_local_themes_dir())

    @classmethod
    def list_user_themes(cls):
        ThemePathResolver.ensure_theme_dirs()
        return cls._list_theme_names_from_dir(ThemePathResolver.get_user_themes_dir())

    @classmethod
    def get_theme_record(cls, theme_id):
        theme_id = ThemePathResolver.normalize_theme_id(theme_id)
        for source in ThemePathResolver.PRECEDENCE:
            path = ThemePathResolver.get_theme_path(theme_id, source)
            if path and path.exists() and path.is_file():
                return {
                    "id": theme_id,
                    "source": source,
                    "path": path,
                }
        return None

    @classmethod
    def get_all_theme_records(cls):
        records = {}
        for source, ids in (
            (ThemePathResolver.SOURCE_BUILTIN, cls.list_builtin_themes()),
            (ThemePathResolver.SOURCE_LOCAL, cls.list_local_themes()),
            (ThemePathResolver.SOURCE_USER, cls.list_user_themes()),
        ):
            for theme_id in ids:
                if theme_id not in records:
                    records[theme_id] = {
                        "id": theme_id,
                        "source": source,
                        "path": ThemePathResolver.get_theme_path(theme_id, source),
                    }
        return [records[key] for key in sorted(records.keys())]

    @classmethod
    def list_themes(cls):
        return [record["id"] for record in cls.get_all_theme_records()]

    @classmethod
    def theme_exists(cls, theme_id):
        if ThemePathResolver.looks_like_theme_path(theme_id):
            path = ThemePathResolver.resolve_theme_path_input(theme_id)
            return bool(path and path.exists() and path.is_file())
        return cls.get_theme_record(theme_id) is not None


class ThemeManagerService:
    @classmethod
    def list_theme_entries(cls):
        entries = []
        for record in ThemeRegistry.get_all_theme_records():
            theme_data = ThemeConfigService.load_theme_file(record["path"]) or {}
            meta = theme_data.get("meta", {}) if isinstance(theme_data, dict) else {}
            entries.append(
                {
                    "id": record["id"],
                    "name": meta.get("name") or record["id"],
                    "type": record["source"],
                    "source": record["source"],
                    "path": str(record["path"]),
                    "base": meta.get("base") or DEFAULT_THEME_ID,
                }
            )
        return entries

    @classmethod
    def get_theme_entry(cls, theme_id):
        record = ThemeRegistry.get_theme_record(theme_id)
        if not record:
            return None
        theme_data = ThemeConfigService.load_theme_file(record["path"]) or {}
        meta = theme_data.get("meta", {}) if isinstance(theme_data, dict) else {}
        return {
            "id": record["id"],
            "name": meta.get("name") or record["id"],
            "type": record["source"],
            "source": record["source"],
            "path": str(record["path"]),
            "base": meta.get("base") or DEFAULT_THEME_ID,
        }

    @classmethod
    def resolve_theme_source(cls, theme_id):
        record = ThemeRegistry.get_theme_record(theme_id)
        return record["source"] if record else None

    @classmethod
    def resolve_theme_path(cls, theme_id):
        record = ThemeRegistry.get_theme_record(theme_id)
        return record["path"] if record else None


class Theme:
    class Colors:
        BACKGROUND = "background"
        PANEL = "panel"
        SURFACE = "surface"
        SURFACE_HOVER = "surface_hover"
        SURFACE_PRESSED = "surface_pressed"
        BORDER = "border"
        TEXT = "text"
        MUTED_TEXT = "muted_text"
        PLACEHOLDER = "placeholder"

        POSITIVE = "positive"
        POSITIVE_HOVER = "positive_hover"
        POSITIVE_PRESSED = "positive_pressed"
        POSITIVE_TEXT = "positive_text"
        POSITIVE_BORDER = "positive_border"

        NEGATIVE = "negative"
        NEGATIVE_HOVER = "negative_hover"
        NEGATIVE_PRESSED = "negative_pressed"
        NEGATIVE_TEXT = "negative_text"
        NEGATIVE_BORDER = "negative_border"

        DANGER = "danger"
        DANGER_HOVER = "danger_hover"
        DANGER_PRESSED = "danger_pressed"
        DANGER_TEXT = "danger_text"
        DANGER_BORDER = "danger_border"

        WARNING = "warning"
        WARNING_HOVER = "warning_hover"
        WARNING_PRESSED = "warning_pressed"
        WARNING_TEXT = "warning_text"
        WARNING_BORDER = "warning_border"

        INFO = "info"
        INFO_HOVER = "info_hover"
        INFO_PRESSED = "info_pressed"
        INFO_TEXT = "info_text"
        INFO_BORDER = "info_border"

        PRIMARY = "primary"
        DANGER_HOVER = "danger_hover"
        DANGER_PRESSED = "danger_pressed"
        DANGER_TEXT = "danger_text"
        DANGER_BORDER = "danger_border"

        WARNING = "warning"
        WARNING_HOVER = "warning_hover"
        WARNING_PRESSED = "warning_pressed"
        WARNING_TEXT = "warning_text"
        WARNING_BORDER = "warning_border"

        INFO = "info"
        INFO_HOVER = "info_hover"
        INFO_PRESSED = "info_pressed"
        INFO_TEXT = "info_text"
        INFO_BORDER = "info_border"

    class Sizes:
        class Space:
            XS = "space.xs"
            SM = "space.sm"
            MD = "space.md"
            LG = "space.lg"
            XL = "space.xl"

        class Radius:
            XS = "radius.xs"
            SM = "radius.sm"
            MD = "radius.md"
            LG = "radius.lg"
            XL = "radius.xl"
            XXL = "radius.2xl"

        class BorderWidth:
            HAIRLINE = "border_width.hairline"
            THIN = "border_width.thin"
            MEDIUM = "border_width.medium"
            THICK = "border_width.thick"
            HEAVY = "border_width.heavy"

        class Icon:
            XS = "icon.xs"
            SM = "icon.sm"
            MD = "icon.md"
            LG = "icon.lg"
            XL = "icon.xl"
            XXL = "icon.2xl"
            XXXL = "icon.3xl"
            XXXXL = "icon.4xl"
            XXXXXL = "icon.5xl"

    class Components:
        class Dock:
            BACKGROUND_COLOR = "background_color"
            BORDER_COLOR = "border_color"
            BORDER_WIDTH = "border_width"
            BORDER_RADIUS = "border_radius"

        class Dialog:
            BACKGROUND_COLOR = "background_color"
            BORDER_COLOR = "border_color"
            BORDER_WIDTH = "border_width"
            BORDER_RADIUS = "border_radius"
            TEXT_COLOR = "text_color"

        class Button:
            BACKGROUND_COLOR = "background_color"
            HOVER_COLOR = "hover_color"
            PRESSED_COLOR = "pressed_color"
            BORDER_COLOR = "border_color"
            BORDER_WIDTH = "border_width"
            BORDER_RADIUS = "border_radius"
            TEXT_COLOR = "text_color"

        class Icon:
            COLOR = "color"
            SIZE = "size"
            PADDING = "padding"

        class Text:
            COLOR = "color"
            FONT_SIZE = "font_size"
            FONT_WEIGHT = "font_weight"

        class Input:
            BACKGROUND_COLOR = "background_color"
            BORDER_COLOR = "border_color"
            BORDER_WIDTH = "border_width"
            BORDER_RADIUS = "border_radius"
            TEXT_COLOR = "text_color"
            PLACEHOLDER_COLOR = "placeholder_color"

        class Tooltip:
            BACKGROUND_COLOR = "background_color"
            BORDER_COLOR = "border_color"
            BORDER_WIDTH = "border_width"
            BORDER_RADIUS = "border_radius"
            TEXT_COLOR = "text_color"

    BUTTON_NORMAL = "normal"
    BUTTON_POSITIVE = "positive"
    BUTTON_NEGATIVE = "negative"
    BUTTON_WARNING = "warning"
    BUTTON_DANGER = "danger"
    BUTTON_INFO = "info"
    BUTTON_CLOSE = "close"
    BUTTON_MUTED = "muted"

    ICON_NORMAL = "normal"
    ICON_POSITIVE = "positive"
    ICON_NEGATIVE = "negative"
    ICON_WARNING = "warning"
    ICON_INFO = "info"
    ICON_MUTED = "muted"

    TEXT_NORMAL = "normal"
    TEXT_MUTED = "muted"
    TEXT_TITLE = "title"
    TEXT_SUBTITLE = "subtitle"
    TEXT_POSITIVE = "positive"
    TEXT_NEGATIVE = "negative"
    TEXT_WARNING = "warning"
    TEXT_INFO = "info"

    DEFAULT_THEME_DATA = {
        "meta": {
            "id": DEFAULT_THEME_ID,
            "name": "Dark",
            "type": "builtin",
            "base": DEFAULT_THEME_ID,
        },
        "colors": {
            "background": "#202020ee",
            "panel": "#ffffff30",
            "surface": "#2b2b2bdd",
            "surface_hover": "#3a3a3add",
            "surface_pressed": "#454545dd",
            "border": "#5f5f5fbb",
            "text": "#ffffff",
            "muted_text": "#bdbdbd",
            "placeholder": "#9ca3af",
            "positive": "#16a34a",
            "positive_hover": "#22c55e",
            "positive_pressed": "#15803d",
            "positive_text": "#ffffff",
            "positive_border": "#4ade80",
            "negative": "#dc2626",
            "negative_hover": "#ef4444",
            "negative_pressed": "#b91c1c",
            "negative_text": "#ffffff",
            "negative_border": "#f87171",
            "danger": "#ef4444dd",
            "danger_hover": "#dc2626dd",
            "danger_pressed": "#b91c1cdd",
            "danger_text": "#fff5f5",
            "danger_border": "#f87171cc",
            "warning": "#d97706",
            "warning_hover": "#f59e0b",
            "warning_pressed": "#b45309",
            "warning_text": "#ffffff",
            "warning_border": "#fbbf24",
            "info": "#2563eb",
            "info_hover": "#3b82f6",
            "info_pressed": "#1d4ed8",
            "info_text": "#ffffff",
            "info_border": "#60a5fa",
        },
        "sizes": {
            "space": {
                "xs": 4,
                "sm": 8,
                "md": 12,
                "lg": 16,
                "xl": 20,
            },
            "radius": {
                "xs": 8,
                "sm": 12,
                "md": 14,
                "lg": 18,
                "xl": 28,
                "2xl": 36,
            },
            "border_width": {
                "hairline": 0.5,
                "thin": 1.0,
                "medium": 1.2,
                "thick": 1.5,
                "heavy": 2.0,
            },
            "icon": {
                "xs": 16,
                "sm": 20,
                "md": 24,
                "lg": 32,
                "xl": 40,
                "2xl": 48,
                "3xl": 56,
                "4xl": 64,
                "5xl": 72,
            },
        },
        "components": {
            "dock": {
                "background_color": "#202020ee",
                "border_color": "#5f5f5fbb",
                "border_width": 1.2,
                "border_radius": 28,
            },
            "button": {
                "normal": {
                    "background_color": "#2b2b2bdd",
                    "hover_color": "#3a3a3add",
                    "pressed_color": "#454545dd",
                    "border_color": "#5f5f5fbb",
                    "text_color": "#ffffff",
                    "border_width": 1.0,
                    "border_radius": 18,
                },
                "muted": {
                    "background_color": "#252525b8",
                    "hover_color": "#2d2d2dc4",
                    "pressed_color": "#343434cc",
                    "border_color": "#5a5a5a88",
                    "text_color": "#ffffff88",
                    "border_width": 1.0,
                    "border_radius": 18,
                },
                "positive": {
                    "background_color": "#16a34a",
                    "hover_color": "#22c55e",
                    "pressed_color": "#15803d",
                    "border_color": "#4ade80",
                    "text_color": "#ffffff",
                    "border_width": 1.0,
                    "border_radius": 18,
                },
                "negative": {
                    "background_color": "#dc2626",
                    "hover_color": "#ef4444",
                    "pressed_color": "#b91c1c",
                    "border_color": "#f87171",
                    "text_color": "#ffffff",
                    "border_width": 1.0,
                    "border_radius": 18,
                },
                "danger": {
                    "background_color": "#ef4444dd",
                    "hover_color": "#dc2626dd",
                    "pressed_color": "#b91c1cdd",
                    "border_color": "#f87171cc",
                    "text_color": "#fff5f5",
                    "border_width": 1.0,
                    "border_radius": 18,
                },
                "warning": {
                    "background_color": "#d97706",
                    "hover_color": "#f59e0b",
                    "pressed_color": "#b45309",
                    "border_color": "#fbbf24",
                    "text_color": "#ffffff",
                    "border_width": 1.0,
                    "border_radius": 18,
                },
                "info": {
                    "background_color": "#2563eb",
                    "hover_color": "#3b82f6",
                    "pressed_color": "#1d4ed8",
                    "border_color": "#60a5fa",
                    "text_color": "#ffffff",
                    "border_width": 1.0,
                    "border_radius": 18,
                },
                "close": {
                    "background_color": "#252525dd",
                    "hover_color": "#3b82f6",
                    "pressed_color": "#1d4ed8",
                    "border_color": "#252525dd",
                    "text_color": "#ffffff",
                    "border_width": 0.0,
                    "border_radius": 12,
                },
            },
            "icon": {
                "normal": {
                    "color": "#ffffff",
                    "size": 56,
                    "padding": 20,
                },
                "positive": {
                    "color": "#22c55e",
                },
                "negative": {
                    "color": "#ef4444",
                },
                "warning": {
                    "color": "#f59e0b",
                },
                "info": {
                    "color": "#3b82f6",
                },
                "muted": {
                    "color": "#9ca3af",
                },
            },
            "text": {
                "normal": {
                    "color": "#ffffff",
                    "font_size": 14,
                    "font_weight": 400,
                },
                "muted": {
                    "color": "#bdbdbd",
                    "font_size": 14,
                    "font_weight": 400,
                },
                "title": {
                    "color": "#ffffff",
                    "font_size": 18,
                    "font_weight": 600,
                },
                "subtitle": {
                    "color": "#bdbdbd",
                    "font_size": 14,
                    "font_weight": 400,
                },
                "positive": {
                    "color": "#22c55e",
                    "font_size": 14,
                    "font_weight": 400,
                },
                "negative": {
                    "color": "#ef4444",
                    "font_size": 14,
                    "font_weight": 400,
                },
                "warning": {
                    "color": "#f59e0b",
                    "font_size": 14,
                    "font_weight": 400,
                },
                "info": {
                    "color": "#3b82f6",
                    "font_size": 14,
                    "font_weight": 400,
                },
            },
            "input": {
                "background_color": "#2b2b2bdd",
                "border_color": "#5f5f5fbb",
                "text_color": "#ffffff",
                "placeholder_color": "#9ca3af",
                "selection_color": "#3b82f6",
                "border_width": 1.0,
                "border_radius": 12,
            },
            "menu": {
                "background_color": "#252525ee",
                "border_color": "#5f5f5fbb",
                "text_color": "#ffffff",
                "hover_color": "#3a3a3add",
                "separator_color": "#5f5f5fbb",
                "border_width": 1.0,
                "border_radius": 14,
            },
            "dialog": {
                "background_color": "#202020ee",
                "border_color": "#5f5f5fbb",
                "text_color": "#ffffff",
                "border_width": 1.0,
                "border_radius": 18,
            },
            "tooltip": {
                "background_color": "#202020ee",
                "border_color": "#5f5f5fbb",
                "text_color": "#ffffff",
                "border_width": 1.0,
                "border_radius": 18,
            },
        },
    }

    _current_theme_id = DEFAULT_THEME_ID
    _current_theme_cache = None

    @classmethod
    def get_user_themes_dir(cls) -> Path:
        return ThemePathResolver.get_user_themes_dir()

    @classmethod
    def get_builtin_themes_dir(cls) -> Path:
        return ThemePathResolver.get_builtin_themes_dir()

    @classmethod
    def get_local_themes_dir(cls) -> Path | None:
        return ThemePathResolver.get_local_themes_dir()

    @classmethod
    def ensure_theme_dirs(cls):
        ThemePathResolver.ensure_theme_dirs()

    @classmethod
    def normalize_theme_id(cls, theme_id):
        return ThemePathResolver.normalize_theme_id(theme_id)

    @classmethod
    def _safe_theme_id(cls, theme_id):
        return ThemePathResolver.safe_theme_id(theme_id)

    @classmethod
    def _looks_like_theme_path(cls, value):
        return ThemePathResolver.looks_like_theme_path(value)

    @classmethod
    def _read_json_file(cls, path: Path):
        return ThemeConfigService.read_json_file(path)

    @classmethod
    def _write_json_file(cls, path: Path, data):
        ThemeConfigService.write_json_file(path, data)

    @classmethod
    def _read_user_config(cls):
        return ThemeConfigService.read_user_config()

    @classmethod
    def _write_user_config(cls, data):
        ThemeConfigService.write_user_config(data)

    @classmethod
    def _normalize_path_separators(cls, value):
        return ThemePathResolver.normalize_path_separators(value)

    @classmethod
    def _is_windows_absolute_path(cls, value):
        return ThemePathResolver.is_windows_absolute_path(value)

    @classmethod
    def _is_project_relative_path(cls, value):
        return ThemePathResolver.is_project_relative_path(value)

    @classmethod
    def _resolve_project_relative_path(cls, value):
        return ThemePathResolver.resolve_project_relative_path(value)

    @classmethod
    def _resolve_theme_path_input(cls, value, base_dir=None):
        return ThemePathResolver.resolve_theme_path_input(value, base_dir=base_dir)

    @classmethod
    def _make_config_theme_value(cls, value):
        return ThemePathResolver.make_config_theme_value(value)

    @classmethod
    def deep_merge_dict(cls, base, override):
        result = deepcopy(base or {})
        for key, value in (override or {}).items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = cls.deep_merge_dict(result[key], value)
            else:
                result[key] = deepcopy(value)
        return result

    @classmethod
    def _get_nested_value(cls, data, path, default=None):
        if not isinstance(data, dict):
            return default
        if not path:
            return default

        current = data
        for part in str(path).split("."):
            if not isinstance(current, dict):
                return default
            if part not in current:
                return default
            current = current[part]
        return current

    @classmethod
    def _resolve_reference(cls, value, theme_data):
        if not isinstance(value, str):
            return value

        value = value.strip()
        if not value.startswith("$"):
            return value

        resolved = cls._get_nested_value(theme_data, value[1:], default=None)
        if resolved is None:
            return value

        return cls._resolve_reference(resolved, theme_data)

    @classmethod
    def _resolve_references(cls, value, theme_data):
        if isinstance(value, dict):
            return {
                key: cls._resolve_references(item, theme_data)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [cls._resolve_references(item, theme_data) for item in value]
        return cls._resolve_reference(value, theme_data)

    @classmethod
    def get_builtin_theme_path(cls, theme_id) -> Path:
        return ThemePathResolver.get_builtin_theme_path(theme_id)

    @classmethod
    def get_local_theme_path(cls, theme_id) -> Path | None:
        return ThemePathResolver.get_local_theme_path(theme_id)

    @classmethod
    def get_user_theme_path(cls, theme_id) -> Path:
        return ThemePathResolver.get_user_theme_path(theme_id)

    @classmethod
    def load_theme_file(cls, path: Path):
        return ThemeConfigService.load_theme_file(path)

    @classmethod
    def load_theme_from_path(cls, path_value, base_dir=None):
        path = cls._resolve_theme_path_input(path_value, base_dir=base_dir)
        if path is None:
            return None
        return cls.load_theme_file(path)

    @classmethod
    def load_builtin_theme(cls, theme_id):
        path = cls.get_builtin_theme_path(theme_id)
        data = cls.load_theme_file(path)
        if data is not None:
            return data
        if cls.normalize_theme_id(theme_id) != DEFAULT_THEME_ID:
            return cls.load_builtin_theme(DEFAULT_THEME_ID)
        return {}

    @classmethod
    def load_local_theme(cls, theme_id):
        path = cls.get_local_theme_path(theme_id)
        return cls.load_theme_file(path) if path else None

    @classmethod
    def load_user_theme(cls, theme_id):
        path = cls.get_user_theme_path(theme_id)
        return cls.load_theme_file(path)

    @classmethod
    def ensure_theme_meta(cls, theme_data, theme_id=None, theme_type=None):
        theme_data = deepcopy(theme_data or {})
        meta = theme_data.setdefault("meta", {})
        if theme_id and not meta.get("id"):
            if cls._looks_like_theme_path(theme_id):
                meta["id"] = str(theme_id).strip()
            else:
                meta["id"] = cls.normalize_theme_id(theme_id)
        if theme_type and not meta.get("type"):
            meta["type"] = theme_type
        if not meta.get("base"):
            meta["base"] = DEFAULT_THEME_ID
        return theme_data

    @classmethod
    def ensure_theme_defaults(cls, theme_data):
        theme_data = deepcopy(theme_data or {})
        if not isinstance(theme_data, dict):
            theme_data = {}
        merged = cls.deep_merge_dict(cls.DEFAULT_THEME_DATA, theme_data)
        return cls._resolve_references(merged, merged)

    @classmethod
    def _extract_base_id(cls, theme_data):
        meta = (theme_data or {}).get("meta", {})
        base_id = meta.get("base") or DEFAULT_THEME_ID

        if cls._looks_like_theme_path(base_id):
            current_id = meta.get("id")
            if current_id and str(base_id).strip() == str(current_id).strip():
                return DEFAULT_THEME_ID
            return str(base_id).strip()

        base_id = cls.normalize_theme_id(base_id)
        if base_id == cls.normalize_theme_id(meta.get("id")):
            return DEFAULT_THEME_ID
        return base_id

    @classmethod
    def _resolve_theme_from_path(cls, path_value, _visited=None, _base_dir=None):
        _visited = _visited or set()

        path = cls._resolve_theme_path_input(path_value, base_dir=_base_dir)
        if path is None:
            return cls.ensure_theme_defaults(cls.load_builtin_theme(DEFAULT_THEME_ID))

        path_key = str(path).lower()
        if path_key in _visited:
            return cls.ensure_theme_defaults(cls.load_builtin_theme(DEFAULT_THEME_ID))

        _visited.add(path_key)

        theme_data = cls.load_theme_file(path)
        if theme_data is None:
            return cls.ensure_theme_defaults(cls.load_builtin_theme(DEFAULT_THEME_ID))

        theme_data = cls.ensure_theme_meta(
            theme_data,
            theme_id=theme_data.get("meta", {}).get("id") or path.stem,
            theme_type=theme_data.get("meta", {}).get("type")
            or ThemePathResolver.SOURCE_FILE,
        )

        base_id = cls._extract_base_id(theme_data)

        if base_id:
            if cls._looks_like_theme_path(base_id):
                base_theme = cls._resolve_theme_from_path(
                    base_id,
                    _visited=_visited,
                    _base_dir=path.parent,
                )
            else:
                if cls.normalize_theme_id(base_id) != cls.normalize_theme_id(
                    theme_data.get("meta", {}).get("id")
                ):
                    base_theme = cls.resolve_theme(base_id, _visited=_visited)
                else:
                    base_theme = {}
            merged = cls.deep_merge_dict(base_theme, theme_data)
            return cls.ensure_theme_defaults(merged)

        return cls.ensure_theme_defaults(theme_data)

    @classmethod
    def _load_registered_theme(cls, theme_id):
        record = ThemeRegistry.get_theme_record(theme_id)
        if not record:
            return None, None
        theme_data = cls.load_theme_file(record["path"])
        return theme_data, record["source"]

    @classmethod
    def resolve_theme(cls, theme_id, _visited=None):
        if cls._looks_like_theme_path(theme_id):
            return cls._resolve_theme_from_path(theme_id, _visited=_visited)

        theme_id = cls.normalize_theme_id(theme_id)
        _visited = _visited or set()

        if theme_id in _visited:
            return cls.ensure_theme_defaults(cls.load_builtin_theme(DEFAULT_THEME_ID))

        _visited.add(theme_id)

        theme_data, theme_source = cls._load_registered_theme(theme_id)

        if theme_data is not None:
            theme_data = cls.ensure_theme_meta(
                theme_data, theme_id=theme_id, theme_type=theme_source
            )
            base_id = cls._extract_base_id(theme_data)

            if base_id:
                if cls._looks_like_theme_path(base_id):
                    base_theme = cls._resolve_theme_from_path(
                        base_id, _visited=_visited
                    )
                else:
                    base_theme = (
                        cls.resolve_theme(base_id, _visited)
                        if base_id != theme_id
                        else {}
                    )
                merged = cls.deep_merge_dict(base_theme, theme_data)
                return cls.ensure_theme_defaults(merged)

            return cls.ensure_theme_defaults(theme_data)

        if theme_id != DEFAULT_THEME_ID:
            return cls.resolve_theme(DEFAULT_THEME_ID, _visited)

        return cls.ensure_theme_defaults({})

    @classmethod
    def get_theme(cls, theme_id=None):
        if theme_id is None:
            return cls.get_current_theme()
        return cls.resolve_theme(theme_id)

    @classmethod
    def set_current_theme(cls, theme_id, save=True):
        if cls._looks_like_theme_path(theme_id):
            cls._current_theme_id = cls._make_config_theme_value(theme_id)
        else:
            cls._current_theme_id = cls.normalize_theme_id(theme_id)

        cls._current_theme_cache = cls.resolve_theme(cls._current_theme_id)

        if save:
            config = cls._read_user_config()
            config["theme"] = cls._current_theme_id
            cls._write_user_config(config)

        return deepcopy(cls._current_theme_cache)

    @classmethod
    def get_current_theme_id(cls):
        return cls._current_theme_id

    @classmethod
    def get_current_theme(cls):
        if cls._current_theme_cache is None:
            stored_theme = cls._read_user_config().get("theme")
            if stored_theme:
                if cls._looks_like_theme_path(stored_theme):
                    cls._current_theme_id = cls._make_config_theme_value(stored_theme)
                else:
                    cls._current_theme_id = cls.normalize_theme_id(stored_theme)
            cls._current_theme_cache = cls.resolve_theme(cls._current_theme_id)
        return deepcopy(cls._current_theme_cache)

    @classmethod
    def reload(cls):
        cls._current_theme_cache = None
        return cls.get_current_theme()

    @classmethod
    def _list_theme_names_from_dir(cls, themes_dir: Path):
        result = []
        if themes_dir.exists() and themes_dir.is_dir():
            for path in sorted(themes_dir.glob(f"*{THEME_FILE_EXTENSION}")):
                if path.is_file():
                    result.append(cls.normalize_theme_id(path.stem))
        return result

    @classmethod
    def list_builtin_themes(cls):
        return ThemeRegistry.list_builtin_themes()

    @classmethod
    def list_local_themes(cls):
        return ThemeRegistry.list_local_themes()

    @classmethod
    def list_user_themes(cls):
        return ThemeRegistry.list_user_themes()

    @classmethod
    def list_themes(cls):
        return ThemeRegistry.list_themes()

    @classmethod
    def theme_exists(cls, theme_id):
        return ThemeRegistry.theme_exists(theme_id)

    @classmethod
    def save_user_theme(cls, theme_id, theme_data):
        cls.ensure_theme_dirs()
        theme_id = cls._safe_theme_id(theme_id)
        theme_data = cls.ensure_theme_meta(
            theme_data, theme_id=theme_id, theme_type="user"
        )
        path = cls.get_user_theme_path(theme_id)
        cls._write_json_file(path, theme_data)
        if cls.get_current_theme_id() == theme_id:
            cls.reload()

    @classmethod
    def create_user_theme(
        cls, theme_id, display_name=None, base_theme_id=DEFAULT_THEME_ID
    ):
        theme_id = cls._safe_theme_id(theme_id)
        if cls._looks_like_theme_path(base_theme_id):
            base_theme_id = str(base_theme_id).strip()
        else:
            base_theme_id = cls.normalize_theme_id(base_theme_id or DEFAULT_THEME_ID)
        data = {
            "meta": {
                "id": theme_id,
                "name": display_name or theme_id,
                "type": "user",
                "base": base_theme_id,
            },
            "colors": {},
            "sizes": {},
            "components": {},
        }
        cls.save_user_theme(theme_id, data)
        return data

    @classmethod
    def delete_user_theme(cls, theme_id):
        path = cls.get_user_theme_path(theme_id)
        if path.exists():
            path.unlink()
        if cls.get_current_theme_id() == cls.normalize_theme_id(theme_id):
            cls.set_current_theme(DEFAULT_THEME_ID)

    @classmethod
    def get_colors(cls, theme_data=None):
        theme_data = theme_data or cls.get_current_theme()
        return deepcopy(theme_data.get("colors", {}))

    @classmethod
    def get_sizes(cls, theme_data=None):
        theme_data = theme_data or cls.get_current_theme()
        return deepcopy(theme_data.get("sizes", {}))

    @classmethod
    def get_color(cls, key, default=None, theme_data=None):
        colors = cls.get_colors(theme_data=theme_data)

        if key in colors:
            return colors.get(key)

        aliases = {
            "text_muted": "muted_text",
            "muted_text": "text_muted",
            "background": "background_color",
            "background_color": "background",
            "surface_alt": "surface_hover",
        }

        alt = aliases.get(key)
        if alt and alt in colors:
            return colors.get(alt)

        return default

    @classmethod
    def get_size(cls, key=None, default=None, theme_data=None):
        sizes = cls.get_sizes(theme_data=theme_data)
        if key is None:
            return deepcopy(sizes)
        value = cls._get_nested_value(sizes, key, default=None)
        if value is not None:
            return value
        return default

    @classmethod
    def get_components(cls, theme_data=None):
        theme_data = theme_data or cls.get_current_theme()
        return deepcopy(theme_data.get("components", {}))

    @classmethod
    def get_component(cls, component_name, theme_data=None, default=None):
        components = cls.get_components(theme_data=theme_data)
        return deepcopy(components.get(component_name, default or {}))

    @classmethod
    def get_component_variant(
        cls, component_name, variant_name="normal", theme_data=None, default=None
    ):
        component = cls.get_component(component_name, theme_data=theme_data, default={})
        variant = component.get(variant_name, default or {})
        if not variant and "normal" in component:
            variant = component.get("normal", default or {})
        return deepcopy(variant)

    @classmethod
    def get_dock(cls, theme_data=None):
        return cls.get_component("dock", theme_data=theme_data)

    @classmethod
    def get_button(cls, variant_name=BUTTON_NORMAL, theme_data=None):
        return cls.get_component_variant("button", variant_name, theme_data=theme_data)

    @classmethod
    def get_icon(cls, variant_name=ICON_NORMAL, theme_data=None):
        return cls.get_component_variant("icon", variant_name, theme_data=theme_data)

    @classmethod
    def get_text(cls, variant_name=TEXT_NORMAL, theme_data=None):
        return cls.get_component_variant("text", variant_name, theme_data=theme_data)

    @classmethod
    def get_input(cls, theme_data=None):
        return cls.get_component("input", theme_data=theme_data)

    @classmethod
    def get_menu(cls, theme_data=None):
        return cls.get_component("menu", theme_data=theme_data)

    @classmethod
    def get_dialog(cls, theme_data=None):
        return cls.get_component("dialog", theme_data=theme_data)

    @classmethod
    def get_tooltip(cls, theme_data=None):
        return cls.get_component("tooltip", theme_data=theme_data)

    @classmethod
    def get_button_color(cls, variant_name=BUTTON_NORMAL, theme_data=None):
        button = cls.get_button(variant_name, theme_data=theme_data)
        return button.get(cls.Components.Button.COLOR) or button.get(
            cls.Components.Button.TEXT_COLOR
        )

    @classmethod
    def get_button_background_color(cls, variant_name=BUTTON_NORMAL, theme_data=None):
        return cls.get_button(variant_name, theme_data=theme_data).get(
            cls.Components.Button.BACKGROUND_COLOR
        )

    @classmethod
    def get_button_hover_color(cls, variant_name=BUTTON_NORMAL, theme_data=None):
        return cls.get_button(variant_name, theme_data=theme_data).get(
            cls.Components.Button.HOVER_COLOR
        )

    @classmethod
    def get_button_pressed_color(cls, variant_name=BUTTON_NORMAL, theme_data=None):
        return cls.get_button(variant_name, theme_data=theme_data).get(
            cls.Components.Button.PRESSED_COLOR
        )

    @classmethod
    def get_button_border_color(cls, variant_name=BUTTON_NORMAL, theme_data=None):
        return cls.get_button(variant_name, theme_data=theme_data).get(
            cls.Components.Button.BORDER_COLOR
        )

    @classmethod
    def get_button_border_width(cls, variant_name=BUTTON_NORMAL, theme_data=None):
        return cls.get_button(variant_name, theme_data=theme_data).get(
            cls.Components.Button.BORDER_WIDTH
        )

    @classmethod
    def get_button_radius(cls, variant_name=BUTTON_NORMAL, theme_data=None):
        return cls.get_button(variant_name, theme_data=theme_data).get(
            cls.Components.Button.BORDER_RADIUS
        )

    @classmethod
    def get_icon_color(cls, variant_name=ICON_NORMAL, theme_data=None):
        return cls.get_icon(variant_name, theme_data=theme_data).get(
            cls.Components.Icon.COLOR
        )

    @classmethod
    def get_icon_size(cls, variant_name=ICON_NORMAL, theme_data=None):
        return cls.get_icon(variant_name, theme_data=theme_data).get(
            cls.Components.Icon.SIZE
        )

    @classmethod
    def get_icon_padding(cls, variant_name=ICON_NORMAL, theme_data=None):
        return cls.get_icon(variant_name, theme_data=theme_data).get(
            cls.Components.Icon.PADDING
        )

    @classmethod
    def get_text_color(cls, variant_name=TEXT_NORMAL, theme_data=None):
        return cls.get_text(variant_name, theme_data=theme_data).get(
            cls.Components.Text.COLOR
        )

    @classmethod
    def get_dock_background_color(cls, theme_data=None):
        return cls.get_dock(theme_data=theme_data).get(
            cls.Components.Dock.BACKGROUND_COLOR
        )

    @classmethod
    def get_dock_border_color(cls, theme_data=None):
        return cls.get_dock(theme_data=theme_data).get(cls.Components.Dock.BORDER_COLOR)

    @classmethod
    def get_dock_border_width(cls, theme_data=None):
        return cls.get_dock(theme_data=theme_data).get(cls.Components.Dock.BORDER_WIDTH)

    @classmethod
    def get_dock_radius(cls, theme_data=None):
        return cls.get_dock(theme_data=theme_data).get(
            cls.Components.Dock.BORDER_RADIUS
        )

    @classmethod
    def get_dialog_background_color(cls, theme_data=None):
        return cls.get_dialog(theme_data=theme_data).get(
            cls.Components.Dialog.BACKGROUND_COLOR
        )

    @classmethod
    def get_dialog_border_color(cls, theme_data=None):
        return cls.get_dialog(theme_data=theme_data).get(
            cls.Components.Dialog.BORDER_COLOR
        )

    @classmethod
    def get_dialog_border_width(cls, theme_data=None):
        return cls.get_dialog(theme_data=theme_data).get(
            cls.Components.Dialog.BORDER_WIDTH
        )

    @classmethod
    def get_dialog_radius(cls, theme_data=None):
        return cls.get_dialog(theme_data=theme_data).get(
            cls.Components.Dialog.BORDER_RADIUS
        )

    @classmethod
    def get_dialog_text_color(cls, theme_data=None):
        return cls.get_dialog(theme_data=theme_data).get(
            cls.Components.Dialog.TEXT_COLOR
        )

    @classmethod
    def get_tooltip_background_color(cls, theme_data=None):
        return cls.get_tooltip(theme_data=theme_data).get(
            cls.Components.Dialog.BACKGROUND_COLOR
        )

    @classmethod
    def get_tooltip_border_color(cls, theme_data=None):
        return cls.get_tooltip(theme_data=theme_data).get(
            cls.Components.Dialog.BORDER_COLOR
        )

    @classmethod
    def get_tooltip_border_width(cls, theme_data=None):
        return cls.get_tooltip(theme_data=theme_data).get(
            cls.Components.Dialog.BORDER_WIDTH
        )

    @classmethod
    def get_tooltip_radius(cls, theme_data=None):
        return cls.get_tooltip(theme_data=theme_data).get(
            cls.Components.Dialog.BORDER_RADIUS
        )

    @classmethod
    def get_tooltip_text_color(cls, theme_data=None):
        return cls.get_tooltip(theme_data=theme_data).get(
            cls.Components.Dialog.TEXT_COLOR
        )

    @staticmethod
    def to_ui_color(color_value):
        value = str(color_value or "").strip()
        if not value.startswith("#"):
            return value

        hex_value = value[1:]

        if len(hex_value) == 8:
            r = hex_value[0:2]
            g = hex_value[2:4]
            b = hex_value[4:6]
            a = hex_value[6:8]
            return f"#{a}{r}{g}{b}"

        return value

    @staticmethod
    def to_ui_qcolor(color_value):
        return QColor(Theme.to_ui_color(color_value))


def deep_merge_dict(base, override):
    return Theme.deep_merge_dict(base, override)


def get_builtin_theme(theme_name):
    return Theme.load_builtin_theme(theme_name)


def get_builtin_themes():
    return {
        theme_name: Theme.load_builtin_theme(theme_name)
        for theme_name in Theme.list_builtin_themes()
    }


def build_default_config():
    from core.config.config_manager import ConfigManager

    return ConfigManager().default_config()
