import { act, renderHook } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { usePartQueue } from './usePartQueue'
import type { LinePartEvent } from '../../services/podcastsApi'

const part = (index: number, streamId = 's1'): LinePartEvent => ({
  event: 'line_part',
  stream_id: streamId,
  index,
  text: `Frase ${index}.`,
  audio_url: `/parts/${streamId}/${index}`,
})

describe('usePartQueue', () => {
  it('plays the first part at once', () => {
    const { result } = renderHook(() => usePartQueue())

    act(() => result.current.add(part(0)))

    expect(result.current.current).toBe('/parts/s1/0')
  })

  it('waits for the current part to end before the next', () => {
    const { result } = renderHook(() => usePartQueue())
    act(() => {
      result.current.add(part(0))
      result.current.add(part(1))
    })

    expect(result.current.current).toBe('/parts/s1/0')
    act(() => result.current.ended())
    expect(result.current.current).toBe('/parts/s1/1')
  })

  it('plays parts in index order, whatever order they arrive in', () => {
    const { result } = renderHook(() => usePartQueue())
    act(() => {
      result.current.add(part(0))
      result.current.add(part(2))
      result.current.add(part(1))
    })

    act(() => result.current.ended())
    expect(result.current.current).toBe('/parts/s1/1')
    act(() => result.current.ended())
    expect(result.current.current).toBe('/parts/s1/2')
  })

  it('plays a part that arrives late as soon as it arrives', () => {
    const { result } = renderHook(() => usePartQueue())
    act(() => result.current.add(part(0)))
    act(() => result.current.ended())

    expect(result.current.current).toBeNull()
    act(() => result.current.add(part(1)))
    expect(result.current.current).toBe('/parts/s1/1')
  })

  it('skips a part with no audio', () => {
    const { result } = renderHook(() => usePartQueue())

    act(() => result.current.add({ ...part(0), audio_url: null }))

    expect(result.current.current).toBeNull()
  })

  it('stops and forgets every part', () => {
    const { result } = renderHook(() => usePartQueue())
    act(() => {
      result.current.add(part(0))
      result.current.add(part(1))
    })

    act(() => result.current.stop())
    act(() => result.current.ended())

    expect(result.current.current).toBeNull()
  })

  it('starts again at the first part of a new stream', () => {
    const { result } = renderHook(() => usePartQueue())
    act(() => result.current.add(part(0)))
    act(() => result.current.ended())

    act(() => result.current.add(part(0, 's2')))

    expect(result.current.current).toBe('/parts/s2/0')
  })
})
