'use client'

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

interface Props {
  data: Array<{ dimension: string; count: number }>
}

export function TopGapsChart({ data }: Props) {
  if (!data.length) {
    return <p className="text-[13px] text-text-placeholder py-8 text-center">No gaps recorded</p>
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} layout="vertical">
        <CartesianGrid strokeDasharray="3 3" stroke="#E5E5E5" />
        <XAxis type="number" tick={{ fontSize: 11, fill: '#999999' }} />
        <YAxis
          type="category"
          dataKey="dimension"
          tick={{ fontSize: 11, fill: '#666666' }}
          width={120}
        />
        <Tooltip
          contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #E5E5E5' }}
        />
        <Bar dataKey="count" fill="#0A1E2F" radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}
