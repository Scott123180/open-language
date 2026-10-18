import { useEffect, useId, useRef, type CSSProperties, type KeyboardEvent, type ReactNode } from 'react'

interface ConfirmDialogProps {
  title: string
  message: string
  confirmLabel: string
  cancelLabel?: string
  /** A confirm that loses something is drawn in the error colour. */
  isDestructive?: boolean
  isBusy?: boolean
  onConfirm: () => void
  onCancel: () => void
  children?: ReactNode
}

const FOCUSABLE = 'button:not([disabled]), [href], input:not([disabled]), [tabindex]:not([tabindex="-1"])'

/** A confirmation that keeps focus inside until it is answered, and gives it back after.
 * Escape and Cancel change nothing (WAI-ARIA APG alert dialog). */
export default function ConfirmDialog(props: ConfirmDialogProps) {
  const ids = { title: useId(), message: useId() }
  const dialog = useRef<HTMLDivElement>(null)
  useFocusReturn(dialog)
  return (
    <div style={backdropStyle}>
      <div ref={dialog} role="alertdialog" aria-modal="true" aria-labelledby={ids.title} aria-describedby={ids.message}
        onKeyDown={(event) => trapKeys(event, dialog.current, props.onCancel)} style={dialogStyle}>
        <h2 id={ids.title} style={titleStyle}>{props.title}</h2>
        <p id={ids.message} style={{ margin: 0, color: 'var(--color-text)' }}>{props.message}</p>
        {props.children}
        <DialogButtons {...props} />
      </div>
    </div>
  )
}

function DialogButtons({ confirmLabel, cancelLabel = 'Cancel', isDestructive, isBusy, onConfirm, onCancel }: ConfirmDialogProps) {
  return (
    <div style={buttonRowStyle}>
      <button type="button" onClick={onCancel} style={cancelStyle}>{cancelLabel}</button>
      <button type="button" onClick={onConfirm} disabled={isBusy} aria-busy={isBusy} style={isDestructive ? destructiveStyle : confirmStyle}>
        {confirmLabel}
      </button>
    </div>
  )
}

/** Focus the first control on open, and the element that opened the dialog on close. */
function useFocusReturn(dialog: React.RefObject<HTMLDivElement>) {
  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null
    dialog.current?.querySelector<HTMLElement>(FOCUSABLE)?.focus()
    return () => opener?.focus()
  }, [dialog])
}

function trapKeys(event: KeyboardEvent, dialog: HTMLDivElement | null, onCancel: () => void): void {
  if (event.key === 'Escape') {
    event.preventDefault()
    onCancel()
  } else if (event.key === 'Tab' && dialog) {
    const focusable = [...dialog.querySelectorAll<HTMLElement>(FOCUSABLE)]
    const [first, last] = [focusable[0], focusable[focusable.length - 1]]
    const edge = event.shiftKey ? first : last
    if (document.activeElement === edge) {
      event.preventDefault()
      ;(event.shiftKey ? last : first).focus()
    }
  }
}

const backdropStyle: CSSProperties = {
  position: 'fixed',
  inset: 0,
  zIndex: 30,
  display: 'grid',
  placeItems: 'center',
  padding: 'var(--space-4)',
  background: 'color-mix(in srgb, var(--color-bg) 70%, transparent)',
}
const dialogStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 'var(--space-4)',
  width: 'min(100%, var(--width-content))',
  padding: 'var(--space-6)',
  background: 'var(--color-surface)',
  color: 'var(--color-text)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-lg)',
  boxShadow: 'var(--shadow-lg)',
}
const titleStyle: CSSProperties = { margin: 0, fontSize: 'var(--text-md)', color: 'var(--color-text)' }
const buttonRowStyle: CSSProperties = { display: 'flex', flexWrap: 'wrap', justifyContent: 'flex-end', gap: 'var(--space-2)' }
const baseButtonStyle: CSSProperties = { minHeight: '44px', padding: '0 var(--space-4)', borderRadius: 'var(--radius-md)', fontWeight: 600 }
const cancelStyle: CSSProperties = { ...baseButtonStyle, background: 'transparent', color: 'var(--color-text)', border: '1px solid var(--color-border)' }
const confirmStyle: CSSProperties = { ...baseButtonStyle, background: 'var(--color-primary)', color: 'var(--color-text-on-primary)' }
const destructiveStyle: CSSProperties = { ...baseButtonStyle, background: 'var(--color-error)', color: 'var(--color-text-on-primary)' }
