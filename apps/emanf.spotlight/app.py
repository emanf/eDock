from core.app.app_base import AppBase

from .spotlight_window import SpotlightWindow

class App(AppBase):
    def on_init(self):
        self.window = None

    def on_load(self):
        if self.window is None:
            self.window = SpotlightWindow(self)

    def on_unload(self):
        if self.window is not None:
            self.window.hide()
        self.window = None

    def on_theme_changed(self):
        if self.window is not None and hasattr(self.window, '_apply_style'):
            self.window._apply_style()
            
    def run(self):
        self.window.toggle()

    def clear_search_history(self):
        try:
            self.write_json_cache("history.json", [])
        except Exception:
            pass

        if self.window is not None:
            self.window.current_results = []
            if self.window.input is not None:
                self.window.input.clear()
            self.window.refresh_list()
