import { test, expect, type Page } from '@playwright/test'
import {
  catalogWithSeries,
  episodeOptions,
  guestDraft,
  mockHomeApis,
  mockPodcastApis,
  mockSeriesApis,
  seriesEpisodeFixture,
  seriesWithSettings,
} from './fixtures'

const SETUP = '/podcasts/setup?show=big-little-questions'
const SCOPE_QUESTION = 'Change for which episodes?'
const START = 'Start episode 2'

type Detail = ReturnType<typeof seriesWithSettings>

async function onSeriesSetup(page: Page, details: Detail[] = [seriesWithSettings()]) {
  await mockHomeApis(page)
  await mockPodcastApis(page, { catalog: { ...catalogWithSeries(), episode_options: episodeOptions } as never, episode: seriesEpisodeFixture() })
  await mockSeriesApis(page)
  let reads = 0
  await page.route('/api/podcasts/series/4', (route) => route.fulfill({ json: details[Math.min(reads++, details.length - 1)] }))
  const starts: Record<string, unknown>[] = []
  await page.route('/api/podcasts/episodes', (route) => {
    if (route.request().method() !== 'POST') return route.fulfill({ json: [] })
    starts.push(route.request().postDataJSON())
    return route.fulfill({ status: 201, json: seriesEpisodeFixture() })
  })
  await page.goto(SETUP)
  await expect(page.getByRole('button', { name: START })).toBeVisible()
  return { starts }
}

const openSettings = (page: Page) => page.getByRole('button', { name: /^Episode settings:/ }).click()
const scopeDialog = (page: Page) => page.getByRole('alertdialog', { name: SCOPE_QUESTION })

async function change(page: Page, group: string, option: RegExp, scope: 'Just this episode' | 'This and later episodes') {
  await page.getByRole('radiogroup', { name: new RegExp(`^${group}`) }).getByRole('radio', { name: option }).click()
  await scopeDialog(page).getByRole('button', { name: scope }).click()
}

test.describe('Podcast series settings (011 US3)', () => {
  test('the first change of each setting asks for its scope and marks its legend', async ({ page }) => {
    await onSeriesSetup(page)
    await openSettings(page)

    await page.getByRole('radiogroup', { name: /^Style/ }).getByRole('radio', { name: /Presented/ }).click()
    await expect(scopeDialog(page)).toBeVisible()
    await scopeDialog(page).getByRole('button', { name: 'Just this episode' }).click()
    await change(page, 'Host lines', /Long/, 'This and later episodes')

    await expect(page.getByRole('radiogroup', { name: /^Style/ })).toContainText('this episode')
    await expect(page.getByRole('radiogroup', { name: /^Host lines/ })).toContainText('from now on')
  })

  test('changing a scoped setting again asks nothing', async ({ page }) => {
    await onSeriesSetup(page)
    await openSettings(page)
    await change(page, 'Style', /Presented/, 'Just this episode')

    await page.getByRole('radiogroup', { name: /^Style/ }).getByRole('radio', { name: /Conversation/ }).click()

    await expect(scopeDialog(page)).toHaveCount(0)
  })

  test('Escape reverts the change', async ({ page }) => {
    await onSeriesSetup(page)
    await openSettings(page)

    await page.getByRole('radiogroup', { name: /^Style/ }).getByRole('radio', { name: /Presented/ }).click()
    await page.keyboard.press('Escape')

    await expect(scopeDialog(page)).toHaveCount(0)
    await expect(page.getByRole('radiogroup', { name: /^Style/ }).getByRole('radio', { name: /Balanced/ })).toBeChecked()
  })

  test('Start sends this episode’s settings and only the from-now-on names', async ({ page }) => {
    const { starts } = await onSeriesSetup(page)
    await openSettings(page)
    await change(page, 'Style', /Presented/, 'Just this episode')
    await change(page, 'Host lines', /Long/, 'This and later episodes')

    await page.getByRole('button', { name: START }).click()

    await expect.poll(() => starts.length).toBe(1)
    expect(starts[0].settings).toMatchObject({ style: 'presented', line_length: 'long' })
    expect(starts[0].from_now_on).toEqual(['line_length'])
  })

  test('the next setup shows the usual settings after a just-this-episode start', async ({ page }) => {
    await onSeriesSetup(page)
    await openSettings(page)
    await change(page, 'Style', /Presented/, 'Just this episode')
    await page.getByRole('button', { name: START }).click()

    await page.goto(SETUP)
    await openSettings(page)

    await expect(page.getByRole('radiogroup', { name: /^Style/ }).getByRole('radio', { name: /Balanced/ })).toBeChecked()
  })

  test('the next setup shows a from-now-on change', async ({ page }) => {
    const changed = seriesWithSettings({ usual_settings: { ...seriesWithSettings().usual_settings, style: 'presented' }, is_standard: false })
    await onSeriesSetup(page, [seriesWithSettings(), changed])
    await openSettings(page)
    await change(page, 'Style', /Presented/, 'This and later episodes')
    await page.getByRole('button', { name: START }).click()

    await page.goto(SETUP)
    await openSettings(page)

    await expect(page.getByRole('radiogroup', { name: /^Style/ }).getByRole('radio', { name: /Presented/ })).toBeChecked()
  })

  test('Use the show’s standard settings asks, resets the series and the form', async ({ page }) => {
    const own = seriesWithSettings({ usual_settings: { ...seriesWithSettings().usual_settings, style: 'presented' }, is_standard: false })
    await onSeriesSetup(page, [own])
    const resets: string[] = []
    await page.route('/api/podcasts/series/4/settings', (route) => {
      resets.push(route.request().method())
      return route.fulfill({ json: seriesWithSettings() })
    })

    await page.getByRole('button', { name: "Use the show's standard settings" }).click()
    await page.getByRole('alertdialog').getByRole('button', { name: 'Use standard settings' }).click()

    await expect.poll(() => resets).toEqual(['DELETE'])
    await expect(page.getByRole('button', { name: "Use the show's standard settings" })).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Episode settings: Balanced · Medium lines · Asked sometimes' })).toBeVisible()
  })

  test('SC-007: Panel, Just this episode, Start brings the expert in as a guest', async ({ page }) => {
    const { starts } = await onSeriesSetup(page)
    await page.route('/api/podcasts/series/4/guest', (route) => route.fulfill({ json: guestDraft }))

    await page.getByRole('radio', { name: /Panel/ }).click()
    await scopeDialog(page).getByRole('button', { name: 'Just this episode' }).click()
    await expect(page.getByText('Guest · this episode')).toBeVisible()
    await expect(page.getByText('Marco', { exact: true })).toBeVisible()
    await page.getByRole('button', { name: START }).click()

    await expect.poll(() => starts.length).toBe(1)
    expect(starts[0].format).toBe('panel')
    expect(starts[0].guest).toEqual(guestDraft)
    expect(starts[0].from_now_on).toBeUndefined()
  })
})
