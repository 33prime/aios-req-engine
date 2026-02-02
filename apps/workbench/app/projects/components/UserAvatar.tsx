import React from 'react'
import { User } from 'lucide-react'

interface UserAvatarProps {
  name?: string
  photoUrl?: string
  size?: 'small' | 'medium' | 'large'
  profile?: {
    first_name?: string
    last_name?: string
    photo_url?: string
  }
}

export function UserAvatar({ name, photoUrl, size = 'small', profile }: UserAvatarProps) {
  // Support both new props and legacy profile prop
  const displayName = name || (profile ? [profile.first_name, profile.last_name].filter(Boolean).join(' ') : undefined)
  const displayPhotoUrl = photoUrl || profile?.photo_url
  const initials = name?.[0]?.toUpperCase() || (profile?.first_name?.[0] || '').toUpperCase()

  const sizeClasses = {
    small: 'w-5 h-5 text-xs',
    medium: 'w-8 h-8 text-sm',
    large: 'w-10 h-10 text-base',
  }

  const iconSizes = {
    small: 'w-3 h-3',
    medium: 'w-4 h-4',
    large: 'w-5 h-5',
  }

  if (!displayName && !displayPhotoUrl) {
    return (
      <div className={`rounded-full bg-gray-200 flex items-center justify-center ${sizeClasses[size]}`}>
        <User className={`text-gray-400 ${iconSizes[size]}`} />
      </div>
    )
  }

  // Generate gradient color based on name
  const getGradientColor = (str: string = '') => {
    const colors = [
      'from-emerald-400 to-teal-500',
      'from-blue-400 to-indigo-500',
      'from-purple-400 to-pink-500',
      'from-orange-400 to-red-500',
      'from-teal-400 to-cyan-500',
    ]
    const hash = str.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)
    return colors[hash % colors.length]
  }

  return (
    <>
      {displayPhotoUrl ? (
        <img
          src={displayPhotoUrl}
          alt={displayName}
          className={`rounded-full object-cover ${sizeClasses[size]}`}
        />
      ) : (
        <div className={`rounded-full bg-gradient-to-br ${getGradientColor(displayName)} flex items-center justify-center text-white font-medium ${sizeClasses[size]}`}>
          {initials || <User className={iconSizes[size]} />}
        </div>
      )}
    </>
  )
}
