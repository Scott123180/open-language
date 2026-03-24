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

  test('delete word removes it from the list', async ({ page }) => {
    await page.route('/api/flashcards/words/1', (route) => {
      if (route.request().method() === 'DELETE') {
        return route.fulfill({ status: 204, body: '' })
      }
    })
    const wordsAfterDelete = mockWords.filter((w) => w.id !== 1)
    await page.route('/api/flashcards/words**', (route) => route.fulfill({ json: wordsAfterDelete }))

    const deleteButtons = page.getByRole('button', { name: /delete/i })
    await deleteButtons.first().click()
    await expect(page.getByText('bonjour')).not.toBeVisible()
  })

  test('classify dropdown updates word classification', async ({ page }) => {
    const updatedWord = { ...mockWords[0], classification: 'difficult' }
    await page.route('/api/flashcards/words/1/classification', (route) => {
      if (route.request().method() === 'PATCH') {
        return route.fulfill({ json: updatedWord })
      }
    })
    const updatedWords = [updatedWord, ...mockWords.slice(1)]
    await page.route('/api/flashcards/words**', (route) => route.fulfill({ json: updatedWords }))

    const selects = page.getByRole('combobox', { name: /change classification/i })
    await selects.first().selectOption('difficult')
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

// ── T047: Deck config panel tests ─────────────────────────────────────────────

test.describe('Deck configuration panel', () => {
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

  test('New Deck button shows config panel', async ({ page }) => {
    await page.getByRole('button', { name: /new deck/i }).click()
    await expect(page.getByText('Configure Deck')).toBeVisible()
  })

  test('config panel shows size presets', async ({ page }) => {
    await page.getByRole('button', { name: /new deck/i }).click()
    await expect(page.getByRole('button', { name: '10' })).toBeVisible()
    await expect(page.getByRole('button', { name: '20' })).toBeVisible()
    await expect(page.getByRole('button', { name: '40' })).toBeVisible()
  })

  test('config panel has practice mode dropdown', async ({ page }) => {
    await page.getByRole('button', { name: /new deck/i }).click()
    await expect(page.getByRole('combobox', { name: /practice mode/i })).toBeVisible()
  })

  test('config panel has algorithm dropdown', async ({ page }) => {
    await page.getByRole('button', { name: /new deck/i }).click()
    await expect(page.getByRole('combobox', { name: /generation algorithm/i })).toBeVisible()
  })

  test('Generate button creates deck and closes panel', async ({ page }) => {
    await page.getByRole('button', { name: /new deck/i }).click()
    await page.getByRole('button', { name: '10' }).click()
    await page.getByRole('button', { name: /generate/i }).click()
    // Panel closes after successful creation
    await expect(page.getByText('Configure Deck')).not.toBeVisible()
  })

  test('Cancel button closes config panel', async ({ page }) => {
    await page.getByRole('button', { name: /new deck/i }).click()
    await expect(page.getByText('Configure Deck')).toBeVisible()
    await page.getByRole('button', { name: /cancel/i }).click()
    await expect(page.getByText('Configure Deck')).not.toBeVisible()
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
