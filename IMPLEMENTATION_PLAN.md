# AIOS Requirements Engine - Unified Architecture Implementation Plan

## Executive Summary

This plan consolidates the requirements engine into a **unified signal processing system** with an **AI Assistant Command Center** that serves as the consultant's primary interface. The design follows your existing style guide (Deep Ocean Blue #044159, clean professional aesthetic).

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        AI ASSISTANT COMMAND CENTER                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │ /status     │  │ /briefing   │  │ /analyze    │  │ /enrich     │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
│                    Context-Aware Mode Switching                          │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────────┐
│                       UNIFIED SIGNAL PROCESSOR                           │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                │
│  │ Ingest       │──▶│ Similarity   │──▶│ Route        │                │
│  │ Signal       │   │ Matcher      │   │ (Create/     │                │
│  └──────────────┘   └──────────────┘   │  Update)     │                │
│                                         └──────┬───────┘                │
└──────────────────────────────────────────────────────────────────────────┘
                                                  │
                    ┌─────────────────────────────┼─────────────────────────────┐
                    │                             │                             │
          ┌─────────▼─────────┐       ┌──────────▼──────────┐       ┌─────────▼─────────┐
          │   CREATE PATH     │       │    UPDATE PATH      │       │   CASCADE PATH    │
          │ ─────────────────│       │ ──────────────────── │       │ ───────────────── │
          │ • Extract claims  │       │ • Extract claims     │       │ • Mark stale      │
          │ • Auto-confirm    │       │ • Field-level patch  │       │ • Propagate       │
          │ • Create entity   │       │ • Version snapshot   │       │ • Notify          │
          │ • Trigger enrich  │       │ • Update entity      │       └───────────────────┘
          └───────────────────┘       └─────────────────────┘
```

---

## Phase 1: Core Infrastructure (Backend)

### 1.1 Similarity Matcher Module
**File:** `app/core/similarity.py`

Extracts and centralizes similarity detection logic currently scattered across `features.py` and other files.

```python
# Core functions to implement:
class SimilarityMatcher:
    def find_best_match(entity_type, candidate, existing_entities) -> MatchResult
    def compute_similarity_score(text_a, text_b, strategy) -> float
    def extract_key_terms(text) -> list[str]
    def multi_strategy_match(candidate, corpus) -> list[ScoredMatch]

# Strategies:
# - token_set_ratio (rapidfuzz) - fuzzy string matching
# - partial_ratio - substring matching
# - key_term_overlap - semantic term matching
# - embedding_similarity - vector similarity (for complex cases)
```

**Dependencies:** `rapidfuzz`, existing `app/core/embeddings.py`

### 1.2 Auto-Confirmation Service
**File:** `app/core/auto_confirmation.py`

Automatic confirmation based on signal source authority.

```python
class AutoConfirmation:
    def should_auto_confirm(signal: Signal) -> bool
    def get_confirmation_status(source: str, authority: str) -> ConfirmationStatus

# Rules:
# - Client signals → confirmed_client
# - Consultant signals → confirmed_consultant
# - AI-generated → ai_generated (needs review)
# - External research → needs_confirmation
```

### 1.3 Unified Dependency Manager
**File:** `app/core/dependency_manager.py`

Replaces `cascade_handler.py` and `entity_cascade.py` with a single system.

```python
class DependencyManager:
    def register_dependency(from_entity, to_entity, dep_type)
    def get_dependents(entity_id) -> list[Dependent]
    def mark_stale(entity_id, reason) -> list[AffectedEntity]
    def propagate_change(entity_id, change_type) -> CascadeResult

# Dependency types:
# - feature → persona (uses)
# - feature → vp_step (implements)
# - persona → vp_step (experiences)
# - vp_step → feature (requires)
```

### 1.4 Entity Versioning Service
**File:** `app/core/entity_versioning.py`

Track changes, diffs, and source attribution.

```python
class EntityVersioning:
    def create_snapshot(entity_id, entity_data) -> VersionId
    def get_history(entity_id) -> list[Version]
    def compute_diff(version_a, version_b) -> Diff
    def get_source_attribution(entity_id, field) -> list[Signal]

# Version metadata:
# - timestamp, author (signal source), change_type
# - field-level diffs with before/after
# - linked signal IDs for traceability
```

### Database Changes
**File:** `migrations/xxx_entity_versioning.sql`

```sql
-- Entity version history
CREATE TABLE entity_versions (
    id UUID PRIMARY KEY,
    entity_type TEXT NOT NULL, -- 'feature', 'persona', 'vp_step'
    entity_id UUID NOT NULL,
    version_number INT NOT NULL,
    data JSONB NOT NULL,
    diff_from_previous JSONB,
    source_signal_id UUID REFERENCES signals(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Source attribution (which signals contributed to which fields)
CREATE TABLE field_attributions (
    id UUID PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id UUID NOT NULL,
    field_path TEXT NOT NULL,  -- e.g., 'name', 'acceptance_criteria[0]'
    signal_id UUID REFERENCES signals(id),
    contributed_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Phase 2: Unified Signal Processor

### 2.1 Main Processor Graph
**File:** `app/graphs/unified_processor.py`

Single entry point replacing `extract_facts_graph.py` and `surgical_update_graph.py`.

```python
# LangGraph state machine
class UnifiedProcessorState(TypedDict):
    signal: Signal
    extracted_claims: list[Claim]
    matched_entities: dict[str, MatchResult]  # claim_id -> match
    operations: list[Operation]  # CREATE or UPDATE
    cascade_results: list[CascadeResult]

# Graph nodes:
# 1. extract_claims - Parse signal into atomic claims
# 2. match_claims - Find existing entities via SimilarityMatcher
# 3. route_operations - Decide CREATE vs UPDATE per claim
# 4. execute_creates - Create new entities with auto-confirm
# 5. execute_updates - Apply field-level patches with versioning
# 6. trigger_cascades - Propagate changes via DependencyManager
# 7. queue_enrichment - Schedule auto-enrichment for confirmed entities
```

### 2.2 Claim Extraction Chain
**File:** `app/chains/extract_claims_v2.py`

Enhanced claim extraction with entity-type hints.

```python
# Output schema
class ExtractedClaim:
    text: str
    entity_type_hint: Literal['feature', 'persona', 'vp_step', 'integration', 'data_model']
    confidence: float
    field_hints: dict[str, str]  # Suggested field mappings

# Extraction prompt focuses on:
# - Identifying WHAT is being described (entity type)
# - Extracting specific attributes mentioned
# - Preserving original language for attribution
```

### 2.3 Smart Update Router
**File:** `app/core/update_router.py`

Decides between create vs update based on similarity results.

```python
class UpdateRouter:
    CREATE_THRESHOLD = 0.7  # Below this, create new
    UPDATE_THRESHOLD = 0.85  # Above this, definitely update

    def route(claim: Claim, match: MatchResult) -> Operation:
        if match.score < CREATE_THRESHOLD:
            return CreateOperation(claim)
        elif match.score >= UPDATE_THRESHOLD:
            return UpdateOperation(claim, match.entity_id)
        else:
            # Ambiguous - flag for consultant review
            return ReviewOperation(claim, match.candidates)
```

---

## Phase 3: Research Knowledge Base

### 3.1 Research Index Service
**File:** `app/core/research_index.py`

One intensive research phase, indexed for reuse everywhere.

```python
class ResearchIndex:
    def run_comprehensive_research(project_id, topics: list[str]) -> ResearchCorpus
    def query_research(project_id, question: str, top_k: int) -> list[ResearchChunk]
    def get_relevant_insights(entity_id) -> list[ResearchInsight]
    def suggest_research_gaps(project_id) -> list[Gap]

# Index structure:
# - Vector store for semantic search
# - Tagged by topic, entity relevance, confidence
# - Includes competitor analysis, market data, UX patterns
```

### 3.2 Research-Enhanced A-Team
**File:** `app/graphs/a_team_v2.py`

Dual-purpose A-Team with research context.

```python
class ATeamV2:
    # High-level sanity check mode
    def strategic_review(project_id) -> StrategicInsights:
        """
        - Does this make sense overall?
        - What's missing?
        - Are there contradictions?
        - Research-backed suggestions
        """

    # Surgical VP analysis mode
    def value_path_deep_dive(vp_step_id) -> VPAnalysis:
        """
        - Is this step well-defined?
        - Does it account for all relevant personas?
        - Research validation for each decision
        - "Wow factor" assessment
        """
```

---

## Phase 4: Auto-Enrichment Pipeline

### 4.1 Enrichment Trigger Service
**File:** `app/core/auto_enrichment.py`

Automatically enriches confirmed entities.

```python
class AutoEnrichment:
    def on_entity_confirmed(entity_type, entity_id):
        """Triggers when status changes to confirmed_*"""

    def enrich_feature(feature_id) -> EnrichedFeature:
        """
        - Acceptance criteria generation
        - Technical considerations
        - UX specifications
        - Research-backed recommendations
        """

    def enrich_persona(persona_id) -> EnrichedPersona:
        """
        - Detailed demographics
        - Goals and frustrations expansion
        - Journey touchpoints
        - Research-backed behavior patterns
        """

    def enrich_vp_step(vp_step_id) -> EnrichedVPStep:
        """
        - Detailed flow breakdown
        - Edge cases and error states
        - Feature requirements mapping
        - Magic moment opportunities
        """
```

### 4.2 Enrichment Queue
**File:** `app/db/enrichment_queue.py`

Background processing for enrichment jobs.

```python
# Queue table
CREATE TABLE enrichment_queue (
    id UUID PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id UUID NOT NULL,
    priority INT DEFAULT 5,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);
```

---

## Phase 5: AI Assistant Command Center

### 5.1 Assistant Context Manager
**File:** `apps/workbench/lib/assistant/context.ts`

```typescript
interface AssistantContext {
  // Current view state
  activeTab: TabType
  selectedEntity: Entity | null

  // Mode-specific context
  mode: AssistantMode
  modeConfig: ModeConfig

  // Conversation state
  messages: Message[]
  pendingActions: Action[]

  // Quick actions for current context
  suggestedActions: QuickAction[]
}

type AssistantMode =
  | 'overview'      // Project health, blockers, recommendations
  | 'signals'       // Signal processing, claim routing
  | 'features'      // Feature management, enrichment
  | 'personas'      // Persona development
  | 'value_path'    // VP flow analysis
  | 'research'      // Research queries, gap analysis
  | 'briefing'      // Pre-meeting prep
```

### 5.2 Slash Command System
**File:** `apps/workbench/lib/assistant/commands.ts`

```typescript
const COMMANDS = {
  // Status & Overview
  '/status': StatusCommand,       // Project health summary
  '/blockers': BlockersCommand,   // Current blockers & recommendations
  '/health': HealthCommand,       // Detailed readiness breakdown

  // Briefings & Prep
  '/briefing': BriefingCommand,   // Pre-meeting brief with discussion points
  '/followup': FollowupCommand,   // Post-meeting action items

  // Analysis
  '/analyze': AnalyzeCommand,     // Deep dive on selected entity
  '/gaps': GapsCommand,           // Find missing pieces
  '/research': ResearchCommand,   // Query research knowledge base

  // Actions
  '/enrich': EnrichCommand,       // Trigger enrichment
  '/add': AddCommand,             // Add new entity via conversation
  '/confirm': ConfirmCommand,     // Confirm selected items

  // A-Team
  '/review': ReviewCommand,       // Strategic A-Team review
  '/surgical': SurgicalCommand,   // Surgical VP analysis
}
```

### 5.3 Context-Aware Mode Switching
**File:** `apps/workbench/lib/assistant/modes.ts`

```typescript
const MODE_CONFIGS: Record<AssistantMode, ModeConfig> = {
  overview: {
    systemPrompt: OVERVIEW_PROMPT,
    quickActions: ['View blockers', 'Get briefing', 'Run A-Team review'],
    proactiveMessages: true,
    focusEntities: ['project_health', 'blockers', 'pending_confirmations']
  },
  features: {
    systemPrompt: FEATURES_PROMPT,
    quickActions: ['Enrich selected', 'Find gaps', 'Add feature'],
    proactiveMessages: false,
    focusEntities: ['features', 'integrations']
  },
  value_path: {
    systemPrompt: VP_PROMPT,
    quickActions: ['Analyze step', 'Surgical review', 'Map features'],
    proactiveMessages: false,
    focusEntities: ['vp_steps', 'personas']
  },
  // ... other modes
}
```

### 5.4 Bidirectional Tab Integration
**File:** `apps/workbench/lib/assistant/integration.ts`

```typescript
// Assistant actions that update tabs
interface AssistantToTabActions {
  navigateToEntity: (entityType: string, entityId: string) => void
  highlightEntity: (entityId: string) => void
  openModal: (modalType: string, data: any) => void
  updateEntityField: (entityId: string, field: string, value: any) => void
}

// Tab events that inform assistant
interface TabToAssistantEvents {
  onEntitySelected: (entity: Entity) => void
  onTabChanged: (tab: TabType) => void
  onSignalAdded: (signal: Signal) => void
  onConfirmationChanged: (entityId: string, status: string) => void
}
```

### 5.5 Proactive Behaviors
**File:** `apps/workbench/lib/assistant/proactive.ts`

```typescript
const PROACTIVE_TRIGGERS = {
  // On tab switch
  onTabSwitch: async (context: AssistantContext) => {
    if (context.activeTab === 'overview') {
      const blockers = await getBlockers(context.projectId)
      if (blockers.length > 0) {
        return { message: `You have ${blockers.length} blockers to address...` }
      }
    }
  },

  // On signal addition
  onSignalAdded: async (signal: Signal, context: AssistantContext) => {
    const claims = await extractClaims(signal)
    return {
      message: `I found ${claims.length} items in this signal. Want me to process them?`,
      actions: ['Process all', 'Review individually']
    }
  },

  // Periodic nudges (configurable)
  onIdle: async (context: AssistantContext) => {
    const pendingConfirmations = await getPendingConfirmations(context.projectId)
    if (pendingConfirmations.length > 5) {
      return {
        message: `You have ${pendingConfirmations.length} items pending confirmation. Want to review them?`
      }
    }
  }
}
```

---

## Phase 6: Frontend Integration

### 6.1 Assistant Panel Component
**File:** `apps/workbench/components/assistant/AssistantPanel.tsx`

```tsx
// Main assistant panel with context-aware UI
export function AssistantPanel({ context }: { context: AssistantContext }) {
  return (
    <div className="assistant-panel">
      {/* Context bar showing current mode/selection */}
      <ContextBar mode={context.mode} entity={context.selectedEntity} />

      {/* Quick actions grid */}
      <QuickActions actions={context.suggestedActions} />

      {/* Chat interface */}
      <ChatInterface messages={context.messages} />

      {/* Command input with autocomplete */}
      <CommandInput commands={COMMANDS} />
    </div>
  )
}
```

### 6.2 Design System Integration

Using your existing tokens from `lib/design-tokens.ts`:

```css
/* Assistant panel styling */
.assistant-panel {
  background: #FAFAFA;
  border-left: 1px solid #E5E5E5;
}

.assistant-context-bar {
  background: #044159;
  color: white;
  padding: 12px 16px;
}

.assistant-quick-action {
  background: white;
  border: 1px solid #E5E5E5;
  border-radius: 8px;
  padding: 8px 12px;
  color: #4B4B4B;
  transition: all 0.2s ease;
}

.assistant-quick-action:hover {
  border-color: #044159;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
}

.assistant-message-user {
  background: #044159;
  color: white;
  border-radius: 12px 12px 4px 12px;
}

.assistant-message-ai {
  background: white;
  border: 1px solid #E5E5E5;
  border-radius: 12px 12px 12px 4px;
}
```

### 6.3 Tab Integration Updates

Each tab receives assistant integration:

```tsx
// Example: FeaturesTab.tsx update
export function FeaturesTab() {
  const { setContext } = useAssistant()
  const [selectedFeature, setSelectedFeature] = useState(null)

  // Update assistant context when selection changes
  useEffect(() => {
    setContext({
      mode: 'features',
      selectedEntity: selectedFeature,
      suggestedActions: selectedFeature
        ? ['Enrich feature', 'View dependencies', 'Add acceptance criteria']
        : ['Add new feature', 'Find gaps', 'Import from signal']
    })
  }, [selectedFeature])

  // ... rest of component
}
```

---

## Files to Delete/Deprecate

After migration is complete:

| File | Reason |
|------|--------|
| `app/graphs/build_state_graph.py` | Replaced by unified_processor |
| `app/graphs/extract_facts_graph.py` | Merged into unified_processor |
| `app/chains/cascade_handler.py` | Replaced by dependency_manager |
| `app/chains/entity_cascade.py` | Replaced by dependency_manager |
| `app/db/prd.py` | PRD sections removed (strategic context only) |
| `app/chains/generate_prd_section_patch.py` | No longer needed |
| `app/api/enrich_prd.py` | No longer needed |
| `app/graphs/enrich_prd_graph.py` | No longer needed |

---

## Migration Strategy

### Step 1: Build Foundation (No Breaking Changes)
- Create new `core/` modules alongside existing code
- Add database tables with migrations
- Build assistant components in parallel

### Step 2: Wire Up New System
- Create unified processor graph
- Route new signals through unified system
- Keep old system as fallback

### Step 3: Migrate Existing Data
- Run migration scripts to populate version history
- Regenerate dependency graph
- Index existing research

### Step 4: Switch Over
- Update API endpoints to use new system
- Deprecate old endpoints
- Remove old files after verification

### Step 5: Polish
- Tune similarity thresholds based on real usage
- Optimize auto-enrichment triggers
- Refine assistant prompts

---

## API Endpoints Summary

### New Endpoints
```
POST /api/signals/process          # Unified signal processing
GET  /api/entities/{id}/history    # Version history
GET  /api/entities/{id}/sources    # Source attribution
POST /api/assistant/command        # Execute slash command
POST /api/assistant/chat           # Chat with context
GET  /api/research/query           # Query research index
POST /api/a-team/strategic         # Strategic review
POST /api/a-team/surgical/{id}     # Surgical VP analysis
```

### Deprecated Endpoints
```
POST /api/phase0/process           # → /api/signals/process
POST /api/baseline/finalize        # No longer needed (no mode)
```

---

## Testing Plan

### Unit Tests
- SimilarityMatcher with edge cases (typos, synonyms, partial matches)
- AutoConfirmation rules
- DependencyManager cascade propagation
- EntityVersioning diff computation

### Integration Tests
- Full signal processing flow
- Create vs update routing accuracy
- Enrichment trigger timing
- Assistant command execution

### E2E Tests
- Add signal → entities created → enriched
- Confirm entity → auto-enrichment runs
- Tab switch → assistant context updates
- Slash command → action executed → UI updated

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Create/Update accuracy | >95% correct routing |
| Auto-enrichment coverage | 100% of confirmed entities |
| Cascade propagation | <500ms for changes |
| Assistant response time | <2s for commands |
| Version history coverage | 100% of entity changes tracked |

---

## Next Steps

Ready to begin implementation. Recommended order:

1. **Start with Phase 1.1** - SimilarityMatcher (foundation for everything)
2. **Then Phase 1.4** - EntityVersioning (needed for safe updates)
3. **Then Phase 2.1** - UnifiedProcessor (main value delivery)
4. **Then Phase 5** - AssistantPanel (user-facing improvement)

Which phase would you like to start with?
