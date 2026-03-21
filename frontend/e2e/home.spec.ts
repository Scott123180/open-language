import { test, expect } from '@playwright/test'
import { mockHomeApis, mockConversation, mockScenario, mockScenario2 } from './fixtures'

test.describe('Home page', () => {
  test.beforeEach(async ({ page }) => {
    await mockHomeApis(page)
    await page.goto('/')
  })

  test('displays Open Language heading', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Open Language' })).toBeVisible()
  })

  test('shows loading state while fetching scenario', async ({ page }) => {
    // Delay scenario response to catch the loading state
    await page.route('/api/scenarios/current', async (route) => {
      await new Promise((r) => setTimeout(r, 200))
      await route.fulfill({ json: mockScenario })
    })
    await page.goto('/')
    await expect(page.getByText('Loading scenario…')).toBeVisible()
  })

  test('shows scenario card after loading', async ({ page }) => {
    await expect(page.getByText(mockScenario.title)).toBeVisible()
    await expect(page.getByText(mockScenario.description)).toBeVisible()
  })

  test('shows navigation links for Past Chats and Settings', async ({ page }) => {
    await expect(page.getByRole('link', { name: 'Past Chats' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Settings' })).toBeVisible()
  })

  test('navigates to History page via Past Chats link', async ({ page }) => {
    await page.route('/api/conversations', (route) =>
      route.fulfill({ json: [] }),
    )
    await page.getByRole('link', { name: 'Past Chats' }).click()
    await expect(page).toHaveURL('/history')
    await expect(page.getByRole('heading', { name: 'Past Chats' })).toBeVisible()
  })

  test('navigates to Settings page via Settings link', async ({ page }) => {
    await page.route('/api/settings', (route) =>
      route.fulfill({
        json: {
          llm_model: 'llama3.1',
          target_language: 'Spanish',
          native_language: 'English',
          tts_voice: 'en_US-ryan-high',
          suggestion_count: 3,
          updated_at: '2026-03-20T10:00:00Z',
        },
      }),
    )
    await page.getByRole('link', { name: 'Settings' }).click()
    await expect(page).toHaveURL('/settings')
    await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible()
  })

  test('refresh button loads next scenario', async ({ page }) => {
    await expect(page.getByText(mockScenario.title)).toBeVisible()
    await page.getByRole('button', { name: /refresh/i }).click()
    await expect(page.getByText(mockScenario2.title)).toBeVisible()
    await expect(page.getByText(mockScenario2.description)).toBeVisible()
  })

  test('shows error banner when scenario API fails', async ({ page }) => {
    await page.route('/api/scenarios/current', (route) =>
      route.fulfill({ status: 500, json: { detail: 'Server error' } }),
    )
    await page.goto('/')
    await expect(page.getByRole('alert')).toBeVisible()
    await expect(page.getByRole('alert')).toContainText('Server error')
  })

  test('dismisses error banner on click', async ({ page }) => {
    await page.route('/api/scenarios/current', (route) =>
      route.fulfill({ status: 500, json: { detail: 'Server error' } }),
    )
    await page.goto('/')
    await expect(page.getByRole('alert')).toBeVisible()
    await page.getByRole('button', { name: /dismiss/i }).click()
    await expect(page.getByRole('alert')).not.toBeVisible()
  })

  test('start chat button navigates to chat page', async ({ page }) => {
    await page.route('/api/settings', (route) =>
      route.fulfill({ json: { llm_model: 'llama3.1', target_language: 'Spanish', native_language: 'English', tts_voice: '', suggestion_count: 3, updated_at: '' } }),
    )
    await page.route('/api/conversations/1', (route) =>
      route.fulfill({ json: mockConversation }),
    )
    await page.route('/api/chat/1/open', (route) =>
      route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: 'data: {"done":true,"message_id":1,"full_content":"Hola"}\n\n',
      }),
    )
    await page.route('/api/audio/tts/**', (route) =>
      route.fulfill({ status: 200, body: '' }),
    )

    await expect(page.getByText(mockScenario.title)).toBeVisible()
    await page.getByRole('button', { name: /start chat/i }).click()
    await expect(page).toHaveURL(`/chat/${mockConversation.id}`)
  })

  test('shows error banner when start chat fails', async ({ page }) => {
    await page.route('/api/conversations', (route) =>
      route.fulfill({ status: 500, json: { detail: 'Could not create conversation' } }),
    )
    await expect(page.getByText(mockScenario.title)).toBeVisible()
    await page.getByRole('button', { name: /start chat/i }).click()
    await expect(page.getByRole('alert')).toContainText('Could not create conversation')
  })

  test('custom prompt section is collapsed by default', async ({ page }) => {
    await expect(page.locator('#custom-prompt')).not.toBeVisible()
  })

  test('expands custom prompt section on button click', async ({ page }) => {
    await page.getByRole('button', { name: /write your own scenario/i }).click()
    await expect(page.locator('#custom-prompt')).toBeVisible()
  })

  test('collapses custom prompt section on second click', async ({ page }) => {
    const toggle = page.getByRole('button', { name: /write your own scenario/i })
    await toggle.click()
    await expect(page.locator('#custom-prompt')).toBeVisible()
    await toggle.click()
    await expect(page.locator('#custom-prompt')).not.toBeVisible()
  })

  test('custom chat start button is disabled when prompt is empty', async ({ page }) => {
    await page.getByRole('button', { name: /write your own scenario/i }).click()
    const startButton = page.getByRole('button', { name: /start chat/i }).last()
    await expect(startButton).toBeDisabled()
  })

  test('custom chat start navigates to chat page', async ({ page }) => {
    await page.route('/api/settings', (route) =>
      route.fulfill({ json: { llm_model: 'llama3.1', target_language: 'Spanish', native_language: 'English', tts_voice: '', suggestion_count: 3, updated_at: '' } }),
    )
    await page.route('/api/conversations/1', (route) =>
      route.fulfill({ json: mockConversation }),
    )
    await page.route('/api/chat/1/open', (route) =>
      route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: 'data: {"done":true,"message_id":1,"full_content":"Hola"}\n\n',
      }),
    )
    await page.route('/api/audio/tts/**', (route) =>
      route.fulfill({ status: 200, body: '' }),
    )

    await page.getByRole('button', { name: /write your own scenario/i }).click()
    await page.locator('#custom-prompt').fill(
      'You are a taxi driver who only speaks Spanish.',
    )
    await page.getByRole('button', { name: /start chat/i }).last().click()
    await expect(page).toHaveURL(`/chat/${mockConversation.id}`)
  })

  test('refresh button shows error banner on API failure', async ({ page }) => {
    await expect(page.getByText(mockScenario.title)).toBeVisible()
    await page.route('/api/scenarios/next**', (route) =>
      route.fulfill({ status: 500, json: { detail: 'Failed to refresh' } }),
    )
    await page.getByRole('button', { name: /refresh/i }).click()
    await expect(page.getByRole('alert')).toContainText('Failed to refresh')
  })
})
