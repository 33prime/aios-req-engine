"""Configuration management for AIOS Req Engine."""

from functools import lru_cache

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables from .env file (only if accessible)
try:
    load_dotenv()
except (PermissionError, OSError):
    # In sandboxed environments, .env might not be accessible
    # Environment variables should be set directly
    pass


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    # Supabase configuration (required)
    SUPABASE_URL: str = Field(..., description="Supabase project URL")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(..., description="Supabase service role key")

    # OpenAI configuration (required)
    OPENAI_API_KEY: str = Field(..., description="OpenAI API key")

    # Environment
    REQ_ENGINE_ENV: str = Field(default="dev", description="Environment: dev, staging, prod")

    # Embedding configuration
    EMBEDDING_MODEL: str = Field(
        default="text-embedding-3-small", description="OpenAI embedding model"
    )
    EMBEDDING_DIM: int = Field(default=1536, description="Embedding vector dimension")

    # Upload and signal limits
    MAX_UPLOAD_BYTES: int = Field(default=2_000_000, description="Max file upload size in bytes")
    MAX_SIGNAL_CHARS: int = Field(default=200_000, description="Max signal text characters")

    # Phase 1: Facts extraction configuration
    FACTS_MODEL: str = Field(default="gpt-4o-mini", description="Model for fact extraction")
    FACTS_PROMPT_VERSION: str = Field(default="facts_v1", description="Prompt version for tracking")
    FACTS_SCHEMA_VERSION: str = Field(default="facts_v1", description="Schema version for tracking")
    MAX_FACT_CHUNKS: int = Field(default=20, description="Max chunks to send for fact extraction")
    MAX_FACT_CHARS_PER_CHUNK: int = Field(
        default=900, description="Max chars per chunk for fact extraction"
    )

    # Phase 1.3: Red-Team configuration
    REDTEAM_MODEL: str = Field(default="gpt-4o-mini", description="Model for red-team analysis")
    REDTEAM_PROMPT_VERSION: str = Field(default="redteam_v1", description="Red-team prompt version")
    REDTEAM_SCHEMA_VERSION: str = Field(default="redteam_v1", description="Red-team schema version")
    REDTEAM_TOP_K_PER_QUERY: int = Field(
        default=6, description="Chunks to retrieve per query for red-team"
    )
    REDTEAM_MAX_TOTAL_CHUNKS: int = Field(
        default=30, description="Max total chunks for red-team after dedup"
    )

    # Phase 2A: State Builder configuration
    STATE_BUILDER_MODEL: str = Field(default="gpt-4o-mini", description="Model for state building")
    STATE_BUILDER_PROMPT_VERSION: str = Field(
        default="state_v1", description="State builder prompt version"
    )
    STATE_BUILDER_SCHEMA_VERSION: str = Field(
        default="state_v1", description="State builder schema version"
    )
    STATE_BUILDER_TOP_K_PER_QUERY: int = Field(
        default=6, description="Chunks per query for state builder"
    )
    STATE_BUILDER_MAX_TOTAL_CHUNKS: int = Field(
        default=30, description="Max total chunks after dedup for state builder"
    )

    # Phase 2B: State Reconciliation configuration
    STATE_MODEL: str = Field(default="gpt-4o-mini", description="Model for state reconciliation")
    STATE_PROMPT_VERSION: str = Field(
        default="reconcile_v1", description="Reconcile prompt version"
    )
    STATE_SCHEMA_VERSION: str = Field(
        default="reconcile_v1", description="Reconcile schema version"
    )

    # Phase 2C: Feature Enrichment configuration
    FEATURES_ENRICH_MODEL: str = Field(default="gpt-4o-mini", description="Model for feature enrichment")
    FEATURES_ENRICH_PROMPT_VERSION: str = Field(
        default="feature_enrich_v1", description="Feature enrich prompt version"
    )
    FEATURES_ENRICH_SCHEMA_VERSION: str = Field(
        default="feature_details_v1", description="Feature enrich schema version"
    )
    MAX_ENRICH_CHUNKS: int = Field(default=24, description="Max chunks to send for feature enrichment")
    MAX_ENRICH_CHARS_PER_CHUNK: int = Field(
        default=900, description="Max chars per chunk for feature enrichment"
    )

    # Phase 2C: PRD Enrichment configuration
    PRD_ENRICH_MODEL: str = Field(default="gpt-4o-mini", description="Model for PRD enrichment")
    PRD_ENRICH_PROMPT_VERSION: str = Field(
        default="prd_enrich_v1", description="PRD enrich prompt version"
    )
    PRD_ENRICH_SCHEMA_VERSION: str = Field(
        default="prd_enrichment_v1", description="PRD enrich schema version"
    )

    # Phase 2C: VP Enrichment configuration
    VP_ENRICH_MODEL: str = Field(default="gpt-4o-mini", description="Model for VP enrichment")
    VP_ENRICH_PROMPT_VERSION: str = Field(
        default="vp_enrich_v1", description="VP enrich prompt version"
    )
    VP_ENRICH_SCHEMA_VERSION: str = Field(
        default="vp_enrichment_v1", description="VP enrich schema version"
    )


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Returns:
        Settings instance

    Raises:
        ValidationError: If required environment variables are missing
    """
    return Settings()
