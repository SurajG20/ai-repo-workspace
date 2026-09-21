# GraphMind

> Repo: [SurajG20/ai-repo-workspace](https://github.com/SurajG20/ai-repo-workspace) — self-hosted **GraphRAG for codebases**.

**Ask architecture questions and get answers grounded in symbols, call graphs, and retrieved chunks** (with `file:line` citations).

## Problem

Generic “chat with repo” tools embed files and hallucinate structure. Maintainers need a **deterministic** map of symbols and relationships, **hybrid retrieval** when questions are fuzzy, and **evidence** for every claim — without sending the whole repository to an LLM on every query.

## Approach

1. **Parse first** — Tree-sitter builds an AST-level symbol graph (`CALLS`, `USES`, `CONTAINS`, `IMPORTS_MODULE`) before any model runs.
2. **Index twice** — Neo4j for graph traversals; Qdrant for semantic chunks.
3. **Retrieve with fusion** — vector + symbol lookup + keyword + graph neighbors, merged with **Reciprocal Rank Fusion (RRF)**.
4. **Answer with citations** — QA uses only retrieved evidence; with no API key, falls back to deterministic retrieval-only mode.

## Architecture

```
Repository → Parser (Tree-sitter) → Neo4j graph + Qdrant vectors
              ↓
         Postgres indexing DAG (queue, retries, lifecycle)
              ↓
FastAPI API ← Celery workers → Hybrid retrieval + GraphRAG QA
              ↓
Next.js dashboard (explorer, PR blast-radius, dead-code views)
```

```
graphmind/
├── apps/
│   ├── api/             # FastAPI backend (auth, repositories, webhooks, intelligence)
│   ├── frontend/        # Next.js 14 App Router with React Flow & shadcn/ui
│   └── workers/         # Celery executors & indexing pipeline dispatchers
├── packages/
│   ├── parser/          # Multi-language Tree-sitter AST engine & symbol extractors
│   ├── graph-engine/    # Neo4j graph synchronization & graph queries
│   ├── embeddings/      # Structural chunking & Qdrant vector client
│   ├── retrieval/       # Hybrid search, RRF, QA, dead code & PR impact
│   ├── prompts/         # Jinja2 prompt templates
│   ├── jobs/            # Indexing pipeline (Postgres-as-queue DAG)
│   └── shared/          # Domain models & shared contracts
├── infrastructure/      # Docker, nginx, scripts
└── docker-compose.yml
```

## Tech

FastAPI · Celery · PostgreSQL (pgvector) · Redis · Neo4j · Qdrant · Tree-sitter · Next.js 14 · React Flow · Docker Compose · optional Ollama · BYOK OpenAI / Anthropic

## Decisions

| Decision | Why |
|----------|-----|
| Symbol graph before LLM | Reproducible grounding; same repo → same graph. |
| RRF over a single retriever | Code questions need semantic and structural paths. |
| Postgres-as-queue for indexing | Durable DAG with crash-safe claims and backoff. |
| Degrade without LLM key | Explore retrieval and graph tooling without paid APIs. |

## Results

- Hybrid **4-way** retrieval plus GraphRAG Q&A with citations.
- **Dead code** and **PR blast-radius** analysis on the same graph.
- One-command **`docker compose up`** for API, workers, UI, and data stores.

## Demo

```bash
git clone https://github.com/SurajG20/ai-repo-workspace.git && cd ai-repo-workspace
cp .env.example .env
docker compose up -d
```

- Dashboard: **http://localhost:8080** (or **http://localhost:3000**)
- API docs: **http://localhost:8000/docs**

---

## Capabilities (detail)

- **Deterministic symbol graph** — TypeScript, JavaScript, Python, Go, Rust, Java.
- **GraphRAG grounded Q&A** — evidence-only answers with `file:line` citations.
- **Dead code detection** — reachability over exports and call graph.
- **PR blast-radius** — transitive downstream impact for changed symbols.
- **Architecture explorer** — interactive constellation / call-graph UI.

## Services & ports

| Service | Port | Description |
|---|---|---|
| **Frontend** | `3000` / `8080` | Next.js dashboard & architecture explorer |
| **API** | `8000` | FastAPI + OpenAPI at `/docs` |
| **Nginx** | `8080` | Reverse proxy |
| **Neo4j** | `7474` (Bolt `7687`) | Graph database |
| **Qdrant** | `6333` | Vector store |
| **PostgreSQL** | `5432` | Relational store & job queue |
| **Redis** | `6379` | Broker & cache |
| **Ollama** *(optional)* | `11434` | Local models (`--profile ai`) |

## Development

### Tests

```bash
pytest
```

### Local (without Docker)

```bash
cd apps/api && pip install -e . && uvicorn app.main:app --reload --port 8000
cd apps/workers && pip install -e . && celery -A app.main worker --loglevel=info
cd apps/frontend && npm install && npm run dev
```

## License

Apache 2.0
