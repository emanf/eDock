import os
import subprocess
import sys
import webbrowser
from pathlib import Path

from core.app.app_logging import print_and_log, safe_app_call


class AppContext:
    def __init__(self, config_manager=None, dock=None, app_loader=None):
        self.config_manager = config_manager
        self.dock = dock
        self.app_loader = app_loader

    def set_dock(self, dock):
        self.dock = dock

    def set_app_loader(self, app_loader):
        self.app_loader = app_loader

    def run_file(self, target, cwd=None):
        if not target:
            return False

        target_path = Path(target)

        try:
            if sys.platform.startswith("win"):
                os.startfile(str(target_path))
                return True

            if sys.platform == "darwin":
                subprocess.Popen(["open", str(target_path)], cwd=str(cwd) if cwd else None)
                return True

            subprocess.Popen(["xdg-open", str(target_path)], cwd=str(cwd) if cwd else None)
            return True

        except Exception as e:
            print_and_log(
                message=f"run_file failed for target '{target}'",
                exc=e,
                source="AppContext",
            )
            return False

    def run_command(self, command, cwd=None):
        if not command:
            return False

        try:
            subprocess.Popen(command, cwd=str(cwd) if cwd else None, shell=isinstance(command, str))
            return True
        except Exception as e:
            print_and_log(
                message=f"run_command failed for command '{command}'",
                exc=e,
                source="AppContext",
            )
            return False

    def open_url(self, url):
        if not url:
            return False

        try:
            webbrowser.open(url)
            return True
        except Exception as e:
            print_and_log(
                message=f"open_url failed for '{url}'",
                exc=e,
                source="AppContext",
            )
            return False

    def reveal_path(self, path):
        if not path:
            return False

        path = Path(path)
        if not path.exists():
            return False

        try:
            if sys.platform.startswith("win"):
                subprocess.Popen(["explorer", "/select,", str(path)])
                return True

            if sys.platform == "darwin":
                subprocess.Popen(["open", "-R", str(path)])
                return True

            subprocess.Popen(["xdg-open", str(path.parent)])
            return True

        except Exception as e:
            print_and_log(
                message=f"reveal_path failed for '{path}'",
                exc=e,
                source="AppContext",
            )
            return False

    def app_info(self, app_instance):
        if app_instance is None:
            return None

        return self.safe_app_call(
            app_instance,
            "show_info",
            lambda: app_instance.show_info() if hasattr(app_instance, "show_info") else None,
            default=None,
        )

    def remove_app(self, app_instance):
        if app_instance is None:
            return False

        result = self.safe_app_call(
            app_instance,
            "remove",
            lambda: app_instance.remove() if hasattr(app_instance, "remove") else None,
            default=False,
        )

        if result is False:
            return False

        try:
            if self.dock is not None and hasattr(self.dock, "reload_apps"):
                self.dock.reload_apps()
        except Exception as e:
            print_and_log(
                message="remove_app succeeded but dock.reload_apps() failed",
                exc=e,
                app_instance=app_instance,
                source="AppContext",
            )

        return True

    def request_shortcut(self, app_instance):
        return None

    def safe_app_call(self, app_instance, action_name, func, default=None):
        return safe_app_call(
            func=func,
            default=default,
            action_name=action_name,
            app_instance=app_instance,
            source="AppContext",
        )
