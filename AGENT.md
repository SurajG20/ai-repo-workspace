# AGENT.md — AI Repository Workspace

## Overview

**AI Repository Workspace** is an open-source, self-hosted, AI-native repository intelligence platform for solo developers and OSS maintainers. It helps developers understand large codebases through AST-powered structural analysis, GraphRAG-based retrieval, architecture visualization, and repository Q&A.

**Current Phase**: Phase 5/9 (Embeddings + Qdrant) — the repo has scaffold, Docker infra, ingestion, AST parsing, graph generation, and embedding pipeline implemented. Retrieval, prompts/RAG, Q&A, UI, and PR intelligence remain.

**Positioning**: "An AI operating system for repositories."

---

## Tech Stack

### Languages
- **Python 3.12+** — Backend, workers, packages
- **TypeScript 5.5+** — Frontend (Next.js 14 App Router)

### Frameworks & Libraries

| Layer | Technology |
|---|---|
| Backend API | FastAPI, Uvicorn, SQLAlchemy 2.0 (async), Alembic |
| Workers | Celery 5.4+ with Redis broker/backend |
| Graph DB | Neo4j 5 (community) via neo4j Python driver |
| Vector DB | Qdrant via qdrant-client (async) |
| AI Embeddings | OpenAI / Ollama (pluggable `BaseEmbedder` abstraction) |
| LLM Providers | OpenAI, Anthropic, Ollama (abstraction declared, not implemented) |
| Parsing | Tree-sitter (multi-language: TS/JS, Python, Go, Rust, Java) |
| Auth | GitHub OAuth only, JWT tokens (python-jose) |
| Frontend | Next.js 14, React 18, TailwindCSS 3, shadcn/ui CSS vars, React Flow, Mermaid |
| Package Management | Hatchling (Python monorepo), npm (frontend) |
| Validation | Pydantic v2 + Pydantic-Settings |
| Logging | structlog (structured logging) |
| Encryption | cryptography (Fernet), python-jose (JWT) |
| HTTP | httpx (async) |

### Infrastructure

| Service | Technology |
|---|---|
| Relational DB | PostgreSQL 16 via pgvector/pgvector |
| Graph DB | Neo4j 5-community + APOC plugin |
| Vector DB | Qdrant (latest) |
| Cache/Queue | Redis 7-alpine |
| LLM Hosting | Ollama (optional, `ai` profile) |
| Reverse Proxy | Nginx (alpine) |
| Orchestration | Docker Compose (one-command setup) |

---

## Architecture

### Folder Layout

```
ai-repo-workspace/
├── apps/
│   ├── api/                 # FastAPI backend (port 8000)
│   │   ├── alembic/         # DB migrations (Phase 2: ingestion core)
│   │   └── app/
│   │       ├── api/         # Route handlers: auth, repositories, webhooks
│   │       ├── core/        # Database, security, logging, health
│   │       ├── models/      # SQLAlchemy models (8 tables)
│   │       └── services/    # Business logic: GitHub OAuth, repo, webhook
│   ├── frontend/            # Next.js 14 App Router (port 3000)
│   │   └── src/app/         # layout.tsx + page.tsx (stub)
│   └── workers/             # Celery workers (async task execution)
│       └── app/tasks/       # ingestion, parsing, sync_graph, embedding
├── packages/
│   ├── shared/              # Shared enums: ProviderType, JobType, EventType, SymbolKind, ChunkType
│   ├── parser/              # Tree-sitter AST engine
│   │   └── src/parser/
│   │       ├── engine.py          # TreeSitterParser — parse_file/parse_many
│   │       ├── registry.py        # Language detection by file extension
│   │       ├── models.py          # ParsedSymbol, SymbolRelationship dataclasses
│   │       ├── resolver.py        # Module import path resolution
│   │       ├── base_extractor.py  # ABC for symbol extraction
│   │       ├── base_dependency.py # ABC for dependency extraction
│   │       ├── extractors/        # TS/JS, Python, Go, Rust, Java extractors
│   │       └── dependencies/      # Per-language dependency extractors
│   ├── graph-engine/        # Neo4j graph operations
│   │   └── src/graph_engine/
│   │       ├── client.py    # Neo4jClient — async driver wrapper
│   │       ├── models.py    # GraphSymbol, GraphRelationship, RelationshipType enum
│   │       ├── queries.py   # GraphQueries — call graph, deps, class hierarchy, etc.
│   │       └── sync.py      # GraphSyncEngine — upsert symbols/relationships to Neo4j
│   ├── embeddings/          # Embedding generation + Qdrant
│   │   └── src/embeddings/
│   │       ├── base.py             # BaseEmbedder ABC
│   │       ├── openai_embedder.py  # OpenAI embedding provider
│   │       ├── ollama_embedder.py  # Ollama local embedding provider
│   │       ├── qdrant_store.py     # Qdrant async client wrapper
│   │       ├── chunker.py          # Structural chunking by symbol
│   │       └── pipeline.py         # EmbeddingPipeline: chunk → embed → store
│   ├── retrieval/           # [EMPTY STUB] Hybrid retrieval engine (planned)
│   └── prompts/             # [EMPTY STUB] LLM prompt templates (planned)
├── infrastructure/
│   ├── docker/              # Dockerfiles: api, frontend, worker, nginx
│   ├── nginx/               # Reverse proxy config
│   └── scripts/             # dev-setup.sh
├── docker-compose.yml       # 8 services (frontend, backend, worker, postgres, redis, neo4j, qdrant, ollama)
├── docker-compose.override.yml  # Dev overrides: hot reload, exposed ports
├── pyproject.toml           # Root monorepo config (ruff, mypy, pytest)
└── Makefile                 # dev commands: up, down, logs, test, lint, typecheck, db-migrate
```

### Request Flow

```
User → Nginx (port 80)
  ├── /api/* → Backend (FastAPI, port 8000)
  │   ├── /auth/*           → auth.py → GitHubOAuthService
  │   ├── /repositories/*   → repositories.py → RepositoryService
  │   ├── /webhooks/*       → webhooks.py → WebhookService
  │   └── /health           → health.py
  └── /* → Frontend (Next.js, port 3000)
```

### Authentication Flow

1. User hits `GET /auth/github/login` → receives GitHub OAuth URL + state
2. User authorizes on GitHub → redirected to `GET /auth/github/callback?code=...&state=...`
3. Backend exchanges code for access token → fetches user info from GitHub API
4. User is created/updated in `users` table (access_token encrypted via Fernet)
5. JWT access token (HS256, 7-day expiry) returned to client
6. Subsequent requests use `Authorization: Bearer <jwt>` → validated by `get_current_user` dependency

### Data Flow (Indexing Pipeline)

```
User creates repo → RepositoryService.create_from_github()
  → IndexingJob (CLONE) enqueued
  → Celery worker: clone_repository task
  → IndexingJob (SNAPSHOT) enqueued
  → Celery worker: create_snapshot task
  → IndexingJob (PARSE) enqueued
  → Celery worker: parse_repository task (Tree-sitter)
  → IndexingJob (GRAPH_SYNC) triggered
  → Celery worker: sync_to_neo4j task
  → IndexingJob (EMBED) triggered
  → Celery worker: embed_repository task
  → Qdrant vector store updated
```

### Event Flow (GitHub Webhooks)

```
GitHub push/PR event → POST /webhooks/github
  → WebhookService.handle_github_event()
    → Idempotency check (delivery_id)
    → WebhookEvent stored (unprocessed)
    → Logged for future processing
```

### Queue Flow

```
FastAPI backend → enqueues IndexingJob → Celery worker picks up
  - clone → snapshot → parse → sync_graph → embed
  - Each task returns result dict with status/metadata
  - Tasks use bind=True, max_retries, and self.retry() on failure
```

---

## Coding Standards

### Naming Conventions
- Python: `snake_case` for functions/variables/methods, `PascalCase` for classes
- TypeScript: `camelCase` for functions/variables, `PascalCase` for components/types
- Files: `snake_case.py` for all Python files
- API routes: `snake_case` endpoints (e.g., `/github/login`, `/repositories/{id}/sync`)
- DB columns: `snake_case` (e.g., `full_name`, `clone_url`)

### Folder Conventions
- Apps contain runnable services (`api`, `frontend`, `workers`)
- Packages contain reusable libraries (`shared`, `parser`, `graph-engine`, `embeddings`)
- Each module has `__init__.py` re-exporting public API
- Package code lives under `src/<package_name>/` (hatchling convention)

### API Style
- RESTful JSON APIs with FastAPI
- Pydantic models for request/response schemas
- `response_model` parameter for automatic docs generation
- `Depends()` for dependency injection (DB sessions, auth, services)
- UUIDs for all resource identifiers

### Error Handling
- HTTPException with appropriate status codes
- Service methods raise exceptions to be caught by route handlers
- Celery tasks use `self.retry(exc=e)` with `max_retries`
- DB sessions auto-rollback on exception via `get_db()` context manager

### Logging
- structlog everywhere with structured context
- Logger created at module level: `logger = structlog.get_logger(__name__)`
- Key-value pairs for all log messages
- Log levels: info for lifecycle events, warning for recoverable errors, error for failures

### Validation
- Pydantic models for all API inputs/outputs
- SQLAlchemy model constraints (nullable, unique, foreign keys)
- Custom validation in service layer (e.g., `create_from_local` path validation expected but missing)

### Testing Approach
- **No tests exist yet** — pytest configured in root `pyproject.toml`
- Test discovery: `testpaths = ["tests"]`, files matching `test_*.py`
- Ruff (linting) and mypy (type checking) configured
- Coverage configured but no coverage configuration in place

---

## Important Commands

### Development
```bash
make up              # docker compose up -d
make down            # docker compose down
make logs            # docker compose logs -f
make restart         # down + up -d
make build           # docker compose build --no-cache
make clean           # down -v (destroys all data)
make reset           # clean + up (full reset)

make shell-backend   # bash in backend container
make shell-worker    # bash in worker container
make shell-frontend  # sh in frontend container
make db-shell        # psql to PostgreSQL
make neo4j-shell     # cypher-shell to Neo4j
```

### Database
```bash
make db-migrate              # alembic upgrade head
make db-migrate-create msg="description"  # new migration (autogenerate)
```

### Testing & Quality
```bash
make test-backend   # pytest in backend container
make test-workers   # pytest in worker container
make lint           # ruff check . in backend
make typecheck      # mypy . in backend
```

### Backend (standalone)
```bash
cd apps/api && pip install -e . && uvicorn app.main:app --reload
```

### Workers (standalone)
```bash
cd apps/workers && pip install -e . && celery -A app.main worker --loglevel=info
```

### Frontend (standalone)
```bash
cd apps/frontend && npm install && npm run dev
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_USER` | `aiworkspace` | PostgreSQL user |
| `POSTGRES_PASSWORD` | `aiworkspace` | PostgreSQL password |
| `POSTGRES_DB` | `aiworkspace` | PostgreSQL database name |
| `POSTGRES_HOST` | `postgres` | PostgreSQL host |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `NEO4J_URI` | `bolt://neo4j:7687` | Neo4j bolt URI |
| `NEO4J_USER` | `neo4j` | Neo4j user |
| `NEO4J_PASSWORD` | `aiworkspace` | Neo4j password |
| `QDRANT_HOST` | `qdrant` | Qdrant host |
| `QDRANT_PORT` | `6333` | Qdrant gRPC/REST port |
| `QDRANT_API_KEY` | `` | Qdrant API key (optional) |
| `REDIS_HOST` | `redis` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_DB` | `0` | Redis DB index |
| `API_HOST` | `0.0.0.0` | Backend bind address |
| `API_PORT` | `8000` | Backend port |
| `API_SECRET_KEY` | `change-me-in-production` | JWT + Fernet encryption key |
| `API_DEBUG` | `false` | Enable debug mode (SQL echo etc.) |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Frontend API endpoint |
| `NEXT_PUBLIC_WS_URL` | `ws://localhost:8000` | Frontend WebSocket endpoint |
| `GITHUB_CLIENT_ID` | `` | GitHub OAuth app client ID |
| `GITHUB_CLIENT_SECRET` | `` | GitHub OAuth app secret |
| `GITHUB_REDIRECT_URI` | `http://localhost:8000/auth/github/callback` | OAuth redirect |
| `OPENAI_API_KEY` | `` | OpenAI API key |
| `ANTHROPIC_API_KEY` | `` | Anthropic API key |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Ollama base URL |
| `EMBEDDING_PROVIDER` | `openai` | Embedding provider (openai/ollama) |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model name |
| `REPO_STORAGE_PATH` | `/data/repositories` | Local repo clone storage |
| `CELERY_BROKER_URL` | `redis://redis:6379/1` | Celery broker URL |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/2` | Celery result backend URL |

---

## External Services

### GitHub OAuth
- Endpoints: `https://github.com/login/oauth/authorize`, `https://github.com/login/oauth/access_token`
- API: `https://api.github.com/user`, `https://api.github.com/user/repos`, `https://api.github.com/repos/{owner}/{repo}`
- Scopes: `repo, user:email`
- Webhook events: push, pull_request

### AI Providers
- **OpenAI**: Embeddings API (`text-embedding-3-small/large`, `text-embedding-ada-002`), Chat API (planned)
- **Anthropic**: Messages API (planned, key accepted in config)
- **Ollama**: Local embeddings via `/api/embeddings`, chat via `/api/chat` (planned)

### Infrastructure Services
- **Neo4j**: Graph database on bolt://neo4j:7687, browser at http://neo4j:7474
- **Qdrant**: Vector database on port 6333
- **Redis**: Queue broker for Celery, caching (planned)
- **PostgreSQL**: Primary relational store with pgvector (PostGIS-like vector support)

---

## Known Technical Debt

### Critical Issues
1. **Webhook signature not verified** (`apps/api/app/api/webhooks.py:22-24`): `signature` header is captured but never validated against payload for webhook authenticity.
2. **Fernet key derivation broken** (`apps/api/app/core/security.py:14-17`): `_get_fernet()` uses zero-padded raw bytes as Fernet key instead of proper base64-encoded 32-byte key. This will silently produce weak encryption and may fail at runtime.
3. **Webhook handler uses fake repository_id** (`apps/api/app/services/webhook.py:30`): `repository_id=uuid.uuid4()` generates a random UUID instead of looking up the actual repo by `full_name`.
4. **No tests exist** — zero test coverage across all packages and apps.

### High Priority
5. **`retrieval/` package is empty** — hybrid retrieval is a core architectural promise but unimplemented.
6. **`prompts/` package is empty** — LLM prompt templates are not defined.
7. **No pagination on list endpoints** — `GET /repositories` returns all repos unfiltered.
8. **Trigger sync enqueues redundant jobs** (`apps/api/app/services/repository.py:111-113`): `trigger_sync` calls both `_enqueue_snapshot_job` and `_enqueue_clone_job` simultaneously, but cloning already implies a snapshot.
9. **Qdrant PointStruct IDs** (`packages/embeddings/src/embeddings/pipeline.py:75`): Uses string UUIDs as PointStruct IDs. Qdrant expects integer or UUID types; string IDs may cause type errors depending on client version.
10. **Workers mix sync and async** — `sync_to_neo4j` and `embed_repository` use `asyncio.run()` inside synchronous Celery tasks. This can cause event loop issues in certain Python environments.

### Medium Priority
11. **No database connection pooling for workers** — workers don't use SQLAlchemy sessions directly, but if they need DB access, they lack pooling config.
12. **No CORS for production** — CORS origins hardcoded to `localhost:3001` and `127.0.0.1:3001` only.
13. **`GraphSyncEngine.sync_all()` doesn't clear stale data** — re-syncing a repo adds new symbols/relationships but doesn't remove deleted ones.
14. **`parse_repository` returns full symbol/relationship data** — Celery task returns potentially megabytes of data in task result, which goes to Redis. This could cause memory issues.
15. **No input validation on local_path** (`apps/api/app/services/repository.py:70-71`): Path traversal possible if user provides `../../../etc/passwd` as local path.
16. **`passlib` listed as dependency but unused** — `apps/api/pyproject.toml` includes `passlib[bcrypt]` but no code uses it.

### Low Priority
17. **Frontend is a bare scaffold** — only a landing page with API docs/health links.
18. **No dark mode toggle** — CSS variables for dark theme are defined but no toggle mechanism.
19. **Alembic uses `uuid-ossp` extension** — PostgreSQL 13+ has built-in `gen_random_uuid()`; `uuid-ossp` is deprecated.
20. **No `setup_grammars.py` integration** — `setup_grammars.py` exists but is not integrated into Dockerfile or Makefile.
21. **`docker-compose.override.yml` exposes all ports** — all DB ports (5432, 7474, 7687, 6333, 6379) are exposed in dev, which is a security concern.
22. **No CI/CD configuration** — no GitHub Actions, no test runner in CI.

---

## Future Improvements

### Phase 6 (Hybrid Retrieval Engine)
- Implement `packages/retrieval/src/retrieval/` with vector + symbol + graph + keyword search
- Query routing and intent classification
- Reranking pipeline
- Retrieval tracing and observability

### Phase 7 (Repository Q&A)
- Implement `packages/prompts/` with prompt templates
- LLM provider abstraction (OpenAI, Anthropic, Ollama)
- GraphRAG context assembly pipeline
- Streaming chat API endpoint
- Source citation support

### Phase 8 (Architecture Explorer UI)
- React Flow graph visualization
- Dependency graph navigation
- Service map view
- API integration with backend graph endpoints

### Phase 9 (PR Intelligence)
- PR summarization workflow
- Impact analysis via graph traversal
- Dead code detection via AST analysis
- GitHub PR webhook integration

### Cross-Cutting Improvements
- Add comprehensive test suite (unit + integration + e2e)
- Set up CI/CD pipeline (GitHub Actions)
- Implement rate limiting (slowapi or Redis-based)
- Add API key management for API access
- Implement proper secret rotation strategy
- Add database migration for pgvector extension
- Set up monitoring (Prometheus + Grafana or similar)
- Add structured error responses (RFC 7807 Problem Details)
- Implement proper pagination for all list endpoints
- Add WebSocket support for real-time task progress
- Add health check dependencies (backed depends on Neo4j + Qdrant)

---

## Project Health Score: 62/100

### Evidence

| Category | Score | Reasoning |
|---|---|---|
| **Architecture** | 18/20 | Well-structured monorepo with clear boundaries. Some empty stubs. |
| **Code Quality** | 12/20 | Good typing, structlog, async patterns. No tests. Several bugs/security issues. |
| **Completeness** | 10/20 | Phases 0-5 done (~60% of planned features). Retrieval, Q&A, UI, PR missing. |
| **Security** | 8/15 | GitHub OAuth implemented. Broken Fernet encryption. No rate limiting, no CSRF. |
| **Performance** | 6/10 | Good async patterns. N+1 query potential in repos list. No pagination. |
| **Dev Experience** | 8/15 | Docker compose, Makefile, hot reload. No CI/CD, no tests, no docs directory. |

**Total: 62/100** — A solid foundation with production patterns, but needs testing, security hardening, and the remaining feature phases to be production-grade.

### Recommended Immediate Actions
1. Fix Fernet key derivation bug
2. Add webhook signature verification
3. Fix webhook repository_id lookup
4. Add test suite (at minimum for services and parser)
5. Set up CI/CD pipeline
6. Implement pagination on list endpoints
7. Add input validation on repository paths
8. Implement the retrieval engine (Phase 6)
