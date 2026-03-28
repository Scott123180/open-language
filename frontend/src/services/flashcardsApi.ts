const BASE = '/api/flashcards'

// ---------------------------------------------------------------------------
// TypeScript interfaces (mirror contracts/api.md)
// ---------------------------------------------------------------------------

export type WordClassification = 'not_practiced' | 'difficult' | 'almost_learned' | 'learned'
export type PracticeMode = 'recall' | 'listen' | 'produce' | 'fill_blank'
export type GenerationAlgorithm = 'not_practiced' | 'difficult' | 'previously_guessed' | 'mixed_review'
export type Rating = 'knew_it' | 'guessed' | 'didnt_know'
export type LlmCacheType = 'meanings' | 'usage' | 'phrases' | 'similar'

export interface WordListItem {
  id: number
  word: string
  translation: string
  target_language: string
  native_language: string
  classification: WordClassification
  manual_override: boolean
  saved_at: string
  source_conversation_id: number | null
}

export interface DeckCardItem {
  position: number
  vocabulary_item_id: number | null
  word: string | null
  translation: string | null
  fill_blank_sentence: string | null
}

export interface DeckDetail {
  id: number
  name: string
  practice_mode: PracticeMode
  algorithm: GenerationAlgorithm
  requested_size: number
  actual_size: number
  size_adjusted: boolean
  created_at: string
  cards: DeckCardItem[]
}

export interface DeckSummary {
  id: number
  name: string
  practice_mode: PracticeMode
  algorithm: GenerationAlgorithm
  card_count: number
  created_at: string
  last_practiced_at: string | null
  session_count: number
  last_accuracy: number | null
}

export interface SessionStarted {
  id: number
  deck_id: number | null
  practice_mode: PracticeMode
  total_cards: number
  started_at: string
}

export interface CardResultResponse {
  cards_reviewed: number
}

export interface WordNeedingWork {
  id: number
  word: string
  translation: string
  rating: Rating
}

export interface SessionSummary {
  session_id: number
  completed: boolean
  cards_reviewed: number
  total_cards: number
  knew_it_count: number
  guessed_count: number
  didnt_know_count: number
  duration_seconds: number | null
  current_streak: number
  words_needing_work: WordNeedingWork[]
}

export interface LlmCacheResponse {
  vocabulary_item_id: number
  cache_type: LlmCacheType
  content: string
  from_cache: boolean
  generated_at: string
}

export interface AccuracyPoint {
  session_id: number
  date: string
  accuracy: number
}

export interface DailyActivityPoint {
  date: string
  cards_reviewed: number
}

export interface ClassificationOverTimePoint {
  date: string
  not_practiced: number
  difficult: number
  almost_learned: number
  learned: number
}

export interface ClassificationNow {
  not_practiced: number
  difficult: number
  almost_learned: number
  learned: number
}

export interface ModePerformanceItem {
  mode: string
  accuracy: number
}

export interface AnalyticsSummary {
  at_a_glance: {
    total_words: number
    words_learned: number
    current_streak: number
    sessions_this_week: number
  }
  accuracy_trend: AccuracyPoint[]
  daily_activity: DailyActivityPoint[]
  classification_over_time: ClassificationOverTimePoint[]
  classification_now: ClassificationNow
  hardest_words: Array<{ id: number; word: string; encounters: number; success_rate: number }>
  recently_learned: Array<{ id: number; word: string; learned_at: string }>
  mode_performance: ModePerformanceItem[]
}

// ---------------------------------------------------------------------------
// Shared fetch helper
// ---------------------------------------------------------------------------

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(body.detail ?? res.statusText)
  }
  if (res.status === 204) return undefined as unknown as T
  return res.json() as Promise<T>
}

// ---------------------------------------------------------------------------
// Word library endpoints
// ---------------------------------------------------------------------------

export type WordSort = 'saved_at_desc' | 'saved_at_asc' | 'word_asc' | 'classification_desc'

export interface WordFilters {
  classification?: WordClassification[]
  date_from?: string
  date_to?: string
  search?: string
  date_preset?: 'week' | 'month'
}

export function fetchWords(filters: WordFilters = {}): Promise<WordListItem[]> {
  const params = new URLSearchParams()
  filters.classification?.forEach((c) => params.append('classification', c))
  if (filters.date_from) params.set('date_from', filters.date_from)
  if (filters.date_to) params.set('date_to', filters.date_to)
  if (filters.search) params.set('search', filters.search)
  const qs = params.toString()
  return apiFetch<WordListItem[]>(`/words${qs ? `?${qs}` : ''}`)
}

export function updateClassification(
  id: number,
  classification: WordClassification,
): Promise<WordListItem> {
  return apiFetch<WordListItem>(`/words/${id}/classification`, {
    method: 'PATCH',
    body: JSON.stringify({ classification }),
  })
}

export function deleteWord(id: number): Promise<void> {
  return apiFetch<void>(`/words/${id}`, { method: 'DELETE' })
}

export function deleteWords(ids: number[]): Promise<{ deleted: number }> {
  return apiFetch<{ deleted: number }>('/words', {
    method: 'DELETE',
    body: JSON.stringify({ ids }),
  })
}

export function fetchWordInfo(id: number, cacheType: LlmCacheType): Promise<LlmCacheResponse> {
  return apiFetch<LlmCacheResponse>(`/words/${id}/info/${cacheType}`)
}

export function getVocabTtsUrl(vocabularyItemId: number): string {
  return `${BASE}/tts/${vocabularyItemId}`
}

// ---------------------------------------------------------------------------
// Deck endpoints
// ---------------------------------------------------------------------------

export interface DeckConfigPayload {
  name?: string | null
  size: number
  word_source: 'all' | 'filtered' | 'selected'
  selected_word_ids?: number[]
  practice_mode: PracticeMode
  algorithm: GenerationAlgorithm
  filter_classifications?: WordClassification[]
  filter_date_from?: string
  filter_date_to?: string
  filter_search?: string
}

export function createDeck(payload: DeckConfigPayload): Promise<DeckDetail> {
  return apiFetch<DeckDetail>('/decks', { method: 'POST', body: JSON.stringify(payload) })
}

export function listDecks(): Promise<DeckSummary[]> {
  return apiFetch<DeckSummary[]>('/decks')
}

export function getDeck(id: number): Promise<DeckDetail> {
  return apiFetch<DeckDetail>(`/decks/${id}`)
}

export function updateDeckName(id: number, name: string): Promise<DeckSummary> {
  return apiFetch<DeckSummary>(`/decks/${id}`, { method: 'PATCH', body: JSON.stringify({ name }) })
}

export function refreshDeck(id: number): Promise<DeckDetail> {
  return apiFetch<DeckDetail>(`/decks/${id}/refresh`, { method: 'POST' })
}

export function deleteDeck(id: number): Promise<void> {
  return apiFetch<void>(`/decks/${id}`, { method: 'DELETE' })
}

// ---------------------------------------------------------------------------
// Session endpoints
// ---------------------------------------------------------------------------

export function startSession(deckId: number): Promise<SessionStarted> {
  return apiFetch<SessionStarted>('/sessions', {
    method: 'POST',
    body: JSON.stringify({ deck_id: deckId }),
  })
}

export function recordCardResult(
  sessionId: number,
  position: number,
  rating: Rating,
  responseType?: string,
  userResponse?: string,
): Promise<CardResultResponse> {
  return apiFetch<CardResultResponse>(`/sessions/${sessionId}/cards/${position}`, {
    method: 'POST',
    body: JSON.stringify({ rating, response_type: responseType ?? null, user_response: userResponse ?? null }),
  })
}

export function endSession(sessionId: number, completed: boolean): Promise<SessionSummary> {
  return apiFetch<SessionSummary>(`/sessions/${sessionId}/end`, {
    method: 'POST',
    body: JSON.stringify({ completed }),
  })
}

export function getSessionSummary(sessionId: number): Promise<SessionSummary> {
  return apiFetch<SessionSummary>(`/sessions/${sessionId}/summary`)
}

export function getEncouragement(sessionId: number): Promise<{ message: string }> {
  return apiFetch<{ message: string }>(`/sessions/${sessionId}/encouragement`)
}

export function createMissedDeck(sessionId: number): Promise<DeckDetail> {
  return apiFetch<DeckDetail>(`/sessions/${sessionId}/missed-deck`, { method: 'POST' })
}

// ---------------------------------------------------------------------------
// Analytics endpoints
// ---------------------------------------------------------------------------

export type AnalyticsRange = '7d' | '30d' | 'all'

export function fetchAnalytics(range: AnalyticsRange = '7d'): Promise<AnalyticsSummary> {
  return apiFetch<AnalyticsSummary>(`/analytics?range=${range}`)
}
