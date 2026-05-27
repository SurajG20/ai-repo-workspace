from __future__ import annotations

import structlog

from .client import Neo4jClient

logger = structlog.get_logger(__name__)


class GraphQueries:
    def __init__(self, client: Neo4jClient | None = None) -> None:
        self._client = client or Neo4jClient()

    async def get_call_graph(self, repository_id: str, depth: int = 3) -> list[dict]:
        return await self._client.execute_read(
            """
            MATCH (s:Symbol {repository_id: $repo_id})-[r:CALLS*1..$depth]->(t:Symbol {repository_id: $repo_id})
            WHERE s.kind IN ['function', 'method']
            RETURN DISTINCT
                s.symbol_id AS source_id, s.name AS source_name, s.file_path AS source_file,
                t.symbol_id AS target_id, t.name AS target_name, t.file_path AS target_file,
                length(r) AS distance
            ORDER BY distance
            LIMIT 500
            """,
            {"repo_id": repository_id, "depth": depth},
        )

    async def get_dependency_graph(self, repository_id: str, limit: int = 200) -> list[dict]:
        return await self._client.execute_read(
            """
            MATCH (m1:Module {repository_id: $repo_id})-[r:IMPORTS_MODULE]->(m2:Module {repository_id: $repo_id})
            RETURN m1.path AS source_module, m2.path AS target_module
            ORDER BY source_module, target_module
            LIMIT $limit
            """,
            {"repo_id": repository_id, "limit": limit},
        )

    async def get_class_hierarchy(self, repository_id: str) -> list[dict]:
        return await self._client.execute_read(
            """
            MATCH (child:Symbol {repository_id: $repo_id, kind: 'class'})
                   -[:EXTENDS]->(parent:Symbol {repository_id: $repo_id, kind: 'class'})
            RETURN child.name AS class_name, child.file_path AS file_path,
                   parent.name AS parent_class, parent.file_path AS parent_file
            ORDER BY class_name
            LIMIT 200
            """,
            {"repo_id": repository_id},
        )

    async def get_interfaces(self, repository_id: str) -> list[dict]:
        return await self._client.execute_read(
            """
            MATCH (iface:Symbol {repository_id: $repo_id, kind: 'interface'})
            OPTIONAL MATCH (impl:Symbol {repository_id: $repo_id, kind: 'class'})
                           -[:IMPLEMENTS]->(iface)
            RETURN iface.name AS interface_name, iface.file_path AS file_path,
                   collect(impl.name) AS implementors
            LIMIT 200
            """,
            {"repo_id": repository_id},
        )

    async def get_symbol(self, repository_id: str, symbol_name: str) -> list[dict]:
        return await self._client.execute_read(
            """
            MATCH (s:Symbol {repository_id: $repo_id, name: $name})
            RETURN s.symbol_id AS symbol_id, s.name AS name, s.kind AS kind,
                   s.signature AS signature, s.file_path AS file_path,
                   s.start_line AS start_line, s.end_line AS end_line,
                   s.parent_name AS parent_name, s.is_exported AS is_exported
            LIMIT 10
            """,
            {"repo_id": repository_id, "name": symbol_name},
        )

    async def get_file_symbols(self, repository_id: str, file_path: str) -> list[dict]:
        return await self._client.execute_read(
            """
            MATCH (m:Module {repository_id: $repo_id, path: $path})-[:CONTAINS]->(s:Symbol)
            RETURN s.symbol_id AS symbol_id, s.name AS name, s.kind AS kind,
                   s.signature AS signature, s.start_line AS start_line,
                   s.end_line AS end_line, s.parent_name AS parent_name
            ORDER BY s.start_line
            """,
            {"repo_id": repository_id, "path": file_path},
        )

    async def get_incoming_calls(self, repository_id: str, symbol_name: str) -> list[dict]:
        return await self._client.execute_read(
            """
            MATCH (caller:Symbol {repository_id: $repo_id})-[r:CALLS]->(tgt:Symbol {repository_id: $repo_id, name: $name})
            RETURN caller.name AS caller_name, caller.file_path AS caller_file,
                   caller.kind AS caller_kind, r.line_number AS line_number
            ORDER BY caller_file, line_number
            LIMIT 100
            """,
            {"repo_id": repository_id, "name": symbol_name},
        )

    async def get_outgoing_calls(self, repository_id: str, symbol_name: str) -> list[dict]:
        return await self._client.execute_read(
            """
            MATCH (src:Symbol {repository_id: $repo_id, name: $name})-[r:CALLS]->(callee:Symbol {repository_id: $repo_id})
            RETURN callee.name AS callee_name, callee.file_path AS callee_file,
                   callee.kind AS callee_kind, r.line_number AS line_number
            ORDER BY r.line_number
            LIMIT 100
            """,
            {"repo_id": repository_id, "name": symbol_name},
        )

    async def get_repository_stats(self, repository_id: str) -> dict:
        results = await self._client.execute_read(
            """
            MATCH (s:Symbol {repository_id: $repo_id})
            RETURN s.kind AS kind, count(s) AS count
            ORDER BY count DESC
            """,
            {"repo_id": repository_id},
        )
        return {r["kind"]: r["count"] for r in results}
