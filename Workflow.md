You should NOT start by asking the agent:

> “Build the entire AI repository workspace.”

That usually creates:

* messy architecture
* random folders
* hallucinated abstractions
* unmaintainable code
* fake AI pipelines

Instead, treat the AI like a junior engineer working under your system design.

Your job:

* define architecture
* define boundaries
* define contracts
* define milestones

The AI’s job:

* implementation acceleration

That mindset is the difference between:

* “AI-generated spaghetti”
  vs
* “production-grade developer tool”

---

# The Correct Build Strategy

You should build this in layers:

```txt
Phase 0 → Architecture + repo setup
Phase 1 → Repository ingestion
Phase 2 → AST parsing
Phase 3 → Graph generation
Phase 4 → Embeddings + Qdrant
Phase 5 → Hybrid retrieval
Phase 6 → Repository Q&A
Phase 7 → Architecture explorer
Phase 8 → PR intelligence
Phase 9 → Cross-repo intelligence
```

DO NOT jump to agents or fancy UI first.

---

# Your Development Workflow

Since you have:

* VS Code
* OpenCode
* DeepSeek model

Your workflow becomes:

```txt
You = system architect
AI = implementation engineer
```

You should:

1. define milestone
2. generate implementation plan
3. ask agent for isolated feature
4. review code
5. refactor
6. commit
7. move to next subsystem

---

# BEST Folder Structure

Start MONOREPO from day 1.

## Recommended

```txt
ai-repo-workspace/
│
├── apps/
│   ├── frontend/
│   ├── api/
│   └── workers/
│
├── packages/
│   ├── parser/
│   ├── graph-engine/
│   ├── embeddings/
│   ├── retrieval/
│   ├── shared/
│   └── prompts/
│
├── infrastructure/
│   ├── docker/
│   ├── nginx/
│   └── scripts/
│
├── docs/
│
└── docker-compose.yml
```

This instantly makes the project look senior-level.

---

# STEP 1 — Initialize the Monorepo

First prompt to agent:

Create a production-grade monorepo structure for an AI repository intelligence platform.

Requirements:

* frontend in Next.js
* backend in FastAPI
* Python workers
* Dockerized architecture
* separate shared packages
* scalable folder organization
* ready for GraphRAG architecture

Create:

* root folder structure
* pyproject.toml
* Docker Compose
* frontend scaffold
* FastAPI scaffold
* worker scaffold
* shared package structure
* environment configuration strategy
* README setup instructions

The architecture should support:

* Neo4j
* Qdrant
* Redis
* PostgreSQL
* webhook-based indexing
* repository parsing
* AST graph generation
* semantic retrieval

Do not implement business logic yet.
Focus only on production architecture scaffolding.

---

# STEP 2 — Docker Infrastructure

After scaffold works.

Prompt:

Implement Docker Compose infrastructure for local development.

Services:

* frontend
* backend
* workers
* postgres
* redis
* qdrant
* neo4j
* nginx

Requirements:

* health checks
* persistent volumes
* shared Docker network
* hot reload for development
* environment variable support
* startup dependency ordering

Provide:

* docker-compose.yml
* Dockerfiles
* .env.example
* local development instructions

---

# STEP 3 — Repository Ingestion

This is your REAL starting point.

NOT AI.

Prompt:

Implement repository ingestion service in FastAPI.

Requirements:

* GitHub OAuth authentication
* clone repositories locally
* support local folder ingestion
* store repository metadata in PostgreSQL
* webhook registration support
* repository version tracking

Create:

* repository service
* database models
* repository APIs
* local repository storage strategy
* GitHub integration layer

The architecture should support future incremental indexing.
Do not implement embeddings or AI yet.

---

# STEP 4 — Tree-sitter Parsing

This is CRITICAL.

Prompt:

Implement AST parsing engine using Tree-sitter for TypeScript and JavaScript repositories.

Requirements:

* parse files into ASTs
* extract:

  * functions
  * classes
  * imports
  * exports
  * symbol references
  * dependency relationships

Create:

* parser service
* AST models
* symbol extraction pipeline
* dependency extraction
* parsing test suite

Store normalized parsing results for future graph generation.

Do not implement vector embeddings yet.
Focus on deterministic repository intelligence.

---

# IMPORTANT

At this stage:

## DO NOT TOUCH LLMs YET.

Most people fail because they:

* add chat first
* retrieval later

You are doing:

```txt
repository intelligence first
AI second
```

Correct approach.

---

# STEP 5 — Graph Generation

Now your project becomes interesting.

Prompt:

Implement Neo4j graph generation pipeline from AST parsing results.

Requirements:

* create symbol nodes
* create import relationships
* create function call relationships
* create module dependency edges
* support cross-file traversal

Graph should support:

* dependency analysis
* architecture traversal
* dead code detection
* impact analysis

Create:

* graph ingestion service
* Neo4j models
* graph update workers
* traversal query layer
* graph synchronization strategy

Focus on production-grade graph architecture.

---

# STEP 6 — Embeddings + Qdrant

NOW introduce AI retrieval.

Prompt:

Implement semantic indexing pipeline using Qdrant.

Requirements:

* structural chunking by symbols/functions/classes
* embedding generation abstraction layer
* pluggable embedding providers
* chunk metadata storage
* repository-aware vector indexing

Support:

* OpenAI embeddings
* local embedding providers later

Create:

* embedding service
* vector indexing pipeline
* chunking engine
* Qdrant integration
* retrieval APIs

Do not implement chat UI yet.

---

# STEP 7 — Hybrid Retrieval

This is your moat.

Prompt:

Implement hybrid retrieval engine combining:

* vector search
* symbol search
* graph traversal
* keyword search

Requirements:

* retrieval orchestration layer
* query routing
* reranking
* graph-aware retrieval
* source attribution
* retrieval tracing

Create:

* retrieval engine
* ranking pipeline
* graph-enhanced retrieval
* observability hooks
* retrieval diagnostics

Focus on retrieval quality and explainability.

---

# STEP 8 — Repository Q&A

NOW add AI chat.

Prompt:

Implement repository Q&A service.

Requirements:

* GraphRAG retrieval pipeline
* streaming responses
* source citations
* repository-aware context assembly
* architecture-aware prompting
* pluggable LLM providers

Support:

* OpenAI
* Anthropic
* local providers later

Create:

* chat APIs
* prompt orchestration
* context builder
* provider abstraction layer
* conversation session handling

Focus on accurate repository understanding.

---

# STEP 9 — Architecture Explorer UI

Now the product becomes visually impressive.

Prompt:

Implement interactive architecture explorer in Next.js using React Flow.

Features:

* dependency graph visualization
* clickable nodes
* graph traversal
* zoomable architecture maps
* service relationship visualization
* cross-repository graph support

Requirements:

* smooth interactions
* modern developer-tool UI
* GitHub + Linear inspired design
* scalable graph rendering

Integrate backend graph APIs.

---

# STEP 10 — PR Intelligence

Prompt:

Implement PR intelligence service.

Requirements:

* PR summarization
* impact analysis
* changed dependency detection
* affected module analysis
* architecture impact reasoning

Use:

* AST graph
* Neo4j traversal
* semantic retrieval

Create:

* PR analysis pipeline
* GitHub PR integration
* impact scoring
* architecture-aware summarization

---

# CRITICAL RULES While Using AI Agents

---

# Rule 1

## Never ask for huge features at once.

Bad:

> “Build GraphRAG.”

Good:

> “Implement AST symbol extraction pipeline.”

---

# Rule 2

## Force architecture-first development.

Always ask:

* interfaces
* services
* abstractions
* models
* boundaries

---

# Rule 3

## Ask for production patterns.

Include:

* retries
* logging
* health checks
* typing
* tests
* observability

---

# Rule 4

## Keep AI focused.

Never mix:

* frontend
* backend
* infra
* AI
* DB

in one prompt.

---

# Rule 5

## Commit after EVERY subsystem.

Your Git history should look like:

```txt
feat: monorepo scaffold
feat: docker infrastructure
feat: repository ingestion
feat: AST parsing pipeline
feat: Neo4j graph generation
feat: semantic indexing
feat: GraphRAG retrieval
```

This matters for portfolio credibility.

---

# VERY IMPORTANT

The REAL impressive part is NOT the chatbot.

It is:

* AST intelligence
* graph architecture
* retrieval quality
* indexing pipelines
* system design
* observability
* visual repository intelligence

That’s what makes this look like:

## a real AI infrastructure product

instead of:

## another wrapper app.
