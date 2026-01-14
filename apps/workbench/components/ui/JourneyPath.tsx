/**
 * JourneyPath Component
 *
 * A cartographic-style horizontal journey visualization showing project progress
 * as a winding trail with waypoints, obstacles, and checkpoints.
 */

'use client'

import { useEffect, useState } from 'react'

interface JourneyStage {
  id: string
  label: string
  shortLabel: string
  score: number
  confirmed: number
  total: number
  issues: string[]
}

interface JourneyPathProps {
  stages: JourneyStage[]
  overallScore: number
  blockers: string[]
  warnings: string[]
  onStageClick?: (stageId: string) => void
}

export function JourneyPath({
  stages,
  overallScore,
  blockers,
  warnings,
  onStageClick
}: JourneyPathProps) {
  const [mounted, setMounted] = useState(false)
  const [hoveredStage, setHoveredStage] = useState<string | null>(null)

  useEffect(() => {
    setMounted(true)
  }, [])

  // Calculate position along path (0-100)
  const journeyProgress = overallScore

  // Path coordinates for a gentle winding trail
  const pathD = "M 40 80 C 120 80, 140 40, 220 45 S 340 90, 420 70 S 520 30, 600 50 S 700 80, 780 60 S 880 40, 960 55"

  // Waypoint positions along the path (percentage)
  const waypointPositions = [0, 25, 50, 75, 100]

  // Calculate point on path for current progress
  const getPointOnPath = (progress: number) => {
    // Simplified bezier approximation for marker position
    const x = 40 + (progress / 100) * 920
    // Approximate y based on the path's wave pattern
    const wave = Math.sin((progress / 100) * Math.PI * 2.5) * 20
    const y = 60 + wave
    return { x, y }
  }

  const currentPos = getPointOnPath(journeyProgress)

  return (
    <div className="journey-container">
      {/* Topographic background texture */}
      <div className="journey-texture" />

      {/* Main SVG */}
      <svg
        viewBox="0 0 1000 160"
        className="journey-svg"
        preserveAspectRatio="xMidYMid meet"
      >
        {/* Definitions */}
        <defs>
          {/* Trail gradient */}
          <linearGradient id="trailGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="var(--trail-complete)" />
            <stop offset={`${journeyProgress}%`} stopColor="var(--trail-complete)" />
            <stop offset={`${journeyProgress}%`} stopColor="var(--trail-pending)" />
            <stop offset="100%" stopColor="var(--trail-pending)" />
          </linearGradient>

          {/* Glow filter for current position */}
          <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>

          {/* Marker symbols */}
          <symbol id="waypoint-complete" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="10" fill="var(--waypoint-complete)" stroke="var(--trail-complete)" strokeWidth="2"/>
            <path d="M8 12l3 3 5-5" stroke="white" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
          </symbol>

          <symbol id="waypoint-current" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="10" fill="var(--waypoint-current)" stroke="white" strokeWidth="2"/>
            <circle cx="12" cy="12" r="4" fill="white"/>
          </symbol>

          <symbol id="waypoint-pending" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="10" fill="var(--expedition-bg)" stroke="var(--trail-pending)" strokeWidth="2" strokeDasharray="4 2"/>
          </symbol>

          <symbol id="blocker-marker" viewBox="0 0 24 24">
            <path d="M12 2L2 22h20L12 2z" fill="var(--blocker-color)" stroke="var(--blocker-stroke)" strokeWidth="1.5"/>
            <text x="12" y="17" textAnchor="middle" fill="white" fontSize="12" fontWeight="bold">!</text>
          </symbol>

          <symbol id="checkpoint-marker" viewBox="0 0 24 24">
            <rect x="4" y="4" width="16" height="16" rx="2" fill="var(--checkpoint-color)" stroke="var(--checkpoint-stroke)" strokeWidth="1.5"/>
            <path d="M8 12h8M12 8v8" stroke="white" strokeWidth="2" strokeLinecap="round"/>
          </symbol>
        </defs>

        {/* Topographic lines (decorative) */}
        <g className="topo-lines" opacity="0.15">
          <path d="M 0 120 Q 250 100, 500 115 T 1000 110" stroke="var(--topo-line)" fill="none" strokeWidth="1"/>
          <path d="M 0 135 Q 250 120, 500 130 T 1000 125" stroke="var(--topo-line)" fill="none" strokeWidth="1"/>
          <path d="M 0 25 Q 250 35, 500 20 T 1000 30" stroke="var(--topo-line)" fill="none" strokeWidth="1"/>
        </g>

        {/* Trail shadow */}
        <path
          d={pathD}
          stroke="rgba(0,0,0,0.1)"
          strokeWidth="12"
          fill="none"
          strokeLinecap="round"
          transform="translate(2, 2)"
        />

        {/* Main trail - pending portion (dashed) */}
        <path
          d={pathD}
          stroke="var(--trail-pending)"
          strokeWidth="8"
          fill="none"
          strokeLinecap="round"
          strokeDasharray="12 6"
          className="trail-pending"
        />

        {/* Main trail - completed portion */}
        <path
          d={pathD}
          stroke="var(--trail-complete)"
          strokeWidth="8"
          fill="none"
          strokeLinecap="round"
          strokeDashoffset="0"
          style={{
            clipPath: `inset(0 ${100 - journeyProgress}% 0 0)`
          }}
          className={mounted ? 'trail-animate' : ''}
        />

        {/* Waypoints */}
        {stages.map((stage, index) => {
          const pos = getPointOnPath(waypointPositions[index])
          const isComplete = stage.score >= 80
          const isCurrent = !isComplete && stage.score >= 40
          const isHovered = hoveredStage === stage.id

          return (
            <g
              key={stage.id}
              className="waypoint-group"
              onClick={() => onStageClick?.(stage.id)}
              onMouseEnter={() => setHoveredStage(stage.id)}
              onMouseLeave={() => setHoveredStage(null)}
              style={{ cursor: onStageClick ? 'pointer' : 'default' }}
            >
              {/* Waypoint marker */}
              <use
                href={isComplete ? '#waypoint-complete' : isCurrent ? '#waypoint-current' : '#waypoint-pending'}
                x={pos.x - 14}
                y={pos.y - 14}
                width="28"
                height="28"
                className={`waypoint-marker ${isHovered ? 'waypoint-hover' : ''}`}
              />

              {/* Label */}
              <text
                x={pos.x}
                y={pos.y + 32}
                textAnchor="middle"
                className="waypoint-label"
                fill="var(--label-color)"
              >
                {stage.shortLabel}
              </text>

              {/* Score badge */}
              <g transform={`translate(${pos.x + 16}, ${pos.y - 18})`}>
                <rect
                  x="-14"
                  y="-10"
                  width="28"
                  height="18"
                  rx="9"
                  fill={isComplete ? 'var(--waypoint-complete)' : isCurrent ? 'var(--waypoint-current)' : 'var(--trail-pending)'}
                  opacity="0.9"
                />
                <text
                  x="0"
                  y="4"
                  textAnchor="middle"
                  className="score-badge"
                  fill="white"
                >
                  {stage.score}
                </text>
              </g>

              {/* Hover tooltip */}
              {isHovered && (
                <g transform={`translate(${pos.x}, ${pos.y - 55})`} className="tooltip-group">
                  <rect
                    x="-60"
                    y="-20"
                    width="120"
                    height="36"
                    rx="4"
                    fill="var(--tooltip-bg)"
                    stroke="var(--tooltip-border)"
                  />
                  <text x="0" y="-4" textAnchor="middle" className="tooltip-title" fill="var(--tooltip-text)">
                    {stage.label}
                  </text>
                  <text x="0" y="10" textAnchor="middle" className="tooltip-detail" fill="var(--tooltip-subtext)">
                    {stage.confirmed}/{stage.total} confirmed
                  </text>
                </g>
              )}
            </g>
          )
        })}

        {/* Blocker markers along the path */}
        {blockers.slice(0, 3).map((_, index) => {
          // Position blockers between current position and next milestone
          const blockerProgress = Math.min(journeyProgress + 5 + (index * 8), 95)
          const pos = getPointOnPath(blockerProgress)
          return (
            <g key={`blocker-${index}`} transform={`translate(${pos.x}, ${pos.y - 30})`}>
              <use
                href="#blocker-marker"
                x="-10"
                y="-10"
                width="20"
                height="20"
                className="blocker-icon"
              />
            </g>
          )
        })}

        {/* Current position marker ("You are here") */}
        <g
          transform={`translate(${currentPos.x}, ${currentPos.y})`}
          filter="url(#glow)"
          className={mounted ? 'current-marker-animate' : ''}
        >
          {/* Pulse ring */}
          <circle
            r="20"
            fill="none"
            stroke="var(--current-marker)"
            strokeWidth="2"
            opacity="0.4"
            className="pulse-ring"
          />
          {/* Inner marker */}
          <circle r="12" fill="var(--current-marker)" stroke="white" strokeWidth="3"/>
          <circle r="4" fill="white"/>
        </g>

        {/* Start marker */}
        <g transform="translate(40, 80)">
          <circle r="6" fill="var(--trail-complete)" stroke="white" strokeWidth="2"/>
          <text x="0" y="24" textAnchor="middle" className="endpoint-label" fill="var(--label-color)">START</text>
        </g>

        {/* End marker (flag) */}
        <g transform="translate(960, 55)">
          <rect x="-3" y="-20" width="6" height="35" rx="2" fill="var(--endpoint-color)"/>
          <path d="M 3 -20 L 25 -12 L 3 -4 Z" fill="var(--flag-color)"/>
          <text x="0" y="30" textAnchor="middle" className="endpoint-label" fill="var(--label-color)">READY</text>
        </g>
      </svg>

      {/* Journey stats bar */}
      <div className="journey-stats">
        <div className="journey-stat">
          <span className="stat-value">{overallScore}%</span>
          <span className="stat-label">Journey Complete</span>
        </div>
        {blockers.length > 0 && (
          <div className="journey-stat journey-stat-alert">
            <span className="stat-value">{blockers.length}</span>
            <span className="stat-label">Obstacles Ahead</span>
          </div>
        )}
        {warnings.length > 0 && (
          <div className="journey-stat journey-stat-warning">
            <span className="stat-value">{warnings.length}</span>
            <span className="stat-label">Caution Points</span>
          </div>
        )}
      </div>

      <style jsx>{`
        .journey-container {
          position: relative;
          background: var(--expedition-bg);
          border-radius: 12px;
          padding: 24px;
          overflow: hidden;
          border: 1px solid var(--expedition-border);
        }

        .journey-texture {
          position: absolute;
          inset: 0;
          background-image:
            radial-gradient(circle at 20% 50%, rgba(139, 115, 85, 0.03) 0%, transparent 50%),
            radial-gradient(circle at 80% 50%, rgba(139, 115, 85, 0.03) 0%, transparent 50%),
            url("data:image/svg+xml,%3Csvg viewBox='0 0 100 100' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
          opacity: 0.4;
          pointer-events: none;
        }

        .journey-svg {
          width: 100%;
          height: auto;
          min-height: 180px;
        }

        .trail-animate {
          animation: trailDraw 1.5s ease-out forwards;
        }

        @keyframes trailDraw {
          from { stroke-dasharray: 2000; stroke-dashoffset: 2000; }
          to { stroke-dasharray: 2000; stroke-dashoffset: 0; }
        }

        .waypoint-label {
          font-family: var(--font-expedition);
          font-size: 11px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .score-badge {
          font-family: var(--font-expedition);
          font-size: 10px;
          font-weight: 700;
        }

        .tooltip-title {
          font-family: var(--font-expedition);
          font-size: 11px;
          font-weight: 600;
        }

        .tooltip-detail {
          font-family: var(--font-expedition);
          font-size: 9px;
        }

        .endpoint-label {
          font-family: var(--font-expedition);
          font-size: 10px;
          font-weight: 700;
          letter-spacing: 1px;
        }

        .waypoint-marker {
          transition: transform 0.2s ease;
        }

        .waypoint-hover {
          transform: scale(1.15);
        }

        .current-marker-animate {
          animation: markerAppear 0.6s ease-out 0.5s both;
        }

        @keyframes markerAppear {
          from { transform: translate(${currentPos.x}px, ${currentPos.y}px) scale(0); opacity: 0; }
          to { transform: translate(${currentPos.x}px, ${currentPos.y}px) scale(1); opacity: 1; }
        }

        .pulse-ring {
          animation: pulse 2s ease-in-out infinite;
        }

        @keyframes pulse {
          0%, 100% { r: 16; opacity: 0.4; }
          50% { r: 24; opacity: 0.1; }
        }

        .blocker-icon {
          animation: blockerBounce 2s ease-in-out infinite;
        }

        @keyframes blockerBounce {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-3px); }
        }

        .journey-stats {
          display: flex;
          gap: 24px;
          margin-top: 16px;
          padding-top: 16px;
          border-top: 1px dashed var(--expedition-border);
        }

        .journey-stat {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .stat-value {
          font-family: var(--font-expedition);
          font-size: 24px;
          font-weight: 700;
          color: var(--stat-value-color);
        }

        .stat-label {
          font-family: var(--font-expedition);
          font-size: 11px;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          color: var(--stat-label-color);
        }

        .journey-stat-alert .stat-value {
          color: var(--blocker-color);
        }

        .journey-stat-warning .stat-value {
          color: var(--warning-color);
        }
      `}</style>
    </div>
  )
}
