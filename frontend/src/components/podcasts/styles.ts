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
