import { test, expect } from '@playwright/test'
import {
  episodeFixture,
  lineFrame,
  makeLineSseBody,
  mockLineStream,
  mockPodcastApis,
} from './fixtures'

const OPENING = { message_id: 901, host_id: 11, content: '¡Bienvenidos a Weekend Food Talk! ¿Qué cocinaste?', intent: 'open', invites_learner: true }
const REPLY = { message_id: 903, host_id: 11, content: '¡Qué rica! ¿Con marisco?', intent: 'discuss', invites_learner: true }
const SIGN_OFF = { message_id: 905, host_id: 11, content: '¡Gracias por venir! ¡Hasta pronto!', intent: 'sign_off' }

test.describe('Podcast episode — One host', () => {
  test('the opening, a reply, and the sign-off', async ({ page }) => {
    await mockPodcastApis(page)
    await mockLineStream(page, 'next', [makeLineSseBody(lineFrame(OPENING, 'learner'))])
    const saved = { event: 'user_message_saved', message_id: 902 }
    const message = await mockLineStream(page, 'message', [makeLineSseBody([saved, ...lineFrame(REPLY, 'learner')])])
    await mockLineStream(page, 'end', [makeLineSseBody(lineFrame(SIGN_OFF, 'finished'))])
    await page.goto('/podcasts/episodes/57')

    await expect(page.getByText(OPENING.content)).toBeVisible()
    await expect(page.getByRole('status').filter({ hasText: 'Your turn' })).toBeVisible()
    await page.getByLabel('Type a message').fill('Hice una paella.')
    await page.getByRole('button', { name: 'Send message' }).click()
    await expect(page.getByText('Hice una paella.')).toBeVisible()
    await expect(page.getByText(REPLY.content)).toBeVisible()
    expect(message.requests[0]).toMatchObject({ content: 'Hice una paella.', input_source: 'keyboard' })

    await page.getByRole('button', { name: 'End episode' }).click()
    await expect(page.getByText(SIGN_OFF.content)).toBeVisible()
    await expect(page.getByText('Episode finished')).toBeVisible()
    await expect(page.getByLabel('Type a message')).toHaveCount(0)
  })

  test('the host name is shown above each line', async ({ page }) => {
    await mockPodcastApis(page)
    await mockLineStream(page, 'next', [makeLineSseBody(lineFrame(OPENING, 'learner'))])
    await page.goto('/podcasts/episodes/57')

    const transcript = page.getByRole('region', { name: 'Episode lines' })
    await expect(transcript.getByText('Lucía')).toBeVisible()
    await expect(transcript.getByText(OPENING.content)).toBeVisible()
  })

  test('a provider failure shows its message and Retry produces the line', async ({ page }) => {
    await mockPodcastApis(page)
    await mockLineStream(page, 'next', [
      makeLineSseBody([{ error: 'The AI is not responding. Please try again.' }]),
      makeLineSseBody(lineFrame(OPENING, 'learner')),
    ])
    await page.goto('/podcasts/episodes/57')

    await expect(page.getByText('The AI is not responding. Please try again.')).toBeVisible()
    await page.getByRole('button', { name: 'Retry' }).click()

    await expect(page.getByText(OPENING.content)).toBeVisible()
    await expect(page.getByText('The AI is not responding. Please try again.')).toHaveCount(0)
  })

  test('a host without a voice is reported and the line stays readable', async ({ page }) => {
    const episode = episodeFixture('one_host')
    const silent = { ...episode.hosts[0], is_voice_available: false, voice_unavailable_message: "Lucía's voice isn't installed, so Lucía's lines can't be read aloud." }
    await mockPodcastApis(page, { episode: { ...episode, hosts: [silent], turn: 'learner', awaiting: null, lines: [{ ...OPENING, speaker: 'host', is_revealed: false, created_at: '2026-09-28T10:00:00Z' }] } })
    await page.goto('/podcasts/episodes/57')

    await expect(page.getByText(silent.voice_unavailable_message)).toBeVisible()
    await expect(page.getByText(OPENING.content)).toBeVisible()
  })
})

test.describe('Podcast episode — Listen', () => {
  const listen = () => ({ ...episodeFixture('listen') })
  const LUCIA_LINE = { message_id: 901, host_id: 11, content: '¡Bienvenidos a Weekend Food Talk!', intent: 'open' }
  const MARCO_LINE = { message_id: 902, host_id: 12, content: 'Hola, soy Marco.', intent: 'greet' }
  const LAST_LINE = { message_id: 903, host_id: 11, content: '¡Hasta la próxima!', intent: 'sign_off' }

  async function listenTo(page: import('@playwright/test').Page, isShowTextOn = false) {
    await mockPodcastApis(page, {
      episode: listen(),
      preferences: { last_format: 'listen', is_show_text_on: isShowTextOn, interests: [], learner_name: null },
    })
    const reveals: string[] = []
    await page.route('/api/podcasts/episodes/57/lines/*/reveal', (route) => {
      reveals.push(route.request().url())
      return route.fulfill({ status: 204 })
    })
    await mockLineStream(page, 'next', [
      makeLineSseBody(lineFrame(LUCIA_LINE, 'hosts', 'continue')),
      makeLineSseBody(lineFrame(MARCO_LINE, 'hosts', 'continue')),
      makeLineSseBody(lineFrame(LAST_LINE, 'finished')),
    ])
    await page.goto('/podcasts/episodes/57')
    return { reveals }
  }

  test('a line shows its speaker with its words hidden, and a tap reveals them', async ({ page }) => {
    const { reveals } = await listenTo(page)

    const hidden = page.getByRole('button', { name: "Show Lucía's line" })
    await expect(hidden).toBeVisible()
    await expect(page.getByText(LUCIA_LINE.content)).toHaveCount(0)
    await hidden.click()

    await expect(page.getByText(LUCIA_LINE.content)).toBeVisible()
    expect(reveals[0]).toContain('/lines/901/reveal')
  })

  test('Continue plays the next line and nothing asks the learner to speak', async ({ page }) => {
    await listenTo(page)
    await expect(page.getByRole('button', { name: "Show Lucía's line" })).toBeVisible()

    await page.getByRole('button', { name: 'Continue' }).click()

    await expect(page.getByRole('button', { name: "Show Marco's line" })).toBeVisible()
    await expect(page.getByLabel('Type a message')).toHaveCount(0)
  })

  test('Show text shows every line and is saved', async ({ page }) => {
    await listenTo(page)
    const saved = page.waitForRequest((r) => r.url().endsWith('/api/podcasts/preferences') && r.method() === 'PUT')
    await page.unroute('/api/podcasts/preferences')
    await page.route('/api/podcasts/preferences', (route) =>
      route.fulfill({ json: { last_format: 'listen', is_show_text_on: route.request().method() === 'PUT', interests: [], learner_name: null } }),
    )

    await page.getByRole('switch', { name: 'Show text' }).click()

    expect((await saved).postDataJSON()).toEqual({ is_show_text_on: true })
    await expect(page.getByText(LUCIA_LINE.content)).toBeVisible()
  })

  test('with Show text remembered, a new Listen episode starts with its words shown', async ({ page }) => {
    await listenTo(page, true)

    await expect(page.getByText(LUCIA_LINE.content)).toBeVisible()
    await expect(page.getByRole('switch', { name: 'Show text' })).toBeChecked()
  })

  test('Continue through to the sign-off finishes the episode', async ({ page }) => {
    await listenTo(page, true)
    await expect(page.getByText(LUCIA_LINE.content)).toBeVisible()

    await page.getByRole('button', { name: 'Continue' }).click()
    await expect(page.getByText(MARCO_LINE.content)).toBeVisible()
    await page.getByRole('button', { name: 'Continue' }).click()

    await expect(page.getByText(LAST_LINE.content)).toBeVisible()
    await expect(page.getByText('Episode finished')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Continue' })).toHaveCount(0)
  })
})

test.describe('Podcast episode — small screens', () => {
  test('the header and the summary bar fit a 360 px screen', async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 740 })
    await mockPodcastApis(page)
    await mockLineStream(page, 'next', [makeLineSseBody(lineFrame(OPENING, 'learner'))])
    await page.goto('/podcasts/episodes/57')
    await expect(page.getByText(OPENING.content)).toBeVisible()

    const overflow = await page.locator('header').evaluate((el) => el.scrollWidth - el.clientWidth)
    const summary = await page.getByRole('button', { name: 'Summary' }).boundingBox()

    expect(overflow).toBe(0)
    expect(summary!.x + summary!.width).toBeLessThanOrEqual(360)
  })
})

test.describe('Podcast episode — Panel', () => {
  const LUCIA = { message_id: 901, host_id: 11, content: '¡Bienvenidos!', intent: 'open' }
  const MARCO_ASKS = { message_id: 902, host_id: 12, content: 'Y tú, ¿qué opinas?', intent: 'greet', invites_learner: true }
  const LUCIA_AGAIN = { message_id: 904, host_id: 11, content: 'Pues yo creo que sí.', intent: 'discuss' }
  const MARCO_ANSWERS = { message_id: 906, host_id: 12, content: 'Te respondo yo.', intent: 'discuss', invites_learner: true }
  const panelFrame = (line: typeof LUCIA, turn: string, awaiting: string | null, flags = {}) => {
    const [lineEvent, done] = lineFrame(line, turn, awaiting)
    return makeLineSseBody([lineEvent, { ...done, ...flags }])
  }

  async function openPanel(page: import('@playwright/test').Page) {
    await mockPodcastApis(page, { episode: { ...episodeFixture('panel'), format_label: 'Panel' } })
    const next = await mockLineStream(page, 'next', [
      panelFrame(LUCIA, 'hosts', 'continue', { can_jump_in: true }),
      panelFrame(MARCO_ASKS, 'learner', null, { can_pass: true }),
    ])
    await page.goto('/podcasts/episodes/57')
    await expect(page.getByText(LUCIA.content)).toBeVisible()
    return { next }
  }

  test('Continue plays the next line and the banner follows the turn', async ({ page }) => {
    await openPanel(page)
    await expect(page.getByRole('status').filter({ hasText: 'Lucía is speaking' })).toBeVisible()

    await page.getByRole('button', { name: 'Continue' }).click()

    await expect(page.getByText(MARCO_ASKS.content)).toBeVisible()
    await expect(page.getByRole('status').filter({ hasText: 'Your turn' })).toBeVisible()
  })

  test('Pass lets the hosts carry on', async ({ page }) => {
    await openPanel(page)
    await page.getByRole('button', { name: 'Continue' }).click()
    const passed = await mockLineStream(page, 'pass', [panelFrame(LUCIA_AGAIN, 'hosts', 'continue', { can_jump_in: true })])

    await page.getByRole('button', { name: 'Pass' }).click()

    await expect(page.getByText(LUCIA_AGAIN.content)).toBeVisible()
    expect(passed.requests).toHaveLength(1)
    await expect(page.getByRole('button', { name: 'Continue' })).toBeVisible()
  })

  test('Jump in opens the input while the hosts are talking', async ({ page }) => {
    await openPanel(page)
    const saved = { event: 'user_message_saved', message_id: 905 }
    const message = await mockLineStream(page, 'message', [makeLineSseBody([saved, ...lineFrame(MARCO_ANSWERS, 'learner')])])

    await page.getByRole('button', { name: 'Jump in' }).click()
    await page.getByLabel('Type a message').fill('¡Una pregunta!')
    await page.getByRole('button', { name: 'Send message' }).click()

    await expect(page.getByText('¡Una pregunta!')).toBeVisible()
    expect(message.requests[0]).toMatchObject({ content: '¡Una pregunta!' })
  })

  test('a message naming a host is answered by that host', async ({ page }) => {
    await openPanel(page)
    await page.getByRole('button', { name: 'Continue' }).click()
    const saved = { event: 'user_message_saved', message_id: 905 }
    await mockLineStream(page, 'message', [makeLineSseBody([saved, ...lineFrame(MARCO_ANSWERS, 'learner')])])

    await page.getByLabel('Type a message').fill('Marco, ¿y tú?')
    await page.getByRole('button', { name: 'Send message' }).click()

    const transcript = page.getByRole('region', { name: 'Episode lines' })
    await expect(transcript.getByText(MARCO_ANSWERS.content)).toBeVisible()
    const speakerAbove = transcript.locator(
      `xpath=//span[normalize-space()="Marco"]/following-sibling::*[1][contains(., "${MARCO_ANSWERS.content}")]`,
    )
    await expect(speakerAbove).toHaveCount(1)
  })
})
