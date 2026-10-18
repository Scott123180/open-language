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
