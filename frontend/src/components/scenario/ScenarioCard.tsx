interface ScenarioCardProps {
  title: string
  description: string
  onRefresh: () => void
  onStartChat: () => void
  isLoading?: boolean
  isStartingChat?: boolean
}

export default function ScenarioCard({
  title,
  description,
  onRefresh,
  onStartChat,
  isLoading = false,
  isStartingChat = false,
}: ScenarioCardProps) {
  return (
    <div
      style={{
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius)',
        boxShadow: 'var(--shadow)',
        padding: '24px',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
        maxWidth: '480px',
        width: '100%',
      }}
    >
      <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--color-text)' }}>{title}</h2>
      <p style={{ color: 'var(--color-text-muted)', lineHeight: 1.6 }}>{description}</p>
      <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end', flexWrap: 'wrap' }}>
        <button
          onClick={onRefresh}
          disabled={isLoading}
          aria-label="Refresh scenario"
          style={{
            padding: '8px 16px',
            background: 'none',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius)',
            color: 'var(--color-text)',
            opacity: isLoading ? 0.6 : 1,
          }}
        >
          {isLoading ? 'Loading…' : 'Refresh'}
        </button>
        <button
          onClick={onStartChat}
          disabled={isLoading || isStartingChat}
          style={{
            padding: '10px 24px',
            background: 'var(--color-primary)',
            borderRadius: 'var(--radius)',
            color: '#fff',
            fontWeight: 600,
            fontSize: '1rem',
            opacity: isLoading || isStartingChat ? 0.6 : 1,
            cursor: isLoading || isStartingChat ? 'not-allowed' : 'pointer',
          }}
        >
          {isStartingChat ? 'Starting…' : 'Start Chat'}
        </button>
      </div>
    </div>
  )
}
