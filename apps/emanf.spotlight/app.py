from core.app.app_base import AppBase

from .ui import SpotlightWindow
from .core.controller import Controller


class SpotlightApp(AppBase):
    def on_init(self):
        self.window = None
        self.controller = None

    def on_load(self):
        if self.window is None:
            self.controller = Controller(app_ref=self)
            self.window = SpotlightWindow(app_ref=self, controller=self.controller)
            self.controller.set_window(self.window)

    def on_unload(self):
        if self.window is not None:
            self.window.hide()
        self.window = None
        self.controller = None

    def on_theme_changed(self):
        if self.window is not None and hasattr(self.window, "apply_theme_change"):
            self.window.apply_theme_change()

    def run(self):
        self.window.toggle()

    def clear_search_history(self):
        try:
            if self.window is not None:
                self.window.clear()
                if hasattr(self, "write_json_cache"):
                    self.write_json_cache("history.json", [])
        except Exception as e:
            print(f"Error clearing search history: {e}")


App = SpotlightApp
