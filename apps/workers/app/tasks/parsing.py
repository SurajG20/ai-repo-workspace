from __future__ import annotations

import os
import uuid
from typing import Any

import structlog

from parser import (
    TreeSitterParser,
    ModulePathResolver,
    get_extractor,
    get_dependency_extractor,
    detect_language,
)

from .main import app

logger = structlog.get_logger(__name__)


@app.task(name="parse_repository", bind=True, max_retries=2)
def parse_repository(
    self,
    repository_id: str,
    snapshot_id: str,
    repo_path: str,
    file_paths: list[str] | None = None,
) -> dict[str, Any]:
    logger.info("parse_repository_start", repo_id=repository_id)

    parser = TreeSitterParser()
    all_files = _collect_files(repo_path, file_paths)
    known_paths = {_relative_path(p, repo_path) for p in all_files}
    resolver = ModulePathResolver(repo_path, known_paths)

    total = len(all_files)
    symbols_data: list[dict] = []
    rel_data: list[dict] = []
    errors: list[dict] = []

    for i, file_path in enumerate(all_files):
        try:
            rel_path = _relative_path(file_path, repo_path)
            lang = detect_language(rel_path)
            if lang is None:
                continue

            with open(file_path, "rb") as f:
                source = f.read()

            result = parser.parse_file(rel_path, source)
            if result is None:
                continue

            tree, lang_config = result

            extractor = get_extractor(lang_config.name)
            symbols = extractor.extract(tree, source, rel_path)

            dep_extractor = get_dependency_extractor(lang_config.name)
            relationships = dep_extractor.extract(tree, source, rel_path, symbols)

            for sym in symbols:
                symbols_data.append({
                    "id": str(uuid.uuid4()),
                    "file_path": sym.file_path,
                    "name": sym.name,
                    "symbol_kind": sym.symbol_kind.value,
                    "signature": sym.signature,
                    "start_line": sym.start_line,
                    "end_line": sym.end_line,
                    "start_col": sym.start_col,
                    "end_col": sym.end_col,
                    "parent_name": sym.parent_name,
                    "metadata": sym.metadata,
                    "snapshot_id": snapshot_id,
                })

            for rel in relationships:
                resolved = None
                if rel.target_file:
                    resolved = resolver.resolve(
                        rel.source_file, rel.target_file, lang_config.name
                    )
                rel_data.append({
                    "id": str(uuid.uuid4()),
                    "source_file": rel.source_file,
                    "source_symbol": rel.source_symbol,
                    "target_symbol": rel.target_symbol,
                    "target_file": rel.target_file,
                    "resolved_file": resolved,
                    "relationship_type": rel.relationship_type,
                    "line_number": rel.line_number,
                    "metadata": rel.metadata,
                    "snapshot_id": snapshot_id,
                })

        except Exception as e:
            logger.warning("parse_file_error", file=rel_path, error=str(e))
            errors.append({
                "file_path": _relative_path(file_path, repo_path),
                "error_type": type(e).__name__,
                "error_message": str(e),
            })

        if total > 100 and i % 50 == 0:
            logger.info("parse_progress", done=i + 1, total=total)

    logger.info(
        "parse_repository_done",
        repo_id=repository_id,
        symbols=len(symbols_data),
        relationships=len(rel_data),
        errors=len(errors),
    )

    return {
        "status": "completed",
        "symbols_count": len(symbols_data),
        "relationships_count": len(rel_data),
        "errors_count": len(errors),
        "symbols": symbols_data,
        "relationships": rel_data,
        "errors": errors,
        "repository_id": repository_id,
        "snapshot_id": snapshot_id,
    }


def _collect_files(repo_path: str, file_paths: list[str] | None) -> list[str]:
    if file_paths:
        return [os.path.join(repo_path, p) for p in file_paths if os.path.isfile(os.path.join(repo_path, p))]

    files: list[str] = []
    for root, dirs, filenames in os.walk(repo_path):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "__pycache__", "vendor", "target", "build", ".git")]
        for name in filenames:
            ext = os.path.splitext(name)[1].lower()
            if ext in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".py", ".pyi", ".go", ".rs", ".java"):
                files.append(os.path.join(root, name))
    return files


def _relative_path(file_path: str, repo_root: str) -> str:
    return os.path.relpath(file_path, repo_root).replace("\\", "/")
