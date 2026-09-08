#!/bin/sh
set -e

echo "=== AI Voice Interview Agent Container Startup ==="

# Execute database seeding if DB is ready
echo "[1/2] Seeding initial database tables and sample data..."
python seed_db.py || echo "[WARNING] Database seeding script finished or skipped."

# Start Uvicorn ASGI server
echo "[2/2] Starting Uvicorn ASGI Server on port 8000..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8000
