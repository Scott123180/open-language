import type { PracticeMode } from '../../services/flashcardsApi'

interface Props {
  mode: PracticeMode
  isOpen: boolean
  onClose: () => void
}

const MODE_HELP: Record<PracticeMode, { title: string; description: string }> = {
  recall: {
    title: 'Recall Mode',
    description:
      'A word in your target language is shown. Try to recall the translation in your native language, then flip the card to check your answer.',
  },
  listen: {
    title: 'Listen Mode',
    description:
      'Audio plays automatically. Listen carefully and try to recall the translation in your native language, then flip the card to check your answer.',
  },
  produce: {
    title: 'Produce Mode',
    description:
      'A word in your native language is shown. Try to produce the translation in your target language, then flip the card to check your answer.',
  },
  fill_blank: {
    title: 'Fill-in-the-Blank Mode',
    description:
      'A sentence with a missing word is shown. Type or say the missing word, then flip the card to see the complete sentence.',
  },
}

export default function HelpOverlay({ mode, isOpen, onClose }: Props) {
  if (!isOpen) return null

  const help = MODE_HELP[mode]

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`Help: ${help.title}`}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 100,
      }}
    >
      <div
        style={{
          background: 'var(--color-surface)',
          borderRadius: 'var(--radius)',
          padding: '32px',
          maxWidth: '420px',
          width: '90%',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
        }}
      >
        <h2 style={{ margin: 0, fontSize: '1.25rem' }}>{help.title}</h2>
        <p style={{ margin: 0, lineHeight: 1.6 }}>{help.description}</p>
        <button
          aria-label="Close help"
          onClick={onClose}
          style={{
            alignSelf: 'flex-end',
            padding: '8px 20px',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius)',
            background: 'var(--color-surface)',
            cursor: 'pointer',
          }}
        >
          Close
        </button>
      </div>
    </div>
  )
}
