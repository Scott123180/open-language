import { test, expect } from '@playwright/test'
import {
  CLAUDE_UNAVAILABLE_MESSAGES,
  type ClaudeUnavailableReason,
  mockConversationLevels,
  mockConversationLevelsApi,
  mockLlmProviders,
  mockLlmProvidersClaudeUnavailable,
  mockSettings,
  mockPracticeLanguagesApi,
  mockVoices,
} from './fixtures'

const SETTINGS_URL = '/settings'

// Every Settings visit loads the provider and level catalogues; tests override them where it matters.
test.beforeEach(async ({ page }) => {
  await mockLlmProviders(page)
  await mockConversationLevelsApi(page)
})

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
  await page.route('/api/settings/voices', (route) =>
    route.fulfill({ json: mockVoices })
  )
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
    await page.route('/api/settings/voices', (route) =>
      route.fulfill({ json: mockVoices })
    )
    await page.goto(SETTINGS_URL)
    await expect(page.getByText('Loading settings…')).toBeVisible()
  })

  test('loads and displays current model', async ({ page }) => {
    await setupSettingsRoutes(page)
    await page.goto(SETTINGS_URL)
    await expect(page.getByLabel('Model', { exact: true })).toHaveValue('llama3.1')
  })

  test('loads and displays current suggestion count', async ({ page }) => {
    await setupSettingsRoutes(page)
    await page.goto(SETTINGS_URL)
    await expect(page.getByLabel('Suggestion Count (1–5)')).toHaveValue('3')
  })

  test('model select shows all available models', async ({ page }) => {
    await setupSettingsRoutes(page)
    await page.goto(SETTINGS_URL)
    const select = page.getByLabel('Model', { exact: true })
    await expect(select.getByRole('option', { name: 'llama3.1', exact: true })).toBeAttached()
    await expect(select.getByRole('option', { name: 'llama3.2' })).toBeAttached()
    await expect(select.getByRole('option', { name: 'mistral' })).toBeAttached()
  })

  test('changing model updates the select value', async ({ page }) => {
    await setupSettingsRoutes(page)
    await page.goto(SETTINGS_URL)
    await page.getByLabel('Model', { exact: true }).selectOption('mistral')
    await expect(page.getByLabel('Model', { exact: true })).toHaveValue('mistral')
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
    await page.route('/api/settings/voices', (route) =>
      route.fulfill({ json: mockVoices })
    )
    await page.goto(SETTINGS_URL)

    await page.getByLabel('Model', { exact: true }).selectOption('mistral')
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
    await page.route('/api/settings/voices', (route) =>
      route.fulfill({ json: mockVoices })
    )
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
    await page.route('/api/settings/voices', (route) =>
      route.fulfill({ json: mockVoices })
    )
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
    await page.route('/api/settings/voices', (route) =>
      route.fulfill({ json: mockVoices })
    )
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
    await page.route('/api/settings/voices', (route) =>
      route.fulfill({ json: mockVoices })
    )
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
    await page.getByRole('link', { name: 'Back to Home' }).click()
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
    await expect(page.getByLabel('Model', { exact: true })).toHaveValue('llama3.2')
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

  test('loads and displays current voice', async ({ page }) => {
    await setupSettingsRoutes(page)
    await page.goto(SETTINGS_URL)
    await expect(page.getByLabel('Voice')).toHaveValue('es_ES-davefx-medium')
  })

  test('voice select shows all available voices', async ({ page }) => {
    await setupSettingsRoutes(page)
    await page.goto(SETTINGS_URL)
    const select = page.getByLabel('Voice')
    await expect(select.getByRole('option', { name: 'David (Spain)' })).toBeAttached()
    await expect(select.getByRole('option', { name: 'Daniela (Argentina)' })).toBeAttached()
  })

  test('selected voice shows gender, country, quality, and pace detail', async ({ page }) => {
    await setupSettingsRoutes(page)
    await page.goto(SETTINGS_URL)
    const metaLine = page.locator('p').filter({ hasText: /Male|Female/ })
    await expect(metaLine).toContainText('Male')
    await expect(metaLine).toContainText('Spain')
    await expect(metaLine).toContainText('Medium quality')
    const paceLine = page.locator('p').filter({ hasText: /Pace:/ })
    await expect(paceLine).toContainText('Natural')
    await expect(paceLine).toContainText('Conversational native speed')
  })

  test('loads and displays current speech recognition model', async ({ page }) => {
    await setupSettingsRoutes(page)
    await page.goto(SETTINGS_URL)
    await expect(page.getByLabel('Speech Recognition Model')).toHaveValue('base')
  })

  test('speech recognition model select shows all three options', async ({ page }) => {
    await setupSettingsRoutes(page)
    await page.goto(SETTINGS_URL)
    const select = page.getByLabel('Speech Recognition Model')
    await expect(select.getByRole('option', { name: /Base/ })).toBeAttached()
    await expect(select.getByRole('option', { name: /Small/ })).toBeAttached()
    await expect(select.getByRole('option', { name: /Medium/ })).toBeAttached()
  })

  test('changing speech recognition model updates the select value', async ({ page }) => {
    await setupSettingsRoutes(page)
    await page.goto(SETTINGS_URL)
    await page.getByLabel('Speech Recognition Model').selectOption('medium')
    await expect(page.getByLabel('Speech Recognition Model')).toHaveValue('medium')
  })

  test('save button sends updated whisper model to API', async ({ page }) => {
    let capturedBody: unknown = null
    await page.route('/api/settings', (route) => {
      if (route.request().method() === 'PUT') {
        capturedBody = route.request().postDataJSON()
        return route.fulfill({ json: mockSettings })
      }
      return route.fulfill({ json: mockSettings })
    })
    await page.route('/api/settings/voices', (route) =>
      route.fulfill({ json: mockVoices })
    )
    await page.goto(SETTINGS_URL)
    await page.getByLabel('Speech Recognition Model').selectOption('small')
    await page.getByRole('button', { name: /save/i }).click()
    await expect(page.getByRole('status')).toContainText('Settings saved.')
    expect(capturedBody).toMatchObject({ whisper_model: 'small' })
  })

  test('changing voice updates the select value', async ({ page }) => {
    await setupSettingsRoutes(page)
    await page.goto(SETTINGS_URL)
    await page.getByLabel('Voice').selectOption('es_AR-daniela-high')
    await expect(page.getByLabel('Voice')).toHaveValue('es_AR-daniela-high')
  })

  test('save button sends updated voice to API', async ({ page }) => {
    let capturedBody: unknown = null
    await page.route('/api/settings', (route) => {
      if (route.request().method() === 'PUT') {
        capturedBody = route.request().postDataJSON()
        return route.fulfill({ json: mockSettings })
      }
      return route.fulfill({ json: mockSettings })
    })
    await page.route('/api/settings/voices', (route) =>
      route.fulfill({ json: mockVoices })
    )
    await page.goto(SETTINGS_URL)
    await page.getByLabel('Voice').selectOption('es_AR-daniela-high')
    await page.getByRole('button', { name: /save/i }).click()
    await expect(page.getByRole('status')).toContainText('Settings saved.')
    expect(capturedBody).toMatchObject({ tts_voice: 'es_AR-daniela-high' })
  })
})

test.describe('Settings page — correction feedback mode', () => {
  test('shows the three correction modes', async ({ page }) => {
    await setupSettingsRoutes(page)
    await page.goto(SETTINGS_URL)
    await expect(page.getByRole('group', { name: /correction/i })).toBeVisible()
    await expect(page.getByRole('radio', { name: 'Off', exact: true })).toBeVisible()
    await expect(page.getByRole('radio', { name: 'Gentle', exact: true })).toBeVisible()
    await expect(page.getByRole('radio', { name: 'Strict', exact: true })).toBeVisible()
  })

  test('defaults to the stored mode', async ({ page }) => {
    await setupSettingsRoutes(page, { ...mockSettings, correction_mode: 'gentle' })
    await page.goto(SETTINGS_URL)
    await expect(page.getByRole('radio', { name: 'Gentle', exact: true })).toBeChecked()
  })

  test('selecting Strict sends it to the API', async ({ page }) => {
    let capturedBody: unknown = null
    await page.route('/api/settings', (route) => {
      if (route.request().method() === 'PUT') {
        capturedBody = route.request().postDataJSON()
        return route.fulfill({ json: { ...mockSettings, correction_mode: 'strict' } })
      }
      return route.fulfill({ json: mockSettings })
    })
    await page.route('/api/settings/voices', (route) => route.fulfill({ json: mockVoices }))
    await page.goto(SETTINGS_URL)

    await page.getByRole('radio', { name: 'Strict', exact: true }).check()
    await page.getByRole('button', { name: /save/i }).click()

    await expect(page.getByRole('status')).toContainText('Settings saved.')
    expect(capturedBody).toMatchObject({ correction_mode: 'strict' })
  })

  test('shows the performance hint and ties it to the control', async ({ page }) => {
    await setupSettingsRoutes(page)
    await page.goto(SETTINGS_URL)

    const group = page.getByRole('group', { name: /correction/i })
    const describedBy = (await group.getAttribute('aria-describedby')) ?? ''
    const ids = describedBy.split(/\s+/).filter(Boolean)
    expect(ids.length).toBeGreaterThan(0)
    const described = page.locator(ids.map((id) => `#${id}`).join(', '))
    await expect(described.first()).toBeVisible()
    const text = (await described.allTextContents()).join(' ')
    expect(text).toMatch(/several seconds per turn/i)
    expect(text).toMatch(/skipped so the conversation continues/i)
  })

  test('warns that corrections are experimental and can be wrong', async ({ page }) => {
    await setupSettingsRoutes(page)
    await page.goto(SETTINGS_URL)

    const warning = page.getByRole('note', { name: /correction accuracy/i })
    await expect(warning).toBeVisible()
    await expect(warning).toContainText(/experimental/i)
    await expect(warning).toContainText(/can be wrong/i)
    await expect(warning).toContainText(/double-check/i)
    await expect(warning).toContainText(/larger model/i)
  })

  test('the warning is tied to the correction-mode control', async ({ page }) => {
    await setupSettingsRoutes(page)
    await page.goto(SETTINGS_URL)

    const group = page.getByRole('group', { name: /correction/i })
    const describedBy = (await group.getAttribute('aria-describedby')) ?? ''
    const warningId = await page
      .getByRole('note', { name: /correction accuracy/i })
      .getAttribute('id')
    expect(warningId).toBeTruthy()
    expect(describedBy.split(/\s+/)).toContain(warningId as string)
  })
})

test.describe('Settings page — language model provider', () => {
  const modelSelect = (page: import('@playwright/test').Page) =>
    page.getByLabel('Model', { exact: true })
  const effortSelect = (page: import('@playwright/test').Page) =>
    page.getByLabel('Effort', { exact: true })

  test('switching to Claude shows its model and effort, and saves all three', async ({ page }) => {
    let capturedBody: unknown = null
    await page.route('/api/settings', (route) => {
      if (route.request().method() === 'PUT') {
        capturedBody = route.request().postDataJSON()
        return route.fulfill({ json: mockSettings })
      }
      return route.fulfill({ json: mockSettings })
    })
    await page.route('/api/settings/voices', (route) => route.fulfill({ json: mockVoices }))
    await page.goto(SETTINGS_URL)

    await page.getByRole('radio', { name: 'Claude (via Claude Code)' }).check()

    await expect(modelSelect(page).locator('option:checked')).toHaveText('Claude Sonnet')
    await expect(effortSelect(page).locator('option:checked')).toHaveText('Low — fastest replies')
    await page.getByRole('button', { name: /save/i }).click()
    await expect(page.getByRole('status')).toContainText('Settings saved.')
    expect(capturedBody).toMatchObject({
      llm_provider: 'claude',
      llm_model: 'sonnet',
      llm_effort: 'low',
    })
  })

  test('switching back to Ollama restores its default model and hides effort', async ({ page }) => {
    await setupSettingsRoutes(page)
    await page.goto(SETTINGS_URL)

    await page.getByRole('radio', { name: 'Claude (via Claude Code)' }).check()
    await expect(effortSelect(page)).toBeVisible()
    await page.getByRole('radio', { name: 'Ollama (local)' }).check()

    await expect(modelSelect(page)).toHaveValue('llama3.1:8b')
    await expect(effortSelect(page)).toHaveCount(0)
  })

  test('a rejected save shows the reason', async ({ page }) => {
    const detail = "That model isn't a Claude model. Choose Sonnet, Haiku, or Opus."
    await page.route('/api/settings', (route) => {
      if (route.request().method() === 'PUT') {
        return route.fulfill({ status: 422, json: { detail } })
      }
      return route.fulfill({ json: mockSettings })
    })
    await page.route('/api/settings/voices', (route) => route.fulfill({ json: mockVoices }))
    await page.goto(SETTINGS_URL)

    await page.getByRole('radio', { name: 'Claude (via Claude Code)' }).check()
    await page.getByRole('button', { name: /save/i }).click()

    await expect(page.getByRole('alert')).toContainText(detail)
    await expect(page.getByRole('radio', { name: 'Claude (via Claude Code)' })).toBeChecked()
  })
})

test.describe('Settings page — Claude availability and privacy', () => {
  const claudeRadio = (page: import('@playwright/test').Page) =>
    page.getByRole('radio', { name: 'Claude (via Claude Code)' })

  for (const reason of ['not_installed', 'not_signed_in', 'not_on_plan'] as ClaudeUnavailableReason[]) {
    test(`Claude is disabled with its reason when ${reason}`, async ({ page }) => {
      await mockLlmProviders(page, mockLlmProvidersClaudeUnavailable(reason))
      await setupSettingsRoutes(page)
      await page.goto(SETTINGS_URL)

      const message = CLAUDE_UNAVAILABLE_MESSAGES[reason]
      await expect(claudeRadio(page)).toBeDisabled()
      await expect(page.getByText(message)).toBeVisible()
      await expect(claudeRadio(page)).toHaveAccessibleDescription(message)
    })
  }

  test('selecting Claude reveals the privacy notice, and Ollama hides it', async ({ page }) => {
    await setupSettingsRoutes(page)
    await page.goto(SETTINGS_URL)
    const notice = page.getByRole('note', { name: /privacy/i })

    await claudeRadio(page).check()
    await expect(notice).toBeVisible()
    await expect(notice).toContainText('sent to Anthropic')
    await page.getByRole('radio', { name: 'Ollama (local)' }).check()
    await expect(notice).toHaveCount(0)
  })
})

test.describe('Settings page — conversation level', () => {
  test('lists the four levels from the catalogue, easiest first', async ({ page }) => {
    await setupSettingsRoutes(page)
    await page.goto(SETTINGS_URL)

    const group = page.getByRole('group', { name: 'Conversation level' })
    await expect(group).toBeVisible()
    const radios = group.getByRole('radio')
    await expect(radios).toHaveCount(mockConversationLevels.length)
    for (const [index, level] of mockConversationLevels.entries()) {
      await expect(radios.nth(index)).toHaveAccessibleName(`${level.label} ${level.cefr_label}`)
      await expect(radios.nth(index)).toHaveAccessibleDescription(level.description)
    }
  })

  test('checks the stored level', async ({ page }) => {
    await setupSettingsRoutes(page, { ...mockSettings, conversation_level: 'intermediate' })
    await page.goto(SETTINGS_URL)

    await expect(page.getByRole('radio', { name: /^Intermediate/ })).toBeChecked()
    await expect(page.getByRole('radio', { name: /^Natural/ })).not.toBeChecked()
  })

  test('choosing Elementary and saving sends it to the API', async ({ page }) => {
    let capturedBody: unknown = null
    await page.route('/api/settings', (route) => {
      if (route.request().method() === 'PUT') {
        capturedBody = route.request().postDataJSON()
        return route.fulfill({ json: { ...mockSettings, conversation_level: 'elementary' } })
      }
      return route.fulfill({ json: mockSettings })
    })
    await page.route('/api/settings/voices', (route) =>
      route.fulfill({ json: mockVoices })
    )
    await page.goto(SETTINGS_URL)

    await page.getByRole('radio', { name: /^Elementary/ }).check()
    await page.getByRole('button', { name: /save/i }).click()

    await expect(page.getByRole('status')).toContainText('Settings saved.')
    expect(capturedBody).toMatchObject({ conversation_level: 'elementary' })
  })

  test('warns that levels are experimental, tied to the level group', async ({ page }) => {
    await setupSettingsRoutes(page)
    await page.goto(SETTINGS_URL)

    const warning = page.getByRole('note', { name: /level accuracy/i })
    await expect(warning).toBeVisible()
    await expect(warning).toContainText(/experimental/i)
    await expect(warning).toContainText(/larger model/i)
    const group = page.getByRole('group', { name: 'Conversation level' })
    await expect(group).toHaveAttribute('aria-describedby', (await warning.getAttribute('id'))!)
  })

  test('explains what to do when the levels cannot be loaded', async ({ page }) => {
    await setupSettingsRoutes(page)
    await page.route('/api/settings/conversation-levels', (route) =>
      route.fulfill({ status: 500, json: { detail: 'Internal error' } })
    )
    await page.goto(SETTINGS_URL)

    await expect(page.getByRole('alert')).toContainText(/could not be loaded.*reload/i)
    await expect(page.getByRole('group', { name: 'Conversation level' })).toHaveCount(0)
  })
})

test.describe('Settings page — practice language (006)', () => {
  test('the practice-language group comes before the Voice field', async ({ page }) => {
    await mockPracticeLanguagesApi(page)
    await setupSettingsRoutes(page)
    await page.goto(SETTINGS_URL)

    const group = page.getByRole('group', { name: 'Practice language' })
    await expect(group).toBeVisible()
    const groupBox = await group.boundingBox()
    const voiceBox = await page.getByLabel('Voice').boundingBox()
    expect(groupBox!.y).toBeLessThan(voiceBox!.y)
    await expect(group.getByRole('radio', { name: 'Spanish' })).toBeChecked()
  })
})
