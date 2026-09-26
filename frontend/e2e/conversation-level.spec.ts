import { test, expect, type Page } from '@playwright/test'
import { mockChatApis, mockSettings, mockVoices } from './fixtures'

const CHAT_URL = '/chat/1'
const SETTINGS_URL = '/settings'
const ANNOUNCEMENT = 'Level set to Beginner. It applies from the next reply.'

type StoredSettings = typeof mockSettings

/** A `/api/settings` route that keeps what is PUT, and records every PUT body. */
async function statefulSettings(page: Page, initial: StoredSettings = mockSettings) {
  const state = { settings: { ...initial }, puts: [] as unknown[] }
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

const levelControl = (page: Page) =>
  page.locator('header').getByRole('combobox', { name: 'Level' })

test.describe('Conversation level — chat header control', () => {
  test.beforeEach(async ({ page }) => {
    await mockChatApis(page)
  })

  test('changing the level sends only the level and announces when it applies', async ({
    page,
  }) => {
    const state = await statefulSettings(page)
    await page.goto(CHAT_URL)
    await expect(page.getByText('¡Hola! ¿Cómo estás?')).toBeVisible()

    await levelControl(page).selectOption('beginner')

    await expect(page.getByText(ANNOUNCEMENT)).toBeAttached()
    expect(state.puts).toEqual([{ conversation_level: 'beginner' }])
    await expect(levelControl(page)).toHaveValue('beginner')
  })

  test('the change keeps the learner in the conversation with its messages', async ({ page }) => {
    await statefulSettings(page)
    await page.goto(CHAT_URL)
    await expect(page.getByText('¡Hola! ¿Cómo estás?')).toBeVisible()

    await levelControl(page).selectOption('beginner')
    await expect(page.getByText(ANNOUNCEMENT)).toBeAttached()

    await expect(page).toHaveURL(CHAT_URL)
    await expect(page.getByText('¡Hola! ¿Cómo estás?')).toBeVisible()
  })

  test('the level can be changed from the keyboard in two steps', async ({ page }) => {
    const state = await statefulSettings(page)
    await page.goto(CHAT_URL)
    await expect(levelControl(page)).toHaveValue('natural')

    await levelControl(page).focus()
    await page.keyboard.press('Home')

    await expect(levelControl(page)).toHaveValue('beginner')
    await expect.poll(() => state.puts).toEqual([{ conversation_level: 'beginner' }])
  })

  test('a failed save reverts the control and shows an alert', async ({ page }) => {
    await page.route('/api/settings', (route) =>
      route.request().method() === 'PUT'
        ? route.fulfill({ status: 500, json: { detail: 'Internal error' } })
        : route.fulfill({ json: mockSettings })
    )
    await page.goto(CHAT_URL)
    await expect(levelControl(page)).toHaveValue('natural')

    await levelControl(page).selectOption('beginner')

    await expect(page.getByRole('alert')).toContainText(/level was not changed/i)
    await expect(levelControl(page)).toHaveValue('natural')
  })

  test('a change in the chat header shows on the Settings screen', async ({ page }) => {
    await statefulSettings(page)
    await page.goto(CHAT_URL)
    await levelControl(page).selectOption('beginner')
    await expect(page.getByText(ANNOUNCEMENT)).toBeAttached()

    await page.goto(SETTINGS_URL)

    await expect(page.getByRole('radio', { name: /^Beginner/ })).toBeChecked()
  })

  test('a level saved on Settings shows in the chat header', async ({ page }) => {
    await statefulSettings(page)
    await page.goto(SETTINGS_URL)
    await page.getByRole('radio', { name: /^Intermediate/ }).check()
    await page.getByRole('button', { name: /save/i }).click()
    await expect(page.getByRole('status')).toContainText('Settings saved.')

    await page.goto(CHAT_URL)

    await expect(levelControl(page)).toHaveValue('intermediate')
  })

  test('explains in the header when the level cannot be loaded', async ({ page }) => {
    await statefulSettings(page)
    await page.route('/api/settings/conversation-levels', (route) =>
      route.fulfill({ status: 500, json: { detail: 'Internal error' } })
    )
    await page.goto(CHAT_URL)

    await expect(page.locator('header').getByRole('alert')).toContainText(/could not be loaded/i)
    await expect(levelControl(page)).toHaveCount(0)
    await expect(page.getByText('¡Hola! ¿Cómo estás?')).toBeVisible()
  })

  test('the header fits a 360 px screen with the title on one line', async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 740 })
    await statefulSettings(page)
    await page.goto(CHAT_URL)
    await expect(levelControl(page)).toBeVisible()

    const header = page.locator('header')
    const overflow = await header.evaluate((el) => el.scrollWidth - el.clientWidth)
    const title = page.getByRole('heading', { name: 'Chat' })
    const titleLines = await title.evaluate(
      (el) => el.getBoundingClientRect().height / parseFloat(getComputedStyle(el).lineHeight)
    )

    expect(overflow).toBe(0)
    expect(Math.round(titleLines)).toBe(1)
    const box = await levelControl(page).boundingBox()
    expect(box!.x + box!.width).toBeLessThanOrEqual(360)
  })
})
