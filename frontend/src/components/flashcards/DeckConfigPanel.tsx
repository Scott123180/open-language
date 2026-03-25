import { useState } from 'react'
import * as api from '../../services/flashcardsApi'
import type { DeckDetail, GenerationAlgorithm, PracticeMode } from '../../services/flashcardsApi'
import { IconEye, IconVolume, IconPenLine, IconTextCursor, IconShuffle, IconSparkles, IconFlame, IconTrophy } from '../shared/icons'

interface Props {
  onCreated: (deck: DeckDetail) => void
  onCancel: () => void
}

const SIZE_PRESETS = [
  { value: 10, sublabel: 'Quick session' },
  { value: 20, sublabel: 'Standard' },
  { value: 40, sublabel: 'Deep dive' },
]

const ALGORITHMS: Array<{ value: GenerationAlgorithm; label: string; description: string; icon: React.ReactNode }> = [
  { value: 'mixed_review', label: 'Mixed Review', description: 'A balanced mix of all your words', icon: <IconShuffle size={20} /> },
  { value: 'not_practiced', label: 'New Words', description: 'Focus on words you have never practiced', icon: <IconSparkles size={20} /> },
  { value: 'difficult', label: 'Difficult', description: 'Words you consistently struggle with', icon: <IconFlame size={20} /> },
  { value: 'previously_guessed', label: 'Almost Learned', description: 'Words you are close to mastering', icon: <IconTrophy size={20} /> },
]

const MODES: Array<{ value: PracticeMode; label: string; description: string; icon: React.ReactNode }> = [
  { value: 'recall', label: 'Recall', description: 'See the word, recall its translation', icon: <IconEye size={20} /> },
  { value: 'listen', label: 'Listen', description: 'Hear the audio only, recall the translation', icon: <IconVolume size={20} /> },
  { value: 'produce', label: 'Produce', description: 'See the translation, produce the word', icon: <IconPenLine size={20} /> },
  { value: 'fill_blank', label: 'Fill in the Blank', description: 'Complete a sentence with the missing word', icon: <IconTextCursor size={20} /> },
]

const STEP_HEADINGS = [
  'How many cards?',
  'How do you want to practice?',
  'Which words?',
]

const STEP_SUBTITLES = [
  'Choose a session size. You can always create more decks later.',
  'Each mode trains a different skill. Pick the one that fits today\'s goal.',
  'Focus on a specific group, or mix everything together.',
]

const TOTAL_STEPS = 3

const tileStyle = (selected: boolean): React.CSSProperties => ({
  padding: '16px 20px',
  border: `2px solid ${selected ? 'var(--color-primary)' : 'var(--color-border)'}`,
  borderRadius: 'var(--radius-lg)',
  background: selected ? 'var(--color-primary-subtle)' : 'var(--color-surface)',
  cursor: 'pointer',
  textAlign: 'left',
  display: 'flex',
  flexDirection: 'column',
  gap: '4px',
  transition: 'border-color 80ms ease, background 80ms ease',
  width: '100%',
})

export default function DeckConfigPanel({ onCreated, onCancel }: Props) {
  const [step, setStep] = useState(0)
  const [size, setSize] = useState(20)
  const [useCustom, setUseCustom] = useState(false)
  const [customSize, setCustomSize] = useState('')
  const [mode, setMode] = useState<PracticeMode>('recall')
  const [algorithm, setAlgorithm] = useState<GenerationAlgorithm>('mixed_review')
  const [isCreating, setIsCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const effectiveSize = useCustom ? parseInt(customSize, 10) || 0 : size
  const canAdvance = step === 0 ? effectiveSize >= 1 : true

  async function handleGenerate() {
    if (effectiveSize < 1) return
    setIsCreating(true)
    setError(null)
    try {
      const deck = await api.createDeck({
        size: effectiveSize,
        word_source: 'all',
        practice_mode: mode,
        algorithm,
      })
      onCreated(deck)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create deck')
      setIsCreating(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>

      {/* Progress dots */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
        {Array.from({ length: TOTAL_STEPS }).map((_, i) => (
          <div
            key={i}
            style={{
              height: '8px',
              width: i === step ? '24px' : '8px',
              borderRadius: '9999px',
              background: i === step
                ? 'var(--color-primary)'
                : i < step
                ? 'var(--color-primary-subtle)'
                : 'var(--color-border)',
              transition: 'width 150ms ease, background 150ms ease',
            }}
          />
        ))}
      </div>

      {/* Step heading */}
      <div style={{ textAlign: 'center' }}>
        <p style={{
          margin: '0 0 8px',
          fontSize: '0.75rem',
          fontWeight: 600,
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
          color: 'var(--color-text-muted)',
        }}>
          Step {step + 1} of {TOTAL_STEPS}
        </p>
        <h2 style={{
          margin: '0 0 8px',
          fontSize: '1.75rem',
          fontWeight: 700,
          letterSpacing: '-0.02em',
          color: 'var(--color-text)',
        }}>
          {STEP_HEADINGS[step]}
        </h2>
        <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
          {STEP_SUBTITLES[step]}
        </p>
      </div>

      {/* Step 0: Deck size */}
      {step === 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {SIZE_PRESETS.map((preset) => {
            const selected = !useCustom && size === preset.value
            return (
              <button
                key={preset.value}
                onClick={() => { setSize(preset.value); setUseCustom(false) }}
                style={{
                  ...tileStyle(selected),
                  flexDirection: 'row',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <span style={{
                  fontSize: '1.75rem',
                  fontWeight: 700,
                  letterSpacing: '-0.02em',
                  color: selected ? 'var(--color-primary-text)' : 'var(--color-text)',
                }}>
                  {preset.value}
                </span>
                <span style={{
                  fontSize: '0.875rem',
                  fontWeight: 500,
                  color: selected ? 'var(--color-primary-text)' : 'var(--color-text-muted)',
                }}>
                  {preset.sublabel}
                </span>
              </button>
            )
          })}

          {/* Custom tile */}
          <button
            onClick={() => setUseCustom(true)}
            style={tileStyle(useCustom)}
          >
            <span style={{
              fontSize: '0.875rem',
              fontWeight: 500,
              color: useCustom ? 'var(--color-primary-text)' : 'var(--color-text-muted)',
            }}>
              Custom
            </span>
            {useCustom && (
              <input
                type="number"
                min={1}
                placeholder="Enter a number"
                value={customSize}
                onClick={(e) => e.stopPropagation()}
                onChange={(e) => setCustomSize(e.target.value)}
                autoFocus
                aria-label="Custom deck size"
                style={{
                  marginTop: '8px',
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid var(--color-primary)',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--color-bg)',
                  color: 'var(--color-text)',
                  fontSize: '1.75rem',
                  fontWeight: 700,
                  textAlign: 'center',
                  letterSpacing: '-0.02em',
                }}
              />
            )}
          </button>
        </div>
      )}

      {/* Step 1: Practice mode */}
      {step === 1 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {MODES.map((m) => {
            const selected = mode === m.value
            return (
              <button key={m.value} onClick={() => setMode(m.value)} style={tileStyle(selected)}>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  color: selected ? 'var(--color-primary-text)' : 'var(--color-text)',
                }}>
                  {m.icon}
                  <span style={{ fontSize: '1.125rem', fontWeight: 600 }}>
                    {m.label}
                  </span>
                </div>
                <span style={{
                  fontSize: '0.875rem',
                  color: selected ? 'var(--color-primary-text)' : 'var(--color-text-muted)',
                  paddingLeft: '30px',
                }}>
                  {m.description}
                </span>
              </button>
            )
          })}
        </div>
      )}

      {/* Step 2: Algorithm */}
      {step === 2 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {error && (
            <p role="alert" style={{
              margin: 0,
              padding: '10px 12px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--color-error-subtle)',
              color: 'var(--color-error)',
              fontSize: '0.875rem',
            }}>
              {error}
            </p>
          )}
          {ALGORITHMS.map((a) => {
            const selected = algorithm === a.value
            return (
              <button key={a.value} onClick={() => setAlgorithm(a.value)} style={tileStyle(selected)}>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  color: selected ? 'var(--color-primary-text)' : 'var(--color-text)',
                }}>
                  {a.icon}
                  <span style={{ fontSize: '1.125rem', fontWeight: 600 }}>
                    {a.label}
                  </span>
                </div>
                <span style={{
                  fontSize: '0.875rem',
                  color: selected ? 'var(--color-primary-text)' : 'var(--color-text-muted)',
                  paddingLeft: '30px',
                }}>
                  {a.description}
                </span>
              </button>
            )
          })}
        </div>
      )}

      {/* Navigation */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '4px' }}>
        {step > 0 ? (
          <button
            onClick={() => setStep((s) => s - 1)}
            style={{
              padding: '10px 20px',
              background: 'none',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--color-text-muted)',
              cursor: 'pointer',
              fontWeight: 500,
              fontSize: '1rem',
            }}
          >
            Back
          </button>
        ) : (
          <button
            onClick={onCancel}
            style={{
              padding: '10px 20px',
              background: 'none',
              border: 'none',
              color: 'var(--color-text-muted)',
              cursor: 'pointer',
              fontWeight: 500,
              fontSize: '1rem',
            }}
          >
            Cancel
          </button>
        )}

        {step < TOTAL_STEPS - 1 ? (
          <button
            onClick={() => setStep((s) => s + 1)}
            disabled={!canAdvance}
            style={{
              padding: '10px 24px',
              background: 'var(--color-primary)',
              border: 'none',
              borderRadius: 'var(--radius-md)',
              color: 'var(--color-text-on-primary)',
              fontWeight: 600,
              fontSize: '1rem',
              cursor: canAdvance ? 'pointer' : 'not-allowed',
              opacity: canAdvance ? 1 : 0.5,
            }}
          >
            Next →
          </button>
        ) : (
          <button
            onClick={handleGenerate}
            disabled={isCreating}
            style={{
              padding: '10px 24px',
              background: 'var(--color-primary)',
              border: 'none',
              borderRadius: 'var(--radius-md)',
              color: 'var(--color-text-on-primary)',
              fontWeight: 600,
              fontSize: '1rem',
              cursor: isCreating ? 'not-allowed' : 'pointer',
              opacity: isCreating ? 0.5 : 1,
            }}
          >
            {isCreating ? 'Generating…' : 'Generate Deck'}
          </button>
        )}
      </div>

    </div>
  )
}
