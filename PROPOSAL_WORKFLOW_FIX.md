# Proposal Workflow Fix ✅

## Problem

User uploaded a transcript and got this message:
- "18 changes generated for review (ID: 347747cd-b162-4054-a17a-6b67b15903b6)"
- "Check the Overview tab to preview and apply changes"

But:
1. ❌ No proposal visible anywhere in the UI
2. ❌ No way to review or apply the changes
3. ❌ Features/personas didn't auto-update (because proposal wasn't applied)

## Root Cause

### Issue #1: Proposals Not Displayed
- The `ProposalPreview` component existed but wasn't being used anywhere
- The `listProposals` API function existed but wasn't being called
- Next Steps tab only showed confirmations, not proposals
- **Result:** Proposals created by signal processing had nowhere to be displayed

### Issue #2: Polling Looked for Wrong Signal
- My previous polling fix looked for `total_impacts > 0`
- But **heavyweight signals create proposals**, not direct impacts
- Proposals don't create impacts until APPLIED
- **Result:** Polling never detected completion for heavyweight signals

## The Fix

### 1. Added Proposal Display to Next Steps Tab

**File:** `apps/workbench/app/projects/[projectId]/components/tabs/NextStepsTab.tsx`

**Changes:**
1. Added imports for proposal functions and ProposalPreview component
2. Added state for proposals and apply/discard handlers
3. Load pending proposals in `loadData()`
4. Display proposals at the top of the tab with apply/discard buttons
5. Reload page after applying to show new entities

**Key Code:**
```typescript
// Load proposals
const [proposalsData] = await Promise.all([
  listProposals(projectId, 'pending')
])

// Handler to apply proposal
const handleApplyProposal = async (proposalId: string) => {
  await applyProposal(proposalId)
  await loadData()
  window.location.reload() // Refresh to show new entities
}

// Display proposals
{proposals.length > 0 && (
  <div className="pending-proposals-section">
    {proposals.map((proposal) => (
      <ProposalPreview
        proposal={proposal}
        onApply={handleApplyProposal}
        onDiscard={handleDiscardProposal}
      />
    ))}
  </div>
)}
```

### 2. Fixed Polling to Detect Proposals

**File:** `apps/workbench/app/projects/[projectId]/page.tsx`

**Changes:**
1. Check signal for `batch_proposal_id` or `proposal_id`
2. Check impact for auto-applied entities
3. Processing complete if EITHER proposal OR impacts exist
4. Log appropriate message based on what was created

**Key Code:**
```typescript
// Check for proposal creation (heavyweight signals)
const hasProposal = signal.batch_proposal_id || signal.proposal_id

// Check for direct impacts (lightweight or auto-applied)
const totalImpacts = impact.total_impacts || 0

// Complete if we have either
if (hasProposal || totalImpacts > 0) {
  if (hasProposal) {
    console.log('📋 Proposal created for review')
    console.log('Navigate to Next Steps tab to review and apply')
  }
  loadProjectData() // Refresh to load proposals
}
```

## How It Works Now

### User Workflow:
1. User uploads transcript via AI assistant
2. AI processes signal → creates proposal (18 changes)
3. **NEW:** Polling detects proposal creation
4. **NEW:** Logs "Navigate to Next Steps tab"
5. User clicks "Next Steps" tab
6. **NEW:** Sees "Pending Proposals" section with proposal card
7. User clicks "Apply" button
8. Proposal applied → creates all 18 entities
9. Page reloads → shows new features/personas/value path items!

### What Gets Displayed:
```
Next Steps Tab
├── Pending Proposals (1)
│   └── CHP follow-up transcript
│       - 18 changes (12 creates, 6 updates, 0 deletes)
│       - [Apply] [Discard] buttons
│       - Expandable change details
├── Client Portal Section
├── Discovery Prep Section
└── Confirmations (if any)
```

## Testing

### Test Proposal Workflow:
1. Upload a transcript via AI assistant
2. Wait for processing (1-2 minutes)
3. Watch console logs:
   - "📥 Signal added - polling for completion"
   - "📋 Signal processing complete! Proposal created for review"
   - "Navigate to Next Steps tab to review and apply changes"
4. Click "Next Steps" tab
5. See "Pending Proposals" section with proposal card
6. Click "Apply" button
7. Page reloads
8. Check Features/Personas/Value Path tabs - should see new items!

### Expected Console Output:
```
📥 Signal added - polling for completion: abc-123-xyz
📋 Signal processing complete! Proposal created for review
Navigate to Next Steps tab to review and apply changes
```

## Files Modified

### Frontend
- `apps/workbench/app/projects/[projectId]/components/tabs/NextStepsTab.tsx`
  - Added proposal state and loading
  - Added apply/discard handlers
  - Added ProposalPreview display

- `apps/workbench/app/projects/[projectId]/page.tsx`
  - Updated `pollSignalStatus()` to detect proposals
  - Added logging for proposal creation

## Proposal Workflow Types

### Heavyweight Signals (Your Case)
- Complex transcripts with many entities
- Creates **proposal** for review
- User must manually apply
- **Flow:** Signal → Proposal → Apply → Entities Created

### Lightweight Signals
- Simple, high-confidence updates
- Creates entities **directly** (auto-applied)
- No proposal needed
- **Flow:** Signal → Entities Created

### How Polling Handles Both
```typescript
// Check both possibilities
const hasProposal = signal.batch_proposal_id
const hasImpacts = totalImpacts > 0

// Complete if EITHER exists
if (hasProposal || hasImpacts) {
  // Log appropriate message
  // Refresh data
}
```

## Why Page Reload After Apply?

When you apply a proposal:
1. Backend creates all entities (features, personas, etc.)
2. Database updates with new data
3. Frontend state is stale (doesn't have new entities)
4. `window.location.reload()` forces full refresh
5. All tabs reload with new data

**Alternative:** Could refresh all tab data without full reload, but reload is simpler and guarantees consistency.

## Comparison: Before vs After

### Before Fix
❌ Proposal created but nowhere to see it
❌ No way to apply changes
❌ Features/personas never update
❌ User confused and stuck

### After Fix
✅ Proposal visible in Next Steps tab
✅ Apply/Discard buttons work
✅ Polling detects proposal creation
✅ Clear workflow to apply changes
✅ Features/personas update after apply
✅ Page automatically refreshes

## Related Components

### ProposalPreview Component
- Shows proposal summary (creates/updates/deletes)
- Expandable change cards
- Evidence badges
- Before/after diffs
- Apply/Discard actions

### Proposal API Functions (lib/api.ts)
- `listProposals(projectId, status)` - Get proposals
- `applyProposal(proposalId)` - Apply all changes
- `discardProposal(proposalId)` - Reject proposal

## Future Enhancements

### Optional Improvements:
1. **Real-time notifications** - Show toast when proposal is ready
2. **Proposal preview in chat** - Show summary in AI assistant
3. **Incremental apply** - Apply individual changes, not all-or-nothing
4. **Proposal diff viewer** - Better before/after comparison
5. **Undo applied proposal** - Rollback if needed

---

## Summary

Fixed the complete proposal workflow:
1. ✅ Proposals now visible in Next Steps tab
2. ✅ Apply/Discard buttons work correctly
3. ✅ Polling detects proposal creation
4. ✅ Clear user guidance to Next Steps tab
5. ✅ Features/personas/value path update after apply

**The user can now see and apply the 18 changes from their transcript!**
