import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'
import {
  mockSettings,
  mockFeedbackNote,
  mockRepeatRequestNote,
  emptyConversationFeedback,
  makeOpenSseBody,
  makeMessageSseBody,
  makeCorrectionSseBody,
  mockConversationLevelsApi,
  mockConversationRoutes,
  mockOpeningRoutes,
} from './fixtures'

const CHAT_URL = '/chat/1'
const OPEN_SSE_BODY = makeOpenSseBody(['¡Hola', '! ¿Cómo', ' estás?'], 1, '¡Hola! ¿Cómo estás?')

/** Chat routes with the correction mode under test. */
async function setupCorrectionRoutes(
  page: Page,
  correctionMode: 'off' | 'gentle' | 'strict',
) {
  await page.route('/api/settings', (route) =>
    route.fulfill({ json: { ...mockSettings, correction_mode: correctionMode } }),
  )
  await mockConversationLevelsApi(page)
  await mockConversationRoutes(page)
  await mockOpeningRoutes(page, OPEN_SSE_BODY)
  await page.route('/api/chat/1/suggestions', (route) =>
    route.fulfill({ json: { suggestions: ['Quiero un café.'] } }),
  )
}

/** A message stream whose frames arrive with a deliberate pause before the reply. */
function slowMessageRoute(bodyBefore: string, bodyAfter: string, delayMs: number) {
  return async (route: import('@playwright/test').Route) => {
    await new Promise((r) => setTimeout(r, delayMs))
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'text/event-stream' },
      body: bodyBefore + bodyAfter,
    })
  }
}

async function send(page: Page, text: string) {
  await page.getByLabel('Type a message').fill(text)
  await page.getByRole('button', { name: /send/i }).click()
}

test.describe('Corrective feedback — turn status (quickstart 6.1, 6.2, 6.4)', () => {
  test('shows the checking indicator while the sentence is evaluated', async ({ page }) => {
    await setupCorrectionRoutes(page, 'strict')
    await page.route('/api/chat/1/message', slowMessageRoute('', makeMessageSseBody(10, ['Claro.'], 11), 1500))
    await page.goto(CHAT_URL)
    await expect(page.getByLabel('Type a message')).toBeVisible()

    await send(page, 'Yo tener veinte años')

    await expect(page.getByText(/checking your sentence/i)).toBeVisible({ timeout: 1000 })
  })

  test('creates no assistant bubble before the first token', async ({ page }) => {
    await setupCorrectionRoutes(page, 'strict')
    await page.route('/api/chat/1/message', slowMessageRoute('', makeMessageSseBody(10, ['Claro.'], 11), 1500))
    await page.goto(CHAT_URL)
    await expect(page.getByLabel('Type a message')).toBeVisible()
    const openingBubbles = await page.getByRole('article', { name: 'AI response' }).count()

    await send(page, 'Yo tener veinte años')
    await expect(page.getByText(/checking your sentence/i)).toBeVisible()

    expect(await page.getByRole('article', { name: 'AI response' }).count()).toBe(openingBubbles)
  })

  test('clears the indicator and shows the bubble on the first token', async ({ page }) => {
    await setupCorrectionRoutes(page, 'gentle')
    await page.route('/api/chat/1/message', (route) =>
      route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: makeMessageSseBody(10, ['Ah, ', 'tienes veinte años.'], 11),
      }),
    )
    await page.goto(CHAT_URL)
    await expect(page.getByLabel('Type a message')).toBeVisible()

    await send(page, 'Yo tener veinte años')

    await expect(page.getByText('Ah, tienes veinte años.')).toBeVisible()
    await expect(page.getByText(/checking your sentence/i)).not.toBeVisible()
  })

  test('Off mode renders no indicator and keeps the send-time placeholder', async ({ page }) => {
    await setupCorrectionRoutes(page, 'off')
    await page.route('/api/chat/1/message', slowMessageRoute('', makeMessageSseBody(10, ['Claro.'], 11), 1000))
    await page.goto(CHAT_URL)
    await expect(page.getByLabel('Type a message')).toBeVisible()
    const openingBubbles = await page.getByRole('article', { name: 'AI response' }).count()

    await send(page, 'Quiero un café')
    await expect(page.getByText('Quiero un café')).toBeVisible()

    // The placeholder bubble still appears on send, exactly as it did before (SC-002).
    await expect(page.getByRole('article', { name: 'AI response' })).toHaveCount(
      openingBubbles + 1,
    )
    await expect(page.getByText(/checking your sentence/i)).not.toBeVisible()
  })

  test('Off mode never requests conversation feedback beyond the initial load', async ({
    page,
  }) => {
    let feedbackCalls = 0
    await setupCorrectionRoutes(page, 'off')
    await page.route('/api/corrections/conversations/1', (route) => {
      feedbackCalls += 1
      return route.fulfill({ json: emptyConversationFeedback })
    })
    await page.route('/api/chat/1/message', (route) =>
      route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: makeMessageSseBody(10, ['Claro.'], 11),
      }),
    )
    await page.goto(CHAT_URL)
    await expect(page.getByLabel('Type a message')).toBeVisible()

    await send(page, 'Quiero un café')
    await expect(page.getByText('Claro.')).toBeVisible()

    expect(feedbackCalls).toBe(1)
  })
})

test.describe('Corrective feedback — hydration on reload (FR-022)', () => {
  test('renders feedback stored against an earlier message', async ({ page }) => {
    await setupCorrectionRoutes(page, 'strict')
    await page.route('/api/conversations/1/messages', (route) =>
      route.fulfill({
        json: [
          {
            id: 10,
            conversation_id: 1,
            role: 'user',
            content: 'Yo tener veinte años',
            input_source: 'keyboard',
            created_at: '2026-03-20T10:01:00Z',
            tts_audio_path: null,
          },
        ],
      }),
    )
    await page.route('/api/corrections/conversations/1', (route) =>
      route.fulfill({
        json: {
          ...emptyConversationFeedback,
          awaiting_retry: true,
          consecutive_corrected_attempts: 1,
          feedback: [mockFeedbackNote],
        },
      }),
    )
    await page.goto(CHAT_URL)

    await expect(page.getByText('Yo tengo veinte años')).toBeVisible()
  })
})

test.describe('Corrective feedback — Strict mode (US1)', () => {
  test('renders the correction under the learner\'s own message', async ({ page }) => {
    await setupCorrectionRoutes(page, 'strict')
    await page.route('/api/chat/1/message', (route) =>
      route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: makeCorrectionSseBody(10, [mockFeedbackNote]),
      }),
    )
    await page.goto(CHAT_URL)
    await expect(page.getByLabel('Type a message')).toBeVisible()

    await send(page, 'Yo tener veinte años')

    const note = page.getByRole('note', { name: /learning feedback/i })
    await expect(note).toBeVisible()
    await expect(note).toContainText('Yo tengo veinte años')
    const learnerBubble = page.getByRole('article', { name: 'Your message' })
    await expect(learnerBubble).toContainText('Yo tener veinte años')
    expect(await learnerBubble.getByRole('note').count()).toBe(1)
  })

  test('the conversation does not advance', async ({ page }) => {
    await setupCorrectionRoutes(page, 'strict')
    await page.route('/api/chat/1/message', (route) =>
      route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: makeCorrectionSseBody(10, [mockFeedbackNote]),
      }),
    )
    await page.goto(CHAT_URL)
    await expect(page.getByLabel('Type a message')).toBeVisible()
    const bubblesBefore = await page.getByRole('article', { name: 'AI response' }).count()

    await send(page, 'Yo tener veinte años')
    await expect(page.getByRole('note', { name: /learning feedback/i })).toBeVisible()

    expect(await page.getByRole('article', { name: 'AI response' }).count()).toBe(bubblesBefore)
  })

  test('the composer switches to retry mode', async ({ page }) => {
    await setupCorrectionRoutes(page, 'strict')
    await page.route('/api/chat/1/message', (route) =>
      route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: makeCorrectionSseBody(10, [mockFeedbackNote]),
      }),
    )
    await page.goto(CHAT_URL)
    await expect(page.getByLabel('Type a message')).toBeVisible()

    await send(page, 'Yo tener veinte años')
    await expect(page.getByRole('note', { name: /learning feedback/i })).toBeVisible()

    await expect(page.getByLabel('Type a message')).toHaveAttribute('placeholder', 'Try again…')
  })

  test('the retry receives a character reply', async ({ page }) => {
    let turn = 0
    await setupCorrectionRoutes(page, 'strict')
    await page.route('/api/chat/1/message', (route) => {
      turn += 1
      const body =
        turn === 1
          ? makeCorrectionSseBody(10, [mockFeedbackNote])
          : makeMessageSseBody(12, ['¡Muy', ' bien!'], 13)
      return route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body,
      })
    })
    await page.goto(CHAT_URL)
    await expect(page.getByLabel('Type a message')).toBeVisible()

    await send(page, 'Yo tener veinte años')
    await expect(page.getByRole('note', { name: /learning feedback/i })).toBeVisible()
    await send(page, 'Yo tengo veinte años')

    await expect(page.getByText('¡Muy bien!')).toBeVisible()
    await expect(page.getByLabel('Type a message')).toHaveAttribute(
      'placeholder',
      'Type a message…',
    )
  })

  test('a flagged Strict turn issues no TTS request (FR-020, SC-005)', async ({ page }) => {
    const ttsRequests: string[] = []
    await setupCorrectionRoutes(page, 'strict')
    await page.route('/api/audio/tts/**', (route) => {
      ttsRequests.push(route.request().url())
      return route.fulfill({ status: 200, body: '' })
    })
    await page.route('/api/chat/1/message', (route) =>
      route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: makeCorrectionSseBody(10, [mockFeedbackNote]),
      }),
    )
    await page.goto(CHAT_URL)
    await expect(page.getByLabel('Type a message')).toBeVisible()
    // The opening message is spoken as usual; wait for it so it is not miscounted.
    await expect.poll(() => ttsRequests.length).toBeGreaterThan(0)
    const openingTtsCount = ttsRequests.length

    await send(page, 'Yo tener veinte años')
    await expect(page.getByRole('note', { name: /learning feedback/i })).toBeVisible()
    await page.waitForTimeout(500)

    expect(ttsRequests.length).toBe(openingTtsCount)
  })

  test('no assistant bubble is ever created during a flagged turn', async ({ page }) => {
    await setupCorrectionRoutes(page, 'strict')
    await page.route('/api/chat/1/message', async (route) => {
      await new Promise((r) => setTimeout(r, 600))
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: makeCorrectionSseBody(10, [mockFeedbackNote]),
      })
    })
    await page.goto(CHAT_URL)
    await expect(page.getByLabel('Type a message')).toBeVisible()
    const baseline = await page.getByRole('article', { name: 'AI response' }).count()

    await send(page, 'Yo tener veinte años')

    // Poll throughout the turn, not merely at the end (quickstart check 6.3).
    const deadline = Date.now() + 1500
    while (Date.now() < deadline) {
      expect(await page.getByRole('article', { name: 'AI response' }).count()).toBe(baseline)
      await page.waitForTimeout(50)
    }
    await expect(page.getByRole('note', { name: /learning feedback/i })).toBeVisible()
  })
})

test.describe('Corrective feedback — Gentle mode (US2)', () => {
  const gentleReply = ['Ah, ', 'tienes veinte años. ', '¿Y de dónde eres?']

  test('produces one uninterrupted reply', async ({ page }) => {
    await setupCorrectionRoutes(page, 'gentle')
    await page.route('/api/chat/1/message', (route) =>
      route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: makeMessageSseBody(10, gentleReply, 11),
      }),
    )
    await page.goto(CHAT_URL)
    await expect(page.getByLabel('Type a message')).toBeVisible()

    await send(page, 'Yo tener veinte años')

    await expect(page.getByText(gentleReply.join(''))).toBeVisible()
  })

  test('shows the checking indicator while evaluating', async ({ page }) => {
    await setupCorrectionRoutes(page, 'gentle')
    await page.route(
      '/api/chat/1/message',
      slowMessageRoute('', makeMessageSseBody(10, gentleReply, 11), 1500),
    )
    await page.goto(CHAT_URL)
    await expect(page.getByLabel('Type a message')).toBeVisible()

    await send(page, 'Yo tener veinte años')

    await expect(page.getByText(/checking your sentence/i)).toBeVisible({ timeout: 1000 })
  })

  test('never renders a feedback note', async ({ page }) => {
    await setupCorrectionRoutes(page, 'gentle')
    await page.route('/api/chat/1/message', (route) =>
      route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: makeMessageSseBody(10, gentleReply, 11),
      }),
    )
    await page.goto(CHAT_URL)
    await expect(page.getByLabel('Type a message')).toBeVisible()

    await send(page, 'Yo tener veinte años')
    await expect(page.getByText(gentleReply.join(''))).toBeVisible()

    await expect(page.getByRole('note', { name: /learning feedback/i })).toHaveCount(0)
    await expect(page.getByLabel('Type a message')).toHaveAttribute(
      'placeholder',
      'Type a message…',
    )
  })

  test('the recast reply is voiced normally (FR-021)', async ({ page }) => {
    const ttsRequests: string[] = []
    await setupCorrectionRoutes(page, 'gentle')
    await page.route('/api/audio/tts/**', (route) => {
      ttsRequests.push(route.request().url())
      return route.fulfill({ status: 200, body: '' })
    })
    await page.route('/api/chat/1/message', (route) =>
      route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: makeMessageSseBody(10, gentleReply, 11),
      }),
    )
    await page.goto(CHAT_URL)
    await expect(page.getByLabel('Type a message')).toBeVisible()

    await send(page, 'Yo tener veinte años')
    await expect(page.getByText(gentleReply.join(''))).toBeVisible()

    await expect.poll(() => ttsRequests.some((u) => u.endsWith('/api/audio/tts/11'))).toBe(true)
  })
})

/** Drive one voice turn: grant the mic, record, stop, and let transcription land. */
async function sendByVoice(page: Page) {
  await page.getByRole('button', { name: /record|microphone|🎤/i }).click()
  await page.getByRole('button', { name: /stop|recording/i }).click()
}

async function stubMicrophone(page: Page) {
  await page.addInitScript(() => {
    class FakeRecorder {
      ondataavailable: ((e: { data: Blob }) => void) | null = null
      onstop: (() => void) | null = null
      state = 'inactive'
      start() {
        this.state = 'recording'
      }
      stop() {
        this.state = 'inactive'
        this.ondataavailable?.({ data: new Blob(['x'], { type: 'audio/webm' }) })
        this.onstop?.()
      }
    }
    // @ts-expect-error test double
    window.MediaRecorder = FakeRecorder
    // @ts-expect-error test double
    window.MediaRecorder.isTypeSupported = () => true
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: {
        getUserMedia: async () => ({ getTracks: () => [{ stop() {} }] }),
      },
    })
  })
}

test.describe('Corrective feedback — low-confidence speech (US3)', () => {
  test('renders the repeat request as a note and speaks nothing', async ({ page }) => {
    const ttsRequests: string[] = []
    await stubMicrophone(page)
    await setupCorrectionRoutes(page, 'strict')
    await page.route('/api/audio/tts/**', (route) => {
      ttsRequests.push(route.request().url())
      return route.fulfill({ status: 200, body: '' })
    })
    await page.route('/api/audio/transcribe', (route) =>
      route.fulfill({
        json: {
          text: 'algo confuso',
          detected_language: 'es',
          confidence: 0.2,
          is_low_confidence: true,
        },
      }),
    )
    await page.route('/api/chat/1/message', (route) =>
      route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: makeCorrectionSseBody(10, [mockRepeatRequestNote]),
      }),
    )
    await page.goto(CHAT_URL)
    await expect(page.getByLabel('Type a message')).toBeVisible()
    await expect.poll(() => ttsRequests.length).toBeGreaterThan(0)
    const openingTtsCount = ttsRequests.length

    await sendByVoice(page)

    const note = page.getByRole('note', { name: /learning feedback/i })
    await expect(note).toBeVisible()
    await expect(note).toContainText(/could you say it again/i)
    await expect(note).not.toContainText('Yo tengo veinte años')
    await page.waitForTimeout(500)
    expect(ttsRequests.length).toBe(openingTtsCount)
  })

  test('forwards the transcription confidence on the message request', async ({ page }) => {
    let capturedBody: Record<string, unknown> | null = null
    await stubMicrophone(page)
    await setupCorrectionRoutes(page, 'strict')
    await page.route('/api/audio/transcribe', (route) =>
      route.fulfill({
        json: {
          text: 'algo confuso',
          detected_language: 'es',
          confidence: 0.31,
          is_low_confidence: true,
        },
      }),
    )
    await page.route('/api/chat/1/message', (route) => {
      capturedBody = route.request().postDataJSON()
      return route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: makeCorrectionSseBody(10, [mockRepeatRequestNote]),
      })
    })
    await page.goto(CHAT_URL)
    await expect(page.getByLabel('Type a message')).toBeVisible()

    await sendByVoice(page)
    await expect(page.getByRole('note', { name: /learning feedback/i })).toBeVisible()

    expect(capturedBody).toMatchObject({
      input_source: 'voice',
      transcription_confidence: 0.31,
    })
  })

  test('forwards a zero confidence rather than dropping it as falsy', async ({ page }) => {
    let capturedBody: Record<string, unknown> | null = null
    await stubMicrophone(page)
    await setupCorrectionRoutes(page, 'strict')
    await page.route('/api/audio/transcribe', (route) =>
      route.fulfill({
        json: {
          text: 'Thank you for watching',
          detected_language: 'es',
          confidence: 0.0,
          is_low_confidence: true,
        },
      }),
    )
    await page.route('/api/chat/1/message', (route) => {
      capturedBody = route.request().postDataJSON()
      return route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: makeCorrectionSseBody(10, [mockRepeatRequestNote]),
      })
    })
    await page.goto(CHAT_URL)
    await expect(page.getByLabel('Type a message')).toBeVisible()

    await sendByVoice(page)
    await expect(page.getByRole('note', { name: /learning feedback/i })).toBeVisible()

    expect(capturedBody).toHaveProperty('transcription_confidence', 0)
  })

  test('a typed message carries no confidence at all', async ({ page }) => {
    let capturedBody: Record<string, unknown> | null = null
    await setupCorrectionRoutes(page, 'strict')
    await page.route('/api/chat/1/message', (route) => {
      capturedBody = route.request().postDataJSON()
      return route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: makeMessageSseBody(10, ['Claro.'], 11),
      })
    })
    await page.goto(CHAT_URL)
    await expect(page.getByLabel('Type a message')).toBeVisible()

    await send(page, 'Yo tengo veinte años')
    await expect(page.getByText('Claro.')).toBeVisible()

    expect(capturedBody).not.toHaveProperty('transcription_confidence')
  })
})

test.describe('Corrective feedback — evaluation failure (SC-004a, quickstart 6.5)', () => {
  /** A timed-out evaluation reaches the client as an ordinary uncorrected turn. */
  const timedOutTurn = makeMessageSseBody(10, ['Claro,', ' ¡con gusto!'], 11)

  test('the reply still streams', async ({ page }) => {
    await setupCorrectionRoutes(page, 'strict')
    await page.route('/api/chat/1/message', slowMessageRoute('', timedOutTurn, 900))
    await page.goto(CHAT_URL)
    await expect(page.getByLabel('Type a message')).toBeVisible()

    await send(page, 'Yo tener veinte años')

    await expect(page.getByText('Claro, ¡con gusto!')).toBeVisible()
  })

  test('the checking indicator clears', async ({ page }) => {
    await setupCorrectionRoutes(page, 'strict')
    await page.route('/api/chat/1/message', slowMessageRoute('', timedOutTurn, 900))
    await page.goto(CHAT_URL)
    await expect(page.getByLabel('Type a message')).toBeVisible()

    await send(page, 'Yo tener veinte años')
    await expect(page.getByText(/checking your sentence/i)).toBeVisible()
    await expect(page.getByText('Claro, ¡con gusto!')).toBeVisible()

    await expect(page.getByText(/checking your sentence/i)).not.toBeVisible()
  })

  test('no feedback note and no error banner appear', async ({ page }) => {
    await setupCorrectionRoutes(page, 'strict')
    await page.route('/api/chat/1/message', slowMessageRoute('', timedOutTurn, 900))
    await page.goto(CHAT_URL)
    await expect(page.getByLabel('Type a message')).toBeVisible()

    await send(page, 'Yo tener veinte años')
    await expect(page.getByText('Claro, ¡con gusto!')).toBeVisible()

    await expect(page.getByRole('note', { name: /learning feedback/i })).toHaveCount(0)
    await expect(page.getByRole('alert')).toHaveCount(0)
    await expect(page.getByLabel('Type a message')).toHaveAttribute(
      'placeholder',
      'Type a message…',
    )
  })

  test('the turn ends indistinguishable from an Off-mode turn', async ({ page }) => {
    await setupCorrectionRoutes(page, 'strict')
    await page.route('/api/chat/1/message', slowMessageRoute('', timedOutTurn, 900))
    await page.goto(CHAT_URL)
    await expect(page.getByLabel('Type a message')).toBeVisible()
    const baseline = await page.getByRole('article', { name: 'AI response' }).count()

    await send(page, 'Yo tener veinte años')
    await expect(page.getByText('Claro, ¡con gusto!')).toBeVisible()

    expect(await page.getByRole('article', { name: 'AI response' }).count()).toBe(baseline + 1)
    // The composer is released, exactly as it is at the end of an Off-mode turn.
    await expect(page.getByLabel('Type a message')).toBeEnabled()
  })
})

