'use client'

import type { LucideIcon } from 'lucide-react'

interface MetricCardProps {
  icon: LucideIcon
  value: string | number
  label: string
  trend?: string
}

export function MetricCard({ icon: Icon, value, label, trend }: MetricCardProps) {
  return (
    <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] p-6">
      <div className="flex items-start justify-between">
        <div className="p-2.5 rounded-xl bg-[#3FAF7A]/10">
          <Icon className="w-5 h-5 text-[#3FAF7A]" />
        </div>
        {trend && (
          <span className="text-[11px] text-[#3FAF7A] font-medium">{trend}</span>
        )}
      </div>
      <div className="mt-4">
        <div className="text-[28px] font-bold text-[#333333]">{value}</div>
        <div className="text-[12px] text-[#999999] uppercase tracking-wide mt-1">{label}</div>
      </div>
    </div>
  )
}
