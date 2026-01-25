# Business Drivers UI Enrichment Plan

## Executive Summary

Business Drivers (KPIs, Pain Points, Goals) are currently displayed with minimal information (description + 1-2 fields) in simple colored cards. This plan upgrades them to match the rich, professional feature card design with expandable sections, enrichment indicators, evidence attribution, and confirmation workflows.

**Goal**: Make business drivers as visually rich and informative as features, using the same brand colors and design patterns.

---

## Current State Analysis

### Features UI (Reference Implementation)
**Location**: `apps/workbench/components/features/FeatureCard.tsx`

#### Visual Elements
- ✅ Expandable card with hover effects (`hover:shadow-md hover:border-blue-200`)
- ✅ Header always visible with name, badges, category, confidence
- ✅ Sparkles icon for AI enrichment
- ✅ Confirmation status badges (Client Confirmed, Confirmed, Needs Review, AI Draft)
- ✅ Confidence dots (high=3, medium=2, low=1)
- ✅ Preview when collapsed (line-clamp-2)
- ✅ Chevron expand/collapse indicator

#### Enriched Content Sections
- **Overview**: Business-friendly description (Markdown supported)
- **Target Personas**: Who uses this (Primary/Secondary roles with context)
- **User Actions**: Step-by-step what users do
- **System Behaviors**: Behind-the-scenes operations
- **UI Requirements**: What users see
- **Business Rules**: Validation and constraints
- **Integrations**: External systems
- **Evidence**: Source attribution with excerpts and rationale
- **Dependencies**: Related features

#### Color Scheme
- Primary Brand: `bg-brand-primary` (teal #009b87)
- Status badges:
  - Green: Confirmed client (`bg-green-100 text-green-800`)
  - Blue: Confirmed consultant (`bg-blue-100 text-blue-800`)
  - Amber: Needs review (`bg-amber-100 text-amber-800`)
  - Gray: AI draft (`bg-gray-100 text-gray-700`)

### Business Drivers Current State
**Location**: `apps/workbench/app/projects/[projectId]/components/tabs/StrategicFoundationTab.tsx` (line 912)

#### Current Display
- Simple colored cards in 3-column grid
- **KPIs**: Green background (`bg-green-50 border-green-100`)
  - Shows: description, measurement (as "Target"), timeframe
- **Pain Points**: Red background (`bg-red-50 border-red-100`)
  - Shows: description, measurement (as "Impact")
- **Goals**: Emerald background (`bg-emerald-50 border-emerald-100`)
  - Shows: description, timeframe
- Edit/delete buttons on hover
- **No enrichment display**
- **No expansion** - everything always visible
- **No evidence attribution**
- **No confirmation workflow**

---

## Database Schema (Already Exists)

### business_drivers Table
From migration `0071_business_drivers_enrichment_fields.sql`:

#### KPI Fields
- `baseline_value` - Current state (e.g., "5 seconds average")
- `target_value` - Desired state (e.g., "2 seconds average")
- `measurement_method` - How measured (e.g., "Google Analytics")
- `tracking_frequency` - How often (e.g., "daily", "weekly")
- `data_source` - Where data comes from (e.g., "Mixpanel dashboard")
- `responsible_team` - Who owns it (e.g., "Growth team", "Sarah (PM)")

#### Pain Point Fields
- `severity` - critical | high | medium | low
- `frequency` - constant | daily | weekly | monthly | rare
- `affected_users` - Who feels this (e.g., "All warehouse staff")
- `business_impact` - Quantified impact (e.g., "$50K/month in lost sales")
- `current_workaround` - How they cope now (e.g., "Manual Excel exports")

#### Goal Fields
- `goal_timeframe` - When to achieve (e.g., "Q2 2024")
- `success_criteria` - Concrete success (e.g., "50+ paying customers")
- `dependencies` - Prerequisites (e.g., "Payment integration")
- `owner` - Who delivers (e.g., "VP Sales")

#### Shared Fields
- `confirmation_status` - ai_generated | confirmed_consultant | needs_client | confirmed_client
- `enrichment_status` - none | enriched | stale
- `enrichment_attempted_at` - Timestamp
- `enrichment_error` - Error message if failed
- `evidence` - JSONB array with signal attribution
- `source_signal_ids` - Array of UUIDs
- `priority` - Integer 1-5
- `notes` - Additional context

---

## Enrichment Chains (Already Implemented)

### app/chains/enrich_kpi.py
**Model**: Pydantic `KPIEnrichment`
**Extracts**: baseline_value, target_value, measurement_method, tracking_frequency, data_source, responsible_team

### app/chains/enrich_pain_point.py
**Model**: Pydantic `PainPointEnrichment`
**Extracts**: severity, frequency, affected_users, business_impact, current_workaround

### app/chains/enrich_goal.py
**Model**: Pydantic `GoalEnrichment`
**Extracts**: goal_timeframe, success_criteria, dependencies, owner

All chains:
- Search project signals for context
- Use evidence to enrich
- Return confidence score (0.0-1.0)
- Return reasoning for transparency

---

## Proposed UI Design

### KPI Card (Enriched)

#### Header (Always Visible)
```
[Target Icon] Reduce page load time
[MVP?] [✨ AI Enriched] [Confirmed Client]
Performance • ●●● High
```

#### Preview (Collapsed)
```
Baseline: 5s average → Target: 2s average | Weekly tracking via Google Analytics
```

#### Expanded Sections
1. **Overview** (if we add it)
   - Business-friendly: "Fast page loads are critical for conversion. Current 5s loads causing 30% bounce rate."

2. **Measurement**
   - Icon: 📊 Measurement Details
   - **Baseline**: "5 seconds average load time"
   - **Target**: "2 seconds average load time"
   - **Gap**: -3 seconds (calculated)
   - **Method**: "Google Analytics Core Web Vitals - Largest Contentful Paint (LCP)"
   - **Tracking**: Daily (automated dashboard)
   - **Data Source**: "Google Analytics 4 + Mixpanel Performance tracking"
   - **Owner**: "Growth team (Sarah - Product Manager)"

3. **Business Impact** (NEW - infer from signals)
   - Icon: 💰 Business Impact
   - Associated features that depend on this KPI
   - User personas affected
   - Related pain points

4. **Evidence** (like features)
   - Source chunks with excerpts

#### Color Scheme
- Background: `bg-green-50` (keep current green)
- Border: `border-green-200`
- Text: `text-green-900` (dark green headings)
- Accent: `text-green-700` (medium green body)
- Icons: `text-green-600`

---

### Pain Point Card (Enriched)

#### Header (Always Visible)
```
[AlertCircle Icon] Manual data entry takes 4 hours daily
[Critical] [Constant] [✨ AI Enriched] [Needs Review]
Operations • ●● Medium
```

#### Preview (Collapsed)
```
Affects: All warehouse staff | Impact: $50K/month in labor costs | No current workaround
```

#### Expanded Sections
1. **Pain Details**
   - Icon: ⚠️ Impact Analysis
   - **Severity**: Critical (color-coded badge: critical=red, high=orange, medium=yellow, low=gray)
   - **Frequency**: Constant (always occurs)
   - **Affected Users**: "All warehouse staff (15 people)"
   - **Business Impact**: "~$50,000/month in labor costs + 20% error rate"
   - **Current Workaround**: "Manual Excel spreadsheets sent via email daily"

2. **Solutions** (NEW - link to features)
   - Icon: 🔧 Addressing This Pain
   - List features designed to solve this pain
   - Show completion status of solutions
   - Link to related goals

3. **User Impact** (NEW - link to personas)
   - Icon: 👥 Who Feels This
   - Primary personas affected
   - Their specific frustrations
   - Quotes from evidence

4. **Evidence**
   - Source attribution

#### Color Scheme
- Background: `bg-red-50` (keep current red)
- Border: `border-red-200`
- Text: `text-red-900` (dark red headings)
- Accent: `text-red-700` (medium red body)
- Severity badges:
  - Critical: `bg-red-600 text-white`
  - High: `bg-orange-500 text-white`
  - Medium: `bg-yellow-500 text-white`
  - Low: `bg-gray-500 text-white`

---

### Goal Card (Enriched)

#### Header (Always Visible)
```
[Sparkles Icon] Launch MVP in Q2 2024
[High Priority] [✨ AI Enriched] [Confirmed Consultant]
Product • ●●● High
```

#### Preview (Collapsed)
```
Q2 2024 | Success: 100+ beta users, 50+ paying customers | Depends on: Payment integration
```

#### Expanded Sections
1. **Goal Details**
   - Icon: 🎯 Achievement Criteria
   - **Timeframe**: "Q2 2024 (April-June)"
   - **Success Criteria**:
     - "100+ beta users signed up"
     - "50+ paying customers"
     - "NPS score > 40"
   - **Dependencies**:
     - "Payment processor integration (Stripe)"
     - "Beta testing program complete"
     - "Marketing site live"
   - **Owner**: "VP Product (Sarah Chen)"

2. **Progress** (NEW - calculated from features)
   - Icon: 📈 Toward This Goal
   - % features completed that support this goal
   - Key milestones
   - Blockers/risks

3. **Supporting Features** (NEW)
   - Icon: 🔗 Features Driving This
   - List features tagged to this goal
   - Show their status (confirmed, in progress, blocked)

4. **Related Metrics** (NEW)
   - Icon: 📊 Success Indicators
   - KPIs that measure this goal
   - Current vs target

5. **Evidence**
   - Source attribution

#### Color Scheme
- Background: `bg-emerald-50` (keep current emerald/brand teal)
- Border: `border-emerald-200`
- Text: `text-gray-900` (dark neutral - brand teal for accents)
- Accent: `text-emerald-700` / `text-[#009b87]` (brand teal)
- Priority badges:
  - High: `bg-emerald-600 text-white`
  - Medium: `bg-blue-500 text-white`
  - Low: `bg-gray-400 text-white`

---

## Implementation Plan

### Phase 1: Component Infrastructure (Week 1)

#### Task 1.1: Create Base BusinessDriverCard Component
**File**: `apps/workbench/components/business-drivers/BusinessDriverCard.tsx`

**Pattern**: Mirror FeatureCard.tsx structure

```tsx
interface BusinessDriverCardProps {
  driver: BusinessDriver // with enrichment fields
  onConfirmationChange?: (driverId: string, newStatus: string) => Promise<void>
  onViewEvidence?: (chunkId: string) => void
  defaultExpanded?: boolean
}

// Core structure:
- Header (always visible): name, badges, type, confidence
- Preview (collapsed): 1-line enrichment summary
- Expanded sections: type-specific enrichment
- Confirmation actions (if handler provided)
- Evidence (if present)
```

**Features**:
- Expandable (useState for expanded state)
- Confirmation status badges (reuse FeatureCard logic)
- Confidence indicators (3 dots)
- Sparkles icon if enriched
- Hover effects matching features
- Edit/delete buttons (pass-through)

#### Task 1.2: Create Type-Specific Section Components

**File**: `apps/workbench/components/business-drivers/KPISections.tsx`
- `MeasurementDetailsSection` - baseline, target, method, frequency, source, owner
- `BusinessImpactSection` (NEW) - features, personas, related pains

**File**: `apps/workbench/components/business-drivers/PainSections.tsx`
- `PainDetailsSection` - severity, frequency, affected users, impact, workaround
- `SolutionsSection` (NEW) - features addressing this pain
- `UserImpactSection` (NEW) - personas affected

**File**: `apps/workbench/components/business-drivers/GoalSections.tsx`
- `GoalDetailsSection` - timeframe, criteria, dependencies, owner
- `ProgressSection` (NEW) - % features complete
- `SupportingFeaturesSection` (NEW) - features tagged to goal
- `RelatedMetricsSection` (NEW) - KPIs measuring this

#### Task 1.3: Update API Types
**File**: `apps/workbench/types/api.ts`

Add enrichment fields to BusinessDriver interface:
```typescript
interface BusinessDriver {
  // Existing
  id: string
  driver_type: 'kpi' | 'pain' | 'goal'
  description: string
  priority: number
  confirmation_status: string
  evidence?: Evidence[]

  // Add enrichment
  enrichment_status?: 'none' | 'enriched' | 'stale'
  enriched_at?: string

  // KPI
  baseline_value?: string
  target_value?: string
  measurement_method?: string
  tracking_frequency?: string
  data_source?: string
  responsible_team?: string

  // Pain
  severity?: 'critical' | 'high' | 'medium' | 'low'
  frequency?: 'constant' | 'daily' | 'weekly' | 'monthly' | 'rare'
  affected_users?: string
  business_impact?: string
  current_workaround?: string

  // Goal
  goal_timeframe?: string
  success_criteria?: string
  dependencies?: string
  owner?: string
}
```

---

### Phase 2: Enrichment Backend Integration (Week 1-2)

#### Task 2.1: API Endpoint for Enrichment Trigger
**File**: `app/api/business_drivers.py`

Add endpoint:
```python
@router.post("/{driver_id}/enrich")
async def enrich_business_driver(
    project_id: UUID,
    driver_id: UUID,
    depth: Literal["quick", "standard", "deep"] = "standard"
)
```

Call appropriate chain based on driver_type.

#### Task 2.2: Update List Endpoint to Return Enrichment
Modify `list_business_drivers()` to include all enrichment fields.

#### Task 2.3: Cross-Entity Associations (NEW)

**File**: `app/db/business_drivers.py`

Add queries:
```python
def get_driver_associated_features(driver_id: UUID) -> list[dict]:
    """Get features that reference this driver (via target_personas, goals, etc.)"""

def get_driver_associated_personas(driver_id: UUID) -> list[dict]:
    """Get personas affected by this driver"""

def get_driver_related_drivers(driver_id: UUID) -> dict:
    """Get related KPIs, pains, goals"""
```

**File**: `app/api/business_drivers.py`

Add endpoint:
```python
@router.get("/{driver_id}/associations")
async def get_driver_associations(driver_id: UUID)
```

Returns:
```json
{
  "features": [...],
  "personas": [...],
  "related_kpis": [...],
  "related_pains": [...],
  "related_goals": [...]
}
```

---

### Phase 3: UI Implementation (Week 2)

#### Task 3.1: Replace Simple Cards with BusinessDriverCard
**File**: `apps/workbench/app/projects/[projectId]/components/tabs/StrategicFoundationTab.tsx`

Replace sections in `BusinessDriversSubTab`:
```tsx
// BEFORE:
<div className="p-3 bg-green-50 rounded-lg">
  <div className="font-medium">{kpi.description}</div>
  {kpi.measurement && <div>Target: {kpi.measurement}</div>}
</div>

// AFTER:
<BusinessDriverCard
  driver={kpi}
  onConfirmationChange={handleConfirmationChange}
  onViewEvidence={handleViewEvidence}
/>
```

#### Task 3.2: Add Enrichment Trigger Button
In BusinessDriverCard header actions:
```tsx
{!isEnriched && (
  <button onClick={handleEnrich} className="...">
    <Sparkles /> Enrich
  </button>
)}
```

#### Task 3.3: Load Associations
Update `loadData()` in StrategicFoundationTab to fetch associations for enriched drivers:
```tsx
const driversWithAssociations = await Promise.all(
  enrichedDrivers.map(async (d) => ({
    ...d,
    associations: await fetchAssociations(d.id)
  }))
)
```

---

### Phase 4: Smart Enrichment Features (Week 3)

#### Task 4.1: Auto-Enrich New Drivers
When drivers are created from signals, automatically trigger enrichment if confidence >= 0.7.

**File**: `app/core/process_strategic_facts.py`

After `smart_upsert_business_driver`, check if action was "created" and trigger enrichment.

#### Task 4.2: Enrichment Status Indicators
Show enrichment freshness:
- `enrichment_status: 'enriched'` → Green checkmark
- `enrichment_status: 'stale'` → Yellow warning (data changed)
- `enrichment_status: 'none'` → Gray "Not enriched"

#### Task 4.3: Bulk Enrichment
Add button in BusinessDriversSubTab to enrich all non-enriched drivers:
```tsx
<button onClick={handleBulkEnrich}>
  Enrich All ({nonEnrichedCount})
</button>
```

Triggers enrichment in parallel with progress indicator.

---

### Phase 5: Association Intelligence (Week 3-4)

#### Task 5.1: Feature-to-Driver Linking
**How**: When features mention KPIs/pains/goals in their descriptions, create associations.

**Algorithm**:
1. Semantic similarity between feature descriptions and driver descriptions (embeddings)
2. Explicit references in feature evidence to drivers
3. Personas in common (feature.target_personas overlap with pain.affected_users)

**File**: `app/core/link_entities.py` (NEW)
```python
def link_features_to_drivers(project_id: UUID):
    """Find and create associations between features and business drivers"""
```

#### Task 5.2: Goal-to-KPI Linking
Goals should automatically link to KPIs that measure them.

**Algorithm**:
- Match goal.success_criteria text to kpi.description
- Semantic similarity
- Shared evidence sources

#### Task 5.3: Pain-to-Feature Linking
Pain points should show which features solve them.

**Algorithm**:
- Feature that mentions pain in evidence
- Features with personas matching pain.affected_users
- Semantic similarity (feature solving the pain)

---

## Design Specifications

### Typography
- **Section headers**: `text-xs font-medium text-gray-500 uppercase tracking-wide` (like features)
- **Values**: `text-sm text-gray-700` (body)
- **Emphasis**: `font-medium text-gray-900`

### Spacing
- **Card padding**: `p-4`
- **Section spacing**: `space-y-4`
- **Item spacing**: `space-y-2` or `space-y-3`

### Icons (Lucide React)
- KPIs: `Target`, `TrendingUp`, `BarChart3`, `Activity`
- Pain Points: `AlertCircle`, `AlertTriangle`, `XCircle`, `Frown`
- Goals: `Sparkles`, `Flag`, `Award`, `CheckCircle`
- Measurement: `Ruler`, `GitBranch`
- Users: `Users`, `User`
- Features: `Zap`, `Box`
- Evidence: `FileText`, `Link2`

### Badges
Follow FeatureCard pattern:
```tsx
<span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-{color}-100 text-{color}-800 border border-{color}-200">
```

### Transitions
- `transition-all duration-200` on cards
- `transition-opacity` on hover buttons
- `transition-colors` on badges/buttons

---

## Success Criteria

### Visual Consistency
✅ Business driver cards match feature card design quality
✅ Same brand colors, spacing, typography
✅ Same hover effects and transitions
✅ Same confirmation workflow UI

### Enrichment Display
✅ All enrichment fields visible in expanded view
✅ Clear visual hierarchy (headers, sections, values)
✅ Icons for each section matching semantic meaning
✅ Evidence attribution displayed like features

### Cross-Entity Intelligence
✅ KPIs show features contributing to them
✅ Pain points show features solving them
✅ Goals show % progress from features
✅ Personas linked to relevant drivers

### User Experience
✅ One-click enrichment from card
✅ Clear loading states during enrichment
✅ Bulk enrichment option
✅ Evidence viewable inline
✅ Confirmation status workflow

---

## Migration Strategy

### Backward Compatibility
- All new enrichment fields are nullable
- Existing drivers work without enrichment
- Gradual enrichment as signals processed

### Data Migration
No migration needed - enrichment fields already exist from migration 0071.

### Rollout
1. Deploy backend changes (enrichment endpoints, associations)
2. Deploy frontend with feature flag `ENABLE_DRIVER_ENRICHMENT`
3. Test on internal project
4. Enable for all projects
5. Backfill enrichment for existing drivers

---

## Effort Estimate

### Phase 1 (Components): 3-4 days
- BusinessDriverCard component: 1 day
- Type-specific sections: 1.5 days
- API types update: 0.5 day

### Phase 2 (Backend): 2-3 days
- Enrichment endpoints: 1 day
- Association queries: 1.5 days
- Testing: 0.5 day

### Phase 3 (UI Integration): 2 days
- Replace cards: 1 day
- Enrichment triggers: 0.5 day
- Association loading: 0.5 day

### Phase 4 (Smart Features): 2 days
- Auto-enrich: 0.5 day
- Status indicators: 0.5 day
- Bulk enrichment: 1 day

### Phase 5 (Associations): 3-4 days
- Linking algorithms: 2 days
- Testing: 1 day
- Performance optimization: 1 day

**Total**: ~12-15 days (2.5-3 weeks)

---

## Future Enhancements

### Analytics
- Show KPI trends over time (if tracked)
- Pain point priority heatmap
- Goal completion timeline

### AI Suggestions
- Suggest KPIs for goals automatically
- Suggest features to solve pains
- Identify missing drivers from signals

### Collaboration
- Comments on drivers
- @mentions for owners
- Approval workflow for consultants

### Reporting
- Export drivers to PDF
- Strategic summary generation
- Stakeholder-facing views
