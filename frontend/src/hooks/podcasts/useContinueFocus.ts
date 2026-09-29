import { useEffect, useRef } from 'react'
import type { RefObject } from 'react'
import type { Awaiting } from '../../services/podcastsApi'

/** After a line arrives, focus moves to Continue, so the keyboard stays on the next step. */
export function useContinueFocus(lineCount: number, awaiting: Awaiting): RefObject<HTMLButtonElement> {
  const continueRef = useRef<HTMLButtonElement>(null)
  useEffect(() => {
    if (awaiting === 'continue') continueRef.current?.focus()
  }, [lineCount, awaiting])
  return continueRef
}
