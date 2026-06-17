from .constants import QUERY_MODE_NORMAL, QUERY_MODE_APPS


class QueryParser:
    @staticmethod
    def parse(query: str) -> tuple[str, str]:
        query = str(query or "").strip()

        if query.startswith(">"):
            cleaned = query[1:].strip()
            return QUERY_MODE_APPS, cleaned

        return QUERY_MODE_NORMAL, query

    @staticmethod
    def get_mode(query: str) -> str:
        mode, _ = QueryParser.parse(query)
        return mode

    @staticmethod
    def get_query(query: str) -> str:
        _, cleaned = QueryParser.parse(query)
        return cleaned
