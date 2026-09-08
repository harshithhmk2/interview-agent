# Engineering Constitution

# AI Voice Interview Agent Constitution

## Principles

### 1. Modular First

Each capability must be implemented as an independent service or agent.

### 2. AI Decisions Must Be Explainable

Every score and recommendation should include supporting evidence.

### 3. Human-in-the-Loop

The system recommends; recruiters make final hiring decisions.

### 4. Privacy by Default

-   Encrypt sensitive data where appropriate.
-   Store only necessary candidate information.
-   Allow deletion of interview data.

### 5. Reproducibility

Prompt templates, model versions, and evaluation settings must be
version controlled.

### 6. Reliability

Gracefully recover from speech, network, or model failures.

### 7. Testability

Each parser, agent, and service must have unit and integration tests.

### 8. Observability

Log interview lifecycle events, model latency, and errors.

### 9. Extensibility

Support new interview types, roles, and models without major
refactoring.

### 10. Fairness

Avoid using protected characteristics in evaluations. Score only on
job-relevant evidence.

## Coding Standards

-   Python type hints
-   PEP 8
-   Async FastAPI endpoints where appropriate
-   Separation of API, services, models, and AI agents

## Definition of Done

-   Feature documented
-   Tests pass
-   Logging added
-   API documented
-   Security reviewed
