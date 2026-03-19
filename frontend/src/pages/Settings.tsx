import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import * as api from '../services/api'

const LLM_OPTIONS = ['llama3.1', 'llama3.2', 'mistral']

export default function Settings() {
  const [llmModel, setLlmModel] = useState('llama3.1')
  const [suggestionCount, setSuggestionCount] = useState(3)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    api
      .getSettings()
      .then((settings) => {
        setLlmModel(settings.llm_model)
        setSuggestionCount(settings.suggestion_count)
        setIsLoading(false)
      })
      .catch(() => {
        setIsLoading(false)
      })
  }, [])

  const handleSave = async () => {
    setIsSaving(true)
    setSuccessMessage(null)
    setErrorMessage(null)
    try {
      await api.updateSettings({ llm_model: llmModel, suggestion_count: suggestionCount })
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
      <Link to='/' style={{ color: 'var(--color-primary)', alignSelf: 'flex-start' }}>
        ← Back to Home
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
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label htmlFor='llm-model' style={{ fontWeight: 600 }}>
              LLM Model
            </label>
            <select
              id='llm-model'
              value={llmModel}
              onChange={(e) => setLlmModel(e.target.value)}
              style={{
                padding: '10px 12px',
                borderRadius: 'var(--radius)',
                border: '1px solid var(--color-border)',
                background: 'var(--color-surface)',
                color: 'var(--color-text)',
                fontSize: '1rem',
              }}
            >
              {LLM_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
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
            <p role='status' style={{ color: 'var(--color-success, green)', fontWeight: 600 }}>
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
              color: isSaving ? 'var(--color-text-muted)' : '#fff',
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
