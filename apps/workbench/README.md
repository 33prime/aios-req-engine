# Consultant Workbench

A Next.js frontend for the AIOS Requirements Engine, providing consultants with a canvas-based workspace to manage requirements, track readiness, and collaborate with clients.

## Features

### Projects Dashboard
- **Table & Kanban views**: Switch between list and stage-based kanban board
- **Stage progression**: Discovery → Validation → Prototype → Proposal → Build → Live
- **Readiness scoring**: Dimensional scoring (value path, problem, solution, engagement) with gate-based progression
- **Smart project creation**: AI-assisted project setup via chat

### Canvas Workspace
- **Overview**: Status narrative, readiness score, tasks, next actions, upcoming meetings
- **Discovery**: Drag-and-drop requirements canvas with personas, journey steps, and feature mapping
- **Build**: Prototype embed with URL management and readiness tracking
- **Collaboration panel**: Chat, portal management, and activity feed

### Core Capabilities
- **Agent Execution**: Build state, enrich features/personas/VP, research agents
- **Signal Management**: Add client signals and research documents
- **Client Portal**: Invite clients, manage phases, send packages
- **Task Management**: Project tasks with priorities and assignments
- **Memory System**: Knowledge graph, beliefs, tribal knowledge

## Setup

### Prerequisites

- Node.js 18+
- npm
- Running AIOS Requirements Engine backend

### Installation

```bash
cd apps/workbench
npm install
```

### Configuration

Create a `.env.local` file:

```bash
NEXT_PUBLIC_API_BASE=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=your-supabase-url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
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
│   ├── layout.tsx                    # Root layout with auth + toast
│   ├── globals.css                   # Global styles + design system import
│   ├── page.tsx                      # Landing / auth page
│   ├── projects/
│   │   ├── page.tsx                  # Projects dashboard (table + kanban)
│   │   └── components/               # Dashboard components
│   │       ├── ProjectsTopNav.tsx    # View toggle, search, create
│   │       ├── ProjectsTable.tsx     # Table view
│   │       ├── ProjectsKanban.tsx    # Kanban board
│   │       ├── StageColumn.tsx       # Kanban stage column
│   │       ├── ProjectKanbanCard.tsx # Kanban project card
│   │       ├── ProjectRow.tsx        # Table row
│   │       └── StageAdvancePopover.tsx # Stage gate checklist
│   ├── projects/[projectId]/
│   │   ├── page.tsx                  # Project detail page
│   │   └── components/               # Project-level components
│   ├── settings/                     # Admin settings
│   └── people/                       # People management
├── components/
│   ├── ui/                           # Design system primitives
│   │   ├── Button.tsx, Card.tsx, Modal.tsx, Toast.tsx
│   │   ├── StatusBadge.tsx, TwoColumnLayout.tsx
│   │   ├── Markdown.tsx, popover.tsx
│   │   └── DeleteConfirmationModal.tsx
│   ├── workspace/                    # Canvas workspace
│   │   ├── WorkspaceLayout.tsx       # Three-zone layout
│   │   ├── OverviewPanel.tsx         # Overview dashboard
│   │   ├── BuildPhaseView.tsx        # Build phase
│   │   ├── PhaseSwitcher.tsx         # Phase navigation
│   │   ├── CollaborationPanel.tsx    # Right panel
│   │   ├── AppSidebar.tsx            # Left sidebar
│   │   ├── BottomDock.tsx            # Bottom panels
│   │   └── canvas/                   # Discovery canvas
│   │       ├── RequirementsCanvas.tsx
│   │       ├── JourneyFlow.tsx, PersonaRow.tsx
│   │       ├── FeatureChip.tsx, StoryEditor.tsx
│   │       └── detail drawers...
│   ├── personas/                     # Persona components
│   ├── tasks/                        # Task management
│   └── meeting/                      # Meeting components
├── lib/
│   ├── api.ts                        # API client (~150 functions)
│   ├── design-tokens.ts              # Design system tokens
│   ├── status-utils.ts               # Status utilities
│   ├── persona-utils.ts              # Persona helpers
│   ├── export-utils.ts               # Export helpers
│   ├── useChat.ts                    # Chat hook (SSE)
│   ├── supabase.ts                   # Supabase client
│   └── assistant/                    # AI assistant system
├── styles/
│   └── design-system.css             # CSS design system
└── types/
    ├── api.ts                        # API type definitions
    └── workspace.ts                  # Workspace types
```

## Testing

```bash
# E2E tests (Playwright)
npx playwright test

# Specific test file
npx playwright test e2e/stage-progression.spec.ts
```

## Contributing

1. Follow TypeScript strict mode
2. Use Tailwind for styling — check `lib/design-tokens.ts` for tokens
3. Use existing `components/ui/*` primitives
4. Test with real project data
