import { test, expect, type Page } from '@playwright/test'
import {
  generatedShowFixture,
  IDEA_DECLINED,
  IDEA_NEEDED,
  mockHomeApis,
  mockPodcastApis,
  mockPodcastCatalog,
  mockPodcastPreferences,
  mockShowGeneration,
} from './fixtures'

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

test.describe('Podcasts — fewer than two voices', () => {
  test('choosing Listen with one voice says the hosts will share it', async ({ page }) => {
    const notice = 'Only one Spanish voice is installed, so both hosts will share it.'
    await mockHomeApis(page)
    await mockPodcastApis(page, {
      catalog: { ...mockPodcastCatalog, voices: { installed_count: 1, shared_voice_notice: notice, unavailable_message: null } },
    })
    await page.goto('/podcasts/setup?show=weekend-food-talk')
    await expect(page.getByText(notice)).toHaveCount(0)

    await page.getByRole('radio', { name: /Listen/ }).click()

    await expect(page.getByRole('status').filter({ hasText: notice })).toBeVisible()
  })
})

test.describe('Podcasts — generator and Surprise me (US4)', () => {
  test.beforeEach(async ({ page }) => {
    await mockHomeApis(page)
    await mockPodcastApis(page)
  })

  const generate = async (page: Page, idea: string) => {
    await page.goto('/podcasts')
    await page.getByLabel('Your show idea').fill(idea)
    await page.getByRole('button', { name: 'Generate' }).click()
  }

  test('generating an idea opens setup with the generated show', async ({ page }) => {
    const requests = await mockShowGeneration(page, [generatedShowFixture])

    await generate(page, 'living abroad as a nurse')

    await expect(page).toHaveURL(/\/podcasts\/setup$/)
    await expect(page.getByRole('heading', { name: 'Night Shift Abroad' })).toBeVisible()
    expect(requests[0]).toEqual({ idea: 'living abroad as a nurse', avoid_titles: [] })
  })

  test('Another version brings a different title and avoids the first', async ({ page }) => {
    const requests = await mockShowGeneration(page, [generatedShowFixture, { ...generatedShowFixture, title: 'Far From Home' }])
    await generate(page, 'living abroad as a nurse')
    await expect(page.getByRole('heading', { name: 'Night Shift Abroad' })).toBeVisible()

    await page.getByRole('button', { name: 'Another version' }).click()

    await expect(page.getByRole('heading', { name: 'Far From Home' })).toBeVisible()
    expect(requests[1]).toEqual({ idea: 'living abroad as a nurse', avoid_titles: ['Night Shift Abroad'] })
  })

  test('a blank idea is refused with the offer of Surprise me', async ({ page }) => {
    await mockShowGeneration(page, [{ detail: IDEA_NEEDED }])

    await generate(page, '   ')

    await expect(page.getByRole('alert')).toHaveText(IDEA_NEEDED)
    await expect(page.getByRole('button', { name: 'Surprise me' })).toBeEnabled()
  })

  test('a declined idea is refused with the offer of Surprise me', async ({ page }) => {
    await mockShowGeneration(page, [{ detail: IDEA_DECLINED }])

    await generate(page, 'something nasty')

    await expect(page.getByRole('alert')).toHaveText(IDEA_DECLINED)
    await expect(page).toHaveURL(/\/podcasts$/)
    await expect(page.getByRole('button', { name: 'Surprise me' })).toBeEnabled()
  })

  test('saving interests sends them to the preferences', async ({ page }) => {
    await page.goto('/podcasts')
    await page.getByText('Your interests').click()
    await page.getByLabel(/Interests/).fill('football, cooking')
    const saved = page.waitForRequest((request) => request.url().endsWith('/api/podcasts/preferences') && request.method() === 'PUT')

    await page.getByRole('button', { name: 'Save interests' }).click()

    expect((await saved).postDataJSON()).toEqual({ interests: ['football', 'cooking'] })
  })

  test('Surprise me opens setup with the surprise show and no Another version', async ({ page }) => {
    await page.route('/api/podcasts/shows/surprise', (route) =>
      route.fulfill({ json: { ...generatedShowFixture, source: 'surprise', title: 'Chess by Candlelight' } }),
    )
    await page.goto('/podcasts')

    await page.getByRole('button', { name: 'Surprise me' }).click()

    await expect(page.getByRole('heading', { name: 'Chess by Candlelight' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Another version' })).toHaveCount(0)
  })

  test('setup without a show returns to Podcasts with a plain message', async ({ page }) => {
    await page.goto('/podcasts/setup')

    await expect(page).toHaveURL(/\/podcasts$/)
    await expect(page.getByText("That show wasn't kept. Generate it again, or pick another one.")).toBeVisible()
  })
})
