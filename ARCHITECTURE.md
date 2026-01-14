# AIOS Requirements Engine - Architecture

> **Last Updated**: January 2026
> **Status**: Production Architecture
> **Supersedes**: All previous phase documentation (Phase 0, 1, 1.2, 2B, 2C)

## Overview

The AIOS Requirements Engine is a signal-driven product requirements management system. It processes diverse inputs (emails, transcripts, notes, research) and maintains a living product definition with features, personas, value paths, and PRD sections.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AIOS Architecture                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐     ┌──────────────────┐     ┌──────────────────────┐    │
│  │   Signals    │────▶│ Unified Processor │────▶│  Entity Management   │    │
│  │   (Input)    │     │                  │     │                      │    │
│  │              │     │  • Extract Claims │     │  • Features          │    │
│  │  • Emails    │     │  • Match Entities │     │  • Personas          │    │
│  │  • Notes     │     │  • Create/Update  │     │  • VP Steps          │    │
│  │  • Transcripts│    │  • Auto-Confirm   │     │  • PRD Sections      │    │
│  │  • Research  │     │  • Queue Enrich   │     │                      │    │
│  └──────────────┘     └──────────────────┘     └──────────────────────┘    │
│                                │                          │                 │
│                                ▼                          ▼                 │
│                       ┌──────────────────┐     ┌──────────────────────┐    │
│                       │   Enrichment     │     │  Version Tracking    │    │
│                       │                  │     │                      │    │
│                       │  • Feature Details│    │  • Snapshots         │    │
│                       │  • PRD Content   │     │  • Diffs             │    │
│                       │  • VP Guidance   │     │  • Field Attribution │    │
│                       └──────────────────┘     └──────────────────────┘    │
│                                                           │                 │
│                                                           ▼                 │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                        AI Assistant Command Center                    │  │
│  │                                                                       │  │
│  │  • Context-aware assistance per tab (mode switching)                  │  │
│  │  • Slash commands (/status, /analyze, /enrich, /confirm, etc.)       │  │
│  │  • Proactive notifications (blockers, pending confirmations)          │  │
│  │  • Quick actions based on current context                            │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Core Principles

### 1. Signal-Driven Truth
- All changes originate from signals (client input, consultant notes, research)
- Every field can be traced back to its source signal(s)
- Authority hierarchy determines confirmation status

### 2. Consultant-in-the-Loop
- AI proposes, consultant approves
- Auto-confirmation only for high-authority signals (client, consultant)
- PRD and entities always show confirmation status

### 3. Evidence-Based Enrichment
- All AI-generated content includes source evidence
- Enrichment enhances but never overwrites confirmed content
- Research findings inform but require consultant validation

### 4. Version Everything
- Entity changes create version snapshots
- Field-level attribution tracks which signals influenced which fields
- Full audit trail for compliance and debugging

---

## Backend Architecture

### Directory Structure

```
app/
├── api/                    # HTTP endpoints
│   ├── phase0.py          # Signal ingestion & search
│   ├── enrich_*.py        # Enrichment endpoints
│   └── chat.py            # Conversational AI
│
├── core/                   # Core services
│   ├── similarity.py      # Centralized fuzzy matching
│   ├── entity_versioning.py # Version tracking & diffs
│   ├── auto_confirmation.py # Authority-based confirmation
│   └── dependency_manager.py # Cascade propagation
│
├── graphs/                 # LangGraph pipelines
│   ├── unified_processor.py # Main signal processing pipeline
│   ├── enrich_feature_graph.py
│   ├── enrich_prd_graph.py
│   └── enrich_vp_graph.py
│
├── chains/                 # LLM prompts & parsers
│   ├── extract_claims.py  # Claim extraction from signals
│   └── enrich_*.py        # Enrichment chains
│
└── db/                     # Database access layer
    ├── features.py
    ├── personas.py
    ├── vp_steps.py
    └── signals.py
```

---

## Core Modules

### 1. Unified Signal Processor (`app/graphs/unified_processor.py`)

Single LangGraph pipeline that replaces the old mode-based split (initial vs maintenance).

```
Signal → Load Context → Extract Claims → Match Entities → Execute Operations → Queue Enrichment
```

**Key Features:**
- Extracts structured claims from any signal type
- Uses similarity matching to find existing entities
- Creates new entities or updates existing ones
- Auto-confirms based on signal authority
- Queues confirmed entities for enrichment

**Usage:**
```python
from app.graphs.unified_processor import process_signal

result = await process_signal(
    signal_id="uuid",
    project_id="uuid",
    run_id="uuid"
)
# Returns: ProcessingResult with claims_extracted, entities_created, entities_updated
```

### 2. Similarity Matcher (`app/core/similarity.py`)

Centralized fuzzy string matching with entity-specific thresholds.

**Strategies:**
- `token_set_ratio` - Best for reordered words
- `partial_ratio` - Best for substring matches
- `key_terms` - Extracts and matches key terms

**Thresholds:**
| Entity Type | Match Threshold | Likely Match |
|-------------|-----------------|--------------|
| Feature     | 0.80            | 0.70         |
| Persona     | 0.75            | 0.65         |
| VP Step     | 0.70            | 0.60         |

**Usage:**
```python
from app.core.similarity import find_matching_feature, should_create_or_update

# Check if feature already exists
result = find_matching_feature("User Authentication", existing_features)
if result.is_match:
    # Update existing
    update_feature(result.matched_item["id"], ...)
else:
    # Create new
    create_feature(...)

# Or use the convenience function
action, match = should_create_or_update("Dashboard Analytics", existing_features, "feature")
# action is "create", "update", or "review"
```

### 3. Entity Versioning (`app/core/entity_versioning.py`)

Tracks entity history with field-level attribution.

**Features:**
- Creates snapshots on every change
- Computes diffs between versions
- Tracks which signals contributed to which fields

**Usage:**
```python
from app.core.entity_versioning import EntityVersioning

versioning = EntityVersioning()

# Get version history
history = versioning.get_history("feature", feature_id, limit=10)

# Compare versions
diff = versioning.compare_versions("feature", feature_id, from_version=1, to_version=3)
# Returns: VersionDiff with changed fields, added, removed

# Get field sources
sources = versioning.get_field_sources("feature", feature_id, "acceptance_criteria")
# Returns: List of signals that contributed to this field
```

### 4. Auto-Confirmation Service (`app/core/auto_confirmation.py`)

Automatic entity confirmation based on signal authority.

**Authority → Status Mapping:**
| Signal Authority | Confirmation Status |
|------------------|---------------------|
| `client`         | `confirmed_client`  |
| `consultant`     | `confirmed_consultant` |
| `system` / `ai`  | `ai_generated`      |
| `research`       | `needs_confirmation`|

**Usage:**
```python
from app.core.auto_confirmation import AutoConfirmation, auto_confirm_from_signal

service = AutoConfirmation()

# Check what status a signal would give
status = service.get_confirmation_status("client")  # → "confirmed_client"

# Auto-confirm an entity from a signal
result = auto_confirm_from_signal("feature", feature_id, "client")
if result and result.triggered_enrichment:
    print("Entity confirmed and queued for enrichment")
```

### 5. Dependency Manager (`app/core/dependency_manager.py`)

Manages entity relationships and cascade propagation.

**Relationship Types:**
- `SERVES` - Persona serves a need
- `ENABLES` - Feature enables capability
- `EXPERIENCES` - Persona experiences VP step
- `REQUIRES` - Entity requires another
- `DEPENDS_ON` - Soft dependency
- `REFERENCES` - Documentation reference

**Cascade Types:**
- `STALENESS` - Mark dependents as stale
- `NOTIFICATION` - Notify about changes
- `ENRICHMENT` - Re-enrich dependents

**Usage:**
```python
from app.core.dependency_manager import DependencyManager

dm = DependencyManager()

# Register a dependency
dm.register_dependency(
    from_type="feature",
    from_id=feature_id,
    to_type="persona",
    to_id=persona_id,
    relationship="SERVES"
)

# Propagate changes
result = dm.propagate_change(
    entity_type="persona",
    entity_id=persona_id,
    change_type="updated",
    cascade_types=["STALENESS", "NOTIFICATION"]
)
# Marks related features as potentially stale
```

---

## Frontend Architecture

### AI Assistant Command Center

Located in `apps/workbench/lib/assistant/`

```
lib/assistant/
├── types.ts       # Type definitions
├── commands.ts    # Slash command registry
├── modes.ts       # Mode configurations per tab
├── proactive.ts   # Proactive behavior triggers
├── context.tsx    # React provider & hooks
└── index.ts       # Public exports
```

### Mode System

The assistant switches modes based on the active tab:

| Tab | Mode | Focus |
|-----|------|-------|
| Overview | `overview` | Project health, blockers, recommendations |
| Sources | `signals` | Signal processing, claim routing |
| Features | `features` | Feature management, enrichment |
| Personas | `personas` | Persona development |
| Value Path | `value_path` | VP flow analysis |
| Research | `research` | Research queries, gap analysis |
| Strategic Context | `briefing` | Meeting prep, summaries |

### Slash Commands

| Command | Description |
|---------|-------------|
| `/status` | Project health overview |
| `/briefing [type]` | Pre-meeting prep (client/internal) |
| `/analyze` | Analyze selected entity |
| `/enrich` | Trigger AI enrichment |
| `/add <type> <name>` | Add new entity |
| `/confirm [level]` | Confirm entity (consultant/client) |
| `/review [type]` | Review pending confirmations |
| `/history` | View entity version history |
| `/surgical <field> <value>` | Targeted field update |
| `/help` | Show all commands |

### Proactive Behaviors

The assistant surfaces relevant information without being asked:

- **Tab Switch**: Shows blockers/pending when entering Overview
- **Entity Selection**: Prompts to confirm AI-generated entities
- **Idle**: Suggests helpful actions after inactivity
- **Signal Added**: Offers to process new signals

### Usage

```tsx
import { AssistantProvider, useAssistant } from '@/lib/assistant'

// Wrap your app
function App() {
  return (
    <AssistantProvider projectId={projectId} initialProjectData={data}>
      <Workspace />
    </AssistantProvider>
  )
}

// Use in components
function ChatPanel() {
  const {
    sendMessage,
    context,
    getQuickActions,
    dismissProactiveMessage
  } = useAssistant()

  // Type "/" to see command autocomplete
  // Quick actions update based on current tab
  // Proactive messages appear for blockers/pending items
}
```

---

## Data Flow

### Signal Processing Flow

```
1. Signal Ingested (email, note, transcript, research)
   │
2. Unified Processor extracts claims
   │
3. For each claim:
   │
   ├─ Find matching entity (similarity matcher)
   │   │
   │   ├─ Match found → Update entity
   │   │   │
   │   │   └─ Create version snapshot
   │   │       Record field attribution
   │   │
   │   └─ No match → Create new entity
   │       │
   │       └─ Set confirmation status from authority
   │
4. Auto-confirm if authority allows
   │
5. Queue confirmed entities for enrichment
   │
6. Propagate changes via dependency manager
```

### Confirmation Flow

```
                    ┌─────────────────┐
                    │  ai_generated   │
                    │   (AI created)  │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
   │ needs_client │  │  confirmed   │  │  confirmed   │
   │  (flagged)   │  │  consultant  │  │   client     │
   └──────────────┘  └──────────────┘  └──────────────┘
```

### Enrichment Flow

```
Confirmed Entity
      │
      ▼
┌─────────────────┐
│ Enrichment Queue│
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ Load Context    │────▶│ Generate Details│
│ (signals, etc.) │     │ (with evidence) │
└─────────────────┘     └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │ Store in Entity │
                        │ (details JSONB) │
                        └─────────────────┘
```

---

## Database Schema (Key Tables)

### Core Entities

```sql
-- Features
CREATE TABLE features (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT,
    is_mvp BOOLEAN DEFAULT false,
    confirmation_status TEXT DEFAULT 'ai_generated',
    details JSONB DEFAULT '{}',  -- Enrichment data
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);

-- Personas
CREATE TABLE personas (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    confirmation_status TEXT DEFAULT 'ai_generated',
    pain_points JSONB DEFAULT '[]',
    goals JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);

-- VP Steps
CREATE TABLE vp_steps (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL,
    step_number INT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    enrichment JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);
```

### Versioning & Attribution

```sql
-- Version snapshots (stored in enrichment_revisions)
CREATE TABLE enrichment_revisions (
    id UUID PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id UUID NOT NULL,
    revision_number INT NOT NULL,
    snapshot JSONB NOT NULL,  -- Full entity state
    changes JSONB,            -- What changed
    change_type TEXT,
    source_signal_id UUID REFERENCES signals(id),
    created_at TIMESTAMPTZ
);

-- Field attribution
CREATE TABLE field_attributions (
    id UUID PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id UUID NOT NULL,
    field_path TEXT NOT NULL,  -- e.g., 'name', 'acceptance_criteria[0]'
    signal_id UUID NOT NULL REFERENCES signals(id),
    version_number INT,
    contributed_at TIMESTAMPTZ
);
```

---

## API Reference

### Signal Processing

```
POST /v1/ingest
  Ingest a new signal (email, note, transcript, file)

POST /v1/process
  Process a signal through the unified processor
```

### Enrichment

```
POST /v1/agents/enrich-features
POST /v1/agents/enrich-prd
POST /v1/agents/enrich-vp
```

### State Management

```
GET  /v1/state/features?project_id=...
GET  /v1/state/personas?project_id=...
GET  /v1/state/vp?project_id=...
GET  /v1/state/prd?project_id=...
```

### Conversational AI

```
POST /v1/chat?project_id=...
  Send message to AI assistant

GET  /v1/chat/tools
  Get available tools for the chat
```

---

## Environment Variables

```bash
# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-key

# OpenAI
OPENAI_API_KEY=sk-...

# Models
FACTS_MODEL=gpt-4o-mini
FEATURES_ENRICH_MODEL=gpt-4o-mini
PRD_ENRICH_MODEL=gpt-4o-mini
VP_ENRICH_MODEL=gpt-4o-mini

# Similarity Matching
SIMILARITY_THRESHOLD_FEATURE=0.80
SIMILARITY_THRESHOLD_PERSONA=0.75
SIMILARITY_THRESHOLD_VP=0.70
```

---

## Migration from Legacy Code

The following legacy patterns are **deprecated**:

| Legacy | Current |
|--------|---------|
| `extract_facts` → `surgical_update` | `unified_processor.process_signal()` |
| `build_state_graph` + `surgical_update_graph` | `unified_processor` handles both |
| Duplicated similarity code in `features.py`/`personas.py` | `app/core/similarity.py` |
| Manual version tracking | `app/core/entity_versioning.py` |
| Hardcoded confirmation logic | `app/core/auto_confirmation.py` |
| Separate cascade systems | `app/core/dependency_manager.py` |

---

## Testing

```bash
# Run all tests
pytest

# Run specific module tests
pytest tests/test_similarity.py
pytest tests/test_entity_versioning.py

# Run with coverage
pytest --cov=app
```

---

## Development Workflow

1. **Signal Ingestion**: Add signals via API or chat
2. **Processing**: Unified processor extracts and routes claims
3. **Review**: Consultant reviews AI-generated entities in UI
4. **Confirmation**: Confirm entities (promotes to confirmed status)
5. **Enrichment**: Confirmed entities get detailed AI enhancement
6. **Export**: Generate PRD or other deliverables

---

## See Also

- `00_CORE_ENGINEERING_RULES.md` - Engineering standards
- `10_LANGGRAPH_SERVICE.md` - LangGraph patterns
- `20_SUPABASE_PGVECTOR.md` - Database guidelines
- `30_TESTING_QUALITY.md` - Testing strategy
