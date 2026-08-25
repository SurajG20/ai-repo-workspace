.PHONY: up down restart logs ps build clean reset shell help

up: ## Start all services (detached)
	docker compose up -d

down: ## Stop all services
	docker compose down

restart: ## Restart all services
	docker compose down && docker compose up -d

logs: ## Tail logs from all services
	docker compose logs -f

ps: ## List running services
	docker compose ps

build: ## Rebuild all images
	docker compose build --no-cache

clean: ## Stop services and remove volumes (destroys all data)
	docker compose down -v

reset: clean up ## Full reset: destroy data, rebuild, restart

shell-backend: ## Open shell in backend container
	docker compose exec backend bash

shell-worker: ## Open shell in worker container
	docker compose exec worker bash

shell-frontend: ## Open shell in frontend container
	docker compose exec frontend sh

db-shell: ## Open PostgreSQL psql
	docker compose exec postgres psql -U aiworkspace

db-migrate: ## Run Alembic migrations
	docker compose exec backend alembic upgrade head

db-migrate-create: ## Create new Alembic migration (usage: make db-migrate-create msg="description")
	docker compose exec backend alembic revision --autogenerate -m "$(msg)"

neo4j-shell: ## Open Neo4j cypher shell
	docker compose exec neo4j cypher-shell -u neo4j -p aiworkspace

test-backend: ## Run backend tests
	docker compose exec backend pytest

test-workers: ## Run worker tests
	docker compose exec worker pytest

lint: ## Run linting (ruff)
	docker compose exec backend ruff check .

typecheck: ## Run type checking (mypy)
	docker compose exec backend mypy .

test: ## Run test suite locally
	pytest

test-frontend: ## Run frontend build and typecheck
	cd apps/frontend && npm run build

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
