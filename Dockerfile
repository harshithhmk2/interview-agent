# Use official slim Python base image
FROM python:3.11-slim

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VERSION=1.8.2 \
    POETRY_HOME="/opt/poetry" \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

# Add Poetry binary folder to PATH
ENV PATH="$POETRY_HOME/bin:$PATH"

# Install system dependencies:
# - build-essential: required for compiling native dependencies
# - curl: needed to install Poetry and perform health checks
# - ffmpeg and libsndfile1: needed for audio file processing (speech transcription and synthesis)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry using official installer script
RUN curl -sSL https://install.python-poetry.org | python3 -

# Set the working directory inside the container
WORKDIR /app

# Copy dependency configuration files
COPY pyproject.toml poetry.lock* /app/

# Install application dependencies
RUN poetry install --only main --no-root --no-directory

# Pre-download FastEmbed model so container starts instantly without runtime downloads
RUN python -c "from fastembed import TextEmbedding; TextEmbedding(model_name='BAAI/bge-small-en-v1.5')"

# Copy the rest of the application files
COPY . /app

# Create audio output directory and set entrypoint permissions
RUN mkdir -p /app/audio_outputs && chmod +x /app/entrypoint.sh

# Expose FastAPI default port
EXPOSE 8000

# Execute entrypoint script (auto-seeds database and starts Uvicorn)
ENTRYPOINT ["/app/entrypoint.sh"]
