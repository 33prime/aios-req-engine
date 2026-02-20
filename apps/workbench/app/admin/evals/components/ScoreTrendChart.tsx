'use client'

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

const COLORS = { score: '#3FAF7A' }

interface Props {
  data: Array<{ date: string; score: number }>
}

export function ScoreTrendChart({ data }: Props) {
  if (!data.length) {
    return <p className="text-[13px] text-[#999999] py-8 text-center">No eval data yet</p>
  }

  const formatted = data.map((d) => ({
    ...d,
    score: +(d.score * 100).toFixed(1),
    label: d.date.slice(5), // MM-DD
  }))

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={formatted}>
        <CartesianGrid strokeDasharray="3 3" stroke="#E5E5E5" />
        <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#999999' }} />
        <YAxis
          domain={[0, 100]}
          tick={{ fontSize: 11, fill: '#999999' }}
          tickFormatter={(v) => `${v}%`}
        />
        <Tooltip
          contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #E5E5E5' }}
          formatter={(v) => [`${v}%`, 'Score']}
        />
        <Line
          type="monotone"
          dataKey="score"
          stroke={COLORS.score}
          strokeWidth={2}
          dot={{ r: 3, fill: COLORS.score }}
          activeDot={{ r: 5 }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
