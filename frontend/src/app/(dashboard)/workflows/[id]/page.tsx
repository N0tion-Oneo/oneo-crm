'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  ArrowLeft, Save, Play, Pause, Settings, Bug,
  RefreshCw, Zap, Clock, ChevronRight, Eye, EyeOff,
  Layout, History, AlertCircle, CheckCircle, XCircle,
  Plus, Trash2, Copy, Share2, HelpCircle, Sparkles
} from 'lucide-react';
import { WorkflowBuilderRedesigned } from '../components/WorkflowBuilderRedesigned';
import { ExecutionHistory } from '../components/ExecutionHistory';
import { WorkflowSettings } from '../components/WorkflowSettings';
import { WorkflowDebugPanel } from '../components/WorkflowDebugPanel';
import { workflowsApi } from '@/lib/api';
import { Workflow, WorkflowDefinition } from '../types';
import { toast } from 'sonner';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';

export default function WorkflowDetailPageRedesigned() {
  const params = useParams();
  const router = useRouter();
  const workflowId = params.id as string;
  const isNew = workflowId === 'new';

  const [workflow, setWorkflow] = useState<Workflow | null>(null);
  const [triggers, setTriggers] = useState<any[]>([]);
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [testRunning, setTestRunning] = useState(false);
  const [currentExecution, setCurrentExecution] = useState<any>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // View states
  const [showSidebar, setShowSidebar] = useState(true);
  const [showDebugPanel, setShowDebugPanel] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [editingName, setEditingName] = useState(false);
  const [workflowName, setWorkflowName] = useState('');
  const [workflowDescription, setWorkflowDescription] = useState('');

  useEffect(() => {
    if (!isNew) {
      fetchWorkflow();
    } else {
      // Initialize new workflow
      const newWorkflow: Workflow = {
        id: '',
        name: 'Untitled Workflow',
        description: 'Add a description for your workflow',
        status: 'draft' as const,
        trigger_type: 'manual',
        definition: {
          nodes: [],
          edges: []
        },
        execution_count: 0,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };
      setWorkflow(newWorkflow);
      setWorkflowName(newWorkflow.name);
      setWorkflowDescription(newWorkflow.description || '');
    }
  }, [workflowId]);

  const fetchWorkflow = async () => {
    try {
      setLoading(true);
      const [workflowResponse, triggersResponse] = await Promise.all([
        workflowsApi.get(workflowId),
        workflowsApi.getTriggers(workflowId)
      ]);

      // Map backend field name to frontend field name
      const workflowData = {
        ...workflowResponse.data,
        definition: workflowResponse.data.workflow_definition || {
          nodes: [],
          edges: []
        }
      };

      setWorkflow(workflowData);
      setWorkflowName(workflowData.name);
      setWorkflowDescription(workflowData.description);
      setTriggers(triggersResponse.data || []);
    } catch (error) {
      console.error('Failed to fetch workflow:', error);
      toast.error('Failed to load workflow');
    } finally {
      setLoading(false);
    }
  };

  const saveWorkflow = async () => {
    if (!workflow) return;

    try {
      setSaving(true);

      const payload = {
        name: workflowName,
        description: workflowDescription,
        status: workflow.status,
        trigger_type: workflow.trigger_type || 'manual',  // Default to manual since triggers are now handled by nodes
        workflow_definition: workflow.definition
      };

      console.log('Saving workflow with payload:', payload);
      console.log('Definition nodes:', payload.workflow_definition?.nodes);
      console.log('Definition edges:', payload.workflow_definition?.edges);

      if (isNew) {
        const response = await workflowsApi.create(payload);
        toast.success('Workflow created successfully');
        router.push(`/workflows/${response.data.id}`);
      } else {
        await workflowsApi.update(workflowId, payload);
        toast.success('Workflow saved successfully');
      }

      setHasUnsavedChanges(false);
    } catch (error) {
      console.error('Failed to save workflow:', error);
      toast.error('Failed to save workflow');
    } finally {
      setSaving(false);
    }
  };

  const testWorkflow = async () => {
    setTestRunning(true);
    setShowDebugPanel(true);
    // Simulate test execution
    setTimeout(() => {
      setTestRunning(false);
      toast.success('Workflow test completed');
    }, 3000);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'draft':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'inactive':
        return 'text-gray-600 bg-gray-50 border-gray-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <CheckCircle className="h-3 w-3" />;
      case 'draft':
        return <AlertCircle className="h-3 w-3" />;
      case 'inactive':
        return <XCircle className="h-3 w-3" />;
      default:
        return <AlertCircle className="h-3 w-3" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="flex flex-col items-center gap-4">
          <RefreshCw className="h-8 w-8 animate-spin text-primary" />
          <p className="text-muted-foreground">Loading workflow...</p>
        </div>
      </div>
    );
  }

  return (
    <TooltipProvider>
      <div className="flex flex-col h-full bg-background">
        {/* Header Bar */}
        <div className="border-b bg-card">
          <div className="flex items-center justify-between h-16 px-4">
            {/* Left section */}
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => router.push('/workflows')}
                className="gap-2"
              >
                <ArrowLeft className="h-4 w-4" />
                Back
              </Button>

              <Separator orientation="vertical" className="h-6" />

              <div className="flex items-center gap-3">
                {editingName ? (
                  <Input
                    value={workflowName}
                    onChange={(e) => {
                      setWorkflowName(e.target.value);
                      setHasUnsavedChanges(true);
                    }}
                    onBlur={() => setEditingName(false)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') setEditingName(false);
                    }}
                    className="h-8 w-64 font-semibold"
                    autoFocus
                  />
                ) : (
                  <h1
                    className="text-lg font-semibold cursor-pointer hover:text-primary transition-colors"
                    onClick={() => setEditingName(true)}
                  >
                    {workflowName}
                  </h1>
                )}

                {workflow && (
                  <Badge
                    variant="outline"
                    className={cn("gap-1", getStatusColor(workflow.status))}
                  >
                    {getStatusIcon(workflow.status)}
                    {workflow.status}
                  </Badge>
                )}

                {hasUnsavedChanges && (
                  <Badge variant="secondary" className="gap-1">
                    <AlertCircle className="h-3 w-3" />
                    Unsaved
                  </Badge>
                )}
              </div>
            </div>

            {/* Right section */}
            <div className="flex items-center gap-2">
              {/* View toggles */}
              <div className="flex items-center gap-1 mr-2">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant={showSidebar ? "secondary" : "ghost"}
                      size="sm"
                      onClick={() => setShowSidebar(!showSidebar)}
                    >
                      <Layout className="h-4 w-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Toggle sidebar</TooltipContent>
                </Tooltip>

                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant={showHistory ? "secondary" : "ghost"}
                      size="sm"
                      onClick={() => setShowHistory(!showHistory)}
                    >
                      <History className="h-4 w-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Execution history</TooltipContent>
                </Tooltip>

                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant={showDebugPanel ? "secondary" : "ghost"}
                      size="sm"
                      onClick={() => setShowDebugPanel(!showDebugPanel)}
                    >
                      <Bug className="h-4 w-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Debug panel</TooltipContent>
                </Tooltip>
              </div>

              <Separator orientation="vertical" className="h-6" />

              {/* Actions */}
              <Button
                variant="outline"
                size="sm"
                onClick={testWorkflow}
                disabled={testRunning || !workflow?.definition?.nodes?.length}
                className="gap-2"
              >
                {testRunning ? (
                  <>
                    <RefreshCw className="h-4 w-4 animate-spin" />
                    Testing...
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4" />
                    Test Run
                  </>
                )}
              </Button>

              <Button
                variant="default"
                size="sm"
                onClick={saveWorkflow}
                disabled={saving}
                className="gap-2"
              >
                {saving ? (
                  <>
                    <RefreshCw className="h-4 w-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4" />
                    Save
                  </>
                )}
              </Button>

              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="sm">
                    <Settings className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuLabel>Workflow Options</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => setShowSettings(true)}>
                    <Settings className="h-4 w-4 mr-2" />
                    Settings
                  </DropdownMenuItem>
                  <DropdownMenuItem>
                    <Copy className="h-4 w-4 mr-2" />
                    Duplicate
                  </DropdownMenuItem>
                  <DropdownMenuItem>
                    <Share2 className="h-4 w-4 mr-2" />
                    Share
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem className="text-red-600">
                    <Trash2 className="h-4 w-4 mr-2" />
                    Delete
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>

          {/* Workflow description bar */}
          <div className="px-4 py-2 bg-muted/30 border-t">
            <div className="flex items-center gap-4">
              <Textarea
                value={workflowDescription}
                onChange={(e) => {
                  setWorkflowDescription(e.target.value);
                  setHasUnsavedChanges(true);
                }}
                placeholder="Add a description for your workflow..."
                className="resize-none h-8 min-h-[32px] py-1.5 bg-transparent border-0 focus-visible:ring-0 focus-visible:ring-offset-0"
                rows={1}
              />

              {/* Workflow stats */}
              <div className="flex items-center gap-4 text-sm text-muted-foreground">
                <div className="flex items-center gap-1">
                  <Zap className="h-3.5 w-3.5" />
                  <span>{workflow?.definition?.nodes?.length || 0} nodes</span>
                </div>
                <div className="flex items-center gap-1">
                  <Clock className="h-3.5 w-3.5" />
                  <span>{workflow?.execution_count || 0} runs</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Main Content Area */}
        <div className="flex-1 flex overflow-hidden">
          {workflow && (
            <WorkflowBuilderRedesigned
              definition={workflow.definition}
              onChange={(definition) => {
                setWorkflow({ ...workflow, definition });
                setHasUnsavedChanges(true);
              }}
              workflowId={workflow.id || workflowId}
              showSidebar={showSidebar}
              showDebugPanel={showDebugPanel}
              showHistory={showHistory}
              debugData={currentExecution}
            />
          )}
        </div>

        {/* Settings Modal */}
        {showSettings && workflow && (
          <WorkflowSettings
            workflow={workflow}
            onChange={(updates) => {
              setWorkflow({ ...workflow, ...updates });
              setHasUnsavedChanges(true);
            }}
          />
        )}
      </div>
    </TooltipProvider>
  );
}