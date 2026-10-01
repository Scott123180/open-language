import { test, expect } from '@playwright/test'
import {
  TOO_EARLY_SUMMARY,
  lineFrame,
  makeLineSseBody,
  mockChatApis,
  mockLineStream,
  mockPodcastApis,
  mockSummarySettings,
  summaryFixture,
} from './fixtures'

test.describe('Conversation summary', () => {
  test('a roleplay summary opens in the conversations language', async ({ page }) => {
    await mockChatApis(page)
    await page.route('/api/conversations/1/summary', (route) => route.fulfill({ json: summaryFixture() }))
    await page.goto('/chat/1')

    await page.getByRole('button', { name: 'Summary' }).click()

    const panel = page.getByRole('region', { name: 'Conversation summary' })
    await expect(panel.getByText('Pides un café con leche.')).toBeVisible()
    await expect(panel.getByRole('radio', { name: 'Spanish' })).toBeChecked()
  })

  test('says when there is nothing to summarise yet', async ({ page }) => {
    await mockChatApis(page)
    await page.route('/api/conversations/1/summary', (route) => route.fulfill({ json: TOO_EARLY_SUMMARY }))
    await page.goto('/chat/1')

    await page.getByRole('button', { name: 'Summary' }).click()

    await expect(page.getByText(TOO_EARLY_SUMMARY.message)).toBeVisible()
  })

  test('switches to English and back, and remembers English in another conversation', async ({ page }) => {
    await mockChatApis(page)
    const settings = await mockSummarySettings(page)
    await page.route('/api/conversations/*/summary', (route) => route.fulfill({ json: summaryFixture() }))
    await page.goto('/chat/1')
    await page.getByRole('button', { name: 'Summary' }).click()
    const panel = page.getByRole('region', { name: 'Conversation summary' })
    await expect(panel.getByText('Pides un café con leche.')).toBeVisible()

    await panel.getByRole('radio', { name: 'English' }).click()
    await expect(panel.getByText('You order a white coffee.')).toBeVisible()
    await panel.getByRole('radio', { name: 'Spanish' }).click()
    await expect(panel.getByText('Pides un café con leche.')).toBeVisible()
    await panel.getByRole('radio', { name: 'English' }).click()
    await expect.poll(() => settings.puts.at(-1)).toEqual({ summary_language: 'native' })

    await mockPodcastApis(page)
    await mockSummarySettings(page, 'native')
    await page.goto('/podcasts/episodes/57')
    await page.getByRole('button', { name: 'Summary' }).click()
    await expect(page.getByRole('region', { name: 'Conversation summary' }).getByText('You order a white coffee.')).toBeVisible()
  })

  test('a podcast summary names the hosts', async ({ page }) => {
    await mockPodcastApis(page)
    await mockLineStream(page, 'next', [makeLineSseBody(lineFrame({ message_id: 901, host_id: 11, content: '¡Hola!', intent: 'open', invites_learner: true }, 'learner'))])
    const points = [{ conversation_language: 'Lucía cocina paella.', english: 'Lucía cooks paella.' }]
    await page.route('/api/conversations/57/summary', (route) => route.fulfill({ json: summaryFixture(57, points) }))
    await page.goto('/podcasts/episodes/57')

    await page.getByRole('button', { name: 'Summary' }).click()

    await expect(page.getByText('Lucía cocina paella.')).toBeVisible()
  })

  test('closing the panel leaves the episode exactly where it was', async ({ page }) => {
    await mockPodcastApis(page)
    const next = await mockLineStream(page, 'next', [makeLineSseBody(lineFrame({ message_id: 901, host_id: 11, content: '¡Hola!', intent: 'open', invites_learner: true }, 'learner'))])
    const message = await mockLineStream(page, 'message', [''])
    await page.route('/api/conversations/57/summary', (route) => route.fulfill({ json: summaryFixture(57) }))
    await page.goto('/podcasts/episodes/57')
    await expect(page.getByText('¡Hola!')).toBeVisible()
    const nextCalls = next.requests.length

    await page.getByRole('button', { name: 'Summary' }).click()
    await expect(page.getByRole('region', { name: 'Conversation summary' })).toBeVisible()
    await page.getByRole('button', { name: 'Summary' }).click()

    await expect(page.getByRole('region', { name: 'Conversation summary' })).toHaveCount(0)
    await expect(page.getByText('¡Hola!')).toBeVisible()
    await expect(page.getByRole('status').filter({ hasText: 'Your turn' })).toBeVisible()
    expect(next.requests.length).toBe(nextCalls)
    expect(message.requests).toHaveLength(0)
  })
})
