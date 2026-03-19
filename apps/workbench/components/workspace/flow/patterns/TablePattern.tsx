'use client'

import type { PatternRendererProps } from './types'
import { KpiCards } from './shared'

export function TablePattern({ fields }: PatternRendererProps) {
  const cols = fields.slice(0, 5)
  return (
    <>
      <KpiCards fields={fields} limit={3} />
      <div className="rounded-[7px] overflow-hidden mb-2.5" style={{ border: '1px solid #E2E8F0' }}>
        <table className="w-full" style={{ borderCollapse: 'separate', borderSpacing: 0 }}>
          <thead>
            <tr>
              {cols.map((f, i) => (
                <th
                  key={i}
                  className="text-left text-[8px] font-semibold uppercase tracking-wide px-2.5 py-1.5"
                  style={{ color: '#718096', background: '#EDF2F7', borderBottom: '1px solid #E2E8F0' }}
                >
                  {f.name}
                </th>
              ))}
              <th
                className="text-left text-[8px] font-semibold uppercase tracking-wide px-2.5 py-1.5"
                style={{ color: '#718096', background: '#EDF2F7', borderBottom: '1px solid #E2E8F0' }}
              >
                Status
              </th>
            </tr>
          </thead>
          <tbody>
            {[0, 1, 2, 3].map(row => (
              <tr key={row}>
                {cols.map((f, ci) => (
                  <td key={ci} className="text-[10px] px-2.5 py-1.5" style={{ color: '#2D3748', borderBottom: '1px solid rgba(0,0,0,0.03)' }}>
                    {f.mock_value || `Item ${row + 1}`}
                  </td>
                ))}
                <td className="px-2.5 py-1.5" style={{ borderBottom: '1px solid rgba(0,0,0,0.03)' }}>
                  <span
                    className="text-[7px] font-semibold uppercase px-[5px] py-[2px] rounded"
                    style={{
                      background: row < 3 ? 'rgba(63,175,122,0.08)' : 'rgba(212,160,23,0.08)',
                      color: row < 3 ? '#2A8F5F' : '#8B6914',
                    }}
                  >
                    {row < 3 ? 'Matched' : 'Review'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex gap-1.5">
        <button className="px-3.5 py-1.5 rounded-[5px] text-[10px] font-semibold text-white" style={{ background: '#3FAF7A' }}>Confirm All</button>
        <button className="px-3.5 py-1.5 rounded-[5px] text-[10px] font-semibold" style={{ background: '#EDF2F7', color: '#4A5568', border: '1px solid #E2E8F0' }}>Export</button>
      </div>
    </>
  )
}
