import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import * as api from '../services/api'
import type { Scenario } from '../services/api'
import ScenarioCard from '../components/scenario/ScenarioCard'
import ErrorBanner from '../components/shared/ErrorBanner'

export default function Home() {
  const navigate = useNavigate()
  const [currentScenario, setCurrentScenario] = useState<Scenario | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [isStartingChat, setIsStartingChat] = useState(false)
  const [error, setError] = useState<string | null>(null)

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
      <nav style={{ display: 'flex', gap: '16px' }}>
        <Link to="/history" style={{ color: 'var(--color-primary)' }}>
          Past Chats
        </Link>
        <Link to="/settings" style={{ color: 'var(--color-primary)' }}>
          Settings
        </Link>
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
    </main>
  )
}
