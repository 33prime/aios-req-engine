'use client'

import type { PatternRendererProps } from './types'

export function FormPattern({ fields }: PatternRendererProps) {
  const formFields = fields.slice(0, 5)
  return (
    <div style={{ maxWidth: 440 }}>
      {formFields.map((f, i) => (
        <div key={i} className="mb-2.5">
          <div className="text-[9px] font-medium mb-[2px]" style={{ color: '#4A5568' }}>{f.name}</div>
          <div
            className="w-full px-2.5 py-[7px] rounded-[5px] text-[10px]"
            style={{
              border: '1px solid #E2E8F0',
              background: f.mock_value ? '#EDF2F7' : '#fff',
              color: '#2D3748',
            }}
          >
            {f.mock_value || '\u2014'}
          </div>
          {f.confidence === 'guess' && (
            <div className="text-[8px] mt-[1px]" style={{ color: '#A0AEC0' }}>Estimated &mdash; needs confirmation</div>
          )}
        </div>
      ))}
      <div className="flex gap-1.5 mt-3">
        <button className="px-3.5 py-[7px] rounded-[5px] text-[10px] font-semibold text-white" style={{ background: '#3FAF7A' }}>Save</button>
        <button className="px-3.5 py-[7px] rounded-[5px] text-[10px] font-semibold" style={{ background: '#EDF2F7', color: '#4A5568', border: '1px solid #E2E8F0' }}>Cancel</button>
      </div>

      <div className="mt-2.5 p-3.5 rounded-[7px]" style={{ background: '#EDF2F7', border: '1px solid #E2E8F0' }}>
        <div className="text-[10px] font-semibold mb-1.5" style={{ color: '#0A1E2F' }}>Preview</div>
        {formFields.slice(0, 4).map((f, i) => (
          <div key={i} className="flex justify-between text-[9px] py-[2px]" style={{ borderBottom: '1px solid rgba(0,0,0,0.03)' }}>
            <span style={{ color: '#4A5568' }}>{f.name}</span>
            <span className="font-medium" style={{ color: '#0A1E2F' }}>{f.mock_value}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
