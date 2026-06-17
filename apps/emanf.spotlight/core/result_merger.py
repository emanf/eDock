from typing import List, Dict, Set
from ..models import SearchResult
from ..core.constants import (
    KIND_LOCAL,
    PRIORITY_LOCAL,
    PRIORITY_SHORTCUT,
    PRIORITY_EXECUTABLE,
    PRIORITY_GENERAL,
)


class ResultMerger:
    @staticmethod
    def merge(
        results_by_provider: Dict[str, List[SearchResult]], max_results: int = 30
    ) -> List[SearchResult]:
        if not results_by_provider:
            return []

        seen: Dict[str, tuple[SearchResult, int]] = {}

        for provider_name, results in results_by_provider.items():
            for result in results:
                key = ResultMerger._canonical_key(result)
                score = ResultMerger._score_result(result, provider_name)

                if key not in seen:
                    seen[key] = (result, score)
                else:
                    existing_result, existing_score = seen[key]
                    if score > existing_score:
                        seen[key] = (result, score)
                    elif score == existing_score:
                        existing_priority = ResultMerger._get_kind_priority(
                            existing_result.kind
                        )
                        new_priority = ResultMerger._get_kind_priority(result.kind)
                        if new_priority > existing_priority:
                            seen[key] = (result, score)

        sorted_results = sorted(seen.values(), key=lambda x: x[1], reverse=True)

        return [result for result, _ in sorted_results[:max_results]]

    @staticmethod
    def _canonical_key(result: SearchResult) -> str:
        if result.kind == KIND_LOCAL and result.id:
            return f"local:{result.id.lower()}"

        if result.path:
            from pathlib import Path

            stem = Path(result.path).stem.lower()

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

        if result.id:
            return f"id:{result.id.lower()}"

        return f"title:{result.title.lower()}"

    @staticmethod
    def _score_result(result: SearchResult, provider_name: str) -> int:

        kind_priority = ResultMerger._get_kind_priority(result.kind)
        base_score = kind_priority * 100

        return base_score

    @staticmethod
    def _get_kind_priority(kind: str) -> int:
        kind_lower = str(kind or "").lower().strip()

        if kind_lower == KIND_LOCAL:
            return PRIORITY_LOCAL
        elif kind_lower == "shortcut":
            return PRIORITY_SHORTCUT
        elif kind_lower == "executable":
            return PRIORITY_EXECUTABLE

        return PRIORITY_GENERAL
