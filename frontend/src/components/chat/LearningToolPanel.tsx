import { useState } from 'react'
import * as api from '../../services/api'

interface LearningToolPanelProps {
  messageId: number
  content: string
  role: 'user' | 'assistant'
  targetLanguage: string
  nativeLanguage: string
}

type ToolName = 'grammar' | 'translate' | 'phrasing'

const spinnerStyle: React.CSSProperties = {
  display: 'inline-block',
  width: '10px',
  height: '10px',
  border: '2px solid currentColor',
  borderTopColor: 'transparent',
  borderRadius: '50%',
  animation: 'spin 0.6s linear infinite',
}

export default function LearningToolPanel({
  messageId,
  targetLanguage,
  nativeLanguage,
  role,
}: LearningToolPanelProps) {
  const [activeTool, setActiveTool] = useState<ToolName | null>(null)
  const [activeToolResult, setActiveToolResult] = useState<string | null>(null)
  const [loadingTool, setLoadingTool] = useState<ToolName | null>(null)
  const [cache, setCache] = useState<Partial<Record<ToolName, string>>>({})

  const handleTool = async (tool: ToolName) => {
    if (loadingTool) return

    if (cache[tool]) {
      setActiveTool(tool)
      setActiveToolResult(cache[tool]!)
      return
    }

    setActiveTool(tool)
    setActiveToolResult(null)
    setLoadingTool(tool)

    try {
      let data: { result: string; cached: boolean }
      if (tool === 'grammar') {
        data = await api.checkGrammar(messageId)
      } else if (tool === 'translate') {
        data = await api.translateMessage(messageId)
      } else {
        data = await api.getAlternativePhrasing(messageId)
      }
      setCache((prev) => ({ ...prev, [tool]: data.result }))
      setActiveToolResult(data.result)
    } catch {
      setActiveToolResult('Error loading result.')
    } finally {
      setLoadingTool(null)
    }
  }

  const btnStyle = (tool: ToolName): React.CSSProperties => ({
    padding: '3px 10px',
    fontSize: '0.75rem',
    borderRadius: 'var(--radius)',
    border: '1px solid var(--color-border)',
    background: activeTool === tool ? 'var(--color-primary)' : 'var(--color-surface)',
    color: activeTool === tool ? '#fff' : 'var(--color-text-muted)',
    cursor: loadingTool ? 'not-allowed' : 'pointer',
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
  })

  const isUser = role === 'user'

  return (
    <div style={{ marginTop: '6px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
        {isUser && (
          <button
            style={btnStyle('grammar')}
            onClick={() => handleTool('grammar')}
            disabled={loadingTool !== null}
            aria-label="Grammar"
          >
            {loadingTool === 'grammar' && <span role="status" style={spinnerStyle} />}
            Grammar
          </button>
        )}
        <button
          style={btnStyle('translate')}
          onClick={() => handleTool('translate')}
          disabled={loadingTool !== null}
          aria-label="Translate"
        >
          {loadingTool === 'translate' && <span role="status" style={spinnerStyle} />}
          Translate
        </button>
        {isUser && (
          <button
            style={btnStyle('phrasing')}
            onClick={() => handleTool('phrasing')}
            disabled={loadingTool !== null}
            aria-label="Alternative Phrasing"
          >
            {loadingTool === 'phrasing' && <span role="status" style={spinnerStyle} />}
            Alternative Phrasing
          </button>
        )}
      </div>
      {activeToolResult && (
        <div
          style={{
            padding: '6px 10px',
            fontSize: '0.82rem',
            background: 'var(--color-bg)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius)',
            color: 'var(--color-text)',
          }}
        >
          {activeToolResult}
        </div>
      )}
      {/* suppress unused prop warnings — consumed by parent for context */}
      <span style={{ display: 'none' }}>{targetLanguage}{nativeLanguage}</span>
    </div>
  )
}
