"""Prompt rendering helpers — turn retrieval hits into grounded context blocks."""

from __future__ import annotations

from typing import Any

from .templates import (
    ARCHITECTURE_PROMPT,
    DEAD_CODE_PROMPT,
    ONBOARDING_PROMPT,
    PR_ANALYSIS_PROMPT,
    QA_SYSTEM_PROMPT,
)

BLOCK_CHAR_BUDGET = 12_000


def format_context_blocks(hits: list[dict], max_chars: int = BLOCK_CHAR_BUDGET) -> str:
    """Render retrieved hits as numbered, citation-ready context blocks."""
    blocks: list[str] = []
    used = 0
    for i, hit in enumerate(hits, start=1):
        header = f"[{i}] {hit.get('kind', 'symbol')} {hit.get('name')} — {hit.get('file_path')}:{hit.get('start_line', 0)}"
        lines: list[str] = []
        if hit.get("signature"):
            lines.append(hit["signature"])
        if hit.get("parent_name"):
            lines.append(f"parent: {hit['parent_name']}")
        block = "\n".join([header, *lines])
        if used + len(block) > max_chars:
            break
        blocks.append(block)
        used += len(block)
    return "\n\n".join(blocks)


def build_qa_messages(
    question: str,
    hits: list[dict],
    repository_name: str,
) -> list[dict[str, str]]:
    context = format_context_blocks(hits)
    system = QA_SYSTEM_PROMPT.format(
        context=context,
    )
    user = (
        f"Repository: {repository_name}\n\n"
        f"Question: {question}\n\n"
        f"Answer with citations to the context blocks above."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def build_dead_code_prompt(candidates: list[dict]) -> str:
    import json

    return DEAD_CODE_PROMPT.format(candidates=json.dumps(candidates, default=str))


def build_pr_analysis_prompt(
    title: str,
    description: str,
    files: list[dict],
    affected: list[dict],
) -> str:
    import json

    return PR_ANALYSIS_PROMPT.format(
        title=title or "(untitled)",
        description=description or "(no description)",
        files=json.dumps(files, default=str),
        affected=json.dumps(affected, default=str),
    )


def build_architecture_prompt(subject: str, hits: list[dict]) -> str:
    context = format_context_blocks(hits)
    return ARCHITECTURE_PROMPT.format(subject=subject, context=context)


def build_onboarding_prompt(inventory: list[dict]) -> str:
    import json

    return ONBOARDING_PROMPT.format(inventory=json.dumps(inventory, default=str))
