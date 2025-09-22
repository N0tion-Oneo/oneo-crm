/**
 * Workflow Detail Page V2
 * Uses the new clean WorkflowBuilder V2
 */

'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Input } from '@/components/ui/input';
import {
  ArrowLeft, Save, Play, RefreshCw, AlertCircle, CheckCircle
} from 'lucide-react';
import { WorkflowBuilder } from '../../builder-v2/WorkflowBuilder';
import { workflowsApi } from '@/lib/api';
import { WorkflowDefinition } from '../../builder-v2/types';
import { toast } from 'sonner';

interface Workflow {
  id: string;
  name: string;
  description: string;
  status: 'active' | 'inactive' | 'draft';
  workflow_definition: WorkflowDefinition;
  created_at: string;
  updated_at: string;
}

export default function WorkflowDetailPageV2() {
  const params = useParams();
  const router = useRouter();
  const workflowId = params.id as string;
  const isNew = workflowId === 'new';

  const [workflow, setWorkflow] = useState<Workflow | null>(null);
  const [name, setName] = useState('Untitled Workflow');
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    if (!isNew) {
      fetchWorkflow();
    } else {
      // Initialize new workflow
      setWorkflow({
        id: '',
        name: 'Untitled Workflow',
        description: '',
        status: 'draft',
        workflow_definition: {
          nodes: [],
          edges: []
        },
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      });
    }
  }, [workflowId]);

  const fetchWorkflow = async () => {
    try {
      setLoading(true);
      const response = await workflowsApi.get(workflowId);
      const data = response.data;

      setWorkflow({
        ...data,
        workflow_definition: data.workflow_definition || { nodes: [], edges: [] }
      });
      setName(data.name);
    } catch (error) {
      console.error('Failed to fetch workflow:', error);
      toast.error('Failed to load workflow');
      router.push('/workflows');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!workflow) return;

    try {
      setSaving(true);

      const payload = {
        name,
        description: workflow.description,
        status: workflow.status,
        trigger_type: 'manual', // Default, as triggers are now nodes
        workflow_definition: workflow.workflow_definition
      };

      if (isNew) {
        const response = await workflowsApi.create(payload);
        toast.success('Workflow created successfully');
        router.push(`/workflows/v2/${response.data.id}`);
      } else {
        await workflowsApi.update(workflowId, payload);
        toast.success('Workflow saved successfully');
      }

      setHasChanges(false);
    } catch (error) {
      console.error('Failed to save workflow:', error);
      toast.error('Failed to save workflow');
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    // TODO: Implement test execution
    setTimeout(() => {
      setTesting(false);
      toast.success('Test completed');
    }, 2000);
  };

  const handleDefinitionChange = (definition: WorkflowDefinition) => {
    if (workflow) {
      setWorkflow({ ...workflow, workflow_definition: definition });
      setHasChanges(true);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'draft':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <CheckCircle className="h-3 w-3" />;
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
    <div className="flex flex-col h-screen bg-background">
      {/* Header */}
      <div className="border-b bg-card">
        <div className="flex items-center justify-between h-16 px-6">
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

            <Input
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                setHasChanges(true);
              }}
              className="h-8 w-64 font-semibold"
              placeholder="Workflow name"
            />

            {workflow && (
              <Badge
                variant="outline"
                className={getStatusColor(workflow.status)}
              >
                {getStatusIcon(workflow.status)}
                <span className="ml-1">{workflow.status}</span>
              </Badge>
            )}

            {hasChanges && (
              <Badge variant="secondary" className="gap-1">
                <AlertCircle className="h-3 w-3" />
                Unsaved
              </Badge>
            )}
          </div>

          {/* Right section */}
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleTest}
              disabled={testing || !workflow?.workflow_definition?.nodes?.length}
              className="gap-2"
            >
              {testing ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  Testing...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  Test
                </>
              )}
            </Button>

            <Button
              size="sm"
              onClick={handleSave}
              disabled={saving || !hasChanges}
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
          </div>
        </div>
      </div>

      {/* Builder */}
      {workflow && (
        <div className="flex-1 overflow-hidden">
          <WorkflowBuilder
            initialDefinition={workflow.workflow_definition}
            onChange={handleDefinitionChange}
          />
        </div>
      )}
    </div>
  );
}