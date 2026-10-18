import { test, expect, type Page } from '@playwright/test'
import { mockHomeApis, mockPodcastApis, mockPodcastCatalog, suggestionsFixture } from './fixtures'

const others = { suggestions: suggestionsFixture.suggestions.map((show) => ({ ...show, title: `${show.title} Again` })) }

async function openPodcasts(page: Page, replies: { status?: number; json: unknown }[]) {
  await mockHomeApis(page)
  await mockPodcastApis(page)
  const requests: { avoid_titles: string[] }[] = []
  await page.route('/api/podcasts/shows/discover', (route) => {
    requests.push(route.request().postDataJSON())
    const reply = replies[Math.min(requests.length, replies.length) - 1]
    return route.fulfill({ status: reply.status ?? 200, json: reply.json })
  })
  await page.goto('/podcasts')
  return requests
}

const readyMadeTitles = (page: Page) => page.getByRole('list').first().getByRole('button', { name: /^(?!Favourite )/ }).allTextContents()

test.describe('Find a new show (010 US5)', () => {
  test('shows the suggestions, and another set avoids the first', async ({ page }) => {
    const requests = await openPodcasts(page, [{ json: suggestionsFixture }, { json: others }])

    await page.getByRole('button', { name: 'Find a new show' }).click()
    await expect(page.getByRole('button', { name: 'Night Trains of Europe', exact: true })).toBeVisible()
    await page.getByRole('button', { name: 'Show me others' }).click()

    await expect(page.getByRole('button', { name: 'Night Trains of Europe Again', exact: true })).toBeVisible()
    expect(requests[1].avoid_titles).toEqual(suggestionsFixture.suggestions.map((show) => show.title))
  })

  test('favouriting a suggestion sends it as a suggested show', async ({ page }) => {
    await openPodcasts(page, [{ json: suggestionsFixture }])
    const favourite = page.waitForRequest((request) => request.url().endsWith('/api/podcasts/favourites'))
    await page.route('/api/podcasts/favourites', (route) => route.fulfill({ json: { ...route.request().postDataJSON().show, saved_show_id: 12, is_favourite: true, series: null } }))

    await page.getByRole('button', { name: 'Find a new show' }).click()
    await page.getByRole('button', { name: 'Favourite Plant Parents' }).click()

    expect((await favourite).postDataJSON()).toMatchObject({ show: { source: 'suggested', title: 'Plant Parents' }, is_favourite: true })
  })

  test('starting a suggestion opens its setup', async ({ page }) => {
    await openPodcasts(page, [{ json: suggestionsFixture }])

    await page.getByRole('button', { name: 'Find a new show' }).click()
    await page.getByRole('button', { name: 'Board Game Night', exact: true }).click()

    await expect(page).toHaveURL(/\/podcasts\/setup$/)
    await expect(page.getByRole('heading', { name: 'Board Game Night' })).toBeVisible()
  })

  test('a 503 shows its plain message and the ready-made list stays as it was', async ({ page }) => {
    const detail = "Find a new show didn't come up with enough shows this time. Please try again."
    await openPodcasts(page, [{ status: 503, json: { detail } }])
    await expect(page.getByRole('button', { name: 'Weekend Food Talk', exact: true })).toBeVisible()
    const before = await readyMadeTitles(page)

    await page.getByRole('button', { name: 'Find a new show' }).click()

    await expect(page.getByText(detail)).toBeVisible()
    expect(await readyMadeTitles(page)).toEqual(before)
    expect(before).toHaveLength(mockPodcastCatalog.shows.length)
  })
})
