import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'
import {
  catalogWithEpisodeOptions,
  episodeFixture,
  mockPodcastApis,
  mockPodcastPreferences,
  noSubjectSuggestions,
  subjectSuggestions,
} from './fixtures'

const SETUP = '/podcasts/setup?show=weekend-food-talk'
const DEFAULT_SUMMARY = 'Episode settings: Balanced · Medium lines · Asked sometimes'
const DECLINED = "That subject can't be used for an episode. Change it or clear it, then start."

async function onSetup(page: Page, options: { preferences?: typeof mockPodcastPreferences & Record<string, unknown> } = {}) {
  await mockPodcastApis(page, { catalog: catalogWithEpisodeOptions() as never, preferences: options.preferences as never })
  const starts: Record<string, unknown>[] = []
  await page.route('/api/podcasts/episodes', (route) => {
    if (route.request().method() !== 'POST') return route.fulfill({ json: [] })
    starts.push(route.request().postDataJSON())
    return route.fulfill({ status: 201, json: episodeFixture('one_host') })
  })
  await page.goto(SETUP)
  return { starts }
}

const openSettings = (page: Page) => page.getByRole('button', { name: /^Episode settings:/ }).click()

test.describe('Podcast setup — Episode settings (011 US2)', () => {
  test('the settings are closed, named by their summary', async ({ page }) => {
    await onSetup(page)

    const toggle = page.getByRole('button', { name: DEFAULT_SUMMARY })
    await expect(toggle).toHaveAttribute('aria-expanded', 'false')
    await expect(page.getByRole('radiogroup', { name: 'Style' })).toHaveCount(0)
  })

  test('starting with the defaults needs no opening and sends them', async ({ page }) => {
    const { starts } = await onSetup(page)

    await page.getByRole('button', { name: /^Start/ }).click()

    await expect.poll(() => starts.length).toBe(1)
    expect(starts[0].settings).toEqual({ style: 'balanced', line_length: 'medium', invite_frequency: 'sometimes', learner_role: 'guest', today_subject: null })
  })

  test('the choices follow the summary and reach the request', async ({ page }) => {
    const { starts } = await onSetup(page)
    await openSettings(page)

    await page.getByRole('radio', { name: /Presented/ }).check()
    await page.getByRole('radiogroup', { name: 'Host lines' }).getByRole('radio', { name: /Long/ }).check()
    await page.getByRole('radio', { name: /Rarely/ }).check()
    await page.getByRole('radio', { name: /Caller/ }).check()
    await page.getByRole('textbox', { name: "Today's subject (optional)" }).fill('why we yawn')

    await expect(page.getByRole('button', { name: 'Episode settings: Presented · Long lines · Asked rarely' })).toBeVisible()
    await page.getByRole('button', { name: /^Start/ }).click()
    await expect.poll(() => starts.length).toBe(1)
    expect(starts[0].settings).toEqual({ style: 'presented', line_length: 'long', invite_frequency: 'rarely', learner_role: 'caller', today_subject: 'why we yawn' })
  })

  test('the next setup offers the last style, lines and frequency, with the show’s own role', async ({ page }) => {
    await onSetup(page, { preferences: { ...mockPodcastPreferences, last_style: 'presented', last_line_length: 'long', last_invite_frequency: 'rarely' } })
    await expect(page.getByRole('button', { name: 'Episode settings: Presented · Long lines · Asked rarely' })).toBeVisible()
    await openSettings(page)

    await expect(page.getByRole('radio', { name: /Guest/ })).toBeChecked()
  })

  test('Listen leaves out how often you are asked and your role', async ({ page }) => {
    await onSetup(page)
    await page.getByRole('radio', { name: /Listen/ }).check()
    await openSettings(page)

    await expect(page.getByRole('radiogroup', { name: 'Style' })).toBeVisible()
    await expect(page.getByRole('radiogroup', { name: "How often you're asked" })).toHaveCount(0)
    await expect(page.getByRole('radiogroup', { name: 'Your role' })).toHaveCount(0)
  })

  test('a declined subject is explained beside the field and nothing starts', async ({ page }) => {
    await mockPodcastApis(page, { catalog: catalogWithEpisodeOptions() as never })
    await page.route('/api/podcasts/episodes', (route) =>
      route.request().method() === 'POST' ? route.fulfill({ status: 422, json: { detail: DECLINED } }) : route.fulfill({ json: [] }),
    )
    await page.goto(SETUP)
    await openSettings(page)
    await page.getByRole('textbox', { name: "Today's subject (optional)" }).fill('something unkind')

    await page.getByRole('button', { name: /^Start/ }).click()

    await expect(page.getByRole('alert').filter({ hasText: DECLINED })).toBeVisible()
    await expect(page).toHaveURL(/\/podcasts\/setup/)
  })

  test('Suggest subjects fills Today’s subject and skips what it already showed', async ({ page }) => {
    const { starts } = await onSetup(page)
    const asked: Record<string, unknown>[] = []
    await page.route('/api/podcasts/subject-suggestions', (route) => {
      asked.push(route.request().postDataJSON())
      return route.fulfill({ json: asked.length === 1 ? subjectSuggestions : noSubjectSuggestions })
    })
    await openSettings(page)

    await page.getByRole('button', { name: 'Suggest subjects' }).click()
    await expect(page.getByRole('button', { name: /^Use: / })).toHaveCount(3)
    await page.getByRole('button', { name: 'Use: why onions make you cry' }).click()
    await expect(page.getByRole('textbox', { name: "Today's subject (optional)" })).toHaveValue('why onions make you cry')
    await expect(page.getByRole('textbox', { name: "Today's subject (optional)" })).toBeFocused()

    await page.getByRole('button', { name: 'Suggest subjects' }).click()
    await expect(page.getByText('No new subjects came back. Type one, or start without one.')).toBeVisible()
    expect(asked[0].avoid).toEqual([])
    expect(asked[1].avoid).toEqual(subjectSuggestions.subjects)

    await page.getByRole('button', { name: /^Start/ }).click()
    await expect.poll(() => starts.length).toBe(1)
    expect((starts[0].settings as Record<string, unknown>).today_subject).toBe('why onions make you cry')
  })

  test('a failed suggestion shows the provider’s message and Start still works', async ({ page }) => {
    const { starts } = await onSetup(page)
    await page.route('/api/podcasts/subject-suggestions', (route) => route.fulfill({ status: 503, json: { detail: "Ollama isn't running." } }))
    await openSettings(page)

    await page.getByRole('button', { name: 'Suggest subjects' }).click()

    await expect(page.getByText("Ollama isn't running.")).toBeVisible()
    await page.getByRole('button', { name: /^Start/ }).click()
    await expect.poll(() => starts.length).toBe(1)
  })

  test('Start stays the one primary action, with Suggest subjects secondary', async ({ page }) => {
    await onSetup(page)
    await openSettings(page)

    const primaries = await page.getByRole('button').evaluateAll((buttons) => {
      const primary = getComputedStyle(document.documentElement).getPropertyValue('--color-primary').trim()
      const probe = document.createElement('div')
      probe.style.background = primary
      document.body.appendChild(probe)
      const colour = getComputedStyle(probe).backgroundColor
      probe.remove()
      return buttons.filter((b) => getComputedStyle(b).backgroundColor === colour).map((b) => b.textContent)
    })

    expect(primaries).toHaveLength(1)
    expect(primaries[0]).toMatch(/^Start/)
  })
})
