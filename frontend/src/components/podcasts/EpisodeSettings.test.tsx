import { fireEvent, render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import EpisodeSettings from './EpisodeSettings'
import { episodeOptions } from './settingsFixtures.test.utils'
import type { EpisodeSettingValues } from '../../hooks/podcasts/useEpisodeSettingsForm'

vi.mock('../../services/podcastsApi')

const values: EpisodeSettingValues = {
  style: 'balanced',
  line_length: 'medium',
  invite_frequency: 'sometimes',
  learner_role: 'guest',
  today_subject: '',
}

function renderSettings(overrides: Partial<Parameters<typeof EpisodeSettings>[0]> = {}) {
  const props = {
    options: episodeOptions,
    form: { values, summary: 'Balanced · Medium lines · Asked sometimes', change: vi.fn(), requestSettings: vi.fn() },
    isListening: false,
    show: { title: 'Big Little Questions', premise: 'Everyday curiosities.', topic: 'everyday curiosities' },
    seriesId: null,
    subjectError: null,
    ...overrides,
  }
  render(<EpisodeSettings {...props} />)
  return props
}

describe('EpisodeSettings (011 contracts §11)', () => {
  it('is a closed disclosure named by its summary', () => {
    renderSettings()

    const toggle = screen.getByRole('button', { name: 'Episode settings: Balanced · Medium lines · Asked sometimes' })
    expect(toggle).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByRole('radiogroup', { name: 'Style' })).not.toBeInTheDocument()
  })

  it('opens to a radio group for each setting', () => {
    renderSettings()

    fireEvent.click(screen.getByRole('button', { name: /Episode settings/ }))

    for (const name of ['Style', 'Host lines', "How often you're asked", 'Your role']) {
      expect(screen.getByRole('radiogroup', { name })).toBeInTheDocument()
    }
    expect(screen.getByRole('button', { name: /Episode settings/ })).toHaveAttribute('aria-expanded', 'true')
  })

  it('reports a choice', () => {
    const props = renderSettings()
    fireEvent.click(screen.getByRole('button', { name: /Episode settings/ }))

    fireEvent.click(screen.getByRole('radio', { name: /Presented/ }))

    expect(props.form.change).toHaveBeenCalledWith('style', 'presented')
  })

  it('in Listen leaves out how often you are asked and your role', () => {
    renderSettings({ isListening: true })
    fireEvent.click(screen.getByRole('button', { name: /Episode settings/ }))

    expect(screen.queryByRole('radiogroup', { name: "How often you're asked" })).not.toBeInTheDocument()
    expect(screen.queryByRole('radiogroup', { name: 'Your role' })).not.toBeInTheDocument()
  })
})

describe('EpisodeSettings — experimental (011 T131)', () => {
  it('says inside the settings that configured talk is experimental', () => {
    renderSettings()

    fireEvent.click(screen.getByRole('button', { name: /^Episode settings:/ }))

    const note = screen.getByRole('note', { name: 'Episode settings are experimental' })
    expect(note).toHaveTextContent(/local model/)
  })

  it('keeps the note out of sight while the settings are closed', () => {
    renderSettings()

    expect(screen.queryByRole('note', { name: 'Episode settings are experimental' })).not.toBeInTheDocument()
  })
})
