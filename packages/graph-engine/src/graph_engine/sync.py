from __future__ import annotations

import structlog

from .client import Neo4jClient
from .models import GraphRelationship, GraphSymbol, RelationshipType

logger = structlog.get_logger(__name__)


class GraphSyncEngine:
    def __init__(self, client: Neo4jClient | None = None) -> None:
        self._client = client or Neo4jClient()

    async def ensure_indexes(self) -> None:
        queries = [
            "CREATE INDEX symbol_repo IF NOT EXISTS FOR (s:Symbol) ON (s.repository_id)",
            "CREATE INDEX symbol_name IF NOT EXISTS FOR (s:Symbol) ON (s.name)",
            "CREATE INDEX symbol_kind IF NOT EXISTS FOR (s:Symbol) ON (s.kind)",
            "CREATE INDEX module_path IF NOT EXISTS FOR (m:Module) ON (m.path)",
            "CREATE INDEX module_repo IF NOT EXISTS FOR (m:Module) ON (m.repository_id)",
        ]
        for q in queries:
            try:
                await self._client.execute_write(q)
            except Exception as e:
                logger.warning("index_create_error", query=q[:60], error=str(e))

    async def clear_repository(self, repository_id: str) -> int:
        result = await self._client.execute_write(
            """
            MATCH (n {repository_id: $repo_id})
            DETACH DELETE n
            RETURN count(n) as deleted
            """,
            {"repo_id": repository_id},
        )
        deleted = result[0]["deleted"] if result else 0
        logger.info("clear_repository", repo_id=repository_id, deleted=deleted)
        return deleted

    async def upsert_symbols(
        self,
        symbols: list[GraphSymbol],
        repository_id: str,
        language: str,
    ) -> int:
        if not symbols:
            return 0

        batch_size = 500
        total = 0

        for i in range(0, len(symbols), batch_size):
            batch = symbols[i : i + batch_size]
            params = {
                "repo_id": repository_id,
                "symbols": [
                    {
                        "symbol_id": s.symbol_id,
                        "name": s.name,
                        "kind": s.kind,
                        "file_path": s.file_path,
                        "language": language,
                        "signature": s.signature,
                        "start_line": s.start_line,
                        "end_line": s.end_line,
                        "start_col": s.start_col,
                        "end_col": s.end_col,
                        "parent_name": s.parent_name,
                        "is_exported": s.is_exported,
                    }
                    for s in batch
                ],
            }

            result = await self._client.execute_write(
                """
                UNWIND $symbols AS sym
                MERGE (m:Module {
                    path: sym.file_path,
                    repository_id: $repo_id
                })
                ON CREATE SET
                    m.language = sym.language,
                    m.created_at = datetime()

                MERGE (s:Symbol {symbol_id: sym.symbol_id})
                ON CREATE SET
                    s.name = sym.name,
                    s.kind = sym.kind,
                    s.file_path = sym.file_path,
                    s.language = sym.language,
                    s.repository_id = $repo_id,
                    s.signature = sym.signature,
                    s.start_line = sym.start_line,
                    s.end_line = sym.end_line,
                    s.start_col = sym.start_col,
                    s.end_col = sym.end_col,
                    s.parent_name = sym.parent_name,
                    s.is_exported = sym.is_exported,
                    s.created_at = datetime()
                ON MATCH SET
                    s.name = sym.name,
                    s.kind = sym.kind,
                    s.signature = sym.signature,
                    s.start_line = sym.start_line,
                    s.end_line = sym.end_line,
                    s.parent_name = sym.parent_name,
                    s.is_exported = sym.is_exported,
                    s.updated_at = datetime()

                MERGE (m)-[:CONTAINS]->(s)

                RETURN count(DISTINCT s) as created
                """,
                params,
            )
            total += result[0]["created"] if result else 0

        logger.info("upsert_symbols_done", count=total, repo_id=repository_id)
        return total

    async def upsert_relationships(
        self,
        relationships: list[GraphRelationship],
        repository_id: str,
    ) -> int:
        if not relationships:
            return 0

        grouped: dict[str, list[GraphRelationship]] = {}
        for r in relationships:
            grouped.setdefault(r.relationship_type.value, []).append(r)

        total = 0
        for rel_type, rels in grouped.items():
            batch_size = 500
            for i in range(0, len(rels), batch_size):
                batch = rels[i : i + batch_size]
                params = {
                    "rel_batch": [
                        {
                            "source_id": r.source_id,
                            "target_id": r.target_id,
                            "source_file": r.source_file or "",
                            "target_file": r.target_file or "",
                            "line_number": r.line_number,
                        }
                        for r in batch
                    ],
                }
                query = (
                    f"""
                    UNWIND $rel_batch AS r
                    MATCH (src:Symbol {{symbol_id: r.source_id}})
                    MATCH (tgt:Symbol {{symbol_id: r.target_id}})
                    MERGE (src)-[:{rel_type} {{
                        source_file: r.source_file,
                        target_file: r.target_file,
                        line_number: r.line_number
                    }}]->(tgt)
                    RETURN count(*) as count
                    """
                )
                await self._client.execute_write(query, params)
                total += len(batch)

        logger.info("upsert_relationships_done", count=total, repo_id=repository_id)
        return total

    async def upsert_cross_module_relationships(
        self,
        module_imports: list[dict],
        repository_id: str,
    ) -> int:
        if not module_imports:
            return 0

        batch_size = 500
        total = 0

        for i in range(0, len(module_imports), batch_size):
            batch = module_imports[i : i + batch_size]
            params = {"repo_id": repository_id, "imports": batch}
            await self._client.execute_write(
                """
                UNWIND $imports AS imp
                MATCH (src:Module {path: imp.source, repository_id: $repo_id})
                MATCH (tgt:Module {path: imp.target, repository_id: $repo_id})
                MERGE (src)-[:IMPORTS_MODULE]->(tgt)
                """,
                params,
            )
            total += len(batch)

        logger.info("upsert_cross_module_done", count=total, repo_id=repository_id)
        return total

    async def sync_all(
        self,
        symbols: list[GraphSymbol],
        relationships: list[GraphRelationship],
        repository_id: str,
        language: str,
        module_imports: list[dict] | None = None,
        clear_existing: bool = True,
    ) -> dict:
        await self.ensure_indexes()

        if clear_existing:
            await self.clear_repository(repository_id)

        sym_count = await self.upsert_symbols(symbols, repository_id, language)
        rel_count = await self.upsert_relationships(relationships, repository_id)

        mod_import_count = 0
        if module_imports:
            mod_import_count = await self.upsert_cross_module_relationships(
                module_imports, repository_id
            )

        return {
            "symbols_synced": sym_count,
            "relationships_synced": rel_count,
            "module_imports_synced": mod_import_count,
        }
