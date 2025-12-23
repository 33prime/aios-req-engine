# Frontend Migration Guide

## Overview

The workbench frontend has been rebuilt from a multi-page application into a unified 4-tab workspace. This guide explains the changes and how to navigate the new structure.

## What Changed

### Before (Multi-Page)
- `/projects/[projectId]` - Dashboard/overview
- `/projects/[projectId]/prd` - PRD sections page
- `/projects/[projectId]/vp` - Value Path steps page
- `/projects/[projectId]/insights` - Insights page
- `/projects/[projectId]/confirmations` - Confirmations page

### After (Unified Workspace)
- `/projects/[projectId]` - **Single workspace page with 4 tabs**
  - Tab 1: Product Requirements
  - Tab 2: Value Path
  - Tab 3: Insights
  - Tab 4: Next Steps (Confirmations)

## Architecture Changes

### Old Structure (Archived)
```
app/projects/[projectId]/
├── page.tsx                    # Old dashboard
├── prd/page.tsx               # ❌ Archived
├── vp/page.tsx                # ❌ Archived
├── insights/page.tsx          # ❌ Archived
└── confirmations/page.tsx     # ❌ Archived
```

### New Structure (Active)
```
app/projects/[projectId]/
├── page.tsx                    # ✅ Unified workspace
├── components/
│   ├── TabNavigation.tsx
│   ├── WorkspaceHeader.tsx
│   ├── AddSignalModal.tsx
│   ├── AddResearchModal.tsx
│   └── tabs/
│       ├── ProductRequirementsTab.tsx
│       ├── ValuePathTab.tsx
│       ├── InsightsTab.tsx
│       ├── NextStepsTab.tsx
│       ├── prd/
│       │   ├── PrdList.tsx
│       │   └── PrdDetail.tsx
│       ├── vp/
│       │   ├── VpList.tsx
│       │   └── VpDetail.tsx
│       ├── insights/
│       │   ├── InsightsList.tsx
│       │   └── InsightDetail.tsx
│       └── confirmations/
│           ├── ConfirmationsList.tsx
│           └── ConfirmationDetail.tsx
└── _archive/
    └── old_pages/              # Old standalone pages
```

## Design System

### New Components (`/components/ui`)

All tabs use a consistent design system with reusable components:

**Badges**
- `StatusBadge` - AI Draft, Confirmed, Needs Confirmation, Confirmed (Client)
- `SeverityBadge` - Minor, Important, Critical
- `GateBadge` - Completeness, Validation, Assumption, Scope, Wow
- `ComplexityBadge` - Low, Medium, High (for confirmations)

**Buttons**
- `Button` - Primary, Secondary, Outline variants
- `IconButton` - Icon-only buttons with labels
- `ButtonGroup` - Grouped button layout

**Cards**
- `Card` - Base card container
- `CardHeader` - Card header with title/actions
- `CardSection` - Card body section
- `CardFooter` - Card footer

**Layout**
- `TwoColumnLayout` - Standard two-column pattern (list + detail)
- `ListItem` - Selectable list item with badge
- `EmptyState` - Empty state placeholder

**Dialogs**
- `Modal` - Reusable modal dialog
- `ToastProvider` / `useToast()` - Toast notifications

### Design Tokens (`/lib/design-tokens.ts`)

Centralized colors, typography, and styles:
- **Brand**: `#044159` (primary), `#88BABF` (accent)
- **Typography**: Inter font, 5 text styles (h1, h2, section, body, support)
- **Status colors**: Per status type with background/text variants
- **Gate colors**: Per gate type with icons and descriptions

### Custom CSS (`/styles/design-system.css`)

Typography classes, card styles, workspace grid, and sticky sidebar utilities.

## Key Features

### 1. Unified Navigation
- **Tab switching** - No page reloads, instant transitions
- **Tab counts** - Show item counts on each tab
- **Mobile-friendly** - Responsive tab navigation for mobile

### 2. Consistent Patterns
All 4 tabs follow the same pattern:
- **Two-column layout** - List (left) + Detail (right)
- **Status badges** - Visual status indicators
- **Evidence modals** - View source signals for all items
- **Filter options** - Filter by status, severity, gate, etc.
- **Action buttons** - Consistent decision workflows

### 3. Header Actions
- **Add Signal** - Upload client communications
- **Add Research** - Upload research documents
- **Run Agent** - Dropdown menu for all agent actions
- **Research Toggle** - Enable/disable research mode
- **Refresh** - Reload workspace data

### 4. Improved UX
- **Toast notifications** - Replace browser alerts
- **Loading states** - Proper loading indicators
- **Empty states** - Helpful empty state messages
- **Keyboard support** - ESC to close modals
- **Auto-save** - Status updates saved immediately

## Migration Checklist

If you have custom code that references the old pages:

- [ ] Update any hardcoded navigation links to use the new workspace URL
- [ ] Replace `alert()` calls with `useToast()` for better UX
- [ ] Use the new design system components instead of custom styles
- [ ] Import from `@/components/ui` for consistent styling
- [ ] Follow the two-column layout pattern for new features

## API Compatibility

✅ **No backend changes required** - All existing API endpoints remain the same:
- `/v1/state/prd` - PRD sections
- `/v1/state/vp` - VP steps
- `/v1/insights` - Insights
- `/v1/confirmations` - Confirmations
- All agent endpoints unchanged

## Old Pages (Archived)

Old standalone pages are preserved in `_archive/old_pages/` for reference:
- `prd/page.tsx`
- `vp/page.tsx`
- `insights/page.tsx`
- `confirmations/page.tsx`

Old components archived in `/components/_archive/`:
- `PrdDetailCard.tsx`
- `VpDetailCard.tsx`
- `InsightsDashboard.tsx`

## Breaking Changes

⚠️ **Navigation URLs**
- Old: `/projects/[id]/prd`, `/projects/[id]/vp`, etc.
- New: `/projects/[id]` with tab navigation

⚠️ **Component Imports**
- Old: `import PrdDetailCard from '@/components/PrdDetailCard'`
- New: `import { PrdDetail } from './tabs/prd'`

## Benefits of New Structure

1. **Faster navigation** - No page reloads between tabs
2. **Consistent UX** - All tabs use same patterns
3. **Better mobile** - Responsive design throughout
4. **Easier maintenance** - Shared components, less duplication
5. **Professional polish** - Toast notifications, modals, animations
6. **Centralized state** - Tab counts and data loaded once

## Support

For questions or issues with the migration, refer to:
- `FRONTEND_REBUILD_PLAN.md` - Original implementation plan
- `/components/ui/` - Design system components
- `/lib/design-tokens.ts` - Design tokens reference
- `/styles/design-system.css` - Custom CSS utilities
