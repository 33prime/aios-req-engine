import { test as setup, expect } from '@playwright/test'
import path from 'path'

const authFile = path.join(__dirname, '.auth/user.json')

/**
 * Authentication setup for e2e tests.
 *
 * To run authenticated tests, set these environment variables:
 *   TEST_USER_EMAIL=your-test-user@example.com
 *   TEST_USER_PASSWORD=your-test-password
 *
 * Then run: npm run test:e2e
 *
 * The auth state will be saved and reused across tests.
 */
setup('authenticate', async ({ page }) => {
  const email = process.env.TEST_USER_EMAIL
  const password = process.env.TEST_USER_PASSWORD

  if (!email || !password) {
    console.log('Skipping auth setup - TEST_USER_EMAIL and TEST_USER_PASSWORD not set')
    // Create empty auth file so tests can check if auth is available
    await page.context().storageState({ path: authFile })
    return
  }

  await page.goto('/auth/login')

  await page.getByLabel('Email address').fill(email)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Sign in' }).click()

  // Wait for redirect to projects page
  await expect(page).toHaveURL('/projects', { timeout: 15000 })

  // Save auth state
  await page.context().storageState({ path: authFile })
})
