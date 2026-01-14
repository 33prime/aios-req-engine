"""Deep Research Agent - Multi-phase competitive intelligence gathering.

Two implementations:
- pipeline.py: Optimized deterministic pipeline (~$0.20/run) - RECOMMENDED
- agent.py: Agentic loop with Claude (~$0.70/run) - Legacy
"""

from app.agents.research.pipeline import run_research_pipeline
from app.agents.research.schemas import (
    DeepResearchRequest,
    DeepResearchResponse,
    CompetitorIntelligence,
    FeatureIntelligence,
    UserVoice,
    MarketGap,
)

__all__ = [
    "run_research_pipeline",
    "DeepResearchRequest",
    "DeepResearchResponse",
    "CompetitorIntelligence",
    "FeatureIntelligence",
    "UserVoice",
    "MarketGap",
]
