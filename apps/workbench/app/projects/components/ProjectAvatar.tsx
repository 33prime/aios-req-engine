import React from 'react'

interface ProjectAvatarProps {
  name: string
  clientName?: string | null
}

export function ProjectAvatar({ name, clientName }: ProjectAvatarProps) {
  // Generate initials from client name or project name
  const displayName = clientName || name
  const initials = displayName
    .split(' ')
    .map((word) => word[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)

  // Generate a consistent gradient based on the name (emerald/teal palette)
  const gradients = [
    'from-emerald-400 to-teal-500',
    'from-teal-400 to-cyan-500',
    'from-emerald-500 to-emerald-600',
    'from-[#009b87] to-emerald-500',
    'from-teal-500 to-teal-600',
  ]
  const gradientIndex = displayName.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0) % gradients.length
  const gradient = gradients[gradientIndex]

  return (
    <div
      className={`w-6 h-6 rounded-lg bg-gradient-to-br ${gradient} text-white flex items-center justify-center text-[10px] font-semibold flex-shrink-0 shadow-sm`}
    >
      {initials}
    </div>
  )
}
