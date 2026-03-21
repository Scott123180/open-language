import { test, expect } from '@playwright/test'
import { mockSettings } from './fixtures'

async function setupSettingsRoutes(page: import('@playwright/test').Page) {
  await page.route('/api/settings', (route) => {
    if (route.request().method() === 'PUT') {
      return route.fulfill({ json: mockSettings })
    }
    return route.fulfill({ json: mockSettings })
  })
}

async function setupHomeRoutes(page: import('@playwright/test').Page) {
  await page.route('/api/scenarios/current', (route) =>
    route.fulfill({ json: { id: 's1', title: 'Coffee Shop', description: 'Cafe' } }),
  )
}

test.describe('Dark mode', () => {
  test('Settings page shows theme toggle with Light, Dark, System options', async ({ page }) => {
    await setupSettingsRoutes(page)
    await page.goto('/settings')
    await expect(page.getByRole('group', { name: /theme/i })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Light' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Dark' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'System' })).toBeVisible()
  })

  test('clicking Dark sets data-theme="dark" on the html element', async ({ page }) => {
    await setupSettingsRoutes(page)
    await page.goto('/settings')
    await page.getByRole('button', { name: 'Dark' }).click()
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  })

  test('clicking Light sets data-theme="light" on the html element', async ({ page }) => {
    await setupSettingsRoutes(page)
    await page.goto('/settings')
    await page.getByRole('button', { name: 'Dark' }).click()
    await page.getByRole('button', { name: 'Light' }).click()
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'light')
  })

  test('clicking System removes data-theme attribute', async ({ page }) => {
    await setupSettingsRoutes(page)
    await page.goto('/settings')
    await page.getByRole('button', { name: 'Dark' }).click()
    await page.getByRole('button', { name: 'System' }).click()
    await expect(page.locator('html')).not.toHaveAttribute('data-theme')
  })

  test('dark mode preference persists across page reload', async ({ page }) => {
    await setupSettingsRoutes(page)
    await page.goto('/settings')
    await page.getByRole('button', { name: 'Dark' }).click()
    await page.reload()
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  })

  test('light mode preference persists across page reload', async ({ page }) => {
    await setupSettingsRoutes(page)
    await page.goto('/settings')
    await page.getByRole('button', { name: 'Dark' }).click()
    await page.getByRole('button', { name: 'Light' }).click()
    await page.reload()
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'light')
  })

  test('theme persists when navigating to other pages', async ({ page }) => {
    await setupSettingsRoutes(page)
    await setupHomeRoutes(page)
    await page.route('/api/conversations', (route) => route.fulfill({ json: [] }))

    await page.goto('/settings')
    await page.getByRole('button', { name: 'Dark' }).click()
    await page.getByRole('link', { name: '← Back to Home' }).click()
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  })

  test('home page shows theme toggle button', async ({ page }) => {
    await setupHomeRoutes(page)
    await page.goto('/')
    await expect(page.getByRole('button', { name: /toggle theme|dark mode|light mode/i })).toBeVisible()
  })

  test('home page theme toggle switches between light and dark', async ({ page }) => {
    await setupHomeRoutes(page)
    await page.goto('/')
    const toggle = page.getByRole('button', { name: /toggle theme|dark mode|light mode/i })
    await toggle.click()
    const theme = await page.locator('html').getAttribute('data-theme')
    expect(['dark', 'light']).toContain(theme)
  })

  test('active theme button is visually indicated in Settings', async ({ page }) => {
    await setupSettingsRoutes(page)
    await page.goto('/settings')
    await page.getByRole('button', { name: 'Dark' }).click()
    // Active button should have aria-pressed="true"
    await expect(page.getByRole('button', { name: 'Dark' })).toHaveAttribute('aria-pressed', 'true')
    await expect(page.getByRole('button', { name: 'Light' })).toHaveAttribute('aria-pressed', 'false')
    await expect(page.getByRole('button', { name: 'System' })).toHaveAttribute('aria-pressed', 'false')
  })

  test('dark mode applies dark background color', async ({ page }) => {
    await setupSettingsRoutes(page)
    await page.goto('/settings')
    await page.getByRole('button', { name: 'Dark' }).click()
    const bgColor = await page.evaluate(() =>
      getComputedStyle(document.documentElement).getPropertyValue('--color-bg').trim(),
    )
    // Dark bg should not be the light default (#f8fafc)
    expect(bgColor).not.toBe('#f8fafc')
  })
})
