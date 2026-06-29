import importlib.util
import json
import sys
import types

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
                except Exception as e:
                    print_and_log(
                        message="Config manager load failed",
                        exc=e,
                        app_id=None,
                        source="AppLoader",
                    )

                if hasattr(self.config_manager, "data") and isinstance(
                    self.config_manager.data, dict
                ):
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

        if not apps_cfg:
            print_and_log(
                message="No apps found in config manager data",
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
                    print_and_log(
                        message=f"Skipping disabled app '{app_id}'",
                        app_id=app_id,
                        source="AppLoader",
                    )
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
                    print_and_log(
                        message=f"App failed to load: '{app_id}'",
                        app_id=app_id,
                        source="AppLoader",
                    )
                    continue

                try:
                    sort_val = (
                        int(app_cfg.get("sort", app_data.get("sort", 0)))
                        if isinstance(app_cfg, dict)
                        else app_data.get("sort", 0)
                    )
                except Exception:
                    sort_val = int(app_data.get("sort", 0) or 0)

                app_data["sort"] = sort_val

                if isinstance(app_cfg, dict):
                    app_data["shortcut"] = app_cfg.get(
                        "shortcut", app_data.get("shortcut", "")
                    )
                    app_data["enabled"] = bool(app_cfg.get("enabled", True))

                apps.append(app_data)

                print_and_log(
                    message=f"Loaded app '{app_id}'",
                    app_id=app_id,
                    source="AppLoader",
                )

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
        except Exception as e:
            print_and_log(
                message=f"Failed checking direct app path for '{app_id}'",
                exc=e,
                app_id=app_id,
                source="AppLoader",
            )

        try:
            if not APPS_DIR.exists():
                print_and_log(
                    message=f"APPS_DIR does not exist: '{APPS_DIR}'",
                    app_id=app_id,
                    source="AppLoader",
                )
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
                except Exception as e:
                    print_and_log(
                        message=f"Failed reading manifest while searching app '{app_id}'",
                        exc=e,
                        app_id=app_id,
                        source="AppLoader",
                    )
                    continue

                if manifest.get("id") == app_id:
                    return app_dir
        except Exception as e:
            print_and_log(
                message=f"Failed searching APPS_DIR for '{app_id}'",
                exc=e,
                app_id=app_id,
                source="AppLoader",
            )

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

        if not manifest_path.exists():
            print_and_log(
                message=f"Missing app.json: '{manifest_path}'",
                app_id=app_dir.name,
                source="AppLoader",
            )
            return None

        if not app_py_path.exists():
            print_and_log(
                message=f"Missing app.py: '{app_py_path}'",
                app_id=app_dir.name,
                source="AppLoader",
            )
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
            print_and_log(
                message=f"No App class found in '{app_py_path}'",
                app_id=app_id,
                source="AppLoader",
            )
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
            module_base = f"edock_app_{str(app_id).replace('/', '_').replace('-', '_').replace('.', '_')}"
            package_name = f"{module_base}_pkg"
            module_name = f"{package_name}.app"

            spec = importlib.util.spec_from_file_location(
                module_name,
                str(app_py_path),
            )

            if spec is None or spec.loader is None:
                print_and_log(
                    message=f"Could not create module spec for '{app_py_path}'",
                    app_id=app_id,
                    source="AppLoader",
                )
                return None

            inserted = False
            try:
                root = str(get_root_dir())
            except Exception:
                root = None

            if root and root not in sys.path:
                sys.path.insert(0, root)
                inserted = True

            package = types.ModuleType(package_name)
            package.__path__ = [str(app_py_path.parent)]
            package.__package__ = package_name

            module = importlib.util.module_from_spec(spec)
            module.__package__ = package_name

            removed_modules = {}
            for name in list(sys.modules.keys()):
                if name == package_name or name == module_name or name.startswith(
                    f"{package_name}."
                ):
                    removed_modules[name] = sys.modules.pop(name)

            sys.modules[package_name] = package
            sys.modules[module_name] = module

            try:
                spec.loader.exec_module(module)
            except Exception:
                for name, mod in removed_modules.items():
                    sys.modules[name] = mod
                sys.modules.pop(package_name, None)
                sys.modules.pop(module_name, None)
                raise
            finally:
                if inserted:
                    try:
                        sys.path.remove(root)
                    except Exception:
                        pass

            app_class = getattr(module, "App", None)
            if app_class is None:
                print_and_log(
                    message=f"Module loaded but App class was not found: '{app_py_path}'",
                    app_id=app_id,
                    source="AppLoader",
                )

            return app_class

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
            print_and_log(
                message=f"Cannot create instance for '{app_id}': app_class is None",
                app_id=app_id,
                source="AppLoader",
            )
            return None

        constructors = [
            (
                "app_context, manifest, app_dir",
                lambda: app_class(self.app_context, manifest, app_dir),
            ),
            ("app_context", lambda: app_class(self.app_context)),
            ("no arguments", lambda: app_class()),
        ]

        last_type_error = None

        for constructor_name, constructor in constructors:
            try:
                instance = constructor()
                print_and_log(
                    message=f"Created app instance for '{app_id}' using constructor: {constructor_name}",
                    app_id=app_id,
                    source="AppLoader",
                )
                return instance
            except TypeError as e:
                last_type_error = e
                continue
            except Exception as e:
                print_and_log(
                    message=f"Failed creating app instance for '{app_id}' using constructor: {constructor_name}",
                    exc=e,
                    app_id=app_id,
                    source="AppLoader",
                )
                return None

        print_and_log(
            message=f"Failed creating app instance for '{app_id}': no constructor matched",
            exc=last_type_error,
            app_id=app_id,
            source="AppLoader",
        )
        return None

    def safe_app_call(self, app_data, action_name, func, default=None):
        return safe_app_call(
            func=func,
            default=default,
            action_name=action_name,
            app_data=app_data,
            source="AppLoader",
        )

    def get_app_data(self, app_id):
        try:
            aid = str(app_id or "").strip()
        except Exception:
            return None

        if not aid:
            return None

        for a in self.loaded_apps or []:
            try:
                if str(a.get("id", "")).strip() == aid:
                    return a
            except Exception:
                continue

        try:
            app_dir = self._find_app_dir_by_id(aid)
            if app_dir is not None:
                return self._load_single_app(app_dir)
        except Exception:
            pass

        return None
