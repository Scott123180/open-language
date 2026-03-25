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

export function IconEye({ size = 16, strokeWidth = 2, style }: IconProps) {
  return (
    <svg {...base(size, strokeWidth)} style={style}>
      <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  )
}

export function IconBrain({ size = 16, strokeWidth = 2, style }: IconProps) {
  return (
    <svg {...base(size, strokeWidth)} style={style}>
      <path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z" />
      <path d="M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z" />
      <path d="M15 13a4.5 4.5 0 0 1-3-4 4.5 4.5 0 0 1-3 4" />
      <path d="M17.599 6.5a3 3 0 0 0 .399-1.375" />
      <path d="M6.003 5.125A3 3 0 0 0 6.401 6.5" />
      <path d="M3.477 10.896a4 4 0 0 1 .585-.396" />
      <path d="M19.938 10.5a4 4 0 0 1 .585.396" />
      <path d="M6 18a4 4 0 0 1-1.967-.516" />
      <path d="M19.967 17.484A4 4 0 0 1 18 18" />
    </svg>
  )
}

export function IconHeadphones({ size = 16, strokeWidth = 2, style }: IconProps) {
  return (
    <svg {...base(size, strokeWidth)} style={style}>
      <path d="M3 14h3a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-7a9 9 0 0 1 18 0v7a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3" />
    </svg>
  )
}

export function IconPenLine({ size = 16, strokeWidth = 2, style }: IconProps) {
  return (
    <svg {...base(size, strokeWidth)} style={style}>
      <path d="M12 20h9" />
      <path d="M16.376 3.622a1 1 0 0 1 3.002 3.002L7.368 18.635a2 2 0 0 1-.855.506l-2.872.838a.5.5 0 0 1-.62-.62l.838-2.872a2 2 0 0 1 .506-.854z" />
    </svg>
  )
}

export function IconTextCursor({ size = 16, strokeWidth = 2, style }: IconProps) {
  return (
    <svg {...base(size, strokeWidth)} style={style}>
      <path d="M17 22h-1a4 4 0 0 1-4-4V6a4 4 0 0 1 4-4h1" />
      <path d="M7 22h1a4 4 0 0 0 4-4v-1" />
      <path d="M7 2h1a4 4 0 0 1 4 4v1" />
    </svg>
  )
}

export function IconShuffle({ size = 16, strokeWidth = 2, style }: IconProps) {
  return (
    <svg {...base(size, strokeWidth)} style={style}>
      <path d="M2 18h1.4c1.3 0 2.5-.6 3.3-1.7l6.1-8.6c.7-1.1 2-1.7 3.3-1.7H22" />
      <path d="m18 2 4 4-4 4" />
      <path d="M2 6h1.9c1.5 0 2.9.9 3.5 2.2" />
      <path d="M22 18h-5.9c-1.3 0-2.6-.7-3.3-1.8l-.5-.8" />
      <path d="m18 14 4 4-4 4" />
    </svg>
  )
}

export function IconSparkles({ size = 16, strokeWidth = 2, style }: IconProps) {
  return (
    <svg {...base(size, strokeWidth)} style={style}>
      <path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z" />
      <path d="M20 3v4" />
      <path d="M22 5h-4" />
      <path d="M4 17v2" />
      <path d="M5 18H3" />
    </svg>
  )
}

export function IconFlame({ size = 16, strokeWidth = 2, style }: IconProps) {
  return (
    <svg {...base(size, strokeWidth)} style={style}>
      <path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z" />
    </svg>
  )
}

export function IconTrophy({ size = 16, strokeWidth = 2, style }: IconProps) {
  return (
    <svg {...base(size, strokeWidth)} style={style}>
      <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6" />
      <path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18" />
      <path d="M4 22h16" />
      <path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22" />
      <path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22" />
      <path d="M18 2H6v7a6 6 0 0 0 12 0V2z" />
    </svg>
  )
}
