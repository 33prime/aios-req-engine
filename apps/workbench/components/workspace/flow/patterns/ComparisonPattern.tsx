'use client'

import type { PatternRendererProps } from './types'

export function ComparisonPattern({ fields }: PatternRendererProps) {
  const rows = fields.slice(0, 6)
  return (
    <div className="rounded-[7px] overflow-hidden" style={{ border: '1px solid #E2E8F0' }}>
      {/* Header */}
      <div className="grid grid-cols-3 text-[8px] font-semibold uppercase tracking-wide" style={{ background: '#EDF2F7' }}>
        <div className="px-3 py-2" style={{ color: '#718096' }}>Criteria</div>
        <div className="px-3 py-2 text-center" style={{ color: '#044159', borderLeft: '1px solid #E2E8F0' }}>Option A</div>
        <div className="px-3 py-2 text-center" style={{ color: '#3FAF7A', borderLeft: '1px solid #E2E8F0' }}>Option B</div>
      </div>
      {/* Rows */}
      {rows.map((f, i) => (
        <div key={i} className="grid grid-cols-3" style={{ borderTop: '1px solid rgba(0,0,0,0.04)' }}>
          <div className="px-3 py-2 text-[9px] font-medium" style={{ color: '#0A1E2F' }}>{f.name}</div>
          <div className="px-3 py-2 text-[9px] text-center" style={{ color: '#4A5568', borderLeft: '1px solid rgba(0,0,0,0.04)' }}>
            {f.mock_value}
          </div>
          <div className="px-3 py-2 text-[9px] text-center" style={{ color: '#4A5568', borderLeft: '1px solid rgba(0,0,0,0.04)' }}>
            {/* Vary the comparison value slightly */}
            {f.confidence === 'known' ? (
              <span style={{ color: '#2A8F5F', fontWeight: 600 }}>{f.mock_value} +</span>
            ) : (
              f.mock_value
            )}
          </div>
        </div>
      ))}
      {/* Footer */}
      <div className="flex gap-1.5 p-2.5" style={{ borderTop: '1px solid #E2E8F0', background: '#EDF2F7' }}>
        <button className="px-3 py-1 rounded-[5px] text-[9px] font-semibold text-white" style={{ background: '#3FAF7A' }}>Select Winner</button>
        <button className="px-3 py-1 rounded-[5px] text-[9px] font-semibold" style={{ background: '#fff', color: '#4A5568', border: '1px solid #E2E8F0' }}>Add Criteria</button>
      </div>
    </div>
  )
}
