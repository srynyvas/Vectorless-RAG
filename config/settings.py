import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Explicitly load .env BEFORE pydantic-settings reads environment
_env_path = PROJECT_ROOT / ".env"
if _env_path.exists():
    load_dotenv(_env_path, override=True)


class Settings(BaseSettings):
    """Application settings loaded from .env file."""

    # LLM Provider: "anthropic" or "openai"
    LLM_PROVIDER: str = "anthropic"

    # Anthropic
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-5-20250929"

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"

    # LLM Parameters
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 4096
    SEARCH_MAX_TOKENS: int = 2048

    # Index generation
    MAX_CHUNK_CHARS: int = 3000
    INDEX_SUMMARY_MAX_WORDS: int = 50

    # Image extraction
    IMAGE_MAX_EDGE: int = 1568
    MAX_IMAGES_PER_SECTION: int = 5
    MAX_CONTEXT_IMAGES: int = 10
    EXTRACT_IMAGES: bool = True

    # Paths (relative to project root)
    UPLOAD_DIR: str = str(PROJECT_ROOT / "data" / "uploads")
    INDEX_DIR: str = str(PROJECT_ROOT / "data" / "indices")

    model_config = {
        "env_file": str(_env_path),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
