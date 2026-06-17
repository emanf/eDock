import json
from pathlib import Path

from core.paths import USER_CONFIG_PATH


class ConfigManager:
    _defaults_cache = None

    def __init__(self, config_path=None):
        self.config_path = Path(config_path) if config_path else USER_CONFIG_PATH
        self.data = self.default_config()
        self.load()

    def default_config(self):
        if ConfigManager._defaults_cache is not None:
            return ConfigManager._defaults_cache.copy()

        defaults_path = Path(__file__).parent / "default.json"
        try:
            with open(defaults_path, "r", encoding="utf-8") as f:
                defaults = json.load(f)
        except Exception:
            defaults = {}

        ConfigManager._defaults_cache = defaults
        return defaults.copy()

    def load(self):
        defaults = self.default_config()

        if not self.config_path.exists():
            self.data = defaults
            self.save()
            return self.data

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
        except Exception:
            self.data = defaults
            self.save()
            return self.data

        if not isinstance(loaded, dict):
            loaded = {}

        merged = defaults.copy()
        merged.update(loaded)

        dock_defaults = defaults.get("dock", {})
        loaded_dock = loaded.get("dock", {})
        if not isinstance(loaded_dock, dict):
            loaded_dock = {}
        merged["dock"] = {**dock_defaults, **loaded_dock}

        loaded_apps = loaded.get("apps", {})
        if not isinstance(loaded_apps, dict):
            loaded_apps = {}
        merged["apps"] = loaded_apps

        self.data = merged

        self._migrate_apps_schema()
        self.save()
        return self.data

    def save(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

    def get(self, key, default=None):
        return self.data.get(key, default)

    def get_dock_config(self):
        return self.data.get("dock", {})

    def ensure_app(self, app_id):
        apps = self.data.setdefault("apps", {})

        if app_id not in apps or not isinstance(apps[app_id], dict):
            apps[app_id] = {"enabled": True, "sort": 0, "shortcut": ""}
            return

        app_cfg = apps[app_id]

        changed = False

        if "enabled" not in app_cfg:
            if "pinned" in app_cfg:
                app_cfg["enabled"] = bool(app_cfg.get("pinned", True))
            else:
                app_cfg["enabled"] = True
            changed = True

        if "sort" not in app_cfg:
            app_cfg["sort"] = 0
            changed = True

        if "shortcut" not in app_cfg:
            app_cfg["shortcut"] = ""
            changed = True

        if changed:
            self.save()

    def _migrate_apps_schema(self):
        apps = self.data.setdefault("apps", {})
        changed = False

        if not isinstance(apps, dict):
            self.data["apps"] = {}
            apps = self.data["apps"]
            changed = True

        sort_counter = 0

        for app_id in list(apps.keys()):
            app_cfg = apps.get(app_id)

            if not isinstance(app_cfg, dict):
                apps[app_id] = {"enabled": True, "sort": sort_counter, "shortcut": ""}
                sort_counter += 1
                changed = True
                continue

            if "enabled" not in app_cfg:
                app_cfg["enabled"] = bool(app_cfg.get("enabled", False))
                changed = True

            if "sort" not in app_cfg:
                app_cfg["sort"] = sort_counter
                changed = True

            if "shortcut" not in app_cfg:
                app_cfg["shortcut"] = ""
                changed = True

            sort_counter += 1

        if changed:
            self.save()

    def get_app_config(self, app_id):
        self.ensure_app(app_id)
        return self.data["apps"].get(app_id, {})

    def get_app_value(self, app_id, key, default=None):
        app_cfg = self.get_app_config(app_id)
        return app_cfg.get(key, default)

    def set_app_value(self, app_id, key, value):
        self.ensure_app(app_id)
        self.data["apps"][app_id][key] = value
        self.save()

    def is_app_enabled(self, app_id, default=True):
        return self.get_app_value(app_id, "enabled", default)

    def set_app_enabled(self, app_id, enabled):
        self.set_app_value(app_id, "enabled", bool(enabled))

    def is_enabled(self, app_id, default=True):
        return self.is_app_enabled(app_id, default)

    def set_enabled(self, app_id, enabled):
        self.set_app_enabled(app_id, enabled)

    def get_app_sort(self, app_id, default=0):
        return self.get_app_value(app_id, "sort", default)

    def set_app_sort(self, app_id, sort_value):
        self.set_app_value(app_id, "sort", int(sort_value))

    def get_shortcut(self, app_id, default=""):
        return self.get_app_value(app_id, "shortcut", default)

    def set_shortcut(self, app_id, shortcut):
        self.set_app_value(app_id, "shortcut", shortcut)
