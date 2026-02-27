'use client'

import { useState } from 'react'
import { Building2, Pencil, Save, X, Loader } from 'lucide-react'
import { updateOrganization } from '@/lib/api'
import type { Organization, OrganizationRole } from '@/types/api'

interface OrganizationDetailsCardProps {
  organization: Organization
  userRole: OrganizationRole
  onUpdate?: (org: Organization) => void
}

export default function OrganizationDetailsCard({
  organization,
  userRole,
  onUpdate,
}: OrganizationDetailsCardProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [name, setName] = useState(organization.name)
  const [slug, setSlug] = useState(organization.slug || '')

  const canEdit = userRole === 'Owner' || userRole === 'Admin'

  const handleSave = async () => {
    if (!name.trim()) return

    setIsSaving(true)
    try {
      const updated = await updateOrganization(organization.id, {
        name: name.trim(),
        slug: slug.trim() || undefined,
      })
      onUpdate?.(updated)
      setIsEditing(false)
    } catch (error) {
      console.error('Failed to update organization:', error)
    } finally {
      setIsSaving(false)
    }
  }

  const handleCancel = () => {
    setName(organization.name)
    setSlug(organization.slug || '')
    setIsEditing(false)
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    })
  }

  return (
    <div className="rounded-xl border border-zinc-200 bg-white shadow-sm p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-4">
          <div className="p-1.5 rounded-full bg-emerald-600/10 text-emerald-600">
            <Building2 className="w-4 h-4" />
          </div>
          <p className="text-[13px] text-zinc-800" style={{ fontWeight: '600' }}>
            Organization Details
          </p>
        </div>
        {canEdit && !isEditing && (
          <button
            onClick={() => setIsEditing(true)}
            className="p-1.5 hover:bg-zinc-100 rounded-lg transition-colors text-zinc-500 hover:text-zinc-700"
          >
            <Pencil className="w-4 h-4" />
          </button>
        )}
        {isEditing && (
          <div className="flex items-center gap-2">
            <button
              onClick={handleCancel}
              disabled={isSaving}
              className="p-1.5 hover:bg-zinc-100 rounded-lg transition-colors text-zinc-500 hover:text-zinc-700"
            >
              <X className="w-4 h-4" />
            </button>
            <button
              onClick={handleSave}
              disabled={isSaving || !name.trim()}
              className="p-1.5 hover:bg-emerald-100 rounded-lg transition-colors text-emerald-600 disabled:opacity-50"
            >
              {isSaving ? (
                <Loader className="w-4 h-4 animate-spin" />
              ) : (
                <Save className="w-4 h-4" />
              )}
            </button>
          </div>
        )}
      </div>

      {isEditing ? (
        <div className="space-y-4">
          <div>
            <label className="text-[12px] text-zinc-600 block mb-1">
              Organization Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full text-[13px] text-zinc-700 border border-zinc-300 rounded-md px-3 py-2 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              placeholder="Enter organization name"
            />
          </div>
          <div>
            <label className="text-[12px] text-zinc-600 block mb-1">
              Slug (URL-friendly name)
            </label>
            <input
              type="text"
              value={slug}
              onChange={(e) => setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '-'))}
              className="w-full text-[13px] text-zinc-700 border border-zinc-300 rounded-md px-3 py-2 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              placeholder="my-organization"
            />
            <p className="text-[11px] text-zinc-500 mt-1">
              Used in URLs. Leave blank to auto-generate.
            </p>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-[11px] text-zinc-500 mb-1">Name</p>
              <p className="text-[13px] text-zinc-800 font-medium">{organization.name}</p>
            </div>
            <div>
              <p className="text-[11px] text-zinc-500 mb-1">Slug</p>
              <p className="text-[13px] text-zinc-700">{organization.slug || '—'}</p>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-[11px] text-zinc-500 mb-1">Created</p>
              <p className="text-[13px] text-zinc-700">{formatDate(organization.created_at)}</p>
            </div>
            <div>
              <p className="text-[11px] text-zinc-500 mb-1">Your Role</p>
              <span className={`inline-flex px-2 py-0.5 rounded-full text-[11px] font-medium ${
                userRole === 'Owner'
                  ? 'bg-emerald-100 text-emerald-700'
                  : userRole === 'Admin'
                  ? 'bg-blue-100 text-brand-primary-hover'
                  : 'bg-zinc-100 text-zinc-700'
              }`}>
                {userRole}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
