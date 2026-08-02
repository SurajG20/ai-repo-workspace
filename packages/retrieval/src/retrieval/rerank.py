from __future__ import annotations

from collections import defaultdict

from .models import RetrievalHit, SearcherResult

RRF_K = 60


def reciprocal_rank_fusion(
    searcher_results: list[SearcherResult],
    limit: int,
) -> list[RetrievalHit]:
    """Fuse per-source ranked lists with Reciprocal Rank Fusion.

    Each hit's score is the sum of 1/(k + rank) across every source that
    returned it; hits matching more retrieval strategies naturally rank
    higher regardless of raw score scales.
    """

    scores: dict[str, float] = defaultdict(float)
    best_hit: dict[str, RetrievalHit] = {}
    sources: dict[str, set[str]] = defaultdict(set)

    for result in searcher_results:
        for rank, hit in enumerate(result.hits, start=1):
            scores[hit.symbol_id] += 1.0 / (RRF_K + rank)
            sources[hit.symbol_id].add(result.source.value)
            if (
                hit.symbol_id not in best_hit
                or hit.score > best_hit[hit.symbol_id].score
            ):
                best_hit[hit.symbol_id] = hit

    fused: list[RetrievalHit] = []
    for symbol_id, score in sorted(scores.items(), key=lambda kv: kv[1], reverse=True):
        hit = best_hit[symbol_id]
        hit.score = score
        hit.sources = sorted(sources[symbol_id])
        fused.append(hit)
        if len(fused) >= limit:
            break

    for i, hit in enumerate(fused, start=1):
        hit.rank = i

    return fused
