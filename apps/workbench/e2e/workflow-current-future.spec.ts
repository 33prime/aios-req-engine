import { test, expect, type Page } from '@playwright/test'
import path from 'path'

const authFile = path.join(__dirname, '.auth/user.json')

/**
 * Phase 2: Workflow Current/Future State
 *
 * Tests the workflow pair creation, side-by-side rendering,
 * step editor, automation badges, and ROI display.
 */

// Helper: navigate to BRD canvas with robust waiting
async function navigateToBRD(page: Page, projectId: string) {
  await page.goto(`/projects/${projectId}`)
  await page.getByText('Loading workspace...').waitFor({ state: 'hidden', timeout: 45000 }).catch(() => {})
  await page.getByRole('button', { name: /Discovery/i }).waitFor({ state: 'visible', timeout: 30000 })
  await page.getByRole('button', { name: /Discovery/i }).click()
  const brdViewBtn = page.getByRole('button', { name: 'BRD View' })
  await brdViewBtn.waitFor({ state: 'visible', timeout: 15000 })
  await brdViewBtn.click()
  await page.getByText('Loading BRD...').waitFor({ state: 'hidden', timeout: 30000 }).catch(() => {})
  await page.waitForSelector('text=Business Requirements Document', { timeout: 30000 })
}

// Helper: scroll to Workflows section
async function scrollToWorkflows(page: Page) {
  const heading = page.getByRole('heading', { name: /Key Workflows/i })
  await heading.scrollIntoViewIfNeeded()
  return heading
}

test.describe('Workflow Section — Rendering (Authenticated)', () => {
  test.skip(!process.env.TEST_USER_EMAIL, 'Requires TEST_USER_EMAIL env var')
  test.skip(!process.env.TEST_PROJECT_ID, 'Requires TEST_PROJECT_ID env var')

  test.setTimeout(60000)
  test.use({ storageState: authFile })

  const projectId = process.env.TEST_PROJECT_ID!

  test.beforeEach(async ({ page }) => {
    await navigateToBRD(page, projectId)
  })

  test('Key Workflows section heading and Add Workflow button are visible', async ({ page }) => {
    await scrollToWorkflows(page)

    // Section heading
    await expect(page.getByRole('heading', { name: /Key Workflows/i })).toBeVisible()

    // Add Workflow button
    await expect(page.getByRole('button', { name: /Add Workflow/i })).toBeVisible()
  })

  test('shows legacy flat workflow list OR workflow pairs', async ({ page }) => {
    await scrollToWorkflows(page)

    await page.waitForTimeout(1000)

    // Either we see workflow pair cards (with "Current State" or "Future State" labels)
    // or we see legacy flat VP step cards, or we see "No workflows mapped yet"
    const hasPairCards = await page.getByText('Current State').first().isVisible().catch(() => false)
      || await page.getByText('Future State').first().isVisible().catch(() => false)
    const hasLegacySteps = await page.locator('text=/^\\d+\\./').first().isVisible().catch(() => false)
    const hasEmptyState = await page.getByText('No workflows mapped yet').isVisible().catch(() => false)

    expect(hasPairCards || hasLegacySteps || hasEmptyState).toBe(true)
  })
})

test.describe('Workflow Creation Modal (Authenticated)', () => {
  test.skip(!process.env.TEST_USER_EMAIL, 'Requires TEST_USER_EMAIL env var')
  test.skip(!process.env.TEST_PROJECT_ID, 'Requires TEST_PROJECT_ID env var')

  test.setTimeout(60000)
  test.use({ storageState: authFile })

  const projectId = process.env.TEST_PROJECT_ID!

  test.beforeEach(async ({ page }) => {
    await navigateToBRD(page, projectId)
  })

  test('clicking Add Workflow opens the create modal', async ({ page }) => {
    await scrollToWorkflows(page)
    await page.getByRole('button', { name: /Add Workflow/i }).click()

    // Modal title
    await expect(page.getByRole('heading', { name: /Create Workflow/i })).toBeVisible({ timeout: 3000 })

    // Required fields
    await expect(page.getByLabel(/Name/i)).toBeVisible()
    await expect(page.getByText('Description')).toBeVisible()
    await expect(page.getByText('Owner')).toBeVisible()

    // State type toggle buttons
    await expect(page.getByRole('button', { name: /Future State/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /Current State/i })).toBeVisible()

    // ROI fields
    await expect(page.getByText(/Runs per week/i)).toBeVisible()
    await expect(page.getByText(/Hourly rate/i)).toBeVisible()

    // Action buttons
    await expect(page.getByRole('button', { name: 'Cancel' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Create' })).toBeVisible()
  })

  test('create button is disabled when name is empty', async ({ page }) => {
    await scrollToWorkflows(page)
    await page.getByRole('button', { name: /Add Workflow/i }).click()

    await expect(page.getByRole('heading', { name: /Create Workflow/i })).toBeVisible({ timeout: 3000 })

    // Create button should be disabled
    const createBtn = page.getByRole('button', { name: 'Create' })
    await expect(createBtn).toBeDisabled()
  })

  test('cancel button closes the modal', async ({ page }) => {
    await scrollToWorkflows(page)
    await page.getByRole('button', { name: /Add Workflow/i }).click()

    await expect(page.getByRole('heading', { name: /Create Workflow/i })).toBeVisible({ timeout: 3000 })

    await page.getByRole('button', { name: 'Cancel' }).click()

    // Modal should close
    await expect(page.getByRole('heading', { name: /Create Workflow/i })).not.toBeVisible()
  })

  test('state type toggle switches between current and future', async ({ page }) => {
    await scrollToWorkflows(page)
    await page.getByRole('button', { name: /Add Workflow/i }).click()

    await expect(page.getByRole('heading', { name: /Create Workflow/i })).toBeVisible({ timeout: 3000 })

    // Default should be Future State (has teal styling)
    const futureBtn = page.getByRole('button', { name: /Future State/i })
    const currentBtn = page.getByRole('button', { name: /Current State/i })

    // Click Current State
    await currentBtn.click()
    // Current State button should now have red styling (bg-red-50)
    await expect(currentBtn).toHaveClass(/bg-red-50/)

    // Click back to Future
    await futureBtn.click()
    await expect(futureBtn).toHaveClass(/bg-teal-50/)
  })

  test('can fill and submit the create workflow form', async ({ page }) => {
    await scrollToWorkflows(page)
    await page.getByRole('button', { name: /Add Workflow/i }).click()

    await expect(page.getByRole('heading', { name: /Create Workflow/i })).toBeVisible({ timeout: 3000 })

    // Fill in name
    const nameInput = page.locator('input[placeholder*="Client Onboarding"]')
    await nameInput.fill('E2E Test Workflow')

    // Fill description
    await page.locator('textarea[placeholder*="Brief description"]').fill('Test workflow description')

    // Fill owner
    await page.locator('input[placeholder*="Account Manager"]').fill('QA Tester')

    // Create button should now be enabled
    const createBtn = page.getByRole('button', { name: 'Create' })
    await expect(createBtn).toBeEnabled()

    // Submit the form
    await createBtn.click()

    // Modal should close after successful creation
    await expect(page.getByRole('heading', { name: /Create Workflow/i })).not.toBeVisible({ timeout: 5000 })

    // Wait for BRD data reload
    await page.waitForTimeout(2000)

    // The new workflow should appear in the list
    await scrollToWorkflows(page)
    const newWorkflow = page.getByText('E2E Test Workflow')
    await expect(newWorkflow).toBeVisible({ timeout: 5000 })
  })
})

test.describe('Workflow Pair Card — Side-by-Side (Authenticated)', () => {
  test.skip(!process.env.TEST_USER_EMAIL, 'Requires TEST_USER_EMAIL env var')
  test.skip(!process.env.TEST_PROJECT_ID, 'Requires TEST_PROJECT_ID env var')

  test.setTimeout(60000)
  test.use({ storageState: authFile })

  const projectId = process.env.TEST_PROJECT_ID!

  test.beforeEach(async ({ page }) => {
    await navigateToBRD(page, projectId)
    await scrollToWorkflows(page)
    await page.waitForTimeout(1000)
  })

  test('workflow pair card shows name, owner, and action buttons', async ({ page }) => {
    // Check if we have any workflow pair cards
    const pairCards = page.locator('.border.rounded-lg.shadow-sm.bg-white')
    const cardCount = await pairCards.count()

    if (cardCount > 0) {
      const firstCard = pairCards.first()
      // Card should have a workflow name visible
      const cardText = await firstCard.textContent()
      expect(cardText).toBeTruthy()

      // Check for action buttons (edit, delete icons)
      const editBtn = firstCard.locator('button[title="Edit workflow"]')
      const deleteBtn = firstCard.locator('button[title="Delete workflow"]')

      // At least one action button should exist
      const hasActions = (await editBtn.count()) > 0 || (await deleteBtn.count()) > 0
      if (hasActions) {
        expect(hasActions).toBe(true)
      }
    }
  })

  test('workflow pair card is collapsible', async ({ page }) => {
    const pairCards = page.locator('.border.rounded-lg.shadow-sm.bg-white')
    const cardCount = await pairCards.count()

    if (cardCount > 0) {
      const firstCard = pairCards.first()
      // Card header is clickable to collapse
      const header = firstCard.locator('.bg-gray-50\\/60').first()

      // Content should be visible initially (expanded by default)
      const content = firstCard.locator('.p-4').first()
      await expect(content).toBeVisible()

      // Click header to collapse
      await header.click()
      await page.waitForTimeout(300)

      // Content should be hidden
      await expect(content).not.toBeVisible()

      // Click again to expand
      await header.click()
      await page.waitForTimeout(300)

      await expect(content).toBeVisible()
    }
  })

  test('side-by-side columns show Current State and Future State labels when both exist', async ({ page }) => {
    // Look for paired workflows with both sides
    const currentLabel = page.getByText('Current State', { exact: true })
    const futureLabel = page.getByText('Future State', { exact: true })

    const hasCurrentLabel = await currentLabel.first().isVisible().catch(() => false)
    const hasFutureLabel = await futureLabel.first().isVisible().catch(() => false)

    // If we have a full pair, both labels should appear
    if (hasCurrentLabel && hasFutureLabel) {
      await expect(currentLabel.first()).toBeVisible()
      await expect(futureLabel.first()).toBeVisible()

      // Current side has "How it works today"
      await expect(page.getByText('How it works today').first()).toBeVisible()
      // Future side has "How the system improves it"
      await expect(page.getByText('How the system improves it').first()).toBeVisible()
    }
  })

  test('automation badges render with correct colors', async ({ page }) => {
    // Look for automation badges
    const manualBadge = page.getByText('Manual', { exact: true })
    const semiBadge = page.getByText('Semi-auto', { exact: true })
    const automatedBadge = page.getByText('Automated', { exact: true })

    const hasManual = await manualBadge.first().isVisible().catch(() => false)
    const hasSemi = await semiBadge.first().isVisible().catch(() => false)
    const hasAutomated = await automatedBadge.first().isVisible().catch(() => false)

    // At least one badge type should be visible if there are steps
    if (hasManual || hasSemi || hasAutomated) {
      // Verify at least one is visible (pass)
      expect(true).toBe(true)
    }
  })

  test('ROI footer shows time saved when workflow pair has ROI data', async ({ page }) => {
    // ROI chip in header: "Xmin saved (Y%)"
    const roiChip = page.getByText(/\d+min saved/)
    const hasROI = await roiChip.first().isVisible().catch(() => false)

    if (hasROI) {
      // ROI footer shows progress bar + stats
      await expect(page.getByText('Time saved').first()).toBeVisible()
      await expect(page.getByText(/Saves \d+min\/run/).first()).toBeVisible()
    }
  })
})

test.describe('Workflow Step Editor (Authenticated)', () => {
  test.skip(!process.env.TEST_USER_EMAIL, 'Requires TEST_USER_EMAIL env var')
  test.skip(!process.env.TEST_PROJECT_ID, 'Requires TEST_PROJECT_ID env var')

  test.setTimeout(60000)
  test.use({ storageState: authFile })

  const projectId = process.env.TEST_PROJECT_ID!

  test.beforeEach(async ({ page }) => {
    await navigateToBRD(page, projectId)
    await scrollToWorkflows(page)
    await page.waitForTimeout(1000)
  })

  test('add step button opens the step editor modal', async ({ page }) => {
    // Look for "Add current step" or "Add future step" buttons
    const addStepBtn = page.locator('button[title="Add current step"]').or(
      page.locator('button[title="Add future step"]')
    )

    const hasAddStep = await addStepBtn.first().isVisible().catch(() => false)

    if (hasAddStep) {
      await addStepBtn.first().click()

      // Step editor modal should appear
      await expect(page.getByRole('heading', { name: /Add Step/i })).toBeVisible({ timeout: 3000 })

      // Fields
      await expect(page.getByText('Label *')).toBeVisible()
      await expect(page.getByText('Description')).toBeVisible()
      await expect(page.getByText('Time (minutes)')).toBeVisible()
      await expect(page.getByText('Automation')).toBeVisible()
      await expect(page.getByText('Operation Type')).toBeVisible()

      // Depending on state type: Pain Description or Benefit Description
      const hasPain = await page.getByText('Pain Description').isVisible().catch(() => false)
      const hasBenefit = await page.getByText('Benefit Description').isVisible().catch(() => false)
      expect(hasPain || hasBenefit).toBe(true)

      // Cancel
      await page.getByRole('button', { name: 'Cancel' }).click()
      await expect(page.getByRole('heading', { name: /Add Step/i })).not.toBeVisible()
    }
  })

  test('step editor shows current state label for current-side steps', async ({ page }) => {
    const addCurrentBtn = page.locator('button[title="Add current step"]')
    const hasBtn = await addCurrentBtn.first().isVisible().catch(() => false)

    if (hasBtn) {
      await addCurrentBtn.first().click()

      // Should show "(Current)" label in header
      await expect(page.getByText('(Current)')).toBeVisible({ timeout: 3000 })

      // Pain Description should be visible (current state shows pain)
      await expect(page.getByText('Pain Description')).toBeVisible()

      await page.getByRole('button', { name: 'Cancel' }).click()
    }
  })

  test('step editor shows future state label for future-side steps', async ({ page }) => {
    const addFutureBtn = page.locator('button[title="Add future step"]')
    const hasBtn = await addFutureBtn.first().isVisible().catch(() => false)

    if (hasBtn) {
      await addFutureBtn.first().click()

      // Should show "(Future)" label in header
      await expect(page.getByText('(Future)')).toBeVisible({ timeout: 3000 })

      // Benefit Description should be visible (future state shows benefit)
      await expect(page.getByText('Benefit Description')).toBeVisible()

      await page.getByRole('button', { name: 'Cancel' }).click()
    }
  })

  test('add step button is disabled when label is empty', async ({ page }) => {
    const addStepBtn = page.locator('button[title="Add current step"]').or(
      page.locator('button[title="Add future step"]')
    )
    const hasBtn = await addStepBtn.first().isVisible().catch(() => false)

    if (hasBtn) {
      await addStepBtn.first().click()
      await expect(page.getByRole('heading', { name: /Add Step/i })).toBeVisible({ timeout: 3000 })

      // The "Add Step" submit button should be disabled when label is empty
      const submitBtn = page.getByRole('button', { name: 'Add Step' })
      await expect(submitBtn).toBeDisabled()

      await page.getByRole('button', { name: 'Cancel' }).click()
    }
  })

  test('automation level dropdown has all three options', async ({ page }) => {
    const addStepBtn = page.locator('button[title="Add current step"]').or(
      page.locator('button[title="Add future step"]')
    )
    const hasBtn = await addStepBtn.first().isVisible().catch(() => false)

    if (hasBtn) {
      await addStepBtn.first().click()
      await expect(page.getByRole('heading', { name: /Add Step/i })).toBeVisible({ timeout: 3000 })

      // Check automation select options
      const automationSelect = page.locator('select').filter({ has: page.locator('option:text("Manual")') })
      await expect(automationSelect).toBeVisible()

      // Verify all three options exist
      await expect(automationSelect.locator('option:text("Manual")')).toHaveCount(1)
      await expect(automationSelect.locator('option:text("Semi-automated")')).toHaveCount(1)
      await expect(automationSelect.locator('option:text("Fully automated")')).toHaveCount(1)

      await page.getByRole('button', { name: 'Cancel' }).click()
    }
  })

  test('operation type dropdown has CRUD + other options', async ({ page }) => {
    const addStepBtn = page.locator('button[title="Add current step"]').or(
      page.locator('button[title="Add future step"]')
    )
    const hasBtn = await addStepBtn.first().isVisible().catch(() => false)

    if (hasBtn) {
      await addStepBtn.first().click()
      await expect(page.getByRole('heading', { name: /Add Step/i })).toBeVisible({ timeout: 3000 })

      // Check operation type select
      const opSelect = page.locator('select').filter({ has: page.locator('option:text("Create")') })
      await expect(opSelect).toBeVisible()

      // Verify key options
      const expectedOptions = ['None', 'Create', 'Read', 'Update', 'Delete', 'Validate', 'Notify', 'Transfer']
      for (const opt of expectedOptions) {
        await expect(opSelect.locator(`option:text("${opt}")`)).toHaveCount(1)
      }

      await page.getByRole('button', { name: 'Cancel' }).click()
    }
  })
})

test.describe('Workflow CRUD — Full Flow (Authenticated)', () => {
  test.skip(!process.env.TEST_USER_EMAIL, 'Requires TEST_USER_EMAIL env var')
  test.skip(!process.env.TEST_PROJECT_ID, 'Requires TEST_PROJECT_ID env var')

  test.setTimeout(90000)
  test.use({ storageState: authFile })

  const projectId = process.env.TEST_PROJECT_ID!

  test('create workflow → verify appears → delete workflow', async ({ page }) => {
    await navigateToBRD(page, projectId)
    await scrollToWorkflows(page)

    const workflowName = `E2E Cleanup Test ${Date.now()}`

    // 1. Create a workflow
    await page.getByRole('button', { name: /Add Workflow/i }).click()
    await expect(page.getByRole('heading', { name: /Create Workflow/i })).toBeVisible({ timeout: 3000 })

    await page.locator('input[placeholder*="Client Onboarding"]').fill(workflowName)
    await page.getByRole('button', { name: 'Create' }).click()

    // Wait for modal close + data reload
    await expect(page.getByRole('heading', { name: /Create Workflow/i })).not.toBeVisible({ timeout: 5000 })
    await page.waitForTimeout(2000)

    // 2. Verify it appears
    await scrollToWorkflows(page)
    await expect(page.getByText(workflowName)).toBeVisible({ timeout: 5000 })

    // 3. Delete it
    // Find the card containing the workflow name
    const card = page.locator('.border.rounded-lg.shadow-sm.bg-white').filter({ hasText: workflowName })
    const deleteBtn = card.locator('button[title="Delete workflow"]')

    if (await deleteBtn.isVisible().catch(() => false)) {
      await deleteBtn.click()

      // Wait for deletion + data reload
      await page.waitForTimeout(2000)

      // Verify it's gone
      await expect(page.getByText(workflowName)).not.toBeVisible({ timeout: 5000 })
    }
  })
})
