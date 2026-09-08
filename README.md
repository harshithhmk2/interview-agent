# AI Voice Interview Agent

This project is an AI-powered voice interviewer that automates initial candidate screening. By analyzing a Job Description (JD) and a candidate's resume, it conducts an adaptive voice interview, evaluates responses, and generates a detailed recruiter-ready report with structured scores and transcript evidence.

---

## Technical Stack
- **Backend:** FastAPI (Python 3.11+)
- **Database:** PostgreSQL (Relational schema) + FAISS (Vector database for semantic matching)
- **AI Orchestration:** LangGraph (State Machine) & LangChain
- **Models:** Local LLM (Ollama), Local Whisper (Speech-to-Text), Local Piper (Text-to-Speech)
- **Testing:** Pytest, Pytest-Asyncio
- **Formatting & Linting:** Black, MyPy, Flake8

---

## Prerequisites
Ensure you have the following installed on your machine:
- [Docker & Docker Compose](https://www.docker.com/)
- [Python 3.11+](https://www.python.org/downloads/)
- [Poetry](https://python-poetry.org/) (for Python dependency management)
- [Ollama](https://ollama.com/) (running locally)

---

## Quick Start Setup Guide

### 1. Configure Environment Variables
Copy the template environment file to create your active configuration:
```bash
cp .env.example .env
```
Open the `.env` file and verify or update the database credentials, security keys, and local model settings.

### 2. Start PostgreSQL Database
Spin up the local PostgreSQL instance via Docker Compose. This runs the database in the background:
```bash
docker-compose up -d
```
You can verify the database container health by running:
```bash
docker ps
```
The database health check is configured to automatically check readiness using `pg_isready`.

### 3. Install Dependencies
Install all package dependencies and development tools inside a virtual environment using Poetry:
```bash
poetry install
```

### 4. Create and Initialize Database
Run the setup script to connect to your PostgreSQL instance and create the necessary database (`interview_db` by default):
```bash
poetry run python setup_db.py
```
This script checks if the database exists and automatically creates it.

### 5. Running Code Formatters & Linters
To ensure conformity with the [CONSTITUTION.md](file:///D:/Interview-Agent/CONSTITUTION.md), run Black and MyPy checks:
- **Run Black Formatter:**
  ```bash
  poetry run black src tests setup_db.py
  ```
- **Run MyPy Type Check:**
  ```bash
  poetry run mypy src tests setup_db.py
  ```

---

## Directory Structure Alignment
Refer to the [System Architecture Blueprint](file:///D:/Interview-Agent/docs/architecture_blueprint.md) for detailed guidelines on adding new FastAPI routes (`src/api`), database models (`src/db/models.py`), schemas (`src/schemas`), or LangGraph agents (`src/agents`).
