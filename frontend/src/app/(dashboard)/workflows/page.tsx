'use client';

import { useState, useEffect } from 'react';
import { Plus, Play, Clock, CheckCircle, XCircle, AlertCircle, Sparkles, GitBranch } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useRouter } from 'next/navigation';
import { workflowsApi } from '@/lib/api';
import { WorkflowTemplates } from './components/WorkflowTemplates';
import { WorkflowAnalytics } from './components/WorkflowAnalytics';
import { formatDistanceToNow } from 'date-fns';

interface Workflow {
  id: string;
  name: string;
  description: string;
  status: 'active' | 'inactive' | 'draft';
  last_execution?: {
    id: string;
    status: 'running' | 'success' | 'failed';
    started_at: string;
    completed_at?: string;
  };
  created_at: string;
  updated_at: string;
  trigger_type: string;
  execution_count: number;
}

export default function WorkflowsPage() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    fetchWorkflows();
  }, []);

  const fetchWorkflows = async () => {
    try {
      setLoading(true);
      const response = await workflowsApi.list();
      setWorkflows(response.data.results || response.data);
    } catch (err) {
      console.error('Failed to fetch workflows:', err);
      setError('Failed to load workflows');
    } finally {
      setLoading(false);
    }
  };

  const triggerWorkflow = async (workflowId: string) => {
    try {
      await workflowsApi.trigger(workflowId, {
        data: {} // Manual trigger data
      });
      // Refresh to show new execution
      fetchWorkflows();
    } catch (err) {
      console.error('Failed to trigger workflow:', err);
    }
  };

  const getStatusIcon = (status?: string) => {
    switch (status) {
      case 'running':
        return <Clock className="h-4 w-4 text-blue-500 animate-spin" />;
      case 'success':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      default:
        return <AlertCircle className="h-4 w-4 text-gray-400" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, 'default' | 'secondary' | 'outline' | 'destructive'> = {
      active: 'default',
      inactive: 'secondary',
      draft: 'outline'
    };
    return (
      <Badge variant={variants[status] || 'outline'}>
        {status}
      </Badge>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-red-500">{error}</p>
        <Button onClick={fetchWorkflows} className="mt-4">
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Workflows</h1>
          <p className="text-muted-foreground mt-1">
            Automate your business processes
          </p>
        </div>
        <Button
          onClick={() => router.push('/workflows/new')}
          className="flex items-center gap-2"
        >
          <Plus className="h-4 w-4" />
          Create Workflow
        </Button>
      </div>

      {/* Tabs for Workflows, Templates, and Analytics */}
      <Tabs defaultValue="workflows" className="w-full">
        <TabsList>
          <TabsTrigger value="workflows">
            <GitBranch className="h-4 w-4 mr-2" />
            My Workflows
          </TabsTrigger>
          <TabsTrigger value="templates">
            <Sparkles className="h-4 w-4 mr-2" />
            Templates
          </TabsTrigger>
          <TabsTrigger value="analytics">
            <Play className="h-4 w-4 mr-2" />
            Analytics
          </TabsTrigger>
        </TabsList>

        <TabsContent value="workflows" className="mt-6">
          {/* Workflows Grid */}
          {workflows.length === 0 ? (
            <Card className="p-12 text-center">
              <div className="max-w-md mx-auto">
                <h3 className="text-lg font-semibold mb-2">No workflows yet</h3>
                <p className="text-muted-foreground mb-4">
                  Create your first workflow to automate tasks and processes
                </p>
                <Button onClick={() => router.push('/workflows/new')}>
                  Create Your First Workflow
                </Button>
              </div>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {workflows.map((workflow) => (
            <Card
              key={workflow.id}
              className="p-6 hover:shadow-lg transition-shadow cursor-pointer"
              onClick={() => router.push(`/workflows/${workflow.id}`)}
            >
              <div className="space-y-4">
                {/* Header */}
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <h3 className="font-semibold text-lg">{workflow.name}</h3>
                    <p className="text-sm text-muted-foreground mt-1">
                      {workflow.description || 'No description'}
                    </p>
                  </div>
                  {getStatusBadge(workflow.status)}
                </div>

                {/* Stats */}
                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-4">
                    <span className="text-muted-foreground">
                      Trigger: <span className="font-medium">{workflow.trigger_type}</span>
                    </span>
                    <span className="text-muted-foreground">
                      Runs: <span className="font-medium">{workflow.execution_count}</span>
                    </span>
                  </div>
                </div>

                {/* Last Execution */}
                {workflow.last_execution && (
                  <div className="flex items-center justify-between pt-3 border-t">
                    <div className="flex items-center gap-2">
                      {getStatusIcon(workflow.last_execution.status)}
                      <span className="text-sm text-muted-foreground">
                        {workflow.last_execution.status === 'running'
                          ? 'Running...'
                          : `Last run ${formatDistanceToNow(new Date(workflow.last_execution.started_at), { addSuffix: true })}`
                        }
                      </span>
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="flex justify-end gap-2 pt-3 border-t">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={(e) => {
                      e.stopPropagation();
                      triggerWorkflow(workflow.id);
                    }}
                    disabled={workflow.status !== 'active'}
                  >
                    <Play className="h-3 w-3 mr-1" />
                    Run
                  </Button>
                </div>
              </div>
            </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="templates" className="mt-6">
          <WorkflowTemplates />
        </TabsContent>

        <TabsContent value="analytics" className="mt-6">
          <WorkflowAnalytics />
        </TabsContent>
      </Tabs>
    </div>
  );
}