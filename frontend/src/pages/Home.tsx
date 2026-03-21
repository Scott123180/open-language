import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import * as api from '../services/api'
import type { Scenario } from '../services/api'
import ScenarioCard from '../components/scenario/ScenarioCard'
import ErrorBanner from '../components/shared/ErrorBanner'
import { useTheme } from '../hooks/useTheme'

export default function Home() {
  const navigate = useNavigate()
  const { preference, setTheme } = useTheme()
  const [currentScenario, setCurrentScenario] = useState<Scenario | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [isStartingChat, setIsStartingChat] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [customPrompt, setCustomPrompt] = useState('')
  const [isCustomExpanded, setIsCustomExpanded] = useState(false)
  const [isStartingCustomChat, setIsStartingCustomChat] = useState(false)

  useEffect(() => {
    api
      .getCurrentScenario()
      .then((s) => {
        setCurrentScenario(s)
        setIsLoading(false)
      })
      .catch((e: Error) => {
        setError(e.message ?? 'Failed to load scenario')
        setIsLoading(false)
      })
  }, [])

  const handleRefresh = async () => {
    setIsRefreshing(true)
    setError(null)
    try {
      const next = await api.getNextScenario(currentScenario?.id)
      setCurrentScenario(next)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to refresh scenario')
    } finally {
      setIsRefreshing(false)
    }
  }

  const handleStartChat = async () => {
    if (!currentScenario) return
    setIsStartingChat(true)
    try {
      const conversation = await api.createConversation(currentScenario.id)
      navigate(`/chat/${conversation.id}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start chat')
    } finally {
      setIsStartingChat(false)
    }
  }

  const handleStartCustomChat = async () => {
    if (!customPrompt.trim()) return
    setIsStartingCustomChat(true)
    setError(null)
    try {
      const conversation = await api.createConversation(null, customPrompt.trim())
      navigate(`/chat/${conversation.id}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start chat')
    } finally {
      setIsStartingCustomChat(false)
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
      <h1 style={{ fontSize: '1.75rem', fontWeight: 700 }}>Open Language</h1>
      <nav style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
        <Link to="/history" style={{ color: 'var(--color-primary)' }}>
          Past Chats
        </Link>
        <Link to="/settings" style={{ color: 'var(--color-primary)' }}>
          Settings
        </Link>
        <button
          onClick={() => setTheme(preference === 'dark' ? 'light' : 'dark')}
          aria-label={preference === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          title='Toggle theme'
          style={{
            background: 'none',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius)',
            padding: '4px 10px',
            fontSize: '1rem',
            color: 'var(--color-text-muted)',
            cursor: 'pointer',
            minHeight: '44px',
          }}
        >
          {preference === 'dark' ? '☀️' : '🌙'}
        </button>
      </nav>
      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}
      {isLoading && <p aria-live="polite">Loading scenario…</p>}
      {!isLoading && currentScenario && (
        <ScenarioCard
          title={currentScenario.title}
          description={currentScenario.description}
          onRefresh={handleRefresh}
          onStartChat={handleStartChat}
          isLoading={isRefreshing}
          isStartingChat={isStartingChat}
        />
      )}
      <div style={{ maxWidth: '480px', width: '100%' }}>
        <button
          onClick={() => setIsCustomExpanded((v) => !v)}
          aria-expanded={isCustomExpanded}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--color-primary)',
            cursor: 'pointer',
            fontSize: '0.9rem',
            padding: '4px 0',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
        >
          <span style={{ fontSize: '0.75rem' }}>{isCustomExpanded ? '▼' : '▶'}</span>
          Write your own scenario
        </button>
        {isCustomExpanded && (
          <div
            style={{
              background: 'var(--color-surface)',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius)',
              boxShadow: 'var(--shadow)',
              padding: '20px',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
              marginTop: '8px',
            }}
          >
            <label
              htmlFor="custom-prompt"
              style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}
            >
              Describe the situation and who the AI should play
            </label>
            <textarea
              id="custom-prompt"
              value={customPrompt}
              onChange={(e) => setCustomPrompt(e.target.value)}
              placeholder="e.g. You are a barista at a busy coffee shop. The customer wants a complicated order and you are slightly impatient."
              rows={4}
              style={{
                width: '100%',
                padding: '10px',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius)',
                background: 'var(--color-bg)',
                color: 'var(--color-text)',
                fontSize: '0.9rem',
                lineHeight: 1.5,
                resize: 'vertical',
                boxSizing: 'border-box',
              }}
            />
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button
                onClick={handleStartCustomChat}
                disabled={!customPrompt.trim() || isStartingCustomChat}
                style={{
                  padding: '10px 24px',
                  background: 'var(--color-primary)',
                  borderRadius: 'var(--radius)',
                  color: '#fff',
                  fontWeight: 600,
                  fontSize: '1rem',
                  opacity: !customPrompt.trim() || isStartingCustomChat ? 0.6 : 1,
                  cursor: !customPrompt.trim() || isStartingCustomChat ? 'not-allowed' : 'pointer',
                }}
              >
                {isStartingCustomChat ? 'Starting…' : 'Start Chat'}
              </button>
            </div>
          </div>
        )}
      </div>
    </main>
  )
}
