'use client'

import { useState } from 'react'
import {
  User,
  Mail,
  Phone,
  Building,
  Star,
  ChevronDown,
  ChevronUp,
  MessageSquare,
  Sparkles,
} from 'lucide-react'

interface Stakeholder {
  id: string
  name: string
  role?: string
  email?: string
  phone?: string
  organization?: string
  stakeholder_type?: string
  influence_level?: string
  domain_expertise?: string[]
  topic_mentions?: Record<string, number>
  is_primary_contact?: boolean
  source_type?: string
  confirmation_status?: string
}

interface StakeholderCardProps {
  stakeholder: Stakeholder
  onSetPrimary?: (id: string) => void
  onEdit?: (stakeholder: Stakeholder) => void
  onDelete?: (id: string) => void
}

export default function StakeholderCard({
  stakeholder,
  onSetPrimary,
  onEdit,
  onDelete,
}: StakeholderCardProps) {
  const [expanded, setExpanded] = useState(false)

  const getInfluenceBadgeColor = (level?: string) => {
    switch (level) {
      case 'high':
        return 'bg-red-100 text-red-700'
      case 'medium':
        return 'bg-yellow-100 text-yellow-700'
      case 'low':
        return 'bg-gray-100 text-gray-600'
      default:
        return 'bg-gray-100 text-gray-600'
    }
  }

  const getTypeBadgeColor = (type?: string) => {
    switch (type) {
      case 'champion':
        return 'bg-green-100 text-green-700'
      case 'sponsor':
        return 'bg-blue-100 text-blue-700'
      case 'blocker':
        return 'bg-red-100 text-red-700'
      case 'influencer':
        return 'bg-purple-100 text-purple-700'
      case 'end_user':
        return 'bg-gray-100 text-gray-600'
      default:
        return 'bg-gray-100 text-gray-600'
    }
  }

  const getSourceBadge = (sourceType?: string) => {
    switch (sourceType) {
      case 'direct_participant':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-green-50 text-green-700">
            <MessageSquare className="w-3 h-3 mr-1" />
            Direct
          </span>
        )
      case 'mentioned':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-gray-50 text-gray-600">
            Mentioned
          </span>
        )
      case 'manual':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-blue-50 text-blue-700">
            Manual
          </span>
        )
      default:
        return null
    }
  }

  // Get top topics by mention count
  const topTopics = stakeholder.topic_mentions
    ? Object.entries(stakeholder.topic_mentions)
        .sort(([, a], [, b]) => b - a)
        .slice(0, 5)
    : []

  return (
    <div className="border border-gray-200 rounded-lg bg-white hover:border-gray-300 transition-colors">
      <div className="p-4">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            {/* Avatar */}
            <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
              stakeholder.is_primary_contact ? 'bg-blue-100' : 'bg-gray-100'
            }`}>
              <User className={`w-5 h-5 ${
                stakeholder.is_primary_contact ? 'text-blue-600' : 'text-gray-500'
              }`} />
            </div>

            {/* Name and role */}
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-medium text-gray-900">{stakeholder.name}</h3>
                {stakeholder.is_primary_contact && (
                  <Star className="w-4 h-4 text-yellow-500 fill-yellow-500" />
                )}
              </div>
              {stakeholder.role && (
                <p className="text-sm text-gray-500">{stakeholder.role}</p>
              )}
            </div>
          </div>

          {/* Expand button */}
          <button
            onClick={() => setExpanded(!expanded)}
            className="p-1 text-gray-400 hover:text-gray-600"
          >
            {expanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
          </button>
        </div>

        {/* Badges */}
        <div className="flex flex-wrap items-center gap-2 mt-3">
          {stakeholder.stakeholder_type && (
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${getTypeBadgeColor(stakeholder.stakeholder_type)}`}>
              {stakeholder.stakeholder_type.replace('_', ' ')}
            </span>
          )}
          {stakeholder.influence_level && (
            <span className={`px-2 py-0.5 rounded text-xs ${getInfluenceBadgeColor(stakeholder.influence_level)}`}>
              {stakeholder.influence_level} influence
            </span>
          )}
          {getSourceBadge(stakeholder.source_type)}
        </div>

        {/* Domain expertise tags */}
        {stakeholder.domain_expertise && stakeholder.domain_expertise.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-3">
            {stakeholder.domain_expertise.map((expertise) => (
              <span
                key={expertise}
                className="inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-indigo-50 text-indigo-700"
              >
                <Sparkles className="w-3 h-3 mr-1" />
                {expertise}
              </span>
            ))}
          </div>
        )}

        {/* Expanded content */}
        {expanded && (
          <div className="mt-4 pt-4 border-t border-gray-100 space-y-3">
            {/* Contact info */}
            <div className="space-y-2">
              {stakeholder.email && (
                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <Mail className="w-4 h-4 text-gray-400" />
                  <a href={`mailto:${stakeholder.email}`} className="hover:text-blue-600">
                    {stakeholder.email}
                  </a>
                </div>
              )}
              {stakeholder.phone && (
                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <Phone className="w-4 h-4 text-gray-400" />
                  {stakeholder.phone}
                </div>
              )}
              {stakeholder.organization && (
                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <Building className="w-4 h-4 text-gray-400" />
                  {stakeholder.organization}
                </div>
              )}
            </div>

            {/* Topic mentions */}
            {topTopics.length > 0 && (
              <div>
                <p className="text-xs font-medium text-gray-500 mb-2">Topics Discussed</p>
                <div className="flex flex-wrap gap-2">
                  {topTopics.map(([topic, count]) => (
                    <span
                      key={topic}
                      className="inline-flex items-center px-2 py-1 rounded text-xs bg-gray-100 text-gray-700"
                    >
                      {topic}
                      <span className="ml-1 text-gray-400">({count})</span>
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex items-center gap-2 pt-2">
              {!stakeholder.is_primary_contact && onSetPrimary && (
                <button
                  onClick={() => onSetPrimary(stakeholder.id)}
                  className="text-xs text-blue-600 hover:text-blue-800"
                >
                  Set as Primary
                </button>
              )}
              {onEdit && (
                <button
                  onClick={() => onEdit(stakeholder)}
                  className="text-xs text-gray-600 hover:text-gray-800"
                >
                  Edit
                </button>
              )}
              {onDelete && (
                <button
                  onClick={() => onDelete(stakeholder.id)}
                  className="text-xs text-red-600 hover:text-red-800"
                >
                  Delete
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
