'use client'

import { Sparkles } from 'lucide-react'
import type { FeatureInsight, CallSignal, ContentNugget, CompetitiveMention } from '@/types/call-intelligence'
import { CollapsibleSection } from './CollapsibleSection'
import {
  REACTION_CONFIG,
  SIGNAL_TYPE_STYLES,
  SIGNAL_TYPE_ICONS,
  SIGNAL_TYPE_LABELS,
  NUGGET_TYPE_STYLES,
  NUGGET_TYPE_LABELS,
  SENTIMENT_STYLES,
} from './constants'

export function AhaMomentHero({ insights }: { insights: FeatureInsight[] }) {
  const ahas = insights.filter(fi => fi.is_aha_moment)
  if (ahas.length === 0) return null

  return (
    <div className="space-y-3">
      {ahas.map((fi, i) => (
        <div key={fi.id || i} className="p-4 bg-[#F0F7FA] border border-[#D4E8EF] rounded-xl">
          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="w-4 h-4 text-[#3FAF7A]" />
            <span className="text-xs font-semibold text-[#044159] uppercase tracking-wide">Aha Moment</span>
            <span className="px-2 py-0.5 text-xs font-medium bg-white rounded-full text-text-body border border-[#D4E8EF]">
              {fi.feature_name}
            </span>
          </div>
          {fi.quote && (
            <blockquote className="text-sm text-text-body italic leading-relaxed">
              &ldquo;{fi.quote}&rdquo;
            </blockquote>
          )}
          {fi.context && <p className="mt-2 text-xs text-text-muted">{fi.context}</p>}
        </div>
      ))}
    </div>
  )
}

export function FeatureReactionsSection({ insights }: { insights: FeatureInsight[] }) {
  const nonAha = insights.filter(fi => !fi.is_aha_moment)
  return (
    <CollapsibleSection title="Feature Reactions" count={nonAha.length}>
      {nonAha.map((fi, i) => {
        const cfg = REACTION_CONFIG[fi.reaction]
        const Icon = cfg.icon
        return (
          <div key={fi.id || i} className="flex items-start gap-3 p-3 bg-white rounded-lg border border-border">
            <div className={`p-1.5 rounded-md ${cfg.color}`}>
              <Icon className="w-4 h-4" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-text-body">{fi.feature_name}</span>
                <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${cfg.color}`}>
                  {cfg.label}
                </span>
              </div>
              {fi.quote && (
                <blockquote className="mt-1.5 text-xs text-text-muted italic border-l-2 border-border pl-2">
                  &ldquo;{fi.quote}&rdquo;
                </blockquote>
              )}
              {fi.context && <p className="mt-1 text-xs text-text-muted">{fi.context}</p>}
            </div>
          </div>
        )
      })}
    </CollapsibleSection>
  )
}

export function MarketSignalsSection({ signals }: { signals: CallSignal[] }) {
  return (
    <CollapsibleSection title="Market Signals" count={signals.length}>
      {signals.map((sig, i) => {
        const Icon = SIGNAL_TYPE_ICONS[sig.signal_type]
        return (
          <div key={sig.id || i} className="p-3 bg-white rounded-lg border border-border space-y-2">
            <div className="flex items-center gap-2">
              <Icon className="w-4 h-4 text-text-muted" />
              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${SIGNAL_TYPE_STYLES[sig.signal_type]}`}>
                {SIGNAL_TYPE_LABELS[sig.signal_type]}
              </span>
              <span className="text-sm font-medium text-text-body">{sig.title}</span>
            </div>
            {sig.description && <p className="text-xs text-text-muted">{sig.description}</p>}
            <div className="flex items-center gap-2">
              <span className="text-xs text-text-muted">Intensity</span>
              <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-brand-primary rounded-full transition-all"
                  style={{ width: `${Math.round(sig.intensity * 100)}%` }}
                />
              </div>
              <span className="text-xs text-text-muted">{Math.round(sig.intensity * 100)}%</span>
            </div>
            {sig.quote && (
              <blockquote className="text-xs text-text-muted italic border-l-2 border-border pl-2">
                &ldquo;{sig.quote}&rdquo;
              </blockquote>
            )}
          </div>
        )
      })}
    </CollapsibleSection>
  )
}

export function ContentNuggetsSection({ nuggets }: { nuggets: ContentNugget[] }) {
  return (
    <CollapsibleSection title="Content Nuggets" count={nuggets.length}>
      {nuggets.map((n, i) => (
        <div key={n.id || i} className="p-3 bg-white rounded-lg border border-border space-y-2">
          <div className="flex items-center gap-2">
            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${NUGGET_TYPE_STYLES[n.nugget_type]}`}>
              {NUGGET_TYPE_LABELS[n.nugget_type]}
            </span>
            {n.speaker && <span className="text-xs text-text-muted">&mdash; {n.speaker}</span>}
          </div>
          <p className="text-sm text-text-body">{n.content}</p>
          <div className="flex items-center gap-2">
            <span className="text-xs text-text-muted">Reuse potential</span>
            <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-brand-primary rounded-full transition-all"
                style={{ width: `${Math.round(n.reuse_score * 100)}%` }}
              />
            </div>
            <span className="text-xs text-text-muted">{Math.round(n.reuse_score * 100)}%</span>
          </div>
        </div>
      ))}
    </CollapsibleSection>
  )
}

export function CompetitiveMentionsSection({ mentions }: { mentions: CompetitiveMention[] }) {
  return (
    <CollapsibleSection title="Competitive Mentions" count={mentions.length}>
      {mentions.map((m, i) => (
        <div key={m.id || i} className="p-3 bg-white rounded-lg border border-border space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-text-body">{m.competitor_name}</span>
            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${SENTIMENT_STYLES[m.sentiment]}`}>
              {m.sentiment}
            </span>
          </div>
          {m.context && <p className="text-xs text-text-muted">{m.context}</p>}
          {m.quote && (
            <blockquote className="text-xs text-text-muted italic border-l-2 border-border pl-2">
              &ldquo;{m.quote}&rdquo;
            </blockquote>
          )}
          {m.feature_comparison && (
            <p className="text-xs text-text-muted"><span className="font-medium">Comparison:</span> {m.feature_comparison}</p>
          )}
        </div>
      ))}
    </CollapsibleSection>
  )
}
