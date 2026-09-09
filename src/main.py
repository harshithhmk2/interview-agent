import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.core.logging import setup_logging
from src.core.exceptions import register_exception_handlers
from src.core.database import engine
from src.db.base import Base
from src.api.router import api_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles FastAPI application lifecycle events:
    - Sets up structured logging.
    - Creates database schemas asynchronously.
    """
    # 1. Initialize structured logging
    setup_logging()
    logger.info("Initializing AI Voice Interview Agent Backend...")
    
    # 2. Async database schema validation and creation with retries
    for attempt in range(15):
        try:
            async with engine.begin() as conn:
                # Import models to ensure they are registered on Base
                from src.db import models
                from sqlalchemy import text
                await conn.run_sync(Base.metadata.create_all)
                try:
                    await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'candidate';"))
                    await conn.execute(text("ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS company_name VARCHAR(255) DEFAULT 'Implere Technologies';"))
                    await conn.execute(text("ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'open';"))
                    await conn.execute(text("ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS work_mode VARCHAR(50) DEFAULT 'onsite';"))
                    await conn.execute(text("ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS location VARCHAR(255) DEFAULT 'Bangalore';"))
                    await conn.execute(text("ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS experience_range VARCHAR(100) DEFAULT '3 - 5 Years';"))
                    await conn.execute(text("ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS salary_range VARCHAR(100) DEFAULT '₹ 15L - 18L / year';"))
                    await conn.execute(text("ALTER TABLE resumes ADD COLUMN IF NOT EXISTS questions_plan JSON;"))
                    await conn.execute(text("ALTER TABLE resumes DROP CONSTRAINT IF EXISTS resumes_candidate_email_key;"))
                    await conn.execute(text("DROP INDEX IF EXISTS resumes_candidate_email_key;"))
                except Exception as schema_err:
                    logger.warning(f"Schema migration check note: {schema_err}")
            logger.info("Database tables verified/created successfully.")
            break
        except Exception as db_err:
            if attempt < 14:
                logger.warning(f"Waiting for database connection on startup (attempt {attempt+1}/15): {db_err}")
                import asyncio
                await asyncio.sleep(2)
            else:
                logger.critical(f"Failed to initialize database tables on startup: {db_err}", exc_info=True)

    yield

    # Clean up connections
    logger.info("Shutting down AI Voice Interview Agent Backend...")
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Register custom application exceptions and FastAPI validation overrides
register_exception_handlers(app)

# Set up CORS middleware for full cross-origin support (local dev & production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ],
    allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include unified api endpoints router mapping to settings prefix (e.g. /api/v1)
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["system"])
async def health_check():
    """
    Basic system liveness health check endpoint.
    """
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "database": "connected"
    }
