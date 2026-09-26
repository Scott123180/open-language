import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import * as api from '../services/api'
import type { CorrectionMode, VoiceOption } from '../services/api'
import { useTheme } from '../hooks/useTheme'
import { IconArrowLeft } from '../components/shared/icons'
import LlmProviderFields, { type LlmSelectionValue } from '../components/settings/LlmProviderFields'
import { useLlmProviders } from '../components/settings/useLlmProviders'

// Replaced by the saved choice on load; an unloaded choice is never sent.
const UNLOADED_LLM: LlmSelectionValue = { provider: '', model: '', effort: '' }
const WHISPER_MODEL_OPTIONS = [
  { value: 'base', label: 'Base — fast, lower accuracy' },
  { value: 'small', label: 'Small — balanced' },
  { value: 'medium', label: 'Medium — slower, higher accuracy' },
]
const CORRECTION_MODE_OPTIONS: { value: CorrectionMode; label: string; description: string }[] = [
  { value: 'off', label: 'Off', description: 'No corrections — the conversation runs as it always has.' },
  { value: 'gentle', label: 'Gentle', description: 'The character restates your sentence correctly inside its own reply.' },
  { value: 'strict', label: 'Strict', description: 'The conversation pauses so you can see the correction and try again.' },
]
const CORRECTION_MODE_HINT_ID = 'correction-mode-hint'
const CORRECTION_MODE_WARNING_ID = 'correction-mode-warning'
const THEME_OPTIONS = [
  { value: 'light' as const, label: 'Light' },
  { value: 'dark' as const, label: 'Dark' },
  { value: 'system' as const, label: 'System' },
]

export default function Settings() {
  const { preference: themePreference, setTheme } = useTheme()
  const llmProviders = useLlmProviders()
  const [llm, setLlm] = useState<LlmSelectionValue>(UNLOADED_LLM)
  const [whisperModel, setWhisperModel] = useState('base')
  const [ttsVoice, setTtsVoice] = useState('')
  const [voices, setVoices] = useState<VoiceOption[]>([])
  const [suggestionCount, setSuggestionCount] = useState(3)
  const [correctionMode, setCorrectionMode] = useState<CorrectionMode>('off')
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    api
      .getSettings()
      .then((settings) => {
        setLlm({ provider: settings.llm_provider, model: settings.llm_model, effort: settings.llm_effort })
        setWhisperModel(settings.whisper_model)
        setTtsVoice(settings.tts_voice)
        setSuggestionCount(settings.suggestion_count)
        setCorrectionMode(settings.correction_mode)
        setIsLoading(false)
      })
      .catch(() => {
        setIsLoading(false)
      })
  }, [])

  useEffect(() => {
    api.getVoices().then(setVoices).catch(() => {})
  }, [])

  const handleSave = async () => {
    setIsSaving(true)
    setSuccessMessage(null)
    setErrorMessage(null)
    try {
      await api.updateSettings({
        ...(llm.provider && { llm_provider: llm.provider, llm_model: llm.model, llm_effort: llm.effort }),
        whisper_model: whisperModel,
        tts_voice: ttsVoice,
        suggestion_count: suggestionCount,
        correction_mode: correctionMode,
      })
      setSuccessMessage('Settings saved.')
    } catch (e) {
      setErrorMessage(e instanceof Error ? e.message : 'Failed to save settings')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <main
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '40px 16px',
        gap: '24px',
        minHeight: '100vh',
        background: 'var(--color-bg)',
      }}
    >
      <h1 style={{ fontSize: '1.75rem', fontWeight: 700 }}>Settings</h1>
      <Link to='/' className='back-link' style={{ alignSelf: 'flex-start' }}>
        <IconArrowLeft size={14} /> Back to Home
      </Link>

      {isLoading && <p aria-live='polite'>Loading settings…</p>}

      {!isLoading && (
        <form
          onSubmit={(e) => {
            e.preventDefault()
            handleSave()
          }}
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '20px',
            width: '100%',
            maxWidth: '480px',
          }}
        >
          <LlmProviderFields providers={llmProviders} value={llm} onChange={setLlm} />

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label htmlFor='whisper-model' style={{ fontWeight: 600 }}>
              Speech Recognition Model
            </label>
            <select
              id='whisper-model'
              value={whisperModel}
              onChange={(e) => setWhisperModel(e.target.value)}
              style={{
                padding: '10px 12px',
                borderRadius: 'var(--radius)',
                border: '1px solid var(--color-border)',
                background: 'var(--color-surface)',
                color: 'var(--color-text)',
                fontSize: '1rem',
              }}
            >
              {WHISPER_MODEL_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
              Takes effect on next recording. Larger models load once then stay in memory.
            </p>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label htmlFor='tts-voice' style={{ fontWeight: 600 }}>
              Voice
            </label>
            <select
              id='tts-voice'
              value={ttsVoice}
              onChange={(e) => setTtsVoice(e.target.value)}
              style={{
                padding: '10px 12px',
                borderRadius: 'var(--radius)',
                border: '1px solid var(--color-border)',
                background: 'var(--color-surface)',
                color: 'var(--color-text)',
                fontSize: '1rem',
              }}
            >
              {voices.map((v) => (
                <option key={v.key} value={v.key}>
                  {v.display_name}
                </option>
              ))}
            </select>
            {(() => {
              const selected = voices.find((v) => v.key === ttsVoice)
              if (!selected) return null
              const regionCode = selected.locale.split('_')[1]
              const country = new Intl.DisplayNames(['en'], { type: 'region' }).of(regionCode) ?? regionCode
              const genderIcon = selected.gender === 'female' ? '♀' : '♂'
              const qualityLabel: Record<string, string> = { high: 'High quality', medium: 'Medium quality', low: 'Low quality', x_low: 'Low quality (fast)' }
              const paceDescriptions: Record<string, { label: string; description: string }> = {
                slow: { label: 'Slow', description: 'Deliberate pace — ideal for beginners' },
                natural: { label: 'Natural', description: 'Conversational native speed' },
                fast: { label: 'Fast', description: 'Quick native pace — ideal for advanced learners' },
              }
              const pace = paceDescriptions[selected.speaking_rate]
              return (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                  <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
                    {genderIcon} {selected.gender.charAt(0).toUpperCase() + selected.gender.slice(1)} · {country} · {qualityLabel[selected.quality] ?? selected.quality}
                  </p>
                  {pace && (
                    <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
                      Pace: <strong style={{ color: 'var(--color-text)' }}>{pace.label}</strong> — {pace.description}
                    </p>
                  )}
                </div>
              )
            })()}
          </div>

          <fieldset
            aria-describedby={`${CORRECTION_MODE_HINT_ID} ${CORRECTION_MODE_WARNING_ID}`}
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
              border: 'none',
              padding: 0,
              margin: 0,
            }}
          >
            <legend style={{ fontWeight: 600, padding: 0 }}>Correction Feedback</legend>
            {CORRECTION_MODE_OPTIONS.map(({ value, label, description }) => (
              <label
                key={value}
                htmlFor={`correction-mode-${value}`}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '10px',
                  padding: '10px 12px',
                  borderRadius: 'var(--radius-lg)',
                  border: '1px solid var(--color-border)',
                  background:
                    correctionMode === value ? 'var(--color-surface-raised)' : 'var(--color-surface)',
                  cursor: 'pointer',
                }}
              >
                <input
                  id={`correction-mode-${value}`}
                  type='radio'
                  name='correction-mode'
                  value={value}
                  checked={correctionMode === value}
                  onChange={() => setCorrectionMode(value)}
                  aria-labelledby={`correction-mode-${value}-label`}
                  aria-describedby={`correction-mode-${value}-description`}
                  style={{ marginTop: '3px' }}
                />
                <span style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                  <span
                    id={`correction-mode-${value}-label`}
                    style={{ fontWeight: 600, color: 'var(--color-text)' }}
                  >
                    {label}
                  </span>
                  <span
                    id={`correction-mode-${value}-description`}
                    style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}
                  >
                    {description}
                  </span>
                </span>
              </label>
            ))}
            <p
              id={CORRECTION_MODE_HINT_ID}
              style={{ margin: 0, fontSize: '0.85rem', color: 'var(--color-text-muted)' }}
            >
              Gentle and Strict run an extra language-model pass over each message before the
              character answers. Without a GPU this can add several seconds per turn. A check that
              takes too long is skipped so the conversation continues.
            </p>
            <aside
              id={CORRECTION_MODE_WARNING_ID}
              role='note'
              aria-label='Correction accuracy'
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '4px',
                borderLeft: '3px solid var(--color-warning)',
                background: 'var(--color-surface-raised)',
                borderRadius: 'var(--radius-lg)',
                boxShadow: 'var(--shadow-sm)',
                padding: '10px 14px',
                lineHeight: 'var(--leading-relaxed)',
              }}
            >
              <span style={{ fontWeight: 600, fontSize: '0.8rem', color: 'var(--color-warning)' }}>
                Corrections are experimental
              </span>
              <span style={{ fontSize: '0.85rem', color: 'var(--color-text)' }}>
                Corrections come from the language model you selected above, and they can be wrong —
                a small model often flags sentences that were already correct. Treat a
                correction as a reason to double-check, not as the last word. Accuracy improves with
                a larger model, at the cost of a slower reply.
              </span>
            </aside>
          </fieldset>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <span style={{ fontWeight: 600 }}>Theme</span>
            <div role='group' aria-label='Theme' style={{ display: 'flex', gap: '8px' }}>
              {THEME_OPTIONS.map(({ value, label }) => (
                <button
                  key={value}
                  type='button'
                  aria-pressed={themePreference === value}
                  onClick={() => setTheme(value)}
                  style={{
                    padding: '8px 16px',
                    borderRadius: 'var(--radius)',
                    border: '1px solid var(--color-border)',
                    background: themePreference === value ? 'var(--color-primary)' : 'var(--color-surface)',
                    color: themePreference === value ? 'var(--color-text-on-primary)' : 'var(--color-text)',
                    fontWeight: themePreference === value ? 600 : 400,
                    cursor: 'pointer',
                    minHeight: '44px',
                  }}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label htmlFor='suggestion-count' style={{ fontWeight: 600 }}>
              Suggestion Count (1–5)
            </label>
            <input
              id='suggestion-count'
              type='number'
              min={1}
              max={5}
              value={suggestionCount}
              onChange={(e) => setSuggestionCount(Number(e.target.value))}
              style={{
                padding: '10px 12px',
                borderRadius: 'var(--radius)',
                border: '1px solid var(--color-border)',
                background: 'var(--color-surface)',
                color: 'var(--color-text)',
                fontSize: '1rem',
                width: '80px',
              }}
            />
          </div>

          {successMessage && (
            <p role='status' style={{ color: 'var(--color-success)', fontWeight: 600 }}>
              {successMessage}
            </p>
          )}

          {errorMessage && (
            <p role='alert' style={{ color: 'var(--color-error)', fontWeight: 600 }}>
              {errorMessage}
            </p>
          )}

          <button
            type='submit'
            disabled={isSaving}
            style={{
              padding: '12px 24px',
              background: isSaving ? 'var(--color-border)' : 'var(--color-primary)',
              color: isSaving ? 'var(--color-text-muted)' : 'var(--color-text-on-primary)',
              borderRadius: 'var(--radius)',
              fontWeight: 600,
              fontSize: '1rem',
              cursor: isSaving ? 'not-allowed' : 'pointer',
              border: 'none',
            }}
          >
            {isSaving ? 'Saving…' : 'Save'}
          </button>
        </form>
      )}
    </main>
  )
}
