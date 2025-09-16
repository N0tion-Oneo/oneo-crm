'use client';

import { useCallback, useMemo, useState, useRef } from 'react';
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

interface WorkflowBuilderRedesignedProps {
  definition: WorkflowDefinition;
  onChange: (definition: WorkflowDefinition) => void;
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
    definition.nodes.map(node => ({
      id: node.id,
      type: 'workflow',
      position: node.position,
      data: { ...node.data, nodeType: node.type }
    }))
  );

  const [edges, setEdges] = useState<Edge[]>(
    definition.edges.map(edge => ({
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
    onNodeSelect(node.id, node.data);
  }, [onNodeSelect]);

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

        <Controls showInteractive={false} className="bg-white border rounded-lg shadow-sm">
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
                <TooltipContent side="left">Zoom in</TooltipContent>
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
                <TooltipContent side="left">Zoom out</TooltipContent>
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
                <TooltipContent side="left">Fit to view</TooltipContent>
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
                <TooltipContent side="left">Toggle grid</TooltipContent>
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
                <TooltipContent side="left">Toggle minimap</TooltipContent>
              </Tooltip>
            </div>
          </TooltipProvider>
        </Controls>

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
  showSidebar = true,
  showDebugPanel = false,
  showHistory = false,
  debugData
}: WorkflowBuilderRedesignedProps) {
  const [selectedCategory, setSelectedCategory] = useState('triggers');
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [selectedNodeData, setSelectedNodeData] = useState<any>(null);

  const handleNodeSelect = (nodeId: string | null, nodeData?: any) => {
    setSelectedNode(nodeId);
    setSelectedNodeData(nodeData);
  };

  const handleNodeUpdate = (nodeId: string, data: any) => {
    // Update the node in the definition
    const updatedNodes = definition.nodes.map(node =>
      node.id === nodeId ? { ...node, data: { ...node.data, ...data } } : node
    );
    onChange({ ...definition, nodes: updatedNodes });
    setSelectedNodeData(data);
  };

  const handleTestNode = async (nodeId: string) => {
    // Placeholder for node testing
    // This would call an API to test the node configuration
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve([
          { id: 1, name: 'Sample Item 1', value: 100 },
          { id: 2, name: 'Sample Item 2', value: 200 }
        ]);
      }, 1000);
    });
  };

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
            availableVariables={[]} // TODO: Calculate from nodes
            onUpdate={handleNodeUpdate}
            onClose={() => handleNodeSelect(null)}
          />
        )}

        {/* Right Panel - Debug/History */}
        {!selectedNode && (showDebugPanel || showHistory) && (
          <div className="w-96 border-l bg-card">
            <Tabs defaultValue={showDebugPanel ? "debug" : "history"} className="h-full flex flex-col">
              <TabsList className="grid w-full grid-cols-2 p-1 m-4" style={{ width: 'calc(100% - 2rem)' }}>
                <TabsTrigger value="debug">Debug</TabsTrigger>
                <TabsTrigger value="history">History</TabsTrigger>
              </TabsList>

              <TabsContent value="debug" className="flex-1 overflow-auto p-4 pt-0">
                <WorkflowDebugPanel data={debugData} />
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