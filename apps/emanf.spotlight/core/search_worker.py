import json
from PySide6.QtCore import QObject, Signal

from ..providers.local_apps_provider import LocalAppsProvider
from ..services import RegistryService
from ..providers.registry_provider import RegistryProvider
from ..core.constants import KIND_LOCAL


class SearchWorker(QObject):
    finished = Signal(int, list)

    def __init__(self, search_id: int, query: str, app_ref=None, parent=None):
        super().__init__(parent)
        self.search_id = int(search_id or 0)
        self.query = str(query or "").strip()
        self.app_ref = app_ref
        self._cancelled = False

    def request_cancel(self):
        self._cancelled = True

    def is_cancelled(self):
        return self._cancelled

    def run(self):
        results = []
        try:
            if self.is_cancelled():
                self.finished.emit(self.search_id, [])
                return

            provider = LocalAppsProvider()
            items = provider.search(self.query, worker=self)

            if self.is_cancelled():
                self.finished.emit(self.search_id, [])
                return

            for item in items:
                if self.is_cancelled():
                    self.finished.emit(self.search_id, [])
                    return
                try:
                    results.append(item.to_dict())
                except Exception:
                    if isinstance(item, dict):
                        results.append(item)
        except Exception:
            pass

        try:
            self.finished.emit(self.search_id, results)
        except Exception:
            pass


class AppsSearchWorker(QObject):
    finished = Signal(int, list)

    def __init__(self, search_id: int, query: str, parent=None):
        super().__init__(parent)
        self.search_id = int(search_id or 0)
        self.query = str(query or "").strip()
        self._cancelled = False

    def request_cancel(self):
        self._cancelled = True

    def is_cancelled(self):
        return self._cancelled

    def _get_installed_ids(self) -> set:
        try:
            provider = LocalAppsProvider()
            apps_dir = provider.apps_dir
            installed = set()
            if apps_dir and apps_dir.exists():
                for app_dir in apps_dir.iterdir():
                    if self.is_cancelled():
                        return set()
                    if app_dir.is_dir():
                        installed.add(app_dir.name.lower())
            return installed
        except Exception:
            return set()

    def run(self):
        results = []
        try:
            if self.is_cancelled():
                self.finished.emit(self.search_id, [])
                return

            local_provider = LocalAppsProvider()

            local_results = local_provider.search_local_apps(self.query, worker=self)

            if self.is_cancelled():
                self.finished.emit(self.search_id, [])
                return

            for item in local_results:
                if self.is_cancelled():
                    self.finished.emit(self.search_id, [])
                    return
                try:
                    results.append(item.to_dict())
                except Exception:
                    if isinstance(item, dict):
                        results.append(item)
            try:
                installed_ids = self._get_installed_ids()
                if self.is_cancelled():
                    self.finished.emit(self.search_id, [])
                    return
                registry_service = RegistryService()
                try:
                    registry_service.refresh_packages()
                except Exception:
                    pass

                registry_provider = RegistryProvider(registry_service, installed_ids)
                registry_results = []

                if self.query:
                    registry_results = registry_provider.search(self.query, worker=self)
                else:
                    try:
                        packages = registry_service.get_packages()
                        for pkg in packages:
                            if self.is_cancelled():
                                self.finished.emit(self.search_id, [])
                                return
                            try:
                                normalized = registry_provider._normalize_package(pkg)
                                if not normalized:
                                    continue

                                try:
                                    manifest_url = (
                                        normalized.get("manifest")
                                        or normalized.get("manifest_url")
                                        or None
                                    )
                                    if manifest_url:
                                        try:
                                            text = registry_service._read_text_source(
                                                manifest_url
                                            )
                                            if text:
                                                try:
                                                    mdata = json.loads(text)
                                                    if isinstance(mdata, dict):
                                                        normalized.update({
                                                            k: v for k, v in mdata.items()
                                                        })
                                                except Exception:
                                                    pass
                                        except Exception:
                                            pass

                                except Exception:
                                    pass

                                try:
                                    app_id = str(normalized.get("id") or normalized.get("app_id") or "").strip()
                                    local_provider = LocalAppsProvider()
                                    apps_dir = local_provider.apps_dir
                                    if app_id and apps_dir and apps_dir.exists():
                                        app_json = apps_dir / app_id / "app.json"
                                        if app_json.exists():
                                            try:
                                                aj = json.loads(app_json.read_text(encoding="utf-8"))
                                                if isinstance(aj, dict):
                                                    normalized.update({k: v for k, v in aj.items()})
                                            except Exception:
                                                pass
                                except Exception:
                                    pass

                                sr = registry_provider._package_to_result(normalized)
                                registry_results.append(sr)
                            except Exception:
                                continue
                    except Exception:
                        registry_results = []

                merged = self._merge_local_and_registry(local_results, registry_results)
                results = []
                for item in merged:
                    if self.is_cancelled():
                        self.finished.emit(self.search_id, [])
                        return

                    results.append(item)
            except Exception:
                pass
        except Exception:
            pass

        try:
            self.finished.emit(self.search_id, results)
        except Exception:
            pass

    def _merge_local_and_registry(self, local_results, registry_results):
        local_map = {}
        for item in local_results:
            try:
                d = item.to_dict() if hasattr(item, "to_dict") else dict(item)
                app_id = str(d.get("app_id") or d.get("id") or "").lower().strip()
                if app_id:
                    local_map[app_id] = d
            except Exception:
                continue

        registry_map = {}
        for item in registry_results:
            try:
                d = item.to_dict() if hasattr(item, "to_dict") else dict(item)
                app_id = str(d.get("app_id") or d.get("id") or "").lower().strip()
                if app_id:
                    registry_map[app_id] = d
            except Exception:
                continue

        merged_ids = list(
            dict.fromkeys(list(local_map.keys()) + list(registry_map.keys()))
        )

        merged = []
        for app_id in merged_ids:
            local_item = local_map.get(app_id)
            reg_item = registry_map.get(app_id)

            if reg_item and local_item:
                merged_item = dict(reg_item)

                merged_item["kind"] = KIND_LOCAL
                meta = merged_item.get("metadata", {}) or {}
                meta["installed"] = True
                meta["online_version"] = reg_item.get("version")
                meta["local_version"] = local_item.get("version")
                meta["local_app_id"] = local_item.get("app_id") or local_item.get("id")
                merged_item["metadata"] = meta
                merged.append(merged_item)
            elif reg_item:
                merged_item = dict(reg_item)
                meta = merged_item.get("metadata", {}) or {}
                if meta.get("installed"):
                    meta.setdefault("local_version", None)
                merged_item["metadata"] = meta
                merged.append(merged_item)
            elif local_item:
                merged.append(local_item)

        return merged
