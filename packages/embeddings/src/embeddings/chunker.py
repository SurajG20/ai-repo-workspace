from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)


def chunk_symbol(
    symbol_name: str,
    kind: str,
    signature: str | None,
    file_path: str,
    parent_name: str | None = None,
) -> str:
    parts: list[str] = []

    scope = f":{parent_name}" if parent_name else ""
    header = f"[{kind.upper()}] {symbol_name}{scope}"
    parts.append(header)

    if signature:
        parts.append(signature)

    parts.append(f"@ {file_path}")

    return "\n".join(parts)


def chunk_from_parse_result(symbol: dict) -> str:
    return chunk_symbol(
        symbol_name=symbol.get("name", "unknown"),
        kind=symbol.get("symbol_kind", "unknown"),
        signature=symbol.get("signature"),
        file_path=symbol.get("file_path", ""),
        parent_name=symbol.get("parent_name"),
    )


def chunk_module(file_path: str, language: str, symbol_names: list[str]) -> str:
    names = ", ".join(symbol_names[:20])
    if len(symbol_names) > 20:
        names += f" ... ({len(symbol_names)} total)"
    return f"[MODULE] {file_path}\nLanguage: {language}\nSymbols: {names}"
