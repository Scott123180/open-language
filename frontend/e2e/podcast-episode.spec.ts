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
