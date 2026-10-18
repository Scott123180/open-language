import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import RememberedPoints from './RememberedPoints'
import { seriesDetail } from './fixtures.test.utils'

const renderPoints = (detail = seriesDetail(), onStartOver = vi.fn()) => {
  render(<RememberedPoints detail={detail} onStartOver={onStartOver} isStartingOver={false} />)
  return onStartOver
}

describe('RememberedPoints', () => {
  it('discloses the topics and what the learner shared, with their episodes', async () => {
    renderPoints()
    const toggle = screen.getByRole('button', { name: 'What the hosts remember' })
    expect(toggle).toHaveAttribute('aria-expanded', 'false')

    await userEvent.click(toggle)

    expect(toggle).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText('Why we yawn')).toBeInTheDocument()
    expect(screen.getByText('You hate mornings.')).toBeInTheDocument()
    expect(screen.getAllByText('Episode 1')).toHaveLength(2)
  })

  it('says it is updating while the hosts catch up', async () => {
    renderPoints(seriesDetail({ memory_status: 'running' }))

    await userEvent.click(screen.getByRole('button', { name: 'What the hosts remember' }))

    expect(screen.getByText('Updating…')).toBeInTheDocument()
  })

  it('asks before starting over', async () => {
    const onStartOver = renderPoints()
    await userEvent.click(screen.getByRole('button', { name: 'What the hosts remember' }))

    await userEvent.click(screen.getByRole('button', { name: 'Start over…' }))
    expect(screen.getByRole('alertdialog')).toHaveAccessibleName('Start over?')
    expect(onStartOver).not.toHaveBeenCalled()

    await userEvent.click(screen.getByRole('button', { name: 'Start over' }))
    expect(onStartOver).toHaveBeenCalled()
  })
})
