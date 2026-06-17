import json
import os
import time
import urllib.request
import hashlib
from pathlib import Path
from typing import List, Dict, Any

from ..core.constants import (
    APP_ID,
    DEFAULT_INDEXES_FILE,
    USER_INDEXES_FILE,
    REGISTRY_CACHE_TTL,
)


class RegistryService:
    def __init__(self, cache_service=None):
        self.cache_service = cache_service
        self._packages_cache = None
        self._packages_cache_time = None
        self._index_urls_cache = None

    def get_packages(self) -> List[Dict[str, Any]]:
        from ..core.constants import REGISTRY_CACHE_TTL

        if self._packages_cache is not None and self._packages_cache_time is not None:
            try:
                if (time.time() - float(self._packages_cache_time)) < float(
                    REGISTRY_CACHE_TTL
                ):
                    return self._packages_cache
            except Exception:
                pass

        packages = []
        for source in self._get_index_urls():
            try:
                source_packages = self._read_packages_index(source)
                packages.extend(source_packages)
            except Exception as e:
                print(f"Error reading packages from {source}: {e}")

        self._packages_cache = packages
        try:
            self._packages_cache_time = time.time()
        except Exception:
            self._packages_cache_time = None
        return packages

    def clear_cache(self):
        self._packages_cache = None
        self._packages_cache_time = None
        self._index_urls_cache = None

    def _get_index_urls(self) -> List[str]:
        if self._index_urls_cache is not None:
            return self._index_urls_cache

        indexes_path = self._ensure_user_indexes_file()
        if not indexes_path or not os.path.exists(indexes_path):
            return []

        try:
            with open(indexes_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return []

        urls = []

        if isinstance(data, dict):
            urls = (
                data.get("app_indexes") or data.get("indexes") or data.get("urls") or []
            )
        elif isinstance(data, list):
            urls = data

        result = []
        seen = set()
        for url in urls:
            url_str = str(url or "").strip()
            if url_str and url_str not in seen:
                result.append(url_str)
                seen.add(url_str)

        self._index_urls_cache = result
        return result

    def _ensure_user_indexes_file(self) -> Path:
        app_data_dir = self._get_app_data_dir()
        if not app_data_dir:
            return None

        os.makedirs(app_data_dir, exist_ok=True)
        user_indexes_path = app_data_dir / USER_INDEXES_FILE

        if user_indexes_path.exists():
            return user_indexes_path

        default_indexes_path = self._get_default_indexes_path()
        try:
            if default_indexes_path and default_indexes_path.exists():
                import shutil

                shutil.copyfile(str(default_indexes_path), str(user_indexes_path))
            else:
                with open(user_indexes_path, "w", encoding="utf-8") as f:
                    json.dump({"app_indexes": []}, f, indent=2)
        except Exception as e:
            print(f"Error creating user indexes file: {e}")
            if default_indexes_path and default_indexes_path.exists():
                return default_indexes_path
            return None

        return user_indexes_path

    def _get_app_data_dir(self) -> Path:
        try:
            from core.paths import get_app_data_dir

            return Path(get_app_data_dir(APP_ID))
        except Exception:
            pass

        home = Path.home()
        return home / ".edock" / "apps" / APP_ID

    def _get_default_indexes_path(self) -> Path:
        app_dir = Path(__file__).resolve().parent.parent
        return app_dir / DEFAULT_INDEXES_FILE

    def _read_packages_index(self, source: str) -> List[Dict[str, Any]]:
        source = str(source or "").strip()
        if not source:
            return []

        try:
            text = self._read_text_source(source)
            if not text:
                return []

            data = json.loads(text)
        except Exception as e:
            print(f"Error reading packages index from {source}: {e}")
            return []

        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]

        if not isinstance(data, dict):
            return []

        for key in ("packages", "apps", "items", "results", "data"):
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]

        if any(
            key in data
            for key in ("id", "title", "name", "manifest", "manifest_url", "download")
        ):
            return [data]

        return []

    def _read_text_source(self, source: str) -> str:
        if source.startswith(("http://", "https://")):
            try:
                from core.paths import ensure_app_cache_dir

                cache_base = ensure_app_cache_dir(APP_ID)
                network_dir = cache_base / "network"
                network_dir.mkdir(parents=True, exist_ok=True)

                url_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
                cache_file = network_dir / f"{url_hash}.json"

                ttl = float(REGISTRY_CACHE_TTL or 0)
                if cache_file.exists() and ttl > 0:
                    age = time.time() - cache_file.stat().st_mtime
                    if age < ttl:
                        try:
                            return cache_file.read_text(encoding="utf-8")
                        except Exception:
                            pass

                request = urllib.request.Request(
                    source,
                    headers={
                        "User-Agent": "eDock-Spotlight/1.0",
                        "Accept": "application/json,text/plain,*/*",
                    },
                )
                with urllib.request.urlopen(request, timeout=8) as response:
                    text = response.read().decode("utf-8", errors="replace")

                try:
                    cache_file.write_text(text, encoding="utf-8")
                except Exception:
                    pass

                return text
            except Exception:
                request = urllib.request.Request(
                    source,
                    headers={
                        "User-Agent": "eDock-Spotlight/1.0",
                        "Accept": "application/json,text/plain,*/*",
                    },
                )
                with urllib.request.urlopen(request, timeout=8) as response:
                    return response.read().decode("utf-8", errors="replace")

        path = Path(source).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path

        with open(path, "r", encoding="utf-8") as f:
            return f.read()
