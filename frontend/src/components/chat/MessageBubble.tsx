import { useState, type ReactNode } from 'react'
import * as api from '../../services/api'
import LearningToolPanel from './LearningToolPanel'
import WordLookupPopover from './WordLookupPopover'

interface MessageBubbleProps {
  role: 'user' | 'assistant'
  content: string
  messageId?: number
  conversationId?: number
  isStreaming?: boolean
  onPlaySlower?: () => void
  onReplay?: () => void
  isAudioPlaying?: boolean
  precedingMessage?: string
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
  conversationId,
  isStreaming = false,
  onPlaySlower,
  onReplay,
  isAudioPlaying = false,
  precedingMessage,
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
        : await api.lookupWord(messageId, word, targetLanguage, nativeLanguage, content)
      setLookupResult(data.result)
    } catch {
      setLookupResult(isPhrase ? 'Error loading translation.' : 'Error loading definition.')
    } finally {
      setLookupLoading(false)
    }
  }

  const handleSaveWord = async (word: string): Promise<void> => {
    if (!lookupResult) return
    await api.saveVocabularyItem(word, lookupResult, conversationId)
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
          borderRadius: 'var(--radius-lg)',
          background: isUser ? 'var(--color-primary)' : 'var(--color-surface)',
          color: isUser ? 'var(--color-text-on-primary)' : 'var(--color-text)',
          border: isUser ? 'none' : '1px solid var(--color-border)',
          boxShadow: 'var(--shadow-sm)',
          lineHeight: 'var(--leading-relaxed)',
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
            onReplay={onReplay}
            onPlaySlower={onPlaySlower}
            isAudioPlaying={isAudioPlaying}
            precedingMessage={precedingMessage}
          />
        </div>
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
