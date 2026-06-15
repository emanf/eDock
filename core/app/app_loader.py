import importlib.util
import json
import sys

from core.app.app_logging import print_and_log, safe_app_call
from core.paths import APPS_DIR, get_root_dir


class AppLoader:
    def __init__(self, app_context, config_manager):
        self.app_context = app_context
        self.config_manager = config_manager
        self.loaded_apps = []

    def load_apps(self):
        apps = []

        apps_cfg = {}
        try:
            if self.config_manager is not None:
                try:
                    if hasattr(self.config_manager, "load"):
                        self.config_manager.load()
                except Exception:
                    pass

                if hasattr(self.config_manager, "data") and isinstance(self.config_manager.data, dict):
                    apps_cfg = self.config_manager.data.get("apps", {})
                    if not isinstance(apps_cfg, dict):
                        apps_cfg = {}
        except Exception as e:
            print_and_log(
                message="Failed to read apps from config manager",
                exc=e,
                app_id=None,
                source="AppLoader",
            )

        try:
            sorted_items = sorted(
                apps_cfg.items(),
                key=lambda kv: (
                    int(kv[1].get("sort", 0) or 0) if isinstance(kv[1], dict) else 0,
                    kv[0],
                ),
            )
        except Exception:
            sorted_items = list(apps_cfg.items())

        for app_id, app_cfg in sorted_items:
            try:
                if isinstance(app_cfg, dict) and not bool(app_cfg.get("enabled", True)):
                    continue

                app_dir = self._find_app_dir_by_id(app_id)
                if app_dir is None:
                    print_and_log(
                        message=f"App listed in config not found in APPS_DIR: '{app_id}'",
                        app_id=app_id,
                        source="AppLoader",
                    )
                    continue

                app_data = self._load_single_app(app_dir)
                if app_data is None:
                    continue

                try:
                    sort_val = int(
                        app_cfg.get("sort", app_data.get("sort", 0))
                    ) if isinstance(app_cfg, dict) else app_data.get("sort", 0)
                except Exception:
                    sort_val = int(app_data.get("sort", 0) or 0)

                app_data["sort"] = sort_val

                if isinstance(app_cfg, dict):
                    app_data["shortcut"] = app_cfg.get(
                        "shortcut",
                        app_data.get("shortcut", "")
                    )
                    app_data["enabled"] = bool(
                        app_cfg.get("enabled", True)
                    )

                apps.append(app_data)

            except Exception as e:
                print_and_log(
                    message=f"Unexpected failure while loading configured app '{app_id}'",
                    exc=e,
                    app_id=app_id,
                    source="AppLoader",
                )

        apps.sort(
            key=lambda a: (
                int(a.get("sort", 0) or 0),
                a.get("title", "").lower(),
            )
        )

        self.loaded_apps = apps
        return apps

    def _find_app_dir_by_id(self, app_id):
        try:
            candidate = APPS_DIR / app_id
            if candidate.exists() and candidate.is_dir():
                return candidate
        except Exception:
            pass

        try:
            if not APPS_DIR.exists():
                return None

            for app_dir in APPS_DIR.iterdir():
                if not app_dir.is_dir():
                    continue

                manifest_path = app_dir / "app.json"
                if not manifest_path.exists():
                    continue

                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        manifest = json.load(f)
                except Exception:
                    continue

                if manifest.get("id") == app_id:
                    return app_dir
        except Exception:
            pass

        return None

    def is_app_loaded(self, app_id):
        return any(
            str(a.get("id", "")).strip() == str(app_id).strip()
            for a in (self.loaded_apps or [])
        )

    def get_loaded_app_ids(self):
        return [
            str(a.get("id", "")).strip()
            for a in (self.loaded_apps or [])
            if str(a.get("id", "")).strip()
        ]

    def _load_single_app(self, app_dir):
        manifest_path = app_dir / "app.json"
        app_py_path = app_dir / "app.py"

        if not manifest_path.exists() or not app_py_path.exists():
            return None

        app_id = app_dir.name

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception as e:
            print_and_log(
                message=f"Failed to read manifest for '{app_dir.name}'",
                exc=e,
                app_id=app_id,
                source="AppLoader",
            )
            return None

        app_id = manifest.get("id") or app_dir.name
        title = manifest.get("title", app_dir.name)
        icon = manifest.get("icon", "")

        if not manifest.get("id"):
            print_and_log(
                message=f"Missing app id in '{manifest_path}'",
                app_id=app_id,
                source="AppLoader",
            )
            return None

        try:
            self.config_manager.ensure_app(app_id)
        except Exception as e:
            print_and_log(
                message=f"Config ensure_app failed for '{app_id}'",
                exc=e,
                app_id=app_id,
                source="AppLoader",
            )
            return None

        enabled = safe_app_call(
            lambda: self.config_manager.is_app_enabled(app_id, True),
            default=True,
            action_name="config.is_app_enabled",
            app_id=app_id,
            source="AppLoader",
        )

        sort_raw = safe_app_call(
            lambda: self.config_manager.get_app_sort(app_id, 0),
            default=0,
            action_name="config.get_app_sort",
            app_id=app_id,
            source="AppLoader",
        )

        try:
            sort = int(sort_raw)
        except Exception:
            sort = 0

        shortcut = safe_app_call(
            lambda: self.config_manager.get_shortcut(app_id, ""),
            default="",
            action_name="config.get_shortcut",
            app_id=app_id,
            source="AppLoader",
        )

        app_class = self._load_app_class(app_py_path, app_id)
        if app_class is None:
            return None

        return {
            "id": app_id,
            "title": title,
            "icon": icon,
            "manifest": manifest,
            "app_dir": app_dir,
            "app_class": app_class,
            "enabled": enabled,
            "sort": sort,
            "shortcut": shortcut,
        }

    def _load_app_class(self, app_py_path, app_id):
        try:
            module_name = f"edock_app_{str(app_id).replace('/', '_').replace('-', '_').replace('.', '_')}"
            spec = importlib.util.spec_from_file_location(
                module_name,
                str(app_py_path),
            )

            if spec is None or spec.loader is None:
                return None

            module = importlib.util.module_from_spec(spec)
            inserted = False
            try:
                root = str(get_root_dir())
            except Exception:
                root = None

            if root:
                if root not in sys.path:
                    sys.path.insert(0, root)
                    inserted = True

            try:
                spec.loader.exec_module(module)
            finally:
                if inserted:
                    try:
                        sys.path.remove(root)
                    except Exception:
                        pass

            return getattr(module, "App", None)

        except Exception as e:
            print_and_log(
                message=f"Failed to load app class from '{app_py_path}'",
                exc=e,
                app_id=app_id,
                source="AppLoader",
            )
            return None

    def create_instance(self, app_data):
        app_id = app_data.get("id", "_unknown")
        app_class = app_data.get("app_class")
        manifest = app_data.get("manifest")
        app_dir = app_data.get("app_dir")

        if app_class is None:
            return None

        constructors = [
            lambda: app_class(self.app_context, manifest, app_dir),
            lambda: app_class(self.app_context),
            lambda: app_class(),
        ]

        for constructor in constructors:
            try:
                return constructor()
            except TypeError:
                continue
            except Exception:
                return None

        return None

    def safe_app_call(self, app_data, action_name, func, default=None):
        return safe_app_call(
            func=func,
            default=default,
            action_name=action_name,
            app_data=app_data,
            source="AppLoader",
        )