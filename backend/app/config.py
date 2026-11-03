"""Application configuration settings using Pydantic Settings."""
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Neo4j Credentials
    NEO4J_URI: str = "neo4j+s://your-instance.databases.neo4j.io"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = ""
    NEO4J_DATABASE: str = "neo4j"

    # Server Configuration
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    RELOAD: bool = False

    # Storage and Security Controls
    MAX_UPLOAD_SIZE_MB: int = 25
    MAX_FILES_COUNT: int = 1000
    MAX_TOTAL_UNCOMPRESSED_MB: int = 50
    STORAGE_DIR: str = "./data/repos"

    model_config = SettingsConfigDict(
        env_file=(
            str(Path(__file__).resolve().parent.parent / ".env"),
            "backend/.env",
            ".env"
        ),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def storage_path(self) -> Path:
        p = Path(self.STORAGE_DIR).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

settings = Settings()
