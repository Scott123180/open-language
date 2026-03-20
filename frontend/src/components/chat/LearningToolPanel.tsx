import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import * as api from '../../services/api'

interface LearningToolPanelProps {
  messageId: number
  content: string
  role: 'user' | 'assistant'
  targetLanguage: string
  nativeLanguage: string
  onReplay?: () => void
  onPlaySlower?: () => void
  isAudioPlaying?: boolean
  precedingMessage?: string
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
  onReplay,
  onPlaySlower,
  isAudioPlaying = false,
  precedingMessage,
}: LearningToolPanelProps) {
  const [playingMode, setPlayingMode] = useState<'normal' | 'slower' | null>(null)

  useEffect(() => {
    if (!isAudioPlaying) setPlayingMode(null)
  }, [isAudioPlaying])
  const [activeTool, setActiveTool] = useState<ToolName | null>(null)
  const [activeToolResult, setActiveToolResult] = useState<string | null>(null)
  const [loadingTool, setLoadingTool] = useState<ToolName | null>(null)
  const [cache, setCache] = useState<Partial<Record<ToolName, string>>>({})

  const handleTool = async (tool: ToolName) => {
    if (loadingTool) return

    // toggle off if already active
    if (activeTool === tool) {
      setActiveTool(null)
      setActiveToolResult(null)
      return
    }

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
        data = await api.checkGrammar(messageId, content, precedingMessage)
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

  const isUser = role === 'user'

  const btnStyle = (tool: ToolName): React.CSSProperties => ({
    padding: '3px 9px',
    fontSize: '0.75rem',
    borderRadius: 'var(--radius)',
    border: '1px solid var(--color-border)',
    background: activeTool === tool ? 'var(--color-primary)' : 'var(--color-surface)',
    color: activeTool === tool ? '#fff' : 'var(--color-text-muted)',
    cursor: loadingTool ? 'not-allowed' : 'pointer',
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    whiteSpace: 'nowrap' as const,
  })

  const plainBtnStyle: React.CSSProperties = {
    padding: '3px 9px',
    fontSize: '0.75rem',
    borderRadius: 'var(--radius)',
    border: '1px solid var(--color-border)',
    background: 'var(--color-surface)',
    color: 'var(--color-text-muted)',
    cursor: 'pointer',
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    whiteSpace: 'nowrap' as const,
  }

  const showResult = activeTool !== null

  return (
    <div style={{ marginTop: '6px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        .tool-result {
          display: grid;
          grid-template-rows: 0fr;
          transition: grid-template-rows 0.2s ease;
        }
        .tool-result.open {
          grid-template-rows: 1fr;
        }
        .tool-result-inner {
          overflow: hidden;
        }
      `}</style>

      <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', alignItems: 'center', justifyContent: isUser ? 'flex-end' : 'flex-start' }}>
        {/* Playback buttons — assistant only */}
        {!isUser && onReplay && (
          <button
            style={{
              ...plainBtnStyle,
              background: playingMode === 'normal' ? 'var(--color-primary)' : 'var(--color-surface)',
              color: playingMode === 'normal' ? '#fff' : 'var(--color-text-muted)',
              border: playingMode === 'normal' ? '1px solid var(--color-primary)' : '1px solid var(--color-border)',
            }}
            onClick={() => { setPlayingMode('normal'); onReplay() }}
            aria-label="Replay"
          >
            ▶ Replay
          </button>
        )}
        {!isUser && onPlaySlower && (
          <button
            style={{
              ...plainBtnStyle,
              background: playingMode === 'slower' ? 'var(--color-primary)' : 'var(--color-surface)',
              color: playingMode === 'slower' ? '#fff' : 'var(--color-text-muted)',
              border: playingMode === 'slower' ? '1px solid var(--color-primary)' : '1px solid var(--color-border)',
            }}
            onClick={() => { setPlayingMode('slower'); onPlaySlower() }}
            aria-label="Play slower"
          >
            🐢 Slower
          </button>
        )}

        {/* Separator if we have playback + learning tools */}
        {!isUser && (onReplay || onPlaySlower) && (
          <span style={{ width: '1px', height: '16px', background: 'var(--color-border)', margin: '0 2px' }} />
        )}

        {/* Learning tool buttons */}
        {isUser && (
          <button
            style={btnStyle('grammar')}
            onClick={() => handleTool('grammar')}
            disabled={loadingTool !== null}
            aria-label="Grammar check"
          >
            {loadingTool === 'grammar' ? <span role="status" style={spinnerStyle} /> : '✓'}
            Grammar
          </button>
        )}
        <button
          style={btnStyle('translate')}
          onClick={() => handleTool('translate')}
          disabled={loadingTool !== null}
          aria-label="Translate"
        >
          {loadingTool === 'translate' ? <span role="status" style={spinnerStyle} /> : '🌐'}
          Translate
        </button>
        {isUser && (
          <button
            style={btnStyle('phrasing')}
            onClick={() => handleTool('phrasing')}
            disabled={loadingTool !== null}
            aria-label="Alternative phrasing"
          >
            {loadingTool === 'phrasing' ? <span role="status" style={spinnerStyle} /> : '↔'}
            Phrasing
          </button>
        )}
      </div>

      <div className={`tool-result${showResult ? ' open' : ''}`}>
        <div className="tool-result-inner">
          {showResult && (
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
              {activeToolResult ? (
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
              ) : (
                <span role="status" style={{ ...spinnerStyle, width: '12px', height: '12px' }} />
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
