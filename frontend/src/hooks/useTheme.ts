import { useState, useEffect } from 'react'

type ThemePreference = 'light' | 'dark' | 'system'

const STORAGE_KEY = 'theme-preference'

function applyTheme(preference: ThemePreference) {
  const root = document.documentElement
  if (preference === 'system') {
    root.removeAttribute('data-theme')
  } else {
    root.setAttribute('data-theme', preference)
  }
}

function readStoredPreference(): ThemePreference {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === 'light' || stored === 'dark' || stored === 'system') return stored
  return 'system'
}

export function useTheme() {
  const [preference, setPreference] = useState<ThemePreference>(readStoredPreference)

  useEffect(() => {
    applyTheme(preference)
  }, [preference])

  const setTheme = (next: ThemePreference) => {
    localStorage.setItem(STORAGE_KEY, next)
    setPreference(next)
  }

  return { preference, setTheme }
}

export function initTheme() {
  applyTheme(readStoredPreference())
}
