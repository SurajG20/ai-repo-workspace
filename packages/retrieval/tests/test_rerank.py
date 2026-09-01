from retrieval.models import RetrievalHit, SearcherResult, SearchSource
from retrieval.rerank import reciprocal_rank_fusion


def make_hit(sym_id: str, name: str, score: float = 1.0) -> RetrievalHit:
    return RetrievalHit(
        symbol_id=sym_id,
        name=name,
        kind="function",
        file_path="src/main.py",
        start_line=1,
        end_line=10,
        score=score,
    )


def test_reciprocal_rank_fusion_single_source():
    hits = [make_hit("r1:a:foo", "foo"), make_hit("r1:a:bar", "bar")]
    result = SearcherResult(source=SearchSource.VECTOR, hits=hits, duration_ms=10.0)
    fused = reciprocal_rank_fusion([result], limit=10)

    assert len(fused) == 2
    assert fused[0].symbol_id == "r1:a:foo"
    assert fused[0].sources == ["vector"]
    assert fused[0].rank == 1
    assert fused[1].symbol_id == "r1:a:bar"
    assert fused[1].rank == 2


def test_reciprocal_rank_fusion_multi_source_boost():
    # Hit matching both vector and symbol search should rank highest
    vec_hits = [make_hit("r1:a:foo", "foo"), make_hit("r1:a:bar", "bar")]
    sym_hits = [make_hit("r1:a:bar", "bar"), make_hit("r1:a:baz", "baz")]

    vec_res = SearcherResult(source=SearchSource.VECTOR, hits=vec_hits)
    sym_res = SearcherResult(source=SearchSource.SYMBOL, hits=sym_hits)

    fused = reciprocal_rank_fusion([vec_res, sym_res], limit=10)

    # 'bar' appears in both sources, so its RRF score is higher
    assert fused[0].symbol_id == "r1:a:bar"
    assert "vector" in fused[0].sources
    assert "symbol" in fused[0].sources
    assert fused[0].rank == 1


def test_reciprocal_rank_fusion_respects_limit():
    hits = [make_hit(f"r1:a:fn_{i}", f"fn_{i}") for i in range(20)]
    result = SearcherResult(source=SearchSource.KEYWORD, hits=hits)
    fused = reciprocal_rank_fusion([result], limit=5)
    assert len(fused) == 5
