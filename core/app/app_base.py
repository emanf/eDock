from pathlib import Path
import shutil
from core import paths


class AppBase:
    def __init__(self, context, manifest, app_dir):
        self.context = context
        self.manifest = manifest or {}
        self.app_dir = Path(app_dir)
        self.id = self.manifest.get("id", self.app_dir.name)
        self.title = self.manifest.get("title", self.app_dir.name)
        self.description = self.manifest.get("description", "")
        self.version = self.manifest.get("version", "")
        self.last_modified = self.manifest.get("last_modified", "")
        self.author = self.manifest.get("author", "")
        self.author_email = self.manifest.get("author_email", "")
        self.author_website = self.manifest.get("author_website", "")
        self.icon = self.manifest.get("icon", "")
        self.shortcut_value = self.get_user_value("shortcut", "")
        self.enabled = self.get_user_value("enabled", True)
        self.pinned = self.get_user_value("pinned", True)

        self._runtime_service = None
        self._runtime_instance_id = None
        self._main_window = None

    def on_init(self):
        pass

    def on_load(self):
        pass

    def on_click(self):
        self.run()

    def on_right_click(self):
        return self.get_context_menu()

    def on_unload(self):
        pass

    def on_theme_changed(self):
        pass

    def run(self):
        pass

    def allow_multiple_instance(self):
        return False

    def remove(self):
        self.enabled = False
        self.set_user_value("enabled", False)
        self.on_remove()

    def on_remove(self):
        pass

    def set_runtime_service(self, runtime_service, instance_id=None):
        self._runtime_service = runtime_service
        self._runtime_instance_id = instance_id

    def runtime_service(self):
        return self._runtime_service

    def runtime_instance_id(self):
        return self._runtime_instance_id

    def register_main_window(self, window):
        self._main_window = window
        if self._runtime_service is not None and window is not None:
            try:
                self._runtime_service.bind_window(self, window)
            except Exception:
                pass
        return window

    def main_window(self):
        return self._main_window

    def clear_main_window(self):
        self._main_window = None

    def show_main_window(self):
        win = self.main_window()
        if win is None:
            return False

        try:
            if hasattr(win, "isMinimized") and win.isMinimized():
                if hasattr(win, "showNormal"):
                    win.showNormal()
                else:
                    win.show()
            else:
                win.show()

            if hasattr(win, "raise_"):
                win.raise_()
            if hasattr(win, "activateWindow"):
                win.activateWindow()
            return True
        except Exception:
            return False

    def hide_main_window(self):
        win = self.main_window()
        if win is None:
            return False

        try:
            win.hide()
            return True
        except Exception:
            return False

    def toggle_main_window(self):
        win = self.main_window()
        if win is None:
            return False

        try:
            if hasattr(win, "isVisible") and win.isVisible():
                win.hide()
            else:
                self.show_main_window()
            return True
        except Exception:
            return False

    def close_main_window(self):
        win = self.main_window()
        if win is None:
            return False

        try:
            win.close()
            return True
        except Exception:
            return False

    def shortcut(self, value=None):
        if value is None:
            return self.get_shortcut()
        self.set_shortcut(value)
        return value

    def get_shortcut(self):
        return self.get_user_value("shortcut", "")

    def set_shortcut(self, shortcut):
        self.shortcut_value = str(shortcut or "").strip()
        self.set_user_value("shortcut", self.shortcut_value)
        self.on_shortcut(self.shortcut_value)

    def clear_shortcut(self):
        self.set_shortcut("")

    def on_shortcut(self, shortcut):
        pass

    def get_default_custom_menu(self):
        return {
            "hide_default_menu": False,
            "items": []
        }

    def get_custom_menu(self):
        return self.get_default_custom_menu()

    def get_context_menu(self):
        menu = self.get_custom_menu()

        if not isinstance(menu, dict):
            return self.get_default_custom_menu()

        items = menu.get("items")
        if not isinstance(items, list):
            items = []

        return {
            "hide_default_menu": bool(menu.get("hide_default_menu", False)),
            "items": items
        }

    def show_info(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "version": self.version,
            "last_modified": self.last_modified,
            "author": self.author,
            "author_email": self.author_email,
            "author_website": self.author_website,
            "icon": self.icon,
            "app_dir": str(self.app_dir)
        }

    def request_shortcut(self):
        handler = self._context_value("request_shortcut", None)
        if callable(handler):
            return handler(self)
        return None

    def clear_cache(self):
        cache_dir = self.get_cache_dir()

        if not cache_dir.exists() or not cache_dir.is_dir():
            return False

        removed = False

        for child in cache_dir.iterdir():
            try:
                if child.is_file() or child.is_symlink():
                    child.unlink()
                    removed = True
                elif child.is_dir():
                    shutil.rmtree(child)
                    removed = True
            except Exception:
                pass

        return removed

    def clear_data(self):
        data_dir = self.get_data_dir()

        if not data_dir.exists() or not data_dir.is_dir():
            return False

        removed = False

        for child in data_dir.iterdir():
            try:
                if child.is_file() or child.is_symlink():
                    child.unlink()
                    removed = True
                elif child.is_dir():
                    shutil.rmtree(child)
                    removed = True
            except Exception:
                pass

        return removed

    def get_cache_dir(self):
        return paths.get_app_cache_dir(self.id)

    def get_data_dir(self):
        return paths.get_app_data_dir(self.id)

    def get_user_value(self, key, default=None):
        manager = self.get_config_manager()
        if manager is None:
            return default
        if hasattr(manager, "get_app_value"):
            return manager.get_app_value(self.id, key, default)
        config = self.get_config_data(manager)
        app_data = config.get("apps", {}).get(self.id, {})
        return app_data.get(key, default)

    def set_user_value(self, key, value):
        manager = self.get_config_manager()
        if manager is None:
            return
        if hasattr(manager, "set_app_value"):
            manager.set_app_value(self.id, key, value)
            return
        config = self.get_config_data(manager)
        config.setdefault("apps", {})
        config["apps"].setdefault(self.id, {})
        config["apps"][self.id][key] = value
        save = getattr(manager, "save", None)
        if callable(save):
            save()

    def get_config_manager(self):
        if isinstance(self.context, dict):
            return self.context.get("config_manager") or self.context.get("config")
        if hasattr(self.context, "config_manager"):
            return self.context.config_manager
        if hasattr(self.context, "config"):
            return self.context.config
        return None

    def get_config_data(self, manager):
        if hasattr(manager, "data") and isinstance(manager.data, dict):
            return manager.data
        if hasattr(manager, "config") and isinstance(manager.config, dict):
            return manager.config
        if isinstance(manager, dict):
            return manager
        return {}

    def asset_path(self, filename):
        return self.app_dir / filename

    def has_asset(self, filename):
        return self.asset_path(filename).exists()

    def get_icon_path(self):
        svg_path = self.app_dir / "app.svg"
        if svg_path.exists():
            return str(svg_path)
        return self.icon

    def manifest_value(self, key, default=None):
        return self.manifest.get(key, default)

    def _context_value(self, key, default=None):
        if isinstance(self.context, dict):
            return self.context.get(key, default)
        return getattr(self.context, key, default)
