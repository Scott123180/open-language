import type { CSSProperties } from 'react'

/** The word filter bar's styles: design-system tokens only. */
export const barStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '8px',
  padding: '10px 16px',
  borderBottom: '1px solid var(--color-border)',
  background: 'var(--color-surface)',
}

export const rowStyle: CSSProperties = { display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '8px' }

export const pillStyle = (color: string, isActive: boolean): CSSProperties => ({
  display: 'inline-flex',
  alignItems: 'center',
  gap: '5px',
  padding: '4px 10px',
  borderRadius: 'var(--radius-full)',
  border: `1.5px solid ${color}`,
  background: isActive ? `color-mix(in srgb, ${color} 12%, transparent)` : 'transparent',
  color: isActive ? color : 'var(--color-text-muted)',
  fontSize: 'var(--text-xs)',
  fontWeight: isActive ? 600 : 400,
  cursor: 'pointer',
  transition: 'all 0.15s',
  minHeight: '30px',
  minWidth: 'unset',
  whiteSpace: 'nowrap',
})

export const pillDotStyle = (color: string, isActive: boolean): CSSProperties => ({
  width: '7px',
  height: '7px',
  borderRadius: '50%',
  background: isActive ? color : 'transparent',
  border: `1.5px solid ${color}`,
  flexShrink: 0,
  transition: 'background 0.15s',
})

export const searchWrapperStyle: CSSProperties = { flex: 1, minWidth: '160px', position: 'relative' }

export const searchIconStyle: CSSProperties = {
  position: 'absolute',
  left: '9px',
  top: '50%',
  transform: 'translateY(-50%)',
  color: 'var(--color-text-muted)',
  pointerEvents: 'none',
  display: 'flex',
}

export const searchInputStyle: CSSProperties = {
  width: '100%',
  paddingLeft: '28px',
  paddingRight: '10px',
  paddingTop: '5px',
  paddingBottom: '5px',
  fontSize: 'var(--text-sm)',
  background: 'var(--color-bg)',
  color: 'var(--color-text)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-md)',
  outline: 'none',
  minHeight: '32px',
}

export const sortSelectStyle: CSSProperties = {
  fontSize: 'var(--text-xs)',
  padding: '5px 8px',
  background: 'var(--color-bg)',
  color: 'var(--color-text)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-md)',
  cursor: 'pointer',
  outline: 'none',
  minHeight: '32px',
  minWidth: 'unset',
  flexShrink: 0,
}

export const selectToggleStyle = (isSelecting: boolean, hasWords: boolean): CSSProperties => ({
  padding: '5px 12px',
  borderRadius: 'var(--radius-md)',
  border: isSelecting ? '1.5px solid var(--color-error)' : '1px solid var(--color-border)',
  background: isSelecting ? 'color-mix(in srgb, var(--color-error) 8%, transparent)' : 'transparent',
  color: isSelecting ? 'var(--color-error)' : 'var(--color-text-muted)',
  fontSize: 'var(--text-xs)',
  fontWeight: isSelecting ? 600 : 400,
  cursor: !hasWords ? 'not-allowed' : 'pointer',
  opacity: !hasWords ? 0.4 : 1,
  transition: 'all 0.15s',
  whiteSpace: 'nowrap',
  minHeight: 'unset',
  minWidth: 'unset',
  flexShrink: 0,
})

export const chipStyle = (isActive: boolean): CSSProperties => ({
  padding: '3px 10px',
  borderRadius: 'var(--radius-full)',
  border: '1.5px solid var(--color-border)',
  background: isActive ? 'color-mix(in srgb, var(--color-primary) 12%, transparent)' : 'transparent',
  color: isActive ? 'var(--color-primary)' : 'var(--color-text-muted)',
  fontSize: 'var(--text-xs)',
  fontWeight: isActive ? 600 : 400,
  cursor: 'pointer',
  transition: 'all 0.15s',
  minHeight: 'unset',
  minWidth: 'unset',
  whiteSpace: 'nowrap',
})
