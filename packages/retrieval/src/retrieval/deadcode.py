from __future__ import annotations

import time

import structlog
from graph_engine import Neo4jClient

logger = structlog.get_logger(__name__)

ENTRY_POINT_PATTERNS = (
    "main",
    "app",
    "application",
    "startup",
    "bootstrap",
    "serve",
    "listen",
    "index",
    "__init__",
    "__main__",
    "handler",
    "config",
    "settings",
    "middleware",
    "router",
    "routes",
    "views",
    "controller",
    "factory",
    "init",
    "create_app",
)

CONSIDERED_LINKS = ("CALLS", "EXTENDS", "IMPLEMENTS", "INSTANTIATES", "USES", "IMPORTS")


class DeadCodeDetector:
    """Finds symbols with no incoming relationships in the call graph.

    Deterministic pass first (unreferenced + not exported), then optional
    LLM-assisted triage in the API layer for false-positive filtering.
    """

    def __init__(self, client: Neo4jClient | None = None) -> None:
        self._client = client or Neo4jClient()

    async def detect(self, repository_id: str, limit: int = 200) -> list[dict]:
        started = time.perf_counter()
        link_pattern = "|".join(CONSIDERED_LINKS)
        try:
            candidates = await self._client.execute_read(
                f"""
                MATCH (s:Symbol {{repository_id: $repo_id}})
                WHERE NOT EXISTS((:Symbol)-[:{link_pattern}]->(s))
                  AND s.is_exported = false
                  AND s.kind IN ['function', 'method', 'class', 'interface', 'variable']
                OPTIONAL MATCH (s)-[r]->(n:Symbol {{repository_id: $repo_id}})
                RETURN s.symbol_id AS symbol_id, s.name AS name, s.kind AS kind,
                       s.file_path AS file_path, s.signature AS signature,
                       s.start_line AS start_line, s.end_line AS end_line,
                       s.parent_name AS parent_name, s.language AS language,
                       count(r) AS outbound_links
                ORDER BY s.file_path, s.start_line
                LIMIT $limit
                """,
                {
                    "repo_id": repository_id,
                    "limit": limit,
                },
            )
            results = [
                {
                    "symbol_id": r["symbol_id"],
                    "name": r["name"],
                    "kind": r["kind"],
                    "file_path": r["file_path"],
                    "signature": r["signature"],
                    "start_line": r["start_line"],
                    "end_line": r["end_line"],
                    "parent_name": r["parent_name"],
                    "language": r["language"],
                    "outbound_links": r["outbound_links"],
                    "entry_point": self._is_entry_point(r["name"]),
                }
                for r in candidates
                if not self._is_entry_point(r["name"])
            ]
            logger.info(
                "dead_code_detected",
                repo=repository_id,
                candidates=len(results),
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
            )
            return results
        except Exception as e:
            logger.warning("dead_code_detection_failed", repo=repository_id, error=str(e))
            return []

    @staticmethod
    def _is_entry_point(name: str) -> bool:
        lowered = name.lower()
        return any(
            lowered == pattern or lowered.startswith(pattern + "_")
            or lowered.startswith("_" + pattern)
            for pattern in ENTRY_POINT_PATTERNS
        )

    async def close(self) -> None:
        await self._client.close()
