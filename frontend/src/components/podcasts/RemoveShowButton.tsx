import { useState } from 'react'
import { useRemoveShow } from '../../hooks/podcasts/useRemoveShow'
import ConfirmDialog from '../shared/ConfirmDialog'
import ErrorBanner from '../shared/ErrorBanner'
import { secondaryButtonStyle } from './styles'

/** Remove a kept learner-made show from My shows, after a confirmation (FR-024). */
export default function RemoveShowButton({ title, savedShowId }: { title: string; savedShowId: number }) {
  const [isConfirming, setConfirming] = useState(false)
  const { remove, isRemoving, error } = useRemoveShow()
  const message = `${title} leaves My shows, and its series end in every language. Its past episodes stay in Past Chats.`
  return (
    <>
      <button type="button" onClick={() => setConfirming(true)} disabled={isRemoving} aria-label={`Remove ${title}`} style={secondaryButtonStyle}>Remove</button>
      {isConfirming && <ConfirmDialog title={`Remove ${title}?`} message={message} confirmLabel="Remove" isDestructive
        onConfirm={() => { setConfirming(false); remove(savedShowId) }} onCancel={() => setConfirming(false)} />}
      {error && <ErrorBanner message={error} />}
    </>
  )
}
