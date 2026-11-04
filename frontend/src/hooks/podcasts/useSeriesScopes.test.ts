import { act, renderHook } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { useSeriesScopes } from './useSeriesScopes'
import type { SeriesSettings } from '../../services/podcastsApi'

const usual: SeriesSettings = {
  format: 'one_host',
  length: 'medium',
  style: 'balanced',
  line_length: 'medium',
  invite_frequency: 'sometimes',
  learner_role: 'guest',
}

const scopes = (settings: SeriesSettings | null = usual) => renderHook(() => useSeriesScopes(settings))

describe('useSeriesScopes (011 data-model §6.1)', () => {
  it('asks on the first change and applies nothing yet', () => {
    const { result } = scopes()
    const apply = vi.fn()

    act(() => result.current.request('style', 'presented', apply))

    expect(result.current.asking).toBe('style')
    expect(apply).not.toHaveBeenCalled()
  })

  it('Just this episode applies the change for this episode', () => {
    const { result } = scopes()
    const apply = vi.fn()
    act(() => result.current.request('style', 'presented', apply))

    act(() => result.current.answer('this-episode'))

    expect(apply).toHaveBeenCalledOnce()
    expect(result.current.scopeOf('style')).toBe('this-episode')
    expect(result.current.asking).toBeNull()
    expect(result.current.fromNowOn()).toEqual([])
  })

  it('This and later episodes keeps the change for later', () => {
    const { result } = scopes()
    act(() => result.current.request('format', 'panel', vi.fn()))

    act(() => result.current.answer('from-now-on'))

    expect(result.current.scopeOf('format')).toBe('from-now-on')
    expect(result.current.fromNowOn()).toEqual(['format'])
  })

  it('Cancel reverts the change', () => {
    const { result } = scopes()
    const apply = vi.fn()
    act(() => result.current.request('style', 'presented', apply))

    act(() => result.current.cancel())

    expect(apply).not.toHaveBeenCalled()
    expect(result.current.asking).toBeNull()
    expect(result.current.scopeOf('style')).toBeUndefined()
  })

  it('changing again keeps the scope without asking', () => {
    const { result } = scopes()
    act(() => result.current.request('style', 'presented', vi.fn()))
    act(() => result.current.answer('from-now-on'))
    const apply = vi.fn()

    act(() => result.current.request('style', 'conversation', apply))

    expect(apply).toHaveBeenCalledOnce()
    expect(result.current.asking).toBeNull()
    expect(result.current.scopeOf('style')).toBe('from-now-on')
  })

  it('setting back to the usual value clears the scope', () => {
    const { result } = scopes()
    act(() => result.current.request('style', 'presented', vi.fn()))
    act(() => result.current.answer('this-episode'))
    const apply = vi.fn()

    act(() => result.current.request('style', 'balanced', apply))

    expect(apply).toHaveBeenCalledOnce()
    expect(result.current.scopeOf('style')).toBeUndefined()
  })

  it('asks nothing on a series’ first episode', () => {
    const { result } = scopes(null)
    const apply = vi.fn()

    act(() => result.current.request('style', 'presented', apply))

    expect(apply).toHaveBeenCalledOnce()
    expect(result.current.asking).toBeNull()
  })

  it('clear forgets every scope', () => {
    const { result } = scopes()
    act(() => result.current.request('style', 'presented', vi.fn()))
    act(() => result.current.answer('from-now-on'))

    act(() => result.current.clear())

    expect(result.current.fromNowOn()).toEqual([])
  })
})
