import type { CSSProperties } from 'react'
import type { HostDraft } from '../../services/podcastsApi'
import { mutedTextStyle } from './styles'

interface ShowCastProps {
  hosts: HostDraft[]
  labelOf: (personalityId: string) => string
}

const avatarStyle: CSSProperties = {
  display: 'grid',
  placeItems: 'center',
  flexShrink: 0,
  width: '32px',
  height: '32px',
  borderRadius: 'var(--radius-full)',
  background: 'var(--color-surface-raised)',
  color: 'var(--color-primary)',
  fontWeight: 'var(--weight-semibold)' as CSSProperties['fontWeight'],
}

function CastMember({ name, personality }: { name: string; personality: string }) {
  return (
    <span style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', minWidth: 0 }}>
      <span style={avatarStyle}>{name.charAt(0)}</span>
      <span style={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <span style={{ fontSize: 'var(--text-sm)', fontWeight: 'var(--weight-semibold)' as never }}>{name}</span>
        <span style={{ ...mutedTextStyle, fontSize: 'var(--text-xs)' }}>{personality}</span>
      </span>
    </span>
  )
}

/** A show's hosts, each an initial beside their name and personality. */
export default function ShowCast({ hosts, labelOf }: ShowCastProps) {
  return (
    <span style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-3) var(--space-5)' }}>
      {hosts.map((host) => <CastMember key={host.slot} name={host.name} personality={labelOf(host.personality_id)} />)}
    </span>
  )
}
