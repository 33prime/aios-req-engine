/**
 * KnowledgeTab — Hero feature: interactive knowledge graph + detail panel + feedback
 *
 * Graph fills 70%, NodeDetailPanel slides from right (30%) on node click.
 * Enhanced from GraphTab with consultant feedback, filtering, and Add Belief.
 */

'use client'

import { useState, useCallback, useMemo, useEffect } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type NodeProps,
  Handle,
  Position,
  MarkerType,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import dagre from 'dagre'
import { Plus } from 'lucide-react'
import type { MemoryVisualizationResponse } from '@/lib/api'
import { submitNodeFeedback } from '@/lib/api'
import type { IntelGraphNode, IntelGraphResponse } from '@/types/workspace'
import { useIntelGraph } from '@/lib/hooks/use-api'
import { NodeDetailPanel } from './NodeDetailPanel'
import { AddBeliefModal } from './AddBeliefModal'

interface KnowledgeTabProps {
  projectId: string
  data: MemoryVisualizationResponse | null
}

type NodeFilter = 'all' | 'fact' | 'belief' | 'insight'
type ConsultantFilter = 'all' | 'confirmed' | 'disputed' | 'unreviewed'

// ─── Dagre layout ────────────────────────────────────────────────────────────

function getLayoutedElements(nodes: Node[], edges: Edge[], direction = 'TB') {
  const g = new dagre.graphlib.Graph()
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph({ rankdir: direction, nodesep: 60, ranksep: 80 })

  nodes.forEach((n) => g.setNode(n.id, { width: 200, height: 70 }))
  edges.forEach((e) => g.setEdge(e.source, e.target))
  dagre.layout(g)

  return {
    nodes: nodes.map((n) => {
      const pos = g.node(n.id)
      return { ...n, position: { x: pos.x - 100, y: pos.y - 35 } }
    }),
    edges,
  }
}

// ─── Edge styles ─────────────────────────────────────────────────────────────

function getEdgeStyle(edgeType: string): Partial<Edge> {
  switch (edgeType) {
    case 'supports':
      return { style: { stroke: '#34d399', strokeWidth: 2 }, animated: true }
    case 'contradicts':
      return { style: { stroke: '#9ca3af', strokeWidth: 2, strokeDasharray: '5,5' } }
    case 'leads_to':
      return {
        style: { stroke: '#3FAF7A', strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#3FAF7A' },
      }
    case 'caused_by':
      return { style: { stroke: '#d1d5db', strokeWidth: 1.5, strokeDasharray: '3,3' } }
    default:
      return { style: { stroke: '#e5e7eb', strokeWidth: 1 } }
  }
}

// ─── Custom node component ───────────────────────────────────────────────────

function MemoryGraphNode({ data }: NodeProps) {
  const { nodeType, summary, confidence, consultantStatus } = data as {
    nodeType: string
    summary: string
    confidence: number
    consultantStatus: string | null
  }

  let bgColor = 'bg-gray-400'
  let textColor = 'text-white'
  let extraClasses = ''

  if (nodeType === 'fact') {
    bgColor = 'bg-emerald-400'
  } else if (nodeType === 'belief') {
    bgColor = 'bg-[#0A1E2F]'
  } else if (nodeType === 'insight') {
    bgColor = 'bg-gray-400'
  }

  // Consultant status visual
  if (consultantStatus === 'confirmed') {
    extraClasses = 'ring-2 ring-brand-primary ring-offset-1'
  } else if (consultantStatus === 'disputed') {
    extraClasses = 'border-2 border-dashed border-gray-400'
  }

  const opacity = nodeType === 'belief' ? Math.max(0.4, confidence) : 1

  return (
    <div className="relative">
      <Handle type="target" position={Position.Top} className="!bg-transparent !border-0 !w-0 !h-0" />
      <div
        className={`rounded-lg px-3 py-2 shadow-sm cursor-pointer min-w-[80px] max-w-[200px] ${bgColor} ${textColor} ${extraClasses}`}
        style={{ opacity }}
      >
        <p className="text-[10px] leading-snug line-clamp-2">{summary}</p>
        {nodeType !== 'fact' && (
          <p className="text-[9px] opacity-80 mt-0.5">{Math.round(confidence * 100)}%</p>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-transparent !border-0 !w-0 !h-0" />
    </div>
  )
}

const nodeTypes = { memoryNode: MemoryGraphNode }

// ─── Build flow elements ─────────────────────────────────────────────────────

function buildElements(
  graphData: IntelGraphResponse | null,
  filter: NodeFilter,
  consultantFilter: ConsultantFilter,
) {
  if (!graphData) return { nodes: [], edges: [] }

  let filtered = graphData.nodes
  if (filter !== 'all') filtered = filtered.filter((n) => n.node_type === filter)

  if (consultantFilter === 'confirmed')
    filtered = filtered.filter((n) => n.consultant_status === 'confirmed')
  else if (consultantFilter === 'disputed')
    filtered = filtered.filter((n) => n.consultant_status === 'disputed')
  else if (consultantFilter === 'unreviewed')
    filtered = filtered.filter((n) => !n.consultant_status)

  const ids = new Set(filtered.map((n) => n.id))

  const flowNodes: Node[] = filtered.map((n) => ({
    id: n.id,
    type: 'memoryNode',
    data: {
      nodeType: n.node_type,
      summary: n.summary,
      confidence: n.confidence,
      consultantStatus: n.consultant_status,
    },
    position: { x: 0, y: 0 },
  }))

  const flowEdges: Edge[] = graphData.edges
    .filter((e) => ids.has(e.from_node_id) && ids.has(e.to_node_id))
    .map((e) => ({
      id: e.id,
      source: e.from_node_id,
      target: e.to_node_id,
      ...getEdgeStyle(e.edge_type),
    }))

  return getLayoutedElements(flowNodes, flowEdges)
}

// ─── KnowledgeTab ────────────────────────────────────────────────────────────

export function KnowledgeTab({ projectId, data: vizData }: KnowledgeTabProps) {
  const { data: swrGraphData, isLoading: swrLoading, mutate } = useIntelGraph(projectId)
  const [filter, setFilter] = useState<NodeFilter>('all')
  const [consultantFilter, setConsultantFilter] = useState<ConsultantFilter>('all')
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [showAddBelief, setShowAddBelief] = useState(false)

  // Use SWR data, fallback to vizData — memoize to prevent infinite re-render
  const graphData: IntelGraphResponse | null = useMemo(() => {
    if (swrGraphData) return swrGraphData
    if (!vizData) return null
    return {
      nodes: vizData.nodes.map((n) => ({
        ...n,
        content: n.summary,
        is_active: true,
        consultant_status: null,
        consultant_note: null,
        consultant_status_at: null,
        hypothesis_status: null,
        linked_entity_type: n.linked_entity_type ?? null,
        linked_entity_id: null,
      })),
      edges: vizData.edges,
      stats: vizData.stats as unknown as Record<string, number>,
    }
  }, [swrGraphData, vizData])
  const isLoading = swrLoading && !vizData

  const { nodes: flowNodes, edges: flowEdges } = useMemo(
    () => buildElements(graphData, filter, consultantFilter),
    [graphData, filter, consultantFilter],
  )

  const [nodes, setNodes, onNodesChange] = useNodesState(flowNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(flowEdges)

  useEffect(() => {
    setNodes(flowNodes)
    setEdges(flowEdges)
  }, [flowNodes, flowEdges, setNodes, setEdges])

  const handleNodeClick = useCallback((_: unknown, node: Node) => {
    setSelectedNodeId(node.id)
  }, [])

  const handleFeedback = useCallback(
    async (nodeId: string, action: 'confirm' | 'dispute' | 'archive', note?: string) => {
      try {
        await submitNodeFeedback(projectId, nodeId, action, note)
        mutate()
      } catch {
        // feedback failed silently
      }
    },
    [projectId, mutate],
  )

  const handleBeliefCreated = useCallback(
    (_newNode: IntelGraphNode) => {
      mutate()
      setShowAddBelief(false)
    },
    [mutate],
  )

  const selectedNode = graphData?.nodes.find((n) => n.id === selectedNodeId) ?? null

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-brand-primary" />
      </div>
    )
  }

  if (!graphData || graphData.nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <p className="text-sm text-text-placeholder mb-2">
            No knowledge graph data yet.
          </p>
          <p className="text-xs text-text-placeholder">
            Process signals to build the knowledge graph, or add beliefs manually.
          </p>
          <button
            onClick={() => setShowAddBelief(true)}
            className="mt-4 inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-brand-primary hover:bg-[#25785A] rounded-xl transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add Belief
          </button>
          {showAddBelief && (
            <AddBeliefModal
              projectId={projectId}
              onCreated={handleBeliefCreated}
              onClose={() => setShowAddBelief(false)}
            />
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-full">
      {/* Graph area */}
      <div className={`relative ${selectedNode ? 'w-[70%]' : 'w-full'} h-full transition-all`}>
        {/* Filter bar */}
        <div className="absolute top-3 left-3 z-10 flex items-center gap-2 bg-white/90 backdrop-blur rounded-lg px-3 py-1.5 shadow-sm border border-border">
          {(['all', 'fact', 'belief', 'insight'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
                filter === f
                  ? 'bg-[#E8F5E9] text-[#25785A]'
                  : 'text-[#666666] hover:text-text-body'
              }`}
            >
              {f === 'all' ? 'All' : f.charAt(0).toUpperCase() + f.slice(1) + 's'}
            </button>
          ))}
          <div className="w-px h-4 bg-border mx-1" />
          {(['all', 'confirmed', 'disputed', 'unreviewed'] as const).map((cf) => (
            <button
              key={cf}
              onClick={() => setConsultantFilter(cf)}
              className={`px-2 py-1 rounded text-[11px] font-medium transition-colors ${
                consultantFilter === cf
                  ? 'bg-[#E8F5E9] text-[#25785A]'
                  : 'text-[#666666] hover:text-text-body'
              }`}
            >
              {cf.charAt(0).toUpperCase() + cf.slice(1)}
            </button>
          ))}
        </div>

        {/* Add Belief button */}
        <div className="absolute top-3 right-3 z-10">
          <button
            onClick={() => setShowAddBelief(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-medium text-white bg-brand-primary hover:bg-[#25785A] rounded-lg shadow-sm transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            Add Belief
          </button>
        </div>

        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={handleNodeClick}
          nodeTypes={nodeTypes}
          fitView
          minZoom={0.2}
          maxZoom={2}
          proOptions={{ hideAttribution: true }}
        >
          <Background />
          <Controls position="bottom-left" />
          <MiniMap
            position="bottom-right"
            nodeColor={(node) => {
              const nt = (node.data as Record<string, unknown>)?.nodeType
              if (nt === 'fact') return '#34d399'
              if (nt === 'belief') return '#0A1E2F'
              return '#9ca3af'
            }}
            maskColor="rgba(255,255,255,0.8)"
          />
        </ReactFlow>
      </div>

      {/* Node detail slide-in */}
      {selectedNode && (
        <div className="w-[30%] h-full border-l border-border bg-white overflow-y-auto">
          <NodeDetailPanel
            projectId={projectId}
            node={selectedNode}
            onClose={() => setSelectedNodeId(null)}
            onFeedback={handleFeedback}
          />
        </div>
      )}

      {/* Add Belief Modal */}
      {showAddBelief && (
        <AddBeliefModal
          projectId={projectId}
          onCreated={handleBeliefCreated}
          onClose={() => setShowAddBelief(false)}
        />
      )}
    </div>
  )
}
