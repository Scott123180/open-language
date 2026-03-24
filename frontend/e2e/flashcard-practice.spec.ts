import { test, expect } from '@playwright/test'

// ── Mock data ─────────────────────────────────────────────────────────────────

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
    source_conversation_id: null,
  },
]

const mockDeck = {
  id: 1,
  name: 'Deck — Mar 22, 2026',
  practice_mode: 'recall',
  algorithm: 'mixed_review',
  requested_size: 2,
  actual_size: 2,
  size_adjusted: false,
  created_at: '2026-03-22T10:00:00Z',
  cards: [
    { position: 0, vocabulary_item_id: 1, word: 'bonjour', translation: 'hello', fill_blank_sentence: null },
    { position: 1, vocabulary_item_id: 2, word: 'merci', translation: 'thank you', fill_blank_sentence: null },
  ],
}

const mockSession = {
  id: 42,
  deck_id: 1,
  practice_mode: 'recall',
  total_cards: 2,
  started_at: '2026-03-22T10:00:00Z',
}

const mockSummary = {
  session_id: 42,
  completed: true,
  cards_reviewed: 2,
  total_cards: 2,
  knew_it_count: 1,
  guessed_count: 1,
  didnt_know_count: 0,
  duration_seconds: 120,
  current_streak: 3,
  words_needing_work: [
    { id: 2, word: 'merci', translation: 'thank you', rating: 'guessed' },
  ],
}

async function setupPracticeMocks(page: import('@playwright/test').Page) {
  await page.route('/api/flashcards/words**', (route) => route.fulfill({ json: mockWords }))
  await page.route('/api/flashcards/decks', (route) => {
    if (route.request().method() === 'POST') {
      return route.fulfill({ status: 201, json: mockDeck })
    }
    return route.fulfill({ json: [{ ...mockDeck, card_count: 2, last_practiced_at: null, session_count: 0, last_accuracy: null }] })
  })
  await page.route('/api/flashcards/decks/1', (route) => route.fulfill({ json: mockDeck }))
  await page.route('/api/flashcards/sessions', (route) => {
    if (route.request().method() === 'POST') {
      return route.fulfill({ status: 201, json: mockSession })
    }
  })
  await page.route('/api/flashcards/sessions/42/cards/**', (route) => {
    return route.fulfill({ json: { cards_reviewed: 1 } })
  })
  await page.route('/api/flashcards/sessions/42/end', (route) => {
    return route.fulfill({ json: mockSummary })
  })
  await page.route('/api/flashcards/sessions/42/summary', (route) => {
    return route.fulfill({ json: mockSummary })
  })
  await page.route('/api/flashcards/tts/**', (route) => route.fulfill({ status: 503, body: '' }))
}

// ── Deck list tests ────────────────────────────────────────────────────────────

test.describe('FlashcardDecks page', () => {
  test.beforeEach(async ({ page }) => {
    await setupPracticeMocks(page)
    await page.goto('/flashcards/decks')
  })

  test('shows deck list', async ({ page }) => {
    await expect(page.getByText('Deck — Mar 22, 2026')).toBeVisible()
  })

  test('shows Practice button for each deck', async ({ page }) => {
    await expect(page.getByRole('button', { name: /practice/i })).toBeVisible()
  })

  test('shows deck card count', async ({ page }) => {
    await expect(page.getByText(/2 cards/i)).toBeVisible()
  })

  test('New Deck button opens config panel', async ({ page }) => {
    await page.getByRole('button', { name: /new deck/i }).click()
    await expect(page.getByText('Configure Deck')).toBeVisible()
  })
})

// ── Practice session tests ─────────────────────────────────────────────────────

test.describe('FlashcardPractice page — Recall mode', () => {
  test.beforeEach(async ({ page }) => {
    await setupPracticeMocks(page)
    await page.goto('/flashcards/practice/42?deck_id=1')
  })

  test('shows the current card word', async ({ page }) => {
    await expect(page.getByText('bonjour')).toBeVisible()
  })

  test('shows card counter', async ({ page }) => {
    await expect(page.getByText(/card 1 of 2/i)).toBeVisible()
  })

  test('shows Flip button before card is flipped', async ({ page }) => {
    await expect(page.getByRole('button', { name: /flip/i })).toBeVisible()
  })

  test('shows self-assessment buttons after flip', async ({ page }) => {
    await page.getByRole('button', { name: /flip/i }).click()
    await expect(page.getByRole('button', { name: /didn't know/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /guessed correctly/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /knew it/i })).toBeVisible()
  })

  test('self-assessment buttons not visible before flip', async ({ page }) => {
    await expect(page.getByRole('button', { name: /didn't know/i })).not.toBeVisible()
  })

  test('rating a card moves to next card', async ({ page }) => {
    await page.getByRole('button', { name: /flip/i }).click()
    await page.getByRole('button', { name: /knew it/i }).click()
    await expect(page.getByText(/card 2 of 2/i)).toBeVisible()
  })

  test('rating the last card ends the session and navigates to summary', async ({ page }) => {
    // Rate card 1
    await page.getByRole('button', { name: /flip/i }).click()
    await page.getByRole('button', { name: /knew it/i }).click()
    // Rate card 2 (last)
    await page.getByRole('button', { name: /flip/i }).click()
    await page.getByRole('button', { name: /knew it/i }).click()
    await expect(page).toHaveURL('/flashcards/summary/42')
  })

  test('exit button ends the session and navigates to summary', async ({ page }) => {
    await page.getByRole('button', { name: /exit/i }).click()
    await expect(page).toHaveURL('/flashcards/summary/42')
  })

  test('shows audio controls', async ({ page }) => {
    await expect(page.getByRole('button', { name: /listen/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /slow/i })).toBeVisible()
  })
})

// ── T057: Listen, Produce, Fill-in-the-Blank mode E2E tests ───────────────────

test.describe('FlashcardPractice — Listen mode', () => {
  test.beforeEach(async ({ page }) => {
    const listenDeck = {
      ...mockDeck,
      practice_mode: 'listen',
      cards: [
        { position: 0, vocabulary_item_id: 1, word: 'bonjour', translation: 'hello', fill_blank_sentence: null },
        { position: 1, vocabulary_item_id: 2, word: 'merci', translation: 'thank you', fill_blank_sentence: null },
      ],
    }
    const listenSession = { ...mockSession, practice_mode: 'listen' }

    await page.route('/api/flashcards/words**', (route) => route.fulfill({ json: mockWords }))
    await page.route('/api/flashcards/decks/1', (route) => route.fulfill({ json: listenDeck }))
    await page.route('/api/flashcards/sessions', (route) => {
      if (route.request().method() === 'POST') {
        return route.fulfill({ status: 201, json: listenSession })
      }
    })
    await page.route('/api/flashcards/sessions/42/cards/**', (route) =>
      route.fulfill({ json: { cards_reviewed: 1 } }),
    )
    await page.route('/api/flashcards/sessions/42/end', (route) => route.fulfill({ json: mockSummary }))
    await page.route('/api/flashcards/sessions/42/summary', (route) => route.fulfill({ json: mockSummary }))
    await page.route('/api/flashcards/tts/**', (route) => route.fulfill({ status: 503, body: '' }))
    await page.goto('/flashcards/practice/42?deck_id=1')
  })

  test('does not show target word as text in listen mode', async ({ page }) => {
    await expect(page.getByText('bonjour')).not.toBeVisible()
  })

  test('shows audio controls in listen mode', async ({ page }) => {
    await expect(page.getByRole('button', { name: /listen/i })).toBeVisible()
  })

  test('shows flip button in listen mode', async ({ page }) => {
    await expect(page.getByRole('button', { name: /flip/i })).toBeVisible()
  })
})

test.describe('FlashcardPractice — Produce mode', () => {
  test.beforeEach(async ({ page }) => {
    const produceDeck = {
      ...mockDeck,
      practice_mode: 'produce',
      cards: [
        { position: 0, vocabulary_item_id: 1, word: 'bonjour', translation: 'hello', fill_blank_sentence: null },
        { position: 1, vocabulary_item_id: 2, word: 'merci', translation: 'thank you', fill_blank_sentence: null },
      ],
    }
    const produceSession = { ...mockSession, practice_mode: 'produce' }

    await page.route('/api/flashcards/words**', (route) => route.fulfill({ json: mockWords }))
    await page.route('/api/flashcards/decks/1', (route) => route.fulfill({ json: produceDeck }))
    await page.route('/api/flashcards/sessions', (route) => {
      if (route.request().method() === 'POST') {
        return route.fulfill({ status: 201, json: produceSession })
      }
    })
    await page.route('/api/flashcards/sessions/42/cards/**', (route) =>
      route.fulfill({ json: { cards_reviewed: 1 } }),
    )
    await page.route('/api/flashcards/sessions/42/end', (route) => route.fulfill({ json: mockSummary }))
    await page.route('/api/flashcards/sessions/42/summary', (route) => route.fulfill({ json: mockSummary }))
    await page.route('/api/flashcards/tts/**', (route) => route.fulfill({ status: 503, body: '' }))
    await page.goto('/flashcards/practice/42?deck_id=1')
  })

  test('shows native translation as prompt in produce mode', async ({ page }) => {
    await expect(page.getByText('hello')).toBeVisible()
  })

  test('does not show target word before flip in produce mode', async ({ page }) => {
    await expect(page.getByText('bonjour')).not.toBeVisible()
  })

  test('shows target word after flip in produce mode', async ({ page }) => {
    await page.getByRole('button', { name: /flip/i }).click()
    await expect(page.getByText('bonjour')).toBeVisible()
  })
})

test.describe('FlashcardPractice — Fill-in-the-Blank mode', () => {
  test.beforeEach(async ({ page }) => {
    const fitbDeck = {
      ...mockDeck,
      practice_mode: 'fill_blank',
      cards: [
        {
          position: 0,
          vocabulary_item_id: 1,
          word: 'bonjour',
          translation: 'hello',
          fill_blank_sentence: 'Je dis ___ à tout le monde.',
        },
        {
          position: 1,
          vocabulary_item_id: 2,
          word: 'merci',
          translation: 'thank you',
          fill_blank_sentence: 'Il dit ___ au serveur.',
        },
      ],
    }
    const fitbSession = { ...mockSession, practice_mode: 'fill_blank' }

    await page.route('/api/flashcards/words**', (route) => route.fulfill({ json: mockWords }))
    await page.route('/api/flashcards/decks/1', (route) => route.fulfill({ json: fitbDeck }))
    await page.route('/api/flashcards/sessions', (route) => {
      if (route.request().method() === 'POST') {
        return route.fulfill({ status: 201, json: fitbSession })
      }
    })
    await page.route('/api/flashcards/sessions/42/cards/**', (route) =>
      route.fulfill({ json: { cards_reviewed: 1 } }),
    )
    await page.route('/api/flashcards/sessions/42/end', (route) => route.fulfill({ json: mockSummary }))
    await page.route('/api/flashcards/sessions/42/summary', (route) => route.fulfill({ json: mockSummary }))
    await page.route('/api/flashcards/tts/**', (route) => route.fulfill({ status: 503, body: '' }))
    await page.goto('/flashcards/practice/42?deck_id=1')
  })

  test('shows fill-blank sentence with placeholder', async ({ page }) => {
    await expect(page.getByText(/Je dis ___ à tout le monde\./)).toBeVisible()
  })

  test('does not show target word before flip in fitb mode', async ({ page }) => {
    await expect(page.getByText('bonjour')).not.toBeVisible()
  })

  test('shows target word after flip in fitb mode', async ({ page }) => {
    await page.getByRole('button', { name: /flip/i }).click()
    await expect(page.getByText('bonjour')).toBeVisible()
  })
})

// ── Session Summary tests ──────────────────────────────────────────────────────

test.describe('FlashcardSummary page', () => {
  test.beforeEach(async ({ page }) => {
    await setupPracticeMocks(page)
    await page.goto('/flashcards/summary/42')
  })

  test('shows session complete heading', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /session complete/i })).toBeVisible()
  })

  test('shows knew it count', async ({ page }) => {
    await expect(page.getByText(/knew it/i)).toBeVisible()
  })

  test('shows guessed count', async ({ page }) => {
    // Multiple "1"s in the page — check for Guessed label
    await expect(page.getByText(/guessed/i)).toBeVisible()
  })

  test('shows words needing work', async ({ page }) => {
    await expect(page.getByText('merci')).toBeVisible()
  })

  test('shows streak indicator', async ({ page }) => {
    await expect(page.getByText(/3-day streak/i)).toBeVisible()
  })

  test('Back to Decks navigates correctly', async ({ page }) => {
    await page.getByRole('button', { name: /back to decks/i }).click()
    await expect(page).toHaveURL('/flashcards/decks')
  })

  test('Practice Again navigates to decks', async ({ page }) => {
    await page.getByRole('button', { name: /practice again/i }).click()
    await expect(page).toHaveURL('/flashcards/decks')
  })

  test('Back to Word List navigates to flashcards word list', async ({ page }) => {
    await page.route('/api/flashcards/words**', (route) => route.fulfill({ json: [] }))
    await page.getByRole('button', { name: /back to word list/i }).click()
    await expect(page).toHaveURL('/flashcards')
  })

  test('Practice Missed Words creates a missed deck and navigates to practice with deck_id', async ({ page }) => {
    const missedDeck = { ...mockDeck, id: 99 }
    const missedSession = { ...mockSession, id: 99, deck_id: 99 }
    await page.route('/api/flashcards/sessions/42/missed-deck', (route) =>
      route.fulfill({ status: 201, json: missedDeck }),
    )
    await page.route('/api/flashcards/sessions', (route) => {
      if (route.request().method() === 'POST') {
        return route.fulfill({ status: 201, json: missedSession })
      }
    })
    await page.route('/api/flashcards/decks/99', (route) => route.fulfill({ json: missedDeck }))
    await page.getByRole('button', { name: /practice missed words/i }).click()
    await expect(page).toHaveURL(/\/flashcards\/practice\/99\?deck_id=99/)
    await expect(page.getByText('bonjour')).toBeVisible()
  })
})

// ── Cross-page navigation flows ────────────────────────────────────────────────

test.describe('Cross-page navigation flows', () => {
  test('clicking Practice on a deck starts a session and navigates with deck_id', async ({ page }) => {
    await setupPracticeMocks(page)
    await page.goto('/flashcards/decks')
    await page.getByRole('button', { name: /start practice for/i }).click()
    await expect(page).toHaveURL(/\/flashcards\/practice\/42\?deck_id=1/)
    await expect(page.getByText('bonjour')).toBeVisible()
  })
})
