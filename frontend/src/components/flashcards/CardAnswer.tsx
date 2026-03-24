import { useState } from 'react'
import * as api from '../../services/flashcardsApi'
import type { LlmCacheType } from '../../services/flashcardsApi'

interface Props {
  vocabularyItemId: number
  isFlipped: boolean
}

const INFO_BUTTONS: Array<{ cacheType: LlmCacheType; label: string }> = [
  { cacheType: 'meanings', label: 'All Meanings' },
  { cacheType: 'usage', label: 'Usage & Sentences' },
  { cacheType: 'phrases', label: 'Common Phrases' },
  { cacheType: 'similar', label: 'Similar Words' },
]

interface InfoState {
  content: string | null
  loading: boolean
  error: boolean
}

export default function CardAnswer({ vocabularyItemId, isFlipped }: Props) {
  const [activeType, setActiveType] = useState<LlmCacheType | null>(null)
  const [infoState, setInfoState] = useState<InfoState>({ content: null, loading: false, error: false })

  if (!isFlipped) return null

  async function handleInfoClick(cacheType: LlmCacheType) {
    if (activeType === cacheType && infoState.content) return
    setActiveType(cacheType)
    setInfoState({ content: null, loading: true, error: false })
    try {
      const result = await api.fetchWordInfo(vocabularyItemId, cacheType)
      setInfoState({ content: result.content, loading: false, error: false })
    } catch {
      setInfoState({ content: null, loading: false, error: true })
    }
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        padding: '12px 0',
      }}
    >
      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
        {INFO_BUTTONS.map(({ cacheType, label }) => (
          <button
            key={cacheType}
            onClick={() => handleInfoClick(cacheType)}
            style={{
              padding: '6px 14px',
              fontSize: '0.8rem',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius)',
              background: activeType === cacheType ? 'var(--color-primary)' : 'var(--color-surface)',
              color: activeType === cacheType ? '#fff' : 'var(--color-text)',
              cursor: 'pointer',
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {infoState.loading && (
        <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>Loading…</p>
      )}

      {infoState.content && !infoState.loading && (
        <p
          style={{
            fontSize: '0.9rem',
            lineHeight: 1.6,
            color: 'var(--color-text)',
            margin: 0,
            whiteSpace: 'pre-wrap',
          }}
        >
          {infoState.content}
        </p>
      )}

      {infoState.error && (
        <p style={{ fontSize: '0.85rem', color: 'red' }}>
          Content unavailable. Please try again.
        </p>
      )}
    </div>
  )
}
