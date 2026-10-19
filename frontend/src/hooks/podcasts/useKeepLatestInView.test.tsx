import { render } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useKeepLatestInView } from './useKeepLatestInView'

function List() {
  const ref = useKeepLatestInView<HTMLElement>()
  return <section ref={ref} aria-label="Lines" />
}

describe('useKeepLatestInView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('scrolls the list to its newest line when the list is resized', () => {
    let notifyResize = () => {}
    vi.stubGlobal('ResizeObserver', class {
      constructor(callback: () => void) { notifyResize = callback }
      observe() {}
      disconnect() {}
    })
    const { getByLabelText } = render(<List />)
    const list = getByLabelText('Lines')
    Object.defineProperty(list, 'scrollHeight', { value: 640 })

    notifyResize()

    expect(list.scrollTop).toBe(640)
  })

  it('renders without a resize observer', () => {
    vi.stubGlobal('ResizeObserver', undefined)

    const { getByLabelText } = render(<List />)

    expect(getByLabelText('Lines')).toBeInTheDocument()
  })
})
