'use client'

import { DrawerShell } from '@/components/ui/DrawerShell'
import { ProgressRing } from '@/components/ui/ProgressRing'
import { StationChat } from './StationChat'
import type { StationSlug } from '@/types/portal'

interface StationPanelProps {
  onClose: () => void
  icon: React.ComponentType<{ className?: string }>
  title: string
  entityLabel?: string
  progress?: number
  station: StationSlug
  projectId: string
  chatGreeting?: string
  width?: number
  onDataChanged?: () => void
  children?: React.ReactNode
}

export function StationPanel({
  onClose,
  icon,
  title,
  entityLabel,
  progress,
  station,
  projectId,
  chatGreeting,
  width = 480,
  onDataChanged,
  children,
}: StationPanelProps) {
  const handleToolResult = (toolName: string, result: Record<string, unknown>) => {
    if (result?.success) onDataChanged?.()
  }

  return (
    <DrawerShell
      onClose={onClose}
      icon={icon}
      title={title}
      entityLabel={entityLabel}
      width={width}
      headerRight={
        progress != null ? (
          <ProgressRing value={progress} size={32} strokeWidth={3} showLabel />
        ) : undefined
      }
      bodyClassName="flex-1 flex flex-col min-h-0 px-0 py-0"
    >
      {/* Structured content zone — scrollable upper portion */}
      {children && (
        <div className="overflow-y-auto max-h-[45%] px-5 py-4 border-b border-border">
          {children}
        </div>
      )}

      {/* Chat zone — fills remaining space */}
      <StationChat
        projectId={projectId}
        station={station}
        greeting={chatGreeting}
        onToolResult={handleToolResult}
      />
    </DrawerShell>
  )
}
