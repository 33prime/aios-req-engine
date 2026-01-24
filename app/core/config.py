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
    OPENAI_MODEL: str = Field(default="gpt-4o", description="Primary OpenAI model")
    OPENAI_MODEL_MINI: str = Field(default="gpt-4o-mini", description="Fast/cheap OpenAI model")

    # Anthropic configuration (optional - for chat assistant)
    ANTHROPIC_API_KEY: str | None = Field(default=None, description="Anthropic API key for Claude chat")

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
    FACTS_MODEL: str = Field(default="gpt-4.1-mini", description="Model for fact extraction")
    FACTS_PROMPT_VERSION: str = Field(default="facts_v1", description="Prompt version for tracking")
    FACTS_SCHEMA_VERSION: str = Field(default="facts_v1", description="Schema version for tracking")
    MAX_FACT_CHUNKS: int = Field(default=15, description="Max chunks to send for fact extraction")
    MAX_FACT_CHARS_PER_CHUNK: int = Field(
        default=1500, description="Max chars per chunk for fact extraction (sentence-boundary aware)"
    )

    # Phase 1.3: Red-Team configuration
    REDTEAM_MODEL: str = Field(default="gpt-4.1-mini", description="Model for red-team analysis")
    REDTEAM_PROMPT_VERSION: str = Field(default="redteam_v1", description="Red-team prompt version")
    REDTEAM_SCHEMA_VERSION: str = Field(default="redteam_v1", description="Red-team schema version")
    REDTEAM_TOP_K_PER_QUERY: int = Field(
        default=6, description="Chunks to retrieve per query for red-team"
    )
    REDTEAM_MAX_TOTAL_CHUNKS: int = Field(
        default=30, description="Max total chunks for red-team after dedup"
    )

    # Phase 2A: State Builder configuration
    STATE_BUILDER_MODEL: str = Field(default="gpt-4.1-mini", description="Model for state building")
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
    STATE_MODEL: str = Field(default="gpt-4.1-mini", description="Model for state reconciliation")
    STATE_PROMPT_VERSION: str = Field(
        default="reconcile_v1", description="Reconcile prompt version"
    )
    STATE_SCHEMA_VERSION: str = Field(
        default="reconcile_v1", description="Reconcile schema version"
    )

    # Phase 2C: Feature Enrichment configuration
    FEATURES_ENRICH_MODEL: str = Field(default="gpt-4.1-mini", description="Model for feature enrichment")
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
    PRD_ENRICH_MODEL: str = Field(default="gpt-4.1-mini", description="Model for PRD enrichment")
    PRD_ENRICH_PROMPT_VERSION: str = Field(
        default="prd_enrich_v1", description="PRD enrich prompt version"
    )
    PRD_ENRICH_SCHEMA_VERSION: str = Field(
        default="prd_enrichment_v1", description="PRD enrich schema version"
    )

    # Phase 2C: VP Enrichment configuration
    VP_ENRICH_MODEL: str = Field(default="gpt-4.1-mini", description="Model for VP enrichment")
    VP_ENRICH_PROMPT_VERSION: str = Field(
        default="vp_enrich_v1", description="VP enrich prompt version"
    )
    VP_ENRICH_SCHEMA_VERSION: str = Field(
        default="vp_enrichment_v1", description="VP enrich schema version"
    )

    # Strategic Context generation configuration
    STRATEGIC_CONTEXT_MODEL: str = Field(
        default="gpt-4.1-mini",
        description="Model for strategic context generation"
    )

    # Perplexity API configuration
    PERPLEXITY_API_KEY: str = Field(..., description="Perplexity API key")
    PERPLEXITY_MODEL: str = Field(
        default="sonar-pro",
        description="Perplexity model for research (sonar, sonar-pro, sonar-reasoning, sonar-reasoning-pro)"
    )

    # Research Agent configuration
    RESEARCH_AGENT_SYNTHESIS_MODEL: str = Field(
        default="gpt-4o",
        description="Model for synthesizing research findings"
    )
    RESEARCH_AGENT_QUERY_GEN_MODEL: str = Field(
        default="gpt-4o-mini",
        description="Model for generating research queries"
    )
    RESEARCH_AGENT_PROMPT_VERSION: str = Field(
        default="research_agent_v1",
        description="Research agent prompt version"
    )
    RESEARCH_AGENT_SCHEMA_VERSION: str = Field(
        default="research_agent_v1",
        description="Research agent schema version"
    )
    RESEARCH_AGENT_MAX_QUERIES: int = Field(
        default=15,
        description="Max research queries per run"
    )
    RESEARCH_AGENT_QUERY_DELAY_SECONDS: float = Field(
        default=1.0,
        description="Delay between Perplexity queries (rate limiting)"
    )

    # A-Team Agent configuration
    A_TEAM_CLASSIFICATION_MODEL: str = Field(
        default="gpt-4.1-mini",
        description="Model for classifying insights"
    )
    A_TEAM_PATCH_GEN_MODEL: str = Field(
        default="gpt-4.1-mini",
        description="Model for generating patches"
    )
    A_TEAM_PROMPT_VERSION: str = Field(
        default="a_team_v1",
        description="A-Team prompt version"
    )

    # Deep Research Agent configuration
    DEEP_RESEARCH_MODEL: str = Field(
        default="claude-sonnet-4-20250514",
        description="Claude model for deep research agent"
    )

    # Design Intelligence Agent configuration
    DI_AGENT_MODEL: str = Field(
        default="claude-sonnet-4-20250514",
        description="Claude model for DI Agent (gating and foundation)"
    )

    # Firecrawl API configuration
    FIRECRAWL_API_KEY: str = Field(default="", description="Firecrawl API key for website scraping")
    FIRECRAWL_TIMEOUT: int = Field(default=30, description="Timeout for Firecrawl requests")

    # Chat Assistant configuration
    CHAT_MODEL: str = Field(
        default="claude-sonnet-4-20250514",
        description="Claude model for chat assistant (Sonnet 4)"
    )
    SUMMARIZATION_MODEL: str = Field(
        default="claude-3-5-haiku-20241022",
        description="Claude model for conversation summarization"
    )
    CHAT_TOTAL_TOKEN_BUDGET: int = Field(
        default=80_000,
        description="Total token budget for chat context window"
    )
    CHAT_RESPONSE_BUFFER: int = Field(
        default=4096,
        description="Reserved tokens for model response"
    )
    CHAT_RECENT_MESSAGES: int = Field(
        default=3,
        description="Number of recent messages to keep verbatim"
    )
    CHAT_MAX_SUMMARY_TOKENS: int = Field(
        default=2000,
        description="Max tokens for conversation summary"
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
