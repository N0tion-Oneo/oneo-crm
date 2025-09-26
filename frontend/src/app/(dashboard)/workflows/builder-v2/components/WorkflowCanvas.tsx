/**
 * WorkflowCanvas Component
 * Simple React Flow wrapper for workflow visualization
 */

import React, { useCallback, useRef, useState } from 'react';
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
  BackgroundVariant,
  ConnectionMode as RFConnectionMode,
} from 'reactflow';
import 'reactflow/dist/style.css';
import WorkflowNode from './WorkflowNode';
import { WorkflowDefinition, WorkflowNode as WorkflowNodeType, WorkflowEdge } from '../types';
import { WorkflowNodeType as NodeType } from '../../types';
import { useCanvasSettings } from '../hooks/useCanvasSettings';
import { useKeyboardShortcuts } from '../hooks/useKeyboardShortcuts';
import { CanvasSettings } from './CanvasSettings';

const nodeTypes = {
  workflow: WorkflowNode,
};

interface WorkflowCanvasProps {
  definition: WorkflowDefinition;
  onNodesChange: (nodes: WorkflowNodeType[]) => void;
  onEdgesChange: (edges: WorkflowEdge[]) => void;
  onNodeSelect: (nodeId: string | null) => void;
  onNodeAdd: (node: WorkflowNodeType) => void;
  onNodeDoubleClick?: (nodeId: string) => void;
  selectedNodeId: string | null;
  nodeConfigs?: Record<string, any>;
}

function WorkflowCanvasInner({
  definition,
  onNodesChange,
  onEdgesChange,
  onNodeSelect,
  onNodeAdd,
  onNodeDoubleClick,
  selectedNodeId,
  nodeConfigs = {},
}: WorkflowCanvasProps) {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [reactFlowInstance, setReactFlowInstance] = React.useState<ReactFlowInstance | null>(null);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);

  // Canvas settings
  const {
    settings,
    updateSetting,
    toggleSetting,
    resetSettings
  } = useCanvasSettings();

  // Keyboard shortcuts
  useKeyboardShortcuts({
    onToggleMiniMap: () => toggleSetting('showMiniMap'),
    onToggleGrid: () => toggleSetting('snapToGrid'),
    onToggleBackground: () => toggleSetting('showBackground'),
    onToggleSettings: () => setIsSettingsOpen(prev => !prev),
  });

  // Convert workflow definition to React Flow format
  // Use useMemo to prevent recreating on every render
  const initialNodes = React.useMemo(() =>
    definition.nodes.map(node => ({
      id: node.id,
      type: 'workflow',
      position: node.position,
      data: {
        ...node.data,
        nodeType: node.type,
        config: nodeConfigs[node.id] || node.data.config,
      },
      selected: node.id === selectedNodeId,
    })), []);  // Empty deps - only compute once on mount

  const initialEdges = React.useMemo(() =>
    definition.edges.map(edge => ({
      id: edge.id,
      type: 'smoothstep',
      source: edge.source,
      target: edge.target,
      sourceHandle: edge.sourceHandle || undefined,
      targetHandle: edge.targetHandle || undefined,
      label: edge.label,
      deletable: true,
      focusable: true,
    })), []); // Empty deps - only compute once on mount

  // Initialize nodes and edges state with initial values
  const [nodes, setNodes, onNodesChangeInternal] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChangeInternal] = useEdgesState(initialEdges);

  // Track if we're currently dragging
  const isDraggingRef = useRef(false);
  const pendingUpdateRef = useRef(false);

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

    // Handle node removal immediately
    if (hasRemove) {
      // Get the IDs of nodes being removed
      const removedNodeIds = changes
        .filter(change => change.type === 'remove')
        .map(change => change.id);

      // Update parent immediately with filtered nodes
      setTimeout(() => {
        const remainingNodes = nodes.filter(node => !removedNodeIds.includes(node.id));
        const workflowNodes: WorkflowNodeType[] = remainingNodes.map(node => ({
          id: node.id,
          type: node.data.nodeType as NodeType,
          position: node.position,
          data: node.data,
        }));
        onNodesChange(workflowNodes);
      }, 0);
      return; // Don't set pending update for removes
    }

    // For other changes, mark pending update
    if (hasDragEnd || (hasSelect && !isDraggingRef.current)) {
      if (hasDragEnd) {
        isDraggingRef.current = false;
      }

      // Mark that we need to update parent
      pendingUpdateRef.current = true;
    }
  }, [onNodesChangeInternal, nodes, onNodesChange]);

  // Track if we're syncing from parent to prevent loops
  const isSyncingFromParentRef = useRef(false);

  // Update parent when nodes change and we have a pending update
  React.useEffect(() => {
    if (pendingUpdateRef.current && !isSyncingFromParentRef.current) {
      pendingUpdateRef.current = false;
      const workflowNodes: WorkflowNodeType[] = nodes.map(node => ({
        id: node.id,
        type: node.data.nodeType as NodeType,
        position: node.position,
        data: node.data,
      }));
      onNodesChange(workflowNodes);
    }
  }, [nodes, onNodesChange]);

  // Handle edges change
  const handleEdgesChange = useCallback((changes: EdgeChange[]) => {
    // Apply changes locally first
    onEdgesChangeInternal(changes);

    // Check for edge removal or selection changes
    const hasRemoval = changes.some(change => change.type === 'remove');
    const hasSelection = changes.some(change => change.type === 'select');

    // Handle selection changes
    if (hasSelection && !hasRemoval) {
      const selectChange = changes.find(change => change.type === 'select');
      if (selectChange && 'selected' in selectChange) {
        if (selectChange.selected) {
          setSelectedEdgeId(selectChange.id);
        } else {
          setSelectedEdgeId(null);
        }
      }
    }

    // For removal, wait for the state to update before syncing with parent
    if (!isSyncingFromParentRef.current && hasRemoval) {
      // Use setTimeout to ensure we get the edges AFTER removal and avoid setState during render
      setTimeout(() => {
        setEdges((currentEdges) => {
          const workflowEdges: WorkflowEdge[] = currentEdges.map(edge => ({
            id: edge.id,
            source: edge.source,
            target: edge.target,
            sourceHandle: edge.sourceHandle || undefined,
            targetHandle: edge.targetHandle || undefined,
            label: typeof edge.label === 'string' ? edge.label : undefined,
          }));

          // Update parent with edges after removal (deferred to avoid setState during render)
          setTimeout(() => {
            onEdgesChange(workflowEdges);
          }, 0);

          // Clear selected edge if it was removed
          if (selectedEdgeId && !currentEdges.find(e => e.id === selectedEdgeId)) {
            setTimeout(() => setSelectedEdgeId(null), 0);
          }

          return currentEdges;
        });
      }, 0);
    }
  }, [onEdgesChangeInternal, onEdgesChange, setEdges, selectedEdgeId]);

  // Handle new connections
  const onConnect = useCallback(
    (params: Connection) => {
      const newEdge = {
        ...params,
        id: `edge-${Date.now()}`,
        type: 'smoothstep',
        deletable: true,
        focusable: true,
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
      // Clear edge selection when node is clicked
      setSelectedEdgeId(null);
    },
    [onNodeSelect]
  );

  // Handle edge click for manual selection
  const onEdgeClick = useCallback(
    (_: React.MouseEvent, edge: Edge) => {
      // Clear node selection when edge is clicked
      onNodeSelect(null);
      // Set the selected edge ID
      setSelectedEdgeId(edge.id);
    },
    [onNodeSelect]
  );

  // Handle node double-click
  const handleNodeDoubleClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      if (onNodeDoubleClick) {
        onNodeDoubleClick(node.id);
      }
    },
    [onNodeDoubleClick]
  );

  // Handle pane click (deselect)
  const onPaneClick = useCallback(() => {
    onNodeSelect(null);
    setSelectedEdgeId(null);
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
    // Only update if not currently dragging and this is a sync from parent
    if (!isDraggingRef.current) {
      // Create the flow nodes and edges inside the effect
      const newFlowNodes: Node[] = definition.nodes.map(node => ({
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

      const newFlowEdges: Edge[] = definition.edges.map(edge => ({
        id: edge.id,
        type: 'smoothstep',
        source: edge.source,
        target: edge.target,
        sourceHandle: edge.sourceHandle || undefined,
        targetHandle: edge.targetHandle || undefined,
        label: edge.label,
        deletable: true,
        focusable: true,
        selected: edge.id === selectedEdgeId,
      }));

      // Mark that we're syncing from parent to prevent loop
      isSyncingFromParentRef.current = true;

      // Use setTimeout to avoid setState during render
      setTimeout(() => {
        setNodes(newFlowNodes);
        setEdges(newFlowEdges);

        // Clear the flag after state update
        setTimeout(() => {
          isSyncingFromParentRef.current = false;
        }, 0);
      }, 0);
    }
  }, [definition, nodeConfigs, selectedNodeId, selectedEdgeId, setNodes, setEdges]);

  // Convert background variant string to enum
  const getBackgroundVariant = (): BackgroundVariant => {
    switch (settings.backgroundVariant) {
      case 'dots':
        return BackgroundVariant.Dots;
      case 'lines':
        return BackgroundVariant.Lines;
      case 'cross':
        return BackgroundVariant.Cross;
      default:
        return BackgroundVariant.Dots;
    }
  };

  return (
    <div className="h-full w-full" ref={reactFlowWrapper}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={handleNodesChange}
        onEdgesChange={handleEdgesChange}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        onEdgeClick={onEdgeClick}
        onNodeDoubleClick={handleNodeDoubleClick}
        onPaneClick={onPaneClick}
        onInit={setReactFlowInstance}
        onDrop={onDrop}
        onDragOver={onDragOver}
        nodeTypes={nodeTypes}
        fitView
        deleteKeyCode={['Delete', 'Backspace']}
        // Enable edge interactivity
        edgesFocusable={true}
        edgesUpdatable={true}
        elementsSelectable={true}
        // Apply settings
        snapToGrid={settings.snapToGrid}
        snapGrid={[settings.gridSize, settings.gridSize]}
        panOnScroll={settings.panOnScroll}
        selectionOnDrag={settings.selectionOnDrag}
        connectionMode={settings.connectionMode as RFConnectionMode}
        minZoom={settings.minZoom}
        maxZoom={settings.maxZoom}
        defaultEdgeOptions={{
          animated: settings.animatedEdges,
          type: 'smoothstep',
          deletable: true,
          focusable: true,
        }}
        proOptions={{ hideAttribution: true }}
      >
        {/* Conditional Background */}
        {settings.showBackground && (
          <Background
            variant={getBackgroundVariant()}
            gap={settings.backgroundGap}
            color={settings.backgroundColor}
            size={settings.backgroundVariant === 'cross' ? 2 : 1}
          />
        )}

        {/* Controls always visible */}
        <Controls showInteractive={false} />

        {/* Conditional MiniMap */}
        {settings.showMiniMap && (
          <MiniMap
            nodeStrokeWidth={3}
            zoomable
            pannable
            position="bottom-left"
          />
        )}

        {/* Settings Panel */}
        <CanvasSettings
          settings={settings}
          onSettingChange={updateSetting}
          onReset={resetSettings}
        />
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