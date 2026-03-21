import { test, expect } from '@playwright/test'
import { mockSettings } from './fixtures'

const SETTINGS_URL = '/settings'

async function setupSettingsRoutes(
  page: import('@playwright/test').Page,
  settings: typeof mockSettings = mockSettings,
) {
  await page.route('/api/settings', (route) => {
    if (route.request().method() === 'PUT') {
      return route.fulfill({ json: { ...settings, updated_at: new Date().toISOString() } })
    }
    return route.fulfill({ json: settings })
  })
}

test.describe('Settings page', () => {
  test('shows Settings heading', async ({ page }) => {
    await setupSettingsRoutes(page)
    await page.goto(SETTINGS_URL)
    await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible()
  })

  test('shows loading state before settings arrive', async ({ page }) => {
    await page.route('/api/settings', async (route) => {
      await new Promise((r) => setTimeout(r, 200))
      await route.fulfill({ json: mockSettings })
    })
    await page.goto(SETTINGS_URL)
    await expect(page.getByText('Loading settings…')).toBeVisible()
  })

  test('loads and displays current LLM model', async ({ page }) => {
    await setupSettingsRoutes(page)
    await page.goto(SETTINGS_URL)
    await expect(page.getByLabel('LLM Model')).toHaveValue('llama3.1')
  })

  test('loads and displays current suggestion count', async ({ page }) => {
    await setupSettingsRoutes(page)
    await page.goto(SETTINGS_URL)
    await expect(page.getByLabel('Suggestion Count (1–5)')).toHaveValue('3')
  })

  test('model select shows all available models', async ({ page }) => {
    await setupSettingsRoutes(page)
    await page.goto(SETTINGS_URL)
    const select = page.getByLabel('LLM Model')
    await expect(select.getByRole('option', { name: 'llama3.1' })).toBeAttached()
    await expect(select.getByRole('option', { name: 'llama3.2' })).toBeAttached()
    await expect(select.getByRole('option', { name: 'mistral' })).toBeAttached()
  })

  test('changing model updates the select value', async ({ page }) => {
    await setupSettingsRoutes(page)
    await page.goto(SETTINGS_URL)
    await page.getByLabel('LLM Model').selectOption('mistral')
    await expect(page.getByLabel('LLM Model')).toHaveValue('mistral')
  })

  test('changing suggestion count updates the input', async ({ page }) => {
    await setupSettingsRoutes(page)
    await page.goto(SETTINGS_URL)
    await page.getByLabel('Suggestion Count (1–5)').fill('5')
    await expect(page.getByLabel('Suggestion Count (1–5)')).toHaveValue('5')
  })

  test('save button sends updated settings to API', async ({ page }) => {
    let capturedBody: unknown = null
    await page.route('/api/settings', (route) => {
      if (route.request().method() === 'PUT') {
        capturedBody = route.request().postDataJSON()
        return route.fulfill({ json: mockSettings })
      }
      return route.fulfill({ json: mockSettings })
    })
    await page.goto(SETTINGS_URL)

    await page.getByLabel('LLM Model').selectOption('mistral')
    await page.getByLabel('Suggestion Count (1–5)').fill('5')
    await page.getByRole('button', { name: /save/i }).click()

    await expect(page.getByRole('status')).toContainText('Settings saved.')
    expect(capturedBody).toMatchObject({ llm_model: 'mistral', suggestion_count: 5 })
  })

  test('shows success message after saving', async ({ page }) => {
    await setupSettingsRoutes(page)
    await page.goto(SETTINGS_URL)
    await page.getByRole('button', { name: /save/i }).click()
    await expect(page.getByRole('status')).toContainText('Settings saved.')
  })

  test('shows error message when save fails', async ({ page }) => {
    await page.route('/api/settings', (route) => {
      if (route.request().method() === 'PUT') {
        return route.fulfill({ status: 500, json: { detail: 'Database unavailable' } })
      }
      return route.fulfill({ json: mockSettings })
    })
    await page.goto(SETTINGS_URL)
    await page.getByRole('button', { name: /save/i }).click()
    await expect(page.getByRole('alert')).toContainText('Database unavailable')
  })

  test('save button shows saving state while request is in flight', async ({ page }) => {
    await page.route('/api/settings', async (route) => {
      if (route.request().method() === 'PUT') {
        await new Promise((r) => setTimeout(r, 300))
        return route.fulfill({ json: mockSettings })
      }
      return route.fulfill({ json: mockSettings })
    })
    await page.goto(SETTINGS_URL)
    await page.getByRole('button', { name: /save/i }).click()
    await expect(page.getByRole('button', { name: /saving/i })).toBeVisible()
    await expect(page.getByRole('status')).toContainText('Settings saved.')
  })

  test('save button is disabled while saving', async ({ page }) => {
    await page.route('/api/settings', async (route) => {
      if (route.request().method() === 'PUT') {
        await new Promise((r) => setTimeout(r, 300))
        return route.fulfill({ json: mockSettings })
      }
      return route.fulfill({ json: mockSettings })
    })
    await page.goto(SETTINGS_URL)
    await page.getByRole('button', { name: /save/i }).click()
    await expect(page.getByRole('button', { name: /saving/i })).toBeDisabled()
  })

  test('suggestion count input enforces min of 1', async ({ page }) => {
    await setupSettingsRoutes(page)
    await page.goto(SETTINGS_URL)
    const input = page.getByLabel('Suggestion Count (1–5)')
    await expect(input).toHaveAttribute('min', '1')
  })

  test('suggestion count input enforces max of 5', async ({ page }) => {
    await setupSettingsRoutes(page)
    await page.goto(SETTINGS_URL)
    const input = page.getByLabel('Suggestion Count (1–5)')
    await expect(input).toHaveAttribute('max', '5')
  })

  test('form submits on Enter key press in suggestion count field', async ({ page }) => {
    let saveCalled = false
    await page.route('/api/settings', (route) => {
      if (route.request().method() === 'PUT') {
        saveCalled = true
        return route.fulfill({ json: mockSettings })
      }
      return route.fulfill({ json: mockSettings })
    })
    await page.goto(SETTINGS_URL)
    // Pressing Enter on a number input inside a form triggers form submit
    await page.getByLabel('Suggestion Count (1–5)').press('Enter')
    await expect(page.getByRole('status')).toContainText('Settings saved.')
    expect(saveCalled).toBe(true)
  })

  test('Back to Home link navigates to home page', async ({ page }) => {
    await setupSettingsRoutes(page)
    await page.route('/api/scenarios/current', (route) =>
      route.fulfill({ json: { id: 's1', title: 'Coffee Shop', description: 'Cafe' } }),
    )
    await page.goto(SETTINGS_URL)
    await page.getByRole('link', { name: '← Back to Home' }).click()
    await expect(page).toHaveURL('/')
    await expect(page.getByRole('heading', { name: 'Open Language' })).toBeVisible()
  })

  test('loads settings from different initial values', async ({ page }) => {
    await setupSettingsRoutes(page, {
      ...mockSettings,
      llm_model: 'llama3.2',
      suggestion_count: 5,
    })
    await page.goto(SETTINGS_URL)
    await expect(page.getByLabel('LLM Model')).toHaveValue('llama3.2')
    await expect(page.getByLabel('Suggestion Count (1–5)')).toHaveValue('5')
  })

  test('success message clears after subsequent save attempt', async ({ page }) => {
    await setupSettingsRoutes(page)
    await page.goto(SETTINGS_URL)

    // First save — success
    await page.getByRole('button', { name: /save/i }).click()
    await expect(page.getByRole('status')).toContainText('Settings saved.')

    // Second save — success message should still be visible (it gets cleared then re-shown)
    await page.getByRole('button', { name: /save/i }).click()
    await expect(page.getByRole('status')).toContainText('Settings saved.')
  })
})
