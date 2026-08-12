"""
Central configuration for MediAssist AI.
All secrets/config are pulled from environment variables so the same
codebase can run locally, in Docker, or on any cloud host without
code changes (12-factor style).
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- LLM provider ---
    # "gemini"    -> free tier (google.ai.studio), no credit card, text + vision
    # "groq"      -> free tier, very fast, TEXT ONLY (no vision) - image agent will
    #                need GEMINI_API_KEY set too if you pick groq for text
    # "anthropic" -> paid, highest quality
    LLM_PROVIDER: str = "gemini"

    GEMINI_API_KEY: str = ""
    GEMINI_TEXT_MODEL: str = "gemini-2.5-flash"
    GEMINI_VISION_MODEL: str = "gemini-2.5-flash"

    GROQ_API_KEY: str = ""
    GROQ_TEXT_MODEL: str = "llama-3.3-70b-versatile"

    ANTHROPIC_API_KEY: str = ""
    TEXT_MODEL: str = "claude-sonnet-4-6"          # used for reasoning/summarization
    VISION_MODEL: str = "claude-sonnet-4-6"        # used for image (X-ray/MRI) description

    # --- App ---
    APP_NAME: str = "MediAssist AI"
    ENV: str = "development"
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # --- Storage paths ---
    UPLOAD_DIR: str = "uploads"
    CHROMA_DIR: str = "rag/chroma_store"
    KNOWLEDGE_BASE_DIR: str = "rag/knowledge_base"
    SQLITE_PATH: str = "database/mediassist.db"

    # --- RAG ---
    RAG_TOP_K: int = 5
    RAG_COLLECTION: str = "medical_knowledge"

    # --- Limits ---
    MAX_UPLOAD_MB: int = 20


@lru_cache
def get_settings() -> Settings:
    return Settings()
