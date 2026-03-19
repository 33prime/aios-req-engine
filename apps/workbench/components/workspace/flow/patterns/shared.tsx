'use client'

import type { FieldInfo, PatternRendererProps } from './types'

export function KpiCards({ fields, limit = 5 }: { fields: FieldInfo[]; limit?: number }) {
  const displayed = fields.filter(f => f.type === 'displayed' || f.type === 'computed').slice(0, limit)
  if (displayed.length === 0) return null
  const colors = ['#3FAF7A', '#0A1E2F', '#D4A017', '#3FAF7A', '#044159']
  return (
    <div className="grid gap-2 mb-3.5" style={{ gridTemplateColumns: `repeat(auto-fit, minmax(110px, 1fr))` }}>
      {displayed.map((f, i) => (
        <div key={i} className="rounded-[7px] p-2.5" style={{ background: '#EDF2F7', border: '1px solid #E2E8F0' }}>
          <div className="text-[20px] font-extrabold leading-none mb-[1px]" style={{ color: colors[i % colors.length] }}>
            {f.mock_value}
          </div>
          <div className="text-[7px] uppercase tracking-wide font-medium" style={{ color: '#718096' }}>
            {f.name}
          </div>
        </div>
      ))}
    </div>
  )
}

export function ChartBars() {
  const heights = [65, 72, 58, 82, 91, 78, 85, 94, 88, 92, 97, 89]
  return (
    <div className="rounded-[7px] p-3 mb-2.5" style={{ background: '#EDF2F7', border: '1px solid #E2E8F0' }}>
      <div className="text-[9px] font-semibold mb-2" style={{ color: '#4A5568' }}>Trend — 12 Periods</div>
      <div className="flex items-end gap-[3px]" style={{ height: 70 }}>
        {heights.map((h, i) => (
          <div
            key={i}
            className="flex-1 rounded-t-sm"
            style={{ height: `${h}%`, background: 'linear-gradient(180deg, #3FAF7A, rgba(63,175,122,0.3))' }}
          />
        ))}
      </div>
    </div>
  )
}

export function AlertBox({ title, desc, variant = 'info' }: { title: string; desc: string; variant?: 'info' | 'warning' }) {
  const isWarning = variant === 'warning'
  return (
    <div
      className="rounded-[7px] px-3 py-2 flex items-center gap-2 mb-2.5"
      style={{
        background: isWarning ? 'rgba(212,160,23,0.06)' : 'rgba(63,175,122,0.04)',
        border: `1px solid ${isWarning ? 'rgba(212,160,23,0.15)' : 'rgba(63,175,122,0.12)'}`,
      }}
    >
      <div
        className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold flex-shrink-0"
        style={{
          background: isWarning ? 'rgba(212,160,23,0.08)' : 'rgba(63,175,122,0.08)',
          color: isWarning ? '#8B6914' : '#2A8F5F',
        }}
      >
        {isWarning ? '\u26A0' : '\u2713'}
      </div>
      <div className="flex-1">
        <div className="text-[10px] font-semibold" style={{ color: '#0A1E2F' }}>{title}</div>
        <div className="text-[9px] leading-snug" style={{ color: '#4A5568' }}>{desc}</div>
      </div>
      <div
        className="text-[9px] font-semibold flex-shrink-0 px-2 py-[3px] rounded"
        style={{ background: 'rgba(63,175,122,0.08)', color: '#2A8F5F', cursor: 'pointer' }}
      >
        Review &rarr;
      </div>
    </div>
  )
}

export function FallbackPattern({ fields }: { fields: FieldInfo[] }) {
  return (
    <div className="grid grid-cols-2 gap-2">
      {fields.map((f, i) => (
        <div key={i} className="flex items-center gap-1.5 px-2.5 py-2 rounded-lg text-[10px]" style={{ background: '#EDF2F7' }}>
          <span
            className="w-[5px] h-[5px] rounded-full flex-shrink-0"
            style={{
              background: f.confidence === 'known' ? '#3FAF7A'
                : f.confidence === 'inferred' ? '#044159'
                : '#BBBBBB',
            }}
          />
          <span className="font-medium" style={{ color: '#2D3748' }}>{f.name}</span>
          <span className="ml-auto text-[9px]" style={{ color: '#718096' }}>{f.mock_value}</span>
        </div>
      ))}
    </div>
  )
}

export function NavItem({ label, active }: { label: string; active?: boolean }) {
  return (
    <div
      className="px-2 py-[3px] rounded text-[9px] font-medium"
      style={{
        background: active ? 'rgba(63,175,122,0.08)' : 'transparent',
        color: active ? '#2A8F5F' : '#718096',
        fontWeight: active ? 600 : 500,
      }}
    >
      {label}
    </div>
  )
}
