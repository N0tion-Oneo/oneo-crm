import { useState, useEffect } from 'react';
import { workflowsApi } from '@/lib/api';
import { WorkflowExecution } from '../types';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { formatDistanceToNow, format } from 'date-fns';
import {
  CheckCircle,
  XCircle,
  Clock,
  AlertCircle,
  ChevronRight,
  RefreshCw
} from 'lucide-react';

interface ExecutionHistoryProps {
  workflowId: string;
}

export function ExecutionHistory({ workflowId }: ExecutionHistoryProps) {
  const [executions, setExecutions] = useState<WorkflowExecution[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedExecution, setSelectedExecution] = useState<string | null>(null);

  useEffect(() => {
    fetchExecutions();
    // Poll for updates every 5 seconds
    const interval = setInterval(fetchExecutions, 5000);
    return () => clearInterval(interval);
  }, [workflowId]);

  const fetchExecutions = async () => {
    try {
      const response = await workflowsApi.getExecutions(workflowId);
      setExecutions(response.data.results || response.data);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch executions:', error);
      setLoading(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <Clock className="h-4 w-4 text-blue-500 animate-spin" />;
      case 'success':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'cancelled':
        return <AlertCircle className="h-4 w-4 text-yellow-500" />;
      default:
        return <AlertCircle className="h-4 w-4 text-gray-400" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, 'default' | 'secondary' | 'outline' | 'destructive'> = {
      running: 'default',
      success: 'outline',
      failed: 'destructive',
      cancelled: 'secondary'
    };
    return (
      <Badge variant={variants[status] || 'outline'}>
        {status}
      </Badge>
    );
  };

  const calculateDuration = (execution: WorkflowExecution) => {
    if (!execution.completed_at) return 'Running...';
    const start = new Date(execution.started_at);
    const end = new Date(execution.completed_at);
    const durationMs = end.getTime() - start.getTime();

    if (durationMs < 1000) return `${durationMs}ms`;
    if (durationMs < 60000) return `${Math.round(durationMs / 1000)}s`;
    return `${Math.round(durationMs / 60000)}m`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (executions.length === 0) {
    return (
      <Card className="p-8 text-center">
        <h3 className="text-lg font-semibold mb-2">No executions yet</h3>
        <p className="text-muted-foreground">
          This workflow hasn't been executed yet. Run it to see execution history.
        </p>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">Execution History</h3>
        <Button variant="outline" size="sm" onClick={fetchExecutions}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      <div className="space-y-2">
        {executions.map((execution) => (
          <Card
            key={execution.id}
            className={`p-4 cursor-pointer transition-colors ${
              selectedExecution === execution.id ? 'border-primary' : ''
            }`}
            onClick={() => setSelectedExecution(
              selectedExecution === execution.id ? null : execution.id
            )}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {getStatusIcon(execution.status)}
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium">
                      Execution #{execution.id.slice(-8)}
                    </span>
                    {getStatusBadge(execution.status)}
                  </div>
                  <div className="text-sm text-muted-foreground mt-1">
                    Started {formatDistanceToNow(new Date(execution.started_at), { addSuffix: true })}
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-4">
                <div className="text-right">
                  <div className="text-sm font-medium">
                    Duration: {calculateDuration(execution)}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {format(new Date(execution.started_at), 'MMM d, yyyy HH:mm')}
                  </div>
                </div>
                <ChevronRight className={`h-4 w-4 transition-transform ${
                  selectedExecution === execution.id ? 'rotate-90' : ''
                }`} />
              </div>
            </div>

            {/* Expanded details */}
            {selectedExecution === execution.id && (
              <div className="mt-4 pt-4 border-t space-y-3">
                {execution.error_message && (
                  <div className="p-3 bg-red-50 border border-red-200 rounded-md">
                    <p className="text-sm text-red-800">
                      <strong>Error:</strong> {execution.error_message}
                    </p>
                  </div>
                )}

                {execution.trigger_data && (
                  <div>
                    <h4 className="text-sm font-medium mb-1">Trigger Data</h4>
                    <pre className="text-xs bg-muted p-2 rounded-md overflow-x-auto">
                      {JSON.stringify(execution.trigger_data, null, 2)}
                    </pre>
                  </div>
                )}

                {execution.logs && execution.logs.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium mb-2">Execution Logs</h4>
                    <div className="space-y-1">
                      {execution.logs.map((log) => (
                        <div key={log.id} className="flex items-center gap-2 text-sm">
                          {getStatusIcon(log.status)}
                          <span className="font-medium">{log.node_name}</span>
                          <span className="text-muted-foreground">
                            {log.duration_ms ? `${log.duration_ms}ms` : 'Running...'}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}