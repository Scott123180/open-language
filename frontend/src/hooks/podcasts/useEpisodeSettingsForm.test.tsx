import { act, renderHook } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { useEpisodeSettingsForm } from './useEpisodeSettingsForm'
import { episodeOptions } from '../../components/podcasts/settingsFixtures.test.utils'
import type { PodcastPreferences } from '../../services/podcastsApi'

const preferences = {
  last_format: 'one_host',
  is_show_text_on: false,
  interests: [],
  learner_name: null,
  last_style: 'presented',
  last_line_length: 'long',
  last_invite_frequency: 'rarely',
} as PodcastPreferences

describe('useEpisodeSettingsForm (011 FR-008, FR-013)', () => {
  it('starts on the defaults with the show’s role and no subject', () => {
    const { result } = renderHook(() => useEpisodeSettingsForm(episodeOptions, undefined, 'caller'))

    expect(result.current.values).toEqual({
      style: 'balanced',
      line_length: 'medium',
      invite_frequency: 'sometimes',
      learner_role: 'caller',
      today_subject: '',
    })
    expect(result.current.summary).toBe('Balanced · Medium lines · Asked sometimes')
  })

  it('starts on the last-used style, lines and frequency, never the last role', () => {
    const { result } = renderHook(() => useEpisodeSettingsForm(episodeOptions, preferences, 'guest'))

    expect(result.current.values).toMatchObject({ style: 'presented', line_length: 'long', invite_frequency: 'rarely', learner_role: 'guest' })
    expect(result.current.summary).toBe('Presented · Long lines · Asked rarely')
  })

  it('follows each change and builds the request’s settings', () => {
    const { result } = renderHook(() => useEpisodeSettingsForm(episodeOptions, undefined, 'guest'))

    act(() => result.current.change('style', 'conversation'))
    act(() => result.current.change('today_subject', '  why we yawn '))

    expect(result.current.summary).toBe('Conversation · Medium lines · Asked sometimes')
    expect(result.current.requestSettings()).toEqual({
      style: 'conversation',
      line_length: 'medium',
      invite_frequency: 'sometimes',
      learner_role: 'guest',
      today_subject: 'why we yawn',
    })
  })

  it('sends no subject when the field is empty', () => {
    const { result } = renderHook(() => useEpisodeSettingsForm(episodeOptions, undefined, 'guest'))

    expect(result.current.requestSettings().today_subject).toBeNull()
  })
})
