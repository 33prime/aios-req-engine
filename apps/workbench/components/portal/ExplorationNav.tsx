'use client'

import { ChevronLeft, ChevronRight, Share2 } from 'lucide-react'

interface ExplorationNavProps {
  currentIndex: number
  totalEpics: number
  epicTitles: string[]
  onPrevious: () => void
  onNext: () => void
  onNavigate: (index: number) => void
  onShare?: () => void
}

export function ExplorationNav({
  currentIndex,
  totalEpics,
  epicTitles,
  onPrevious,
  onNext,
  onNavigate,
  onShare,
}: ExplorationNavProps) {
  return (
    <div className="flex items-center justify-between px-4 py-2">
      <button
        onClick={onPrevious}
        disabled={currentIndex <= 0}
        className="flex items-center gap-1 text-sm text-white/80 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
      >
        <ChevronLeft className="w-4 h-4" />
        Previous
      </button>

      {/* Progress dots + share */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          {Array.from({ length: totalEpics }).map((_, i) => (
            <button
              key={i}
              onClick={() => onNavigate(i)}
              title={epicTitles[i] || `Epic ${i + 1}`}
              className={`w-2.5 h-2.5 rounded-full transition-all ${
                i === currentIndex
                  ? 'bg-white scale-125'
                  : 'bg-white/30 hover:bg-white/60'
              }`}
            />
          ))}
        </div>

        {onShare && (
          <button
            onClick={onShare}
            title="Share with a colleague"
            className="p-1.5 rounded-lg text-white/50 hover:text-white hover:bg-white/10 transition-colors"
          >
            <Share2 className="w-4 h-4" />
          </button>
        )}
      </div>

      <button
        onClick={onNext}
        className="flex items-center gap-1 text-sm text-white/80 hover:text-white transition-colors"
      >
        {currentIndex >= totalEpics - 1 ? 'Finish' : 'Next'}
        <ChevronRight className="w-4 h-4" />
      </button>
    </div>
  )
}
