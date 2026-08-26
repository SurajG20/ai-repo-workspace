# Hybrid retrieval with Reciprocal Rank Fusion

No single retrieval signal finds everything: vector search misses exact identifiers, symbol lookup misses concepts, keyword search misses structure, and graph traversal alone has no ranking. We fuse four independent retrievers — Qdrant vectors, Neo4j symbol lookup, keyword matching, and graph-neighbour traversal — using Reciprocal Rank Fusion instead of a learned reranker.

## Considered Options

- **Vector-only retrieval**: rejected — hallucination risk on identifier-shaped queries and no structural awareness.
- **Learned reranker (cross-encoder)**: rejected — adds model hosting and latency to a self-hosted product whose default path must run without any LLM.
- **RRF fusion**: chosen — parameter-light, deterministic, rank-only (no score calibration needed across heterogeneous retrievers).

## Consequences

- Each retriever can fail or return empty without breaking the pipeline; fusion degrades gracefully.
- Adding a new signal is additive: emit another ranked list into the RRF combiner.
- Scores exposed to the Q&A layer are fusion ranks, not probabilities; prompts must not present them as confidence values.
