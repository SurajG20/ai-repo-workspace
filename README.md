# AI Repository Workspace

An open-source, self-hosted AI-native repository intelligence platform.

> "An AI operating system for repositories."

## Quick Start

```bash
# 1. Clone and navigate
git clone <repo-url> && cd ai-repo-workspace

# 2. Copy environment config
cp .env.example .env

# 3. Start everything
docker compose up -d
```

Open http://localhost:3000 for the frontend and http://localhost:8000/docs for the API.

## Services

| Service    | URL                      |
|------------|--------------------------|
| Frontend   | http://localhost:3000    |
| API        | http://localhost:8000    |
| API Docs   | http://localhost:8000/docs |
| Neo4j      | http://localhost:7474    |
| Qdrant     | http://localhost:6333    |

## Architecture

```
apps/
├── frontend/     # Next.js (React, TypeScript, TailwindCSS)
├── api/          # FastAPI backend
└── workers/      # Celery workers

packages/
├── parser/       # Tree-sitter AST engine
├── graph-engine/ # Neo4j graph operations
├── embeddings/   # Embedding generation + Qdrant
├── retrieval/    # Hybrid retrieval engine
├── shared/       # Shared types, utils, config
└── prompts/      # LLM prompt templates

infrastructure/
├── docker/       # Dockerfiles
├── nginx/        # Reverse proxy config
└── scripts/      # Dev/ops scripts
```

## Development

### Local (without Docker)

```bash
# Backend
cd apps/api
pip install -e .
uvicorn app.main:app --reload

# Workers
cd apps/workers
pip install -e .
celery -A app.main worker --loglevel=info

# Frontend
cd apps/frontend
npm install
npm run dev
```

## License

Apache 2.0
