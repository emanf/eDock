import uuid


class AppRuntimeService:
    def __init__(self, context):
        self.context = context
        self.app_registry = {}
        self.instances_by_id = {}
        self.instance_ids_by_app = {}
        self.primary_instance_by_app = {}
        self.windows_by_instance = {}
        self._cleaned_instance_ids = set()

    def _safe_call(self, instance, action_name, func, default=None):
        if self.context is not None and hasattr(self.context, "safe_app_call"):
            try:
                return self.context.safe_app_call(instance, action_name, func, default=default)
            except TypeError:
                try:
                    return self.context.safe_app_call(instance, action_name, func, default)
                except Exception:
                    return default
            except Exception:
                return default

        try:
            return func()
        except Exception:
            return default

    def _app_id(self, app_data):
        return str((app_data or {}).get("id", "")).strip()

    def _new_instance_id(self):
        return str(uuid.uuid4())

    def _create_raw_instance(self, app_data):
        app_class = app_data.get("app_class")
        if not app_class:
            return None

        manifest = app_data.get("manifest", {})
        app_dir = app_data.get("folder_path") or app_data.get("app_dir")

        for args in ((self.context, manifest, app_dir), (self.context,), ()):
            try:
                return app_class(*args)
            except Exception:
                continue

        return None

    def create_instance(self, app_data):
        aid = self._app_id(app_data)
        if not aid:
            return None

        inst = self._create_raw_instance(app_data)
        if not inst:
            return None

        instance_id = self._new_instance_id()

        if hasattr(inst, "set_runtime_service"):
            self._safe_call(
                inst,
                "set_runtime_service",
                lambda: inst.set_runtime_service(self, instance_id),
                default=None,
            )

        self.app_registry[aid] = app_data
        self.instances_by_id[instance_id] = inst
        self.instance_ids_by_app.setdefault(aid, []).append(instance_id)

        allow_multi = False
        if hasattr(inst, "allow_multiple_instance"):
            allow_multi = bool(
                self._safe_call(
                    inst,
                    "allow_multiple_instance",
                    lambda: inst.allow_multiple_instance(),
                    default=False,
                )
            )

        if not allow_multi:
            self.primary_instance_by_app[aid] = instance_id

        if hasattr(inst, "on_load"):
            self._safe_call(
                inst,
                "on_load",
                lambda: inst.on_load(),
                default=None,
            )

        return inst

    def allows_multiple_instance(self, app_data):
        probe = self._create_raw_instance(app_data)
        if not probe:
            return False

        if hasattr(probe, "allow_multiple_instance"):
            return bool(
                self._safe_call(
                    probe,
                    "allow_multiple_instance",
                    lambda: probe.allow_multiple_instance(),
                    default=False,
                )
            )

        return False

    def get_instances(self, app_data):
        aid = self._app_id(app_data)
        if not aid:
            return []

        ids = self.instance_ids_by_app.get(aid, [])
        result = []

        for instance_id in ids:
            inst = self.instances_by_id.get(instance_id)
            if inst is not None:
                result.append(inst)

        return result

    def get_instance(self, app_data):
        aid = self._app_id(app_data)
        if not aid:
            return None

        primary_id = self.primary_instance_by_app.get(aid)
        if primary_id:
            return self.instances_by_id.get(primary_id)

        instances = self.get_instances(app_data)
        return instances[0] if instances else None

    def bind_window(self, instance, window):
        if instance is None or window is None:
            return

        instance_id_getter = getattr(instance, "runtime_instance_id", None)
        if not callable(instance_id_getter):
            return

        instance_id = self._safe_call(
            instance,
            "runtime_instance_id",
            lambda: instance_id_getter(),
            default=None,
        )

        if not instance_id:
            return

        self.windows_by_instance[instance_id] = window

        try:
            window.destroyed.connect(
                lambda *args, iid=instance_id: self.unregister_instance_by_id(iid)
            )
        except Exception:
            pass

    def unregister_instance(self, instance):
        if instance is None:
            return

        instance_id_getter = getattr(instance, "runtime_instance_id", None)
        if not callable(instance_id_getter):
            return

        instance_id = self._safe_call(
            instance,
            "runtime_instance_id",
            lambda: instance_id_getter(),
            default=None,
        )

        if instance_id:
            self.unregister_instance_by_id(instance_id)

    def unregister_instance_by_id(self, instance_id):
        if not instance_id:
            return

        if instance_id in self._cleaned_instance_ids:
            return

        inst = self.instances_by_id.get(instance_id)
        self._cleaned_instance_ids.add(instance_id)

        if inst is None:
            self.windows_by_instance.pop(instance_id, None)
            return

        aid = getattr(inst, "id", None)

        if hasattr(inst, "clear_main_window"):
            self._safe_call(
                inst,
                "clear_main_window",
                lambda: inst.clear_main_window(),
                default=None,
            )

        self.windows_by_instance.pop(instance_id, None)
        self.instances_by_id.pop(instance_id, None)

        if aid in self.instance_ids_by_app:
            self.instance_ids_by_app[aid] = [
                iid for iid in self.instance_ids_by_app[aid]
                if iid != instance_id
            ]
            if not self.instance_ids_by_app[aid]:
                self.instance_ids_by_app.pop(aid, None)

        if self.primary_instance_by_app.get(aid) == instance_id:
            remaining = self.instance_ids_by_app.get(aid, [])
            if remaining:
                self.primary_instance_by_app[aid] = remaining[0]
            else:
                self.primary_instance_by_app.pop(aid, None)

    def create_or_get_instance(self, app_data):
        if self.allows_multiple_instance(app_data):
            return self.create_instance(app_data)

        inst = self.get_instance(app_data)
        if inst is not None:
            return inst

        return self.create_instance(app_data)

    def _activate_existing_instance(self, inst):
        if inst is None:
            return None

        win = None

        if hasattr(inst, "main_window") and callable(inst.main_window):
            win = self._safe_call(
                inst,
                "main_window",
                lambda: inst.main_window(),
                default=None,
            )

        if win is not None:
            if hasattr(inst, "toggle_main_window"):
                toggled = self._safe_call(
                    inst,
                    "toggle_main_window",
                    lambda: inst.toggle_main_window(),
                    default=False,
                )
                if toggled:
                    return inst

            try:
                if hasattr(win, "isVisible") and not win.isVisible():
                    win.show()
                if hasattr(win, "raise_"):
                    win.raise_()
                if hasattr(win, "activateWindow"):
                    win.activateWindow()
                return inst
            except Exception:
                pass

        if hasattr(inst, "on_click"):
            self._safe_call(
                inst,
                "on_click",
                lambda: inst.on_click(),
                default=None,
            )
            return inst

        if hasattr(inst, "run"):
            self._safe_call(
                inst,
                "run",
                lambda: inst.run(),
                default=None,
            )
            return inst

        return inst

    def launch(self, app_data):
        if self.allows_multiple_instance(app_data):
            inst = self.create_instance(app_data)
            if not inst:
                return None

            if hasattr(inst, "on_click"):
                self._safe_call(
                    inst,
                    "on_click",
                    lambda: inst.on_click(),
                    default=None,
                )
            elif hasattr(inst, "run"):
                self._safe_call(
                    inst,
                    "run",
                    lambda: inst.run(),
                    default=None,
                )

            return inst

        inst = self.get_instance(app_data)
        if inst is not None:
            return self._activate_existing_instance(inst)

        inst = self.create_instance(app_data)
        if not inst:
            return None

        if hasattr(inst, "on_click"):
            self._safe_call(
                inst,
                "on_click",
                lambda: inst.on_click(),
                default=None,
            )
        elif hasattr(inst, "run"):
            self._safe_call(
                inst,
                "run",
                lambda: inst.run(),
                default=None,
            )

        return inst

    def unload_all(self):
        for instance_id, inst in list(self.instances_by_id.items()):
            if hasattr(inst, "on_unload"):
                self._safe_call(
                    inst,
                    "on_unload",
                    lambda inst=inst: inst.on_unload(),
                    default=None,
                )

            try:
                win = self.windows_by_instance.get(instance_id)
                if win is not None and hasattr(win, "close"):
                    win.close()
            except Exception:
                pass

        for instance_id in list(self.instances_by_id.keys()):
            self.unregister_instance_by_id(instance_id)

        self.app_registry.clear()
        self.instance_ids_by_app.clear()
        self.primary_instance_by_app.clear()
        self.windows_by_instance.clear()

    def unload_app(self, app_id):
        if not app_id:
            return

        ids = list(self.instance_ids_by_app.get(app_id, []))

        for instance_id in ids:
            inst = self.instances_by_id.get(instance_id)
            if inst is None:
                continue

            if hasattr(inst, "on_unload"):
                try:
                    self._safe_call(
                        inst,
                        "on_unload",
                        lambda inst=inst: inst.on_unload(),
                        default=None,
                    )
                except Exception:
                    pass

            try:
                win = self.windows_by_instance.get(instance_id)
                if win is not None and hasattr(win, "close"):
                    win.close()
            except Exception:
                pass

            try:
                self.unregister_instance_by_id(instance_id)
            except Exception:
                pass

    def broadcast_theme_changed(self):
        for inst in list(self.instances_by_id.values()):
            if hasattr(inst, 'on_theme_changed'):
                self._safe_call(
                    inst,
                    'on_theme_changed',
                    lambda inst=inst: inst.on_theme_changed(),
                    default=None,
                )
