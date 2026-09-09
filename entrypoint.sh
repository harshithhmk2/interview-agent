#!/bin/sh
set -e

echo "=== AI Voice Interview Agent Container Startup ==="

echo "[1/3] Waiting for PostgreSQL database to be ready..."
python -c "
import asyncio, sys, time
from src.core.database import engine
from src.db.base import Base
from src.db import models

async def wait_for_db():
    for attempt in range(30):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            print('[SUCCESS] Connected to PostgreSQL and created/verified all tables.')
            return
        except Exception as e:
            print(f'Waiting for PostgreSQL (attempt {attempt+1}/30): {e}')
            time.sleep(2)
    print('[ERROR] Could not connect to PostgreSQL after 30 attempts.', file=sys.stderr)
    sys.exit(1)

asyncio.run(wait_for_db())
"

# Execute database seeding if DB is ready
echo "[2/3] Seeding initial database tables and sample data..."
python seed_db.py || echo "[WARNING] Database seeding script finished or skipped."

# Start Uvicorn ASGI server
echo "[3/3] Starting Uvicorn ASGI Server on port 8000..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8000
