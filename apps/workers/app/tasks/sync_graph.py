from __future__ import annotations

import json
from typing import Any

import structlog
from graph_engine import GraphSyncEngine
from shared.models.symbol import IndexedSymbol, SymbolRelationship

logger = structlog.get_logger(__name__)


async def graph_sync_stage(
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

    indexed_symbols = [IndexedSymbol.from_payload(s) for s in symbols or []]
    indexed_relationships = [
        SymbolRelationship.from_payload(r) for r in relationships or []
    ]

    logger.info(
        "sync_to_neo4j_start",
        repo_id=repository_id,
        symbols=len(indexed_symbols),
    )

    engine = GraphSyncEngine()
    result = await engine.sync_parsed(
        repository_id=repository_id,
        language=language,
        symbols=indexed_symbols,
        relationships=indexed_relationships,
    )

    logger.info("sync_to_neo4j_done", repo_id=repository_id, result=result)
    return {"status": "completed", **result}
