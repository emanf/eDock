from pathlib import Path
from PySide6.QtGui import QFontDatabase

from core import paths


MATERIAL_ICONS_FONT_FAMILY = "Material Icons"

MATERIAL_ICON_CODEPOINTS = {
    "home": "\ue88a",
    "search": "\ue8b6",
    "settings": "\ue8b8",
    "power_settings_new": "\ue8ac",
    "terminal": "\ueb8e",
    "folder": "\ue2c7",
    "folder_open": "\ue2c8",
    "file_open": "\ueaf3",
    "description": "\ue873",
    "article": "\uef42",
    "explore": "\ue87a",
    "apps": "\ue5c3",
    "app": "\ue5c3",
    "menu": "\ue5d2",
    "close": "\ue5cd",
    "check": "\ue5ca",
    "done": "\ue876",
    "clear": "\ue14c",
    "add": "\ue145",
    "remove": "\ue15b",
    "delete": "\ue872",
    "edit": "\ue3c9",
    "save": "\ue161",
    "download": "\uf090",
    "upload": "\uf09b",
    "refresh": "\ue5d5",
    "sync": "\ue627",
    "restart_alt": "\uf053",
    "logout": "\ue9ba",
    "login": "\uea77",
    "lock": "\ue897",
    "lock_open": "\ue898",
    "visibility": "\ue8f4",
    "visibility_off": "\ue8f5",
    "favorite": "\ue87d",
    "favorite_border": "\ue87e",
    "star": "\ue838",
    "star_border": "\ue83a",
    "info": "\ue88e",
    "help": "\ue887",
    "warning": "\ue002",
    "error": "\ue000",
    "notifications": "\ue7f4",
    "mail": "\ue158",
    "email": "\ue0be",
    "chat": "\ue0b7",
    "message": "\ue0c9",
    "volume_up": "\ue050",
    "volume_down": "\ue04d",
    "volume_off": "\ue04f",
    "play_arrow": "\ue037",
    "pause": "\ue034",
    "stop": "\ue047",
    "image": "\ue3f4",
    "photo": "\ue410",
    "photo_camera": "\ue412",
    "palette": "\ue40a",
    "brush": "\ue3ae",
    "dashboard": "\ue871",
    "extension": "\ue87b",
    "widgets": "\ue1bd",
    "view_module": "\ue8f0",
    "view_list": "\ue8ef",
    "grid_view": "\ue9b0",
    "list": "\ue896",
    "filter_list": "\ue152",
    "sort": "\ue164",
    "tune": "\ue429",
    "more_vert": "\ue5d4",
    "more_horiz": "\ue5d3",
    "open_in_new": "\ue89e",
    "fullscreen": "\ue5d0",
    "fullscreen_exit": "\ue5d1",
    "launch": "\ue895",
    "arrow_back": "\ue5c4",
    "arrow_forward": "\ue5c8",
    "arrow_upward": "\ue5d8",
    "arrow_downward": "\ue5db",
    "keyboard_arrow_up": "\ue316",
    "keyboard_arrow_down": "\ue313",
    "keyboard_arrow_left": "\ue314",
    "keyboard_arrow_right": "\ue315",
    "chevron_left": "\ue5cb",
    "chevron_right": "\ue5cc",
    "expand_less": "\ue5ce",
    "expand_more": "\ue5cf",
    "undo": "\ue166",
    "redo": "\ue15a",
    "history": "\ue889",
    "schedule": "\ue8b5",
    "calendar_today": "\ue935",
    "event": "\ue878",
    "timer": "\ue425",
    "computer": "\ue30a",
    "desktop_windows": "\ue30c",
    "laptop": "\ue31e",
    "phone_android": "\ue324",
    "devices": "\ue1b1",
    "keyboard": "\ue312",
    "mouse": "\ue323",
    "memory": "\ue322",
    "storage": "\ue1db",
    "dns": "\ue875",
    "code": "\ue86f",
    "bug_report": "\ue868",
    "build": "\ue869",
    "construction": "\uea3c",
    "security": "\ue32a",
    "shield": "\ue9e0",
    "verified": "\uef76",
    "key": "\ue73c",
    "wifi": "\ue63e",
    "wifi_off": "\ue648",
    "bluetooth": "\ue1a7",
    "battery_full": "\ue1a4",
    "dark_mode": "\ue51c",
    "light_mode": "\ue518",
    "language": "\ue894",
    "public": "\ue80b",
    "location_on": "\ue0c8",
    "map": "\ue55b",
    "place": "\ue55f",
    "navigation": "\ue55d",
    "shopping_cart": "\ue8cc",
    "shopping_bag": "\uf1cc",
    "store": "\ue8d1",
    "payments": "\uef63",
    "payment": "\ue8a1",
    "credit_card": "\ue870",
    "work": "\ue8f9",
    "business": "\ue0af",
    "school": "\ue80c",
    "science": "\uea4b",
    "health_and_safety": "\ue1d5",
    "restaurant": "\ue56c",
    "flight": "\ue539",
    "directions_car": "\ue531",
    "hotel": "\ue53a",
    "inventory": "\ue179",
    "archive": "\ue149",
    "print": "\ue8ad",
    "qr_code": "\uef6b",
    "analytics": "\uef3e",
    "bar_chart": "\ue26b",
    "pie_chart": "\ue6c4",
    "task": "\uf075",
    "task_alt": "\ue2e6",
    "check_circle": "\ue86c",
    "cancel": "\ue5c9",
    "radio_button_checked": "\ue837",
    "radio_button_unchecked": "\ue836",
    "check_box": "\ue834",
    "toggle_on": "\ue9f6",
    "toggle_off": "\ue9f5",
    "add_circle": "\ue147",
    "remove_circle": "\ue15c",
    "block": "\ue14b",
    "flag": "\ue153",
    "bolt": "\uea0b",
    "flash_on": "\ue3e7",
    "auto_awesome": "\ue65f",
    "emoji_events": "\uea23",
    "rocket_launch": "\ueb9b",
    "hub": "\ue9f4",
    "dock": "\ue30e",
    "web": "\ue051",
    "window": "\uf088",
    "space_dashboard": "\ue66b"
}


def normalize_material_icon_name(name):
    return str(name).strip().lower().replace("-", "_").replace(" ", "_")


def material_icon_font_family():
    return MATERIAL_ICONS_FONT_FAMILY


def load_material_icons_font(font_path):
    path = Path(font_path)

    if not path.exists():
        return False

    font_id = QFontDatabase.addApplicationFont(str(path))

    return font_id != -1


def find_material_icons_font():
    root = paths.get_assets_dir()
    path = root / "fonts" / "MaterialIcons-Regular.ttf"

    if path.exists():
        return path

    return None


def ensure_material_icons_font():
    path = find_material_icons_font()

    if path is not None:
        load_material_icons_font(path)

    return MATERIAL_ICONS_FONT_FAMILY


def custom_material_icon(value):
    text = str(value).strip()

    if not text.startswith("m:"):
        return ""

    code = text[2:].strip()

    if len(code) == 1:
        return code

    if code.startswith("\\\\u"):
        code = code[3:]
    elif code.startswith("\\u"):
        code = code[2:]
    elif code.startswith("0x"):
        code = code[2:]
    else:
        return ""

    try:
        return chr(int(code, 16))
    except ValueError:
        return ""


def get_material_icon(name, fallback=""):
    text = str(name).strip()

    if text.startswith("m:"):
        raw = text[2:].strip()
        key = normalize_material_icon_name(raw)

        if key in MATERIAL_ICON_CODEPOINTS:
            return MATERIAL_ICON_CODEPOINTS[key]

        icon = custom_material_icon(text)

        if icon:
            return icon

        return fallback

    key = normalize_material_icon_name(text)

    return MATERIAL_ICON_CODEPOINTS.get(key, fallback)


def material_icon_glyph(name, fallback=""):
    return get_material_icon(name, fallback)


def has_material_icon(name):
    return get_material_icon(name, "") != ""


class MaterialIcons:
    FONT_FAMILY = MATERIAL_ICONS_FONT_FAMILY
    ICONS = MATERIAL_ICON_CODEPOINTS
    _font_loaded = False

    @staticmethod
    def ensure_font():
        if not MaterialIcons._font_loaded:
            ensure_material_icons_font()
            MaterialIcons._font_loaded = True

        return MATERIAL_ICONS_FONT_FAMILY

    @staticmethod
    def load_font(font_path):
        loaded = load_material_icons_font(font_path)

        if loaded:
            MaterialIcons._font_loaded = True

        return loaded

    @staticmethod
    def font_family():
        return MATERIAL_ICONS_FONT_FAMILY

    @staticmethod
    def normalize(name):
        return normalize_material_icon_name(name)

    @staticmethod
    def custom(value):
        return custom_material_icon(value)

    @staticmethod
    def get(name, fallback=""):
        return get_material_icon(name, fallback)

    @staticmethod
    def glyph(name, fallback=""):
        return material_icon_glyph(name, fallback)

    @staticmethod
    def has(name):
        return has_material_icon(name)