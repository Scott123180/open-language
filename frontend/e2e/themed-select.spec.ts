import { test, expect, type Locator, type Page } from '@playwright/test'
import {
  combobox,
  contrastRatio,
  mockChatApis,
  mockConversationLevelsApi,
  mockHomeApis,
  mockLlmProviders,
  mockPodcastApis,
  mockPodcastPreferences,
  mockPracticeLanguageSetting,
  mockPracticeLanguagesApi,
  mockSettings,
  mockVoices,
} from './fixtures'

/** FR-021, SC-008: every drop-down draws its open list in the theme, with readable contrast. */

const MIN_CONTRAST = 4.5
const THEMES = [
  { name: 'light', preference: 'light', colorScheme: 'light' },
  { name: 'dark', preference: 'dark', colorScheme: 'light' },
  { name: 'system-dark', preference: 'system', colorScheme: 'dark' },
] as const

async function openSettings(page: Page) {
  await mockLlmProviders(page)
  await mockConversationLevelsApi(page)
  await mockPracticeLanguagesApi(page)
  await page.route('/api/settings', (route) => route.fulfill({ json: mockSettings }))
  await page.route('/api/settings/voices', (route) => route.fulfill({ json: mockVoices }))
  await page.goto('/settings')
}

const DROP_DOWNS: { name: string; label: string; open: (page: Page) => Promise<void> }[] = [
  {
    name: 'the podcast personality',
    label: "Marco's personality",
    open: async (page) => {
      await mockHomeApis(page)
      await mockPodcastApis(page, { preferences: { ...mockPodcastPreferences, last_format: 'panel' } })
      await page.goto('/podcasts/setup?show=weekend-food-talk')
    },
  },
  { name: 'the Settings voice', label: 'Voice', open: openSettings },
  { name: 'the Settings speech model', label: 'Speech Recognition Model', open: openSettings },
  { name: 'the provider model', label: 'Model', open: openSettings },
  {
    name: 'the provider effort',
    label: 'Effort',
    open: async (page) => {
      await openSettings(page)
      await page.getByRole('radio', { name: 'Claude (via Claude Code)' }).check()
    },
  },
  {
    name: 'the chat Level control',
    label: 'Level',
    open: async (page) => {
      await mockChatApis(page)
      await page.goto('/chat/1')
    },
  },
  {
    name: 'the flashcards word filter',
    label: 'Sort words',
    open: async (page) => {
      await mockPracticeLanguageSetting(page, 'es')
      await page.route('/api/flashcards/words**', (route) => route.fulfill({ json: [] }))
      await page.goto('/flashcards')
    },
  },
]

/** The theme's surface and text colours, as the browser computes them. */
const themeColours = (page: Page) =>
  page.evaluate(() => {
    const probe = document.createElement('div')
    probe.style.backgroundColor = 'var(--color-surface)'
    probe.style.color = 'var(--color-text)'
    document.body.append(probe)
    const style = getComputedStyle(probe)
    const colours = { surface: style.backgroundColor, text: style.color }
    probe.remove()
    return colours
  })

const optionColours = (option: Locator) =>
  option.evaluate((element) => {
    const style = getComputedStyle(element)
    return { color: style.color, background: style.backgroundColor, outline: style.outlineStyle }
  })

/** Move the active option off the chosen one, so chosen, active and plain can all be checked. */
async function moveOffTheChosenOption(page: Page, list: Locator) {
  await page.keyboard.press('End')
  const active = list.locator('.themed-select-option--active')
  if ((await active.getAttribute('aria-selected')) === 'true') await page.keyboard.press('Home')
}

for (const theme of THEMES) {
  for (const dropDown of DROP_DOWNS) {
    test(`${dropDown.name} is themed and readable in ${theme.name} mode`, async ({ page }) => {
      await page.emulateMedia({ colorScheme: theme.colorScheme })
      await page.addInitScript((preference) => localStorage.setItem('theme-preference', preference), theme.preference)
      await dropDown.open(page)
      const select = combobox(page, dropDown.label)
      await expect(select).not.toHaveText('')
      const chosen = await select.textContent()

      await select.focus()
      await page.keyboard.press('Enter')
      const list = page.getByRole('listbox')
      await expect(list).toBeVisible()
      await moveOffTheChosenOption(page, list)

      const colours = await themeColours(page)
      expect(await list.evaluate((element) => getComputedStyle(element).backgroundColor)).toBe(colours.surface)
      const selected = await optionColours(list.locator('[aria-selected="true"]'))
      const active = await optionColours(list.locator('.themed-select-option--active'))
      expect(contrastRatio(selected.color, selected.background)).toBeGreaterThanOrEqual(MIN_CONTRAST)
      expect(contrastRatio(active.color, active.background)).toBeGreaterThanOrEqual(MIN_CONTRAST)
      expect(active.outline).toBe('solid')
      const plain = list.locator('[aria-selected="false"]:not(.themed-select-option--active)')
      if ((await plain.count()) > 0) {
        const normal = await optionColours(plain.first())
        expect(normal).toEqual({ color: colours.text, background: colours.surface, outline: 'none' })
        expect(contrastRatio(normal.color, normal.background)).toBeGreaterThanOrEqual(MIN_CONTRAST)
      }

      await page.keyboard.press('Escape')
      await expect(list).toHaveCount(0)
      await expect(select).toHaveText(chosen ?? '')
    })
  }
}

test('a drop-down chooses with ↓ and Enter from the keyboard', async ({ page }) => {
  await openSettings(page)
  const select = combobox(page, 'Speech Recognition Model')
  await expect(select).toHaveText('Base — fast, lower accuracy')

  await select.focus()
  await page.keyboard.press('ArrowDown')
  await page.keyboard.press('ArrowDown')
  await page.keyboard.press('Enter')

  await expect(page.getByRole('listbox')).toHaveCount(0)
  await expect(select).toHaveText('Small — balanced')
})
