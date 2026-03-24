import {
  LineChart, Line, BarChart, Bar, AreaChart, Area,
  PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import type {
  AccuracyPoint,
  DailyActivityPoint,
  ClassificationOverTimePoint,
  ClassificationNow,
  ModePerformanceItem,
} from '../../services/flashcardsApi'

const CLASSIFICATION_COLORS = {
  not_practiced: '#94a3b8',
  difficult: '#ef4444',
  almost_learned: '#f59e0b',
  learned: '#22c55e',
}

const MODE_COLOR = '#6366f1'

function EmptyState({ message }: { message: string }) {
  return (
    <div style={{ textAlign: 'center', padding: '32px', color: 'var(--color-text-muted)', fontSize: '0.9rem' }}>
      {message}
    </div>
  )
}

export function AccuracyTrendChart({ data }: { data: AccuracyPoint[] }) {
  if (data.length === 0) return <EmptyState message="No data available yet" />
  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" tick={{ fontSize: 11 }} />
        <YAxis domain={[0, 1]} tickFormatter={(v) => `${Math.round(v * 100)}%`} tick={{ fontSize: 11 }} />
        <Tooltip formatter={(v: number) => `${Math.round(v * 100)}%`} />
        <Line type="monotone" dataKey="accuracy" stroke="#6366f1" dot={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}

export function DailyActivityChart({ data }: { data: DailyActivityPoint[] }) {
  if (data.length === 0) return <EmptyState message="No data available yet" />
  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip />
        <Bar dataKey="cards_reviewed" fill={MODE_COLOR} name="Cards" />
      </BarChart>
    </ResponsiveContainer>
  )
}

export function ClassificationOverTimeChart({ data }: { data: ClassificationOverTimePoint[] }) {
  if (data.length === 0) return <EmptyState message="No data available yet" />
  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip />
        <Legend />
        <Area type="monotone" dataKey="not_practiced" stackId="1" fill={CLASSIFICATION_COLORS.not_practiced} stroke={CLASSIFICATION_COLORS.not_practiced} name="Not Practiced" />
        <Area type="monotone" dataKey="difficult" stackId="1" fill={CLASSIFICATION_COLORS.difficult} stroke={CLASSIFICATION_COLORS.difficult} name="Difficult" />
        <Area type="monotone" dataKey="almost_learned" stackId="1" fill={CLASSIFICATION_COLORS.almost_learned} stroke={CLASSIFICATION_COLORS.almost_learned} name="Almost Learned" />
        <Area type="monotone" dataKey="learned" stackId="1" fill={CLASSIFICATION_COLORS.learned} stroke={CLASSIFICATION_COLORS.learned} name="Learned" />
      </AreaChart>
    </ResponsiveContainer>
  )
}

export function ClassificationDonut({ data }: { data: ClassificationNow }) {
  const pieData = [
    { name: 'Not Practiced', value: data.not_practiced, color: CLASSIFICATION_COLORS.not_practiced },
    { name: 'Difficult', value: data.difficult, color: CLASSIFICATION_COLORS.difficult },
    { name: 'Almost Learned', value: data.almost_learned, color: CLASSIFICATION_COLORS.almost_learned },
    { name: 'Learned', value: data.learned, color: CLASSIFICATION_COLORS.learned },
  ].filter(d => d.value > 0)

  return (
    <ResponsiveContainer width="100%" height={200}>
      <PieChart>
        <Pie data={pieData} dataKey="value" innerRadius={50} outerRadius={80} nameKey="name">
          {pieData.map((entry) => (
            <Cell key={entry.name} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  )
}

export function ModePerformanceChart({ data }: { data: ModePerformanceItem[] }) {
  if (data.length === 0) return <EmptyState message="No data available yet" />
  const chartData = data.map(d => ({ ...d, accuracy_pct: Math.round(d.accuracy * 100) }))
  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="mode" tick={{ fontSize: 11 }} />
        <YAxis domain={[0, 100]} tickFormatter={(v) => `${v}%`} tick={{ fontSize: 11 }} />
        <Tooltip formatter={(v: number) => `${v}%`} />
        <Bar dataKey="accuracy_pct" fill={MODE_COLOR} name="Accuracy" />
      </BarChart>
    </ResponsiveContainer>
  )
}
