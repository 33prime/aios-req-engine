'use client'

import { useEffect, useState, useRef } from 'react'
import { Building2, Check, ChevronDown, Plus, Loader } from 'lucide-react'
import { listOrganizations, setCurrentOrganization, getCurrentOrganization } from '@/lib/api'
import type { OrganizationWithRole } from '@/types/api'

interface OrganizationSwitcherProps {
  onCreateOrg?: () => void
}

export default function OrganizationSwitcher({ onCreateOrg }: OrganizationSwitcherProps) {
  const [organizations, setOrganizations] = useState<OrganizationWithRole[]>([])
  const [currentOrgId, setCurrentOrgId] = useState<string | null>(null)
  const [isOpen, setIsOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const dropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    loadOrganizations()
  }, [])

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const loadOrganizations = async () => {
    try {
      const orgs = await listOrganizations()
      setOrganizations(orgs)

      // Set current org from localStorage or first org
      const savedOrgId = localStorage.getItem('currentOrganizationId')
      const orgToSelect = savedOrgId && orgs.find(o => o.id === savedOrgId)
        ? savedOrgId
        : orgs.length > 0 ? orgs[0].id : null

      if (orgToSelect) {
        setCurrentOrgId(orgToSelect)
        setCurrentOrganization(orgToSelect)
        localStorage.setItem('currentOrganizationId', orgToSelect)
      }
    } catch (error) {
      console.error('Failed to load organizations:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSelectOrg = (orgId: string) => {
    setCurrentOrgId(orgId)
    setCurrentOrganization(orgId)
    localStorage.setItem('currentOrganizationId', orgId)
    setIsOpen(false)
    // Optionally trigger a refresh of data
    window.dispatchEvent(new CustomEvent('organization-changed', { detail: { orgId } }))
  }

  const currentOrg = organizations.find(o => o.id === currentOrgId)

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 text-zinc-500">
        <Loader className="w-4 h-4 animate-spin" />
        <span className="text-[13px]">Loading...</span>
      </div>
    )
  }

  if (organizations.length === 0) {
    return (
      <button
        onClick={onCreateOrg}
        className="flex items-center gap-2 px-3 py-1.5 text-[13px] text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors"
      >
        <Plus className="w-4 h-4" />
        <span>Create Organization</span>
      </button>
    )
  }

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 hover:bg-zinc-100 rounded-lg transition-colors"
      >
        <div className="p-1 rounded bg-emerald-600/10">
          <Building2 className="w-3.5 h-3.5 text-emerald-600" />
        </div>
        <span className="text-[13px] font-medium text-zinc-800 max-w-[150px] truncate">
          {currentOrg?.name || 'Select Organization'}
        </span>
        <ChevronDown className={`w-4 h-4 text-zinc-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-1 w-64 bg-white rounded-lg shadow-lg border border-zinc-200 py-1 z-50">
          <div className="px-3 py-2 border-b border-zinc-100">
            <p className="text-[11px] text-zinc-500 uppercase tracking-wide font-medium">
              Organizations
            </p>
          </div>

          <div className="max-h-64 overflow-y-auto py-1">
            {organizations.map((org) => (
              <button
                key={org.id}
                onClick={() => handleSelectOrg(org.id)}
                className="w-full flex items-center gap-3 px-3 py-2 hover:bg-zinc-50 transition-colors"
              >
                <div className="p-1 rounded bg-emerald-600/10 flex-shrink-0">
                  <Building2 className="w-3 h-3 text-emerald-600" />
                </div>
                <div className="flex-1 text-left min-w-0">
                  <p className="text-[13px] font-medium text-zinc-800 truncate">
                    {org.name}
                  </p>
                  <p className="text-[11px] text-zinc-500">
                    {org.current_user_role}
                  </p>
                </div>
                {org.id === currentOrgId && (
                  <Check className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                )}
              </button>
            ))}
          </div>

          {onCreateOrg && (
            <>
              <div className="border-t border-zinc-100 my-1" />
              <button
                onClick={() => {
                  setIsOpen(false)
                  onCreateOrg()
                }}
                className="w-full flex items-center gap-3 px-3 py-2 hover:bg-zinc-50 transition-colors text-emerald-600"
              >
                <div className="p-1 rounded bg-emerald-600/10">
                  <Plus className="w-3 h-3" />
                </div>
                <span className="text-[13px] font-medium">Create Organization</span>
              </button>
            </>
          )}
        </div>
      )}
    </div>
  )
}
