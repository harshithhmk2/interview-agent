# System Design

# High-Level Architecture

    React UI
       |
    FastAPI API
       |
    +-----------------------------+
    | Resume | JD | Interview     |
    | Parser | AI | Conversation  |
    +-----------------------------+
                 |
            LangGraph
                 |
          Local LLM (Ollama)
                 |
        Whisper / Piper
                 |
     PostgreSQL + FAISS

## Components

### Frontend

-   Recruiter Dashboard
-   Candidate Interview Portal

### Backend

-   Authentication
-   Resume Service
-   JD Service
-   Interview Service
-   Evaluation Service
-   Report Service

### AI Layer

-   Resume Agent
-   JD Agent
-   Matching Agent
-   Interview Planner
-   Conversation Agent
-   Evaluation Agent
-   Report Agent

## Data Flow

1.  Upload JD
2.  Upload Resume
3.  Parse documents
4.  Generate interview plan
5.  Conduct voice interview
6.  Evaluate answers
7.  Generate report

## Technology

-   React
-   FastAPI
-   PostgreSQL
-   SQLAlchemy
-   LangGraph
-   Ollama
-   Whisper
-   Piper TTS
-   FAISS
