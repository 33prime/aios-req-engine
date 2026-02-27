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
    <div className="bg-white rounded-2xl shadow-md border border-border p-6">
      <div className="flex items-start justify-between">
        <div className="p-2.5 rounded-xl bg-brand-primary-light">
          <Icon className="w-5 h-5 text-brand-primary" />
        </div>
        {trend && (
          <span className="text-[11px] text-brand-primary font-medium">{trend}</span>
        )}
      </div>
      <div className="mt-4">
        <div className="text-[28px] font-bold text-text-body">{value}</div>
        <div className="text-[12px] text-text-placeholder uppercase tracking-wide mt-1">{label}</div>
      </div>
    </div>
  )
}
