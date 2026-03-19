'use client'

import type { SolutionFlowStepDetail, PersonaSummary } from '@/types/workspace'
import { PATTERN_LABELS } from '@/lib/solution-flow-constants'
import { X } from 'lucide-react'

interface FlowPreviewModalProps {
  step: { title: string; actors: string[] }
  detail: SolutionFlowStepDetail
  isOpen: boolean
  onClose: () => void
  personas: PersonaSummary[]
}

function getPersonaColor(name: string): string {
  const palette = ['#3FAF7A', '#044159', '#2D6B4A', '#0A1E2F']
  let hash = 0
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash)
  return palette[Math.abs(hash) % palette.length]
}

function getInitials(name: string): string {
  return name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
}

export function FlowPreviewModal({ step, detail, isOpen, onClose, personas }: FlowPreviewModalProps) {
  if (!isOpen) return null

  const actor = step.actors[0] || 'User'
  const color = getPersonaColor(actor)
  const initials = getInitials(actor)
  const pattern = detail.implied_pattern || 'dashboard'
  const fields = detail.information_fields || []

  return (
    <div
      className="fixed top-0 left-0 bottom-0 z-[190] flex items-stretch"
      style={{ right: 480, background: 'rgba(10,30,47,0.4)' }}
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="flex-1 flex items-center justify-center p-6">
        <div
          className="bg-white rounded-xl w-full flex flex-col overflow-hidden"
          style={{
            maxWidth: 800,
            maxHeight: '92vh',
            boxShadow: '0 20px 60px rgba(10,30,47,0.25)',
            animation: 'previewIn 0.3s ease',
          }}
        >
          {/* Browser chrome */}
          <div
            className="flex items-center px-3.5 py-2 flex-shrink-0 gap-2"
            style={{ background: 'linear-gradient(180deg, #FAFAFA 0%, #F0F0F0 100%)', borderBottom: '1px solid #E2E8F0' }}
          >
            <div className="flex gap-1">
              <div className="w-2 h-2 rounded-full" style={{ background: '#FF5F57' }} />
              <div className="w-2 h-2 rounded-full" style={{ background: '#FEBC2E' }} />
              <div className="w-2 h-2 rounded-full" style={{ background: '#28C840' }} />
            </div>
            <div className="flex-1 text-center text-[10px] font-medium" style={{ color: '#718096' }}>
              {step.title}
            </div>
            <button
              onClick={onClose}
              className="w-[22px] h-[22px] rounded-full flex items-center justify-center transition-colors"
              style={{ border: '1px solid #E2E8F0', background: '#fff', color: '#718096' }}
              onMouseEnter={e => { e.currentTarget.style.background = '#EDF2F7'; e.currentTarget.style.color = '#0A1E2F' }}
              onMouseLeave={e => { e.currentTarget.style.background = '#fff'; e.currentTarget.style.color = '#718096' }}
            >
              <X size={10} />
            </button>
          </div>

          {/* App body */}
          <div className="flex-1 overflow-y-auto bg-white">
            {/* App top bar */}
            <div className="flex items-center px-4 py-2" style={{ borderBottom: '1px solid #E2E8F0' }}>
              <div className="text-[11px] font-bold mr-2.5" style={{ color: '#3FAF7A' }}>AppName</div>
              <div className="flex gap-0.5">
                <NavItem label="Dashboard" />
                <NavItem label={step.title.split(' ').slice(0, 2).join(' ')} active />
                <NavItem label="Reports" />
                <NavItem label="Settings" />
              </div>
              <div className="ml-auto flex items-center gap-1.5">
                <span className="text-[9px]" style={{ color: '#718096' }}>{actor}</span>
                <div
                  className="w-5 h-5 rounded-full flex items-center justify-center text-[6px] font-bold text-white"
                  style={{ background: color }}
                >
                  {initials}
                </div>
              </div>
            </div>

            {/* Content */}
            <div className="p-4">
              <div className="text-[15px] font-bold mb-[3px]" style={{ color: '#0A1E2F' }}>
                {step.title}
              </div>
              <div className="text-[10px] mb-3.5" style={{ color: '#718096' }}>
                {PATTERN_LABELS[pattern] || pattern} view
              </div>

              {/* Pattern-specific render */}
              {pattern === 'dashboard' && <DashboardPattern fields={fields} />}
              {pattern === 'table' && <TablePattern fields={fields} />}
              {pattern === 'wizard' && <WizardPattern fields={fields} step={step} />}
              {pattern === 'card' && <CardPattern fields={fields} />}
              {pattern === 'form' && <FormPattern fields={fields} />}
              {!['dashboard', 'table', 'wizard', 'card', 'form'].includes(pattern) && (
                <FallbackPattern fields={fields} />
              )}
            </div>
          </div>
        </div>
      </div>

      <style jsx>{`
        @keyframes previewIn {
          from { opacity: 0; transform: scale(0.96) translateY(10px); }
          to { opacity: 1; transform: scale(1) translateY(0); }
        }
      `}</style>
    </div>
  )
}

function NavItem({ label, active }: { label: string; active?: boolean }) {
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

// ── Pattern Renderers ──────────────────────────

type FieldInfo = { name: string; type: string; mock_value: string; confidence: string }

function KpiCards({ fields, limit = 5 }: { fields: FieldInfo[]; limit?: number }) {
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

function ChartBars() {
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

function AlertBox({ title, desc, variant = 'info' }: { title: string; desc: string; variant?: 'info' | 'warning' }) {
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
        {isWarning ? '⚠' : '✓'}
      </div>
      <div className="flex-1">
        <div className="text-[10px] font-semibold" style={{ color: '#0A1E2F' }}>{title}</div>
        <div className="text-[9px] leading-snug" style={{ color: '#4A5568' }}>{desc}</div>
      </div>
      <div
        className="text-[9px] font-semibold flex-shrink-0 px-2 py-[3px] rounded"
        style={{ background: 'rgba(63,175,122,0.08)', color: '#2A8F5F', cursor: 'pointer' }}
      >
        Review →
      </div>
    </div>
  )
}

function DashboardPattern({ fields }: { fields: FieldInfo[] }) {
  return (
    <>
      <KpiCards fields={fields} />
      <ChartBars />
      <AlertBox title="AI Insight" desc="System detected a pattern in your data" />
    </>
  )
}

function TablePattern({ fields }: { fields: FieldInfo[] }) {
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
                    {ci === 0 ? `Item ${row + 1}` : f.mock_value}
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

function WizardPattern({ fields, step }: { fields: FieldInfo[]; step: { title: string } }) {
  const wizardSteps = ['Import', 'Map', 'Configure', 'Confirm']
  const capturedFields = fields.filter(f => f.type === 'captured' || f.type === 'displayed').slice(0, 4)
  return (
    <>
      {/* Wizard steps */}
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
                {i < 1 ? '✓' : i + 1}
              </div>
              <span className="text-[8px] font-medium whitespace-nowrap" style={{ color: '#718096' }}>{ws}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Form fields */}
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
              {f.mock_value || '—'}
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

function CardPattern({ fields }: { fields: FieldInfo[] }) {
  const items = fields.filter(f => f.type === 'computed' || f.type === 'displayed').slice(0, 4)
  const colors = ['#D4A017', '#3FAF7A', '#D4A017', '#3FAF7A']
  return (
    <>
      <KpiCards fields={fields} limit={3} />
      <div className="grid gap-2 mb-2.5" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(170px, 1fr))' }}>
        {items.map((f, i) => (
          <div key={i} className="rounded-[7px] p-3" style={{ background: '#fff', border: '1px solid #E2E8F0' }}>
            <div className="flex items-center justify-between mb-1.5">
              <div className="text-[10px] font-semibold" style={{ color: '#0A1E2F' }}>{f.name}</div>
              <span
                className="text-[7px] font-semibold uppercase px-[5px] py-[2px] rounded"
                style={{
                  background: i % 2 === 0 ? 'rgba(212,160,23,0.08)' : 'rgba(63,175,122,0.08)',
                  color: i % 2 === 0 ? '#8B6914' : '#2A8F5F',
                }}
              >
                {i % 2 === 0 ? 'Flag' : 'OK'}
              </span>
            </div>
            <div className="text-[18px] font-extrabold mb-[2px]" style={{ color: '#0A1E2F' }}>{f.mock_value}</div>
            <div className="text-[8px] mb-[5px]" style={{ color: '#718096' }}>{f.type}</div>
            <div className="h-[3px] rounded-full overflow-hidden" style={{ background: '#EDF2F7' }}>
              <div className="h-full rounded-full" style={{ width: `${60 + i * 10}%`, background: colors[i % colors.length] }} />
            </div>
            <div className="flex gap-[3px] mt-1.5">
              <span className="text-[8px] font-medium px-[7px] py-[2px] rounded cursor-pointer" style={{ background: 'rgba(63,175,122,0.08)', color: '#2A8F5F' }}>Approve</span>
              <span className="text-[8px] font-medium px-[7px] py-[2px] rounded cursor-pointer" style={{ background: 'rgba(212,160,23,0.08)', color: '#8B6914' }}>Adjust</span>
            </div>
          </div>
        ))}
      </div>
      <div className="flex gap-1.5">
        <button className="px-3.5 py-1.5 rounded-[5px] text-[10px] font-semibold text-white" style={{ background: '#3FAF7A' }}>Approve All</button>
        <button className="px-3.5 py-1.5 rounded-[5px] text-[10px] font-semibold" style={{ background: '#EDF2F7', color: '#4A5568', border: '1px solid #E2E8F0' }}>Generate POs</button>
      </div>
    </>
  )
}

function FormPattern({ fields }: { fields: FieldInfo[] }) {
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
            {f.mock_value || '—'}
          </div>
          {f.confidence === 'guess' && (
            <div className="text-[8px] mt-[1px]" style={{ color: '#A0AEC0' }}>Estimated — needs confirmation</div>
          )}
        </div>
      ))}
      <div className="flex gap-1.5 mt-3">
        <button className="px-3.5 py-[7px] rounded-[5px] text-[10px] font-semibold text-white" style={{ background: '#3FAF7A' }}>Save</button>
        <button className="px-3.5 py-[7px] rounded-[5px] text-[10px] font-semibold" style={{ background: '#EDF2F7', color: '#4A5568', border: '1px solid #E2E8F0' }}>Cancel</button>
      </div>

      {/* Report preview */}
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

function FallbackPattern({ fields }: { fields: FieldInfo[] }) {
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
