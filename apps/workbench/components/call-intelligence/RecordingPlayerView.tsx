'use client'

import { useState, useRef, useEffect } from 'react'
import { Play, Pause, Volume2, Loader2, Mic } from 'lucide-react'
import type { CallDetails } from '@/types/call-intelligence'
import { formatDuration } from './constants'
import { SyncedTranscript } from './SyncedTranscript'

export function RecordingPlayerView({
  details,
}: {
  details: CallDetails | null
}) {
  const audioRef = useRef<HTMLAudioElement>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const [playing, setPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)

  const recording = details?.recording
  const transcript = details?.transcript
  const analysis = details?.analysis

  const mediaUrl = recording?.video_url || recording?.recording_url || recording?.audio_url
  const isVideo = !!recording?.video_url || (recording?.recording_url?.includes('video'))

  // Sync playback time
  useEffect(() => {
    const el = isVideo ? videoRef.current : audioRef.current
    if (!el) return

    const onTimeUpdate = () => setCurrentTime(el.currentTime)
    const onDurationChange = () => setDuration(el.duration)
    const onPlay = () => setPlaying(true)
    const onPause = () => setPlaying(false)

    el.addEventListener('timeupdate', onTimeUpdate)
    el.addEventListener('durationchange', onDurationChange)
    el.addEventListener('play', onPlay)
    el.addEventListener('pause', onPause)

    return () => {
      el.removeEventListener('timeupdate', onTimeUpdate)
      el.removeEventListener('durationchange', onDurationChange)
      el.removeEventListener('play', onPlay)
      el.removeEventListener('pause', onPause)
    }
  }, [isVideo, mediaUrl])

  const togglePlay = () => {
    const el = isVideo ? videoRef.current : audioRef.current
    if (!el) return
    if (playing) el.pause()
    else el.play()
  }

  const seekTo = (seconds: number) => {
    const el = isVideo ? videoRef.current : audioRef.current
    if (!el) return
    el.currentTime = seconds
    setCurrentTime(seconds)
  }

  const handleProgressClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!duration) return
    const rect = e.currentTarget.getBoundingClientRect()
    const pct = (e.clientX - rect.left) / rect.width
    seekTo(pct * duration)
  }

  if (!recording) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-6 h-6 animate-spin text-text-muted" />
      </div>
    )
  }

  if (!mediaUrl) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-text-muted gap-2 p-8">
        <Mic className="w-10 h-10 text-[#D0D0D0]" />
        <p className="text-sm">No recording media available</p>
        <p className="text-xs">The recording may still be processing or no audio was captured.</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      {/* Player */}
      <div className="p-5 space-y-3 shrink-0">
        {isVideo ? (
          <div className="bg-[#1a1a2e] rounded-lg overflow-hidden aspect-video">
            <video
              ref={videoRef}
              src={mediaUrl}
              className="w-full h-full"
              playsInline
            />
          </div>
        ) : (
          <div className="bg-gradient-to-r from-[#0A1E2F] to-[#044159] rounded-lg p-6 flex items-center gap-4">
            <button
              onClick={togglePlay}
              className="w-12 h-12 rounded-full bg-white/15 flex items-center justify-center hover:bg-white/25 transition-colors shrink-0"
            >
              {playing ? (
                <Pause className="w-5 h-5 text-white" />
              ) : (
                <Play className="w-5 h-5 text-white ml-0.5" />
              )}
            </button>
            <div className="flex-1 min-w-0 space-y-2">
              <div className="text-sm font-medium text-white truncate">
                {recording.title || 'Call Recording'}
              </div>
              <div
                className="h-1.5 bg-white/20 rounded-full cursor-pointer overflow-hidden"
                onClick={handleProgressClick}
              >
                <div
                  className="h-full bg-white/80 rounded-full transition-all"
                  style={{ width: duration ? `${(currentTime / duration) * 100}%` : '0%' }}
                />
              </div>
              <div className="flex justify-between text-[10px] text-white/60 font-mono">
                <span>{formatDuration(Math.round(currentTime))}</span>
                <span>{formatDuration(Math.round(duration || recording.duration_seconds || 0))}</span>
              </div>
            </div>
            <Volume2 className="w-4 h-4 text-white/40 shrink-0" />
          </div>
        )}

        {/* Video controls bar (for video) */}
        {isVideo && (
          <div className="flex items-center gap-3">
            <button
              onClick={togglePlay}
              className="w-8 h-8 rounded-full bg-surface-muted flex items-center justify-center hover:bg-gray-100 transition-colors"
            >
              {playing ? (
                <Pause className="w-3.5 h-3.5 text-text-body" />
              ) : (
                <Play className="w-3.5 h-3.5 text-text-body ml-0.5" />
              )}
            </button>
            <div
              className="flex-1 h-1.5 bg-gray-100 rounded-full cursor-pointer overflow-hidden"
              onClick={handleProgressClick}
            >
              <div
                className="h-full bg-brand-primary rounded-full transition-all"
                style={{ width: duration ? `${(currentTime / duration) * 100}%` : '0%' }}
              />
            </div>
            <span className="text-xs text-text-muted font-mono shrink-0">
              {formatDuration(Math.round(currentTime))} / {formatDuration(Math.round(duration || recording.duration_seconds || 0))}
            </span>
          </div>
        )}

        {/* Hidden audio element */}
        {!isVideo && <audio ref={audioRef} src={mediaUrl} preload="metadata" />}
      </div>

      {/* Transcript */}
      <div className="flex-1 px-5 pb-5">
        {transcript ? (
          <SyncedTranscript
            segments={transcript.segments}
            timeline={analysis?.engagement_timeline}
            activeTimestamp={currentTime}
            onSegmentClick={seekTo}
          />
        ) : (
          <div className="flex flex-col items-center justify-center py-12 text-text-muted gap-2">
            <p className="text-sm">No transcript available</p>
            <p className="text-xs">Transcript will appear here once processing completes.</p>
          </div>
        )}
      </div>
    </div>
  )
}
