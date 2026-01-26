# Auto-Update After Signal Processing - FIXED ✅

## Problem
When user uploaded a transcript:
- Backend processed it successfully (23 entities extracted, proposal created)
- But UI didn't update to show new features/personas/value path items
- No notification was shown
- User had to manually refresh the page

## Root Cause
- No polling mechanism to detect when signal processing completes
- No automatic refresh of project data after processing
- Proactive notifications framework was ready but not integrated

## Solution Implemented

### 1. Signal Processing Polling (page.tsx)

Added `pollSignalStatus()` function that:
- Polls `/v1/signals/{signalId}/impact` endpoint every 3 seconds
- Checks if any entities were created/updated (`total_impacts > 0`)
- When complete, logs entity breakdown and calls `loadProjectData()`
- Timeout after 2 minutes (60 polls × 3 seconds)

```typescript
const pollSignalStatus = async (signalId: string) => {
  // Poll every 3 seconds for up to 2 minutes
  // Check signal impact endpoint
  // When total_impacts > 0, processing is complete
  // Call loadProjectData() to refresh UI
}
```

### 2. Automatic Detection (page.tsx)

Added useEffect that watches chat messages:
- Detects when `add_signal` tool completes
- Extracts `signal_id` from tool result
- Starts polling immediately

```typescript
useEffect(() => {
  const lastMessage = messages[messages.length - 1]
  const addSignalTool = lastMessage.toolCalls?.find(
    (tc) => tc.tool_name === 'add_signal' && tc.status === 'complete'
  )

  if (addSignalTool?.result?.signal_id) {
    pollSignalStatus(addSignalTool.result.signal_id)
  }
}, [messages])
```

## How It Works

### User Flow:
1. User pastes transcript into AI assistant
2. ChatPanel calls `sendSignal()` from useChat
3. Signal sent to backend via chat API
4. Backend calls `add_signal` tool
5. Tool completes with `signal_id` in result
6. **NEW:** useEffect detects tool completion
7. **NEW:** Starts polling signal impact
8. Backend processes signal (1-2 minutes)
9. **NEW:** Poll detects entities created (impact > 0)
10. **NEW:** Calls `loadProjectData()` to refresh
11. User sees new features/personas/value path items!

### What Gets Refreshed:
- Features tab
- Personas tab
- Value Path tab
- Business Drivers
- Sources count
- Overview tab
- Next Steps (if proposal created)

## Testing

### Manual Test:
1. Open workbench at `/projects/[projectId]`
2. Open AI assistant
3. Click transcript button
4. Paste a meeting transcript
5. Submit
6. Watch console logs:
   - "📥 Signal added - polling for completion"
   - "✅ Signal processing complete! X entities created/updated"
   - Entity breakdown logged
7. Check tabs - should see new items immediately

### Expected Console Output:
```
📥 Signal added - polling for completion: <uuid>
✅ Signal processing complete! 23 entities created/updated
Entity breakdown: { feature: 12, persona: 5, business_driver: 6 }
```

## Files Modified

### `/Users/matt/aios-req-engine/apps/workbench/app/projects/[projectId]/page.tsx`

**Lines added:**
- `pollSignalStatus()` function (after `pollJobStatus`)
- useEffect to watch for signal completion (after existing useEffect)

**Pattern Used:**
- Same polling pattern as existing `pollJobStatus()` for consistency
- Uses signal impact endpoint (more reliable than checking signal fields)
- Logs helpful messages for debugging

## Related Issues (Still Need Fixing)

### 1. Page Refresh on Tab Switch
**Problem:** Leaving browser tab and coming back causes page to refresh

**Investigation needed:**
- Check for window visibility event listeners
- Look for React Strict Mode in app/layout.tsx
- Check service worker caching
- Test in production build

### 2. URL Redirect on Browser Refresh
**Problem:** Refreshing browser at `/projects/[projectId]` redirects to `/projects`

**Investigation needed:**
- Check Next.js middleware for redirects
- Check app/layout.tsx for auth/redirect logic
- Verify URL is preserved in browser
- Check project loading error handling

## Next Steps

1. **Test the auto-update fix** - upload a transcript and verify UI refreshes
2. **Integrate proactive notifications** (optional) - show "Processing..." and "Complete!" messages
3. **Fix page refresh issue** - investigate visibility events
4. **Fix URL redirect issue** - check middleware and routing

## Architecture Notes

### Why Use Impact Endpoint?
- More reliable than checking signal fields directly
- Signal record might not have `proposal_id` if auto-applied
- Impact tracking is always updated when entities are created
- Gives us entity breakdown for logging

### Why 3 Second Interval?
- Signal processing takes 1-2 minutes
- 3 seconds × 60 = 180 seconds = 3 minutes max
- Balance between responsiveness and API load
- Same pattern as job polling (2 seconds)

### Why Not WebSockets?
- Polling is simpler and already established pattern
- Job polling uses same approach
- Signal processing is infrequent enough that polling is fine
- Can upgrade to WebSockets later if needed
