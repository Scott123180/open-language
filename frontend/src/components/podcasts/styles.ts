import type { CSSProperties } from 'react'

/** Shared podcast styles. Design-system tokens only (docs/design-system.md). */
export const cardStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 'var(--space-1)',
  width: '100%',
  padding: 'var(--space-4)',
  textAlign: 'left',
  background: 'var(--color-surface)',
  color: 'var(--color-text)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-lg)',
  boxShadow: 'var(--shadow-sm)',
  cursor: 'pointer',
}

export const mutedTextStyle: CSSProperties = {
  fontSize: 'var(--text-sm)',
  color: 'var(--color-text-muted)',
  lineHeight: 'var(--leading-normal)',
}

export const fieldsetStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 'var(--space-2)',
  margin: 0,
  padding: 'var(--space-4)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-lg)',
}

export const legendStyle: CSSProperties = {
  padding: '0 var(--space-1)',
  fontWeight: 'var(--weight-semibold)' as CSSProperties['fontWeight'],
  color: 'var(--color-text)',
}

export const radioLabelStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'flex-start',
  gap: 'var(--space-2)',
  minHeight: '44px',
  cursor: 'pointer',
  color: 'var(--color-text)',
}

export const primaryButtonStyle: CSSProperties = {
  minHeight: '44px',
  padding: '0 var(--space-5)',
  background: 'var(--color-primary)',
  color: 'var(--color-text-on-primary)',
  border: 'none',
  borderRadius: 'var(--radius-md)',
  fontWeight: 'var(--weight-semibold)' as CSSProperties['fontWeight'],
  cursor: 'pointer',
}

export const secondaryButtonStyle: CSSProperties = {
  minHeight: '44px',
  padding: '0 var(--space-4)',
  background: 'transparent',
  color: 'var(--color-text)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-md)',
  cursor: 'pointer',
}

/** Read by screen readers, not shown: a label whose control already says what it is. */
export const visuallyHiddenStyle: CSSProperties = {
  position: 'absolute',
  width: '1px',
  height: '1px',
  padding: 0,
  margin: '-1px',
  overflow: 'hidden',
  clip: 'rect(0, 0, 0, 0)',
  whiteSpace: 'nowrap',
  border: 0,
}

/** A group of selection tiles: a legend over a vertical stack (design-system Selection Tile Cards). */
export const choiceGroupStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '10px',
  margin: 0,
  padding: 0,
  border: 'none',
}

export const choiceLegendStyle: CSSProperties = { ...legendStyle, padding: 0, marginBottom: 'var(--space-2)' }

export const choiceTileStyle = (isChecked: boolean): CSSProperties => ({
  display: 'flex',
  alignItems: 'flex-start',
  gap: 'var(--space-3)',
  padding: 'var(--space-3) var(--space-4)',
  border: `2px solid ${isChecked ? 'var(--color-primary)' : 'var(--color-border)'}`,
  borderRadius: 'var(--radius-lg)',
  background: isChecked ? 'var(--color-primary-subtle)' : 'var(--color-surface)',
  cursor: 'pointer',
  transition: 'border-color var(--transition-fast), background var(--transition-fast)',
})

export const choiceLabelStyle = (isChecked: boolean): CSSProperties => ({
  fontWeight: 'var(--weight-semibold)' as CSSProperties['fontWeight'],
  color: isChecked ? 'var(--color-primary-text)' : 'var(--color-text)',
})

export const choiceDetailStyle = (isChecked: boolean): CSSProperties => ({
  fontSize: 'var(--text-sm)',
  lineHeight: 'var(--leading-normal)',
  color: isChecked ? 'var(--color-primary-text)' : 'var(--color-text-muted)',
})
