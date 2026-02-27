"""API router for v1 endpoints."""

import os

from fastapi import APIRouter

from app.api import (
    activity,
    admin,
    agents,
    analytics,
    auth,
    baseline,
    business_drivers,
    chat,
    chat_signals,
    client_packages,
    client_portal,
    client_pulse,
    clients,
    collaboration,
    communications,
    competitor_refs,
    confirmations,
    consultant_enrichment,
    creative_brief,
    discovery,
    discovery_prep,
    document_uploads,
    entity_cascades,
    eval,
    evidence,
    icp,
    intelligence,
    jobs,
    meetings,
    n8n_research,
    notifications,
    open_questions,
    organizations,
    outreach,
    phase0,
    process_documents,
    project_creation,
    project_launch,
    projects,
    proposals,
    prototype_builder,
    prototype_sessions,
    prototypes,
    pulse,
    readiness,
    research,
    research_agent,
    revisions,
    risks,
    signals,
    sources,
    stakeholders,
    state,
    strategic_analytics,
    super_admin,
    tasks,
    workspace,
    workspace_discovery,
)

router = APIRouter()

# Include Phase 0 routes
router.include_router(phase0.router, tags=["phase0"])

# Include Phase 1 agents routes
router.include_router(agents.router, prefix="/agents", tags=["agents"])

# Include Phase 1.3: Projects routes (baseline gate management)
router.include_router(projects.router, prefix="/projects", tags=["projects"])

# Include Chat Assistant routes
router.include_router(chat.router, tags=["chat"])

# Include Chat-as-Signal routes (detect-entities, save-as-signal)
router.include_router(chat_signals.router, tags=["chat"])

# Include Phase 1.3: Research ingestion routes
router.include_router(research.router, prefix="/research", tags=["research"])

# Include Research Agent routes
router.include_router(research_agent.router, tags=["research_agent"])

# Include n8n Research Integration routes
router.include_router(n8n_research.router, tags=["n8n_research"])

# Include Phase 2D: Job status routes
router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])

# Include Phase 2D: Signal evidence drilldown routes
router.include_router(signals.router, tags=["signals"])

# Include Phase 2A: State building routes (PRD, VP, Features)
router.include_router(state.router, tags=["state"])

# Include Phase 2B: Confirmation queue routes
router.include_router(confirmations.router, tags=["confirmations"])

# Include Phase 2B: Outreach draft routes
router.include_router(outreach.router, tags=["outreach"])

# Include Phase 3: Baseline management routes
router.include_router(baseline.router, tags=["baseline"])

# Include analytics routes
router.include_router(analytics.router, tags=["analytics"])

# Include Creative Brief routes
router.include_router(creative_brief.router, tags=["creative_brief"])

# Include Batch Proposals and Cascade routes
router.include_router(proposals.router, tags=["proposals"])

# Include Entity Cascade routes (impact analysis, staleness tracking)
router.include_router(entity_cascades.router, tags=["entity_cascades"])

# Include Activity Feed routes (recent changes, items needing action)
router.include_router(activity.router, tags=["activity"])

# Include Revisions routes (entity-level change history)
router.include_router(revisions.router, tags=["revisions"])

# Include Stakeholders routes
router.include_router(stakeholders.router, tags=["stakeholders"])

# Include People routes (cross-project stakeholder views)
router.include_router(stakeholders.people_router, tags=["people"])

# Include Business Drivers routes (Strategic Foundation)
router.include_router(business_drivers.router, tags=["business_drivers"])

# Include Competitor References routes (Strategic Foundation)
router.include_router(competitor_refs.router, tags=["competitor_refs"])

# Include Risks routes (Strategic Foundation)
router.include_router(risks.router, tags=["risks"])

# Include Strategic Analytics routes (Strategic Foundation)
router.include_router(strategic_analytics.router, tags=["strategic_analytics"])

# Include Authentication routes
router.include_router(auth.router, tags=["auth"])

# Include Admin routes (consultant management of clients)
router.include_router(admin.router, tags=["admin"])

# Include Organizations routes
router.include_router(organizations.router, tags=["organizations"])

# Include Client Portal routes
router.include_router(client_portal.router, tags=["portal"])

# Include Discovery Prep routes (pre-call question/document generation)
router.include_router(discovery_prep.router, tags=["discovery_prep"])

# Include Collaboration routes (touchpoints, phase management)
router.include_router(collaboration.router, tags=["collaboration"])

# Include Client Packages routes (AI-synthesized questions)
router.include_router(client_packages.router, tags=["client_packages"])

# Include Meetings routes
router.include_router(meetings.router, tags=["meetings"])

# Include Tasks routes (system-generated tasks)
router.include_router(tasks.router, tags=["tasks"])

# Include cross-project tasks routes (my tasks, task detail, comments)
router.include_router(tasks.my_tasks_router, tags=["my-tasks"])

# Include Readiness routes (project readiness scoring)
router.include_router(readiness.router, tags=["readiness"])

# Include Project Creation Chat routes (AI-assisted project creation)
router.include_router(project_creation.router, tags=["project_creation"])

# Include Document Uploads routes (document processing)
router.include_router(document_uploads.router, tags=["document_uploads"])

# Include Evidence Quality routes (source provenance tracking)
router.include_router(evidence.router, tags=["evidence"])

# Include Unified Sources routes (cross-source search)
router.include_router(sources.router, tags=["sources"])

# Include Workspace routes (canvas-based UI)
router.include_router(workspace.router, tags=["workspace"])

# Include Prototype Refinement routes
router.include_router(prototypes.router, tags=["prototypes"])
router.include_router(prototype_sessions.router, tags=["prototype_sessions"])

# Include Communication Integration routes (Google OAuth, email, recording)
router.include_router(communications.router, tags=["communications"])

# Include Client Organizations routes (cross-project client management)
router.include_router(clients.router, tags=["clients"])

# Include Discovery Pipeline routes (data-first intelligence)
router.include_router(discovery.router, tags=["discovery"])

# Include Process Documents routes (expanded KB items)
router.include_router(process_documents.router, tags=["process_documents"])

# Include Open Questions routes (unified question lifecycle)
router.include_router(open_questions.router, tags=["open_questions"])

# Include Project Launch routes (smart project setup pipeline)
router.include_router(project_launch.router, tags=["project_launch"])

# Include Consultant Enrichment routes (profile synthesis from LinkedIn/website)
router.include_router(consultant_enrichment.router, tags=["consultant_enrichment"])

# Include ICP Signal Extraction routes (behavioral signal routing + scoring)
router.include_router(icp.router, tags=["icp"])

# Include Notifications routes (in-app notification management)
router.include_router(notifications.router, tags=["notifications"])

# Include Intelligence Module routes (upgraded memory panel)
router.include_router(intelligence.router, tags=["intelligence"])

# Include Super Admin routes (platform management dashboard)
router.include_router(super_admin.router, tags=["super_admin"])

# Include Eval Pipeline routes (prototype eval admin)
router.include_router(eval.router, tags=["eval"])

# Include Client Pulse routes (collaborate view engagement metrics)
router.include_router(client_pulse.router, tags=["collaboration"])

# Include Pulse Engine routes (project health snapshots)
router.include_router(pulse.router, tags=["pulse"])

# Include Discovery Protocol routes (North Star categorization + mission alignment)
router.include_router(workspace_discovery.router, tags=["discovery_protocol"])

# Include Prototype Builder routes (payload assembly, plan generation, rendering)
router.include_router(prototype_builder.router, tags=["prototype_builder"])

# Include Debug Graph routes (dev-only — Tier 2.5 diagnostics)
if os.environ.get("REQ_ENGINE_ENV", "dev") == "dev":
    from app.api import debug_graph

    router.include_router(debug_graph.router, tags=["debug"])
