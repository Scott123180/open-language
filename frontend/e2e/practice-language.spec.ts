import { test, expect, type Page } from '@playwright/test'
import {
  GERMAN_VOICE_UNAVAILABLE_MESSAGE,
  mockConversationLevelsApi,
  mockGermanChatApis,
  mockGermanConversation,
  mockHomeApis,
  mockLlmProviders,
  mockPracticeLanguagesApi,
  mockPracticeLanguagesGermanVoiceMissing,
  mockSettings,
  mockVoices,
  stubMicrophone,
} from './fixtures'

const SETTINGS_URL = '/settings'
const GERMAN_CHAT_URL = `/chat/${mockGermanConversation.id}`

type StoredSettings = typeof mockSettings

/** A `/api/settings` route that keeps what is PUT, and records every PUT body. */
async function statefulSettings(page: Page, initial: StoredSettings = mockSettings) {
  const state = { settings: { ...initial }, puts: [] as Record<string, unknown>[] }
  await page.route('/api/settings', (route) => {
    if (route.request().method() === 'PUT') {
      const body = route.request().postDataJSON()
      state.puts.push(body)
      state.settings = { ...state.settings, ...body }
    }
    return route.fulfill({ json: state.settings })
  })
  await page.route('/api/settings/voices', (route) => route.fulfill({ json: mockVoices }))
  return state
}

async function openSettings(page: Page, initial: StoredSettings = mockSettings) {
  await mockLlmProviders(page)
  await mockConversationLevelsApi(page)
  await mockPracticeLanguagesApi(page)
  const state = await statefulSettings(page, initial)
  await page.goto(SETTINGS_URL)
  await expect(page.getByRole('group', { name: 'Practice language' })).toBeVisible()
  return state
}

const voiceOptions = (page: Page) => page.getByLabel('Voice').locator('option')

test.describe('Practice language — Settings', () => {
  test('choosing German lists only German voices, with Thorsten selected', async ({ page }) => {
    await openSettings(page)

    await page.getByRole('radio', { name: 'German' }).check()

    await expect(voiceOptions(page)).toHaveText(['Thorsten (Germany)', 'Kerstin (Germany)'])
    await expect(page.getByLabel('Voice')).toHaveValue('de_DE-thorsten-medium')
  })

  test('saving sends the language and its voice together', async ({ page }) => {
    const state = await openSettings(page)

    await page.getByRole('radio', { name: 'German' }).check()
    await page.getByRole('button', { name: /save/i }).click()

    await expect.poll(() => state.puts.length).toBe(1)
    expect(state.puts[0]).toMatchObject({
      target_language: 'de',
      tts_voice: 'de_DE-thorsten-medium',
    })
  })

  test('the level and correction warnings still show', async ({ page }) => {
    await openSettings(page)

    await page.getByRole('radio', { name: 'German' }).check()

    await expect(page.getByText('Corrections are experimental')).toBeVisible()
    await expect(page.getByRole('note', { name: 'Level accuracy' })).toBeVisible()
  })
})

test.describe('Practice language — Home', () => {
  test('names the practice language', async ({ page }) => {
    await mockHomeApis(page)
    await page.route('/api/settings', (route) =>
      route.fulfill({ json: { ...mockSettings, target_language: 'de' } }),
    )

    await page.goto('/')

    await expect(page.getByText('Practising German')).toBeVisible()
  })
})

test.describe('Practice language — a German conversation', () => {
  test('the header shows German and offers no language control', async ({ page }) => {
    await mockGermanChatApis(page)

    await page.goto(GERMAN_CHAT_URL)

    const header = page.locator('header')
    await expect(header.getByText('German', { exact: true })).toBeVisible()
    await expect(header.getByRole('combobox', { name: /language/i })).toHaveCount(0)
  })

  test('the expression helper is labelled English → German', async ({ page }) => {
    await mockGermanChatApis(page)
    await page.goto(GERMAN_CHAT_URL)
    await expect(page.getByLabel('Type a message')).toBeVisible()

    await page.getByRole('button', { name: 'Open expression helper' }).click()

    await expect(page.getByText('English → German')).toBeVisible()
  })

  test('speech is transcribed as German while Spanish is selected', async ({ page }) => {
    const languages: string[] = []
    await stubMicrophone(page)
    await mockGermanChatApis(page)
    await page.route('/api/audio/transcribe', (route) => {
      languages.push(route.request().postData()?.match(/name="language"\r\n\r\n(\w+)/)?.[1] ?? '')
      return route.fulfill({
        json: { text: 'Hallo', detected_language: 'de', confidence: 0.9, is_low_confidence: false },
      })
    })
    await page.route(`/api/chat/${mockGermanConversation.id}/message`, (route) =>
      route.fulfill({ status: 200, headers: { 'Content-Type': 'text/event-stream' }, body: '' }),
    )
    await page.goto(GERMAN_CHAT_URL)
    await expect(page.getByLabel('Type a message')).toBeVisible()

    await page.getByRole('button', { name: /record|microphone/i }).click()
    await page.getByRole('button', { name: /stop|recording/i }).click()

    await expect.poll(() => languages).toEqual(['de'])
  })

  test('with the German voice missing, a notice shows and nothing is played', async ({ page }) => {
    const { ttsRequests } = await mockGermanChatApis(page, mockPracticeLanguagesGermanVoiceMissing)

    await page.goto(GERMAN_CHAT_URL)

    await expect(page.getByRole('status').filter({ hasText: GERMAN_VOICE_UNAVAILABLE_MESSAGE })).toBeVisible()
    await expect(page.getByText('Guten Tag!')).toBeVisible()
    await page.waitForTimeout(300)
    expect(ttsRequests).toEqual([])
  })
})
