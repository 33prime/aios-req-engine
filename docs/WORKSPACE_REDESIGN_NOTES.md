# Workspace Redesign Implementation Notes

## Date: 2026-01-29

## Summary

Implemented a new canvas-based workspace UI that can be accessed at `/projects/{projectId}/workspace`.

## New Files Created

### Backend (Python)
- `app/api/workspace.py` - New API endpoint for canvas UI
- `migrations/0092_workspace_redesign.sql` - Schema changes for workspace features

### Frontend (TypeScript/React)
- `apps/workbench/components/workspace/AppSidebar.tsx` - Fixed left navigation bar
- `apps/workbench/components/workspace/PhaseSwitcher.tsx` - Discovery/Build/Live phase toggle
- `apps/workbench/components/workspace/CollaborationPanel.tsx` - Right panel with chat/portal/activity
- `apps/workbench/components/workspace/WorkspaceLayout.tsx` - Main layout orchestrator
- `apps/workbench/components/workspace/BuildPhaseView.tsx` - Prototype embed view
- `apps/workbench/components/workspace/canvas/RequirementsCanvas.tsx` - Main canvas component
- `apps/workbench/components/workspace/canvas/StoryEditor.tsx` - Editable pitch line
- `apps/workbench/components/workspace/canvas/PersonaRow.tsx` - Horizontal persona display
- `apps/workbench/components/workspace/canvas/JourneyFlow.tsx` - Value path visualization
- `apps/workbench/components/workspace/canvas/JourneyStep.tsx` - Individual journey step (droppable)
- `apps/workbench/components/workspace/canvas/FeatureChip.tsx` - Draggable feature badge
- `apps/workbench/components/workspace/canvas/UnmappedFeatures.tsx` - Pool for unassigned features
- `apps/workbench/components/workspace/canvas/index.ts` - Canvas component exports
- `apps/workbench/components/workspace/index.ts` - Workspace component exports
- `apps/workbench/types/workspace.ts` - TypeScript types for workspace
- `apps/workbench/app/projects/[projectId]/workspace/page.tsx` - New workspace route
- `apps/workbench/app/projects/[projectId]/workspace/layout.tsx` - Workspace layout bypass

### Modified Files
- `apps/workbench/lib/api.ts` - Added workspace API functions
- `apps/workbench/components/LayoutWrapper.tsx` - Bypass app shell for workspace routes
- `apps/workbench/app/projects/[projectId]/components/WorkspaceHeader.tsx` - Added Canvas link
- `app/api/__init__.py` - Registered workspace router

## Database Schema Changes

```sql
-- New columns on projects table
ALTER TABLE projects ADD COLUMN IF NOT EXISTS prototype_url TEXT;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS prototype_updated_at TIMESTAMPTZ;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS pitch_line TEXT;

-- New column on features table
ALTER TABLE features ADD COLUMN IF NOT EXISTS vp_step_id UUID REFERENCES vp_steps(id);
```

## Dependencies Added
- `@dnd-kit/core` - Drag and drop
- `@dnd-kit/sortable` - Sortable functionality
- `@dnd-kit/utilities` - DnD utilities

## Code That Can Be Deprecated Later

Once the new workspace UI is stable and becomes the default, the following can be considered for deprecation:

### Components
- `apps/workbench/components/AppHeader.tsx` - Replaced by AppSidebar
- `apps/workbench/app/projects/[projectId]/components/TabNavigation.tsx` - Replaced by PhaseSwitcher
- `apps/workbench/app/projects/[projectId]/components/WorkspaceHeader.tsx` - Merged into WorkspaceLayout

### Pages
- `apps/workbench/app/projects/[projectId]/page.tsx` - Will be replaced by workspace/page.tsx

### Tabs (can be consolidated into canvas components)
- `apps/workbench/app/projects/[projectId]/components/tabs/OverviewTab.tsx`
- `apps/workbench/app/projects/[projectId]/components/tabs/PersonasFeaturesTab.tsx`
- `apps/workbench/app/projects/[projectId]/components/tabs/ValuePathTab.tsx`

## API Endpoints

### New Endpoints
- `GET /projects/{project_id}/workspace` - Get all workspace data for canvas
- `PATCH /projects/{project_id}/workspace/pitch-line` - Update pitch line
- `PATCH /projects/{project_id}/workspace/prototype-url` - Update prototype URL
- `PATCH /projects/{project_id}/workspace/features/{feature_id}/map-to-step` - Map feature to VP step

## How to Access

1. Navigate to any project in the workbench
2. Click the "Canvas" button in the header (top right)
3. Or navigate directly to `/projects/{projectId}/workspace`

## Design System Used

- Sidebar background: `#F8F9FB`
- Primary color: `#009b87`
- Active states: emerald-50/emerald tints
- Font: Inter (system default)
- Border radius: rounded-lg (8px)
- Transitions: 200ms duration

## Next Steps

1. Add chat integration to CollaborationPanel
2. Implement Live phase view
3. Add activity feed to CollaborationPanel
4. Make workspace the default route
5. Clean up deprecated components
