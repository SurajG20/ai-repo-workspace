# AGENTS.md — AI Repository Workspace

## Project Identity

**AI Repository Workspace** — Open-source, self-hosted AI-native repository intelligence platform for solo developers and OSS maintainers. Focuses on **repository understanding** (not code generation).

Positioning: "An AI operating system for repositories."

---

## Development Philosophy

- **Repository intelligence first, AI second** — deterministic parsing/graphing before any LLM/chat
- **Architecture-first** — define interfaces, services, abstractions, models, boundaries before implementation
- **Build in layers** — never jump to fancy UI or agents first
- **Commit after every subsystem** with clean feat: messages

---

## Role Model

- **User = System Architect** — defines architecture, boundaries, contracts, milestones
- **AI = Implementation Engineer** — accelerates implementation based on defined architecture

---

## Critical Rules

1. **Never ask for huge features at once** — decompose into isolated, small subsystems
2. **Force architecture-first development** — always produce interfaces, services, abstractions, models, boundaries
3. **Ask for production patterns** — include retries, logging, health checks, typing, tests, observability
4. **Keep AI focused** — never mix frontend, backend, infra, AI, and DB in one prompt
5. **Commit after EVERY subsystem** — Git history should read like a clean portfolio

---

## Build Phases (Sequential)

```
Phase 0 → Architecture + monorepo scaffold
Phase 1 → Docker infrastructure
Phase 2 → Repository ingestion (GitHub OAuth, clone, metadata)
Phase 3 → AST parsing (Tree-sitter: TS/JS first)
Phase 4 → Graph generation (Neo4j)
Phase 5 → Embeddings + Qdrant (structural chunking by symbols)
Phase 6 → Hybrid retrieval (vector + symbol + graph + keyword)
Phase 7 → Repository Q&A (GraphRAG pipeline)
Phase 8 → Architecture explorer UI (React Flow)
Phase 9 → PR intelligence / Dead code detection
```

**DO NOT implement LLM/chat until Phase 7.**

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js, TypeScript, TailwindCSS, shadcn/ui, React Flow, Mermaid |
| Backend | FastAPI, Python 3.12+ |
| Workers | Celery/RQ, Redis |
| Relational DB | PostgreSQL |
| Graph DB | Neo4j |
| Vector DB | Qdrant |
| Cache/Queue | Redis |
| Parsing | Tree-sitter (TS/JS V1) |
| AI Providers | OpenAI, Anthropic, Ollama (pluggable abstraction) |
| Auth | GitHub OAuth only |
| Deployment | Docker Compose (one-command setup) |

---

## Monorepo Structure

```
ai-repo-workspace/
├── apps/
│   ├── frontend/          # Next.js
│   ├── api/               # FastAPI backend
│   └── workers/           # Python workers (Celery/RQ)
├── packages/
│   ├── parser/            # Tree-sitter AST engine
│   ├── graph-engine/      # Neo4j graph operations
│   ├── embeddings/        # Embedding generation + Qdrant
│   ├── retrieval/         # Hybrid retrieval engine
│   ├── shared/            # Shared types, utils, config
│   └── prompts/           # LLM prompt templates
├── infrastructure/
│   ├── docker/            # Dockerfiles
│   ├── nginx/             # Reverse proxy config
│   └── scripts/           # Dev/ops scripts
├── docs/
└── docker-compose.yml
```

---

## Design Principles

- **Structural chunking only** — chunk by function, class, module, service (never naive token splitting)
- **Pluggable providers** — BYOK architecture for AI providers; support local models
- **Hybrid retrieval** — vector search + symbol search + graph traversal + keyword search
- **Graph-grounded context** — deterministic retrieval with citations to prevent hallucinations
- **GitHub + Linear inspired UI** — minimal but powerful, graph-first interactions
- **Self-hosted friendly** — one-command `docker compose up`

---

## What This Product IS / IS NOT

**IS:** Repository intelligence platform, AI-native dev workspace, GraphRAG system, architecture understanding engine, self-hosted AI dev infrastructure

**IS NOT:** AI autocomplete, Copilot replacement, IDE plugin, "chat with repo" wrapper

---

## License

Apache 2.0 or MIT
