/**
 * GraphTab - Interactive Knowledge Graph
 *
 * Uses @xyflow/react + dagre for layout to render the memory knowledge graph.
 * Nodes colored by type (fact/belief/insight), edges styled by relationship type.
 * Click a node to see details in a side panel.
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
import { X } from 'lucide-react'
import type { MemoryVisualizationResponse, MemoryNodeViz, MemoryEdgeViz } from '@/lib/api'

interface GraphTabProps {
  data: MemoryVisualizationResponse | null
}

type NodeFilter = 'all' | 'fact' | 'belief' | 'insight'

// Dagre layout
function getLayoutedElements(
  nodes: Node[],
  edges: Edge[],
  direction: string = 'TB'
) {
  const dagreGraph = new dagre.graphlib.Graph()
  dagreGraph.setDefaultEdgeLabel(() => ({}))
  dagreGraph.setGraph({ rankdir: direction, nodesep: 60, ranksep: 80 })

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: 200, height: 70 })
  })

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target)
  })

  dagre.layout(dagreGraph)

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id)
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - 100,
        y: nodeWithPosition.y - 35,
      },
    }
  })

  return { nodes: layoutedNodes, edges }
}

// Edge styles by type
function getEdgeStyle(edgeType: string): Partial<Edge> {
  switch (edgeType) {
    case 'supports':
      return {
        style: { stroke: '#34d399', strokeWidth: 2 },
        animated: true,
      }
    case 'contradicts':
      return {
        style: { stroke: '#9ca3af', strokeWidth: 2, strokeDasharray: '5,5' },
      }
    case 'caused_by':
      return {
        style: { stroke: '#d1d5db', strokeWidth: 1.5, strokeDasharray: '3,3' },
      }
    case 'leads_to':
      return {
        style: { stroke: '#14b8a6', strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#14b8a6' },
      }
    case 'supersedes':
    case 'related_to':
    default:
      return {
        style: { stroke: '#e5e7eb', strokeWidth: 1 },
      }
  }
}

// Convert API data to React Flow elements
function buildFlowElements(
  vizNodes: MemoryNodeViz[],
  vizEdges: MemoryEdgeViz[],
  filter: NodeFilter,
  showLabels: boolean,
  showConfidence: boolean
) {
  const filteredNodes = filter === 'all'
    ? vizNodes
    : vizNodes.filter((n) => n.node_type === filter)

  const filteredNodeIds = new Set(filteredNodes.map((n) => n.id))

  const flowNodes: Node[] = filteredNodes.map((n) => ({
    id: n.id,
    type: 'memoryNode',
    data: {
      nodeType: n.node_type,
      summary: n.summary,
      confidence: n.confidence,
      showLabels,
      showConfidence,
    },
    position: { x: 0, y: 0 },
  }))

  const flowEdges: Edge[] = vizEdges
    .filter((e) => filteredNodeIds.has(e.from_node_id) && filteredNodeIds.has(e.to_node_id))
    .map((e) => ({
      id: e.id,
      source: e.from_node_id,
      target: e.to_node_id,
      label: undefined,
      ...getEdgeStyle(e.edge_type),
    }))

  return getLayoutedElements(flowNodes, flowEdges)
}

// Custom node component
function MemoryGraphNode({ data }: NodeProps) {
  const { nodeType, summary, confidence, showLabels, showConfidence } = data as {
    nodeType: string
    summary: string
    confidence: number
    showLabels: boolean
    showConfidence: boolean
  }

  let bgColor = 'bg-gray-400'
  let textColor = 'text-white'
  let shape = 'rounded-lg'

  if (nodeType === 'fact') {
    bgColor = 'bg-emerald-400'
    shape = 'rounded-full'
  } else if (nodeType === 'belief') {
    bgColor = 'bg-teal-500'
  } else if (nodeType === 'insight') {
    bgColor = 'bg-gray-400'
    shape = 'rounded-lg rotate-45'
  }

  // Opacity by confidence for beliefs
  const opacity = nodeType === 'belief'
    ? Math.max(0.3, confidence)
    : 1

  return (
    <div className="relative">
      <Handle type="target" position={Position.Top} className="!bg-transparent !border-0 !w-0 !h-0" />
      <div
        className={`${shape} px-3 py-2 shadow-sm border border-white/20 cursor-pointer min-w-[80px] max-w-[200px] ${bgColor} ${textColor}`}
        style={{ opacity }}
      >
        {nodeType === 'insight' ? (
          <div className="-rotate-45 max-w-[140px]">
            {showLabels && (
              <p className="text-[10px] leading-snug">{summary}</p>
            )}
            {showConfidence && (
              <p className="text-[9px] opacity-80 mt-0.5">{Math.round(confidence * 100)}%</p>
            )}
          </div>
        ) : (
          <>
            {showLabels && (
              <p className="text-[10px] leading-snug">{summary}</p>
            )}
            {showConfidence && nodeType !== 'fact' && (
              <p className="text-[9px] opacity-80 mt-0.5">{Math.round(confidence * 100)}%</p>
            )}
          </>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-transparent !border-0 !w-0 !h-0" />
    </div>
  )
}

const nodeTypes = { memoryNode: MemoryGraphNode }

export function GraphTab({ data }: GraphTabProps) {
  const [filter, setFilter] = useState<NodeFilter>('all')
  const [showLabels, setShowLabels] = useState(true)
  const [showConfidence, setShowConfidence] = useState(true)
  const [selectedNode, setSelectedNode] = useState<MemoryNodeViz | null>(null)
  const [showTip, setShowTip] = useState(() => {
    if (typeof window === 'undefined') return false
    return !localStorage.getItem('memory-graph-tip-dismissed')
  })

  const { nodes: flowNodes, edges: flowEdges } = useMemo(() => {
    if (!data) return { nodes: [], edges: [] }
    return buildFlowElements(data.nodes, data.edges, filter, showLabels, showConfidence)
  }, [data, filter, showLabels, showConfidence])

  const [nodes, setNodes, onNodesChange] = useNodesState(flowNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(flowEdges)

  // Update when flow elements change
  useEffect(() => {
    setNodes(flowNodes)
    setEdges(flowEdges)
  }, [flowNodes, flowEdges, setNodes, setEdges])

  const handleNodeClick = useCallback((_: any, node: Node) => {
    if (!data) return
    const vizNode = data.nodes.find((n) => n.id === node.id)
    setSelectedNode(vizNode || null)
  }, [data])

  const dismissTip = useCallback(() => {
    setShowTip(false)
    localStorage.setItem('memory-graph-tip-dismissed', '1')
  }, [])

  if (!data || data.nodes.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-sm text-ui-supportText">No graph data yet. Process signals to build the knowledge graph.</p>
      </div>
    )
  }

  // Compute connected nodes for selected node detail
  const connectedNodes = selectedNode && data
    ? data.edges
        .filter((e) => e.from_node_id === selectedNode.id || e.to_node_id === selectedNode.id)
        .map((e) => {
          const otherId = e.from_node_id === selectedNode.id ? e.to_node_id : e.from_node_id
          const otherNode = data.nodes.find((n) => n.id === otherId)
          return otherNode ? { node: otherNode, edgeType: e.edge_type } : null
        })
        .filter(Boolean) as { node: MemoryNodeViz; edgeType: string }[]
    : []

  return (
    <div className="relative" style={{ height: '500px' }}>
      {/* Filter bar */}
      <div className="absolute top-2 left-2 z-10 flex items-center gap-2 bg-white/90 backdrop-blur rounded-lg px-3 py-1.5 shadow-sm border border-gray-200">
        {(['all', 'fact', 'belief', 'insight'] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
              filter === f
                ? 'bg-brand-teal/10 text-brand-teal'
                : 'text-ui-supportText hover:text-ui-headingDark'
            }`}
          >
            {f === 'all' ? 'All' : f.charAt(0).toUpperCase() + f.slice(1) + 's'}
          </button>
        ))}
        <div className="w-px h-4 bg-gray-200 mx-1" />
        <label className="flex items-center gap-1.5 text-[11px] text-ui-supportText cursor-pointer">
          <input
            type="checkbox"
            checked={showLabels}
            onChange={(e) => setShowLabels(e.target.checked)}
            className="rounded text-brand-teal"
          />
          Labels
        </label>
        <label className="flex items-center gap-1.5 text-[11px] text-ui-supportText cursor-pointer">
          <input
            type="checkbox"
            checked={showConfidence}
            onChange={(e) => setShowConfidence(e.target.checked)}
            className="rounded text-brand-teal"
          />
          Confidence
        </label>
      </div>

      {/* Educational tooltip */}
      {showTip && (
        <div className="absolute top-14 left-2 z-10 bg-white rounded-lg shadow-lg border border-gray-200 px-3 py-2 max-w-xs">
          <p className="text-[11px] text-ui-bodyText mb-1.5">
            This is your AI&apos;s knowledge graph. <span className="text-emerald-500 font-medium">Green = facts</span>, <span className="text-teal-500 font-medium">Blue = beliefs</span>, <span className="text-gray-400 font-medium">Gray = insights</span>.
          </p>
          <button
            onClick={dismissTip}
            className="text-[10px] text-brand-teal font-medium hover:underline"
          >
            Got it, don&apos;t show again
          </button>
        </div>
      )}

      {/* React Flow graph */}
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
            const nt = (node.data as any)?.nodeType
            if (nt === 'fact') return '#34d399'
            if (nt === 'belief') return '#14b8a6'
            return '#9ca3af'
          }}
          maskColor="rgba(255,255,255,0.8)"
        />
      </ReactFlow>

      {/* Node detail panel */}
      {selectedNode && (
        <div className="absolute top-0 right-0 w-72 h-full bg-white border-l border-gray-200 shadow-lg z-20 overflow-y-auto">
          <div className="p-4">
            <div className="flex items-center justify-between mb-3">
              <span className={`text-[11px] font-semibold uppercase tracking-wide ${
                selectedNode.node_type === 'fact' ? 'text-emerald-600' :
                selectedNode.node_type === 'belief' ? 'text-teal-600' : 'text-gray-500'
              }`}>
                {selectedNode.node_type}
              </span>
              <button
                onClick={() => setSelectedNode(null)}
                className="p-1 rounded hover:bg-gray-100 text-ui-supportText"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-sm font-medium text-ui-headingDark mb-2">
              {selectedNode.summary}
            </p>

            <p className="text-[12px] text-ui-bodyText mb-3 whitespace-pre-wrap">
              {selectedNode.content}
            </p>

            <div className="space-y-1.5 text-[11px] text-ui-supportText mb-4">
              {selectedNode.node_type !== 'fact' && (
                <p>Confidence: <span className="font-medium text-ui-bodyText">{Math.round(selectedNode.confidence * 100)}%</span></p>
              )}
              {selectedNode.belief_domain && (
                <p>Domain: <span className="font-medium text-ui-bodyText">{selectedNode.belief_domain.replace('_', ' ')}</span></p>
              )}
              {selectedNode.insight_type && (
                <p>Type: <span className="font-medium text-ui-bodyText">{selectedNode.insight_type}</span></p>
              )}
              {selectedNode.source_type && (
                <p>Source: <span className="font-medium text-ui-bodyText">{selectedNode.source_type}</span></p>
              )}
              <p>Created: <span className="font-medium text-ui-bodyText">{new Date(selectedNode.created_at).toLocaleDateString()}</span></p>
            </div>

            {/* Connected nodes */}
            {connectedNodes.length > 0 && (
              <div>
                <h6 className="text-[11px] font-semibold text-ui-headingDark uppercase tracking-wide mb-2">
                  Connected ({connectedNodes.length})
                </h6>
                <div className="space-y-1.5">
                  {connectedNodes.map(({ node, edgeType }) => (
                    <button
                      key={node.id}
                      onClick={() => setSelectedNode(node)}
                      className="w-full text-left bg-ui-background rounded px-2.5 py-2 hover:bg-gray-100 transition-colors"
                    >
                      <div className="flex items-center gap-1.5 mb-0.5">
                        <span className={`text-[9px] font-semibold uppercase ${
                          node.node_type === 'fact' ? 'text-emerald-600' :
                          node.node_type === 'belief' ? 'text-teal-600' : 'text-gray-500'
                        }`}>
                          {node.node_type}
                        </span>
                        <span className="text-[9px] text-ui-supportText">{edgeType}</span>
                      </div>
                      <p className="text-[11px] text-ui-bodyText truncate">{node.summary}</p>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
