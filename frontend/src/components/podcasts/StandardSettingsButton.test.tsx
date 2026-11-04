import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as podcasts from '../../services/podcastsApi'
import StandardSettingsButton from './StandardSettingsButton'
import { seriesDetail } from './fixtures.test.utils'
import { queryWrapper } from '../../hooks/podcasts/queryWrapper.test.utils'

vi.mock('../../services/podcastsApi')

beforeEach(() => {
  vi.clearAllMocks()
})

const renderButton = (isStandard: boolean, onReset = vi.fn()) => {
  render(<StandardSettingsButton detail={seriesDetail({ is_standard: isStandard })} onReset={onReset} />, { wrapper: queryWrapper().wrapper })
  return onReset
}

describe('StandardSettingsButton (011 FR-019)', () => {
  it('is absent while the series is on the show’s standard settings', () => {
    renderButton(true)

    expect(screen.queryByRole('button', { name: "Use the show's standard settings" })).not.toBeInTheDocument()
  })

  it('asks first, then resets the series and the form', async () => {
    vi.mocked(podcasts.resetSeriesSettings).mockResolvedValue(seriesDetail({ is_standard: true }))
    const onReset = renderButton(false)

    await userEvent.click(screen.getByRole('button', { name: "Use the show's standard settings" }))
    expect(screen.getByRole('alertdialog')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Use standard settings' }))

    await waitFor(() => expect(onReset).toHaveBeenCalledOnce())
    expect(podcasts.resetSeriesSettings).toHaveBeenCalledWith(4)
  })

  it('changes nothing when cancelled', async () => {
    const onReset = renderButton(false)

    await userEvent.click(screen.getByRole('button', { name: "Use the show's standard settings" }))
    await userEvent.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(podcasts.resetSeriesSettings).not.toHaveBeenCalled()
    expect(onReset).not.toHaveBeenCalled()
  })
})
