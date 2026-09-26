import type { CSSProperties } from 'react'
import { useTheme } from '../../hooks/useTheme'
import { fieldStyle, labelStyle } from './settingsStyles'

const THEME_OPTIONS = [
  { value: 'light' as const, label: 'Light' },
  { value: 'dark' as const, label: 'Dark' },
  { value: 'system' as const, label: 'System' },
]

const themeButtonStyle = (isPressed: boolean): CSSProperties => ({
  padding: '8px 16px',
  borderRadius: 'var(--radius)',
  border: '1px solid var(--color-border)',
  background: isPressed ? 'var(--color-primary)' : 'var(--color-surface)',
  color: isPressed ? 'var(--color-text-on-primary)' : 'var(--color-text)',
  fontWeight: isPressed ? 600 : 400,
  cursor: 'pointer',
  minHeight: '44px',
})

export default function ThemeField() {
  const { preference, setTheme } = useTheme()
  return (
    <div style={fieldStyle}>
      <span style={labelStyle}>Theme</span>
      <div role="group" aria-label="Theme" style={{ display: 'flex', gap: '8px' }}>
        {THEME_OPTIONS.map(({ value, label }) => (
          <ThemeButton key={value} isPressed={preference === value} onPress={() => setTheme(value)}>
            {label}
          </ThemeButton>
        ))}
      </div>
    </div>
  )
}

interface ThemeButtonProps {
  isPressed: boolean
  onPress: () => void
  children: string
}

function ThemeButton({ isPressed, onPress, children }: ThemeButtonProps) {
  return (
    <button
      type="button"
      aria-pressed={isPressed}
      onClick={onPress}
      style={themeButtonStyle(isPressed)}
    >
      {children}
    </button>
  )
}
