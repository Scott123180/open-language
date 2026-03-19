import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
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
  content,
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
        data = await api.checkGrammar(messageId, content)
      } else if (tool === 'translate') {
        data = await api.translateMessage(messageId, content, nativeLanguage)
      } else {
        data = await api.getAlternativePhrasing(messageId, content, targetLanguage)
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
          <ReactMarkdown
            components={{
              p: ({ children }) => <p style={{ margin: '0 0 4px' }}>{children}</p>,
              ul: ({ children }) => <ul style={{ margin: '4px 0', paddingLeft: '16px' }}>{children}</ul>,
              ol: ({ children }) => <ol style={{ margin: '4px 0', paddingLeft: '16px' }}>{children}</ol>,
              li: ({ children }) => <li style={{ marginBottom: '2px' }}>{children}</li>,
            }}
          >
            {activeToolResult}
          </ReactMarkdown>
        </div>
      )}
    </div>
  )
}
