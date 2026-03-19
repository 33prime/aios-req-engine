'use client'

import type { PatternRendererProps } from './types'

export function WizardPattern({ fields, step }: PatternRendererProps) {
  const wizardSteps = ['Import', 'Map', 'Configure', 'Confirm']
  const capturedFields = fields.filter(f => f.type === 'captured' || f.type === 'displayed').slice(0, 4)
  return (
    <>
      <div className="flex items-center justify-center gap-0 px-5 pb-4 mb-3.5" style={{ borderBottom: '1px solid #E2E8F0' }}>
        {wizardSteps.map((ws, i) => (
          <div key={i} className="flex items-center">
            {i > 0 && (
              <div className="w-10 h-[2px] -mt-4" style={{ background: i <= 1 ? '#3FAF7A' : '#E2E8F0' }} />
            )}
            <div className="flex flex-col items-center gap-[3px]">
              <div
                className="w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold"
                style={{
                  background: i < 1 ? '#3FAF7A' : i === 1 ? '#3FAF7A' : '#EDF2F7',
                  color: i <= 1 ? '#fff' : '#A0AEC0',
                  border: i > 1 ? '2px solid #E2E8F0' : 'none',
                  boxShadow: i === 1 ? '0 0 0 3px rgba(63,175,122,0.18)' : 'none',
                }}
              >
                {i < 1 ? '\u2713' : i + 1}
              </div>
              <span className="text-[8px] font-medium whitespace-nowrap" style={{ color: '#718096' }}>{ws}</span>
            </div>
          </div>
        ))}
      </div>
      <div style={{ maxWidth: 400 }}>
        {capturedFields.map((f, i) => (
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
          </div>
        ))}
        <div className="flex gap-1.5 mt-3">
          <button className="px-3.5 py-[7px] rounded-[5px] text-[10px] font-semibold text-white" style={{ background: '#3FAF7A' }}>Continue</button>
          <button className="px-3.5 py-[7px] rounded-[5px] text-[10px] font-semibold" style={{ background: '#EDF2F7', color: '#4A5568', border: '1px solid #E2E8F0' }}>Save Draft</button>
        </div>
      </div>
    </>
  )
}
