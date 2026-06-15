import os
import shutil
from pathlib import Path

from PySide6.QtCore import QObject, Signal


class SearchWorker(QObject):
    finished = Signal(int, list)

    def __init__(self, search_id, query, local_apps, history):
        super().__init__()
        self.search_id = search_id
        self.query = str(query or "").strip()
        self.local_apps = local_apps if isinstance(local_apps, list) else []
        self.history = history if isinstance(history, list) else []

    def normalize(self, text):
        return str(text or "").strip().lower()

    def words_from_text(self, text):
        text = self.normalize(text)
        for char in ["-", "_", ".", ",", "(", ")", "[", "]", "{", "}", "+", "&", "@", "#"]:
            text = text.replace(char, " ")
        return [word for word in text.split() if word]

    def initials(self, text):
        words = self.words_from_text(text)
        return "".join(word[0] for word in words if word)

    def compact(self, text):
        text = self.normalize(text)
        return "".join(ch for ch in text if ch.isalnum())

    def is_subsequence(self, query, text):
        query = self.compact(query)
        text = self.compact(text)

        if not query or not text:
            return False

        index = 0

        for char in text:
            if index < len(query) and query[index] == char:
                index += 1

        return index == len(query)

    def abbreviation_score(self, query, title):
        query_norm = self.compact(query)
        title_norm = self.compact(title)
        words = self.words_from_text(title)
        initials = self.initials(title)

        if not query_norm:
            return 0

        score = 0

        if initials == query_norm:
            score += 1200
        elif initials.startswith(query_norm):
            score += 900
        elif query_norm in initials:
            score += 650

        if self.is_subsequence(query_norm, initials):
            score += 500

        if self.is_subsequence(query_norm, title_norm):
            score += 260

        if words:
            joined_first_letters = "".join(word[0] for word in words)
            if joined_first_letters.startswith(query_norm):
                score += 700

        return score

    def score(self, query, title, path=""):
        query = self.normalize(query)
        title_norm = self.normalize(title)
        path_norm = self.normalize(path)

        if not query:
            return 0

        score = 0

        if title_norm == query:
            score += 1000
        if title_norm.startswith(query):
            score += 800
        if query in title_norm:
            score += 500

        words = self.words_from_text(title_norm)

        for word in words:
            if word == query:
                score += 350
            elif word.startswith(query):
                score += 250
            elif query in word:
                score += 120

        score += self.abbreviation_score(query, title_norm)

        if path_norm:
            file_stem = self.normalize(Path(path).stem)

            if file_stem == query:
                score += 900
            elif file_stem.startswith(query):
                score += 650
            elif query in file_stem:
                score += 400
            elif query in path_norm:
                score += 80

            score += self.abbreviation_score(query, file_stem)

        return score

    def source_priority(self, item):
        kind = str(item.get("kind", "")).lower().strip()

        if kind == "local":
            return 4
        if kind == "shortcut":
            return 3
        if kind == "executable":
            return 2
        return 1

    def canonical_key(self, item):
        kind = self.normalize(item.get("kind", ""))
        item_id = self.normalize(item.get("id", ""))
        path = self.normalize(item.get("path", ""))
        title = self.normalize(item.get("title", ""))

        if kind == "local" and item_id:
            return f"local:{item_id}"

        if path:
            stem = self.normalize(Path(path).stem)

            if stem in ("notepad", "calc", "mspaint", "cmd", "powershell", "explorer", "regedit", "taskmgr", "control"):
                return f"system:{stem}"

            return f"pathstem:{stem}"

        if item_id:
            return f"id:{item_id}"

        return f"title:{title}"

    def better_item(self, old_item, new_item, old_score, new_score):
        old_priority = self.source_priority(old_item)
        new_priority = self.source_priority(new_item)

        if new_score > old_score:
            return new_item, new_score

        if new_score == old_score and new_priority > old_priority:
            return new_item, new_score

        return old_item, old_score

    def start_menu_dirs(self):
        dirs = []

        program_data = os.environ.get("PROGRAMDATA")
        app_data = os.environ.get("APPDATA")

        if program_data:
            dirs.append(Path(program_data) / "Microsoft" / "Windows" / "Start Menu" / "Programs")

        if app_data:
            dirs.append(Path(app_data) / "Microsoft" / "Windows" / "Start Menu" / "Programs")

        return [x for x in dirs if x.exists()]

    def collect_start_menu_apps(self):
        results = []
        seen = set()

        for root in self.start_menu_dirs():
            try:
                files = []
                files.extend(root.rglob("*.lnk"))
                files.extend(root.rglob("*.url"))
                files.extend(root.rglob("*.appref-ms"))
            except Exception:
                files = []

            for path in files:
                title = path.stem.strip()
                score = self.score(self.query, title, str(path))

                if score <= 0:
                    continue

                key = str(path).lower()

                if key in seen:
                    continue

                seen.add(key)

                results.append({
                    "id": key,
                    "title": title,
                    "kind": "shortcut",
                    "path": str(path),
                    "command": ""
                })

        return results

    def collect_path_executables(self):
        results = []
        seen = set()
        query_norm = self.normalize(self.query)

        direct = shutil.which(query_norm)
        if direct:
            path = Path(direct)
            results.append({
                "id": str(path).lower(),
                "title": path.stem,
                "kind": "executable",
                "path": str(path),
                "command": str(path)
            })
            seen.add(str(path).lower())

        path_env = os.environ.get("PATH", "")

        for folder in path_env.split(os.pathsep):
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
                if not file_path.is_file():
                    continue

                if file_path.suffix.lower() not in (".exe", ".bat", ".cmd", ".ps1"):
                    continue

                score = self.score(self.query, file_path.stem, str(file_path))

                if score <= 0:
                    continue

                key = str(file_path).lower()

                if key in seen:
                    continue

                seen.add(key)

                results.append({
                    "id": key,
                    "title": file_path.stem,
                    "kind": "executable",
                    "path": str(file_path),
                    "command": str(file_path)
                })

        return results

    def collect_common_windows_locations(self):
        results = []
        seen = set()
        windir = os.environ.get("WINDIR", "C:\\Windows")

        folders = [
            Path(windir),
            Path(windir) / "System32",
            Path(windir) / "SysWOW64"
        ]

        for folder in folders:
            if not folder.exists():
                continue

            try:
                children = list(folder.glob("*.exe"))
            except Exception:
                continue

            for file_path in children:
                score = self.score(self.query, file_path.stem, str(file_path))

                if score <= 0:
                    continue

                key = str(file_path).lower()

                if key in seen:
                    continue

                seen.add(key)

                results.append({
                    "id": key,
                    "title": file_path.stem,
                    "kind": "executable",
                    "path": str(file_path),
                    "command": str(file_path)
                })

        return results

    def search_history(self):
        results = []

        for item in self.history:
            if not isinstance(item, dict):
                continue

            score = self.score(self.query, item.get("title", ""), item.get("path", ""))

            if score > 0:
                copy = dict(item)
                copy["_history_score"] = 2000
                results.append(copy)

        return results

    def run(self):
        if not self.query:
            self.finished.emit(self.search_id, self.history)
            return

        pool = []
        pool.extend(self.search_history())
        pool.extend(self.local_apps)
        pool.extend(self.collect_start_menu_apps())
        pool.extend(self.collect_path_executables())
        pool.extend(self.collect_common_windows_locations())

        merged = {}

        for item in pool:
            if not isinstance(item, dict):
                continue

            title = item.get("title", "")
            path = item.get("path", "")
            score = self.score(self.query, title, path) + int(item.get("_history_score", 0))

            if score <= 0:
                continue

            key = self.canonical_key(item)

            if key not in merged:
                merged[key] = (score, item)
            else:
                old_score, old_item = merged[key]
                best_item, best_score = self.better_item(old_item, item, old_score, score)
                merged[key] = (best_score, best_item)

        scored = [(score, item) for score, item in merged.values()]
        scored.sort(key=lambda x: (-x[0], self.normalize(x[1].get("title", ""))))
        self.finished.emit(self.search_id, [item for _, item in scored[:40]])
