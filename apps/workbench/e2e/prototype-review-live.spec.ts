/**
 * Live prototype review test — runs against the REAL Unmasked prototype.
 *
 * Unlike the seeded E2E tests, this uses existing production data:
 * - Project: 5f7ac835 (Unmasked)
 * - Prototype: 3f768a2d (14 overlays, real deploy URL)
 * - iframe loads https://v0-unmasked-app-prototype.vercel.app
 *
 * Run: cd apps/workbench && npx playwright test prototype-review-live --headed --project=chromium --no-deps
 *
 * Cleans up after itself (deletes session + clears verdicts).
 */
import { test, expect, type Page, type BrowserContext } from '@playwright/test'
import path from 'path'
import { createClient } from '@supabase/supabase-js'
import dotenv from 'dotenv'

dotenv.config({ path: path.resolve(__dirname, '../../../.env') })

const authFile = path.join(__dirname, '.auth/user.json')

const UNMASKED_PROJECT_ID = '5f7ac835-d557-480f-9789-21a9631cc369'
const UNMASKED_PROTOTYPE_ID = '3f768a2d-fd88-4a09-931e-9d1ef648036f'

const supabase = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,
  { auth: { autoRefreshToken: false, persistSession: false } }
)

/** Click a portal button via JS (React handler workaround) */
async function portalClickButton(page: Page, textMatch: string): Promise<boolean> {
  return page.evaluate((match) => {
    const buttons = Array.from(document.querySelectorAll('button'))
    const btn = buttons.find((b) => b.textContent?.includes(match))
    if (btn) { btn.click(); return true }
    return false
  }, textMatch)
}

test.describe.serial('Live Prototype Review — Unmasked', () => {
  test.skip(!process.env.TEST_USER_EMAIL, 'Requires TEST_USER_EMAIL env var')
  test.setTimeout(120000)
  test.use({ storageState: authFile })

  let sessionId: string | null = null

  test.afterAll(async () => {
    // Clean up: delete the session we created + clear any verdicts
    if (sessionId) {
      await supabase.from('prototype_sessions').delete().eq('id', sessionId)
    }
    // Clear any verdicts we set
    await supabase
      .from('prototype_feature_overlays')
      .update({ consultant_verdict: null, consultant_notes: null, client_verdict: null, client_notes: null })
      .eq('prototype_id', UNMASKED_PROTOTYPE_ID)
  })

  test('full review loop with real prototype iframe', async ({ page, browser }) => {
    // ── Step 1: Navigate to prototype page ──
    await page.goto(`/projects/${UNMASKED_PROJECT_ID}/prototype`)

    // Wait for "Prototype Ready for Review" or existing session
    const startBtn = page.getByRole('button', { name: /Start Review Session/i })
    await startBtn.waitFor({ state: 'visible', timeout: 30000 })

    console.log('✓ Prototype page loaded — 14 features analyzed')
    await expect(page.getByText(/14 features analyzed/i)).toBeVisible()

    // ── Step 2: Start session ──
    await startBtn.click()
    await expect(page.getByText(/^Session \d+$/)).toBeVisible({ timeout: 15000 })

    // Grab session ID from DB
    const { data: sessions } = await supabase
      .from('prototype_sessions')
      .select('id, session_number')
      .eq('prototype_id', UNMASKED_PROTOTYPE_ID)
      .order('session_number', { ascending: false })
      .limit(1)
    sessionId = sessions?.[0]?.id || null
    console.log(`✓ Session started (#${sessions?.[0]?.session_number}) — id: ${sessionId}`)

    // ── Step 3: Verify iframe loaded the real prototype ──
    const iframe = page.locator('iframe')
    await expect(iframe).toBeVisible({ timeout: 15000 })
    const iframeSrc = await iframe.getAttribute('src')
    expect(iframeSrc).toContain('v0-unmasked-app-prototype.vercel.app')
    console.log(`✓ Iframe loaded: ${iframeSrc}`)

    // ── Step 4: Verify overlay panel shows features ──
    await expect(page.getByText('Feature Overlays')).toBeVisible({ timeout: 10000 })
    console.log('✓ Feature overlay panel visible')

    // Let the user see the prototype for a moment
    await page.waitForTimeout(3000)

    // ── Step 5: End review ──
    await page.getByRole('button', { name: /End Review/i }).click()
    await expect(
      page.getByRole('heading', { name: /Review Complete/i })
    ).toBeVisible({ timeout: 15000 })

    // Extract client URL
    const linkInput = page.locator('input[readonly]')
    await expect(linkInput).toBeVisible()
    const clientUrl = await linkInput.inputValue()
    expect(clientUrl).toContain('/portal/')
    console.log(`✓ Review ended — client URL: ${clientUrl}`)

    // ── Step 6: Open client portal in new context ──
    const clientContext: BrowserContext = await browser.newContext()
    const clientPage = await clientContext.newPage()

    try {
      await clientPage.goto(clientUrl)

      await expect(
        clientPage.getByRole('heading', { name: /Prototype Review/i })
      ).toBeVisible({ timeout: 30000 })

      await expect(
        clientPage.getByText(/features reviewed/i)
      ).toBeVisible({ timeout: 10000 })

      console.log('✓ Client portal loaded — features visible')

      // Wait for hydration
      await clientPage.waitForTimeout(2000)

      // ── Step 7: Set verdicts on first 3 features ──
      // Click Aligned
      const v1 = clientPage.waitForResponse(r => r.url().includes('/verdict'), { timeout: 10000 }).catch(() => null)
      await portalClickButton(clientPage, 'Aligned')
      const r1 = await v1
      console.log(`✓ Verdict 1 (Aligned): ${r1?.status() || 'no response'}`)

      await clientPage.waitForTimeout(500)

      // Click Needs Adjustment on second feature
      const v2 = clientPage.waitForResponse(r => r.url().includes('/verdict'), { timeout: 10000 }).catch(() => null)
      await portalClickButton(clientPage, 'Needs Adjustment')
      const r2 = await v2
      console.log(`✓ Verdict 2 (Needs Adjustment): ${r2?.status() || 'no response'}`)

      await clientPage.waitForTimeout(500)

      // ── Step 8: Complete review ──
      const completeResp = clientPage.waitForResponse(
        r => r.url().includes('/complete-client-review'),
        { timeout: 10000 }
      ).catch(() => null)

      await portalClickButton(clientPage, 'Complete Review')
      const cr = await completeResp
      console.log(`✓ Complete review: ${cr?.status() || 'no response'}`)

      await expect(
        clientPage.getByText('Thank You!')
      ).toBeVisible({ timeout: 15000 })

      console.log('✓ Client review complete — "Thank You!" displayed')

      // ── Step 9: Verify DB state ──
      const { data: overlays } = await supabase
        .from('prototype_feature_overlays')
        .select('id, client_verdict')
        .eq('prototype_id', UNMASKED_PROTOTYPE_ID)

      const withVerdict = overlays?.filter(o => o.client_verdict) || []
      console.log(`✓ DB check: ${withVerdict.length} overlays have client verdicts`)
      expect(withVerdict.length).toBeGreaterThanOrEqual(1)

      const session = await supabase
        .from('prototype_sessions')
        .select('status, client_completed_at')
        .eq('id', sessionId!)
        .single()
      console.log(`✓ Session status: ${session.data?.status}, client_completed_at: ${session.data?.client_completed_at ? 'SET' : 'NULL'}`)
    } finally {
      await clientContext.close()
    }
  })
})
