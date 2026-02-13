'use client'

import { useState, useCallback, useMemo, useEffect } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  MarkerType,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import dagre from 'dagre'
import { Loader2 } from 'lucide-react'
import { getDataEntityGraph } from '@/lib/api'
import { ERDEntityNode } from './ERDEntityNode'
import type { ERDEntityNodeData } from './ERDEntityNode'
import type { DataEntityGraphData } from '@/types/workspace'

interface DataEntityERDProps {
  projectId: string
}

// Node types registered with ReactFlow
const nodeTypes = {
  erdEntity: ERDEntityNode,
}

// Edge style config by type
const EDGE_STYLES: Record<string, { stroke: string; strokeDasharray?: string }> = {
  uses: { stroke: '#3FAF7A' },
  derived_from: { stroke: '#666666', strokeDasharray: '5 3' },
  depends_on: { stroke: '#0A1E2F' },
}

// Dagre layout
function getLayoutedElements(
  nodes: Node[],
  edges: Edge[],
  direction: string = 'LR'
) {
  const dagreGraph = new dagre.graphlib.Graph()
  dagreGraph.setDefaultEdgeLabel(() => ({}))
  dagreGraph.setGraph({ rankdir: direction, nodesep: 60, ranksep: 120 })

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: 220, height: 140 })
  })

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target)
  })

  dagre.layout(dagreGraph)

  const layoutedNodes = nodes.map((node) => {
    const dagreNode = dagreGraph.node(node.id)
    return {
      ...node,
      position: {
        x: dagreNode.x - 110,
        y: dagreNode.y - 70,
      },
    }
  })

  return { nodes: layoutedNodes, edges }
}

function buildGraph(graphData: DataEntityGraphData): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = graphData.nodes.map((n) => ({
    id: n.id,
    type: 'erdEntity',
    position: { x: 0, y: 0 },
    data: {
      name: n.name,
      entity_category: n.entity_category,
      fields: n.fields,
      field_count: n.field_count,
      workflow_step_count: n.workflow_step_count,
    } satisfies ERDEntityNodeData,
  }))

  // Only include edges where both source and target are in node set
  const nodeIds = new Set(graphData.nodes.map((n) => n.id))
  const edges: Edge[] = graphData.edges
    .filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target))
    .map((e) => {
      const style = EDGE_STYLES[e.edge_type] || EDGE_STYLES.uses
      return {
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.label || undefined,
        type: 'default',
        style: {
          stroke: style.stroke,
          strokeWidth: 1.5,
          strokeDasharray: style.strokeDasharray,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: style.stroke,
          width: 16,
          height: 16,
        },
        labelStyle: { fontSize: 10, fill: '#666666' },
      }
    })

  return getLayoutedElements(nodes, edges)
}

export function DataEntityERD({ projectId }: DataEntityERDProps) {
  const [graphData, setGraphData] = useState<DataEntityGraphData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])

  const loadGraph = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)
      const data = await getDataEntityGraph(projectId)
      setGraphData(data)
    } catch (err) {
      console.error('Failed to load data entity graph:', err)
      setError('Failed to load relationship diagram')
    } finally {
      setIsLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    loadGraph()
  }, [loadGraph])

  useEffect(() => {
    if (!graphData || graphData.nodes.length === 0) return
    const { nodes: layoutedNodes, edges: layoutedEdges } = buildGraph(graphData)
    setNodes(layoutedNodes)
    setEdges(layoutedEdges)
  }, [graphData, setNodes, setEdges])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-5 h-5 animate-spin text-[#3FAF7A]" />
        <span className="ml-2 text-[12px] text-[#999999]">Loading diagram...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-[12px] text-[#999999]">{error}</p>
        <button
          onClick={loadGraph}
          className="mt-2 text-[12px] text-[#3FAF7A] hover:text-[#25785A]"
        >
          Retry
        </button>
      </div>
    )
  }

  if (!graphData || graphData.nodes.length === 0) {
    return (
      <p className="text-[12px] text-[#999999] italic py-4 text-center">
        No data entities to visualize
      </p>
    )
  }

  return (
    <div className="h-[400px] bg-[#F4F4F4] rounded-xl border border-[#E5E5E5] overflow-hidden">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.3}
        maxZoom={1.5}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#E5E5E5" gap={20} />
        <Controls
          showInteractive={false}
          className="!bg-white !border-[#E5E5E5] !rounded-lg !shadow-sm"
        />
      </ReactFlow>

      {/* Legend */}
      <div className="absolute bottom-3 left-3 bg-white/90 rounded-lg border border-[#E5E5E5] px-3 py-2 flex gap-4 text-[10px] text-[#666666]">
        <span className="flex items-center gap-1">
          <span className="w-3 h-0.5 bg-[#3FAF7A] inline-block" /> uses
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-0.5 border-t border-dashed border-[#666666] inline-block" /> derived
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-0.5 bg-[#0A1E2F] inline-block" /> depends
        </span>
      </div>
    </div>
  )
}
