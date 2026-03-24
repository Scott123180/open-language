import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import * as api from '../services/flashcardsApi'
import type { AnalyticsRange } from '../services/flashcardsApi'
import {
  AccuracyTrendChart,
  DailyActivityChart,
  ClassificationOverTimeChart,
  ClassificationDonut,
  ModePerformanceChart,
} from '../components/flashcards/AnalyticsCharts'
import ErrorBanner from '../components/shared/ErrorBanner'
import { IconArrowLeft } from '../components/shared/icons'

const RANGES: { label: string; value: AnalyticsRange }[] = [
  { label: '7 Days', value: '7d' },
  { label: '30 Days', value: '30d' },
  { label: 'All Time', value: 'all' },
]

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div
      style={{
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius)',
        padding: '16px',
        textAlign: 'center',
        flex: 1,
        minWidth: 0,
      }}
    >
      <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{value}</div>
      <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: '4px' }}>
        {label}
      </div>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section style={{ width: '100%', maxWidth: '800px' }}>
      <h2 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '8px' }}>{title}</h2>
      <div
        style={{
          background: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius)',
          padding: '16px',
        }}
      >
        {children}
      </div>
    </section>
  )
}

export default function FlashcardAnalytics() {
  const [range, setRange] = useState<AnalyticsRange>('7d')
  const navigate = useNavigate()

  const { data, isLoading, error } = useQuery({
    queryKey: ['analytics', range],
    queryFn: () => api.fetchAnalytics(range),
  })

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: '80px', color: 'var(--color-text-muted)' }}>
        Loading analytics…
      </div>
    )
  }

  if (error || !data) {
    return (
      <div style={{ padding: '24px' }}>
        <ErrorBanner message="Failed to load analytics." onDismiss={() => navigate('/flashcards')} />
      </div>
    )
  }

  const ag = data.at_a_glance

  return (
    <main
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '24px 16px',
        gap: '24px',
        background: 'var(--color-bg)',
        minHeight: '100vh',
      }}
    >
      <div style={{ width: '100%', maxWidth: '800px', display: 'flex', alignItems: 'center', gap: '12px' }}>
        <button
          onClick={() => navigate('/flashcards')}
          className="back-link"
          style={{ background: 'none', border: 'none', cursor: 'pointer' }}
          aria-label="Back to Flashcards"
        >
          <IconArrowLeft size={14} /> Back
        </button>
        <h1 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700 }}>Analytics</h1>
      </div>

      {/* At-a-glance stat cards */}
      <div style={{ display: 'flex', gap: '12px', width: '100%', maxWidth: '800px', flexWrap: 'wrap' }}>
        <StatCard label="Total Words" value={ag.total_words} />
        <StatCard label="Words Learned" value={ag.words_learned} />
        <StatCard label="Current Streak" value={`${ag.current_streak}d`} />
        <StatCard label="Sessions This Week" value={ag.sessions_this_week} />
      </div>

      {/* Time-range toggle */}
      <div style={{ display: 'flex', gap: '8px' }}>
        {RANGES.map(r => (
          <button
            key={r.value}
            onClick={() => setRange(r.value)}
            aria-pressed={range === r.value}
            style={{
              padding: '6px 14px',
              borderRadius: 'var(--radius)',
              border: '1px solid var(--color-border)',
              background: range === r.value ? 'var(--color-primary)' : 'var(--color-surface)',
              color: range === r.value ? '#fff' : 'var(--color-text)',
              cursor: 'pointer',
              fontSize: '0.85rem',
            }}
          >
            {r.label}
          </button>
        ))}
      </div>

      {/* Charts */}
      <Section title="Accuracy Trend">
        <AccuracyTrendChart data={data.accuracy_trend} />
      </Section>

      <Section title="Daily Activity">
        <DailyActivityChart data={data.daily_activity} />
      </Section>

      <Section title="Classification Distribution Over Time">
        <ClassificationOverTimeChart data={data.classification_over_time} />
      </Section>

      <Section title="Current Classification Breakdown">
        <ClassificationDonut data={data.classification_now} />
      </Section>

      <Section title="Performance by Mode">
        <ModePerformanceChart data={data.mode_performance} />
      </Section>

      {/* Hardest words table */}
      {data.hardest_words.length > 0 && (
        <Section title="Hardest Words">
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--color-border)', textAlign: 'left' }}>
                <th style={{ padding: '8px 4px' }}>Word</th>
                <th style={{ padding: '8px 4px' }}>Encounters</th>
                <th style={{ padding: '8px 4px' }}>Success</th>
              </tr>
            </thead>
            <tbody>
              {data.hardest_words.map(w => (
                <tr
                  key={w.id}
                  style={{ borderBottom: '1px solid var(--color-border)', cursor: 'pointer' }}
                  onClick={() => navigate(`/flashcards?word=${w.id}`)}
                  role="button"
                  aria-label={`View ${w.word} in word list`}
                >
                  <td style={{ padding: '8px 4px', fontWeight: 600 }}>{w.word}</td>
                  <td style={{ padding: '8px 4px', color: 'var(--color-text-muted)' }}>{w.encounters}</td>
                  <td style={{ padding: '8px 4px', color: w.success_rate < 0.5 ? '#ef4444' : 'var(--color-text)' }}>
                    {Math.round(w.success_rate * 100)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Section>
      )}

      {/* Recently learned */}
      {data.recently_learned.length > 0 && (
        <Section title="Recently Learned">
          <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {data.recently_learned.map(w => (
              <li
                key={w.id}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  fontSize: '0.9rem',
                  padding: '4px 0',
                }}
              >
                <span style={{ fontWeight: 600 }}>{w.word}</span>
                <span style={{ color: 'var(--color-text-muted)', fontSize: '0.8rem' }}>
                  {new Date(w.learned_at).toLocaleDateString()}
                </span>
              </li>
            ))}
          </ul>
        </Section>
      )}
    </main>
  )
}
