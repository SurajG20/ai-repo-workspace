from __future__ import annotations

import json
import os
from typing import Any

import structlog

from graph_engine import (
    Neo4jClient,
    GraphSyncEngine,
    GraphSymbol,
    GraphRelationship,
    RelationshipType,
)

from ..main import app

logger = structlog.get_logger(__name__)

RELATIONSHIP_TYPE_MAP: dict[str, RelationshipType] = {
    "invokes": RelationshipType.CALLS,
    "calls": RelationshipType.CALLS,
    "extends": RelationshipType.EXTENDS,
    "implements": RelationshipType.IMPLEMENTS,
    "instantiates": RelationshipType.INSTANTIATES,
    "imports": RelationshipType.IMPORTS,
    "uses": RelationshipType.USES,
    "exports": RelationshipType.EXPORTS,
}


@app.task(name="sync_to_neo4j", bind=True, max_retries=2)
def sync_to_neo4j(
    self,
    repository_id: str,
    language: str,
    symbols: list[dict] | None = None,
    relationships: list[dict] | None = None,
    data_file: str | None = None,
) -> dict[str, Any]:
    if data_file:
        logger.info("loading_parse_data_from_file", file=data_file)
        with open(data_file) as f:
            data = json.load(f)
        symbols = data.get("symbols", [])
        relationships = data.get("relationships", [])
        repository_id = data.get("repository_id", repository_id)
        try:
            os.unlink(data_file)
        except OSError:
            pass

    import asyncio

    return asyncio.run(
        _sync_to_neo4j_async(
            self, repository_id, language, symbols or [], relationships or []
        )
    )


async def _sync_to_neo4j_async(
    self,
    repository_id: str,
    language: str,
    symbols: list[dict],
    relationships: list[dict],
) -> dict[str, Any]:
    logger.info("sync_to_neo4j_start", repo_id=repository_id, symbols=len(symbols))

    try:
        engine = GraphSyncEngine()
        client = engine._client

        symbol_id_map: dict[str, str] = {}
        graph_symbols = []
        for s in symbols:
            sid = _build_symbol_id(repository_id, s["file_path"], s["name"])
            symbol_id_map[s["id"]] = sid
            graph_symbols.append(
                GraphSymbol(
                    symbol_id=sid,
                    name=s["name"],
                    kind=s["symbol_kind"],
                    file_path=s["file_path"],
                    language=language,
                    repository_id=repository_id,
                    signature=s.get("signature"),
                    start_line=s.get("start_line", 0),
                    end_line=s.get("end_line", 0),
                    start_col=s.get("start_col", 0),
                    end_col=s.get("end_col", 0),
                    parent_name=s.get("parent_name"),
                    is_exported=s.get("metadata", {}).get("is_exported", False)
                    if s.get("metadata")
                    else False,
                )
            )

        graph_relationships = []
        module_imports = []

        for r in relationships:
            rel_type = RELATIONSHIP_TYPE_MAP.get(
                r["relationship_type"], RelationshipType.USES
            )

            if rel_type == RelationshipType.IMPORTS:
                resolved = r.get("resolved_file")
                if resolved and resolved != r.get("source_file"):
                    module_imports.append({
                        "source": r["source_file"],
                        "target": resolved,
                    })
                continue

            src_id = symbol_id_map.get(
                r.get("source_symbol_id", ""),
                _build_symbol_id(
                    repository_id,
                    r.get("source_file", ""),
                    r["source_symbol"],
                ),
            )
            tgt_id = symbol_id_map.get(
                r.get("target_symbol_id", ""),
                _build_symbol_id(
                    repository_id,
                    r.get("target_file") or r.get("resolved_file") or r.get("source_file", ""),
                    r["target_symbol"],
                ),
            )

            graph_relationships.append(
                GraphRelationship(
                    source_id=src_id,
                    target_id=tgt_id,
                    relationship_type=rel_type,
                    source_file=r.get("source_file", ""),
                    target_file=r.get("resolved_file", ""),
                    line_number=r.get("line_number", 0),
                )
            )

        result = await engine.sync_all(
            symbols=graph_symbols,
            relationships=graph_relationships,
            repository_id=repository_id,
            language=language,
            module_imports=module_imports,
        )

        await client.close()

        logger.info("sync_to_neo4j_done", repo_id=repository_id, result=result)
        return {"status": "completed", **result}

    except Exception as e:
        logger.error("sync_to_neo4j_error", repo_id=repository_id, error=str(e))
        raise self.retry(exc=e)


def _build_symbol_id(repository_id: str, file_path: str, symbol_name: str) -> str:
    parts = [repository_id, file_path, symbol_name]
    return ":".join(parts)
