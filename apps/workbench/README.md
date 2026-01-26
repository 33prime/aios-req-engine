# Consultant Workbench

A Next.js frontend for the AIOS Requirements Engine, providing consultants with a unified 4-tab workspace to manage requirements, run AI agents, and review confirmations.

## Features

### Unified Workspace
- **4-Tab Interface**: Product Requirements, Value Path, Insights, Next Steps
- **Tab Navigation**: Instant switching between tabs with live counts
- **Consistent UX**: All tabs follow the same two-column pattern (list + detail)
- **Mobile Responsive**: Adaptive layout for all screen sizes

### Tab 1: Product Requirements (PRD)
- Review and confirm PRD sections (personas, key features, happy path, constraints)
- View AI-enriched content with supporting evidence
- Update status: Draft → Confirmed → Needs Confirmation → Confirmed (Client)
- Filter by status and section type

### Tab 2: Value Path (VP)
- Sequential VP steps with enrichment details
- Data schema, business logic, and transition logic views
- Status tracking and confirmation workflow
- Evidence-based step validation

### Tab 3: Insights (Red Team)
- Gap analysis with 5-gate validation (Completeness, Validation, Assumption, Scope, Wow)
- Filter by severity (critical, important, minor) and gate
- Decision workflow: Apply Internally, Needs Confirmation, or Dismiss
- Targeted entity tracking (which PRD/VP/features are affected)

### Tab 4: Next Steps (Confirmations)
- Batched client confirmations from all sources
- Complexity scoring with meeting recommendations
- Status workflow: Resolve, Queue for Meeting, or Dismiss
- Evidence tracking for all confirmation items

### Core Capabilities
- **Agent Execution**: Build state, reconcile, enrich PRD/VP, red-team analysis
- **Research Mode**: Toggle research access with baseline management
- **Signal Management**: Add client signals and research documents
- **Evidence Drilldown**: View source signals and chunks for all AI decisions
- **Job Monitoring**: Real-time async operation tracking with polling
- **Toast Notifications**: Professional feedback for all actions

## Setup

### Prerequisites

- Node.js 18+
- npm or yarn
- Running AIOS Requirements Engine backend

### Installation

```bash
cd apps/workbench
npm install
```

### Configuration

Create a `.env.local` file:

```bash
NEXT_PUBLIC_API_BASE=http://localhost:8001
```

### Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## Project Structure

```
apps/workbench/
├── app/
│   ├── layout.tsx                  # Root layout with ToastProvider
│   ├── globals.css                 # Global styles
│   ├── page.tsx                    # Landing page (project ID entry)
│   └── projects/[projectId]/
│       ├── page.tsx                # ✅ Unified 4-tab workspace
│       └── components/
│           ├── TabNavigation.tsx   # Tab navigation bar
│           ├── WorkspaceHeader.tsx # Header with actions
│           ├── AddSignalModal.tsx  # Add client signal
│           ├── AddResearchModal.tsx # Upload research
│           └── tabs/
│               ├── ProductRequirementsTab.tsx  # Tab 1
│               ├── ValuePathTab.tsx            # Tab 2
│               ├── InsightsTab.tsx             # Tab 3
│               ├── NextStepsTab.tsx            # Tab 4
│               ├── prd/                        # PRD components
│               ├── vp/                         # VP components
│               ├── insights/                   # Insights components
│               └── confirmations/              # Confirmations components
├── components/ui/              # Design system components
│   ├── StatusBadge.tsx        # Status, severity, gate, complexity badges
│   ├── Button.tsx             # Button components
│   ├── Card.tsx               # Card components
│   ├── TwoColumnLayout.tsx    # Two-column layout pattern
│   ├── Modal.tsx              # Modal dialog
│   └── Toast.tsx              # Toast notifications
├── lib/
│   ├── api.ts                 # API client
│   ├── design-tokens.ts       # Design system tokens
│   └── status-utils.ts        # Status utilities
├── styles/
│   └── design-system.css      # Custom CSS utilities
├── types/
│   └── api.ts                 # TypeScript definitions
├── MIGRATION_GUIDE.md         # Migration documentation
└── README.md                  # This file
```

## Backend API Dependencies

The workbench requires these backend endpoints (no changes from previous version):

### Jobs API
- `GET /v1/jobs/{job_id}` - Job status and results
- `GET /v1/jobs?project_id=...` - List project jobs

### Project APIs
- `GET /v1/projects/{id}/baseline` - Baseline status
- `PATCH /v1/projects/{id}/baseline` - Update baseline

### State APIs
- `GET /v1/state/features?project_id=...` - Features
- `GET /v1/state/prd?project_id=...` - PRD sections
- `GET /v1/state/vp?project_id=...` - VP steps
- `PATCH /v1/state/vp/{id}/status` - Update VP step status

### Agent APIs
- `POST /v1/state/build` - Build state
- `POST /v1/state/reconcile` - Reconcile state
- `POST /v1/agents/enrich-features` - Feature enrichment
- `POST /v1/agents/enrich-personas` - Persona enrichment
- `POST /v1/agents/enrich-vp` - VP enrichment

### Insights APIs
- `GET /v1/insights?project_id=...` - List insights
- `PATCH /v1/insights/{id}/apply` - Apply insight internally
- `POST /v1/insights/{id}/confirm` - Create confirmation from insight
- `PATCH /v1/insights/{id}/dismiss` - Dismiss insight

### Confirmation APIs
- `GET /v1/confirmations?project_id=...&status=...` - List confirmations
- `PATCH /v1/confirmations/{id}/status` - Update confirmation status

### Signal APIs
- `POST /v1/signals` - Create new signal
- `GET /v1/signals/{id}` - Signal details
- `GET /v1/signals/{id}/chunks` - Signal chunks

### Research APIs
- `POST /v1/research/ingest` - Upload research document

## Usage Guide

### 1. Enter Project ID

- Visit the workbench homepage
- Enter your project UUID (e.g., `97e0dc34-feb9-48ca-a3a3-ba104d9e8203`)
- Click "Open Project"

### 2. Project Dashboard

The dashboard shows:
- **Stats**: Feature counts, enrichment status, open confirmations
- **Navigation**: Links to Features, PRD, VP, and Confirmations pages
- **Agent Actions**: Buttons to run build state, reconcile, and red-team
- **Baseline Toggle**: Enable/disable research access

### 3. Managing Features

- View all features with MVP status, confidence levels, and status
- **Enrich Features**: Run AI enrichment on MVP or all features
- **View Enrichment**: See AI-generated business rules, risks, and acceptance criteria
- **Evidence**: Click to view supporting signal chunks

### 4. Reviewing Confirmations

- **Status Filters**: View open, queued, resolved, dismissed, or all confirmations
- **Detail View**: Click any confirmation to see full details and evidence
- **Actions**:
  - **Confirm & Resolve**: Mark as resolved with consultant approval
  - **Queue for Meeting**: Flag for client discussion
  - **Dismiss**: Remove from consideration
- **Evidence Drilldown**: View source signals and chunks

### 5. Running Agents

- **Build State**: Extract initial features/PRD/VP from signals
- **Reconcile**: Update canonical state and create confirmations
- **Red Team**: Generate insights and identify risks
- **Enrich**: Add structured details to features/PRD/VP

All agents run asynchronously with job status monitoring.

### 6. Baseline Management

- **Toggle**: Enable/disable research access per project
- **Research Features**: When enabled, agents can use research signals
- **Safety**: Research never changes canonical truth, only influences insights

## Development

### Adding New Pages

Create new route folders under `app/projects/[projectId]/`:

```
app/projects/[projectId]/new-feature/
├── page.tsx
└── components/
```

### API Integration

Use the API client in `lib/api.ts`:

```typescript
import { getFeatures, enrichFeatures } from '@/lib/api'

// Use in components
const features = await getFeatures(projectId)
```

### Components

Reusable components in `components/`:
- Button styles via Tailwind
- Loading states
- Error handling
- Modal dialogs

## Smoke Tests

### Backend Tests

1. **Jobs API**
   ```bash
   # Get job status
   curl "http://localhost:8001/v1/jobs/{job_id}"

   # List project jobs
   curl "http://localhost:8001/v1/jobs?project_id={project_id}&limit=5"
   ```

2. **Confirmations API**
   ```bash
   # List confirmations
   curl "http://localhost:8001/v1/confirmations?project_id={project_id}&status=open"

   # Update confirmation
   curl -X PATCH "http://localhost:8001/v1/confirmations/{id}/status" \
     -H "Content-Type: application/json" \
     -d '{"status": "resolved", "resolution_evidence": {"type": "email", "ref": "approved", "note": "Consultant approved"}}'
   ```

### Frontend Tests

1. **Project Access**
   - Visit `http://localhost:3000`
   - Enter project ID
   - Should load dashboard with stats

2. **Agent Execution**
   - Click "Build State" button
   - Should show loading, then success alert
   - Stats should update

3. **Baseline Toggle**
   - Toggle baseline switch
   - Should change from false to true
   - Research-enabled agents should work

4. **Features Page**
   - Navigate to Features
   - Should show feature cards
   - Click "Enrich MVP Features"
   - Should add enrichment details

5. **Confirmations Page**
   - Navigate to Confirmations
   - Should show confirmation items
   - Click item to view details
   - Click "Confirm & Resolve"
   - Should update status and refresh list

6. **Evidence Drilldown**
   - In confirmations, click "View source" on evidence
   - Should show modal with signal chunks
   - Should display source text and metadata

## Troubleshooting

### API Connection Issues
- Check `NEXT_PUBLIC_API_BASE` environment variable
- Ensure backend is running on correct port
- Check CORS settings on backend

### Job Status Not Updating
- Jobs use polling every 2 seconds
- Check browser console for errors
- Verify job ID is valid

### Features Not Loading
- Run "Build State" agent first
- Check project has signals
- Verify project ID is correct

## Contributing

1. Follow TypeScript strict mode
2. Use Tailwind for styling
3. Add error boundaries for API calls
4. Test with real project data
5. Update this README for new features
