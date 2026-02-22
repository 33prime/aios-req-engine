/**
 * ConnectionsTab - Causal chain visualization
 *
 * For each belief (sorted by confidence DESC), shows the chain of
 * supporting facts, contradictions, and implications.
 */

'use client'

import { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import type { MemoryVisualizationResponse, MemoryNodeViz, MemoryEdgeViz } from '@/lib/api'

interface ConnectionsTabProps {
  data: MemoryVisualizationResponse | null
}

export function ConnectionsTab({ data }: ConnectionsTabProps) {
  if (!data || data.nodes.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-sm text-[#999999]">No connections to display yet.</p>
      </div>
    )
  }

  const { nodes, edges } = data
  const nodeMap = new Map(nodes.map((n) => [n.id, n]))

  // Get beliefs sorted by confidence DESC, max 10
  const beliefs = nodes
    .filter((n) => n.node_type === 'belief')
    .sort((a, b) => b.confidence - a.confidence)
    .slice(0, 10)

  if (beliefs.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-sm text-[#999999]">No beliefs formed yet. Process more signals to build connections.</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {beliefs.map((belief) => (
        <BeliefChain
          key={belief.id}
          belief={belief}
          edges={edges}
          nodeMap={nodeMap}
        />
      ))}
    </div>
  )
}

function BeliefChain({ belief, edges, nodeMap }: {
  belief: MemoryNodeViz
  edges: MemoryEdgeViz[]
  nodeMap: Map<string, MemoryNodeViz>
}) {
  const [expanded, setExpanded] = useState(false)
  const pct = Math.round(belief.confidence * 100)

  // Find supporting edges (pointing TO this belief with type 'supports')
  const supportEdges = edges.filter(
    (e) => e.to_node_id === belief.id && e.edge_type === 'supports'
  )
  // Find contradicting edges
  const contradictEdges = edges.filter(
    (e) => e.to_node_id === belief.id && e.edge_type === 'contradicts'
  )
  // Find leads_to edges (FROM this belief)
  const implicationEdges = edges.filter(
    (e) => e.from_node_id === belief.id && e.edge_type === 'leads_to'
  )

  return (
    <div className="bg-[#F9F9F9] rounded-lg overflow-hidden">
      {/* Belief header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left px-4 py-3 flex items-center gap-3"
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[11px] font-semibold text-teal-600 uppercase tracking-wide flex-shrink-0">
              Belief
            </span>
            <div className="flex items-center gap-2 flex-shrink-0">
              <div className="w-16 h-1.5 rounded-full bg-gray-200 overflow-hidden">
                <div
                  className="h-full rounded-full bg-emerald-500"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="text-[11px] font-medium text-emerald-700">
                {pct}%
              </span>
            </div>
          </div>
          <p className="text-sm font-medium text-[#333333]">{belief.summary}</p>
        </div>
        {expanded ? (
          <ChevronUp className="w-4 h-4 text-[#999999] flex-shrink-0" />
        ) : (
          <ChevronDown className="w-4 h-4 text-[#999999] flex-shrink-0" />
        )}
      </button>

      {/* Expanded chain */}
      {expanded && (
        <div className="px-4 pb-4">
          {/* Supports section */}
          <ChainSection
            title={`Supports (${supportEdges.length})`}
            titleColor="text-emerald-700"
            borderColor="border-emerald-300"
            icon="✓"
            edges={supportEdges}
            nodeMap={nodeMap}
            directionKey="from_node_id"
          />

          {/* Contradictions section */}
          <ChainSection
            title={`Contradictions (${contradictEdges.length})`}
            titleColor="text-gray-600"
            borderColor="border-gray-300"
            icon="✗"
            edges={contradictEdges}
            nodeMap={nodeMap}
            directionKey="from_node_id"
          />

          {/* Implications section */}
          {implicationEdges.length > 0 && (
            <ChainSection
              title={`Implications (${implicationEdges.length})`}
              titleColor="text-teal-700"
              borderColor="border-teal-300"
              icon="→"
              edges={implicationEdges}
              nodeMap={nodeMap}
              directionKey="to_node_id"
            />
          )}
        </div>
      )}
    </div>
  )
}

function ChainSection({ title, titleColor, borderColor, icon, edges, nodeMap, directionKey }: {
  title: string
  titleColor: string
  borderColor: string
  icon: string
  edges: MemoryEdgeViz[]
  nodeMap: Map<string, MemoryNodeViz>
  directionKey: 'from_node_id' | 'to_node_id'
}) {
  return (
    <div className="mt-3">
      <div className="flex items-center gap-1.5 mb-2">
        <span className={`text-xs font-semibold ${titleColor}`}>
          {icon} {title}
        </span>
      </div>
      {edges.length === 0 ? (
        <p className="text-[11px] text-[#999999] pl-5">None</p>
      ) : (
        <div className={`border-l-2 ${borderColor} ml-1 pl-4 space-y-2`}>
          {edges.map((edge) => {
            const linkedNode = nodeMap.get(edge[directionKey])
            if (!linkedNode) return null
            const nodeType = linkedNode.node_type.toUpperCase()
            return (
              <div key={edge.id} className="bg-white rounded-lg px-3 py-2">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className={`text-[10px] font-semibold uppercase tracking-wide ${
                    linkedNode.node_type === 'fact' ? 'text-emerald-600' :
                    linkedNode.node_type === 'belief' ? 'text-teal-600' : 'text-gray-500'
                  }`}>
                    {nodeType}
                  </span>
                  <span className="text-[10px] text-[#999999]">
                    Source: {linkedNode.source_type || 'unknown'}
                  </span>
                  <span className="text-[10px] text-[#999999]">
                    Strength: {edge.strength?.toFixed(2) || '—'}
                  </span>
                </div>
                <p className="text-sm text-[#333333]">{linkedNode.summary}</p>
                {linkedNode.node_type === 'belief' && (
                  <span className="text-[10px] text-teal-600">
                    Confidence: {Math.round(linkedNode.confidence * 100)}%
                  </span>
                )}
                {edge.rationale && (
                  <p className="text-[11px] text-[#999999] italic mt-1">
                    {edge.rationale}
                  </p>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
