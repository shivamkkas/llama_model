"""
Configuration management for MCP Server
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import yaml
import os


@dataclass
class OllamaConfig:
    host: str = "http://ollama:11434"  # Docker container name
    model: str = "llama3"
    temperature: float = 0.7
    timeout: int = 300
    max_tokens: int = 4096


@dataclass
class DatabaseConfig:
    type: str  # "sqlite" or "postgresql"
    connection_string: str
    pool_size: int = 5
    max_overflow: int = 10
    echo: bool = False
    
    # Table access control
    table_permissions: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class ChromaDBConfig:
    host: str = "localhost"
    port: int = 8000
    collection_name: str = "mcp_conversations"
    persist_directory: str = "./chroma_data"
    distance_metric: str = "cosine"


@dataclass
class DocumentConfig:
    storage_path: str = "./documents"
    chroma_collection: str = "documents"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    supported_formats: List[str] = field(
        default_factory=lambda: ["txt", "pdf", "docx", "md", "json", "csv"]
    )


@dataclass
class APIConfig:
    registry_path: str = "./api_registry.json"
    timeout: int = 30
    max_retries: int = 3
    cache_ttl: int = 3600


@dataclass
class Config:
    ollama: OllamaConfig
    databases: Dict[str, DatabaseConfig]
    chroma: ChromaDBConfig
    documents: DocumentConfig
    apis: APIConfig
    
    # Security settings
    api_key: Optional[str] = None
    allowed_origins: List[str] = field(default_factory=lambda: ["*"])
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "./mcp_server.log"
    
    @classmethod
    def from_file(cls, filepath: str) -> "Config":
        """Load configuration from YAML file"""
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)
        
        return cls(
            ollama=OllamaConfig(**data.get("ollama", {})),
            databases={
                name: DatabaseConfig(**db_config)
                for name, db_config in data.get("databases", {}).items()
            },
            chroma=ChromaDBConfig(**data.get("chroma", {})),
            documents=DocumentConfig(**data.get("documents", {})),
            apis=APIConfig(**data.get("apis", {})),
            api_key=data.get("api_key"),
            allowed_origins=data.get("allowed_origins", ["*"]),
            log_level=data.get("log_level", "INFO"),
            log_file=data.get("log_file", "./mcp_server.log")
        )
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables"""
        return cls(
            ollama=OllamaConfig(
                host=os.getenv("OLLAMA_HOST", "http://ollama:11434"),
                model=os.getenv("OLLAMA_MODEL", "llama2"),
                temperature=float(os.getenv("OLLAMA_TEMPERATURE", "0.7")),
            ),
            databases={
                "sqlite": DatabaseConfig(
                    type="sqlite",
                    connection_string=os.getenv(
                        "SQLITE_CONNECTION", 
                        "sqlite:///./mcp_data.db"
                    ),
                ),
                "postgresql": DatabaseConfig(
                    type="postgresql",
                    connection_string=os.getenv(
                        "POSTGRES_CONNECTION",
                        "postgresql://user:password@localhost:5432/mcp_db"
                    ),
                )
            },
            chroma=ChromaDBConfig(
                host=os.getenv("CHROMA_HOST", "localhost"),
                port=int(os.getenv("CHROMA_PORT", "8000")),
                persist_directory=os.getenv("CHROMA_PERSIST_DIR", "./chroma_data"),
            ),
            documents=DocumentConfig(
                storage_path=os.getenv("DOCUMENT_STORAGE", "./documents"),
            ),
            apis=APIConfig(
                registry_path=os.getenv("API_REGISTRY", "./api_registry.json"),
            ),
        )

