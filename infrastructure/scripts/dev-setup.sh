#!/usr/bin/env bash
set -euo pipefail

echo "=== AI Repository Workspace — Dev Setup ==="

if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "Done. Edit .env to configure your environment."
else
    echo ".env already exists, skipping."
fi

echo ""
echo "=== Starting Docker services ==="
docker compose up -d postgres redis

echo ""
echo "Waiting for services to be healthy..."
sleep 5

echo ""
echo "=== Starting remaining services ==="
docker compose up -d

echo ""
echo "=== Setup complete ==="
echo ""
echo "Services:"
echo "  Frontend : http://localhost:3000"
echo "  API      : http://localhost:8000"
echo "  API Docs : http://localhost:8000/docs"
echo "  Neo4j    : http://localhost:7474"
echo "  Qdrant   : http://localhost:6333"
echo ""
echo "Run 'docker compose logs -f' to tail logs."
