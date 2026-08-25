from __future__ import annotations

import json
import os
import tempfile
from typing import Any

import structlog
from parser import (
    ModulePathResolver,
    TreeSitterParser,
    detect_language,
    get_dependency_extractor,
    get_extractor,
    to_indexed_relationship,
    to_indexed_symbol,
)

logger = structlog.get_logger(__name__)


async def parse_stage(
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
                indexed = to_indexed_symbol(
                    sym,
                    repository_id=repository_id,
                    snapshot_id=snapshot_id or None,
                    language=lang_config.name,
                )
                symbols_data.append(indexed.to_payload())

            for rel in relationships:
                resolved = None
                if rel.target_file:
                    resolved = resolver.resolve(
                        rel.source_file, rel.target_file, lang_config.name
                    )
                indexed_rel = to_indexed_relationship(
                    rel,
                    repository_id=repository_id,
                    snapshot_id=snapshot_id or None,
                    resolved_target_file=resolved,
                )
                rel_data.append(indexed_rel.to_payload())

        except Exception as e:
            logger.warning("parse_file_error", file=rel_path, error=str(e))
            errors.append({
                "file_path": _relative_path(file_path, repo_path),
                "error_type": type(e).__name__,
                "error_message": str(e),
            })

        if total > 100 and i % 50 == 0:
            logger.info("parse_progress", done=i + 1, total=total)

    symbol_count = len(symbols_data)
    rel_count = len(rel_data)

    logger.info(
        "parse_repository_done",
        repo_id=repository_id,
        symbols=symbol_count,
        relationships=rel_count,
        errors=len(errors),
    )

    result = {
        "status": "completed",
        "symbols_count": symbol_count,
        "relationships_count": rel_count,
        "errors_count": len(errors),
        "repository_id": repository_id,
        "snapshot_id": snapshot_id,
        "language": _detect_language(all_files),
    }

    total_items = symbol_count + rel_count
    if total_items > 5000:
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", prefix=f"parse_{repository_id}_", delete=False
        )
        json.dump({
            "symbols": symbols_data,
            "relationships": rel_data,
            "errors": errors,
            "repository_id": repository_id,
            "snapshot_id": snapshot_id,
        }, tmp, default=str)
        tmp.flush()
        result["data_file"] = tmp.name
        logger.warning(
            "parse_large_result_written_to_file",
            repo_id=repository_id,
            items=total_items,
            file=tmp.name,
        )
    else:
        result["symbols"] = symbols_data
        result["relationships"] = rel_data
        result["errors"] = errors

    return result


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


_LANGUAGE_BY_EXT = {
    ".ts": "typescript", ".tsx": "typescript", ".js": "javascript",
    ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".py": "python", ".pyi": "python",
    ".go": "go", ".rs": "rust", ".java": "java",
}


def _detect_language(files: list[str]) -> str:
    counts: dict[str, int] = {}
    for f in files:
        ext = os.path.splitext(f)[1].lower()
        lang = _LANGUAGE_BY_EXT.get(ext)
        if lang:
            counts[lang] = counts.get(lang, 0) + 1
    if not counts:
        return ""
    return max(counts, key=counts.get)
