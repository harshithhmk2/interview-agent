import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables and/or .env files.
    """
    # Application settings
    PROJECT_NAME: str = "AI Voice Interview Agent"
    API_V1_STR: str = "/api/v1"
    LOG_LEVEL: str = "INFO"

    # Database Settings
    # Supports asyncpg for SQLAlchemy async operations
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/interview_agent",
        description="SQLAlchemy connection URI for PostgreSQL using asyncpg"
    )

    # Security Settings
    # Use a secure random string in production
    JWT_SECRET_KEY: str = Field(
        default="SUPER_SECRET_JWT_KEY_CHANGE_THIS_IN_PRODUCTION_12345!",
        description="Secret key to sign and verify JSON Web Tokens (JWT)"
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Groq & Multi-Model LLM Settings
    GROQ_API_KEY: Optional[str] = Field(
        default=None,
        description="Groq API Key for ultra-fast cloud LLM inference"
    )
    GROQ_BASE_URL: str = Field(
        default="https://api.groq.com/openai/v1",
        description="Base URL for Groq API endpoint"
    )
    LLM_PROVIDER: str = Field(
        default="auto",
        description="LLM Provider: 'auto', 'groq', or 'ollama'. Auto uses Groq if API key is available."
    )
    
    # Task-Specific Model Allocations (Multi-Model Setup)
    PLANNER_MODEL: Optional[str] = Field(
        default=None,
        description="Model to use for planner node (e.g. llama-3.3-70b-versatile for Groq or llama3 for Ollama)"
    )
    EVALUATOR_MODEL: Optional[str] = Field(
        default=None,
        description="Model to use for evaluation node (e.g. llama-3.3-70b-versatile for Groq or llama3.2:1b for Ollama)"
    )
    INTERVIEWER_MODEL: Optional[str] = Field(
        default=None,
        description="Model to use for question generation (e.g. llama-3.1-8b-instant for Groq or llama3.2:1b for Ollama)"
    )
    REPORTER_MODEL: Optional[str] = Field(
        default=None,
        description="Model to use for report generation node"
    )

    # Local LLM (Ollama) Settings
    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434",
        description="Local URL of the running Ollama instance"
    )
    OLLAMA_MODEL: str = Field(
        default="llama3",
        description="Default Ollama model name to use for generation tasks"
    )
    OLLAMA_TIMEOUT: float = Field(
        default=300.0,
        description="Timeout in seconds for Ollama HTTP requests"
    )
    MOCK_LLM: bool = Field(
        default=False,
        description="If True, returns mock LLM text/JSON data without connecting to LLM providers"
    )
    DEFAULT_MATCH_THRESHOLD: float = Field(
        default=70.0,
        description="Default minimum percentage match required for a candidate to automatically proceed to next round"
    )

    # Local Speech Services Settings (Whisper & Piper)
    WHISPER_MODEL_PATH: str = Field(
        default="base",
        description="Local Whisper model size/path (e.g., base, small, tiny)"
    )
    PIPER_MODEL_PATH: str = Field(
        default="en_US-lessac-medium",
        description="Piper voice model file name or local model path"
    )
    PIPER_VOICE: str = Field(
        default="en_US-lessac-medium",
        description="Default Piper speaker voice configuration"
    )
    ENABLE_TTS: bool = Field(
        default=False,
        description="Set to True to synthesize audio voice for next questions using Piper; False to generate text questions only"
    )
    AUDIO_OUTPUT_DIR: str = Field(
        default="./audio_outputs",
        description="Local folder to store generated TTS and user uploaded audio files"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


# Instantiate settings for global imports
settings = Settings()
