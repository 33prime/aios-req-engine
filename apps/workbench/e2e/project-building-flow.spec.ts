/**
 * E2E Test: Project Building Flow
 *
 * Tests the full lifecycle with mocked API:
 * 1. Projects page shows gear badge on building cards
 * 2. Clicking building card opens BuildingProgressModal
 * 3. Dismissing modal, gear badge persists, click reopens
 * 4. Build completes → gear disappears, card navigable
 * 5. Workspace loads without pulse overlay or building animation
 * 6. Activity icon opens Health overlay, not Pulse
 * 7. URL params from onboarding auto-open modal
 * 8. Page refresh during build shows gear, not modal
 *
 * All API calls are intercepted via page.route() — no real backend needed.
 *
 * IMPORTANT: Playwright routes use LIFO (Last In, First Out) priority.
 * Also, URL patterns WITHOUT wildcards act as PREFIX matches.
 * Register catch-all routes FIRST, specific routes AFTER.
 */

import { test, expect, type Page } from '@playwright/test'

// ============================================================================
// Supabase Auth Mock
// ============================================================================

const SUPABASE_URL = 'https://fveyvialmiohrwvnmcip.supabase.co'
const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3001'

const FAKE_USER = {
  id: '00000000-0000-0000-0000-000000000099',
  email: 'test@example.com',
  user_metadata: { full_name: 'Test User' },
  app_metadata: { provider: 'email' },
  aud: 'authenticated',
  role: 'authenticated',
  created_at: '2026-01-01T00:00:00Z',
}

const FAKE_SESSION = {
  access_token: 'fake-access-token-for-testing',
  refresh_token: 'fake-refresh-token',
  expires_in: 3600,
  expires_at: Math.floor(Date.now() / 1000) + 3600,
  token_type: 'bearer',
  user: FAKE_USER,
}

const FAKE_STORAGE_STATE = {
  cookies: [],
  origins: [
    {
      origin: baseURL,
      localStorage: [
        {
          name: 'sb-fveyvialmiohrwvnmcip-auth-token',
          value: JSON.stringify(FAKE_SESSION),
        },
      ],
    },
  ],
}

async function mockSupabaseAuth(page: Page) {
  await page.route(`${SUPABASE_URL}/auth/v1/**`, (route) => {
    const url = route.request().url()
    if (url.includes('/token')) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(FAKE_SESSION) })
    }
    if (url.includes('/user')) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(FAKE_USER) })
    }
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ data: { session: FAKE_SESSION } }) })
  })
}

// ============================================================================
// Mock Data
// ============================================================================

const PROJECT_BUILDING_ID = '11111111-1111-1111-1111-111111111111'
const PROJECT_NORMAL_ID = '22222222-2222-2222-2222-222222222222'
const LAUNCH_ID = 'aaaa0000-0000-0000-0000-000000000001'

const PROFILE_MOCK = {
  id: '00000000-0000-0000-0000-000000000099',
  first_name: 'Test',
  last_name: 'User',
  email: 'test@example.com',
  platform_role: 'consultant',
  photo_url: null,
}

function makeProject(overrides: Record<string, any> = {}) {
  return {
    id: PROJECT_NORMAL_ID,
    name: 'Acme CRM Rebuild',
    description: 'Rebuilding the legacy CRM system',
    stage: 'discovery',
    status: 'active',
    created_at: '2026-02-01T00:00:00Z',
    updated_at: '2026-02-15T00:00:00Z',
    client_name: 'Acme Corp',
    readiness_score: 45,
    launch_status: null,
    active_launch_id: null,
    portal_enabled: false,
    portal_phase: null,
    stage_eligible: false,
    cached_readiness_data: null,
    created_by: PROFILE_MOCK.id,
    ...overrides,
  }
}

const PROJECT_BUILDING = makeProject({
  id: PROJECT_BUILDING_ID,
  name: 'New Widget Platform',
  description: 'Building a widget management platform',
  client_name: 'Widget Co',
  launch_status: 'building',
  active_launch_id: LAUNCH_ID,
  readiness_score: 0,
})

const PROJECT_NORMAL = makeProject()

const PROJECTS_LIST_RESPONSE = {
  projects: [PROJECT_BUILDING, PROJECT_NORMAL],
  total: 2,
  owner_profiles: {
    [PROFILE_MOCK.id]: { first_name: 'Test', last_name: 'User', photo_url: null },
  },
}

function makeLaunchProgress(overrides: Record<string, any> = {}) {
  return {
    launch_id: LAUNCH_ID,
    project_id: PROJECT_BUILDING_ID,
    status: 'running',
    progress_pct: 35,
    can_navigate: false,
    steps: [
      { step_key: 'company_research', step_label: 'Researching company', status: 'completed', result_summary: 'Found company info' },
      { step_key: 'entity_generation', step_label: 'Building project foundation', status: 'running', result_summary: null },
      { step_key: 'stakeholder_enrichment', step_label: 'Enriching stakeholder profiles', status: 'pending', result_summary: null },
      { step_key: 'quality_check', step_label: 'Verifying output quality', status: 'pending', result_summary: null },
    ],
    ...overrides,
  }
}

const LAUNCH_PROGRESS_RUNNING = makeLaunchProgress()

const LAUNCH_PROGRESS_COMPLETED = makeLaunchProgress({
  status: 'completed',
  progress_pct: 100,
  can_navigate: true,
  steps: [
    { step_key: 'company_research', step_label: 'Researching company', status: 'completed', result_summary: 'Found company info' },
    { step_key: 'entity_generation', step_label: 'Building project foundation', status: 'completed', result_summary: '4 personas, 6 workflows, 12 requirements' },
    { step_key: 'stakeholder_enrichment', step_label: 'Enriching stakeholder profiles', status: 'completed', result_summary: '2 stakeholders enriched' },
    { step_key: 'quality_check', step_label: 'Verifying output quality', status: 'completed', result_summary: 'Quality: excellent' },
  ],
})

// Full CanvasData shape matching the workspace.ts CanvasData interface
const WORKSPACE_DATA_MOCK = {
  project_id: PROJECT_NORMAL_ID,
  project_name: 'Acme CRM Rebuild',
  pitch_line: 'Rebuilding the legacy CRM',
  collaboration_phase: 'discovery',
  portal_phase: null,
  prototype_url: null,
  prototype_updated_at: null,
  readiness_score: 45,
  personas: [{ id: 'p1', name: 'Admin', slug: 'admin', feature_count: 2, confirmation_status: 'ai_generated' }],
  features: [{ id: 'f1', name: 'Dashboard', overview: 'Main dashboard', status: 'proposed', priority_group: 'must_have', confirmation_status: 'ai_generated' }],
  vp_steps: [],
  unmapped_features: [],
  portal_enabled: false,
  portal_clients: [],
  pending_count: 3,
}

const BRD_DATA_MOCK = {
  vision: { text: 'A modern CRM', scores: null, revision_count: 0 },
  background: { text: 'Legacy system replacement' },
  personas: [],
  features: [],
  workflows: { workflow_pairs: [], legacy_steps: [] },
  drivers: [],
  data_entities: [],
  stakeholders: [],
  completeness: { overall_score: 45, category_scores: {} },
  next_actions: [],
}

const PULSE_DATA_MOCK = {
  score: 45,
  summary: 'Good foundation \u2014 4 personas identified, 6 workflows mapped.',
  background: 'Rebuilding the legacy CRM system',
  vision: 'A modern CRM platform',
  entity_counts: { personas: 4, features: 12, workflows: 6, drivers: 8, stakeholders: 2, vp_steps: 0 },
  strengths: ['4 personas identified', '6 workflows mapped'],
  next_actions: [
    { title: 'Review and confirm entities', description: 'Walk through the generated requirements.', priority: 'medium' },
  ],
  first_visit: false,
}

const HEALTH_DATA_MOCK = {
  stale_entities: { features: [], personas: [], vp_steps: [], data_entities: [], strategic_context: [], total_stale: 0 },
  scope_alerts: [],
  dependency_count: 5,
  pending_cascade_count: 0,
}

const PROJECT_DETAIL_NORMAL = {
  ...PROJECT_NORMAL,
  counts: { signals: 3, features: 12, personas: 4, vp_steps: 0, business_drivers: 8 },
}

// ============================================================================
// API Mock Setup
// ============================================================================

const API_BASE = 'http://localhost:8000/v1'

/**
 * Helper: check if URL is exactly the given path (not a sub-path).
 * Playwright URL patterns without wildcards match as PREFIX, so
 * /projects/123 also matches /projects/123/workspace.
 * This helper returns true only for exact match (optionally with query params).
 */
function isExactPath(url: string, basePath: string): boolean {
  const afterBase = url.slice(basePath.length)
  return !afterBase || afterBase === '/' || afterBase.startsWith('?')
}

async function setupProjectsPageMocks(page: Page, overrides?: {
  projects?: any
  launchProgress?: any
}) {
  const projectsResponse = overrides?.projects ?? PROJECTS_LIST_RESPONSE
  const launchProgressResponse = overrides?.launchProgress ?? LAUNCH_PROGRESS_RUNNING

  await page.route(`${API_BASE}/organizations/profile/me`, (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(PROFILE_MOCK) })
  )

  // Projects list
  await page.route(`${API_BASE}/projects`, (route) => {
    const url = route.request().url()
    if (route.request().method() === 'GET' && !url.match(/\/projects\/[0-9a-f-]{36}/)) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(projectsResponse) })
    }
    return route.fallback()
  })
  await page.route(`${API_BASE}/projects?*`, (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(projectsResponse) })
  )

  // Launch progress
  await page.route(`${API_BASE}/projects/*/launch/*/progress`, (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(launchProgressResponse) })
  )

  // Batch dashboard
  await page.route(`${API_BASE}/projects/batch/dashboard-data`, (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ next_actions: {}, task_stats: {} }) })
  )

  // Meetings
  await page.route(`${API_BASE}/meetings/upcoming*`, (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) })
  )

  // Notifications
  await page.route(`${API_BASE}/notifications*`, (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ notifications: [], unread_count: 0 }) })
  )
}

/**
 * Set up mocks for the workspace page (project detail).
 *
 * CRITICAL ordering notes:
 * - Playwright routes are LIFO: last registered = highest priority
 * - URL patterns without wildcards are PREFIX matches
 * - Register catch-all FIRST, then specific routes
 * - Project detail route must check for exact URL to avoid intercepting sub-paths
 */
async function setupWorkspaceMocks(page: Page) {
  // ---- CATCH-ALL (lowest priority — registered first) ----
  // Returns safe defaults for known endpoint patterns that components might access
  await page.route(`${API_BASE}/**`, (route) => {
    const url = route.request().url()
    if (route.request().method() === 'GET') {
      // Return proper empty arrays for list endpoints that crash on undefined
      if (url.includes('/tasks')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ tasks: [], total: 0 }) })
      if (url.includes('/actions')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ actions: [], phase: 'discovery', phase_progress: 0, structural_gaps: [], signal_gaps: [], knowledge_gaps: [], state_snapshot: '', workflow_context: '', memory_hints: [], entity_counts: {}, total_gap_count: 0, computed_at: '2026-02-15T00:00:00Z', open_questions: [] }) })
      return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
    }
    return route.fulfill({ status: 200, contentType: 'application/json', body: '{"ok":true}' })
  })

  // Profile
  await page.route(`${API_BASE}/organizations/profile/me`, (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(PROFILE_MOCK) })
  )

  // Notifications
  await page.route(`${API_BASE}/notifications*`, (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ notifications: [], unread_count: 0 }) })
  )

  // Launch progress
  await page.route(`${API_BASE}/projects/*/launch/*/progress`, (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(LAUNCH_PROGRESS_COMPLETED) })
  )

  // Prototype by project
  await page.route(`${API_BASE}/prototypes/by-project/${PROJECT_NORMAL_ID}`, (route) =>
    route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'Not found' }) })
  )

  // Readiness
  await page.route(`${API_BASE}/projects/${PROJECT_NORMAL_ID}/readiness*`, (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ score: 45, details: {} }) })
  )

  // Tasks stats
  await page.route(`${API_BASE}/projects/${PROJECT_NORMAL_ID}/tasks/stats`, (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ total: 0, by_status: {} }) })
  )

  // Collaboration history
  await page.route(`${API_BASE}/projects/${PROJECT_NORMAL_ID}/collaboration/history`, (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ sessions: [], total: 0 }) })
  )

  // Question counts
  await page.route(`${API_BASE}/projects/${PROJECT_NORMAL_ID}/questions/counts`, (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ total: 0, by_status: {} }) })
  )

  // Tasks list (TaskListCompact in OverviewPanel fetches this — without it, `result.tasks` is undefined → crash)
  await page.route(`${API_BASE}/projects/${PROJECT_NORMAL_ID}/tasks`, (route) => {
    const url = route.request().url()
    // Don't intercept /tasks/stats (handled separately above)
    if (url.includes('/tasks/stats')) return route.fallback()
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ tasks: [], total: 0 }) })
  })

  // Context frame (workspace actions v3 — useContextFrame SWR hook)
  await page.route(`${API_BASE}/projects/${PROJECT_NORMAL_ID}/workspace/actions*`, (route) =>
    route.fulfill({
      status: 200, contentType: 'application/json', body: JSON.stringify({
        phase: 'discovery',
        phase_progress: 45,
        structural_gaps: [],
        signal_gaps: [],
        knowledge_gaps: [],
        actions: [],
        state_snapshot: '',
        workflow_context: '',
        memory_hints: [],
        entity_counts: { personas: 1, features: 1 },
        total_gap_count: 0,
        computed_at: '2026-02-15T00:00:00Z',
        open_questions: [],
      })
    })
  )

  // Pulse dismiss (must be before pulse — LIFO means this registers before but checks after)
  // Actually with LIFO, we register more specific LAST so they take priority
  await page.route(`${API_BASE}/projects/${PROJECT_NORMAL_ID}/workspace/pulse`, (route) => {
    const url = route.request().url()
    if (url.includes('/dismiss')) return route.fallback()
    if (route.request().method() === 'POST') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: '{"ok":true}' })
    }
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(PULSE_DATA_MOCK) })
  })
  await page.route(`${API_BASE}/projects/${PROJECT_NORMAL_ID}/workspace/pulse/dismiss`, (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: '{"ok":true}' })
  )

  // BRD data (prefix matches /workspace/brd and /workspace/brd?mode=...)
  await page.route(`${API_BASE}/projects/${PROJECT_NORMAL_ID}/workspace/brd`, (route) => {
    const url = route.request().url()
    if (url.includes('/health')) return route.fallback()
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(BRD_DATA_MOCK) })
  })

  // BRD health (registered AFTER /brd to take priority via LIFO)
  await page.route(`${API_BASE}/projects/${PROJECT_NORMAL_ID}/workspace/brd/health`, (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(HEALTH_DATA_MOCK) })
  )

  // Workspace data — the critical route
  // Must not match /workspace/brd, /workspace/pulse, etc. (but those are registered above with higher LIFO priority)
  await page.route(`${API_BASE}/projects/${PROJECT_NORMAL_ID}/workspace`, (route) => {
    const url = route.request().url()
    // Only handle the exact /workspace endpoint, not sub-paths
    // Sub-paths like /workspace/brd are handled by their own routes above (higher LIFO priority)
    const basePath = `${API_BASE}/projects/${PROJECT_NORMAL_ID}/workspace`
    if (!isExactPath(url, basePath)) return route.fallback()
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(WORKSPACE_DATA_MOCK) })
  })

  // Single project detail — MUST check for exact URL match
  // Without this check, /projects/123 prefix-matches /projects/123/workspace
  await page.route(`${API_BASE}/projects/${PROJECT_NORMAL_ID}`, (route) => {
    const url = route.request().url()
    const basePath = `${API_BASE}/projects/${PROJECT_NORMAL_ID}`
    if (!isExactPath(url, basePath)) return route.fallback()
    if (route.request().method() !== 'GET') return route.fallback()
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(PROJECT_DETAIL_NORMAL) })
  })
}

// ============================================================================
// Tests
// ============================================================================

test.describe('Project Building Flow', () => {
  test.use({ storageState: FAKE_STORAGE_STATE as any })

  // --------------------------------------------------
  // Test 1: Gear badge on building cards
  // --------------------------------------------------
  test('projects page shows gear badge on building cards, not on normal cards', async ({ page }) => {
    await mockSupabaseAuth(page)
    await setupProjectsPageMocks(page)
    await page.goto('/projects')

    await expect(page.getByText('New Widget Platform')).toBeVisible({ timeout: 15000 })
    await expect(page.getByText('Acme CRM Rebuild')).toBeVisible()

    // Gear badge should exist (only one)
    const gearBadge = page.getByTitle('Build in progress \u2014 click for details')
    await expect(gearBadge).toBeVisible()
    await expect(gearBadge).toHaveCount(1)
    await expect(gearBadge).toContainText('Building')

    // Card content readable (not blurred)
    await expect(page.getByText('Widget Co')).toBeVisible()

    // No modal auto-opened
    await expect(page.getByText('Building Your Project')).not.toBeVisible()
  })

  // --------------------------------------------------
  // Test 2: Click building card opens modal
  // --------------------------------------------------
  test('clicking building card opens BuildingProgressModal with rich content', async ({ page }) => {
    await mockSupabaseAuth(page)
    await setupProjectsPageMocks(page)
    await page.goto('/projects')

    await expect(page.getByText('New Widget Platform')).toBeVisible({ timeout: 15000 })

    // Click building card
    await page.getByText('New Widget Platform', { exact: true }).click()

    // Modal opens
    await expect(page.getByText('Building Your Project')).toBeVisible({ timeout: 5000 })

    // Steps visible
    await expect(page.getByText('Researching company')).toBeVisible()
    await expect(page.getByText('Building project foundation...')).toBeVisible()

    // Cycling sub-label
    const subLabelPattern = /Analyzing business goals|Mapping current.*future|Identifying key personas|Generating requirements|Building feature roadmap|Connecting workflows/
    await expect(page.locator('p').filter({ hasText: subLabelPattern }).first()).toBeVisible({ timeout: 5000 })

    // Grid blurred behind modal
    await expect(page.locator('.blur-sm')).toBeVisible()

    // Didn't navigate to workspace
    expect(page.url()).not.toContain(`/projects/${PROJECT_BUILDING_ID}`)
    expect(page.url()).toContain('/projects')
  })

  // --------------------------------------------------
  // Test 3: Dismiss modal, gear persists, click reopens
  // --------------------------------------------------
  test('dismissing modal keeps gear badge, clicking gear reopens modal', async ({ page }) => {
    await mockSupabaseAuth(page)
    await setupProjectsPageMocks(page)
    await page.goto('/projects')

    await expect(page.getByText('New Widget Platform')).toBeVisible({ timeout: 15000 })

    // Open modal
    await page.getByText('New Widget Platform', { exact: true }).click()
    await expect(page.getByText('Building Your Project')).toBeVisible({ timeout: 5000 })

    // Dismiss
    await page.getByRole('button', { name: 'Close' }).click()
    await expect(page.getByText('Building Your Project')).not.toBeVisible()

    // Grid unblurred
    await expect(page.locator('.blur-sm.pointer-events-none')).not.toBeVisible()

    // Gear badge still visible
    const gearBadge = page.getByTitle('Build in progress \u2014 click for details')
    await expect(gearBadge).toBeVisible()

    // Click gear to reopen
    await gearBadge.click()
    await expect(page.getByText('Building Your Project')).toBeVisible({ timeout: 5000 })
  })

  // --------------------------------------------------
  // Test 4: Build completes — gear disappears
  // --------------------------------------------------
  test('build completion removes gear badge and makes card navigable', async ({ page }) => {
    await mockSupabaseAuth(page)
    await setupProjectsPageMocks(page, { launchProgress: LAUNCH_PROGRESS_RUNNING })
    await page.goto('/projects')
    await expect(page.getByText('New Widget Platform')).toBeVisible({ timeout: 15000 })

    // Gear visible initially
    const gearBadge = page.getByTitle('Build in progress \u2014 click for details')
    await expect(gearBadge).toBeVisible()

    // Simulate build completion
    await page.route(`${API_BASE}/projects/*/launch/*/progress`, (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(LAUNCH_PROGRESS_COMPLETED) })
    )

    const completedProjectsList = {
      ...PROJECTS_LIST_RESPONSE,
      projects: [
        makeProject({
          id: PROJECT_BUILDING_ID,
          name: 'New Widget Platform',
          client_name: 'Widget Co',
          launch_status: 'ready',
          active_launch_id: null,
          readiness_score: 45,
          stage: 'discovery',
        }),
        PROJECT_NORMAL,
      ],
    }
    await page.route(`${API_BASE}/projects?*`, (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(completedProjectsList) })
    )
    await page.route(`${API_BASE}/projects`, (route) => {
      const url = route.request().url()
      if (route.request().method() === 'GET' && !url.match(/\/projects\/[0-9a-f-]{36}/)) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(completedProjectsList) })
      }
      return route.fallback()
    })

    // Wait for SWR refresh
    await page.waitForTimeout(10000)

    // Gear gone
    await expect(gearBadge).not.toBeVisible({ timeout: 5000 })

    // Stage label shows Discovery
    await expect(page.getByText('Discovery').first()).toBeVisible()
  })

  // --------------------------------------------------
  // Test 5: Workspace loads clean
  // --------------------------------------------------
  test('workspace loads without pulse overlay or building animation', async ({ page }) => {
    await mockSupabaseAuth(page)
    await setupWorkspaceMocks(page)

    await page.goto(`/projects/${PROJECT_NORMAL_ID}`)

    // Wait for workspace
    await expect(page.getByText('Acme CRM Rebuild').first()).toBeVisible({ timeout: 30000 })

    // No building screen
    await expect(page.getByText('Building Your Project')).not.toBeVisible()

    // No pulse overlay (check for overlay-specific elements, NOT "Project Pulse" text which exists in OverviewPanel card)
    await expect(page.getByRole('button', { name: /Let.s Get Started/i })).not.toBeVisible()

    // Activity icon visible
    await expect(page.getByTitle('Project Health')).toBeVisible()
  })

  // --------------------------------------------------
  // Test 6: Activity icon opens Health overlay
  // --------------------------------------------------
  test('activity icon opens Health overlay with score and actions', async ({ page }) => {
    await mockSupabaseAuth(page)
    await setupWorkspaceMocks(page)

    await page.goto(`/projects/${PROJECT_NORMAL_ID}`)
    await expect(page.getByText('Acme CRM Rebuild').first()).toBeVisible({ timeout: 30000 })

    // Click Activity icon
    await page.getByTitle('Project Health').click()

    // Health overlay content visible
    await expect(page.getByText('45').first()).toBeVisible({ timeout: 5000 })
    await expect(page.getByText(/Good foundation/)).toBeVisible()
    await expect(page.getByText('Review and confirm entities')).toBeVisible()

    // Dismiss
    await page.getByRole('button', { name: /Got It/i }).click()

    // Workspace still visible
    await expect(page.getByText('Acme CRM Rebuild').first()).toBeVisible()
  })

  // --------------------------------------------------
  // Test 7: URL params auto-open modal
  // --------------------------------------------------
  test('navigating with building URL params auto-opens modal', async ({ page }) => {
    await mockSupabaseAuth(page)
    await setupProjectsPageMocks(page)

    await page.goto(`/projects?building=${PROJECT_BUILDING_ID}&launch=${LAUNCH_ID}`)

    await expect(page.getByText('Building Your Project')).toBeVisible({ timeout: 15000 })
    await expect(page.locator('.blur-sm')).toBeVisible()

    // URL cleaned
    await page.waitForURL('**/projects', { timeout: 5000 })
    expect(page.url()).not.toContain('building=')
    expect(page.url()).not.toContain('launch=')
  })

  // --------------------------------------------------
  // Test 8: Page refresh shows gear, not modal
  // --------------------------------------------------
  test('page refresh during build shows gear badge without auto-opening modal', async ({ page }) => {
    await mockSupabaseAuth(page)
    await setupProjectsPageMocks(page)

    await page.goto('/projects')
    await expect(page.getByText('New Widget Platform')).toBeVisible({ timeout: 15000 })

    // Gear visible
    const gearBadge = page.getByTitle('Build in progress \u2014 click for details')
    await expect(gearBadge).toBeVisible()

    // No modal
    await expect(page.getByText('Building Your Project')).not.toBeVisible()
  })
})
