import type { CSSProperties } from 'react'

/** Styles shared by the Settings screen's sections (design-system tokens only). */
export const fieldStyle: CSSProperties = { display: 'flex', flexDirection: 'column', gap: '6px' }
export const fieldsetStyle: CSSProperties = { ...fieldStyle, border: 'none', padding: 0, margin: 0 }
export const labelStyle: CSSProperties = { fontWeight: 600 }
export const legendStyle: CSSProperties = { fontWeight: 600, padding: 0 }
export const controlStyle: CSSProperties = {
  padding: '10px 12px',
  borderRadius: 'var(--radius)',
  border: '1px solid var(--color-border)',
  background: 'var(--color-surface)',
  color: 'var(--color-text)',
  fontSize: '1rem',
}
export const hintStyle: CSSProperties = {
  margin: 0,
  fontSize: '0.85rem',
  color: 'var(--color-text-muted)',
}
export const radioCardStyle = (isChecked: boolean): CSSProperties => ({
  display: 'flex',
  alignItems: 'flex-start',
  gap: '10px',
  padding: '10px 12px',
  borderRadius: 'var(--radius-lg)',
  border: '1px solid var(--color-border)',
  background: isChecked ? 'var(--color-surface-raised)' : 'var(--color-surface)',
  cursor: 'pointer',
})
export const radioTextStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '2px',
}
export const radioLabelStyle: CSSProperties = { fontWeight: 600, color: 'var(--color-text)' }
export const radioBadgeStyle: CSSProperties = {
  fontWeight: 400,
  fontSize: '0.85rem',
  color: 'var(--color-text-muted)',
}
export const radioDescriptionStyle: CSSProperties = {
  fontSize: '0.85rem',
  color: 'var(--color-text-muted)',
}
export const warningNoteStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '4px',
  borderLeft: '3px solid var(--color-warning)',
  background: 'var(--color-surface-raised)',
  borderRadius: 'var(--radius-lg)',
  boxShadow: 'var(--shadow-sm)',
  padding: '10px 14px',
  lineHeight: 'var(--leading-relaxed)',
}
export const warningTitleStyle: CSSProperties = {
  fontWeight: 600,
  fontSize: '0.8rem',
  color: 'var(--color-warning-text)',
}
export const warningBodyStyle: CSSProperties = { fontSize: '0.85rem', color: 'var(--color-text)' }
export const errorTextStyle: CSSProperties = { color: 'var(--color-error)', fontWeight: 600 }
export const successTextStyle: CSSProperties = { color: 'var(--color-success)', fontWeight: 600 }
