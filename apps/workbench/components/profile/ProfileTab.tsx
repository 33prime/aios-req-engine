'use client'

import { useState, useRef, useEffect } from 'react'
import { User, Pencil, Save, X, Loader, Phone, Linkedin, Video, MapPin, FileText, Briefcase, LogOut, Camera, Sparkles, CheckCircle, AlertCircle } from 'lucide-react'
import Image from 'next/image'
import { updateMyProfile, enrichConsultantProfile, getConsultantEnrichmentStatus } from '@/lib/api'
import { useProfile } from '@/lib/hooks/use-api'
import { useAuth } from '@/components/auth/AuthProvider'
import { supabase } from '@/lib/supabase'
import { analytics } from '@/lib/analytics'
import type { Profile, ProfileUpdate, ConsultantEnrichmentStatus } from '@/types/api'

interface ProfileTabProps {
  onLogout?: () => void
}

export default function ProfileTab({ onLogout }: ProfileTabProps) {
  const { user, signOut } = useAuth()
  const { data: profile, error: profileError, isLoading, mutate: mutateProfile } = useProfile()
  const [isUploadingPhoto, setIsUploadingPhoto] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleUpdateProfile = async (updates: ProfileUpdate) => {
    if (!profile) return
    try {
      const updated = await updateMyProfile(updates)
      // Update SWR cache so AppSidebar etc. see the change instantly
      mutateProfile(updated, false)
    } catch (err) {
      console.error('Failed to update profile:', err)
      throw err
    }
  }

  const handlePhotoUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file || !profile || !supabase) return

    // Validate file type
    if (!file.type.startsWith('image/')) {
      alert('Please select an image file')
      return
    }

    // Validate file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      alert('Image must be less than 5MB')
      return
    }

    setIsUploadingPhoto(true)
    try {
      // Generate unique filename
      const fileExt = file.name.split('.').pop()
      const fileName = `${profile.user_id}-${Date.now()}.${fileExt}`
      const filePath = `profile-photos/${fileName}`

      // Upload to Supabase Storage
      const { error: uploadError } = await supabase.storage
        .from('avatars')
        .upload(filePath, file, { upsert: true })

      if (uploadError) {
        throw uploadError
      }

      // Get public URL
      const { data: { publicUrl } } = supabase.storage
        .from('avatars')
        .getPublicUrl(filePath)

      // Update profile with new photo URL
      const updated = await updateMyProfile({ photo_url: publicUrl })
      mutateProfile(updated, false)
    } catch (err) {
      console.error('Failed to upload photo:', err)
      alert('Failed to upload photo. Please try again.')
    } finally {
      setIsUploadingPhoto(false)
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const handleLogout = async () => {
    await signOut()
    onLogout?.()
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'numeric',
      day: 'numeric',
      year: 'numeric',
    })
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader className="w-5 h-5 animate-spin text-zinc-400" />
      </div>
    )
  }

  if (profileError || !profile) {
    return (
      <div className="rounded-xl border border-zinc-200 bg-white shadow-sm p-8 text-center">
        <User className="w-10 h-10 text-zinc-300 mx-auto mb-4" />
        <h3 className="text-[14px] font-semibold text-zinc-900 mb-2">
          {profileError ? 'Failed to load profile' : 'Profile not found'}
        </h3>
      </div>
    )
  }

  const displayName = profile.first_name && profile.last_name
    ? `${profile.first_name} ${profile.last_name}`
    : profile.first_name || profile.email.split('@')[0]

  const initials = profile.first_name && profile.last_name
    ? `${profile.first_name[0]}${profile.last_name[0]}`.toUpperCase()
    : profile.email[0].toUpperCase()

  return (
    <div className="space-y-6">
      {/* Profile Header */}
      <div className="rounded-xl border border-zinc-200 bg-white shadow-sm p-6">
        <div className="flex items-center gap-4">
          {/* Profile Photo with Upload */}
          <div className="relative group">
            <div className="w-16 h-16 rounded-full bg-gradient-to-br from-emerald-400 to-teal-500 flex items-center justify-center text-white overflow-hidden">
              {profile.photo_url ? (
                <Image
                  src={profile.photo_url}
                  alt={displayName}
                  width={64}
                  height={64}
                  className="w-full h-full object-cover"
                />
              ) : (
                <span className="text-xl font-semibold">{initials}</span>
              )}
            </div>
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploadingPhoto}
              className="absolute inset-0 rounded-full bg-black/50 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity cursor-pointer"
            >
              {isUploadingPhoto ? (
                <Loader className="w-5 h-5 text-white animate-spin" />
              ) : (
                <Camera className="w-5 h-5 text-white" />
              )}
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handlePhotoUpload}
              className="hidden"
            />
          </div>
          <div className="flex-1">
            <h2 className="text-[16px] font-semibold text-zinc-900">{displayName}</h2>
            <p className="text-[13px] text-zinc-600">{profile.email}</p>
            <p className="text-[12px] text-zinc-500 mt-1">
              Profile created {formatDate(profile.created_at)}
              {profile.updated_at && ` · Last updated ${formatDate(profile.updated_at)}`}
            </p>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 px-3 py-2 text-[13px] text-red-600 hover:bg-red-50 rounded-lg transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Log out
          </button>
        </div>
      </div>

      {/* Personal Information */}
      <PersonalInfoCard profile={profile} onUpdate={handleUpdateProfile} />

      {/* About Me */}
      <AboutMeCard profile={profile} onUpdate={handleUpdateProfile} />

      {/* Solution Consulting Background */}
      <ConsultingBackgroundCard profile={profile} onUpdate={handleUpdateProfile} />

      {/* AI Profile Enrichment */}
      <ConsultantEnrichmentCard profile={profile} onEnriched={() => mutateProfile()} />
    </div>
  )
}

// ============================================================================
// Personal Information Card
// ============================================================================

interface CardProps {
  profile: Profile
  onUpdate: (updates: ProfileUpdate) => Promise<void>
}

function PersonalInfoCard({ profile, onUpdate }: CardProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [formData, setFormData] = useState({
    first_name: profile.first_name || '',
    last_name: profile.last_name || '',
    phone_number: profile.phone_number || '',
    linkedin: profile.linkedin || '',
    meeting_link: profile.meeting_link || '',
    city: profile.city || '',
    state: profile.state || '',
  })

  const handleSave = async () => {
    setIsSaving(true)
    try {
      await onUpdate({
        first_name: formData.first_name || undefined,
        last_name: formData.last_name || undefined,
        phone_number: formData.phone_number || undefined,
        linkedin: formData.linkedin || undefined,
        meeting_link: formData.meeting_link || undefined,
        city: formData.city || undefined,
        state: formData.state || undefined,
      })
      setIsEditing(false)
    } catch (err) {
      console.error('Failed to save:', err)
    } finally {
      setIsSaving(false)
    }
  }

  const handleCancel = () => {
    setFormData({
      first_name: profile.first_name || '',
      last_name: profile.last_name || '',
      phone_number: profile.phone_number || '',
      linkedin: profile.linkedin || '',
      meeting_link: profile.meeting_link || '',
      city: profile.city || '',
      state: profile.state || '',
    })
    setIsEditing(false)
  }

  return (
    <div className="rounded-xl border border-zinc-200 bg-white shadow-sm p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-1.5 rounded-full bg-emerald-600/10 text-emerald-600">
            <User className="w-4 h-4" />
          </div>
          <p className="text-[13px] text-zinc-800 font-semibold">Personal Information</p>
        </div>
        {!isEditing ? (
          <button
            onClick={() => setIsEditing(true)}
            className="p-1.5 hover:bg-zinc-100 rounded-lg transition-colors text-zinc-500 hover:text-zinc-700"
          >
            <Pencil className="w-4 h-4" />
          </button>
        ) : (
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
              disabled={isSaving}
              className="p-1.5 hover:bg-emerald-100 rounded-lg transition-colors text-emerald-600 disabled:opacity-50"
            >
              {isSaving ? <Loader className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            </button>
          </div>
        )}
      </div>

      {isEditing ? (
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-[12px] text-zinc-600 block mb-1">First Name</label>
            <input
              type="text"
              value={formData.first_name}
              onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
              className="w-full text-[13px] text-zinc-700 border border-zinc-300 rounded-md px-3 py-2 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
          </div>
          <div>
            <label className="text-[12px] text-zinc-600 block mb-1">Last Name</label>
            <input
              type="text"
              value={formData.last_name}
              onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
              className="w-full text-[13px] text-zinc-700 border border-zinc-300 rounded-md px-3 py-2 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
          </div>
          <div>
            <label className="text-[12px] text-zinc-600 block mb-1">Phone Number</label>
            <input
              type="tel"
              value={formData.phone_number}
              onChange={(e) => setFormData({ ...formData, phone_number: e.target.value })}
              className="w-full text-[13px] text-zinc-700 border border-zinc-300 rounded-md px-3 py-2 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
          </div>
          <div>
            <label className="text-[12px] text-zinc-600 block mb-1">LinkedIn</label>
            <input
              type="url"
              value={formData.linkedin}
              onChange={(e) => setFormData({ ...formData, linkedin: e.target.value })}
              className="w-full text-[13px] text-zinc-700 border border-zinc-300 rounded-md px-3 py-2 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              placeholder="https://linkedin.com/in/..."
            />
          </div>
          <div>
            <label className="text-[12px] text-zinc-600 block mb-1">Meeting Link</label>
            <input
              type="url"
              value={formData.meeting_link}
              onChange={(e) => setFormData({ ...formData, meeting_link: e.target.value })}
              className="w-full text-[13px] text-zinc-700 border border-zinc-300 rounded-md px-3 py-2 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              placeholder="https://calendly.com/..."
            />
          </div>
          <div>
            <label className="text-[12px] text-zinc-600 block mb-1">City/State</label>
            <div className="flex gap-2">
              <input
                type="text"
                value={formData.city}
                onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                className="flex-1 text-[13px] text-zinc-700 border border-zinc-300 rounded-md px-3 py-2 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                placeholder="City"
              />
              <input
                type="text"
                value={formData.state}
                onChange={(e) => setFormData({ ...formData, state: e.target.value })}
                className="w-20 text-[13px] text-zinc-700 border border-zinc-300 rounded-md px-3 py-2 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                placeholder="State"
              />
            </div>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-[11px] text-zinc-500 mb-1">First Name</p>
            <p className="text-[13px] text-zinc-800">{profile.first_name || 'Not set'}</p>
          </div>
          <div>
            <p className="text-[11px] text-zinc-500 mb-1">Last Name</p>
            <p className="text-[13px] text-zinc-800">{profile.last_name || 'Not set'}</p>
          </div>
          <div>
            <p className="text-[11px] text-zinc-500 mb-1">Email</p>
            <p className="text-[13px] text-zinc-800">{profile.email}</p>
          </div>
          <div>
            <p className="text-[11px] text-zinc-500 mb-1 flex items-center gap-1">
              <Phone className="w-3 h-3" /> Phone Number
            </p>
            <p className="text-[13px] text-zinc-800">{profile.phone_number || 'Not set'}</p>
          </div>
          <div>
            <p className="text-[11px] text-zinc-500 mb-1 flex items-center gap-1">
              <Linkedin className="w-3 h-3" /> LinkedIn
            </p>
            <p className="text-[13px] text-zinc-800">{profile.linkedin || 'Not set'}</p>
          </div>
          <div>
            <p className="text-[11px] text-zinc-500 mb-1 flex items-center gap-1">
              <Video className="w-3 h-3" /> Meeting Link
            </p>
            <p className="text-[13px] text-zinc-800">{profile.meeting_link || 'Not set'}</p>
          </div>
          <div>
            <p className="text-[11px] text-zinc-500 mb-1 flex items-center gap-1">
              <MapPin className="w-3 h-3" /> City/State
            </p>
            <p className="text-[13px] text-zinc-800">
              {profile.city || profile.state
                ? `${profile.city || ''}${profile.city && profile.state ? ', ' : ''}${profile.state || ''}`
                : 'Not set'}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

// ============================================================================
// About Me Card
// ============================================================================

function AboutMeCard({ profile, onUpdate }: CardProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [bio, setBio] = useState(profile.bio || '')

  const handleSave = async () => {
    setIsSaving(true)
    try {
      await onUpdate({ bio: bio || undefined })
      setIsEditing(false)
    } catch (err) {
      console.error('Failed to save:', err)
    } finally {
      setIsSaving(false)
    }
  }

  const handleCancel = () => {
    setBio(profile.bio || '')
    setIsEditing(false)
  }

  return (
    <div className="rounded-xl border border-zinc-200 bg-white shadow-sm p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="p-1.5 rounded-full bg-emerald-600/10 text-emerald-600">
            <FileText className="w-4 h-4" />
          </div>
          <p className="text-[13px] text-zinc-800 font-semibold">About Me</p>
        </div>
        {!isEditing ? (
          <button
            onClick={() => setIsEditing(true)}
            className="p-1.5 hover:bg-zinc-100 rounded-lg transition-colors text-zinc-500 hover:text-zinc-700"
          >
            <Pencil className="w-4 h-4" />
          </button>
        ) : (
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
              disabled={isSaving}
              className="p-1.5 hover:bg-emerald-100 rounded-lg transition-colors text-emerald-600 disabled:opacity-50"
            >
              {isSaving ? <Loader className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            </button>
          </div>
        )}
      </div>

      <p className="text-[12px] text-zinc-500 mb-2">Brief description about yourself and your role</p>

      {isEditing ? (
        <textarea
          value={bio}
          onChange={(e) => setBio(e.target.value)}
          rows={4}
          className="w-full text-[13px] text-zinc-700 border border-zinc-300 rounded-md px-3 py-2 focus:outline-none focus:ring-1 focus:ring-emerald-500 resize-none"
          placeholder="Tell us about yourself..."
        />
      ) : (
        <p className="text-[13px] text-zinc-700 italic">
          {profile.bio || 'Please add text'}
        </p>
      )}
    </div>
  )
}

// ============================================================================
// Solution Consulting Background Card
// ============================================================================

function ConsultingBackgroundCard({ profile, onUpdate }: CardProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [expertiseText, setExpertiseText] = useState(profile.expertise_areas?.join('\n') || '')

  const handleSave = async () => {
    setIsSaving(true)
    try {
      const areas = expertiseText
        .split('\n')
        .map(s => s.trim())
        .filter(s => s.length > 0)
      await onUpdate({ expertise_areas: areas.length > 0 ? areas : undefined })
      setIsEditing(false)
    } catch (err) {
      console.error('Failed to save:', err)
    } finally {
      setIsSaving(false)
    }
  }

  const handleCancel = () => {
    setExpertiseText(profile.expertise_areas?.join('\n') || '')
    setIsEditing(false)
  }

  return (
    <div className="rounded-xl border border-zinc-200 bg-white shadow-sm p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="p-1.5 rounded-full bg-emerald-600/10 text-emerald-600">
            <Briefcase className="w-4 h-4" />
          </div>
          <p className="text-[13px] text-zinc-800 font-semibold">Solution Consulting Background</p>
        </div>
        {!isEditing ? (
          <button
            onClick={() => setIsEditing(true)}
            className="p-1.5 hover:bg-zinc-100 rounded-lg transition-colors text-zinc-500 hover:text-zinc-700"
          >
            <Pencil className="w-4 h-4" />
          </button>
        ) : (
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
              disabled={isSaving}
              className="p-1.5 hover:bg-emerald-100 rounded-lg transition-colors text-emerald-600 disabled:opacity-50"
            >
              {isSaving ? <Loader className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            </button>
          </div>
        )}
      </div>

      <p className="text-[12px] text-zinc-500 mb-2">Your experience and expertise in solution consulting</p>

      {isEditing ? (
        <textarea
          value={expertiseText}
          onChange={(e) => setExpertiseText(e.target.value)}
          rows={4}
          className="w-full text-[13px] text-zinc-700 border border-zinc-300 rounded-md px-3 py-2 focus:outline-none focus:ring-1 focus:ring-emerald-500 resize-none"
          placeholder="Enter your expertise areas (one per line)..."
        />
      ) : (
        <div className="text-[13px] text-zinc-700">
          {profile.expertise_areas && profile.expertise_areas.length > 0 ? (
            <ul className="space-y-1">
              {profile.expertise_areas.map((area, i) => (
                <li key={i}>• {area}</li>
              ))}
            </ul>
          ) : (
            <p className="italic">Please add text</p>
          )}
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Consultant AI Enrichment Card
// ============================================================================

interface EnrichmentCardProps {
  profile: Profile
  onEnriched: () => void
}

function ConsultantEnrichmentCard({ profile, onEnriched }: EnrichmentCardProps) {
  const [linkedinText, setLinkedinText] = useState('')
  const [websiteText, setWebsiteText] = useState('')
  const [isEnriching, setIsEnriching] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [enrichmentData, setEnrichmentData] = useState<ConsultantEnrichmentStatus | null>(null)

  // Load enrichment status on mount if already enriched
  useEffect(() => {
    if (profile.enrichment_status === 'enriched') {
      getConsultantEnrichmentStatus()
        .then(setEnrichmentData)
        .catch(() => {})
    }
  }, [profile.enrichment_status])

  const handleEnrich = async () => {
    if (!linkedinText && !websiteText) return
    setIsEnriching(true)
    setError(null)
    analytics.profileEnrichmentStarted()

    try {
      const result = await enrichConsultantProfile({
        linkedin_text: linkedinText || undefined,
        website_text: websiteText || undefined,
      })
      analytics.profileEnrichmentCompleted(result.profile_completeness)
      // Refresh enrichment status
      const status = await getConsultantEnrichmentStatus()
      setEnrichmentData(status)
      onEnriched()
    } catch (err: any) {
      setError(err.message || 'Enrichment failed')
    } finally {
      setIsEnriching(false)
    }
  }

  const statusBadge = () => {
    const status = profile.enrichment_status || 'pending'
    switch (status) {
      case 'enriched':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-[#E8F5E9] text-[#25785A]">
            <CheckCircle className="w-3 h-3" /> Enriched
          </span>
        )
      case 'enriching':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-[#F0F0F0] text-[#666666]">
            <Loader className="w-3 h-3 animate-spin" /> Enriching...
          </span>
        )
      case 'failed':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-red-50 text-red-600">
            <AlertCircle className="w-3 h-3" /> Failed
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-[#F0F0F0] text-[#666666]">
            Pending
          </span>
        )
    }
  }

  return (
    <div className="rounded-xl border border-zinc-200 bg-white shadow-sm p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="p-1.5 rounded-full bg-brand-primary-light text-brand-primary">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <p className="text-[13px] text-zinc-800 font-semibold">AI Profile Enrichment</p>
            <p className="text-[11px] text-zinc-500">Paste your LinkedIn profile or website bio for AI analysis</p>
          </div>
        </div>
        {statusBadge()}
      </div>

      {/* Enrichment Results (if enriched) */}
      {enrichmentData && enrichmentData.enrichment_status === 'enriched' && (
        <div className="mb-6 space-y-3">
          {/* Completeness Bar */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-[11px] text-zinc-500">Profile Completeness</span>
              <span className="text-[11px] font-medium text-zinc-700">{enrichmentData.profile_completeness}%</span>
            </div>
            <div className="w-full h-1.5 bg-zinc-100 rounded-full">
              <div
                className="h-full bg-brand-primary rounded-full transition-all"
                style={{ width: `${enrichmentData.profile_completeness}%` }}
              />
            </div>
          </div>

          {/* Summary */}
          {enrichmentData.consultant_summary && (
            <div className="p-3 bg-zinc-50 rounded-lg">
              <p className="text-[11px] text-zinc-500 mb-1">Professional Summary</p>
              <p className="text-[12px] text-zinc-700">{enrichmentData.consultant_summary}</p>
            </div>
          )}

          {/* Expertise Tags */}
          {enrichmentData.industry_expertise.length > 0 && (
            <div>
              <p className="text-[11px] text-zinc-500 mb-1.5">Industry Expertise</p>
              <div className="flex flex-wrap gap-1.5">
                {enrichmentData.industry_expertise.map((ind, i) => (
                  <span key={i} className="px-2 py-0.5 bg-[#F0F0F0] text-[#666666] text-[11px] rounded-md">
                    {ind}
                  </span>
                ))}
              </div>
            </div>
          )}

          {enrichmentData.methodology_expertise.length > 0 && (
            <div>
              <p className="text-[11px] text-zinc-500 mb-1.5">Methodology</p>
              <div className="flex flex-wrap gap-1.5">
                {enrichmentData.methodology_expertise.map((m, i) => (
                  <span key={i} className="px-2 py-0.5 bg-[#E8F5E9] text-[#25785A] text-[11px] rounded-md">
                    {m}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Input Areas */}
      <div className="space-y-3">
        <div>
          <label className="text-[12px] text-zinc-600 block mb-1">LinkedIn Profile Text</label>
          <textarea
            value={linkedinText}
            onChange={(e) => setLinkedinText(e.target.value)}
            rows={3}
            className="w-full text-[13px] text-zinc-700 border border-zinc-300 rounded-md px-3 py-2 focus:outline-none focus:ring-1 focus:ring-brand-primary resize-none"
            placeholder="Copy and paste your LinkedIn About section, Experience, etc..."
          />
        </div>
        <div>
          <label className="text-[12px] text-zinc-600 block mb-1">Website Bio (optional)</label>
          <textarea
            value={websiteText}
            onChange={(e) => setWebsiteText(e.target.value)}
            rows={3}
            className="w-full text-[13px] text-zinc-700 border border-zinc-300 rounded-md px-3 py-2 focus:outline-none focus:ring-1 focus:ring-brand-primary resize-none"
            placeholder="Paste your website bio or about page content..."
          />
        </div>

        {error && (
          <p className="text-[12px] text-red-600">{error}</p>
        )}

        <button
          onClick={handleEnrich}
          disabled={isEnriching || (!linkedinText && !websiteText)}
          className="flex items-center gap-2 px-4 py-2 bg-brand-primary hover:bg-[#25785A] text-white text-[13px] font-medium rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isEnriching ? (
            <>
              <Loader className="w-4 h-4 animate-spin" />
              Enriching...
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              {profile.enrichment_status === 'enriched' ? 'Re-enrich Profile' : 'Enrich Profile'}
            </>
          )}
        </button>
      </div>
    </div>
  )
}
