import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import {
  AccuracyTrendChart,
  DailyActivityChart,
  ClassificationOverTimeChart,
  ClassificationDonut,
  ModePerformanceChart,
} from './AnalyticsCharts'

// Recharts uses ResizeObserver — polyfill for jsdom
vi.stubGlobal('ResizeObserver', class {
  observe() {}
  unobserve() {}
  disconnect() {}
})

const accuracyData = [
  { session_id: 1, date: '2026-03-20', accuracy: 0.8 },
  { session_id: 2, date: '2026-03-21', accuracy: 0.9 },
]

const activityData = [
  { date: '2026-03-20', cards_reviewed: 10 },
  { date: '2026-03-21', cards_reviewed: 15 },
]

const overTimeData = [
  { date: '2026-03-20', not_practiced: 10, difficult: 3, almost_learned: 2, learned: 1 },
]

const donutData = { not_practiced: 10, difficult: 3, almost_learned: 2, learned: 5 }

const modeData = [
  { mode: 'recall', accuracy: 0.8 },
  { mode: 'produce', accuracy: 0.6 },
]

describe('AccuracyTrendChart', () => {
  it('renders without crashing with data', () => {
    render(<AccuracyTrendChart data={accuracyData} />)
  })

  it('shows empty-state when no data', () => {
    render(<AccuracyTrendChart data={[]} />)
    expect(screen.getByText(/no data/i)).toBeInTheDocument()
  })
})

describe('DailyActivityChart', () => {
  it('renders without crashing with data', () => {
    render(<DailyActivityChart data={activityData} />)
  })

  it('shows empty-state when no data', () => {
    render(<DailyActivityChart data={[]} />)
    expect(screen.getByText(/no data/i)).toBeInTheDocument()
  })
})

describe('ClassificationOverTimeChart', () => {
  it('renders without crashing with data', () => {
    render(<ClassificationOverTimeChart data={overTimeData} />)
  })

  it('shows empty-state when no data', () => {
    render(<ClassificationOverTimeChart data={[]} />)
    expect(screen.getByText(/no data/i)).toBeInTheDocument()
  })
})

describe('ClassificationDonut', () => {
  it('renders without crashing', () => {
    render(<ClassificationDonut data={donutData} />)
  })
})

describe('ModePerformanceChart', () => {
  it('renders without crashing with data', () => {
    render(<ModePerformanceChart data={modeData} />)
  })

  it('shows empty-state when no data', () => {
    render(<ModePerformanceChart data={[]} />)
    expect(screen.getByText(/no data/i)).toBeInTheDocument()
  })
})
