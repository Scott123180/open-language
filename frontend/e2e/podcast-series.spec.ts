import { test, expect, type Page } from '@playwright/test'
import {
  catalogWithSeries,
  mockHomeApis,
  mockPodcastApis,
  mockSeriesApis,
  seriesDetailFixture,
  seriesEpisodeFixture,
  seriesShowFixture,
  seriesSummaryFixture,
} from './fixtures'

const SETUP = '/podcasts/setup?show=big-little-questions'
const unfinishedShow = { ...seriesShowFixture, series: { ...seriesSummaryFixture, unfinished_episode: { conversation_id: 81, episode_number: 1 } } }

async function openPodcasts(page: Page, catalog = catalogWithSeries()) {
  await mockHomeApis(page)
  await mockPodcastApis(page, { catalog, episode: seriesEpisodeFixture() })
}

const startRequest = (page: Page) =>
  page.waitForRequest((request) => request.url().endsWith('/api/podcasts/episodes') && request.method() === 'POST')

test.describe('Podcast series (010 US1)', () => {
  test('the card says which episode is next, and setup offers it with the same hosts', async ({ page }) => {
    await openPodcasts(page)
    await mockSeriesApis(page)
    await page.goto('/podcasts')

    const card = page.getByRole('button', { name: 'Big Little Questions' })
    await expect(card).toContainText('Episode 2 next')
    await card.click()

    await expect(page.getByRole('button', { name: 'Start episode 2' })).toBeVisible()
    await page.getByRole('radio', { name: /Panel/ }).check()
    await expect(page.getByText('Hugo', { exact: true })).toBeVisible()
    await expect(page.getByText('Inés', { exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: /Shuffle/ })).toHaveCount(0)
  })

  test('Start sends a series episode with the listed hosts and the header names the episode', async ({ page }) => {
    await openPodcasts(page)
    await mockSeriesApis(page)
    await page.goto(SETUP)
    const started = startRequest(page)

    await page.getByRole('button', { name: 'Start episode 2' }).click()

    const body = (await started).postDataJSON()
    expect(body.kind).toBe('series')
    expect(body.show.hosts.map((host: { name: string }) => host.name)).toEqual(['Hugo', 'Inés'])
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Big Little Questions · Episode 2')
  })

  test('an unfinished episode is offered first', async ({ page }) => {
    await openPodcasts(page, catalogWithSeries(unfinishedShow))
    await mockSeriesApis(page, { detail: seriesDetailFixture({ unfinished_episode: { conversation_id: 81, episode_number: 1 } }) })
    await page.goto(SETUP)

    await expect(page.getByRole('button', { name: 'Continue episode 1' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Start a new episode instead' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Start episode 2' })).toHaveCount(0)
  })

  test('Start waits while the hosts catch up, then opens the episode on its own', async ({ page }) => {
    await openPodcasts(page)
    const series = await mockSeriesApis(page, { detail: seriesDetailFixture({ memory_status: 'pending' }), holdWaits: true })
    await page.goto(SETUP)

    await page.getByRole('button', { name: 'Start episode 2' }).click()

    await expect(page.getByRole('status')).toHaveText('Hugo and Inés are catching up on episode 1. This takes a few seconds.')
    await expect(page.getByRole('button', { name: 'Start episode 2' })).toHaveAttribute('aria-busy', 'true')
    series.release()
    await expect(page).toHaveURL(/\/podcasts\/episodes\/57/)
  })

  test('a failed catch-up offers Try again and Start without it', async ({ page }) => {
    await openPodcasts(page)
    await mockSeriesApis(page, {
      detail: seriesDetailFixture({ memory_status: 'pending' }),
      waits: [{ status: 'failed', detail: "Ollama isn't running. Start it and try again." }],
    })
    await page.goto(SETUP)

    await page.getByRole('button', { name: 'Start episode 2' }).click()

    await expect(page.getByRole('status')).toHaveText("The hosts couldn't catch up on episode 1. Ollama isn't running. Start it and try again.")
    await expect(page.getByRole('button', { name: 'Try again' })).toBeVisible()
    const started = startRequest(page)
    await page.getByRole('button', { name: 'Start without it' }).click()
    expect((await started).postDataJSON().kind).toBe('series')
    await expect(page).toHaveURL(/\/podcasts\/episodes\/57/)
  })
})

test.describe('Podcast series — consistent hosts (010 US3)', () => {
  const recastDetail = seriesDetailFixture({
    hosts: [
      seriesDetailFixture().hosts[0],
      { ...seriesDetailFixture().hosts[1], name: 'Pablo', personality_id: 'joker', personality_label: 'Joker', has_history: false, is_new_next_episode: true },
    ],
  })

  async function openSetup(page: Page, preferences?: { learner_name: string | null }) {
    await mockHomeApis(page)
    await mockPodcastApis(page, { catalog: catalogWithSeries(), episode: seriesEpisodeFixture() })
    if (preferences) {
      await page.unroute('/api/podcasts/preferences')
      await page.route('/api/podcasts/preferences', (route) =>
        route.fulfill({ json: { last_format: 'panel', is_show_text_on: false, interests: [], ...preferences } }),
      )
    }
    await mockSeriesApis(page)
    await page.goto(SETUP)
    await expect(page.getByRole('button', { name: 'Start episode 2' })).toBeVisible()
  }

  test('a series episode has no Shuffle and no personality drop-down', async ({ page }) => {
    await openSetup(page)

    await expect(page.getByRole('button', { name: /Shuffle/ })).toHaveCount(0)
    await expect(page.getByRole('combobox')).toHaveCount(0)
  })

  test('Recast… then Cancel sends nothing', async ({ page }) => {
    await openSetup(page, { learner_name: 'Sam' })
    const recasts: unknown[] = []
    await page.route('/api/podcasts/series/4/hosts/**', (route) => {
      recasts.push(route.request().postDataJSON())
      return route.fulfill({ json: recastDetail })
    })

    await page.getByRole('button', { name: 'Recast Inés' }).click()
    await expect(page.getByRole('alertdialog')).toContainText("won't know what was said in earlier episodes")
    await page.getByRole('button', { name: 'Cancel' }).click()

    await expect(page.getByRole('alertdialog')).toHaveCount(0)
    expect(recasts).toEqual([])
  })

  test('Recast… with a chosen personality posts it and shows the new host', async ({ page }) => {
    await openSetup(page, { learner_name: 'Sam' })
    const recast = page.waitForRequest((request) => request.url().endsWith('/series/4/hosts/second/recast'))
    await page.route('/api/podcasts/series/4/hosts/second/recast', (route) => route.fulfill({ json: recastDetail }))

    await page.getByRole('button', { name: 'Recast Inés' }).click()
    await page.getByRole('combobox', { name: "The new host's personality" }).click()
    await page.getByRole('option', { name: 'Joker' }).click()
    await page.getByRole('button', { name: 'Recast', exact: true }).click()

    expect((await recast).postDataJSON()).toEqual({ language: 'es', learner_name: 'Sam', personality_id: 'joker' })
    await expect(page.getByText('Pablo', { exact: true })).toBeVisible()
    await expect(page.getByText('Inés', { exact: true })).toHaveCount(0)
  })

  test('the remembered points are listed', async ({ page }) => {
    await openSetup(page)

    await page.getByRole('button', { name: 'What the hosts remember' }).click()

    await expect(page.getByText('Why we yawn')).toBeVisible()
    await expect(page.getByText('You hate mornings.')).toBeVisible()
  })

  test('Start over asks first, then forgets the series', async ({ page }) => {
    await openSetup(page)
    const resets: string[] = []
    await page.route('/api/podcasts/series/4', (route) => {
      if (route.request().method() !== 'DELETE') return route.fallback()
      resets.push(route.request().url())
      return route.fulfill({ status: 204, body: '' })
    })
    await page.unroute('/api/podcasts/catalog')
    await page.route('/api/podcasts/catalog', (route) => route.fulfill({ json: catalogWithSeries({ ...seriesShowFixture, series: null }) }))

    await page.getByRole('button', { name: 'What the hosts remember' }).click()
    await page.getByRole('button', { name: 'Start over…' }).click()
    await page.getByRole('button', { name: 'Start over', exact: true }).click()

    expect(resets).toHaveLength(1)
    await expect(page.getByRole('button', { name: 'Start episode 1' })).toBeVisible()
  })

  test('a name clash with a series host is pointed out', async ({ page }) => {
    await openSetup(page, { learner_name: 'Hugo' })

    await expect(page.getByRole('status')).toHaveText('Hugo has the same name as you. Change the name the hosts call you.')
  })
})
