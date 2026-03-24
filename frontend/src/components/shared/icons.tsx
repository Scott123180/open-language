/**
 * Inline SVG icon components — Lucide-style
 * 24×24 viewBox, stroke="currentColor", fill="none",
 * strokeWidth="2", strokeLinecap="round", strokeLinejoin="round"
 *
 * All icons are aria-hidden by default; accessibility comes from the
 * parent element's aria-label.
 */

interface IconProps {
  size?: number
  strokeWidth?: number
  style?: React.CSSProperties
}

const base = (size: number, sw: number): React.SVGProps<SVGSVGElement> => ({
  width: size,
  height: size,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: sw,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  'aria-hidden': true,
})

export function IconMic({ size = 16, strokeWidth = 2, style }: IconProps) {
  return (
    <svg {...base(size, strokeWidth)} style={style}>
      <rect x="9" y="2" width="6" height="13" rx="3" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
      <path d="M12 19v3" />
    </svg>
  )
}

export function IconStop({ size = 16, strokeWidth = 2, style }: IconProps) {
  return (
    <svg {...base(size, strokeWidth)} style={style}>
      <rect width="18" height="18" x="3" y="3" rx="2" />
    </svg>
  )
}

export function IconPlay({ size = 16, strokeWidth = 2, style }: IconProps) {
  return (
    <svg {...base(size, strokeWidth)} style={style}>
      <path d="M5 5a2 2 0 0 1 3.008-1.728l11.997 6.998a2 2 0 0 1 .003 3.458l-12 7A2 2 0 0 1 5 19z" />
    </svg>
  )
}

export function IconClock({ size = 16, strokeWidth = 2, style }: IconProps) {
  return (
    <svg {...base(size, strokeWidth)} style={style}>
      <circle cx="12" cy="12" r="10" />
      <path d="M12 6v6l4 2" />
    </svg>
  )
}

export function IconCheck({ size = 16, strokeWidth = 2, style }: IconProps) {
  return (
    <svg {...base(size, strokeWidth)} style={style}>
      <path d="M20 6 9 17l-5-5" />
    </svg>
  )
}

export function IconGlobe({ size = 16, strokeWidth = 2, style }: IconProps) {
  return (
    <svg {...base(size, strokeWidth)} style={style}>
      <circle cx="12" cy="12" r="10" />
      <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20" />
      <path d="M2 12h20" />
    </svg>
  )
}

export function IconArrowLeftRight({ size = 16, strokeWidth = 2, style }: IconProps) {
  return (
    <svg {...base(size, strokeWidth)} style={style}>
      <path d="M8 3 4 7l4 4" />
      <path d="M4 7h16" />
      <path d="m16 21 4-4-4-4" />
      <path d="M20 17H4" />
    </svg>
  )
}

export function IconLightbulb({ size = 16, strokeWidth = 2, style }: IconProps) {
  return (
    <svg {...base(size, strokeWidth)} style={style}>
      <path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5" />
      <path d="M9 18h6" />
      <path d="M10 22h4" />
    </svg>
  )
}

export function IconMessageCircle({ size = 16, strokeWidth = 2, style }: IconProps) {
  return (
    <svg {...base(size, strokeWidth)} style={style}>
      <path d="M2.992 16.342a2 2 0 0 1 .094 1.167l-1.065 3.29a1 1 0 0 0 1.236 1.168l3.413-.998a2 2 0 0 1 1.099.092 10 10 0 1 0-4.777-4.719" />
    </svg>
  )
}

export function IconArrowLeft({ size = 16, strokeWidth = 2, style }: IconProps) {
  return (
    <svg {...base(size, strokeWidth)} style={style}>
      <path d="M19 12H5" />
      <path d="m12 5-7 7 7 7" />
    </svg>
  )
}

export function IconSearch({ size = 16, strokeWidth = 2, style }: IconProps) {
  return (
    <svg {...base(size, strokeWidth)} style={style}>
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.3-4.3" />
    </svg>
  )
}

export function IconTrash({ size = 16, strokeWidth = 2, style }: IconProps) {
  return (
    <svg {...base(size, strokeWidth)} style={style}>
      <path d="M3 6h18" />
      <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
      <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
    </svg>
  )
}

export function IconVolume({ size = 16, strokeWidth = 2, style }: IconProps) {
  return (
    <svg {...base(size, strokeWidth)} style={style}>
      <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
      <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
      <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
    </svg>
  )
}
