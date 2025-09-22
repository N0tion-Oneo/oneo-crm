/**
 * WorkflowCanvas Component
 * Simple React Flow wrapper for workflow visualization
 */

import React, { useCallback, useRef } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Connection,
  useNodesState,
  useEdgesState,
  addEdge,
  Background,
  Controls,
  MiniMap,
  ReactFlowProvider,
  ReactFlowInstance,
  NodeChange,
  EdgeChange,
  applyNodeChanges,
  applyEdgeChanges,
} from 'reactflow';
import 'reactflow/dist/style.css';
import WorkflowNode from './WorkflowNode';
import { WorkflowDefinition, WorkflowNode as WorkflowNodeType, WorkflowEdge } from '../types';
import { WorkflowNodeType as NodeType } from '../../types';

const nodeTypes = {
  workflow: WorkflowNode,
};

interface WorkflowCanvasProps {
  definition: WorkflowDefinition;
  onNodesChange: (nodes: WorkflowNodeType[]) => void;
  onEdgesChange: (edges: WorkflowEdge[]) => void;
  onNodeSelect: (nodeId: string | null) => void;
  onNodeAdd: (node: WorkflowNodeType) => void;
  selectedNodeId: string | null;
  nodeConfigs?: Record<string, any>;
}

function WorkflowCanvasInner({
  definition,
  onNodesChange,
  onEdgesChange,
  onNodeSelect,
  onNodeAdd,
  selectedNodeId,
  nodeConfigs = {},
}: WorkflowCanvasProps) {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [reactFlowInstance, setReactFlowInstance] = React.useState<ReactFlowInstance | null>(null);

  // Convert workflow nodes to React Flow nodes with config
  const flowNodes: Node[] = definition.nodes.map(node => ({
    id: node.id,
    type: 'workflow',
    position: node.position,
    data: {
      ...node.data,
      nodeType: node.type,
      config: nodeConfigs[node.id] || node.data.config,
    },
    selected: node.id === selectedNodeId,
  }));

  // Convert workflow edges to React Flow edges
  const flowEdges: Edge[] = definition.edges.map(edge => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    sourceHandle: edge.sourceHandle || undefined,
    targetHandle: edge.targetHandle || undefined,
    label: edge.label,
  }));

  const [nodes, setNodes, onNodesChangeInternal] = useNodesState(flowNodes);
  const [edges, setEdges, onEdgesChangeInternal] = useEdgesState(flowEdges);

  // Track if we're currently dragging
  const isDraggingRef = useRef(false);

  // Handle nodes change - only update parent on specific events
  const handleNodesChange = useCallback((changes: NodeChange[]) => {
    // Apply changes to local state immediately for smooth interaction
    onNodesChangeInternal(changes);

    // Check what type of changes occurred
    const hasPositionChange = changes.some(change => change.type === 'position');
    const hasDragEnd = changes.some(change =>
      change.type === 'position' && 'dragging' in change && change.dragging === false
    );
    const hasDragStart = changes.some(change =>
      change.type === 'position' && 'dragging' in change && change.dragging === true
    );
    const hasRemove = changes.some(change => change.type === 'remove');
    const hasSelect = changes.some(change => change.type === 'select');

    // Track dragging state
    if (hasDragStart) {
      isDraggingRef.current = true;
    }

    // Only update parent when:
    // 1. Drag ends (position finalized)
    // 2. Node is removed
    // 3. Selection changes (but not during drag)
    if (hasDragEnd || hasRemove || (hasSelect && !isDraggingRef.current)) {
      if (hasDragEnd) {
        isDraggingRef.current = false;
      }

      // Get the current nodes after changes
      setNodes((currentNodes) => {
        const workflowNodes: WorkflowNodeType[] = currentNodes.map(node => ({
          id: node.id,
          type: node.data.nodeType as NodeType,
          position: node.position,
          data: node.data,
        }));
        onNodesChange(workflowNodes);
        return currentNodes;
      });
    }
  }, [onNodesChangeInternal, onNodesChange, setNodes]);

  // Handle edges change
  const handleEdgesChange = useCallback((changes: EdgeChange[]) => {
    // Apply changes locally first
    onEdgesChangeInternal(changes);

    // Update parent with new edges
    setEdges((currentEdges) => {
      const workflowEdges: WorkflowEdge[] = currentEdges.map(edge => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        sourceHandle: edge.sourceHandle || undefined,
        targetHandle: edge.targetHandle || undefined,
        label: typeof edge.label === 'string' ? edge.label : undefined,
      }));
      onEdgesChange(workflowEdges);
      return currentEdges;
    });
  }, [onEdgesChangeInternal, onEdgesChange, setEdges]);

  // Handle new connections
  const onConnect = useCallback(
    (params: Connection) => {
      const newEdge = {
        ...params,
        id: `edge-${Date.now()}`,
      };
      setEdges((eds) => addEdge(newEdge, eds));

      // Update parent
      const workflowEdge: WorkflowEdge = {
        id: newEdge.id,
        source: params.source!,
        target: params.target!,
        sourceHandle: params.sourceHandle || undefined,
        targetHandle: params.targetHandle || undefined,
      };
      onEdgesChange([...definition.edges, workflowEdge]);
    },
    [setEdges, definition.edges, onEdgesChange]
  );

  // Handle node click
  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      onNodeSelect(node.id);
    },
    [onNodeSelect]
  );

  // Handle pane click (deselect)
  const onPaneClick = useCallback(() => {
    onNodeSelect(null);
  }, [onNodeSelect]);

  // Handle drop
  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      if (!reactFlowInstance || !reactFlowWrapper.current) return;

      const reactFlowBounds = reactFlowWrapper.current.getBoundingClientRect();
      const data = event.dataTransfer.getData('application/reactflow');

      if (!data) return;

      try {
        const nodeData = JSON.parse(data);

        // Calculate position
        const position = reactFlowInstance.project({
          x: event.clientX - reactFlowBounds.left,
          y: event.clientY - reactFlowBounds.top,
        });

        // Create new node
        const newNode: WorkflowNodeType = {
          id: `${nodeData.type}-${Date.now()}`,
          type: nodeData.type,
          position,
          data: {
            label: nodeData.label,
            icon: nodeData.icon,
          },
        };

        onNodeAdd(newNode);
      } catch (err) {
        console.error('Failed to parse dropped node data:', err);
      }
    },
    [reactFlowInstance, onNodeAdd]
  );

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  // Sync nodes and edges when definition changes from parent
  React.useEffect(() => {
    // Only update if not currently dragging
    if (!isDraggingRef.current) {
      setNodes(flowNodes);
      setEdges(flowEdges);
    }
  }, [definition, setNodes, setEdges]);

  return (
    <div className="h-full w-full" ref={reactFlowWrapper}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={handleNodesChange}
        onEdgesChange={handleEdgesChange}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        onInit={setReactFlowInstance}
        onDrop={onDrop}
        onDragOver={onDragOver}
        nodeTypes={nodeTypes}
        fitView
        deleteKeyCode={['Delete', 'Backspace']}
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  );
}

export function WorkflowCanvas(props: WorkflowCanvasProps) {
  return (
    <ReactFlowProvider>
      <WorkflowCanvasInner {...props} />
    </ReactFlowProvider>
  );
}