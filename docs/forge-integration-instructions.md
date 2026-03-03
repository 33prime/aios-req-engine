# AIOS Integration — Instructions for RTG Forge Repo

AIOS (aios-req-engine) is now an HTTP client that calls Forge's API. The integration is live on the AIOS side — it just needs Forge to expose 4 endpoints and add metadata to modules. All calls from AIOS include `Authorization: Bearer {API_KEY}` in headers.

## What AIOS Does With Forge Data

1. **BRD phase**: When consultants extract features from signals, AIOS matches feature names/overviews against module `ai_use_when` + `name` + `tags` using Jaccard similarity (threshold 0.40). Matched modules surface their stage-filtered decisions as discovery probes in the chat assistant.

2. **Phase 0 (prebuild)**: Before generating a prototype, AIOS fetches co-occurrence data for matched modules. High co-occurrence rates (>0.75, same sprint) become H1 horizon signals. Module status affects build depth — `stable`/`beta` modules boost to full depth, `draft` stays visual, `stub` stays placeholder.

3. **After build**: AIOS fires a POST with prototype insights — which features matched modules, which didn't (gap signals), which decisions were resolved, co-module usage pairs, and build depth stats.

---

## Step 1: Add Fields to Module Schema

Every module needs these fields. Add them to whatever schema/model defines a module:

```
ai_use_when  TEXT     -- "Project needs call recording, transcription, or meeting analysis"
tags         TEXT[]   -- ["meetings", "transcription", "analysis", "recording"]
companions   TEXT[]   -- ["icp_signal_extraction", "stakeholder_enrichment"]
```

`ai_use_when` is the most important field. AIOS tokenizes it along with `name` and `tags`, then computes Jaccard similarity against feature descriptions. Write it as a natural sentence describing when this module is relevant. More specific keywords = better matching.

Every decision within a module needs two new fields:

```
stage   TEXT   -- "brd" | "solution_flow" | "prototype" | "build" | "all"
impact  TEXT   -- "scope" | "architecture" | "ui" | "data" | "integration"
```

Stage tells AIOS when to surface the decision:
- `brd` — shown during BRD phase as discovery probes ("Should the system record calls automatically?")
- `solution_flow` — shown when building solution flows ("Where should analysis results appear?")
- `prototype` — shown during prototype review ("Show real transcription or simulated data?")
- `build` — only relevant during actual build, AIOS ignores these during discovery
- `all` — always shown regardless of phase

Impact tells the consultant what kind of choice this is (scope, architecture, ui, data, integration).

---

## Step 2: Build 4 API Endpoints

### Endpoint 1: `GET /api/modules`

**Priority: HIGH — this is the most-called endpoint (AIOS caches it for 5 min)**

Optional query params: `?category=intelligence&status=beta,stable`

Response shape:

```json
{
  "modules": [
    {
      "slug": "call_intelligence",
      "name": "Call Intelligence",
      "category": "intelligence",
      "status": "beta",
      "ai_use_when": "Project needs call recording, transcription, or meeting analysis capabilities",
      "tags": ["meetings", "transcription", "analysis", "recording"],
      "decisions": [
        {
          "key": "recording_method",
          "question": "How should calls be recorded?",
          "options": ["recall_ai", "native_integration", "manual_upload"],
          "stage": "solution_flow",
          "impact": "architecture",
          "default": "recall_ai"
        }
      ],
      "companions": ["icp_signal_extraction", "stakeholder_enrichment"]
    }
  ]
}
```

AIOS reads these fields from each module:
- `slug` — unique identifier
- `name` — display name (also used in Jaccard matching)
- `category` — passed through to prompt compiler
- `status` — `stub | draft | beta | stable` (affects prototype build depth)
- `ai_use_when` — **primary matching text** (Jaccard against feature names/overviews)
- `tags` — **secondary matching keywords** (included in Jaccard token set)
- `decisions` — array of decision objects with `key`, `question`, `options`, `stage`, `impact`, `default`
- `companions` — slugs of modules commonly paired with this one

### Endpoint 2: `POST /api/modules/co-occurrence`

**Priority: MEDIUM — called during Phase 0 prebuild only**

Request:
```json
{
  "module_slugs": ["call_intelligence", "stakeholder_enrichment", "icp_signal_extraction"]
}
```

Response:
```json
{
  "pairs": [
    {
      "module_a": "call_intelligence",
      "module_b": "stakeholder_enrichment",
      "co_occurrence_rate": 0.82,
      "median_gap_days": 3,
      "horizon_signal": "H1",
      "sample_size": 17
    },
    {
      "module_a": "call_intelligence",
      "module_b": "icp_signal_extraction",
      "co_occurrence_rate": 0.65,
      "median_gap_days": 14,
      "horizon_signal": "H2",
      "sample_size": 17
    }
  ]
}
```

Only return pairs where both slugs appear in the request. Compute `horizon_signal` as:
- rate >= 0.75 AND gap_days <= 7 → `"H1"` (used together same sprint)
- rate >= 0.50 AND gap_days <= 30 → `"H2"` (used together weeks later)
- rate >= 0.25 → `"H2"` or `"H3"` depending on gap
- rate < 0.25 → `"H3"` (rare pairing)

If you don't have co-occurrence data yet, return `{"pairs": []}`. AIOS handles empty gracefully.

### Endpoint 3: `POST /api/insights/prototype`

**Priority: HIGH — enables the feedback loop. Even basic storage is valuable.**

AIOS sends this after every prototype build. Accept and store it.

Request:
```json
{
  "project_id": "uuid-string",
  "project_name": "ClientCo Platform",
  "project_type": "saas",
  "features": [
    {
      "id": "uuid",
      "name": "Call Recording & Analysis",
      "horizon": "H1",
      "build_depth": "full",
      "matched_module": "call_intelligence"
    },
    {
      "id": "uuid",
      "name": "Custom Dashboard Builder",
      "horizon": "H2",
      "build_depth": "visual",
      "matched_module": null
    }
  ],
  "unmatched_gaps": [
    {
      "name": "Custom Dashboard Builder",
      "overview": "",
      "priority": "should_have"
    }
  ],
  "resolved_decisions": [
    {
      "module_slug": "call_intelligence",
      "decision_key": "recording_method",
      "chosen_option": "recall_ai",
      "rationale": "Client needs multi-platform support"
    }
  ],
  "horizon_assignments": {
    "feature-uuid-1": "H1",
    "feature-uuid-2": "H2"
  },
  "co_module_usage": [
    {
      "module_a": "call_intelligence",
      "module_b": "stakeholder_enrichment",
      "same_project": true
    }
  ],
  "build_stats": {
    "total_features": 12,
    "full_depth": 4,
    "visual_depth": 6,
    "placeholder_depth": 2
  },
  "generated_at": "2026-02-28T12:00:00Z"
}
```

Response: `200 OK` (body doesn't matter, AIOS ignores it).

What to do with this data:
1. **`unmatched_gaps`** — Store as demand signals. If a gap name appears across 3+ projects, flag it as a module candidate.
2. **`resolved_decisions`** — Update the decision option's usage count. Store the rationale as a real-world example.
3. **`co_module_usage`** — Increment the co-occurrence count for each (module_a, module_b) pair. Recalculate `co_occurrence_rate` and `median_gap_days`.
4. **`horizon_assignments`** — Compare AIOS-assigned horizons with Forge's co-occurrence-derived signals. Divergence means the model may need recalibration.
5. **`build_stats`** — Track depth distribution per module. Modules whose features consistently get "full" depth are well-understood. "placeholder" means the module needs better docs.

### Endpoint 4: `GET /api/modules/{slug}/intelligence`

**Priority: LOW — only called during Phase 0 for deep info on specific modules**

Response:
```json
{
  "slug": "call_intelligence",
  "name": "Call Intelligence",
  "status": "beta",
  "decisions": [
    {
      "key": "recording_method",
      "question": "How should calls be recorded?",
      "options": ["recall_ai", "native_integration", "manual_upload"],
      "stage": "solution_flow",
      "impact": "architecture",
      "default": "recall_ai"
    }
  ],
  "companions": ["stakeholder_enrichment", "icp_signal_extraction"],
  "co_occurrence": {
    "stakeholder_enrichment": {
      "rate": 0.82,
      "gap_days": 3,
      "horizon": "H1"
    },
    "icp_signal_extraction": {
      "rate": 0.65,
      "gap_days": 14,
      "horizon": "H2"
    }
  },
  "build_recommendations": {
    "minimum_viable": ["recording_method", "call_platforms"],
    "full_featured": ["analysis_focus", "custom_dimensions", "results_destination"],
    "typical_depth": "full"
  },
  "demand_signals": {
    "projects_using": 17,
    "unmatched_related_gaps": ["real-time transcription overlay", "sentiment tracking"],
    "avg_feature_survival_rate": 0.85
  }
}
```

---

## Step 3: New Database Tables

```sql
-- Co-occurrence matrix: updated by record_module_usage + prototype insights
CREATE TABLE forge_co_occurrence (
    module_a TEXT NOT NULL,
    module_b TEXT NOT NULL,
    project_count INT DEFAULT 0,
    co_occurrence_rate FLOAT DEFAULT 0.0,
    median_gap_days INT DEFAULT 0,
    horizon_signal TEXT DEFAULT 'H3',
    updated_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (module_a, module_b)
);

-- Demand signals: unmatched features from AIOS prototype builds
CREATE TABLE forge_demand_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    feature_name TEXT NOT NULL,
    feature_overview TEXT DEFAULT '',
    priority TEXT DEFAULT 'unset',
    source_project_id TEXT,
    source_project_type TEXT DEFAULT '',
    occurrence_count INT DEFAULT 1,
    matched_to_module TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Decision usage: real-world choices from AIOS builds
CREATE TABLE forge_decision_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    module_slug TEXT NOT NULL,
    decision_key TEXT NOT NULL,
    chosen_option TEXT NOT NULL,
    rationale TEXT DEFAULT '',
    source_project_id TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

---

## Step 4: Auth

AIOS sends this header on every request:

```
Authorization: Bearer {FORGE_API_KEY}
```

Add middleware or a dependency that validates the Bearer token against an env var like `AIOS_API_KEY`. Return 401 if invalid.

---

## Implementation Order

1. **Add `ai_use_when`, `tags`, `companions` to module model** + **`stage`, `impact` to decision model** — this is the foundation. Tag existing modules and decisions with these fields.
2. **`GET /api/modules`** — serve module registry. AIOS calls this the most.
3. **`POST /api/insights/prototype`** — receive and store build insights. Even just storing the raw JSON is enough to start the feedback loop.
4. **`POST /api/modules/co-occurrence`** — can return `{"pairs": []}` initially, then populate as `record_module_usage` events accumulate.
5. **`GET /api/modules/{slug}/intelligence`** — lowest priority, only used in Phase 0.

---

## Testing the Connection

Once endpoints are up, set these env vars in AIOS:

```
FORGE_API_URL=https://your-forge-url.com
FORGE_API_KEY=your-api-key
```

Then verify:
```bash
# Should return ForgeService instance
uv run python -c "from app.services.forge_service import get_forge_service; print(get_forge_service())"

# Should list modules
uv run python -c "
import asyncio
from app.services.forge_service import get_forge_service
forge = get_forge_service()
modules = asyncio.run(forge.list_modules())
print(f'{len(modules)} modules loaded')
for m in modules[:3]:
    print(f'  {m[\"slug\"]}: {m.get(\"ai_use_when\", \"\")}')
"
```
