"""API router for v1 endpoints."""

from fastapi import APIRouter

from app.api import agents, baseline, confirmations, enrich_features, enrich_prd, enrich_vp, insights, jobs, outreach, phase0, projects, reconcile, redteam, research, signals, state

router = APIRouter()

# Include Phase 0 routes
router.include_router(phase0.router, tags=["phase0"])

# Include Phase 1 agents routes
router.include_router(agents.router, prefix="/agents", tags=["agents"])

# Include Phase 1.3: Projects routes (baseline gate management)
router.include_router(projects.router, prefix="/projects", tags=["projects"])

# Include Phase 1.3: Research ingestion routes
router.include_router(research.router, tags=["research"])

# Include Phase 1.3: Red-team routes (agents/red-team and insights)
router.include_router(redteam.router, tags=["redteam"])

# Include Phase 2D: Insights management routes
router.include_router(insights.router, tags=["insights"])

# Include Phase 2D: Job status routes
router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])

# Include Phase 2D: Signal evidence drilldown routes
router.include_router(signals.router, tags=["signals"])

# Include Phase 2A: State building routes (PRD, VP, Features)
router.include_router(state.router, tags=["state"])

# Include Phase 2B: Reconciliation routes
router.include_router(reconcile.router, tags=["reconcile"])

# Include Phase 2C: Feature enrichment routes
router.include_router(enrich_features.router, tags=["enrich_features"])

# Include Phase 2C: PRD enrichment routes
router.include_router(enrich_prd.router, tags=["enrich_prd"])

# Include Phase 2C: VP enrichment routes
router.include_router(enrich_vp.router, tags=["enrich_vp"])

# Include Phase 2B: Confirmation queue routes
router.include_router(confirmations.router, tags=["confirmations"])

# Include Phase 2B: Outreach draft routes
router.include_router(outreach.router, tags=["outreach"])

# Include Phase 3: Baseline management routes
router.include_router(baseline.router, tags=["baseline"])
