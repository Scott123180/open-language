import { test, expect } from '@playwright/test'
import {
  mockSettings,
  mockConversation,
  makeOpenSseBody,
  makeMessageSseBody,
  makeHelperSseBody,
} from './fixtures'

const CHAT_URL = '/chat/1'
const OPEN_SSE_BODY = makeOpenSseBody(
  ['¡Hola', '! ¿Cómo', ' estás?'],
  1,
  '¡Hola! ¿Cómo estás?',
)

async function setupChatRoutes(page: import('@playwright/test').Page) {
  await page.route('/api/settings', (route) =>
    route.fulfill({ json: mockSettings }),
  )
  await page.route('/api/conversations/1', (route) => {
    if (route.request().method() === 'PATCH') {
      return route.fulfill({ json: { ...mockConversation, status: 'completed' } })
    }
    return route.fulfill({ json: mockConversation })
  })
  await page.route('/api/chat/1/open', (route) =>
    route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'text/event-stream' },
      body: OPEN_SSE_BODY,
    }),
  )
  await page.route('/api/audio/tts/**', (route) =>
    route.fulfill({ status: 200, body: '' }),
  )
  await page.route('/api/chat/1/suggestions', (route) =>
    route.fulfill({ json: { suggestions: ['Quiero un café.', 'Necesito ayuda.', '¿Cuánto cuesta?'] } }),
  )
}

test.describe('Chat page', () => {
  test.beforeEach(async ({ page }) => {
    await setupChatRoutes(page)
    await page.goto(CHAT_URL)
  })

  test('shows Chat heading', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Chat' })).toBeVisible()
  })

  test('shows scenario title in subheader', async ({ page }) => {
    await expect(page.getByText(mockConversation.scenario_title)).toBeVisible()
  })

  test('shows End Chat button', async ({ page }) => {
    await expect(page.getByRole('button', { name: 'End Chat' })).toBeVisible()
  })

  test('streams opening message into chat', async ({ page }) => {
    await expect(page.getByText('¡Hola! ¿Cómo estás?')).toBeVisible()
  })

  test('text input appears after opening message completes', async ({ page }) => {
    await expect(page.getByLabel('Type a message')).toBeVisible()
  })

  test('send button is disabled when text input is empty', async ({ page }) => {
    await expect(page.getByLabel('Type a message')).toBeVisible()
    await expect(page.getByRole('button', { name: /send/i })).toBeDisabled()
  })

  test('send button becomes enabled when text is typed', async ({ page }) => {
    await page.getByLabel('Type a message').fill('Hola')
    await expect(page.getByRole('button', { name: /send/i })).toBeEnabled()
  })

  test('sends message via Send button and shows user and assistant messages', async ({
    page,
  }) => {
    await page.route(
      '/api/chat/1/message',
      (route) =>
        route.fulfill({
          status: 200,
          headers: { 'Content-Type': 'text/event-stream' },
          body: makeMessageSseBody(10, ['Claro,', ' ¡con', ' gusto!'], 11),
        }),
    )

    await page.getByLabel('Type a message').fill('Quiero un café')
    await page.getByRole('button', { name: /send/i }).click()

    await expect(page.getByText('Quiero un café')).toBeVisible()
    await expect(page.getByText('Claro, ¡con gusto!')).toBeVisible()
  })

  test('sends message via Enter key', async ({ page }) => {
    await page.route(
      '/api/chat/1/message',
      (route) =>
        route.fulfill({
          status: 200,
          headers: { 'Content-Type': 'text/event-stream' },
          body: makeMessageSseBody(10, ['De', ' nada.'], 11),
        }),
    )

    await page.getByLabel('Type a message').fill('Gracias')
    await page.getByLabel('Type a message').press('Enter')

    await expect(page.getByText('Gracias')).toBeVisible()
    await expect(page.getByText('De nada.')).toBeVisible()
  })

  test('clears text input after sending', async ({ page }) => {
    await page.route('/api/chat/1/message', (route) =>
      route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: makeMessageSseBody(10, ['Ok.'], 11),
      }),
    )

    const input = page.getByLabel('Type a message')
    await input.fill('Hello')
    await page.getByRole('button', { name: /send/i }).click()
    await expect(input).toHaveValue('')
  })

  test('shows error banner when opening stream fails', async ({ page }) => {
    await page.route('/api/chat/1/open', (route) =>
      route.fulfill({ status: 500 }),
    )
    await page.goto(CHAT_URL)
    await expect(page.getByRole('alert')).toBeVisible()
  })

  test('dismisses error banner', async ({ page }) => {
    await page.route('/api/chat/1/open', (route) =>
      route.fulfill({ status: 500 }),
    )
    await page.goto(CHAT_URL)
    await page.getByRole('button', { name: /dismiss/i }).click()
    await expect(page.getByRole('alert')).not.toBeVisible()
  })

  test('shows error banner when message stream fails', async ({ page }) => {
    await page.route('/api/chat/1/message', (route) =>
      route.fulfill({ status: 503 }),
    )
    await page.getByLabel('Type a message').fill('Test')
    await page.getByRole('button', { name: /send/i }).click()
    await expect(page.getByRole('alert')).toBeVisible()
  })

  test('End Chat navigates back to home', async ({ page }) => {
    await page.route('/api/scenarios/current', (route) =>
      route.fulfill({
        json: { id: 'scenario-1', title: 'Coffee Shop', description: 'Cafe scene' },
      }),
    )
    await page.getByRole('button', { name: 'End Chat' }).click()
    await expect(page).toHaveURL('/')
    await expect(page.getByRole('heading', { name: 'Open Language' })).toBeVisible()
  })

  test('chat messages area is labeled', async ({ page }) => {
    await expect(page.getByRole('region', { name: 'Chat messages' })).toBeVisible()
  })

  test('expression helper button is visible in footer', async ({ page }) => {
    await expect(page.getByRole('button', { name: /open expression helper/i })).toBeVisible()
  })

  test('expression helper opens when toggled', async ({ page }) => {
    await page.route('/api/chat/helper', (route) =>
      route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: makeHelperSseBody(['Try:', ' "¡Encantado!"']),
      }),
    )
    await page.getByRole('button', { name: /open expression helper/i }).click()
    // Panel close button uses "Close Expression Helper" (capital E)
    await expect(
      page.getByRole('button', { name: 'Close Expression Helper', exact: true }),
    ).toBeVisible()
  })

  test('expression helper closes via close button', async ({ page }) => {
    await page.getByRole('button', { name: /open expression helper/i }).click()
    await expect(
      page.getByRole('button', { name: 'Close Expression Helper', exact: true }),
    ).toBeVisible()
    await page.getByRole('button', { name: 'Close Expression Helper', exact: true }).click()
    await expect(page.getByRole('button', { name: /open expression helper/i })).toBeVisible()
  })

  test('suggested responses panel toggle is visible', async ({ page }) => {
    await expect(page.getByRole('button', { name: /show suggestions/i })).toBeVisible()
  })

  test('expanding suggestions loads and shows options', async ({ page }) => {
    await page.getByRole('button', { name: /show suggestions/i }).click()
    await expect(page.getByText('Quiero un café.')).toBeVisible()
    await expect(page.getByText('Necesito ayuda.')).toBeVisible()
  })

  test('record button is visible in footer', async ({ page }) => {
    await expect(page.getByRole('button', { name: /record|microphone|🎤/i })).toBeVisible()
  })

  test('input is disabled while streaming opening message', async ({ page }) => {
    // Navigate to a fresh page with a slow SSE stream
    await page.route('/api/chat/1/open', async (route) => {
      await new Promise((r) => setTimeout(r, 500))
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: makeOpenSseBody(['Hola'], 1, 'Hola'),
      })
    })
    await page.goto(CHAT_URL)

    // Footer input should not yet be rendered (openingDone = false)
    await expect(page.getByLabel('Type a message')).not.toBeVisible()
  })
})

test.describe('Chat page — learning tools', () => {
  test.beforeEach(async ({ page }) => {
    await setupChatRoutes(page)
    // Seed a second message via mock so we have a completed assistant message to interact with
    await page.route('/api/chat/1/message', (route) =>
      route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: makeMessageSseBody(10, ['Muy', ' bien.'], 11),
      }),
    )
    await page.goto(CHAT_URL)
    // Wait for the opening message to finish
    await expect(page.getByLabel('Type a message')).toBeVisible()
  })

  test('translate button appears on completed assistant message', async ({ page }) => {
    await expect(page.getByRole('button', { name: /translate/i }).first()).toBeVisible()
  })

  test('translate button fetches and shows translation', async ({ page }) => {
    await page.route('/api/learning/translate', (route) =>
      route.fulfill({ json: { result: 'Hello! How are you?', cached: false } }),
    )
    await page.getByRole('button', { name: /translate/i }).first().click()
    await expect(page.getByText('Hello! How are you?')).toBeVisible()
  })

  test('send a user message and grammar button appears', async ({ page }) => {
    await page.getByLabel('Type a message').fill('Yo quiero café')
    await page.getByRole('button', { name: /send/i }).click()
    await expect(page.getByText('Yo quiero café')).toBeVisible()
    // Grammar check only shows for user messages
    await expect(page.getByRole('button', { name: /grammar/i }).first()).toBeVisible()
  })

  test('grammar check fetches and shows result', async ({ page }) => {
    await page.route('/api/learning/grammar', (route) =>
      route.fulfill({ json: { result: 'Your grammar looks great!', cached: false } }),
    )
    await page.getByLabel('Type a message').fill('Yo quiero café')
    await page.getByRole('button', { name: /send/i }).click()
    await expect(page.getByText('Yo quiero café')).toBeVisible()
    await page.getByRole('button', { name: /grammar/i }).first().click()
    await expect(page.getByText('Your grammar looks great!')).toBeVisible()
  })

  test('play slower button appears on completed assistant message', async ({ page }) => {
    await expect(page.getByRole('button', { name: /slower/i }).first()).toBeVisible()
  })

  test('replay button appears on completed assistant message', async ({ page }) => {
    await expect(page.getByRole('button', { name: /replay/i }).first()).toBeVisible()
  })
})
