import { test, expect } from '@playwright/test'
import { mockHomeApis, mockPodcastApis, mockPodcastCatalog, mockPodcastPreferences } from './fixtures'

test.describe('Podcasts', () => {
  test.beforeEach(async ({ page }) => {
    await mockHomeApis(page)
    await mockPodcastApis(page)
  })

  test('Home leads to at least six show cards with title, topic, hosts and role', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('link', { name: 'Podcasts' }).click()

    await expect(page.getByRole('heading', { name: 'Podcasts' })).toBeVisible()
    const cards = page.getByRole('list').getByRole('button')
    await expect(cards).toHaveCount(mockPodcastCatalog.shows.length)
    expect(mockPodcastCatalog.shows.length).toBeGreaterThanOrEqual(6)
    const food = page.getByRole('button', { name: 'Weekend Food Talk' })
    await expect(food).toContainText('Topic: food')
    await expect(food).toContainText('Lucía (Enthusiast) & Marco (Dry sceptic)')
    await expect(food).toContainText("You're the guest")
  })

  test('choosing a show opens its setup on One host and Medium', async ({ page }) => {
    await page.goto('/podcasts')
    await page.getByRole('button', { name: 'Weekend Food Talk' }).click()

    await expect(page).toHaveURL(/\/podcasts\/setup\?show=weekend-food-talk/)
    await expect(page.getByRole('heading', { name: 'Weekend Food Talk' })).toBeVisible()
    await expect(page.getByRole('radio', { name: /One host/ })).toBeChecked()
    await expect(page.getByRole('radio', { name: /Medium/ })).toBeChecked()
  })

  test('Start episode lands on the episode', async ({ page }) => {
    await page.goto('/podcasts/setup?show=weekend-food-talk')
    const started = page.waitForRequest((request) => request.url().endsWith('/api/podcasts/episodes') && request.method() === 'POST')

    await page.getByRole('button', { name: 'Start episode' }).click()

    const body = (await started).postDataJSON()
    expect(body).toMatchObject({ format: 'one_host', length: 'medium', show: { show_id: 'weekend-food-talk' } })
    await expect(page).toHaveURL(/\/podcasts\/episodes\/57/)
  })

  test('the setup starts on the format used last', async ({ page }) => {
    await page.unroute('/api/podcasts/preferences')
    await page.route('/api/podcasts/preferences', (route) =>
      route.fulfill({ json: { ...mockPodcastPreferences, last_format: 'panel' } }),
    )

    await page.goto('/podcasts/setup?show=weekend-food-talk')

    await expect(page.getByRole('radio', { name: /Panel/ })).toBeChecked()
  })

  test('an unknown show returns to Podcasts with a plain message', async ({ page }) => {
    await page.goto('/podcasts/setup?show=missing')

    await expect(page).toHaveURL(/\/podcasts$/)
    await expect(page.getByText("That show isn't available any more. Pick another one.")).toBeVisible()
  })
})
