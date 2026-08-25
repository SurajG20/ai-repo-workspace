# AI Repository Workspace (Graphmind)

An open-source, self-hosted AI-native repository intelligence and GraphRAG platform for solo developers and OSS maintainers.

> *"An AI operating system for repositories."*

---

## Key Capabilities

* **Deterministic Symbol Graph**: Extracts AST-level symbols and relationships using Tree-sitter across TypeScript, JavaScript, Python, Go, Rust, and Java into Neo4j (`CALLS`, `USES`, `CONTAINS`, `IMPORTS_MODULE`).
* **Hybrid 4-Way Retrieval**: Fuses vector search (Qdrant), exact/fuzzy symbol lookup (Neo4j), keyword matching, and graph neighbor traversals with **Reciprocal Rank Fusion (RRF)**.
* **GraphRAG Grounded Q&A**: Answers architectural and codebase questions strictly grounded in retrieved evidence with `file:line` citations. Degrades to pure deterministic retrieval if no LLM key is supplied.
* **Dead Code Detection**: AST and graph reachability analysis identifying unused exports, unreferenced functions, and orphaned modules.
* **PR Blast-Radius Impact Analysis**: Analyzes pull request changes and computes transitive downstream dependencies and affected symbols.
* **Postgres-as-Queue Indexing Pipeline**: Durable, crash-resilient DAG engine with atomic claim reservation, retry backoff, and automatic artifact lifecycle cleanup.
* **Interactive Architecture Explorer**: Visual constellation and call-graph explorer built with Next.js 14, React Flow, and TailwindCSS.

---

## Quick Start

```bash
# 1. Clone repository
git clone https://github.com/SurajG20/ai-repo-workspace.git && cd ai-repo-workspace

# 2. Configure environment
cp .env.example .env

# 3. Launch all services
docker compose up -d
```

Open **http://localhost:8080** (or **http://localhost:3000**) for the dashboard and **http://localhost:8000/docs** for the API documentation.

---

## Services & Ports

| Service | Port | Description |
|---|---|---|
| **Frontend** | `http://localhost:3000` (or `8080`) | Next.js 14 developer dashboard & architecture explorer |
| **API** | `http://localhost:8000` | FastAPI backend with OpenAPI documentation at `/docs` |
| **Nginx** | `http://localhost:8080` | Reverse proxy mapping API and frontend |
| **Neo4j** | `http://localhost:7474` (Bolt: `7687`) | Cypher query console and graph database |
| **Qdrant** | `http://localhost:6333` | Vector database dashboard & REST/gRPC API |
| **PostgreSQL** | `localhost:5432` | Relational store & job queue (`pgvector/pgvector:pg16`) |
| **Redis** | `localhost:6379` | Task queue broker & cache |
| **Ollama** *(optional)* | `http://localhost:11434` | Local model inference (enabled via `--profile ai`) |

---

## Architecture & Monorepo Structure

```
graphmind/
├── apps/
│   ├── api/             # FastAPI backend (auth, repositories, webhooks, intelligence)
│   ├── frontend/        # Next.js 14 App Router with React Flow & shadcn/ui
│   └── workers/         # Celery executors & Indexing Pipeline dispatchers
├── packages/
│   ├── parser/          # Multi-language Tree-sitter AST engine & symbol extractors
│   ├── graph-engine/    # Neo4j graph synchronization & graph queries
│   ├── embeddings/      # Structural chunking & Qdrant vector client
│   ├── retrieval/       # Hybrid search engine, RRF reranker, QA pipeline, dead code & PR impact
│   ├── prompts/         # Jinja2 prompt templates & message builders
│   ├── jobs/            # Indexing Pipeline (Postgres-as-queue DAG engine)
│   └── shared/          # Canonical domain models, IndexedSymbol contracts & Fernet crypto
├── infrastructure/
│   ├── docker/          # Dockerfiles for API, worker, frontend, and nginx
│   ├── nginx/           # Reverse proxy configuration
│   └── scripts/         # Dev setup & entrypoint scripts
└── docker-compose.yml   # Multi-service container orchestration
```

---

## Development

### Running the Test Suite

```bash
# Run all tests (shared, parser, jobs, prompts, embeddings, retrieval, graph-engine, api)
pytest
```

### Running Locally (without Docker)

```bash
# Backend
cd apps/api
pip install -e .
uvicorn app.main:app --reload --port 8000

# Workers
cd apps/workers
pip install -e .
celery -A app.main worker --loglevel=info

# Frontend
cd apps/frontend
npm install
npm run dev
```

---

## License

Apache 2.0
