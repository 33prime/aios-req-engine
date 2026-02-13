'use client'

import { memo } from 'react'
import { Handle, Position, type NodeProps } from '@xyflow/react'
import { Database } from 'lucide-react'

export interface ERDEntityNodeData extends Record<string, unknown> {
  name: string
  entity_category: 'domain' | 'reference' | 'transactional' | 'system'
  fields: { name: string; type?: string; required?: boolean }[]
  field_count: number
  workflow_step_count: number
}

const CATEGORY_BORDER: Record<string, string> = {
  domain: 'border-l-[#3FAF7A]',
  reference: 'border-l-[#0A1E2F]',
  transactional: 'border-l-[#666666]',
  system: 'border-l-[#999999]',
}

const CATEGORY_LABEL: Record<string, string> = {
  domain: 'Domain',
  reference: 'Reference',
  transactional: 'Transactional',
  system: 'System',
}

function ERDEntityNodeComponent({ data }: NodeProps) {
  const nodeData = data as unknown as ERDEntityNodeData
  const borderClass = CATEGORY_BORDER[nodeData.entity_category] || CATEGORY_BORDER.domain
  const categoryLabel = CATEGORY_LABEL[nodeData.entity_category] || nodeData.entity_category

  const displayFields = nodeData.fields.slice(0, 5)
  const extraCount = nodeData.field_count - displayFields.length

  return (
    <>
      <Handle type="target" position={Position.Left} className="!w-2 !h-2 !bg-[#E5E5E5] !border-[#999999]" />
      <Handle type="source" position={Position.Right} className="!w-2 !h-2 !bg-[#E5E5E5] !border-[#999999]" />
      <Handle type="target" position={Position.Top} className="!w-2 !h-2 !bg-[#E5E5E5] !border-[#999999]" />
      <Handle type="source" position={Position.Bottom} className="!w-2 !h-2 !bg-[#E5E5E5] !border-[#999999]" />

      <div className={`bg-white rounded-xl border border-[#E5E5E5] shadow-sm w-[200px] border-l-4 ${borderClass} overflow-hidden`}>
        {/* Header */}
        <div className="px-3 py-2 border-b border-[#E5E5E5]">
          <div className="flex items-center gap-1.5">
            <Database className="w-3 h-3 text-[#999999]" />
            <span className="text-[13px] font-semibold text-[#333333] truncate">{nodeData.name}</span>
          </div>
          <span className="text-[10px] text-[#999999] font-medium">{categoryLabel}</span>
        </div>

        {/* Fields */}
        {displayFields.length > 0 && (
          <div className="px-3 py-1.5">
            {displayFields.map((field, i) => (
              <div key={i} className="flex items-center gap-1 py-0.5">
                <span className="text-[11px] text-[#333333] truncate">{field.name}</span>
                {field.type && (
                  <span className="text-[10px] text-[#999999]">: {field.type}</span>
                )}
                {field.required && (
                  <span className="text-[10px] text-[#3FAF7A]">*</span>
                )}
              </div>
            ))}
            {extraCount > 0 && (
              <span className="text-[10px] text-[#999999] italic">+{extraCount} more fields</span>
            )}
          </div>
        )}

        {/* Footer */}
        {nodeData.workflow_step_count > 0 && (
          <div className="px-3 py-1 border-t border-[#E5E5E5]">
            <span className="text-[10px] text-[#999999]">
              {nodeData.workflow_step_count} workflow {nodeData.workflow_step_count === 1 ? 'link' : 'links'}
            </span>
          </div>
        )}
      </div>
    </>
  )
}

export const ERDEntityNode = memo(ERDEntityNodeComponent)
