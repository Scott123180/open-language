import { test, expect } from '@playwright/test'

const mockAnalytics = {
  at_a_glance: {
    total_words: 25,
    words_learned: 8,
    current_streak: 3,
    sessions_this_week: 5,
  },
  accuracy_trend: [
    { session_id: 1, date: '2026-03-20', accuracy: 0.75 },
    { session_id: 2, date: '2026-03-21', accuracy: 0.85 },
  ],
  daily_activity: [
    { date: '2026-03-20', cards_reviewed: 10 },
    { date: '2026-03-21', cards_reviewed: 15 },
  ],
  classification_over_time: [
    { date: '2026-03-21', not_practiced: 10, difficult: 5, almost_learned: 2, learned: 8 },
  ],
  classification_now: {
    not_practiced: 10,
    difficult: 5,
    almost_learned: 2,
    learned: 8,
  },
  hardest_words: [
    { id: 2, word: 'merci', encounters: 5, success_rate: 0.2 },
  ],
  recently_learned: [
    { id: 1, word: 'bonjour', learned_at: '2026-03-21T10:00:00Z' },
  ],
  mode_performance: [
    { mode: 'recall', accuracy: 0.8 },
    { mode: 'produce', accuracy: 0.6 },
  ],
}

async function mockAnalyticsApi(page: import('@playwright/test').Page, data = mockAnalytics) {
  await page.route('/api/flashcards/analytics**', (route) => {
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(data) })
  })
}

test.describe('Analytics Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await mockAnalyticsApi(page)
    await page.goto('/flashcards/analytics')
    await page.waitForSelector('h1:has-text("Analytics")')
  })

  test('shows Analytics heading', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /analytics/i })).toBeVisible()
  })

  test('shows at-a-glance stat cards', async ({ page }) => {
    await expect(page.getByText('Total Words')).toBeVisible()
    await expect(page.getByText('Words Learned')).toBeVisible()
    await expect(page.getByText('Current Streak')).toBeVisible()
    await expect(page.getByText('Sessions This Week')).toBeVisible()
  })

  test('shows time-range toggle buttons', async ({ page }) => {
    await expect(page.getByRole('button', { name: /7 days/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /30 days/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /all time/i })).toBeVisible()
  })

  test('time-range toggle triggers new data fetch', async ({ page }) => {
    let requestCount = 0
    await page.route('/api/flashcards/analytics**', (route) => {
      requestCount++
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockAnalytics) })
    })
    await page.getByRole('button', { name: /30 days/i }).click()
    await page.waitForTimeout(300)
    expect(requestCount).toBeGreaterThanOrEqual(1)
  })

  test('shows hardest words table with word name', async ({ page }) => {
    await expect(page.getByText('merci')).toBeVisible()
    await expect(page.getByText('Hardest Words')).toBeVisible()
  })

  test('hardest word row navigates to word list on click', async ({ page }) => {
    await page.getByRole('button', { name: /view merci/i }).click()
    await expect(page).toHaveURL(/\/flashcards/)
  })

  test('shows recently learned section', async ({ page }) => {
    await expect(page.getByText('bonjour')).toBeVisible()
    await expect(page.getByText('Recently Learned')).toBeVisible()
  })

  test('back button navigates to flashcards home', async ({ page }) => {
    // Mock the words API so the flashcards page loads
    await page.route('/api/flashcards/words**', (route) => {
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
    })
    await page.getByRole('button', { name: /back/i }).click()
    await expect(page).toHaveURL('/flashcards')
  })
})
