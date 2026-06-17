from difflib import SequenceMatcher
from typing import List, Dict, Any, Set
from ..models import SearchResult
from .base_provider import BaseProvider
from ..services import RegistryService
from ..core.constants import KIND_ONLINE, REGISTRY_RESULTS_LIMIT


class RegistryProvider(BaseProvider):
    def __init__(
        self,
        registry_service: RegistryService = None,
        installed_app_ids: Set[str] = None,
    ):
        self.registry_service = registry_service or RegistryService()
        self.installed_app_ids = installed_app_ids or set()

    def search(self, query: str, worker=None) -> List[SearchResult]:
        query = str(query or "").strip()
        if not query:
            return []

        packages = self.registry_service.get_packages()
        if not packages:
            return []

        results = []
        for package_dict in packages:
            if worker and worker.is_cancelled():
                return []
            try:
                normalized = self._normalize_package(package_dict)
                if not normalized:
                    continue

                score = self._score_package(query, normalized)
                if score <= 0:
                    continue

                result = self._package_to_result(normalized)
                results.append((score, result))
            except Exception as e:
                print(
                    f"Error processing package {package_dict.get('id', 'unknown')}: {e}"
                )

        results.sort(key=lambda x: (-x[0], self._normalize(x[1].title)))

        return [result for _, result in results[:REGISTRY_RESULTS_LIMIT]]

    def _normalize_package(self, package: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(package, dict):
            return None

        app_id = str(
            package.get("id")
            or package.get("app_id")
            or package.get("package")
            or package.get("slug")
            or ""
        ).strip()

        raw_title = str(
            package.get("title")
            or package.get("name")
            or package.get("display_name")
            or app_id
            or ""
        ).strip()

        title = self._format_title(raw_title or app_id)
        if not title:
            return None

        subtitle = str(
            package.get("subtitle")
            or package.get("summary")
            or package.get("description")
            or package.get("author")
            or ""
        ).strip()

        manifest_url = str(
            package.get("manifest")
            or package.get("manifest_url")
            or package.get("url")
            or ""
        ).strip()

        download_url = str(
            package.get("download")
            or package.get("download_url")
            or package.get("install_url")
            or ""
        ).strip()

        version = str(package.get("version") or "").strip()
        author = str(package.get("author") or package.get("developer") or "").strip()
        description = str(
            package.get("description") or package.get("summary") or ""
        ).strip()
        icon = str(package.get("icon") or package.get("icon_url") or "m:apps").strip()

        installed = self._is_installed(app_id, title)

        item = dict(package)
        item.update(
            {
                "id": app_id,
                "app_id": app_id,
                "title": title,
                "name": title,
                "subtitle": subtitle,
                "description": description,
                "author": author,
                "version": version,
                "manifest": manifest_url,
                "manifest_url": manifest_url,
                "download": download_url,
                "download_url": download_url,
                "icon": icon,
                "kind": KIND_ONLINE,
                "type": "online",
                "source": "online",
                "is_online": True,
                "is_installed": installed,
                "installed": installed,
                "_spotlight_source": "online",
            }
        )

        return item

    def _format_title(self, value: str) -> str:
        text = str(value or "").strip()
        if not text:
            return ""

        text = text.replace("_", " ").replace("-", " ").replace(".", " ")
        words = [word for word in text.split() if word]
        if not words:
            return ""

        return " ".join(word[:1].upper() + word[1:].lower() for word in words)

    def _is_installed(self, app_id: str, title: str) -> bool:
        candidates = {
            str(app_id or "").lower(),
            str(title or "").lower(),
        }
        return any(
            candidate and candidate in self.installed_app_ids
            for candidate in candidates
        )

    def _score_package(self, query: str, package: Dict[str, Any]) -> int:
        query = self._normalize(query)
        if not query:
            return 0

        title = self._normalize(package.get("title", ""))
        app_id = self._normalize(package.get("id") or package.get("app_id", ""))
        subtitle = self._normalize(package.get("subtitle", ""))
        description = self._normalize(package.get("description", ""))
        author = self._normalize(package.get("author", ""))

        tags_value = package.get("tags") or package.get("keywords") or []
        if isinstance(tags_value, str):
            tags = [self._normalize(tags_value)]
        elif isinstance(tags_value, (list, tuple, set)):
            tags = [self._normalize(str(tag)) for tag in tags_value]
        else:
            tags = []

        searchable = " ".join(
            [title, app_id, subtitle, description, author, " ".join(tags)]
        ).strip()
        if not searchable:
            return 0

        if query == title or query == app_id:
            return 1000

        score = 0

        if title.startswith(query):
            score = max(score, 900)
        if app_id.startswith(query):
            score = max(score, 850)
        if query in title:
            score = max(score, 760)
        if query in app_id:
            score = max(score, 720)

        if any(tag.startswith(query) for tag in tags):
            score = max(score, 680)
        if any(query in tag for tag in tags):
            score = max(score, 620)

        if query in subtitle:
            score = max(score, 560)
        if query in description:
            score = max(score, 460)
        if query in author:
            score = max(score, 360)

        title_ratio = SequenceMatcher(None, query, title).ratio() if title else 0
        id_ratio = SequenceMatcher(None, query, app_id).ratio() if app_id else 0
        fuzzy_score = int(max(title_ratio, id_ratio) * 500)

        if fuzzy_score >= 230:
            score = max(score, fuzzy_score)

        words = searchable.split()
        for word in words:
            if word.startswith(query):
                score = max(score, 420)
                break

        return score

    def _package_to_result(self, package: Dict[str, Any]) -> SearchResult:
        metadata = {
            k: v
            for k, v in package.items()
            if k not in ("id", "title", "kind", "subtitle", "icon", "description")
        }

        return SearchResult(
            id=package.get("id", ""),
            title=package.get("title", ""),
            kind=KIND_ONLINE,
            subtitle=package.get("subtitle") or package.get("description"),
            icon=package.get("icon", "m:apps"),
            source="registry",
            metadata=metadata,
        )

    def _normalize(self, text: str) -> str:
        return str(text or "").strip().lower()

    def get_name(self) -> str:
        return "RegistryProvider"
