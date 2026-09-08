#!/bin/bash
# Exit immediately if a command exits with a non-zero status
set -e

echo "=========================================================="
echo "      AI Voice Interview Agent Container Verification     "
echo "=========================================================="
echo ""

echo "[1/4] Checking running container statuses..."
docker compose ps
echo ""

echo "[2/4] Checking database healthcheck status..."
DB_HEALTH=$(docker inspect --format='{{json .State.Health.Status}}' interview-agent-db 2>/dev/null || echo "\"not found\"")
echo "PostgreSQL DB Health: $DB_HEALTH"
echo ""

echo "[3/4] Testing FastAPI Backend connection & health endpoint..."
if curl -s -f http://localhost:8000/health > /dev/null; then
    echo "Backend: OK (Healthy)"
    curl -s http://localhost:8000/health
    echo ""
else
    echo "Backend: ERROR (Port 8000 is not responding)"
fi
echo ""

echo "[4/4] Testing Ollama and pre-downloaded model status..."
if curl -s -f http://localhost:11434/api/tags > /dev/null; then
    echo "Ollama: OK (Responding)"
    echo "Downloaded Models:"
    curl -s http://localhost:11434/api/tags | json_pp 2>/dev/null || curl -s http://localhost:11434/api/tags
    echo ""
else
    echo "Ollama: ERROR (Port 11434 is not responding)"
fi
echo ""

echo "=== Verification script completed ==="
