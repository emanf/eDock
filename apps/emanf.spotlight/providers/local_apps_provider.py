import os
import shutil
from pathlib import Path
from typing import List, Dict, Any
from ..models import SearchResult
from .base_provider import BaseProvider
from ..core.constants import (
    KIND_LOCAL,
    KIND_SHORTCUT,
    KIND_EXECUTABLE,
    LOCAL_SEARCH_MAX_RESULTS,
)


class LocalAppsProvider(BaseProvider):
    def __init__(self, apps_dir: Path = None):
        self.apps_dir = apps_dir
        if self.apps_dir is None:
            self._discover_apps_dir()

    def _discover_apps_dir(self):
        try:
            from core.paths import get_apps_dir

            self.apps_dir = Path(get_apps_dir())
        except Exception:
            current = Path(__file__).resolve()
            for parent in current.parents:
                apps_candidate = parent / "apps"
                if apps_candidate.exists():
                    self.apps_dir = apps_candidate
                    return
            self.apps_dir = Path.cwd() / "apps"

    def search(self, query: str, worker=None) -> List[SearchResult]:

        query = " ".join(str(query or "").split()).strip()

        if not query:
            try:
                return [
                    self._dict_to_search_result(item)
                    if isinstance(item, dict)
                    else item
                    for item, _ in self._search_local_apps("", worker)
                ]
            except Exception:
                return []
        left, sep, right = query.partition(" ")
        if "." in left:
            try:
                all_items = self._search_local_apps("", worker)
            except Exception:
                all_items = []

            q_left = self._normalize(left)
            candidates = {}
            for item, _ in all_items:
                try:
                    app_id = self._normalize(item.get("app_id") or item.get("id") or "")
                    if not app_id:
                        continue
                    if app_id == q_left:
                        candidates[app_id] = item
                        continue
                    app_parts = [p for p in app_id.split('.') if p]
                    left_parts = [p for p in q_left.split('.') if p]
                    ok = True
                    for i, part in enumerate(left_parts):
                        if i >= len(app_parts) or not app_parts[i].startswith(part):
                            ok = False
                            break
                    if ok:
                        candidates[app_id] = item
                except Exception:
                    continue

            if candidates:
                if not right:
                    result_objects = []
                    for app_id, item in candidates.items():
                        if worker and worker.is_cancelled():
                            return []
                        result_objects.append(self._dict_to_search_result(item))
                    return result_objects

                try:
                    rest_items = self._search_local_apps(right, worker)
                except Exception:
                    rest_items = []

                filtered = []
                for item, score in rest_items:
                    try:
                        aid = self._normalize(item.get("app_id") or item.get("id") or "")
                        if aid in candidates:
                            filtered.append((score, item))
                    except Exception:
                        continue

                filtered.sort(key=lambda x: (-x[0], self._normalize(x[1]["title"])))
                result_objects = []
                for _, item in filtered[:LOCAL_SEARCH_MAX_RESULTS]:
                    if worker and worker.is_cancelled():
                        return []
                    result_objects.append(self._dict_to_search_result(item))
                return result_objects

        query = self._normalize(query)
        results = {}

        sources = [
            self._search_local_apps,
            self._search_start_menu_shortcuts,
            self._search_path_executables,
            self._search_windows_system,
        ]

        for source_func in sources:
            if worker and worker.is_cancelled():
                return []
            try:
                items = source_func(query, worker)
                for item, score in items:
                    if worker and worker.is_cancelled():
                        return []
                    key = self._canonical_key(item)
                    if key not in results:
                        results[key] = (item, score)
                    else:
                        old_item, old_score = results[key]
                        best = self._better_item(old_item, item, old_score, score)
                        results[key] = best

            except Exception as e:
                print(f"Error in {source_func.__name__}: {e}")

        scored = [(score, item) for item, score in results.values()]
        scored.sort(key=lambda x: (-x[0], self._normalize(x[1]["title"])))

        q = query
        qualified = any((not ch.isalnum() and ch != " ") for ch in q)
        if qualified and q:
            exact_matches = []
            q_parts = [p for p in q.split('.') if p]
            for _, item in scored:
                try:
                    app_id = self._normalize(item.get("app_id") or item.get("id") or "")
                    if not app_id:
                        continue

                    if app_id == q:
                        exact_matches.append(item)
                        continue

                    if '.' in q and q_parts:
                        app_parts = [p for p in app_id.split('.') if p]
                        ok = True
                        for i, part in enumerate(q_parts):
                            if i >= len(app_parts):
                                ok = False
                                break
                            if not app_parts[i].startswith(part):
                                ok = False
                                break
                        if ok:
                            exact_matches.append(item)
                except Exception:
                    continue

            if exact_matches:
                result_objects = []
                for item in exact_matches:
                    if worker and worker.is_cancelled():
                        return []
                    result_objects.append(self._dict_to_search_result(item))
                return result_objects

        result_objects = []
        for _, item in scored[:LOCAL_SEARCH_MAX_RESULTS]:
            if worker and worker.is_cancelled():
                return []
            result = self._dict_to_search_result(item)
            result_objects.append(result)

        return result_objects

    def _search_local_apps(self, query: str, worker=None) -> List[tuple]:
        if not self.apps_dir or not self.apps_dir.exists():
            return []

        results = []

        try:
            for app_dir in self.apps_dir.iterdir():
                if worker and worker.is_cancelled():
                    return []
                if not app_dir.is_dir():
                    continue

                app_id = app_dir.name
                app_json_path = app_dir / "app.json"
                if not app_json_path.exists():
                    continue

                try:
                    import json

                    with open(app_json_path, "r", encoding="utf-8") as f:
                        app_data = json.load(f)
                except Exception:
                    continue

                if not isinstance(app_data, dict):
                    continue

                title = str(app_data.get("title", app_id)).strip()

                try:
                    description = str(app_data.get("description", "") or "").strip()
                except Exception:
                    description = ""

                tags_value = app_data.get("keywords") or app_data.get("tags") or []
                tags = []
                try:
                    if isinstance(tags_value, str):
                        tags = [t.strip() for t in tags_value.split(",") if t.strip()]
                    elif isinstance(tags_value, (list, tuple, set)):
                        tags = [str(t).strip() for t in tags_value if str(t).strip()]
                except Exception:
                    tags = []

                app_id_norm = self._normalize(app_id)
                title_norm = self._normalize(title)
                desc_norm = self._normalize(description)
                tags_norm = [self._normalize(t) for t in tags]

                q_norm = self._normalize(query)
                words = [w for w in q_norm.split() if w]

                if words:
                    ok = True
                    for w in words:
                        if not (
                            (w in app_id_norm)
                            or (w in title_norm)
                            or (w in desc_norm)
                            or any(w in t for t in tags_norm)
                        ):
                            ok = False
                            break
                    if not ok:
                        continue

                score = self._score_item(q_norm, title, app_id) if q_norm else 100

                item = {
                    "id": app_id,
                    "title": title,
                    "kind": KIND_LOCAL,
                    "subtitle": description or None,
                    "icon": str(app_data.get("icon", "m:apps")).strip() or "m:apps",
                    "app_id": app_id,
                    "version": app_data.get("version"),
                    "author": app_data.get("author"),
                    "description": description,
                    "keywords": tags,
                }

                results.append((item, score))
        except Exception as e:
            print(f"Error searching local apps: {e}")

        return results

    def _search_start_menu_shortcuts(self, query: str, worker=None) -> List[tuple]:
        results = []
        seen = set()

        for root in self._get_start_menu_dirs():
            if worker and worker.is_cancelled():
                return []
            try:
                files = []
                files.extend(root.rglob("*.lnk"))
                files.extend(root.rglob("*.url"))
                files.extend(root.rglob("*.appref-ms"))
            except Exception:
                files = []

            for path in files:
                if worker and worker.is_cancelled():
                    return []
                title = path.stem.strip()
                score = self._score_item(query, title, str(path))

                if score <= 0:
                    continue

                key = str(path).lower()
                if key in seen:
                    continue

                seen.add(key)

                item = {
                    "id": key,
                    "title": title,
                    "kind": KIND_SHORTCUT,
                    "path": str(path),
                    "command": "",
                    "subtitle": str(path),
                }

                results.append((item, score))

        return results

    def _search_path_executables(self, query: str, worker=None) -> List[tuple]:
        results = []
        seen = set()

        query_norm = self._normalize(query)
        direct = shutil.which(query_norm)
        if direct:
            path = Path(direct)
            key = str(path).lower()
            if key not in seen:
                seen.add(key)
                item = {
                    "id": key,
                    "title": path.stem,
                    "kind": KIND_EXECUTABLE,
                    "path": str(path),
                    "command": str(path),
                    "subtitle": str(path),
                }
                score = self._score_item(query, path.stem, str(path))
                results.append((item, score))

        path_env = os.environ.get("PATH", "")

        for folder in path_env.split(os.pathsep):
            if worker and worker.is_cancelled():
                return []
            if not folder:
                continue

            folder_path = Path(folder)

            if not folder_path.exists() or not folder_path.is_dir():
                continue

            try:
                children = list(folder_path.iterdir())
            except Exception:
                continue

            for file_path in children:
                if worker and worker.is_cancelled():
                    return []
                if not file_path.is_file():
                    continue

                if file_path.suffix.lower() not in (".exe", ".bat", ".cmd", ".ps1"):
                    continue

                score = self._score_item(query, file_path.stem, str(file_path))

                if score <= 0:
                    continue

                key = str(file_path).lower()
                if key in seen:
                    continue

                seen.add(key)

                item = {
                    "id": key,
                    "title": file_path.stem,
                    "kind": KIND_EXECUTABLE,
                    "path": str(file_path),
                    "command": str(file_path),
                    "subtitle": str(file_path),
                }

                results.append((item, score))

        return results

    def _search_windows_system(self, query: str, worker=None) -> List[tuple]:
        results = []
        seen = set()

        windir = os.environ.get("WINDIR", "C:\\Windows")
        folders = [
            Path(windir) / "System32",
            Path(windir) / "SysWOW64",
        ]

        for folder in folders:
            if worker and worker.is_cancelled():
                return []
            if not folder.exists():
                continue

            try:
                children = list(folder.glob("*.exe"))
            except Exception:
                continue

            for file_path in children:
                if worker and worker.is_cancelled():
                    return []
                score = self._score_item(query, file_path.stem, str(file_path))

                if score <= 0:
                    continue

                key = str(file_path).lower()
                if key in seen:
                    continue

                seen.add(key)

                item = {
                    "id": key,
                    "title": file_path.stem,
                    "kind": KIND_EXECUTABLE,
                    "path": str(file_path),
                    "command": str(file_path),
                    "subtitle": str(file_path),
                }

                results.append((item, score))

        return results

    def _get_start_menu_dirs(self) -> List[Path]:
        dirs = []

        program_data = os.environ.get("PROGRAMDATA")
        app_data = os.environ.get("APPDATA")

        if program_data:
            dirs.append(
                Path(program_data) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
            )

        if app_data:
            dirs.append(
                Path(app_data) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
            )

        return [x for x in dirs if x.exists()]

    def search_local_apps(self, query: str, worker=None) -> List[SearchResult]:
        try:
            items = [
                self._dict_to_search_result(item) if isinstance(item, dict) else item
                for item, _ in self._search_local_apps(query or "", worker)
            ]
            return items
        except Exception:
            return []

    def _score_item(self, query: str, title: str, path: str = "") -> int:
        query = self._normalize(query)
        title_norm = self._normalize(title)
        path_norm = self._normalize(path)

        if not query:
            return 0

        score = 0

        if title_norm == query:
            score += 1000
        elif title_norm.startswith(query):
            score += 800
        elif query in title_norm:
            score += 500

        words = self._words_from_text(title_norm)
        for word in words:
            if word == query:
                score += 350
            elif word.startswith(query):
                score += 250
            elif query in word:
                score += 120

        score += self._abbreviation_score(query, title_norm)

        if path_norm:
            file_stem = self._normalize(Path(path).stem)

            if file_stem == query:
                score += 900
            elif file_stem.startswith(query):
                score += 650
            elif query in file_stem:
                score += 400
            elif query in path_norm:
                score += 80

            score += self._abbreviation_score(query, file_stem)

        return score

    def _abbreviation_score(self, query: str, title: str) -> int:
        query_norm = self._compact(query)

        title_norm = self._normalize(title)
        initials = self._initials(title_norm)

        if not query_norm:
            return 0

        score = 0

        if initials == query_norm:
            score += 1200
        elif initials.startswith(query_norm):
            score += 900
        elif query_norm in initials:
            score += 650

        if self._is_subsequence(query_norm, initials):
            score += 500

        compact_title = self._compact(title)
        if self._is_subsequence(query_norm, compact_title):
            score += 260

        return score

    def _canonical_key(self, item: Dict) -> str:
        kind = self._normalize(item.get("kind", ""))
        item_id = self._normalize(item.get("id", ""))
        path = self._normalize(item.get("path", ""))
        title = self._normalize(item.get("title", ""))

        if kind == KIND_LOCAL and item_id:
            return f"local:{item_id}"

        if path:
            stem = self._normalize(Path(path).stem)

            if stem in (
                "notepad",
                "calc",
                "mspaint",
                "cmd",
                "powershell",
                "explorer",
                "regedit",
                "taskmgr",
                "control",
            ):
                return f"system:{stem}"

            return f"pathstem:{stem}"

        if item_id:
            return f"id:{item_id}"

        return f"title:{title}"

    def _better_item(
        self, old_item: Dict, new_item: Dict, old_score: int, new_score: int
    ) -> tuple:
        old_priority = self._get_priority(old_item)
        new_priority = self._get_priority(new_item)

        if new_score > old_score:
            return new_item, new_score

        if new_score == old_score and new_priority > old_priority:
            return new_item, new_score

        return old_item, old_score

    def _get_priority(self, item: Dict) -> int:
        kind = str(item.get("kind", "")).lower().strip()

        if kind == KIND_LOCAL:
            return 4
        elif kind == KIND_SHORTCUT:
            return 3
        elif kind == KIND_EXECUTABLE:
            return 2
        return 1

    def _dict_to_search_result(self, item: Dict) -> SearchResult:
        metadata = {
            k: v
            for k, v in item.items()
            if k not in ("id", "title", "kind", "subtitle", "icon", "path", "command")
        }

        return SearchResult(
            id=item.get("id", ""),
            title=item.get("title", ""),
            kind=item.get("kind", "general"),
            subtitle=item.get("subtitle"),
            icon=item.get("icon"),
            path=item.get("path"),
            command=item.get("command"),
            source="local",
            metadata=metadata,
        )

    def _normalize(self, text: str) -> str:
        return str(text or "").strip().lower()

    def _compact(self, text: str) -> str:
        text = self._normalize(text)
        return "".join(ch for ch in text if ch.isalnum())

    def _words_from_text(self, text: str) -> List[str]:
        text = self._normalize(text)
        for char in [
            "-",
            "_",
            ".",
            ",",
            "(",
            ")",
            "[",
            "]",
            "{",
            "}",
            "+",
            "&",
            "@",
            "#",
        ]:
            text = text.replace(char, " ")
        return [word for word in text.split() if word]

    def _initials(self, text: str) -> str:
        words = self._words_from_text(text)
        return "".join(word[0] for word in words if word)

    def _is_subsequence(self, query: str, text: str) -> bool:
        if not query or not text:
            return False

        index = 0
        for char in text:
            if index < len(query) and query[index] == char:
                index += 1

        return index == len(query)

    def get_name(self) -> str:
        return "LocalAppsProvider"
