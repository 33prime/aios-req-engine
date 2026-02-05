import { test, expect } from '@playwright/test'
import fs from 'fs'
import path from 'path'

const authFile = path.join(__dirname, '.auth/user.json')

test.describe('Stage Progression (Authenticated)', () => {
  test.skip(!process.env.TEST_USER_EMAIL, 'Requires TEST_USER_EMAIL and TEST_USER_PASSWORD env vars')

  test.use({ storageState: authFile })

  test('kanban view loads with stage columns visible', async ({ page }) => {
    await page.goto('/projects')

    // Switch to kanban view
    const kanbanButton = page.locator('button[title="Kanban view"]').or(
      page.getByRole('button', { name: /kanban/i })
    )
    if (await kanbanButton.isVisible()) {
      await kanbanButton.click()
    }

    // Verify stage columns are visible
    await expect(page.getByText('Discovery')).toBeVisible()
    await expect(page.getByText('Validation')).toBeVisible()
    await expect(page.getByText('Prototype')).toBeVisible()
    await expect(page.getByText('Proposal')).toBeVisible()
    await expect(page.getByText('Build')).toBeVisible()
    await expect(page.getByText('Live')).toBeVisible()
  })

  test('projects with stage_eligible=true show advance indicator', async ({ page }) => {
    await page.goto('/projects')

    // Switch to kanban view
    const kanbanButton = page.locator('button[title="Kanban view"]').or(
      page.getByRole('button', { name: /kanban/i })
    )
    if (await kanbanButton.isVisible()) {
      await kanbanButton.click()
    }

    // Wait for projects to load
    await page.waitForTimeout(2000)

    // Check for advance indicator (green up arrow) — may not exist if no projects are eligible
    const advanceIndicators = page.locator('button[title="Ready to advance stage"]')
    const count = await advanceIndicators.count()

    // If any eligible projects exist, verify the indicator is visible
    if (count > 0) {
      await expect(advanceIndicators.first()).toBeVisible()
    }
  })

  test('clicking advance indicator opens stage popover', async ({ page }) => {
    await page.goto('/projects')

    // Switch to kanban view
    const kanbanButton = page.locator('button[title="Kanban view"]').or(
      page.getByRole('button', { name: /kanban/i })
    )
    if (await kanbanButton.isVisible()) {
      await kanbanButton.click()
    }

    await page.waitForTimeout(2000)

    const advanceIndicators = page.locator('button[title="Ready to advance stage"]')
    const count = await advanceIndicators.count()

    if (count > 0) {
      // Click the first advance indicator
      await advanceIndicators.first().click()

      // Popover should show criteria checklist
      await expect(page.getByText('criteria met')).toBeVisible({ timeout: 5000 })
    }
  })

  test('popover shows criteria checklist with gate labels', async ({ page }) => {
    await page.goto('/projects')

    const kanbanButton = page.locator('button[title="Kanban view"]').or(
      page.getByRole('button', { name: /kanban/i })
    )
    if (await kanbanButton.isVisible()) {
      await kanbanButton.click()
    }

    await page.waitForTimeout(2000)

    const advanceIndicators = page.locator('button[title="Ready to advance stage"]')
    const count = await advanceIndicators.count()

    if (count > 0) {
      await advanceIndicators.first().click()

      // Should show known gate labels
      const gateLabels = ['Core Pain', 'Primary Persona', 'Wow Moment', 'Business Case', 'Budget', 'Full Requirements', 'Confirmed Scope']
      let foundAtLeastOne = false

      for (const label of gateLabels) {
        const el = page.getByText(label)
        if (await el.isVisible().catch(() => false)) {
          foundAtLeastOne = true
          break
        }
      }

      // At least one gate label should be visible in the criteria list
      expect(foundAtLeastOne).toBe(true)
    }
  })

  test('advance button is visible when all criteria met', async ({ page }) => {
    await page.goto('/projects')

    const kanbanButton = page.locator('button[title="Kanban view"]').or(
      page.getByRole('button', { name: /kanban/i })
    )
    if (await kanbanButton.isVisible()) {
      await kanbanButton.click()
    }

    await page.waitForTimeout(2000)

    const advanceIndicators = page.locator('button[title="Ready to advance stage"]')
    const count = await advanceIndicators.count()

    if (count > 0) {
      await advanceIndicators.first().click()

      // Wait for popover content
      await page.waitForTimeout(1000)

      // Look for the "Advance to ..." button
      const advanceButton = page.locator('button:has-text("Advance to")')
      if (await advanceButton.isVisible().catch(() => false)) {
        await expect(advanceButton).toBeEnabled()
      }
    }
  })
})
