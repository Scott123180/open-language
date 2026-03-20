import { useState, type ReactNode } from 'react'
import * as api from '../../services/api'
import LearningToolPanel from './LearningToolPanel'
import WordLookupPopover from './WordLookupPopover'

interface MessageBubbleProps {
  role: 'user' | 'assistant'
  content: string
  messageId?: number
  isStreaming?: boolean
  onPlaySlower?: () => void
  children?: ReactNode
  showLearningTools?: boolean
  targetLanguage?: string
  nativeLanguage?: string
}

const cursorStyle: React.CSSProperties = {
  display: 'inline-block',
  width: '2px',
  height: '1em',
  background: 'currentColor',
  marginLeft: '2px',
  verticalAlign: 'text-bottom',
  animation: 'blink 1s step-start infinite',
}

export default function MessageBubble({
  role,
  content,
  messageId,
  isStreaming = false,
  onPlaySlower,
  children,
  showLearningTools = false,
  targetLanguage = '',
  nativeLanguage = '',
}: MessageBubbleProps) {
  const isUser = role === 'user'

  const [lookupWord, setLookupWord] = useState<string | null>(null)
  const [lookupResult, setLookupResult] = useState<string | null>(null)
  const [lookupLoading, setLookupLoading] = useState(false)
  const [lookupPosition, setLookupPosition] = useState<{ x: number; y: number } | null>(null)
  const [lookupIsPhrase, setLookupIsPhrase] = useState(false)

  const handleSelectionEnd = async () => {
    if (!messageId) return
    const selection = window.getSelection()
    const word = selection?.toString().trim()
    if (!word) return

    const range = selection?.getRangeAt(0)
    const rect = range?.getBoundingClientRect()
    if (rect) {
      setLookupPosition({ x: rect.left + rect.width / 2, y: rect.bottom + window.scrollY })
    }

    const isPhrase = word.includes(' ')
    setLookupIsPhrase(isPhrase)
    setLookupWord(word)
    setLookupResult(null)
    setLookupLoading(true)

    try {
      const data = isPhrase
        ? await api.translateMessage(messageId, word, nativeLanguage)
        : await api.lookupWord(messageId, word, targetLanguage, nativeLanguage)
      setLookupResult(data.result)
    } catch {
      setLookupResult(isPhrase ? 'Error loading translation.' : 'Error loading definition.')
    } finally {
      setLookupLoading(false)
    }
  }

  const handleSaveWord = async (word: string) => {
    if (!lookupResult || !messageId) return
    try {
      await api.saveVocabularyItem(word, lookupResult, messageId)
    } catch {
      // best-effort save
    }
    handleCloseLookup()
  }

  const handleCloseLookup = () => {
    setLookupWord(null)
    setLookupResult(null)
    setLookupLoading(false)
    setLookupPosition(null)
    window.getSelection()?.removeAllRanges()
  }

  return (
    <article
      role="article"
      aria-label={isUser ? 'Your message' : 'AI response'}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: isUser ? 'flex-end' : 'flex-start',
        marginBottom: '12px',
        position: 'relative',
      }}
    >
      <div
        onMouseUp={handleSelectionEnd}
        onTouchEnd={handleSelectionEnd}
        style={{
          maxWidth: '75%',
          padding: '10px 14px',
          borderRadius: 'var(--radius)',
          background: isUser ? 'var(--color-primary)' : 'var(--color-surface)',
          color: isUser ? '#fff' : 'var(--color-text)',
          border: isUser ? 'none' : '1px solid var(--color-border)',
          boxShadow: 'var(--shadow)',
        }}
      >
        <span>{content}</span>
        {isStreaming && <span aria-hidden="true" style={cursorStyle} />}
      </div>

      {showLearningTools && messageId != null && !isStreaming && (
        <div style={{ maxWidth: '75%', width: '100%', alignSelf: isUser ? 'flex-end' : 'flex-start' }}>
          <LearningToolPanel
            messageId={messageId}
            content={content}
            role={role}
            targetLanguage={targetLanguage}
            nativeLanguage={nativeLanguage}
          />
        </div>
      )}

      {!isUser && onPlaySlower && (
        <button
          onClick={onPlaySlower}
          style={{
            marginTop: '4px',
            padding: '2px 10px',
            fontSize: '0.78rem',
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius)',
            color: 'var(--color-text-muted)',
            cursor: 'pointer',
          }}
        >
          🐢 Play Slower
        </button>
      )}

      {children && <div style={{ marginTop: '4px' }}>{children}</div>}

      {lookupWord && lookupPosition && (
        <WordLookupPopover
          word={lookupWord}
          result={lookupResult}
          isLoading={lookupLoading}
          onSave={lookupIsPhrase ? undefined : handleSaveWord}
          onClose={handleCloseLookup}
          position={lookupPosition}
        />
      )}
    </article>
  )
}
