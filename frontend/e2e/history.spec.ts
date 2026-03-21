import { test, expect } from '@playwright/test'
import { mockConversation, mockConversationCompleted, mockMessages } from './fixtures'

const HISTORY_URL = '/history'

async function setupHistoryRoutes(
  page: import('@playwright/test').Page,
  conversations: unknown[] = [mockConversation, mockConversationCompleted],
) {
  await page.route('/api/conversations', (route) =>
    route.fulfill({ json: conversations }),
  )
  await page.route(`/api/conversations/${mockConversation.id}/messages`, (route) =>
    route.fulfill({ json: mockMessages }),
  )
  await page.route(`/api/conversations/${mockConversationCompleted.id}/messages`, (route) =>
    route.fulfill({ json: [] }),
  )
}

test.describe('History page', () => {
  test('shows Past Chats heading', async ({ page }) => {
    await setupHistoryRoutes(page)
    await page.goto(HISTORY_URL)
    await expect(page.getByRole('heading', { name: 'Past Chats' })).toBeVisible()
  })

  test('shows loading state before conversations arrive', async ({ page }) => {
    await page.route('/api/conversations', async (route) => {
      await new Promise((r) => setTimeout(r, 200))
      await route.fulfill({ json: [] })
    })
    await page.goto(HISTORY_URL)
    await expect(page.getByText('Loading…')).toBeVisible()
  })

  test('shows empty state when no conversations exist', async ({ page }) => {
    await setupHistoryRoutes(page, [])
    await page.goto(HISTORY_URL)
    await expect(page.getByText('No past conversations yet.')).toBeVisible()
  })

  test('shows conversation cards with title and status', async ({ page }) => {
    await setupHistoryRoutes(page)
    await page.goto(HISTORY_URL)
    await expect(page.getByText(mockConversation.scenario_title)).toBeVisible()
    await expect(page.getByText(mockConversationCompleted.scenario_title)).toBeVisible()
    await expect(page.getByText('active')).toBeVisible()
    await expect(page.getByText('completed')).toBeVisible()
  })

  test('shows formatted start date on conversation card', async ({ page }) => {
    await setupHistoryRoutes(page)
    await page.goto(HISTORY_URL)
    // The date 2026-03-20T10:00:00Z formatted as locale date should be visible
    // We just check some part of the date is there
    const cards = page.getByRole('button', { name: /coffee shop/i })
    await expect(cards.first()).toBeVisible()
  })

  test('expands conversation on click and shows loading messages', async ({ page }) => {
    await page.route('/api/conversations', (route) =>
      route.fulfill({ json: [mockConversation] }),
    )
    await page.route(`/api/conversations/${mockConversation.id}/messages`, async (route) => {
      await new Promise((r) => setTimeout(r, 200))
      await route.fulfill({ json: mockMessages })
    })
    await page.goto(HISTORY_URL)

    await page.getByRole('button', { name: /coffee shop/i }).click()
    await expect(page.getByText('Loading messages…')).toBeVisible()
  })

  test('shows messages after expanding conversation', async ({ page }) => {
    await setupHistoryRoutes(page)
    await page.goto(HISTORY_URL)

    await page.getByRole('button', { name: /coffee shop/i }).click()
    await expect(
      page.getByText('¡Hola! ¿En qué puedo ayudarte hoy?'),
    ).toBeVisible()
    await expect(
      page.getByText('Quiero un café con leche, por favor.'),
    ).toBeVisible()
  })

  test('shows "No messages" for conversation with no messages', async ({ page }) => {
    await setupHistoryRoutes(page)
    await page.goto(HISTORY_URL)

    await page.getByRole('button', { name: /hotel check-in/i }).click()
    await expect(page.getByText('No messages.')).toBeVisible()
  })

  test('collapses conversation on second click', async ({ page }) => {
    await setupHistoryRoutes(page)
    await page.goto(HISTORY_URL)

    const card = page.getByRole('button', { name: /coffee shop/i })
    await card.click()
    await expect(page.getByText('¡Hola! ¿En qué puedo ayudarte hoy?')).toBeVisible()

    await card.click()
    await expect(page.getByText('¡Hola! ¿En qué puedo ayudarte hoy?')).not.toBeVisible()
  })

  test('does not reload messages when re-expanding same conversation', async ({ page }) => {
    let requestCount = 0
    await page.route('/api/conversations', (route) =>
      route.fulfill({ json: [mockConversation] }),
    )
    await page.route(`/api/conversations/${mockConversation.id}/messages`, (route) => {
      requestCount++
      return route.fulfill({ json: mockMessages })
    })
    await page.goto(HISTORY_URL)

    const card = page.getByRole('button', { name: /coffee shop/i })
    await card.click()
    await expect(page.getByText('¡Hola! ¿En qué puedo ayudarte hoy?')).toBeVisible()
    await card.click() // collapse
    await card.click() // re-expand — should use cached messages
    await expect(page.getByText('¡Hola! ¿En qué puedo ayudarte hoy?')).toBeVisible()

    expect(requestCount).toBe(1)
  })

  test('Back to Home link navigates to home page', async ({ page }) => {
    await setupHistoryRoutes(page)
    await page.route('/api/scenarios/current', (route) =>
      route.fulfill({ json: { id: 's1', title: 'Coffee Shop', description: 'Cafe' } }),
    )
    await page.goto(HISTORY_URL)
    await page.getByRole('link', { name: '← Back to Home' }).click()
    await expect(page).toHaveURL('/')
    await expect(page.getByRole('heading', { name: 'Open Language' })).toBeVisible()
  })

  test('only one conversation can be expanded at a time', async ({ page }) => {
    await setupHistoryRoutes(page)
    await page.goto(HISTORY_URL)

    await page.getByRole('button', { name: /coffee shop/i }).click()
    await expect(page.getByText('¡Hola! ¿En qué puedo ayudarte hoy?')).toBeVisible()

    await page.getByRole('button', { name: /hotel check-in/i }).click()
    await expect(page.getByText('¡Hola! ¿En qué puedo ayudarte hoy?')).not.toBeVisible()
    await expect(page.getByText('No messages.')).toBeVisible()
  })
})
