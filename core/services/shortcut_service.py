try:
    import keyboard
except Exception:
    keyboard = None


class ShortcutService:
    def __init__(self, launch_callback):
        self.launch_callback = launch_callback
        self.handles = {}

    def normalize(self, shortcut):
        value = str(shortcut or "").strip()
        if not value:
            return ""

        replacements = {
            "Ctrl": "ctrl",
            "Control": "ctrl",
            "Alt": "alt",
            "Shift": "shift",
            "Meta": "windows",
            "Win": "windows",
            "Windows": "windows",
            "Cmd": "command",
            "Command": "command",
            "PgUp": "page up",
            "PgDown": "page down",
            "Del": "delete",
            "Ins": "insert",
            "Esc": "esc",
            "Return": "enter",
        }

        parts = [
            part.strip()
            for part in value.replace(" ", "").split("+")
            if part.strip()
        ]

        normalized = []

        for part in parts:
            normalized.append(replacements.get(part, part.lower()))

        return "+".join(normalized)

    def register(self, app_id, shortcut, app_data):
        if not keyboard:
            return

        app_id = str(app_id or "").strip()
        shortcut = self.normalize(shortcut)

        if not app_id or not shortcut:
            return

        self.unregister(app_id)

        try:
            self.handles[app_id] = keyboard.add_hotkey(
                shortcut,
                lambda data=dict(app_data): self.launch_callback(data),
            )
        except Exception:
            pass

    def register_apps(self, apps):
        self.unregister_all()

        for app in apps:
            app_id = str(app.get("id", "") or "").strip()
            shortcut = str(app.get("shortcut", "") or "").strip()

            if app_id and shortcut:
                self.register(app_id, shortcut, app)

    def unregister(self, app_id):
        if not keyboard:
            return

        if app_id not in self.handles:
            return

        try:
            keyboard.remove_hotkey(self.handles.pop(app_id))
        except Exception:
            pass

    def unregister_all(self):
        for app_id in list(self.handles.keys()):
            self.unregister(app_id)