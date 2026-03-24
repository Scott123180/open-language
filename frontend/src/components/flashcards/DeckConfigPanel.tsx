import { useState } from 'react'
import * as api from '../../services/flashcardsApi'
import type { DeckDetail, GenerationAlgorithm, PracticeMode } from '../../services/flashcardsApi'

interface Props {
  onCreated: (deck: DeckDetail) => void
  onCancel: () => void
}

const SIZE_PRESETS = [10, 20, 40]

const ALGORITHMS: Array<{ value: GenerationAlgorithm; label: string; description: string }> = [
  { value: 'mixed_review', label: 'Mixed Review', description: 'Balanced mix of all classifications' },
  { value: 'not_practiced', label: 'Not Practiced', description: 'Focus on new words' },
  { value: 'difficult', label: 'Difficult Words', description: 'Focus on words you struggle with' },
  { value: 'previously_guessed', label: 'Almost Learned', description: 'Words you are close to mastering' },
]

const MODES: Array<{ value: PracticeMode; label: string }> = [
  { value: 'recall', label: 'Recall — see word, recall translation' },
  { value: 'listen', label: 'Listen — audio only, recall translation' },
  { value: 'produce', label: 'Produce — see translation, produce word' },
  { value: 'fill_blank', label: 'Fill-in-the-Blank — complete a sentence' },
]

export default function DeckConfigPanel({ onCreated, onCancel }: Props) {
  const [size, setSize] = useState(20)
  const [customSize, setCustomSize] = useState('')
  const [useCustom, setUseCustom] = useState(false)
  const [algorithm, setAlgorithm] = useState<GenerationAlgorithm>('mixed_review')
  const [mode, setMode] = useState<PracticeMode>('recall')
  const [isCreating, setIsCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sizeAdjusted, setSizeAdjusted] = useState<number | null>(null)

  const effectiveSize = useCustom ? parseInt(customSize, 10) || 0 : size

  async function handleGenerate() {
    if (effectiveSize < 1) return
    setIsCreating(true)
    setError(null)
    setSizeAdjusted(null)
    try {
      const deck = await api.createDeck({
        size: effectiveSize,
        word_source: 'all',
        practice_mode: mode,
        algorithm,
      })
      if (deck.size_adjusted) {
        setSizeAdjusted(deck.actual_size)
      }
      onCreated(deck)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create deck')
    } finally {
      setIsCreating(false)
    }
  }

  return (
    <div
      style={{
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius)',
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
        maxWidth: '480px',
      }}
    >
      <h2 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700 }}>Configure Deck</h2>

      {error && (
        <p role="alert" style={{ color: 'red', margin: 0, fontSize: '0.9rem' }}>
          {error}
        </p>
      )}

      {sizeAdjusted !== null && (
        <p style={{ color: 'var(--color-text-muted)', margin: 0, fontSize: '0.85rem' }}>
          Note: Only {sizeAdjusted} words available — deck size adjusted.
        </p>
      )}

      {/* Deck size */}
      <fieldset style={{ border: 'none', padding: 0, margin: 0 }}>
        <legend style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', marginBottom: '8px' }}>
          Deck Size
        </legend>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {SIZE_PRESETS.map((s) => (
            <button
              key={s}
              onClick={() => { setSize(s); setUseCustom(false) }}
              style={{
                padding: '6px 16px',
                border: `2px solid ${!useCustom && size === s ? 'var(--color-primary)' : 'var(--color-border)'}`,
                borderRadius: 'var(--radius)',
                background: !useCustom && size === s ? 'var(--color-primary)' : 'var(--color-surface)',
                color: !useCustom && size === s ? '#fff' : 'var(--color-text)',
                cursor: 'pointer',
                fontWeight: !useCustom && size === s ? 700 : 400,
              }}
            >
              {s}
            </button>
          ))}
          <input
            type="number"
            min={1}
            placeholder="Custom"
            value={useCustom ? customSize : ''}
            onFocus={() => setUseCustom(true)}
            onChange={(e) => { setUseCustom(true); setCustomSize(e.target.value) }}
            style={{
              width: '80px',
              padding: '6px 10px',
              border: `2px solid ${useCustom ? 'var(--color-primary)' : 'var(--color-border)'}`,
              borderRadius: 'var(--radius)',
              background: 'var(--color-bg)',
              color: 'var(--color-text)',
              fontSize: '0.9rem',
            }}
            aria-label="Custom deck size"
          />
        </div>
      </fieldset>

      {/* Practice mode */}
      <label style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
        Practice Mode
        <select
          value={mode}
          onChange={(e) => setMode(e.target.value as PracticeMode)}
          style={{
            padding: '8px 10px',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius)',
            background: 'var(--color-bg)',
            color: 'var(--color-text)',
            fontSize: '0.9rem',
          }}
        >
          {MODES.map((m) => (
            <option key={m.value} value={m.value}>{m.label}</option>
          ))}
        </select>
      </label>

      {/* Algorithm */}
      <label style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
        Generation Algorithm
        <select
          value={algorithm}
          onChange={(e) => setAlgorithm(e.target.value as GenerationAlgorithm)}
          style={{
            padding: '8px 10px',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius)',
            background: 'var(--color-bg)',
            color: 'var(--color-text)',
            fontSize: '0.9rem',
          }}
        >
          {ALGORITHMS.map((a) => (
            <option key={a.value} value={a.value}>{a.label} — {a.description}</option>
          ))}
        </select>
      </label>

      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
        <button
          onClick={onCancel}
          style={{
            padding: '10px 20px',
            background: 'none',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius)',
            color: 'var(--color-text-muted)',
            cursor: 'pointer',
          }}
        >
          Cancel
        </button>
        <button
          onClick={handleGenerate}
          disabled={isCreating || effectiveSize < 1}
          style={{
            padding: '10px 24px',
            background: 'var(--color-primary)',
            border: 'none',
            borderRadius: 'var(--radius)',
            color: 'var(--color-text-on-primary)',
            fontWeight: 600,
            cursor: isCreating || effectiveSize < 1 ? 'not-allowed' : 'pointer',
            opacity: isCreating || effectiveSize < 1 ? 0.6 : 1,
          }}
        >
          {isCreating ? 'Generating…' : 'Generate'}
        </button>
      </div>
    </div>
  )
}
