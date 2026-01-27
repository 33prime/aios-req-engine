import { test, expect } from '@playwright/test'

test.describe('Login Page (Unauthenticated)', () => {
  test('homepage redirects to login', async ({ page }) => {
    await page.goto('/')

    // Should redirect to /auth/login
    await expect(page).toHaveURL(/\/auth\/login/)
  })

  test('displays login form', async ({ page }) => {
    await page.goto('/auth/login')

    // Check heading
    await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible()

    // Check form elements
    await expect(page.getByLabel('Email address')).toBeVisible()
    await expect(page.getByLabel('Password')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible()
  })

  test('displays branding', async ({ page }) => {
    await page.goto('/auth/login')

    // Use first() since branding appears twice (desktop hero panel + mobile header)
    await expect(page.getByText('Consultant Workbench').first()).toBeVisible()
    await expect(page.getByText('Enter your credentials to access your account')).toBeVisible()
  })

  test('has magic link option for clients', async ({ page }) => {
    await page.goto('/auth/login')

    await expect(page.getByText('Are you a client?')).toBeVisible()
    await expect(page.getByRole('link', { name: 'Sign in with magic link' })).toBeVisible()
  })

  test('sign in button is disabled without credentials', async ({ page }) => {
    await page.goto('/auth/login')

    const signInButton = page.getByRole('button', { name: 'Sign in' })
    await expect(signInButton).toBeDisabled()
  })

  test('sign in button enables when form is filled', async ({ page }) => {
    await page.goto('/auth/login')

    await page.getByLabel('Email address').fill('test@example.com')
    await page.getByLabel('Password').fill('password123')

    const signInButton = page.getByRole('button', { name: 'Sign in' })
    await expect(signInButton).toBeEnabled()
  })

  test('shows error on invalid credentials', async ({ page }) => {
    await page.goto('/auth/login')

    await page.getByLabel('Email address').fill('invalid@example.com')
    await page.getByLabel('Password').fill('wrongpassword')
    await page.getByRole('button', { name: 'Sign in' }).click()

    // Wait for error message (API will return an error)
    await expect(page.getByText(/failed|invalid|error/i)).toBeVisible({ timeout: 10000 })
  })

  test('magic link page is accessible', async ({ page }) => {
    await page.goto('/auth/login')

    await page.getByRole('link', { name: 'Sign in with magic link' }).click()

    await expect(page).toHaveURL('/auth')
  })
})

test.describe('Protected Routes (Unauthenticated)', () => {
  test('projects page redirects to login', async ({ page }) => {
    await page.goto('/projects')

    await expect(page).toHaveURL(/\/auth\/login/)
  })
})
