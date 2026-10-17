import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { IconArrowLeft } from '../shared/icons'

interface PageShellProps {
  title: string
  backTo: string
  backLabel: string
  /** The column's widest extent; the card grid on Podcasts takes more room than a form. */
  maxWidth?: string
  children: ReactNode
}

const mainStyle = {
  display: 'flex',
  flexDirection: 'column' as const,
  gap: 'var(--space-5)',
  width: '100%',
  margin: '0 auto',
  padding: 'var(--space-8) var(--space-4)',
  minHeight: '100vh',
  background: 'var(--color-bg)',
}

/** The frame of the Podcasts and setup screens: a back link and one heading. */
export default function PageShell({ title, backTo, backLabel, maxWidth = 'var(--width-wide)', children }: PageShellProps) {
  return (
    <main style={{ ...mainStyle, maxWidth }}>
      <Link to={backTo} className="back-link" style={{ alignSelf: 'flex-start' }}>
        <IconArrowLeft size={14} /> {backLabel}
      </Link>
      <h1 style={{ margin: 0, fontSize: 'var(--text-xl)', color: 'var(--color-text)' }}>{title}</h1>
      {children}
    </main>
  )
}
