# app/config.py
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data.db")
    CHROMA_DIR: str = os.getenv("CHROMA_DIR", "mcp_Server/vector_db")
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3")
    EMBED_MODEL: str = os.getenv("EMBED_MODEL", "nomic-embed-text")
  
settings = Settings()
