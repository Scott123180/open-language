import { test, expect } from '@playwright/test'
import { mockHomeApis, mockScenario } from './fixtures'

// ── Mock word data ─────────────────────────────────────────────────────────────

const mockWords = [
  {
    id: 1,
    word: 'bonjour',
    translation: 'hello',
    target_language: 'fr',
    native_language: 'en',
    classification: 'not_practiced',
    manual_override: false,
    saved_at: '2026-03-20T10:00:00Z',
    source_conversation_id: null,
  },
  {
    id: 2,
    word: 'merci',
    translation: 'thank you',
    target_language: 'fr',
    native_language: 'en',
    classification: 'difficult',
    manual_override: false,
    saved_at: '2026-03-21T10:00:00Z',
    source_conversation_id: 1,
  },
  {
    id: 3,
    word: 'au revoir',
    translation: 'goodbye',
    target_language: 'fr',
    native_language: 'en',
    classification: 'learned',
    manual_override: false,
    saved_at: '2026-03-22T10:00:00Z',
    source_conversation_id: null,
  },
]

async function mockFlashcardApis(page: import('@playwright/test').Page, words = mockWords) {
  await page.route('/api/flashcards/words**', (route) => {
    const url = new URL(route.request().url())
    const classifications = url.searchParams.getAll('classification')
    const search = url.searchParams.get('search') ?? ''
    let filtered = words
    if (classifications.length > 0) {
      filtered = filtered.filter((w) => classifications.includes(w.classification))
    }
    if (search) {
      filtered = filtered.filter(
        (w) =>
          w.word.toLowerCase().includes(search.toLowerCase()) ||
          w.translation.toLowerCase().includes(search.toLowerCase()),
      )
    }
    return route.fulfill({ json: filtered })
  })
}

// ── Tests ──────────────────────────────────────────────────────────────────────

test.describe('Flashcards word list', () => {
  test.beforeEach(async ({ page }) => {
    await mockFlashcardApis(page)
    await page.goto('/flashcards')
  })

  test('displays all saved words', async ({ page }) => {
    await expect(page.getByText('bonjour')).toBeVisible()
    await expect(page.getByText('merci')).toBeVisible()
    await expect(page.getByText('au revoir')).toBeVisible()
  })

  test('displays word translations', async ({ page }) => {
    await expect(page.getByText('hello')).toBeVisible()
    await expect(page.getByText('thank you')).toBeVisible()
    await expect(page.getByText('goodbye')).toBeVisible()
  })

  test('shows word count in footer', async ({ page }) => {
    await expect(page.getByText('3 words')).toBeVisible()
  })

  test('Practice button is enabled when words exist', async ({ page }) => {
    const btn = page.getByRole('button', { name: 'Practice', exact: true })
    await expect(btn).toBeVisible()
    await expect(btn).not.toBeDisabled()
  })

  test('Practice button is disabled when no words', async ({ page }) => {
    await page.route('/api/flashcards/words**', (route) => route.fulfill({ json: [] }))
    await page.reload()
    const btn = page.getByRole('button', { name: 'Practice', exact: true })
    await expect(btn).toBeDisabled()
  })

  test('empty state message shown when no words', async ({ page }) => {
    await page.route('/api/flashcards/words**', (route) => route.fulfill({ json: [] }))
    await page.reload()
    await expect(page.getByText(/no words found/i)).toBeVisible()
  })

  test('filter by classification shows only matching words', async ({ page }) => {
    await page.getByRole('button', { name: 'Difficult' }).click()
    await expect(page.getByText('merci')).toBeVisible()
    await expect(page.getByText('bonjour')).not.toBeVisible()
    await expect(page.getByText('au revoir')).not.toBeVisible()
  })

  test('filter by multiple classifications', async ({ page }) => {
    await page.getByRole('button', { name: 'Difficult' }).click()
    await page.getByRole('button', { name: 'Learned', exact: true }).click()
    await expect(page.getByText('merci')).toBeVisible()
    await expect(page.getByText('au revoir')).toBeVisible()
    await expect(page.getByText('bonjour')).not.toBeVisible()
  })

  test('search filters words by text', async ({ page }) => {
    await page.getByRole('searchbox').fill('bonjour')
    await expect(page.getByText('bonjour')).toBeVisible()
    await expect(page.getByText('merci')).not.toBeVisible()
  })

  test('delete word shows confirm prompt then removes it', async ({ page }) => {
    let deleted = false
    await page.route('/api/flashcards/words**', (route) => {
      if (route.request().method() === 'DELETE') {
        deleted = true
        return route.fulfill({ status: 204, body: '' })
      }
      return route.fulfill({ json: deleted ? mockWords.filter((w) => w.id !== 1) : mockWords })
    })

    await page.getByRole('button', { name: /delete bonjour/i }).click()
    await expect(page.getByRole('button', { name: /delete\?/i })).toBeVisible()
    await page.getByRole('button', { name: /delete\?/i }).click()
    await expect(page.getByText('bonjour')).not.toBeVisible()
  })

  test('delete cancel restores trash button without deleting', async ({ page }) => {
    await page.getByRole('button', { name: /delete bonjour/i }).click()
    await page.getByRole('button', { name: /cancel/i }).first().click()
    await expect(page.getByText('bonjour')).toBeVisible()
    await expect(page.getByRole('button', { name: /delete bonjour/i })).toBeVisible()
  })

  test('sort dropdown changes word order', async ({ page }) => {
    const sortSelect = page.getByRole('combobox', { name: /sort/i })
    await expect(sortSelect).toBeVisible()
    await sortSelect.selectOption('word_asc')
    await expect(sortSelect).toHaveValue('word_asc')
  })

  test('This week chip sets date filter', async ({ page }) => {
    await page.route('/api/flashcards/words**', (route) => {
      const url = new URL(route.request().url())
      const dateFrom = url.searchParams.get('date_from')
      const filtered = dateFrom ? mockWords.filter((w) => w.saved_at >= dateFrom) : mockWords
      return route.fulfill({ json: filtered })
    })
    await page.getByRole('button', { name: /this week/i }).click()
    await expect(page.getByRole('button', { name: /this week/i })).toHaveAttribute('aria-pressed', 'true')
  })

  test('This month chip toggles off when clicked again', async ({ page }) => {
    await page.getByRole('button', { name: /this month/i }).click()
    await expect(page.getByRole('button', { name: /this month/i })).toHaveAttribute('aria-pressed', 'true')
    await page.getByRole('button', { name: /this month/i }).click()
    await expect(page.getByRole('button', { name: /this month/i })).toHaveAttribute('aria-pressed', 'false')
  })

  test('Select button enters selection mode with checkboxes', async ({ page }) => {
    await page.getByRole('button', { name: /delete multiple/i }).click()
    await expect(page.getByRole('checkbox').first()).toBeVisible()
  })

  test('bulk delete: select words then confirm deletion', async ({ page }) => {
    let bulkDeleted = false
    await page.route('/api/flashcards/words**', (route) => {
      if (route.request().method() === 'DELETE') {
        bulkDeleted = true
        return route.fulfill({ json: { deleted: 2 } })
      }
      return route.fulfill({ json: bulkDeleted ? [mockWords[2]] : mockWords })
    })

    await page.getByRole('button', { name: /delete multiple/i }).click()
    const checkboxes = page.getByRole('checkbox')
    await checkboxes.nth(0).click()
    await checkboxes.nth(1).click()
    await expect(page.getByText(/2 words selected/i)).toBeVisible()
    await page.getByRole('button', { name: /delete 2 words/i }).click()
    await expect(page.getByRole('dialog')).toBeVisible()
    await page.getByRole('dialog').getByRole('button', { name: /^delete$/i }).click()
    expect(bulkDeleted).toBe(true)
  })

  test('bulk delete: cancel modal keeps words', async ({ page }) => {
    await page.getByRole('button', { name: /delete multiple/i }).click()
    await page.getByRole('checkbox').first().click()
    await page.getByRole('button', { name: /delete 1 word/i }).click()
    await expect(page.getByRole('dialog')).toBeVisible()
    await page.getByRole('dialog').getByRole('button', { name: /cancel/i }).click()
    await expect(page.getByRole('dialog')).not.toBeVisible()
    await expect(page.getByText('bonjour')).toBeVisible()
  })

  test('navigates to home via back button', async ({ page }) => {
    await mockHomeApis(page)
    await page.route('/api/scenarios/current', (route) => route.fulfill({ json: mockScenario }))
    await page.getByRole('button', { name: /back to home/i }).click()
    await expect(page).toHaveURL('/')
  })

  test('navigates to my decks via link', async ({ page }) => {
    await page.getByRole('button', { name: /my decks/i }).click()
    await expect(page).toHaveURL('/flashcards/decks')
  })
})

// ── T047: Deck creation wizard tests ──────────────────────────────────────────

test.describe('Deck creation wizard', () => {
  test.beforeEach(async ({ page }) => {
    const deckList = [
      {
        id: 1,
        name: 'Test Deck',
        practice_mode: 'recall',
        algorithm: 'mixed_review',
        card_count: 2,
        created_at: '2026-03-22T10:00:00Z',
        last_practiced_at: null,
        session_count: 0,
        last_accuracy: null,
      },
    ]
    const createdDeck = {
      id: 2,
      name: 'Deck — Mar 22, 2026',
      practice_mode: 'recall',
      algorithm: 'mixed_review',
      requested_size: 10,
      actual_size: 3,
      size_adjusted: true,
      created_at: '2026-03-22T10:00:00Z',
      cards: [],
    }
    await page.route('/api/flashcards/decks', (route) => {
      if (route.request().method() === 'POST') {
        return route.fulfill({ status: 201, json: createdDeck })
      }
      return route.fulfill({ json: deckList })
    })
    await page.goto('/flashcards/decks')
  })

  test('New Deck button opens wizard modal', async ({ page }) => {
    await page.getByRole('button', { name: /new deck/i }).click()
    await expect(page.getByRole('dialog')).toBeVisible()
    await expect(page.getByText('How many cards?')).toBeVisible()
  })

  test('step 1 shows size preset tiles', async ({ page }) => {
    await page.getByRole('button', { name: /new deck/i }).click()
    await expect(page.getByRole('button', { name: '10' })).toBeVisible()
    await expect(page.getByRole('button', { name: '20' })).toBeVisible()
    await expect(page.getByRole('button', { name: '40' })).toBeVisible()
    await expect(page.getByRole('button', { name: /custom/i })).toBeVisible()
  })

  test('Next advances from size step to practice mode step', async ({ page }) => {
    await page.getByRole('button', { name: /new deck/i }).click()
    await page.getByRole('button', { name: '10' }).click()
    await page.getByRole('button', { name: /next/i }).click()
    await expect(page.getByText('How do you want to practice?')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Recall See the word, recall its translation' })).toBeVisible()
    await expect(page.getByRole('button', { name: /listen/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /produce/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /fill in the blank/i })).toBeVisible()
  })

  test('Next advances from practice mode step to word selection step', async ({ page }) => {
    await page.getByRole('button', { name: /new deck/i }).click()
    await page.getByRole('button', { name: '10' }).click()
    await page.getByRole('button', { name: /next/i }).click()
    await page.getByRole('button', { name: /next/i }).click()
    await expect(page.getByText('Which words?')).toBeVisible()
    await expect(page.getByRole('button', { name: /mixed review/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /new words/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /difficult/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /almost learned/i })).toBeVisible()
  })

  test('Back returns to previous step', async ({ page }) => {
    await page.getByRole('button', { name: /new deck/i }).click()
    await page.getByRole('button', { name: '10' }).click()
    await page.getByRole('button', { name: /next/i }).click()
    await expect(page.getByText('How do you want to practice?')).toBeVisible()
    await page.getByRole('button', { name: /back/i }).click()
    await expect(page.getByText('How many cards?')).toBeVisible()
  })

  test('Generate Deck creates deck and closes modal', async ({ page }) => {
    await page.getByRole('button', { name: /new deck/i }).click()
    await page.getByRole('button', { name: '10' }).click()
    await page.getByRole('button', { name: /next/i }).click()
    await page.getByRole('button', { name: /next/i }).click()
    await page.getByRole('button', { name: /generate deck/i }).click()
    await expect(page.getByRole('dialog')).not.toBeVisible()
  })

  test('Cancel button on step 1 closes modal', async ({ page }) => {
    await page.getByRole('button', { name: /new deck/i }).click()
    await expect(page.getByRole('dialog')).toBeVisible()
    await page.getByRole('button', { name: /cancel/i }).click()
    await expect(page.getByRole('dialog')).not.toBeVisible()
  })

  test('Close button dismisses modal', async ({ page }) => {
    await page.getByRole('button', { name: /new deck/i }).click()
    await expect(page.getByRole('dialog')).toBeVisible()
    await page.getByRole('button', { name: /close/i }).click()
    await expect(page.getByRole('dialog')).not.toBeVisible()
  })

  test('Escape key dismisses modal', async ({ page }) => {
    await page.getByRole('button', { name: /new deck/i }).click()
    await expect(page.getByRole('dialog')).toBeVisible()
    await page.keyboard.press('Escape')
    await expect(page.getByRole('dialog')).not.toBeVisible()
  })

  test('clicking backdrop dismisses modal', async ({ page }) => {
    await page.getByRole('button', { name: /new deck/i }).click()
    await expect(page.getByRole('dialog')).toBeVisible()
    await page.mouse.click(10, 10)
    await expect(page.getByRole('dialog')).not.toBeVisible()
  })
})

test.describe('Flashcards navigation from home', () => {
  test('Flashcards link on home navigates to word list', async ({ page }) => {
    await mockFlashcardApis(page)
    await page.route('/api/scenarios/current', (route) =>
      route.fulfill({ json: mockScenario }),
    )
    await page.goto('/')
    await page.getByRole('link', { name: 'Flashcards' }).click()
    await expect(page).toHaveURL('/flashcards')
    await expect(page.getByText('bonjour')).toBeVisible()
  })
})
