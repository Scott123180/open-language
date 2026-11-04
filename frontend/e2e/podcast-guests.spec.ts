import { test, expect, type Page } from '@playwright/test'
import {
  catalogWithSeries,
  episodeOptions,
  guestDraft,
  guestEpisodeFixture,
  mockHomeApis,
  mockPodcastApis,
  mockSeriesApis,
  panelSeriesWithSettings,
} from './fixtures'

const SETUP = '/podcasts/setup?show=big-little-questions'
const START = 'Start episode 2'
const SOFIA = { ...guestDraft, name: 'Sofía' }

async function onPanelSeries(page: Page) {
  await mockHomeApis(page)
  await mockPodcastApis(page, { catalog: { ...catalogWithSeries(), episode_options: episodeOptions } as never, episode: guestEpisodeFixture() as never })
  await mockSeriesApis(page)
  await page.route('/api/podcasts/series/4', (route) => route.fulfill({ json: panelSeriesWithSettings() }))
  const guestRequests: Record<string, unknown>[] = []
  await page.route('/api/podcasts/series/4/guest', (route) => {
    guestRequests.push(route.request().postDataJSON())
    return route.fulfill({ json: guestRequests.length === 1 ? guestDraft : SOFIA })
  })
  const starts: Record<string, unknown>[] = []
  await page.route('/api/podcasts/episodes', (route) => {
    if (route.request().method() !== 'POST') return route.fulfill({ json: [] })
    starts.push(route.request().postDataJSON())
    return route.fulfill({ status: 201, json: guestEpisodeFixture() })
  })
  await page.goto(SETUP)
  await expect(page.getByRole('button', { name: START })).toBeVisible()
  return { guestRequests, starts }
}

async function inviteForInes(page: Page) {
  await page.getByRole('button', { name: 'Invite a guest in place of Inés' }).click()
  const dialog = page.getByRole('alertdialog', { name: 'Invite a guest in place of Inés?' })
  await dialog.getByRole('radio', { name: /Joker/ }).click()
  await dialog.getByRole('button', { name: 'Invite' }).click()
}

test.describe('Podcast guests (011 US4)', () => {
  test('Invite a guest…, a personality and Invite seat the guest with Inés away', async ({ page }) => {
    const { guestRequests } = await onPanelSeries(page)

    await inviteForInes(page)

    await expect(page.getByText('Guest · this episode')).toBeVisible()
    await expect(page.getByText('Marco', { exact: true })).toBeVisible()
    await expect(page.getByText('Away this episode')).toBeVisible()
    expect(guestRequests[0]).toMatchObject({ slot: 'second', format: 'panel', personality_id: 'joker', avoid_names: [] })
  })

  test('Another guest sends the names already drawn', async ({ page }) => {
    const { guestRequests } = await onPanelSeries(page)
    await inviteForInes(page)
    await expect(page.getByText('Marco', { exact: true })).toBeVisible()

    await page.getByRole('button', { name: 'Another guest' }).click()

    await expect(page.getByText('Sofía', { exact: true })).toBeVisible()
    expect(guestRequests[1]).toMatchObject({ avoid_names: ['Marco'], personality_id: 'joker' })
  })

  test('Remove guest gives Inés her chair back', async ({ page }) => {
    await onPanelSeries(page)
    await inviteForInes(page)

    await page.getByRole('button', { name: 'Remove guest' }).click()

    await expect(page.getByText('Guest · this episode')).toHaveCount(0)
    await expect(page.getByText('Away this episode')).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Invite a guest in place of Inés' })).toBeVisible()
  })

  test('Start sends the guest, and the episode header names the guest and who is away', async ({ page }) => {
    const { starts } = await onPanelSeries(page)
    await inviteForInes(page)
    await expect(page.getByText('Marco', { exact: true })).toBeVisible()

    await page.getByRole('button', { name: START }).click()

    await expect.poll(() => starts.length).toBe(1)
    expect(starts[0].guest).toEqual(guestDraft)
    await expect(page.getByText('Guest: Marco')).toBeVisible()
    await expect(page.getByText('Inés is away')).toBeVisible()
  })
})
