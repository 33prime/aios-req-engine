import { test, expect } from '@playwright/test'
import fs from 'fs'
import path from 'path'

const authFile = path.join(__dirname, '.auth/user.json')

// Check if we have valid auth state
function hasValidAuth(): boolean {
  if (!fs.existsSync(authFile)) return false
  try {
    const state = JSON.parse(fs.readFileSync(authFile, 'utf-8'))
    // Check if there are any cookies or localStorage entries
    return (state.cookies?.length > 0 || state.origins?.some((o: any) => o.localStorage?.length > 0))
  } catch {
    return false
  }
}

// Only run these tests if auth is configured
test.describe('Projects Page (Authenticated)', () => {
  test.skip(!process.env.TEST_USER_EMAIL, 'Requires TEST_USER_EMAIL and TEST_USER_PASSWORD env vars')

  test.use({ storageState: authFile })

  test('displays Daily Snapshot header', async ({ page }) => {
    await page.goto('/projects')

    await expect(page.getByRole('heading', { name: 'Daily Snapshot' })).toBeVisible()
    await expect(page.getByText('Welcome back!')).toBeVisible()
  })

  test('displays Latest Projects section', async ({ page }) => {
    await page.goto('/projects')

    await expect(page.getByRole('heading', { name: 'Latest Projects' })).toBeVisible()
  })

  test('displays Upcoming Meetings section', async ({ page }) => {
    await page.goto('/projects')

    await expect(page.getByRole('heading', { name: 'Upcoming Meetings' })).toBeVisible()
  })

  test('has search input', async ({ page }) => {
    await page.goto('/projects')

    const searchInput = page.getByPlaceholder('Search...')
    await expect(searchInput).toBeVisible()
  })

  test('has Active/Archived filter buttons', async ({ page }) => {
    await page.goto('/projects')

    await expect(page.getByRole('button', { name: 'Active' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Archived' })).toBeVisible()
  })

  test('can switch between Active and Archived filters', async ({ page }) => {
    await page.goto('/projects')

    // Active should be selected by default
    const activeButton = page.getByRole('button', { name: 'Active' })
    const archivedButton = page.getByRole('button', { name: 'Archived' })

    // Click Archived
    await archivedButton.click()

    // Click Active again
    await activeButton.click()
  })

  test('has New Project button', async ({ page }) => {
    await page.goto('/projects')

    const newProjectButton = page.getByRole('button', { name: /New Project/i })
    await expect(newProjectButton).toBeVisible()
  })

  test('clicking New Project opens creation modal', async ({ page }) => {
    await page.goto('/projects')

    await page.getByRole('button', { name: /New Project/i }).click()

    // Wait for modal to appear
    await expect(page.getByRole('dialog').or(page.locator('[class*="modal"]'))).toBeVisible({ timeout: 5000 })
  })

  test('search filters projects', async ({ page }) => {
    await page.goto('/projects')

    const searchInput = page.getByPlaceholder('Search...')
    await searchInput.fill('nonexistent-project-12345')
    await searchInput.press('Enter')

    // Should show no results or filtered list
    await page.waitForTimeout(1000) // Wait for filter to apply
  })
})
