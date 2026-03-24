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

  const isDark = preference === 'dark'

  return (
    <div style={{ minHeight: '100vh', background: 'var(--color-bg)', display: 'flex', flexDirection: 'column' }}>
      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 20px',
          height: '56px',
          borderBottom: '1px solid var(--color-border)',
          background: 'var(--color-surface)',
          position: 'sticky',
          top: 0,
          zIndex: 10,
        }}
      >
        <h1
          style={{
            fontSize: '1.1rem',
            fontWeight: 700,
            color: 'var(--color-text)',
            letterSpacing: '-0.01em',
          }}
        >
          Open Language
        </h1>
        <button
          className="theme-toggle"
          onClick={() => setTheme(isDark ? 'light' : 'dark')}
          aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          <span aria-hidden="true">{isDark ? '☀' : '☾'}</span>
          {isDark ? 'Light' : 'Dark'}
        </button>
      </header>

      <nav
        aria-label="Main navigation"
        style={{
          display: 'flex',
          gap: '8px',
          padding: '10px 20px',
          borderBottom: '1px solid var(--color-border)',
          background: 'var(--color-surface)',
          justifyContent: 'center',
          flexWrap: 'wrap',
        }}
      >
        <Link className="nav-pill" to="/history">Past Chats</Link>
        <Link className="nav-pill" to="/flashcards">Flashcards</Link>
        <Link className="nav-pill" to="/settings">Settings</Link>
      </nav>

      <main
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          padding: '32px 16px',
          gap: '24px',
        }}
      >
        {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

        <div style={{ maxWidth: '480px', width: '100%' }}>
          <p
            style={{
              fontSize: '0.7rem',
              fontWeight: 600,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              color: 'var(--color-text-muted)',
              marginBottom: '10px',
            }}
          >
            Today's Scenario
          </p>
          {isLoading && (
            <p aria-live="polite" style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem' }}>
              Loading scenario…
            </p>
          )}
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
        </div>

        <div style={{ maxWidth: '480px', width: '100%' }}>
          <button
            onClick={() => setIsCustomExpanded((v) => !v)}
            aria-expanded={isCustomExpanded}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--color-text-muted)',
              cursor: 'pointer',
              fontSize: '0.875rem',
              padding: '4px 0',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              minHeight: 'unset',
              minWidth: 'unset',
              fontWeight: 500,
              width: '100%',
            }}
          >
            <span
              aria-hidden="true"
              style={{
                width: '18px',
                height: '18px',
                border: '1.5px solid var(--color-border)',
                borderRadius: '4px',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '14px',
                flexShrink: 0,
              }}
            >
              {isCustomExpanded ? '−' : '+'}
            </span>
            Write your own scenario
          </button>
          {isCustomExpanded && (
            <div
              style={{
                background: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-lg)',
                boxShadow: 'var(--shadow-sm)',
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
                  borderRadius: 'var(--radius-md)',
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
                    border: 'none',
                    borderRadius: 'var(--radius-md)',
                    color: 'var(--color-text-on-primary)',
                    fontWeight: 600,
                    fontSize: '1rem',
                    opacity: !customPrompt.trim() || isStartingCustomChat ? 0.6 : 1,
                    cursor: !customPrompt.trim() || isStartingCustomChat ? 'not-allowed' : 'pointer',
                    minHeight: 'unset',
                    minWidth: 'unset',
                  }}
                >
                  {isStartingCustomChat ? 'Starting…' : 'Start Chat'}
                </button>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
