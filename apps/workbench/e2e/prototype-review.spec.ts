import { test, expect, type Page, type BrowserContext } from '@playwright/test'
import path from 'path'
import {
  seedPrototypeTestData,
  teardownPrototypeTestData,
  getSessionByPrototype,
  getOverlay,
  type SeedResult,
} from './helpers/seed-prototype'

const authFile = path.join(__dirname, '.auth/user.json')

/**
 * Navigate to the prototype page and start a review session.
 * Returns once the "End Review" button is visible (reviewing state).
 */
async function startReviewSession(page: Page, projectId: string) {
  await page.goto(`/projects/${projectId}/prototype`)

  const startBtn = page.getByRole('button', { name: /Start Review Session/i })
  await startBtn.waitFor({ state: 'visible', timeout: 30000 })
  await startBtn.click()

  // Wait for "Session N" header (NOT matching "Start Review Session")
  await expect(page.getByText(/^Session \d+$/)).toBeVisible({ timeout: 15000 })
  await expect(
    page.getByRole('button', { name: /End Review/i })
  ).toBeVisible({ timeout: 10000 })
}

/**
 * From reviewing state, end the review and return the client portal URL.
 */
async function endReviewAndGetClientUrl(page: Page, projectId: string): Promise<string> {
  await page.getByRole('button', { name: /End Review/i }).click()

  await expect(
    page.getByRole('heading', { name: /Review Complete/i })
  ).toBeVisible({ timeout: 15000 })

  const linkInput = page.locator('input[readonly]')
  await expect(linkInput).toBeVisible()
  const url = await linkInput.inputValue()
  expect(url).toContain(`/portal/${projectId}/prototype`)
  expect(url).toContain('token=')
  return url
}

/**
 * Click a button in the portal page via JavaScript.
 *
 * The portal page is nested inside the LayoutWrapper + Portal layout,
 * which causes Playwright's coordinate-based native clicks to not trigger
 * React synthetic event handlers. Using element.click() via JS works.
 */
async function portalClickButton(page: Page, textMatch: string): Promise<boolean> {
  return page.evaluate((match) => {
    const buttons = Array.from(document.querySelectorAll('button'))
    const btn = buttons.find((b) => b.textContent?.includes(match))
    if (btn) {
      btn.click()
      return true
    }
    return false
  }, textMatch)
}

/**
 * Prototype Review Loop E2E Tests
 *
 * Tests the full consultant → client → synthesis flow using seeded DB data.
 * The iframe loads a fake deploy_url (https://example.com/prototype) which
 * will error — we're testing the review flow, not the prototype itself.
 */
test.describe.serial('Prototype Review Loop', () => {
  test.skip(!process.env.TEST_USER_EMAIL, 'Requires TEST_USER_EMAIL env var')
  test.skip(!process.env.TEST_PROJECT_ID, 'Requires TEST_PROJECT_ID env var')

  test.setTimeout(90000)
  test.use({ storageState: authFile })

  const projectId = process.env.TEST_PROJECT_ID!
  let testData: SeedResult

  test.beforeAll(async () => {
    testData = await seedPrototypeTestData(projectId)
  })

  test.afterAll(async () => {
    await teardownPrototypeTestData(testData.prototypeId, testData.featureIds)
  })

  // -----------------------------------------------------------------------
  // Test 1: Consultant sees "Ready for Review" and starts a session
  // -----------------------------------------------------------------------
  test('consultant starts session and sees overlays', async ({ page }) => {
    await page.goto(`/projects/${projectId}/prototype`)

    await expect(
      page.getByRole('heading', { name: /Prototype Ready for Review/i })
    ).toBeVisible({ timeout: 30000 })

    await expect(page.getByText(/3 features analyzed/i)).toBeVisible()

    await page.getByRole('button', { name: /Start Review Session/i }).click()

    await expect(page.getByText(/^Session \d+$/)).toBeVisible({ timeout: 15000 })
    await expect(page.getByText('Feature Overlays')).toBeVisible({ timeout: 10000 })
  })

  // -----------------------------------------------------------------------
  // Test 2: Consultant ends review and sees awaiting_client panel
  // -----------------------------------------------------------------------
  test('consultant ends review and sees share panel', async ({ page }) => {
    await startReviewSession(page, projectId)
    await endReviewAndGetClientUrl(page, projectId)

    await expect(page.getByText(/Your Verdict Summary/i)).toBeVisible()
    await expect(page.getByRole('button', { name: /Share with Client/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /Fix First/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /Not Ready/i })).toBeVisible()
    await expect(page.getByText(/Listening for client feedback/i)).toBeVisible()
  })

  // -----------------------------------------------------------------------
  // Test 3: "Not Ready — Keep Working" returns to reviewing state
  // -----------------------------------------------------------------------
  test('"Not Ready" returns to reviewing state', async ({ page }) => {
    await startReviewSession(page, projectId)
    await endReviewAndGetClientUrl(page, projectId)

    await page.getByRole('button', { name: /Not Ready/i }).click()

    await expect(
      page.getByRole('button', { name: /End Review/i })
    ).toBeVisible({ timeout: 10000 })
  })

  // -----------------------------------------------------------------------
  // Test 4: Client opens portal, sees features, sets verdict, completes review
  // -----------------------------------------------------------------------
  test('client reviews via portal and completes review', async ({ page, browser }) => {
    await startReviewSession(page, projectId)
    const clientUrl = await endReviewAndGetClientUrl(page, projectId)

    // Open client URL in a NEW browser context (no auth — token-gated)
    const clientContext: BrowserContext = await browser.newContext()
    const clientPage = await clientContext.newPage()

    try {
      await clientPage.goto(clientUrl)

      // Should see "Prototype Review" header
      await expect(
        clientPage.getByRole('heading', { name: /Prototype Review/i })
      ).toBeVisible({ timeout: 30000 })

      // Should see instruction text
      await expect(
        clientPage.getByText(/Review each feature below/i)
      ).toBeVisible()

      // Should see feature review cards (3 features)
      await expect(
        clientPage.getByText(/features reviewed/i)
      ).toBeVisible({ timeout: 10000 })

      // Wait for React hydration
      await clientPage.waitForTimeout(2000)

      // Click "Aligned" on first feature via JS (Playwright native clicks
      // don't trigger React handlers in the nested portal layout)
      const verdictResponsePromise = clientPage.waitForResponse(
        (resp) => resp.url().includes('/verdict'),
        { timeout: 10000 }
      ).catch(() => null)

      const clicked = await portalClickButton(clientPage, 'Aligned')
      expect(clicked).toBe(true)

      const resp = await verdictResponsePromise
      expect(resp).not.toBeNull()
      expect(resp!.status()).toBe(200)

      // Verify UI updated
      await expect(
        clientPage.getByText(/1\/3 features reviewed/i)
      ).toBeVisible({ timeout: 5000 })

      // Verify in DB: at least one overlay has a client_verdict
      const allOverlays = await Promise.all(
        testData.overlayIds.map((id) => getOverlay(id))
      )
      const withVerdict = allOverlays.filter((o) => o?.client_verdict)
      expect(withVerdict.length).toBeGreaterThanOrEqual(1)

      // Click "Complete Review" via JS
      const completeResponsePromise = clientPage.waitForResponse(
        (resp) => resp.url().includes('/complete-client-review'),
        { timeout: 10000 }
      ).catch(() => null)

      await portalClickButton(clientPage, 'Complete Review')

      const completeResp = await completeResponsePromise
      expect(completeResp).not.toBeNull()

      // Should see "Thank You!" confirmation
      await expect(
        clientPage.getByText('Thank You!')
      ).toBeVisible({ timeout: 15000 })

      // Verify session status in DB
      const session = await getSessionByPrototype(testData.prototypeId)
      expect(session).not.toBeNull()
      expect(session!.client_completed_at).not.toBeNull()
    } finally {
      await clientContext.close()
    }
  })

  // -----------------------------------------------------------------------
  // Test 5: Client verdicts actually persist (regression test for prototypeId bug)
  // -----------------------------------------------------------------------
  test('client verdict persists to database', async ({ page, browser }) => {
    await startReviewSession(page, projectId)
    const clientUrl = await endReviewAndGetClientUrl(page, projectId)

    const clientContext: BrowserContext = await browser.newContext()
    const clientPage = await clientContext.newPage()

    try {
      await clientPage.goto(clientUrl)

      await expect(
        clientPage.getByRole('heading', { name: /Prototype Review/i })
      ).toBeVisible({ timeout: 30000 })

      // Wait for hydration
      await clientPage.waitForTimeout(2000)

      // Click "Needs Adjustment" on first feature via JS
      const verdictResponsePromise = clientPage.waitForResponse(
        (resp) => resp.url().includes('/verdict'),
        { timeout: 10000 }
      ).catch(() => null)

      await portalClickButton(clientPage, 'Needs Adjustment')

      const resp = await verdictResponsePromise
      expect(resp).not.toBeNull()
      expect(resp!.status()).toBe(200)

      // Verify directly in database
      await clientPage.waitForTimeout(500)
      const allOverlays = await Promise.all(
        testData.overlayIds.map((id) => getOverlay(id))
      )
      const needsAdj = allOverlays.filter((o) => o?.client_verdict === 'needs_adjustment')
      expect(needsAdj.length).toBeGreaterThanOrEqual(1)
    } finally {
      await clientContext.close()
    }
  })
})
