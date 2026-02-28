"""RTG Forge integration — module matching, intelligence, and feedback.

AIOS as HTTP client calling Forge's API. All calls are fire-and-forget
or cached — never on the hot path. Follows the same pattern as github_service.py.
"""

from __future__ import annotations

import time

import httpx

from app.core.logging import get_logger
from app.core.schemas_forge import ForgeModuleMatch, PrototypeInsightsPayload

logger = get_logger(__name__)


class ForgeService:
    """RTG Forge integration — module matching, intelligence, and feedback."""

    def __init__(
        self,
        api_url: str,
        api_key: str,
        cache_ttl: int = 300,
        match_threshold: float = 0.40,
    ):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.cache_ttl = cache_ttl
        self.match_threshold = match_threshold
        self._module_cache: tuple[float, list[dict]] | None = None  # (timestamp, data)
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def list_modules(
        self, category: str | None = None, status: str | None = None
    ) -> list[dict]:
        """Fetch module registry. Cached for cache_ttl seconds."""
        # Check cache
        if self._module_cache:
            ts, data = self._module_cache
            if time.time() - ts < self.cache_ttl:
                modules = data
                if category:
                    modules = [m for m in modules if m.get("category") == category]
                if status:
                    statuses = set(status.split(","))
                    modules = [m for m in modules if m.get("status") in statuses]
                return modules

        params: dict[str, str] = {}
        if category:
            params["category"] = category
        if status:
            params["status"] = status

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self.api_url}/api/modules",
                headers=self._headers,
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()
            modules = data.get("modules", data) if isinstance(data, dict) else data

        # Cache the full unfiltered list
        self._module_cache = (time.time(), modules)
        return modules

    async def get_module(self, slug: str) -> dict | None:
        """Fetch single module with full metadata."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self.api_url}/api/modules/{slug}",
                headers=self._headers,
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()

    async def get_module_intelligence(self, slug: str) -> dict | None:
        """Fetch deep intelligence for a single module (Phase 0)."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self.api_url}/api/modules/{slug}/intelligence",
                headers=self._headers,
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()

    async def get_co_occurrence(self, module_slugs: list[str]) -> dict:
        """Fetch cross-module co-occurrence rates."""
        if not module_slugs:
            return {"pairs": []}

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self.api_url}/api/modules/co-occurrence",
                headers=self._headers,
                json={"module_slugs": module_slugs},
            )
            resp.raise_for_status()
            return resp.json()

    async def send_prototype_insights(self, payload: PrototypeInsightsPayload) -> bool:
        """Send prototype build insights to Forge. Fire-and-forget."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.api_url}/api/insights/prototype",
                headers=self._headers,
                json=payload.model_dump(),
            )
            resp.raise_for_status()
            return True

    async def match_features(
        self,
        features: list[dict],
        stage: str = "brd",
    ) -> list[ForgeModuleMatch]:
        """Match AIOS features to Forge modules.

        Deterministic: keyword overlap + Jaccard similarity on
        feature.overview vs module.ai_use_when. No LLM needed.
        """
        modules = await self.list_modules()
        matches: list[ForgeModuleMatch] = []

        for feature in features:
            best_match: ForgeModuleMatch | None = None
            best_score = 0.0

            for module in modules:
                score = _compute_match_score(feature, module)
                if score >= self.match_threshold and score > best_score:
                    # Filter decisions to current stage
                    stage_decisions = [
                        d
                        for d in module.get("decisions", [])
                        if d.get("stage", "all") in (stage, "all")
                    ]
                    best_match = ForgeModuleMatch(
                        module_slug=module.get("slug", ""),
                        module_name=module.get("name", ""),
                        category=module.get("category", ""),
                        status=module.get("status", "stub"),
                        match_score=score,
                        match_reason=_explain_match(feature, module),
                        stage_decisions=stage_decisions,
                        companion_modules=module.get("companions", []),
                        co_occurrence=None,
                        feature_id=feature.get("id", ""),
                    )
                    best_score = score

            if best_match:
                matches.append(best_match)

        return matches


def _compute_match_score(feature: dict, module: dict) -> float:
    """Deterministic text similarity — keyword overlap + Jaccard."""
    feature_text = (
        f"{feature.get('name', '')} {feature.get('overview', '')}"
    ).lower()
    module_text = (
        f"{module.get('ai_use_when', '')} {module.get('name', '')} "
        f"{' '.join(module.get('tags', []))}"
    ).lower()

    # Tokenize, removing very short words (articles, etc.)
    feature_tokens = {w for w in feature_text.split() if len(w) > 2}
    module_tokens = {w for w in module_text.split() if len(w) > 2}

    if not feature_tokens or not module_tokens:
        return 0.0

    intersection = feature_tokens & module_tokens
    union = feature_tokens | module_tokens
    return len(intersection) / len(union) if union else 0.0


def _explain_match(feature: dict, module: dict) -> str:
    """Generate a human-readable explanation of why feature matched module."""
    feature_text = (
        f"{feature.get('name', '')} {feature.get('overview', '')}"
    ).lower()
    module_text = (
        f"{module.get('ai_use_when', '')} {module.get('name', '')} "
        f"{' '.join(module.get('tags', []))}"
    ).lower()

    feature_tokens = {w for w in feature_text.split() if len(w) > 2}
    module_tokens = {w for w in module_text.split() if len(w) > 2}
    shared = feature_tokens & module_tokens

    if shared:
        return f"keyword: {', '.join(sorted(shared)[:5])}"
    return "low-confidence match"


# ── Factory ────────────────────────────────────────────────────────


def get_forge_service() -> ForgeService | None:
    """Get ForgeService if configured, else None."""
    from app.core.config import get_settings

    settings = get_settings()
    if not settings.FORGE_API_URL:
        return None
    return ForgeService(
        api_url=settings.FORGE_API_URL,
        api_key=settings.FORGE_API_KEY,
        cache_ttl=settings.FORGE_CACHE_TTL,
        match_threshold=settings.FORGE_MATCH_THRESHOLD,
    )


# ── Persistence helpers ────────────────────────────────────────────


def save_forge_matches(
    project_id: str, matches: list[ForgeModuleMatch]
) -> None:
    """Upsert forge module matches to DB."""
    from app.db.supabase_client import get_supabase

    sb = get_supabase()
    for match in matches:
        if not match.feature_id:
            continue
        row = {
            "project_id": project_id,
            "feature_id": match.feature_id,
            "module_slug": match.module_slug,
            "match_score": match.match_score,
            "match_reason": match.match_reason,
            "horizon_suggestion": (
                match.co_occurrence.get("horizon_signal")
                if match.co_occurrence
                else None
            ),
            "updated_at": "now()",
        }
        try:
            sb.table("forge_module_matches").upsert(
                row,
                on_conflict="project_id,feature_id,module_slug",
            ).execute()
        except Exception as e:
            logger.debug(f"Forge match upsert failed for {match.module_slug}: {e}")
