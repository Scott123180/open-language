import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import PodcastSetup from './PodcastSetup'
import { chooseOption } from '../components/shared/themedSelect.test.utils'
import * as podcasts from '../services/podcastsApi'
import { catalog, episode, preferences } from './podcastPageFixtures.test.utils'
import { generatedShow, seriesDetail, seriesListing } from '../components/podcasts/fixtures.test.utils'

vi.mock('../services/podcastsApi')

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => ({
  ...(await vi.importActual<typeof import('react-router-dom')>('react-router-dom')),
  useNavigate: () => mockNavigate,
}))

const renderSetup = (search = '?show=weekend-food-talk') =>
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter initialEntries={[`/podcasts/setup${search}`]}>
        <PodcastSetup />
      </MemoryRouter>
    </QueryClientProvider>,
  )

const renderWithDraft = (state: unknown) =>
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter initialEntries={[{ pathname: '/podcasts/setup', state }]}>
        <PodcastSetup />
      </MemoryRouter>
    </QueryClientProvider>,
  )

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(podcasts.getPodcastCatalog).mockResolvedValue(catalog)
  vi.mocked(podcasts.getPodcastPreferences).mockResolvedValue(preferences)
  vi.mocked(podcasts.startEpisode).mockResolvedValue(episode())
})

describe('PodcastSetup page', () => {
  it('shows the show, its hosts and the learners role', async () => {
    renderSetup()

    expect(await screen.findByRole('heading', { name: 'Weekend Food Talk' })).toBeInTheDocument()
    expect(screen.getByText('Lucía')).toBeInTheDocument()
    expect(screen.getByText('Marco')).toBeInTheDocument()
  })

  it('starts on the last format and the default length', async () => {
    renderSetup()

    await waitFor(() => expect(screen.getByRole('radio', { name: /Panel/ })).toBeChecked())
    expect(screen.getByRole('radio', { name: /Medium/ })).toBeChecked()
  })

  it('prefills the learners name', async () => {
    renderSetup()

    await waitFor(() => expect(screen.getByLabelText(/Your name/)).toHaveValue('Sam'))
  })

  it('starts the episode with the chosen options and opens it', async () => {
    renderSetup()
    await waitFor(() => expect(screen.getByRole('radio', { name: /Panel/ })).toBeChecked())
    fireEvent.click(screen.getByRole('radio', { name: /One host/ }))
    fireEvent.click(screen.getByRole('radio', { name: /Short/ }))

    fireEvent.click(screen.getByRole('button', { name: 'Start episode 1' }))

    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/podcasts/episodes/57'))
    expect(podcasts.startEpisode).toHaveBeenCalledWith({
      show: catalog.shows[0],
      format: 'one_host',
      length: 'short',
      learner_name: 'Sam',
      kind: 'series',
    })
  })

  it('shows why an episode could not start', async () => {
    vi.mocked(podcasts.startEpisode).mockRejectedValue(new Error('The practice language changed. Pick the show again.'))
    renderSetup()
    await screen.findByRole('heading', { name: 'Weekend Food Talk' })

    fireEvent.click(screen.getByRole('button', { name: 'Start episode 1' }))

    expect(await screen.findByText('The practice language changed. Pick the show again.')).toBeInTheDocument()
  })

  it('returns to Podcasts with a message for an unknown show', async () => {
    renderSetup('?show=missing')

    await waitFor(() =>
      expect(mockNavigate).toHaveBeenCalledWith('/podcasts', {
        replace: true,
        state: { message: expect.stringMatching(/isn't available/) },
      }),
    )
  })
})

describe('PodcastSetup page — voice notices (spec edge case)', () => {
  const withVoices = (voices: Partial<typeof catalog.voices>) => ({ ...catalog, voices: { ...catalog.voices, ...voices } })

  it('says the hosts share one voice when a two-host format is chosen', async () => {
    vi.mocked(podcasts.getPodcastCatalog).mockResolvedValue(withVoices({ installed_count: 1, shared_voice_notice: 'Both hosts will share one voice.' }))
    renderSetup()

    await waitFor(() => expect(screen.getByRole('radio', { name: /Panel/ })).toBeChecked())

    expect(screen.getByRole('status')).toHaveTextContent('Both hosts will share one voice.')
    fireEvent.click(screen.getByRole('radio', { name: /One host/ }))
    expect(screen.queryByText('Both hosts will share one voice.')).not.toBeInTheDocument()
  })

  it('says when no voice is installed', async () => {
    vi.mocked(podcasts.getPodcastCatalog).mockResolvedValue(withVoices({ installed_count: 0, unavailable_message: 'No Spanish voice is installed.' }))

    renderSetup()

    expect(await screen.findByText('No Spanish voice is installed.')).toBeInTheDocument()
  })
})

describe('PodcastSetup page — generated drafts (US4)', () => {
  const generated = { draft: generatedShow, idea: 'nurses', previousTitles: [] }

  it('sets up the draft passed in router state', async () => {
    renderWithDraft(generated)

    expect(await screen.findByRole('heading', { name: 'Night Shift Abroad' })).toBeInTheDocument()
  })

  it('starts the episode with the generated draft', async () => {
    renderWithDraft(generated)

    fireEvent.click(await screen.findByRole('button', { name: 'Start episode 1' }))

    await waitFor(() => expect(podcasts.startEpisode).toHaveBeenCalledWith(expect.objectContaining({ show: generatedShow })))
  })

  it('offers another version of a generated show, avoiding the titles so far', async () => {
    vi.mocked(podcasts.generateShow).mockResolvedValue({ ...generatedShow, title: 'Far From Home' })
    renderWithDraft(generated)

    fireEvent.click(await screen.findByRole('button', { name: 'Another version' }))

    expect(await screen.findByRole('heading', { name: 'Far From Home' })).toBeInTheDocument()
    expect(podcasts.generateShow).toHaveBeenCalledWith('nurses', ['Night Shift Abroad'])
  })

  it('shows why another version could not be made', async () => {
    vi.mocked(podcasts.generateShow).mockRejectedValue(new Error('The show came back unreadable. Please try again.'))
    renderWithDraft(generated)

    fireEvent.click(await screen.findByRole('button', { name: 'Another version' }))

    expect(await screen.findByText('The show came back unreadable. Please try again.')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Night Shift Abroad' })).toBeInTheDocument()
  })

  it('offers no other version of a surprise or a ready-made show', async () => {
    renderWithDraft({ draft: { ...generatedShow, source: 'surprise' }, idea: null, previousTitles: [] })
    await screen.findByRole('heading', { name: 'Night Shift Abroad' })

    expect(screen.queryByRole('button', { name: 'Another version' })).not.toBeInTheDocument()
  })

  it('offers no other version of a ready-made show', async () => {
    renderSetup()
    await screen.findByRole('heading', { name: 'Weekend Food Talk' })

    expect(screen.queryByRole('button', { name: 'Another version' })).not.toBeInTheDocument()
  })

  it('returns to Podcasts with a plain message when the draft is gone', async () => {
    renderSetup('')

    await waitFor(() =>
      expect(mockNavigate).toHaveBeenCalledWith('/podcasts', {
        replace: true,
        state: { message: expect.stringMatching(/Generate it again/) },
      }),
    )
  })
})

describe('PodcastSetup page — shaping the hosts (US5)', () => {
  const pablo = { slot: 'second' as const, name: 'Pablo', personality_id: 'joker', voice_key: 'es_ES-davefx-medium', show_role: 'co_host', angle: null }

  const onPanel = async () => {
    renderSetup()
    await waitFor(() => expect(screen.getByRole('radio', { name: /Panel/ })).toBeChecked())
  }

  it('replaces only the shuffled host', async () => {
    vi.mocked(podcasts.shuffleHost).mockResolvedValue(pablo)
    await onPanel()

    fireEvent.click(screen.getByRole('button', { name: 'Shuffle Marco' }))

    expect(await screen.findByText('Pablo')).toBeInTheDocument()
    expect(screen.getByText('Lucía')).toBeInTheDocument()
    expect(podcasts.shuffleHost).toHaveBeenCalledWith({ language: 'es', slot: 'second', hosts: catalog.shows[0].hosts, learner_name: 'Sam' })
  })

  it('starts the episode with the hosts as the learner left them', async () => {
    vi.mocked(podcasts.shuffleHost).mockResolvedValue(pablo)
    await onPanel()
    fireEvent.click(screen.getByRole('button', { name: 'Shuffle Marco' }))
    await screen.findByText('Pablo')
    chooseOption("Lucía's personality", 'Dry sceptic')

    fireEvent.click(screen.getByRole('button', { name: 'Start episode 1' }))

    await waitFor(() => expect(podcasts.startEpisode).toHaveBeenCalled())
    const { show } = vi.mocked(podcasts.startEpisode).mock.calls[0][0]
    expect(show.hosts).toEqual([{ ...catalog.shows[0].hosts[0], personality_id: 'dry_sceptic' }, pablo])
  })

  it('shows why a shuffle failed and keeps the host', async () => {
    vi.mocked(podcasts.shuffleHost).mockRejectedValue(new Error('The practice language changed. Pick the show again.'))
    await onPanel()

    fireEvent.click(screen.getByRole('button', { name: 'Shuffle Marco' }))

    expect(await screen.findByText('The practice language changed. Pick the show again.')).toBeInTheDocument()
    expect(screen.getByText('Marco')).toBeInTheDocument()
  })

  it('plays a hosts voice sample', async () => {
    const play = vi.spyOn(window.HTMLMediaElement.prototype, 'play').mockResolvedValue(undefined)
    vi.mocked(podcasts.voiceSampleUrl).mockReturnValue('/api/podcasts/voice-sample?voice_key=v&name=Luc%C3%ADa')
    await onPanel()

    fireEvent.click(screen.getByRole('button', { name: "Play Lucía's voice" }))

    expect(podcasts.voiceSampleUrl).toHaveBeenCalledWith(catalog.shows[0].hosts[0].voice_key, 'Lucía')
    expect(play).toHaveBeenCalled()
  })
})

describe('PodcastSetup page — a series (010 US1)', () => {
  const withSeries = (listing = seriesListing) => ({ ...catalog, shows: [...catalog.shows, listing] })
  const unfinished = { ...seriesListing, series: { ...seriesListing.series!, unfinished_episode: { conversation_id: 81, episode_number: 1 } } }

  beforeEach(() => {
    vi.mocked(podcasts.getPodcastCatalog).mockResolvedValue(withSeries())
    vi.mocked(podcasts.getSeries).mockResolvedValue(seriesDetail())
    vi.mocked(podcasts.catchUpSeriesMemory).mockResolvedValue({ status: 'up_to_date' })
  })

  it('shows the series hosts read-only with Start episode 2 as the one primary action', async () => {
    renderSetup('?show=big-little-questions')

    expect(await screen.findByRole('button', { name: 'Start episode 2' })).toBeInTheDocument()
    expect(screen.getByText('Hugo')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Shuffle/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Continue episode/ })).not.toBeInTheDocument()
  })

  it('offers to continue an unfinished episode first', async () => {
    vi.mocked(podcasts.getPodcastCatalog).mockResolvedValue(withSeries(unfinished))
    vi.mocked(podcasts.getSeries).mockResolvedValue(seriesDetail({ unfinished_episode: { conversation_id: 81, episode_number: 1 } }))
    renderSetup('?show=big-little-questions')

    fireEvent.click(await screen.findByRole('button', { name: 'Continue episode 1' }))

    expect(mockNavigate).toHaveBeenCalledWith('/podcasts/episodes/81')
    expect(screen.queryByRole('button', { name: 'Start episode 2' })).not.toBeInTheDocument()
  })

  it('waits for the hosts to catch up, then starts the next episode', async () => {
    vi.mocked(podcasts.getSeries).mockResolvedValue(seriesDetail({ memory_status: 'pending' }))
    let finish: (value: podcasts.CatchUpResult) => void = () => undefined
    vi.mocked(podcasts.catchUpSeriesMemory).mockImplementation((_id, options) =>
      options?.wait ? new Promise((resolve) => { finish = resolve }) : Promise.resolve({ status: 'started' }),
    )
    renderSetup('?show=big-little-questions')
    await waitFor(() => expect(podcasts.getSeries).toHaveBeenCalled())

    fireEvent.click(await screen.findByRole('button', { name: 'Start episode 2' }))

    expect(await screen.findByText('Hugo and Inés are catching up on episode 1. This takes a few seconds.')).toBeInTheDocument()
    finish({ status: 'up_to_date' })
    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/podcasts/episodes/57'))
    expect(podcasts.startEpisode).toHaveBeenCalledWith(expect.objectContaining({ kind: 'series', show: expect.objectContaining({ show_id: 'big-little-questions' }) }))
  })
})

describe('PodcastSetup page — a one-off beside the series (010 US2)', () => {
  const pablo = { slot: 'second' as const, name: 'Pablo', personality_id: 'joker', voice_key: 'es_ES-davefx-medium', show_role: 'co_host', angle: null }

  beforeEach(() => {
    vi.mocked(podcasts.getPodcastCatalog).mockResolvedValue({ ...catalog, shows: [...catalog.shows, seriesListing] })
    vi.mocked(podcasts.getSeries).mockResolvedValue(seriesDetail())
    vi.mocked(podcasts.catchUpSeriesMemory).mockResolvedValue({ status: 'up_to_date' })
    vi.mocked(podcasts.shuffleHost).mockResolvedValue(pablo)
  })

  it('offers the next episode by default and a one-off beside it', async () => {
    renderSetup('?show=big-little-questions')

    expect(await screen.findByRole('radio', { name: /Episode 2/ })).toBeChecked()
    expect(screen.getByRole('radio', { name: /One-off episode/ })).not.toBeChecked()
  })

  it('a one-off brings back Shuffle and starts as a one-off with the shuffled hosts', async () => {
    renderSetup('?show=big-little-questions')
    await waitFor(() => expect(screen.getByRole('radio', { name: /Panel/ })).toBeChecked())

    fireEvent.click(await screen.findByRole('radio', { name: /One-off episode/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Shuffle Inés' }))
    await screen.findByText('Pablo')
    fireEvent.click(screen.getByRole('button', { name: 'Start one-off episode' }))

    await waitFor(() => expect(podcasts.startEpisode).toHaveBeenCalled())
    const body = vi.mocked(podcasts.startEpisode).mock.calls[0][0]
    expect(body.kind).toBe('one_off')
    expect(body.show.hosts[1]).toEqual(pablo)
    expect(podcasts.catchUpSeriesMemory).not.toHaveBeenCalledWith(4, { wait: true })
  })
})
