import { useRef, useState, type KeyboardEvent } from 'react'

/** How long typed letters keep building one type-ahead search (WAI-ARIA APG). */
const TYPE_AHEAD_MS = 500

export interface ListboxNavigation {
  isOpen: boolean
  activeIndex: number
  open: () => void
  close: () => void
  choose: (index: number) => void
  onKeyDown: (event: KeyboardEvent) => void
}

/**
 * The keyboard model of a select-only combobox (WAI-ARIA APG): Enter, Space and Alt+↓ open;
 * ↑/↓/Home/End move; letters jump; Enter or Tab chooses; Escape closes without a change.
 */
export function useListboxNavigation(labels: string[], selectedIndex: number, onChoose: (index: number) => void): ListboxNavigation {
  const [isOpen, setOpen] = useState(false)
  const [activeIndex, setActive] = useState(selectedIndex)
  const typeAhead = useTypeAhead(labels)
  const open = () => {
    setActive(Math.max(selectedIndex, 0))
    setOpen(true)
  }
  const close = () => setOpen(false)
  const choose = (index: number) => {
    close()
    if (index >= 0) onChoose(index)
  }
  const move = (index: number) => setActive(clamp(index, labels.length))
  const nav = { isOpen, activeIndex, open, close, choose, move, typeAhead }
  return { isOpen, activeIndex, open, close, choose, onKeyDown: (event) => handleKey(event, nav) }
}

interface NavState {
  isOpen: boolean
  activeIndex: number
  open: () => void
  close: () => void
  choose: (index: number) => void
  move: (index: number) => void
  typeAhead: (key: string, from: number) => number
}

function handleKey(event: KeyboardEvent, nav: NavState): void {
  if (!nav.isOpen) return handleClosedKey(event, nav)
  const target = openKeyTarget(event, nav)
  if (target === undefined) return handleOpenAction(event, nav)
  event.preventDefault()
  nav.move(target)
}

function handleClosedKey(event: KeyboardEvent, nav: NavState): void {
  const opens = ['Enter', ' ', 'ArrowDown', 'ArrowUp'].includes(event.key)
  if (opens) {
    event.preventDefault()
    nav.open()
  } else if (isPrintable(event)) {
    nav.open()
    nav.move(nav.typeAhead(event.key, nav.activeIndex))
  }
}

/** Where a movement key puts the active option, or undefined when the key does not move it. */
function openKeyTarget(event: KeyboardEvent, nav: NavState): number | undefined {
  if (event.altKey && event.key === 'ArrowUp') return undefined
  const moves: Record<string, number> = {
    ArrowDown: nav.activeIndex + 1,
    ArrowUp: nav.activeIndex - 1,
    Home: 0,
    End: Number.MAX_SAFE_INTEGER,
  }
  if (event.key in moves) return moves[event.key]
  return isPrintable(event) && event.key !== ' ' ? nav.typeAhead(event.key, nav.activeIndex) : undefined
}

function handleOpenAction(event: KeyboardEvent, nav: NavState): void {
  const isChoice = event.key === 'Enter' || event.key === ' ' || (event.altKey && event.key === 'ArrowUp')
  if (isChoice) {
    event.preventDefault()
    nav.choose(nav.activeIndex)
  } else if (event.key === 'Escape') {
    event.preventDefault()
    event.stopPropagation()
    nav.close()
  } else if (event.key === 'Tab') {
    nav.choose(nav.activeIndex)
  }
}

/** Letters typed in quick succession search together; a repeated letter cycles its matches. */
function useTypeAhead(labels: string[]): (key: string, from: number) => number {
  const buffer = useRef('')
  const lastTyped = useRef(0)
  return (key, from) => {
    const now = Date.now()
    buffer.current = now - lastTyped.current > TYPE_AHEAD_MS ? key : buffer.current + key
    lastTyped.current = now
    const search = buffer.current.toLowerCase()
    const isRepeat = search.length > 1 && [...search].every((letter) => letter === search[0])
    return findMatch(labels, isRepeat ? search[0] : search, isRepeat || search.length === 1 ? from + 1 : from)
  }
}

function findMatch(labels: string[], search: string, start: number): number {
  for (let step = 0; step < labels.length; step += 1) {
    const index = (start + step) % labels.length
    if (labels[index].toLowerCase().startsWith(search)) return index
  }
  return Math.max(start - 1, 0) % Math.max(labels.length, 1)
}

const clamp = (index: number, count: number): number => Math.min(Math.max(index, 0), count - 1)

const isPrintable = (event: KeyboardEvent): boolean =>
  event.key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey
