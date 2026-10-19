import { useEffect, useRef } from 'react'

/**
 * Keeps a scrolling list at its newest line when the list itself gets shorter: the input bar
 * appearing, or the suggestions opening, would otherwise cover the end of the last line.
 */
export function useKeepLatestInView<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  useEffect(() => {
    const list = ref.current
    if (!list || typeof ResizeObserver === 'undefined') return
    const observer = new ResizeObserver(() => {
      list.scrollTop = list.scrollHeight
    })
    observer.observe(list)
    return () => observer.disconnect()
  }, [])
  return ref
}
