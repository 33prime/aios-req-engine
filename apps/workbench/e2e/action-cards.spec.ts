import { test, expect, type Page } from '@playwright/test'
import path from 'path'

const authFile = path.join(__dirname, '.auth/user.json')

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function goToBRD(page: Page, projectId: string) {
  await page.goto(`/projects/${projectId}`)
  await page
    .getByText('Loading workspace...')
    .waitFor({ state: 'hidden', timeout: 45000 })
    .catch(() => {})
  await page
    .getByRole('button', { name: /Discovery/i })
    .waitFor({ state: 'visible', timeout: 30000 })
  await page.getByRole('button', { name: /Discovery/i }).click()
  const brdViewBtn = page.getByRole('button', { name: 'BRD View' })
  await brdViewBtn.waitFor({ state: 'visible', timeout: 15000 })
  await brdViewBtn.click()
  await page
    .getByText('Loading BRD...')
    .waitFor({ state: 'hidden', timeout: 30000 })
    .catch(() => {})
  await page.waitForSelector('text=Business Requirements Document', {
    timeout: 30000,
  })
}

async function goToOverview(page: Page, projectId: string) {
  await page.goto(`/projects/${projectId}`)
  await page
    .getByText('Loading workspace...')
    .waitFor({ state: 'hidden', timeout: 45000 })
    .catch(() => {})
  await page
    .getByRole('button', { name: /Overview/i })
    .waitFor({ state: 'visible', timeout: 30000 })
  await page.getByRole('button', { name: /Overview/i }).click()
  // Wait for overview content to appear (Project Pulse card is always present)
  await page.waitForSelector('text=Project Pulse', { timeout: 30000 })
}

// ---------------------------------------------------------------------------
// Suite 1: BRD NextActionsBar
// ---------------------------------------------------------------------------

test.describe('Action Cards — BRD NextActionsBar', () => {
  test.skip(!process.env.TEST_USER_EMAIL, 'Requires TEST_USER_EMAIL env var')
  test.skip(!process.env.TEST_PROJECT_ID, 'Requires TEST_PROJECT_ID env var')

  test.setTimeout(60000)
  test.use({ storageState: authFile })

  const projectId = process.env.TEST_PROJECT_ID!

  test.beforeEach(async ({ page }) => {
    await goToBRD(page, projectId)
  })

  test('renders NextActionsBar with header and at least one action', async ({
    page,
  }) => {
    // Wait for the actions bar to load (may show "Computing recommended actions..." first)
    await page
      .getByText('Computing recommended actions...')
      .waitFor({ state: 'hidden', timeout: 15000 })
      .catch(() => {})

    const header = page.getByText('Next Best Actions')
    await expect(header.first()).toBeVisible({ timeout: 10000 })

    // At least one numbered action badge (the "1" badge)
    const firstBadge = page.locator(
      '.rounded-full:has-text("1")'
    )
    await expect(firstBadge.first()).toBeVisible()

    // At least one CTA button in the bar
    const validLabels = ['Confirm All', 'Open', 'Go to Section', 'Ask AI']
    let foundCta = false
    for (const label of validLabels) {
      const btn = page.getByRole('button', { name: label })
      if (await btn.first().isVisible().catch(() => false)) {
        foundCta = true
        break
      }
    }
    expect(foundCta).toBe(true)
  })

  test('CTA buttons show valid labels', async ({ page }) => {
    await page
      .getByText('Computing recommended actions...')
      .waitFor({ state: 'hidden', timeout: 15000 })
      .catch(() => {})

    // Gather all CTA button labels inside the actions bar area
    const validLabels = ['Confirm All', 'Open', 'Go to Section', 'Ask AI']
    const ctaButtons = page.locator(
      'button:has-text("Confirm All"), button:has-text("Open"), button:has-text("Go to Section"), button:has-text("Ask AI")'
    )
    const count = await ctaButtons.count()

    // Every visible CTA should be one of the valid labels
    for (let i = 0; i < count; i++) {
      const text = await ctaButtons.nth(i).innerText()
      const matched = validLabels.some((label) => text.includes(label))
      expect(matched).toBe(true)
    }
  })

  test('navigate action scrolls to BRD section', async ({ page }) => {
    await page
      .getByText('Computing recommended actions...')
      .waitFor({ state: 'hidden', timeout: 15000 })
      .catch(() => {})

    const goToBtn = page.getByRole('button', { name: 'Go to Section' }).first()
    if (await goToBtn.isVisible().catch(() => false)) {
      await goToBtn.click()
      // Verify some brd-section-* element is in the viewport after scroll
      const section = page.locator('[id^="brd-section-"]').first()
      await expect(section).toBeInViewport({ timeout: 5000 })
    } else {
      // No navigate actions available — skip gracefully
      test.skip()
    }
  })

  test('drawer action opens panel', async ({ page }) => {
    await page
      .getByText('Computing recommended actions...')
      .waitFor({ state: 'hidden', timeout: 15000 })
      .catch(() => {})

    const openBtn = page.getByRole('button', { name: 'Open' }).first()
    if (await openBtn.isVisible().catch(() => false)) {
      await openBtn.click()
      // A dialog or drawer should appear
      const dialog = page.locator('[role="dialog"]')
      await expect(dialog.first()).toBeVisible({ timeout: 5000 })
    } else {
      test.skip()
    }
  })

  test('inline action does not cause page error', async ({ page }) => {
    await page
      .getByText('Computing recommended actions...')
      .waitFor({ state: 'hidden', timeout: 15000 })
      .catch(() => {})

    const confirmBtn = page
      .getByRole('button', { name: 'Confirm All' })
      .first()
    if (await confirmBtn.isVisible().catch(() => false)) {
      // Listen for console errors
      const errors: string[] = []
      page.on('pageerror', (err) => errors.push(err.message))

      await confirmBtn.click()
      await page.waitForTimeout(2000)

      // BRD title should still be present (page didn't crash)
      await expect(
        page.getByText('Business Requirements Document')
      ).toBeVisible()
      expect(errors.length).toBe(0)
    } else {
      test.skip()
    }
  })
})

// ---------------------------------------------------------------------------
// Suite 2: Overview Panel Actions
// ---------------------------------------------------------------------------

test.describe('Action Cards — Overview Panel', () => {
  test.skip(!process.env.TEST_USER_EMAIL, 'Requires TEST_USER_EMAIL env var')
  test.skip(!process.env.TEST_PROJECT_ID, 'Requires TEST_PROJECT_ID env var')

  test.setTimeout(60000)
  test.use({ storageState: authFile })

  const projectId = process.env.TEST_PROJECT_ID!

  test.beforeEach(async ({ page }) => {
    await goToOverview(page, projectId)
  })

  test('hero action banner renders with title and green CTA', async ({
    page,
  }) => {
    // The hero banner is the top card with the "1" badge and green CTA button
    // It either shows an action or the "Your BRD is looking great!" fallback
    const heroBanner = page
      .locator('.border-l-4')
      .first()
    const fallback = page.getByText('Your BRD is looking great!')

    const hasHero = await heroBanner.isVisible().catch(() => false)
    const hasFallback = await fallback.isVisible().catch(() => false)

    // One of the two states must be present
    expect(hasHero || hasFallback).toBe(true)

    if (hasHero) {
      // Hero has a green CTA button
      const ctaBtn = heroBanner.locator('button')
      await expect(ctaBtn).toBeVisible()
    }
  })

  test('hero CTA navigates to discovery', async ({ page }) => {
    const heroBanner = page.locator('.border-l-4').first()
    if (!(await heroBanner.isVisible().catch(() => false))) {
      test.skip()
      return
    }

    const ctaBtn = heroBanner.locator('button')
    await ctaBtn.click()

    // Should switch to Discovery phase — BRD or Canvas view appears
    await expect(
      page.getByText('Business Requirements Document')
    ).toBeVisible({ timeout: 30000 })
  })

  test('Next Actions card renders in overview grid', async ({ page }) => {
    // The overview grid has a "Next Best Actions" card
    const actionsCard = page.getByText('Next Best Actions')
    await expect(actionsCard.first()).toBeVisible({ timeout: 10000 })
  })

  test('action item click navigates to BRD', async ({ page }) => {
    // Find clickable action items in the overview Next Actions card
    // These are full-width buttons with action titles
    const actionButtons = page.locator(
      'button.w-full.rounded-xl'
    )
    const count = await actionButtons.count()

    if (count === 0) {
      test.skip()
      return
    }

    // Click the first action item
    await actionButtons.first().click()

    // Should navigate to BRD view
    await expect(
      page.getByText('Business Requirements Document')
    ).toBeVisible({ timeout: 30000 })
  })
})

// ---------------------------------------------------------------------------
// Suite 3: Cross-View Execution
// ---------------------------------------------------------------------------

test.describe('Action Cards — Cross-View Execution', () => {
  test.skip(!process.env.TEST_USER_EMAIL, 'Requires TEST_USER_EMAIL env var')
  test.skip(!process.env.TEST_PROJECT_ID, 'Requires TEST_PROJECT_ID env var')

  test.setTimeout(60000)
  test.use({ storageState: authFile })

  const projectId = process.env.TEST_PROJECT_ID!

  test('overview action navigates to BRD and scrolls to section', async ({
    page,
  }) => {
    await goToOverview(page, projectId)

    // Find a clickable action in the overview (hero CTA or grid item)
    const heroBanner = page.locator('.border-l-4').first()
    const hasHero = await heroBanner.isVisible().catch(() => false)

    if (hasHero) {
      const ctaBtn = heroBanner.locator('button')
      await ctaBtn.click()
    } else {
      // Try grid action buttons
      const actionButtons = page.locator('button.w-full.rounded-xl')
      if ((await actionButtons.count()) === 0) {
        test.skip()
        return
      }
      await actionButtons.first().click()
    }

    // Should land on BRD
    await expect(
      page.getByText('Business Requirements Document')
    ).toBeVisible({ timeout: 30000 })

    // Wait for potential scroll animation
    await page.waitForTimeout(1500)

    // At least one BRD section should be visible on the page
    const sections = page.locator('[id^="brd-section-"]')
    const sectionCount = await sections.count()
    expect(sectionCount).toBeGreaterThan(0)
  })
})
