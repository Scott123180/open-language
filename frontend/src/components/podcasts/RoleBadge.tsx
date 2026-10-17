import type { CSSProperties } from 'react'
import { LEARNER_ROLES, roleText } from './learnerRole'

const badgeStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 'var(--space-2)',
  padding: 'var(--space-1) var(--space-3)',
  background: 'var(--color-primary-subtle)',
  color: 'var(--color-primary-text)',
  borderRadius: 'var(--radius-full)',
  fontSize: 'var(--text-sm)',
  fontWeight: 'var(--weight-semibold)' as CSSProperties['fontWeight'],
}

/** The learner's part in a show as a pill whose icon tells the roles apart at a glance. */
export default function RoleBadge({ role }: { role: string }) {
  const Icon = LEARNER_ROLES[role]?.Icon
  return (
    <span style={badgeStyle}>
      {Icon && <Icon size={14} />}
      {roleText(role)}
    </span>
  )
}
