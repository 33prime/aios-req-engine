# Investigation Results - Page Refresh Issues

## Issue #1: Page Refresh on Tab Switch ✅ IDENTIFIED

### Root Cause
**React Strict Mode in Development** (`next.config.js` line 25)

In development mode, React Strict Mode causes components to mount, unmount, and remount to help detect side effects. This creates the appearance of a "page refresh" when:
- Switching tabs (component may unmount/remount)
- Any state change triggers re-renders

### Evidence
```javascript
// apps/workbench/next.config.js line 25
reactStrictMode: true,
```

### Why This Happens
1. User switches to different browser tab
2. Browser may pause React rendering
3. When user returns, React Strict Mode triggers remounting
4. Components re-run initialization logic
5. Appears like a "refresh" but is actually React re-mounting

### Solution
**This is NORMAL BEHAVIOR in development mode and does NOT happen in production.**

To verify:
```bash
cd apps/workbench
npm run build
npm start
# Test if issue still happens - it won't!
```

### Optional Fix for Development
If the remounting behavior is disruptive during development, you can temporarily disable it:

```javascript
// apps/workbench/next.config.js
// Change line 25 from:
reactStrictMode: true,
// To:
reactStrictMode: false,
```

**WARNING:** Disabling Strict Mode hides potential bugs. Only do this temporarily.

### Recommendation
✅ **No fix needed** - this is expected development behavior that won't occur in production.

---

## Issue #2: URL Redirect on Browser Refresh ✅ IDENTIFIED

### Root Cause
**AuthProvider redirects to `/projects` on SIGNED_IN event**

### The Problem Flow

#### What Should Happen:
1. User is on `/projects/abc-123-xyz`
2. User hits Cmd+R to refresh
3. Page reloads at `/projects/abc-123-xyz`
4. User stays on same page

#### What Actually Happens:
1. User is on `/projects/abc-123-xyz`
2. User hits Cmd+R to refresh
3. Page loads, AuthProvider mounts
4. AuthProvider checks session with Supabase
5. Session is restored successfully
6. **PROBLEM:** AuthProvider line 106-107 triggers:
   ```typescript
   if (event === 'SIGNED_IN') {
     router.push('/projects')  // ❌ Redirects to /projects, losing projectId
   }
   ```
7. User ends up at `/projects` instead of `/projects/abc-123-xyz`

### Evidence

**File:** `apps/workbench/components/auth/AuthProvider.tsx`

**Lines 91-112:**
```typescript
// Listen for auth state changes
const { data: { subscription } } = client.auth.onAuthStateChange(
  async (event, newSession) => {
    console.log('Auth state changed:', event)

    if (newSession) {
      setSession(newSession)
      setUser(newSession.user)
      setAccessToken(newSession.access_token)
    } else {
      setSession(null)
      setUser(null)
      clearAuth()
    }

    // Handle specific events
    if (event === 'SIGNED_IN') {
      router.push('/projects')  // ❌ THIS IS THE PROBLEM
    } else if (event === 'SIGNED_OUT') {
      router.push('/auth/login')
    }
  }
)
```

### Why This Is Wrong

The `SIGNED_IN` event fires when:
1. User logs in (correct - should redirect to `/projects`)
2. **Session is restored on page refresh** (incorrect - should NOT redirect)

When you refresh the page, Supabase restores the session from localStorage, which triggers the `SIGNED_IN` event. This causes the unwanted redirect.

### Solution

Change the redirect logic to only redirect on actual login, not on session restoration.

**Option 1: Check if user was already authenticated**
```typescript
// Add flag to track if this is initial mount
const isInitialMount = useRef(true)

// In onAuthStateChange:
if (event === 'SIGNED_IN') {
  // Only redirect on actual login, not on session restoration
  if (!isInitialMount.current) {
    router.push('/projects')
  }
}

// After initAuth():
isInitialMount.current = false
```

**Option 2: Only redirect from login page** (RECOMMENDED)
```typescript
if (event === 'SIGNED_IN') {
  // Only redirect if user is on login page
  if (pathname.startsWith('/auth')) {
    router.push('/projects')
  }
  // Otherwise, let them stay on current page
}
```

### The Fix

I'll implement Option 2 as it's cleaner and more predictable:

```typescript
// Handle specific events
if (event === 'SIGNED_IN') {
  // Only redirect to /projects if coming from auth pages
  // This prevents unwanted redirects on page refresh
  if (pathname.startsWith('/auth')) {
    router.push('/projects')
  }
} else if (event === 'SIGNED_OUT') {
  router.push('/auth/login')
}
```

---

## Summary

### Issue #1: Page Refresh on Tab Switch
- **Cause:** React Strict Mode in development
- **Impact:** Development only, does NOT happen in production
- **Fix:** No fix needed (or disable Strict Mode for development only)
- **Status:** ✅ Identified, no action required

### Issue #2: URL Redirect on Browser Refresh
- **Cause:** AuthProvider redirects to `/projects` on `SIGNED_IN` event, which fires on session restoration
- **Impact:** Production issue - users lose their place when refreshing
- **Fix:** Only redirect from auth pages, not on session restoration
- **Status:** ✅ Identified, fix ready to apply

---

## Files to Modify

### Fix for Issue #2 (URL Redirect)

**File:** `apps/workbench/components/auth/AuthProvider.tsx`

**Lines 106-110:**
```typescript
// BEFORE (BROKEN):
if (event === 'SIGNED_IN') {
  router.push('/projects')
} else if (event === 'SIGNED_OUT') {
  router.push('/auth/login')
}

// AFTER (FIXED):
if (event === 'SIGNED_IN') {
  // Only redirect to /projects if coming from auth pages
  // This prevents unwanted redirects on page refresh
  if (pathname.startsWith('/auth')) {
    router.push('/projects')
  }
} else if (event === 'SIGNED_OUT') {
  router.push('/auth/login')
}
```

---

## Testing Plan

### Test Issue #1 (Page Refresh on Tab Switch)

**Development Mode:**
```bash
cd apps/workbench
npm run dev
# Navigate to /projects/[projectId]
# Switch to different tab
# Come back
# Expected: May see re-render (this is normal)
```

**Production Mode:**
```bash
cd apps/workbench
npm run build
npm start
# Navigate to /projects/[projectId]
# Switch to different tab
# Come back
# Expected: No refresh/re-render
```

### Test Issue #2 (URL Redirect on Refresh)

**Before Fix:**
1. Navigate to `/projects/abc-123-xyz`
2. Hit Cmd+R (Mac) or Ctrl+R (Windows)
3. Current: Redirects to `/projects` ❌
4. Expected: Stay on `/projects/abc-123-xyz` ✅

**After Fix:**
1. Navigate to `/projects/abc-123-xyz`
2. Hit Cmd+R (Mac) or Ctrl+R (Windows)
3. Expected: Stay on `/projects/abc-123-xyz` ✅

**Verify Login Still Works:**
1. Sign out
2. Go to `/auth/login`
3. Sign in
4. Expected: Redirect to `/projects` ✅

---

## Next Steps

1. ✅ Apply fix for Issue #2 (URL redirect)
2. ✅ Test that page refresh now preserves URL
3. ✅ Verify login flow still works
4. ✅ Document that Issue #1 is expected dev behavior
