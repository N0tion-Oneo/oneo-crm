'use client';

import { useCallback, useMemo, useState, useRef } from 'react';
import { workflowsApi } from '@/lib/api';
import ReactFlow, {
  Node,
  Edge,
  addEdge,
  applyNodeChanges,
  applyEdgeChanges,
  NodeChange,
  EdgeChange,
  Connection,
  ReactFlowProvider,
  Controls,
  Background,
  MiniMap,
  Panel,
  useReactFlow,
  ReactFlowInstance,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { WorkflowDefinition, WorkflowNode, WorkflowEdge, WorkflowNodeType } from '../types';
import { NodePaletteRedesigned } from './NodePaletteRedesigned';
import { WorkflowNodeComponent } from './WorkflowNode';
import WorkflowLoopControllerNode from './nodes/WorkflowLoopControllerNode';
import { NodeConfigurationPanel } from './NodeConfigurationPanel';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import {
  Settings, ZoomIn, ZoomOut, Maximize, Grid3x3, Layers,
  Play, Pause, SkipForward, RefreshCw, Search, Filter,
  ChevronRight, ChevronLeft, Info, AlertCircle, CheckCircle,
  Clock, Zap, Database, Code, GitBranch, Target, Send,
  MessageSquare, Mail, Bot, Sparkles, Package, Workflow
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { ExecutionHistory } from './ExecutionHistory';
import { WorkflowDebugPanel } from './WorkflowDebugPanel';
import { WorkflowContextPanel } from './WorkflowContextPanel';
import { workflowSchemaService } from '@/services/workflowSchemaService';

interface WorkflowBuilderRedesignedProps {
  definition: WorkflowDefinition;
  onChange: (definition: WorkflowDefinition) => void;
  workflowId?: string;
  showSidebar?: boolean;
  showDebugPanel?: boolean;
  showHistory?: boolean;
  debugData?: any;
}

const nodeTypes = {
  workflow: WorkflowNodeComponent,
  loopController: WorkflowLoopControllerNode,
};

function WorkflowCanvas({
  definition,
  onChange,
  onNodeSelect
}: {
  definition: WorkflowDefinition;
  onChange: (definition: WorkflowDefinition) => void;
  onNodeSelect: (nodeId: string | null, nodeData?: any) => void;
}) {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [reactFlowInstance, setReactFlowInstance] = useState<ReactFlowInstance | null>(null);

  const [nodes, setNodes] = useState<Node[]>(
    (definition?.nodes || []).map(node => ({
      id: node.id,
      type: 'workflow',
      position: node.position,
      data: { ...node.data, nodeType: node.type }
    }))
  );

  const [edges, setEdges] = useState<Edge[]>(
    (definition?.edges || []).map(edge => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      sourceHandle: edge.sourceHandle,
      targetHandle: edge.targetHandle,
      label: edge.label,
      type: edge.type || 'default',
      animated: edge.type === 'conditional',
      style: edge.type === 'error' ? { stroke: '#ef4444' } : undefined
    }))
  );

  const [showMinimap, setShowMinimap] = useState(true);
  const [showGrid, setShowGrid] = useState(true);

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => {
      const newNodes = applyNodeChanges(changes, nodes);
      setNodes(newNodes);
      updateDefinition(newNodes, edges);
    },
    [nodes, edges]
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      const newEdges = applyEdgeChanges(changes, edges);
      setEdges(newEdges);
      updateDefinition(nodes, newEdges);
    },
    [nodes, edges]
  );

  const onConnect = useCallback(
    (params: Connection) => {
      const newEdges = addEdge(
        {
          ...params,
          id: `edge-${Date.now()}`,
          type: 'default',
          animated: false
        },
        edges
      );
      setEdges(newEdges);
      updateDefinition(nodes, newEdges);
    },
    [nodes, edges]
  );

  const updateDefinition = (newNodes: Node[], newEdges: Edge[]) => {
    const workflowNodes: WorkflowNode[] = newNodes.map(node => ({
      id: node.id,
      type: node.data.nodeType as WorkflowNodeType,
      position: node.position,
      data: node.data
    }));

    const workflowEdges: WorkflowEdge[] = newEdges.map(edge => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      sourceHandle: edge.sourceHandle || undefined,
      targetHandle: edge.targetHandle || undefined,
      label: edge.label,
      type: edge.type
    }));

    onChange({
      nodes: workflowNodes,
      edges: workflowEdges
    });
  };

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      const nodeDataStr = event.dataTransfer.getData('application/reactflow');
      if (!nodeDataStr || !reactFlowInstance || !reactFlowWrapper.current) return;

      // Parse the node data
      let nodeData;
      try {
        nodeData = JSON.parse(nodeDataStr);
      } catch (e) {
        // Fallback for old format (just the type string)
        nodeData = { type: nodeDataStr, label: `New ${nodeDataStr} Node` };
      }

      const reactFlowBounds = reactFlowWrapper.current.getBoundingClientRect();
      const position = reactFlowInstance.project({
        x: event.clientX - reactFlowBounds.left,
        y: event.clientY - reactFlowBounds.top,
      });

      // Determine the node type based on the workflow node type
      let nodeType = 'workflow'; // default
      if (nodeData.type === WorkflowNodeType.WORKFLOW_LOOP_CONTROLLER) {
        nodeType = 'loopController';
      }

      const newNode: Node = {
        id: `node-${Date.now()}`,
        type: nodeType,
        position,
        data: {
          label: nodeData.label || `New ${nodeData.type} Node`,
          description: nodeData.description,
          nodeType: nodeData.type,
          icon: nodeData.icon,
          color: nodeData.color,
          config: {}
        }
      };

      setNodes((nds) => nds.concat(newNode));
    },
    [reactFlowInstance]
  );

  const onNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    // When selecting a node, also fetch its current data from the definition
    const definitionNode = definition?.nodes?.find(n => n.id === node.id);
    const nodeData = definitionNode ? definitionNode.data : node.data;
    onNodeSelect(node.id, nodeData);
  }, [onNodeSelect, definition]);

  const updateNode = (nodeId: string, data: any) => {
    setNodes((nds) =>
      nds.map((node) => {
        if (node.id === nodeId) {
          return {
            ...node,
            data: {
              ...node.data,
              ...data
            }
          };
        }
        return node;
      })
    );
  };

  const fitView = () => {
    if (reactFlowInstance) {
      reactFlowInstance.fitView({ padding: 0.2 });
    }
  };

  return (
    <div className="relative flex-1 h-full" ref={reactFlowWrapper}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        onInit={setReactFlowInstance}
        onDragOver={onDragOver}
        onDrop={onDrop}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{
          padding: 0.2,
          maxZoom: 1,
          minZoom: 0.5
        }}
        defaultViewport={{ x: 0, y: 0, zoom: 0.75 }}
        minZoom={0.1}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
        defaultEdgeOptions={{
          animated: false,
          type: 'default'
        }}
      >
        <Background
          variant="dots"
          gap={12}
          size={1}
          color={showGrid ? "#e5e7eb" : "transparent"}
        />

        {showMinimap && (
          <MiniMap
            style={{
              backgroundColor: 'white',
              border: '1px solid #e5e7eb'
            }}
            maskColor="rgb(229, 231, 235, 0.7)"
          />
        )}

        <Controls
          showZoom={false}
          showInteractive={false}
          className="bg-white border rounded-lg shadow-sm"
        />

        <Panel position="bottom-left" className="!m-3">
          <div className="bg-white border rounded-lg shadow-sm">
            <TooltipProvider>
              <div className="flex flex-col gap-1 p-1">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => reactFlowInstance?.zoomIn()}
                    >
                      <ZoomIn className="h-4 w-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="right">Zoom in</TooltipContent>
                </Tooltip>

                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => reactFlowInstance?.zoomOut()}
                    >
                      <ZoomOut className="h-4 w-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="right">Zoom out</TooltipContent>
                </Tooltip>

                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={fitView}
                    >
                      <Maximize className="h-4 w-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="right">Fit to view</TooltipContent>
                </Tooltip>

                <Separator className="my-1" />

                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant={showGrid ? "secondary" : "ghost"}
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => setShowGrid(!showGrid)}
                    >
                      <Grid3x3 className="h-4 w-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="right">Toggle grid</TooltipContent>
                </Tooltip>

                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant={showMinimap ? "secondary" : "ghost"}
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => setShowMinimap(!showMinimap)}
                    >
                      <Layers className="h-4 w-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="right">Toggle minimap</TooltipContent>
                </Tooltip>
              </div>
            </TooltipProvider>
          </div>
        </Panel>

        {/* Canvas Status Panel */}
        <Panel position="top-center" className="bg-white/90 backdrop-blur border rounded-lg px-3 py-1.5 shadow-sm">
          <div className="flex items-center gap-4 text-sm">
            <div className="flex items-center gap-1.5">
              <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
              <span className="text-muted-foreground">Canvas ready</span>
            </div>
            <Separator orientation="vertical" className="h-4" />
            <span className="text-muted-foreground">
              {nodes.length} nodes • {edges.length} connections
            </span>
          </div>
        </Panel>
      </ReactFlow>

    </div>
  );
}

export function WorkflowBuilderRedesigned({
  definition,
  onChange,
  workflowId,
  showSidebar = true,
  showDebugPanel = false,
  showHistory = false,
  debugData
}: WorkflowBuilderRedesignedProps) {
  const [selectedCategory, setSelectedCategory] = useState('triggers');
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [selectedNodeData, setSelectedNodeData] = useState<any>(null);
  const [executionContext, setExecutionContext] = useState<Record<string, any>>({ nodes: {} });
  const [showContextPanel, setShowContextPanel] = useState(true);

  const handleNodeSelect = (nodeId: string | null, nodeData?: any) => {
    setSelectedNode(nodeId);
    setSelectedNodeData(nodeData);
  };

  const handleNodeUpdate = (nodeId: string, data: any) => {
    // Update the node in the definition with flat structure
    const updatedNodes = (definition?.nodes || []).map(node =>
      node.id === nodeId ? { ...node, data } : node
    );
    onChange({ ...definition, nodes: updatedNodes });

    // Update selectedNodeData to reflect the exact state of the node
    // This ensures tab switches always have the latest data
    const updatedNode = updatedNodes.find(n => n.id === nodeId);
    if (updatedNode) {
      setSelectedNodeData(updatedNode.data);
    }
  };

  const handleTestNode = async (nodeId: string, testRecordId?: string) => {
    console.log('Testing node:', nodeId);
    console.log('Node data:', selectedNodeData);
    console.log('Test record ID:', testRecordId);

    try {
      // Find the node in the definition
      const node = definition?.nodes?.find(n => n.id === nodeId);
      if (!node) {
        throw new Error('Node not found');
      }

      // Build context with ACTUAL outputs from predecessor nodes
      const nodeOutputs: Record<string, any> = {};

      // Get all predecessor nodes in topological order
      const executionOrder: string[] = [];
      const visited = new Set<string>();

      const buildExecutionOrder = (targetId: string) => {
        const incomingEdges = definition?.edges?.filter((edge: WorkflowEdge) => edge.target === targetId) || [];

        for (const edge of incomingEdges) {
          if (!visited.has(edge.source)) {
            visited.add(edge.source);
            // Recursively process predecessors first
            buildExecutionOrder(edge.source);
            // Then add this node to execution order
            executionOrder.push(edge.source);
          }
        }
      };

      // Build the execution order
      buildExecutionOrder(nodeId);

      // Execute each predecessor node to get actual outputs
      for (const predecessorId of executionOrder) {
        const predecessorNode = definition?.nodes?.find((n: WorkflowNode) => n.id === predecessorId);
        if (predecessorNode) {
          console.log(`Executing predecessor node: ${predecessorId} (${predecessorNode.type})`);

          try {
            // Execute the predecessor node to get its actual output using standalone API
            const predecessorResponse = await workflowsApi.testNodeStandalone({
              node_type: predecessorNode.type,
              node_config: predecessorNode.data,
              test_data_id: testRecordId,
              test_data_type: testRecordId ? 'record' : undefined
            });

            // Store the actual output from this node
            // The testNodeStandalone returns output directly, not nested in output.data
            if (predecessorResponse.data?.output) {
              nodeOutputs[predecessorId] = predecessorResponse.data.output;
              console.log(`Stored output for node ${predecessorId}:`, nodeOutputs[predecessorId]);
            }
          } catch (error) {
            console.error(`Failed to execute predecessor node ${predecessorId}:`, error);
            // Store error state but continue with other nodes
            nodeOutputs[predecessorId] = {
              error: `Failed to execute: ${error instanceof Error ? error.message : 'Unknown error'}`
            };
          }
        }
      }

      // Now execute the target node with all predecessor outputs
      console.log('Executing target node with predecessor outputs:', nodeOutputs);

      // Store the context for display
      setExecutionContext({
        nodes: nodeOutputs,
        pipeline_id: node.data?.pipeline_id,
        test_record_id: testRecordId
      });

      // Show the context panel
      setShowContextPanel(true);

      // Call the backend API to test the target node using standalone API
      const response = await workflowsApi.testNodeStandalone({
        node_type: node.type,
        node_config: node.data,
        test_data_id: testRecordId,
        test_data_type: testRecordId ? 'record' : undefined
      });

      // Update context with the current node's output
      // The testNodeStandalone returns output directly, not nested in output.data
      if (response.data?.output) {
        setExecutionContext(prev => ({
          ...prev,
          nodes: {
            ...prev.nodes,
            [nodeId]: response.data.output
          }
        }));
      }

      return response.data;
    } catch (error: any) {
      console.error('Failed to test node:', error);
      console.error('Error response:', error.response?.data);
      console.error('Error status:', error.response?.status);

      // If we got a response from the backend, throw the real error
      if (error.response) {
        throw new Error(error.response.data?.error || error.response.data?.detail || 'Node test failed');
      }

      // Only return dummy data for network errors (no backend connection)
      throw new Error('Failed to connect to test endpoint');
    }
  };

  // Calculate available variables from predecessor nodes
  const calculateAvailableVariables = useCallback((nodeId: string | null) => {
    if (!nodeId || !definition?.nodes || !definition?.edges) {
      return [];
    }

    const availableVars: Array<{ nodeId: string; label: string; outputs: string[] }> = [];
    const visited = new Set<string>();

    // Helper function to get all predecessor nodes recursively
    const getPredecessors = (targetId: string) => {
      // Find all edges that have this node as target
      const incomingEdges = definition.edges.filter((edge: WorkflowEdge) => edge.target === targetId);

      for (const edge of incomingEdges) {
        if (!visited.has(edge.source)) {
          visited.add(edge.source);

          // Find the source node
          const sourceNode = definition.nodes.find((n: WorkflowNode) => n.id === edge.source);

          if (sourceNode) {
            // For now, we'll provide basic output structure since backend doesn't provide output schemas yet
            // TODO: Update when backend provides output_schema in node_schemas endpoint

            // Provide default outputs based on node type
            let outputKeys: string[] = [];
            const nodeType = sourceNode.type.toLowerCase();

            // Provide some basic outputs for common node types
            if (nodeType.includes('record') || nodeType.includes('fetch')) {
              outputKeys = ['record', 'data', 'success'];
            } else if (nodeType.includes('ai') || nodeType.includes('prompt')) {
              outputKeys = ['response', 'content', 'success'];
            } else if (nodeType.includes('condition')) {
              outputKeys = ['result', 'matched_condition'];
            } else if (nodeType.includes('email') || nodeType.includes('send')) {
              outputKeys = ['sent', 'message_id', 'success'];
            } else if (nodeType.includes('trigger')) {
              outputKeys = ['trigger_data', 'event', 'timestamp'];
            } else {
              // Default outputs for unknown node types
              outputKeys = ['output', 'data', 'success'];
            }

            availableVars.push({
              nodeId: sourceNode.id,
              label: sourceNode.data?.label || sourceNode.type || sourceNode.id,
              outputs: outputKeys
            });
          }

          // Recursively get predecessors of this node
          getPredecessors(edge.source);
        }
      }
    };

    getPredecessors(nodeId);
    return availableVars;
  }, [definition]);

  return (
    <ReactFlowProvider>
      <div className="flex h-full w-full">
        {/* Left Sidebar - Node Palette */}
        {showSidebar && (
          <div className="w-80 border-r bg-card flex flex-col">
            <div className="p-4 border-b">
              <h2 className="text-lg font-semibold mb-2">Workflow Components</h2>
              <p className="text-sm text-muted-foreground">
                Drag components to the canvas to build your workflow
              </p>
            </div>

            <Tabs value={selectedCategory} onValueChange={setSelectedCategory} className="flex-1 flex flex-col overflow-hidden">
              <TabsList className="grid w-full grid-cols-3 p-1 mx-4 mt-4" style={{ width: 'calc(100% - 2rem)' }}>
                <TabsTrigger value="triggers" className="text-xs">Triggers</TabsTrigger>
                <TabsTrigger value="actions" className="text-xs">Actions</TabsTrigger>
                <TabsTrigger value="logic" className="text-xs">Logic</TabsTrigger>
              </TabsList>

              <div className="flex-1 overflow-hidden">
                <ScrollArea className="h-full px-4">
                  <NodePaletteRedesigned selectedCategory={selectedCategory} />
                </ScrollArea>
              </div>
            </Tabs>

            {/* Help Section */}
            <div className="p-4 border-t bg-muted/30">
              <div className="flex items-start gap-2">
                <Info className="h-4 w-4 text-muted-foreground mt-0.5" />
                <div className="text-xs text-muted-foreground">
                  <p className="font-medium mb-1">Quick tips:</p>
                  <ul className="space-y-1">
                    <li>• Drag nodes from here to canvas</li>
                    <li>• Connect nodes by dragging handles</li>
                    <li>• Click nodes to configure them</li>
                    <li>• Use keyboard shortcuts for efficiency</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Main Canvas */}
        <div className="flex-1 relative">
          <WorkflowCanvas
            definition={definition}
            onChange={onChange}
            onNodeSelect={handleNodeSelect}
          />
        </div>

        {/* Right Panel - Configuration */}
        {selectedNode && (
          <NodeConfigurationPanel
            nodeId={selectedNode}
            nodeType={selectedNodeData?.nodeType}
            nodeData={selectedNodeData}
            workflowId={workflowId}
            availableVariables={calculateAvailableVariables(selectedNode)}
            onUpdate={handleNodeUpdate}
            onClose={() => handleNodeSelect(null)}
            onTest={handleTestNode}
          />
        )}

        {/* Right Panel - Debug/History/Context */}
        {!selectedNode && (showDebugPanel || showHistory || showContextPanel) && (
          <div className="w-96 border-l bg-card">
            <Tabs defaultValue={showContextPanel ? "context" : (showDebugPanel ? "debug" : "history")} className="h-full flex flex-col">
              <TabsList className="grid w-full grid-cols-3 p-1 m-4" style={{ width: 'calc(100% - 2rem)' }}>
                <TabsTrigger value="context">Context</TabsTrigger>
                <TabsTrigger value="debug">Debug</TabsTrigger>
                <TabsTrigger value="history">History</TabsTrigger>
              </TabsList>

              <TabsContent value="context" className="flex-1 overflow-hidden p-0">
                <WorkflowContextPanel
                  context={executionContext}
                  isLoading={false}
                />
              </TabsContent>

              <TabsContent value="debug" className="flex-1 overflow-auto p-4 pt-0">
                <WorkflowDebugPanel
                  execution={debugData}
                  workflow={null}
                  onClose={() => {}}
                />
              </TabsContent>

              <TabsContent value="history" className="flex-1 overflow-auto p-4 pt-0">
                {/* ExecutionHistory component would go here */}
                <div className="text-center py-8 text-muted-foreground">
                  <Clock className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>Execution history will appear here</p>
                </div>
              </TabsContent>
            </Tabs>
          </div>
        )}
      </div>
    </ReactFlowProvider>
  );
}