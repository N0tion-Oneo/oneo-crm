'use client';

import { useState, useEffect, useRef } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  X,
  CheckCircle,
  XCircle,
  Clock,
  AlertCircle,
  ChevronRight,
  ChevronDown,
  Zap,
  Code,
  FileJson,
  Activity,
  Wifi,
  WifiOff
} from 'lucide-react';
import { Workflow } from '../types';
import { useWorkflowWebSocket } from '@/hooks/useWorkflowWebSocket';

interface WorkflowDebugPanelProps {
  execution: any;
  workflow: Workflow | null;
  onClose: () => void;
}

export function WorkflowDebugPanel({ execution, workflow, onClose }: WorkflowDebugPanelProps) {
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('flow');
  const [nodeExecutions, setNodeExecutions] = useState<Record<string, any>>(
    execution?.node_executions || {}
  );
  const [executionStatus, setExecutionStatus] = useState(execution?.status);
  const [executionLogs, setExecutionLogs] = useState<any[]>(execution?.logs || []);

  // WebSocket connection for real-time updates
  const {
    isConnected,
    connectionError,
    subscribeToExecution,
    unsubscribeFromExecution
  } = useWorkflowWebSocket({
    executionId: execution?.id,
    onExecutionStarted: (data) => {
      setExecutionStatus('running');
      setNodeExecutions({});
      setExecutionLogs([]);
    },
    onNodeStarted: (data) => {
      setNodeExecutions(prev => ({
        ...prev,
        [data.node_id]: {
          ...prev[data.node_id],
          status: 'running',
          started_at: data.started_at
        }
      }));
    },
    onNodeCompleted: (data) => {
      setNodeExecutions(prev => ({
        ...prev,
        [data.node_id]: {
          ...prev[data.node_id],
          status: data.status,
          completed_at: data.completed_at,
          output_data: data.output,
          error: data.error,
          duration_ms: data.duration_ms
        }
      }));
    },
    onExecutionCompleted: (data) => {
      setExecutionStatus(data.status);
    },
    onExecutionLog: (data) => {
      setExecutionLogs(prev => [...prev, data]);
    }
  });

  // Subscribe to execution updates when execution changes
  useEffect(() => {
    if (execution?.id && isConnected) {
      subscribeToExecution(execution.id);
      return () => {
        unsubscribeFromExecution(execution.id);
      };
    }
  }, [execution?.id, isConnected, subscribeToExecution, unsubscribeFromExecution]);

  const toggleNodeExpansion = (nodeId: string) => {
    const newExpanded = new Set(expandedNodes);
    if (newExpanded.has(nodeId)) {
      newExpanded.delete(nodeId);
    } else {
      newExpanded.add(nodeId);
    }
    setExpandedNodes(newExpanded);
  };

  const getNodeStatus = (nodeId: string) => {
    if (!nodeExecutions) return 'pending';
    const nodeExecution = nodeExecutions[nodeId];
    return nodeExecution?.status || 'pending';
  };

  const getNodeIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'running':
        return <Clock className="h-4 w-4 text-blue-500 animate-spin" />;
      case 'skipped':
        return <AlertCircle className="h-4 w-4 text-gray-400" />;
      default:
        return <Clock className="h-4 w-4 text-gray-400" />;
    }
  };

  const getExecutionStatusBadge = () => {
    if (!executionStatus) return null;

    const variants: Record<string, 'default' | 'secondary' | 'outline' | 'destructive'> = {
      running: 'default',
      success: 'outline',
      failed: 'destructive',
      cancelled: 'secondary',
      paused: 'secondary'
    };

    return (
      <Badge variant={variants[executionStatus] || 'outline'}>
        {executionStatus}
      </Badge>
    );
  };

  const formatDuration = (startTime: string, endTime?: string) => {
    const start = new Date(startTime);
    const end = endTime ? new Date(endTime) : new Date();
    const duration = end.getTime() - start.getTime();

    if (duration < 1000) return `${duration}ms`;
    if (duration < 60000) return `${(duration / 1000).toFixed(1)}s`;
    return `${(duration / 60000).toFixed(1)}m`;
  };

  const renderNodeExecution = (nodeId: string, nodeData: any) => {
    const isExpanded = expandedNodes.has(nodeId);
    const status = getNodeStatus(nodeId);
    const nodeExecution = nodeExecutions?.[nodeId];

    return (
      <div key={nodeId} className="border rounded-lg mb-2">
        <div
          className="flex items-center justify-between p-3 cursor-pointer hover:bg-muted/50"
          onClick={() => toggleNodeExpansion(nodeId)}
        >
          <div className="flex items-center gap-2">
            {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            {getNodeIcon(status)}
            <span className="font-medium">{nodeData.label || nodeId}</span>
            <Badge variant="secondary" className="text-xs">
              {nodeData.nodeType}
            </Badge>
          </div>
          {nodeExecution && (
            <span className="text-xs text-muted-foreground">
              {formatDuration(nodeExecution.started_at, nodeExecution.completed_at)}
            </span>
          )}
        </div>

        {isExpanded && nodeExecution && (
          <div className="px-3 pb-3 space-y-2">
            {/* Input Data */}
            {nodeExecution.input_data && (
              <div>
                <h5 className="text-sm font-medium mb-1">Input:</h5>
                <pre className="text-xs bg-muted p-2 rounded overflow-x-auto">
                  {JSON.stringify(nodeExecution.input_data, null, 2)}
                </pre>
              </div>
            )}

            {/* Output Data */}
            {nodeExecution.output_data && (
              <div>
                <h5 className="text-sm font-medium mb-1">Output:</h5>
                <pre className="text-xs bg-muted p-2 rounded overflow-x-auto">
                  {JSON.stringify(nodeExecution.output_data, null, 2)}
                </pre>
              </div>
            )}

            {/* Error */}
            {nodeExecution.error && (
              <div className="p-2 bg-red-50 border border-red-200 rounded">
                <h5 className="text-sm font-medium text-red-800 mb-1">Error:</h5>
                <p className="text-xs text-red-600">{nodeExecution.error}</p>
              </div>
            )}

            {/* Logs */}
            {nodeExecution.logs && nodeExecution.logs.length > 0 && (
              <div>
                <h5 className="text-sm font-medium mb-1">Logs:</h5>
                <div className="space-y-1">
                  {nodeExecution.logs.map((log: any, index: number) => (
                    <div key={index} className="text-xs p-1 bg-muted rounded">
                      <span className="text-muted-foreground">
                        [{new Date(log.timestamp).toLocaleTimeString()}]
                      </span>{' '}
                      {log.message}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <Card className="h-[calc(100vh-200px)] flex flex-col">
      <div className="flex items-center justify-between p-4 border-b">
        <div>
          <h3 className="font-semibold">Debug Panel</h3>
          {execution && (
            <div className="flex items-center gap-2 mt-1">
              {getExecutionStatusBadge()}
              <span className="text-xs text-muted-foreground">
                Execution #{execution.id?.slice(-8)}
              </span>
              {isConnected ? (
                <span title="WebSocket connected">
                  <Wifi className="h-3 w-3 text-green-500" />
                </span>
              ) : (
                <span title={connectionError || "WebSocket disconnected"}>
                  <WifiOff className="h-3 w-3 text-red-500" />
                </span>
              )}
            </div>
          )}
        </div>
        <Button variant="ghost" size="sm" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      {!execution ? (
        <div className="flex-1 flex items-center justify-center text-muted-foreground">
          <div className="text-center">
            <Zap className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No execution running</p>
            <p className="text-sm mt-2">Click "Test Run" to start debugging</p>
          </div>
        </div>
      ) : (
        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
          <TabsList className="w-full justify-start px-4">
            <TabsTrigger value="flow">
              <Activity className="h-4 w-4 mr-2" />
              Flow
            </TabsTrigger>
            <TabsTrigger value="context">
              <FileJson className="h-4 w-4 mr-2" />
              Context
            </TabsTrigger>
            <TabsTrigger value="logs">
              <Code className="h-4 w-4 mr-2" />
              Logs
            </TabsTrigger>
          </TabsList>

          <ScrollArea className="flex-1">
            <TabsContent value="flow" className="p-4">
              <div className="space-y-2">
                {workflow?.definition.nodes.map((node) => 
                  renderNodeExecution(node.id, node.data)
                )}
              </div>
            </TabsContent>

            <TabsContent value="context" className="p-4">
              <div className="space-y-4">
                <div>
                  <h4 className="text-sm font-medium mb-2">Execution Context</h4>
                  <pre className="text-xs bg-muted p-3 rounded overflow-x-auto">
                    {JSON.stringify(execution.context || {}, null, 2)}
                  </pre>
                </div>

                <div>
                  <h4 className="text-sm font-medium mb-2">Trigger Data</h4>
                  <pre className="text-xs bg-muted p-3 rounded overflow-x-auto">
                    {JSON.stringify(execution.trigger_data || {}, null, 2)}
                  </pre>
                </div>

                <div>
                  <h4 className="text-sm font-medium mb-2">Variables</h4>
                  <pre className="text-xs bg-muted p-3 rounded overflow-x-auto">
                    {JSON.stringify(execution.variables || {}, null, 2)}
                  </pre>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="logs" className="p-4">
              <div className="space-y-2">
                {executionLogs?.map((log: any, index: number) => (
                  <div
                    key={index}
                    className={`text-xs p-2 rounded border ${
                      log.level === 'error'
                        ? 'bg-red-50 border-red-200'
                        : log.level === 'warning'
                        ? 'bg-yellow-50 border-yellow-200'
                        : 'bg-muted border-border'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-medium">{log.node_id || 'System'}</span>
                      <span className="text-muted-foreground">
                        {new Date(log.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <p className="break-all">{log.message}</p>
                    {log.data && (
                      <pre className="mt-2 text-xs opacity-75">
                        {JSON.stringify(log.data, null, 2)}
                      </pre>
                    )}
                  </div>
                )) || (
                  <p className="text-muted-foreground text-center py-4">
                    No logs available
                  </p>
                )}
              </div>
            </TabsContent>
          </ScrollArea>
        </Tabs>
      )}
    </Card>
  );
}