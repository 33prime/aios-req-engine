'use client'

import type { PortalDashboard } from '@/types/portal'

interface ActivityTimelineProps {
  activities: PortalDashboard['recent_activity']
}

function groupByDay(activities: ActivityTimelineProps['activities']) {
  const groups: Record<string, typeof activities> = {}
  for (const a of activities) {
    const day = new Date(a.created_at).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    })
    if (!groups[day]) groups[day] = []
    groups[day].push(a)
  }
  return groups
}

const VERDICT_COLORS: Record<string, string> = {
  confirmed: 'bg-green-500',
  refine: 'bg-amber-500',
  flag: 'bg-red-500',
}

export function ActivityTimeline({ activities }: ActivityTimelineProps) {
  if (!activities || activities.length === 0) return null

  const grouped = groupByDay(activities.slice(0, 12))

  return (
    <div className="bg-surface-card border border-border rounded-lg p-4">
      <h3 className="text-xs font-medium text-text-muted uppercase tracking-wide mb-3">
        Recent Activity
      </h3>
      <div className="space-y-4">
        {Object.entries(grouped).map(([day, items]) => (
          <div key={day}>
            <p className="text-[10px] text-text-placeholder font-medium mb-1.5">{day}</p>
            <div className="space-y-2">
              {items.map((activity) => (
                <div key={activity.id} className="flex items-start gap-2 text-xs">
                  <span
                    className={`mt-1 w-2 h-2 rounded-full flex-shrink-0 ${
                      VERDICT_COLORS[activity.verdict] || 'bg-gray-300'
                    }`}
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-text-secondary">
                      <span className="font-medium text-text-primary">
                        {activity.stakeholders?.name || 'Stakeholder'}
                      </span>{' '}
                      {activity.verdict}{' '}
                      <span className="text-text-muted">
                        {activity.entity_type.replace('_', ' ')}
                      </span>
                    </p>
                    {activity.notes && (
                      <p className="text-text-placeholder truncate">{activity.notes}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
