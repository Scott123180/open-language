import { test, expect, type Page } from '@playwright/test'
import {
  generatedShowFixture,
  mockHomeApis,
  mockPodcastApis,
  mockPodcastCatalog,
  mockSeriesApis,
  seriesEpisodeFixture,
  seriesShowFixture,
  showListingFixture,
} from './fixtures'

const keptShow = showListingFixture({ ...generatedShowFixture, saved_show_id: 9 })
const gameDay = mockPodcastCatalog.shows.find((show) => show.show_id === 'game-day')!

/** The ready-made list, which also holds every ready-made show in My shows, as the server's does. */
const readyMade = (mine: ReturnType<typeof showListingFixture>[]) => [
  ...mockPodcastCatalog.shows,
  ...mine.filter((show) => show.show_id && !mockPodcastCatalog.shows.some((each) => each.show_id === show.show_id)),
]

/** A catalogue whose My shows changes as the learner favourites, as the server's would. */
async function mockFavourites(page: Page, initial: ReturnType<typeof showListingFixture>[] = []) {
  let mine = [...initial]
  const puts: { show: { title: string; source: string }; is_favourite: boolean }[] = []
  await mockHomeApis(page)
  await mockPodcastApis(page, { episode: seriesEpisodeFixture() })
  await page.unroute('/api/podcasts/catalog')
  await page.route('/api/podcasts/catalog', (route) =>
    route.fulfill({
      json: {
        ...mockPodcastCatalog,
        shows: readyMade(mine).map((show) => ({ ...show, is_favourite: mine.some((m) => m.show_id === show.show_id && m.is_favourite) })),
        my_shows: mine,
      },
    }),
  )
  await page.route('/api/podcasts/favourites', (route) => {
    const body = route.request().postDataJSON()
    puts.push(body)
    const listing = { ...body.show, is_favourite: body.is_favourite }
    const keepsIt = body.is_favourite || listing.series
    mine = mine.filter((show) => show.title !== listing.title)
    if (keepsIt) mine = [listing, ...mine]
    return keepsIt ? route.fulfill({ json: listing }) : route.fulfill({ status: 204, body: '' })
  })
  return { puts }
}

test.describe('Podcast favourites and My shows (010 US4)', () => {
  test('favouriting a show sends it and adds it to My shows; unfavouriting takes it out', async ({ page }) => {
    const { puts } = await mockFavourites(page)
    await page.goto('/podcasts')
    await expect(page.getByRole('region', { name: 'My shows' })).toHaveCount(0)

    const toggle = page.getByRole('list').getByRole('button', { name: 'Favourite Game Day' })
    await toggle.click()

    expect(puts[0]).toMatchObject({ show: { title: 'Game Day' }, is_favourite: true })
    const mine = page.getByRole('region', { name: 'My shows' })
    await expect(mine.getByRole('button', { name: 'Game Day', exact: true })).toBeVisible()
    await expect(mine.getByRole('button', { name: 'Favourite Game Day' })).toHaveAttribute('aria-pressed', 'true')

    await mine.getByRole('button', { name: 'Favourite Game Day' }).click()
    await expect(page.getByRole('region', { name: 'My shows' })).toHaveCount(0)
  })

  test('a show with a series stays in My shows after unfavouriting', async ({ page }) => {
    await mockFavourites(page, [{ ...seriesShowFixture, is_favourite: true }])
    await page.goto('/podcasts')
    const mine = page.getByRole('region', { name: 'My shows' })

    await mine.getByRole('button', { name: 'Favourite Big Little Questions' }).click()

    await expect(mine.getByRole('button', { name: 'Big Little Questions', exact: true })).toContainText('Episode 2 next')
  })

  test('after a reload, the favourite is still listed', async ({ page }) => {
    await mockFavourites(page, [{ ...gameDay, is_favourite: true }])
    await page.goto('/podcasts')
    await page.reload()

    await expect(page.getByRole('region', { name: 'My shows' }).getByRole('button', { name: 'Game Day', exact: true })).toBeVisible()
  })

  test('a kept learner-made show reopens with its title and hosts', async ({ page }) => {
    await mockFavourites(page, [keptShow])
    await page.goto('/podcasts')

    await page.getByRole('region', { name: 'My shows' }).getByRole('button', { name: 'Night Shift Abroad', exact: true }).click()

    await expect(page).toHaveURL(/\/podcasts\/setup\?saved=9/)
    await expect(page.getByRole('heading', { name: 'Night Shift Abroad' })).toBeVisible()
    await expect(page.getByText('Lucía', { exact: true })).toBeVisible()
  })

  test('Remove asks first: Cancel sends nothing, Confirm removes the show', async ({ page }) => {
    await mockFavourites(page, [keptShow])
    const removed: string[] = []
    await page.route('/api/podcasts/shows/9', (route) => {
      removed.push(route.request().method())
      return route.fulfill({ status: 204, body: '' })
    })
    await page.goto('/podcasts')
    const mine = page.getByRole('region', { name: 'My shows' })

    await mine.getByRole('button', { name: 'Remove Night Shift Abroad' }).click()
    await page.getByRole('button', { name: 'Cancel' }).click()
    expect(removed).toEqual([])

    await page.unroute('/api/podcasts/catalog')
    await page.route('/api/podcasts/catalog', (route) => route.fulfill({ json: { ...mockPodcastCatalog, my_shows: [] } }))
    await mine.getByRole('button', { name: 'Remove Night Shift Abroad' }).click()
    await page.getByRole('button', { name: 'Remove', exact: true }).click()

    await expect.poll(() => removed).toEqual(['DELETE'])
    await expect(page.getByRole('region', { name: 'My shows' })).toHaveCount(0)
  })

  test('a favourite’s next episode starts in two choices from the Podcasts screen (SC-005)', async ({ page }) => {
    await mockFavourites(page, [{ ...seriesShowFixture, is_favourite: true }])
    await mockSeriesApis(page)
    await page.goto('/podcasts')
    const started = page.waitForRequest((request) => request.url().endsWith('/api/podcasts/episodes') && request.method() === 'POST')

    await page.getByRole('region', { name: 'My shows' }).getByRole('button', { name: 'Big Little Questions', exact: true }).click()
    await page.getByRole('button', { name: 'Start episode 2' }).click()

    expect((await started).postDataJSON().kind).toBe('series')
  })
})
