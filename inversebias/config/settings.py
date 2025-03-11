"""
Core configuration settings for the InverseBias application.

This module loads configuration from a single YAML file and exposes the settings
through Pydantic models.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any

import yaml

from pydantic_settings import BaseSettings
from pydantic import field_validator, ConfigDict


# Load configuration from YAML file
def load_yaml_config() -> Dict[str, Any]:
    """Load configuration from the config.yaml file."""
    config_path = Path(__file__).parent / "config.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    return config


# Load the configuration once at module import time
_yaml_config = load_yaml_config()


class DatabaseSettings(BaseSettings):
    environment: str = os.getenv("INVERSEBIAS_ENV", "development")
    uri: str = _yaml_config.get("database", {}).get(
        "uri", "postgresql://localhost/inversebias"
    )  # Default value from config
    pool_size: int = _yaml_config.get("database", {}).get("pool_size", 20)
    echo: bool = _yaml_config.get("database", {}).get("echo", False)

    model_config = ConfigDict(env_prefix="DB_", extra="ignore")

    def __init__(self, **data):
        # Get the environment from env var, default to development if not set
        current_env = os.getenv("INVERSEBIAS_ENV", "development")

        if current_env == "production":
            # For production, use DATABASE_URL environment variable directly
            database_url = os.getenv("DATABASE_URL")

            if database_url:
                # Use the provided DATABASE_URL
                data["uri"] = database_url
            else:
                # Fallback: Construct from individual variables if DATABASE_URL is not set
                postgres_user = os.getenv("POSTGRES_USER", "postgres")
                postgres_password = os.getenv("POSTGRES_PASSWORD", "")
                postgres_host = os.getenv("POSTGRES_HOST", "localhost")
                postgres_port = os.getenv("POSTGRES_PORT", "5432")
                postgres_db = os.getenv("POSTGRES_DB", "inversebias")

                # Construct the database URI
                env_uri = f"postgresql://{postgres_user}"
                if postgres_password:
                    env_uri += f":{postgres_password}"
                env_uri += f"@{postgres_host}:{postgres_port}/{postgres_db}"

                data["uri"] = env_uri
        else:
            # For development and other environments, use the URI from config.yaml
            data["uri"] = _yaml_config.get("database", {}).get(
                "uri", "postgresql://localhost/inversebias"
            )

        data["environment"] = current_env
        super().__init__(**data)


# Store news sources directly as a dictionary
NEWS_SOURCES = _yaml_config.get("news_sources", {})


class ApiSettings(BaseSettings):
    host: str = _yaml_config.get("api", {}).get("host", "0.0.0.0")
    port: int = int(
        os.getenv("PORT", str(_yaml_config.get("api", {}).get("port", 8080)))
    )
    frontend_url: str = _yaml_config.get("api", {}).get(
        "frontend_url", "https://inversebias.com"
    )
    default_limit: int = _yaml_config.get("api", {}).get("default_limit", 10)
    max_limit: int = _yaml_config.get("api", {}).get("max_limit", 100)

    model_config = ConfigDict(env_prefix="API_", extra="ignore")


class AnalysisSettings(BaseSettings):
    bias_threshold: float = _yaml_config.get("analysis", {}).get(
        "bias_threshold", 2 / 3
    )
    sentiment_categories: List[str] = _yaml_config.get("analysis", {}).get(
        "sentiment_categories", ["positive", "neutral", "negative"]
    )
    llm_model: str = _yaml_config.get("analysis", {}).get("llm_model", "ollama/llama2")

    model_config = ConfigDict(env_prefix="ANALYSIS_", extra="ignore")


class AppSettings(BaseSettings):
    # Base paths
    base_dir: Path = Path(__file__).parent.parent
    data_dir: Optional[str] = None

    # Subject configuration - loaded directly from YAML
    subjects: List[str] = _yaml_config.get("subjects", [])

    # Sub-settings
    database: DatabaseSettings = DatabaseSettings()
    api: ApiSettings = ApiSettings()
    analysis: AnalysisSettings = AnalysisSettings()

    model_config = ConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @field_validator("data_dir")
    def set_data_dir(cls, v):
        if v is None:
            return str(Path(__file__).parent / "data")
        return v


# Create a global settings instance
settings = AppSettings()

# Convenience exports
SOURCE_TO_URL = NEWS_SOURCES
SUBJECTS = settings.subjects
BIAS_THRESHOLD = settings.analysis.bias_threshold
