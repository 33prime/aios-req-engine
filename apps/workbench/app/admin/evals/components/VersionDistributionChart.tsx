'use client'

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts'

const ACTION_COLORS: Record<string, string> = {
  accept: '#3FAF7A',
  retry: '#f59e0b',
  notify: '#ef4444',
  pending: '#999999',
}

interface Props {
  data: Record<string, number>
}

export function VersionDistributionChart({ data }: Props) {
  const entries = Object.entries(data).map(([name, value]) => ({ name, value }))

  if (!entries.length) {
    return <p className="text-[13px] text-[#999999] py-8 text-center">No outcomes yet</p>
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie
          data={entries}
          cx="50%"
          cy="50%"
          innerRadius={50}
          outerRadius={80}
          paddingAngle={3}
          dataKey="value"
          label={({ name, percent }) => `${name} (${((percent ?? 0) * 100).toFixed(0)}%)`}
          labelLine={false}
        >
          {entries.map((entry) => (
            <Cell key={entry.name} fill={ACTION_COLORS[entry.name] || '#999999'} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #E5E5E5' }}
        />
        <Legend
          iconSize={8}
          wrapperStyle={{ fontSize: 12 }}
        />
      </PieChart>
    </ResponsiveContainer>
  )
}
