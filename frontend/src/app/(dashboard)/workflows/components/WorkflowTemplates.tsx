'use client';

import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Mail,
  Users,
  FileText,
  MessageSquare,
  Calendar,
  Zap,
  GitBranch,
  RefreshCw,
  Target,
  Bell
} from 'lucide-react';
import { WorkflowNodeType } from '../types';
import { toast } from 'sonner';
import { workflowsApi } from '@/lib/api';
import { useRouter } from 'next/navigation';

interface WorkflowTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  icon: React.ReactNode;
  tags: string[];
  definition: {
    nodes: any[];
    edges: any[];
  };
}

const templates: WorkflowTemplate[] = [
  {
    id: 'welcome-email',
    name: 'Welcome Email Sequence',
    description: 'Send a series of welcome emails to new contacts',
    category: 'Marketing',
    icon: <Mail className="h-6 w-6" />,
    tags: ['email', 'automation', 'onboarding'],
    definition: {
      nodes: [
        {
          id: 'trigger-1',
          type: 'workflow',
          position: { x: 100, y: 100 },
          data: {
            nodeType: WorkflowNodeType.TRIGGER_EVENT,
            label: 'New Contact Created',
            config: {
              event_type: 'record_created',
              pipeline: 'contacts'
            }
          }
        },
        {
          id: 'email-1',
          type: 'workflow',
          position: { x: 300, y: 100 },
          data: {
            nodeType: WorkflowNodeType.UNIPILE_SEND_EMAIL,
            label: 'Send Welcome Email',
            config: {
              recipient_email: '{{record.email}}',
              subject: 'Welcome to Our Platform!',
              content: 'Hi {{record.first_name}},\n\nWelcome aboard! We\'re excited to have you.',
              tracking_enabled: true
            }
          }
        },
        {
          id: 'wait-1',
          type: 'workflow',
          position: { x: 500, y: 100 },
          data: {
            nodeType: WorkflowNodeType.WAIT_DELAY,
            label: 'Wait 2 Days',
            config: {
              delay_type: 'duration',
              duration_value: 2,
              duration_unit: 'days'
            }
          }
        },
        {
          id: 'email-2',
          type: 'workflow',
          position: { x: 700, y: 100 },
          data: {
            nodeType: WorkflowNodeType.UNIPILE_SEND_EMAIL,
            label: 'Send Follow-up Email',
            config: {
              recipient_email: '{{record.email}}',
              subject: 'Getting Started Guide',
              content: 'Here are some resources to help you get started...',
              tracking_enabled: true
            }
          }
        }
      ],
      edges: [
        { id: 'e1', source: 'trigger-1', target: 'email-1' },
        { id: 'e2', source: 'email-1', target: 'wait-1' },
        { id: 'e3', source: 'wait-1', target: 'email-2' }
      ]
    }
  },
  {
    id: 'lead-scoring',
    name: 'Lead Scoring & Assignment',
    description: 'Score leads based on activity and assign to sales reps',
    category: 'Sales',
    icon: <Target className="h-6 w-6" />,
    tags: ['leads', 'scoring', 'assignment'],
    definition: {
      nodes: [
        {
          id: 'trigger-1',
          type: 'workflow',
          position: { x: 100, y: 100 },
          data: {
            nodeType: WorkflowNodeType.TRIGGER_EVENT,
            label: 'Lead Activity',
            config: {
              event_type: 'record_updated',
              pipeline: 'leads'
            }
          }
        },
        {
          id: 'ai-1',
          type: 'workflow',
          position: { x: 300, y: 100 },
          data: {
            nodeType: WorkflowNodeType.AI_ANALYSIS,
            label: 'Calculate Lead Score',
            config: {
              prompt: 'Analyze the lead data and calculate a score from 0-100 based on engagement, company size, and interest level.',
              model: 'gpt-4'
            }
          }
        },
        {
          id: 'update-1',
          type: 'workflow',
          position: { x: 500, y: 100 },
          data: {
            nodeType: WorkflowNodeType.RECORD_UPDATE,
            label: 'Update Lead Score',
            config: {
              pipeline_id: 'leads',
              record_id: '{{trigger.record_id}}',
              field_values: {
                lead_score: '{{ai-1.output}}'
              }
            }
          }
        },
        {
          id: 'condition-1',
          type: 'workflow',
          position: { x: 700, y: 100 },
          data: {
            nodeType: WorkflowNodeType.CONDITION,
            label: 'High Score Check',
            config: {
              condition_type: 'greater_than',
              left_value: '{{ai-1.output}}',
              right_value: '75'
            }
          }
        },
        {
          id: 'notify-1',
          type: 'workflow',
          position: { x: 900, y: 50 },
          data: {
            nodeType: WorkflowNodeType.TASK_NOTIFY,
            label: 'Notify Sales Team',
            config: {
              title: 'Hot Lead Alert',
              message: 'High-scoring lead requires immediate attention'
            }
          }
        }
      ],
      edges: [
        { id: 'e1', source: 'trigger-1', target: 'ai-1' },
        { id: 'e2', source: 'ai-1', target: 'update-1' },
        { id: 'e3', source: 'update-1', target: 'condition-1' },
        { id: 'e4', source: 'condition-1', target: 'notify-1', label: 'true' }
      ]
    }
  },
  {
    id: 'data-sync',
    name: 'Cross-Platform Data Sync',
    description: 'Sync data between pipelines and external systems',
    category: 'Integration',
    icon: <RefreshCw className="h-6 w-6" />,
    tags: ['sync', 'integration', 'api'],
    definition: {
      nodes: [
        {
          id: 'trigger-1',
          type: 'workflow',
          position: { x: 100, y: 100 },
          data: {
            nodeType: WorkflowNodeType.TRIGGER_SCHEDULE,
            label: 'Daily Sync',
            config: {
              schedule_type: 'daily',
              time: '02:00'
            }
          }
        },
        {
          id: 'find-1',
          type: 'workflow',
          position: { x: 300, y: 100 },
          data: {
            nodeType: WorkflowNodeType.RECORD_FIND,
            label: 'Find Updated Records',
            config: {
              pipeline_id: 'contacts',
              criteria: {
                updated_after: '{{yesterday}}'
              }
            }
          }
        },
        {
          id: 'foreach-1',
          type: 'workflow',
          position: { x: 500, y: 100 },
          data: {
            nodeType: WorkflowNodeType.FOR_EACH,
            label: 'Process Each Record',
            config: {
              items_source: '{{find-1.results}}',
              item_variable: 'record'
            }
          }
        },
        {
          id: 'http-1',
          type: 'workflow',
          position: { x: 700, y: 100 },
          data: {
            nodeType: WorkflowNodeType.HTTP_REQUEST,
            label: 'Sync to External API',
            config: {
              method: 'POST',
              url: 'https://api.external.com/contacts',
              headers: {
                'Authorization': 'Bearer {{env.API_KEY}}',
                'Content-Type': 'application/json'
              },
              body: '{{record}}'
            }
          }
        }
      ],
      edges: [
        { id: 'e1', source: 'trigger-1', target: 'find-1' },
        { id: 'e2', source: 'find-1', target: 'foreach-1' },
        { id: 'e3', source: 'foreach-1', target: 'http-1' }
      ]
    }
  },
  {
    id: 'approval-workflow',
    name: 'Document Approval Process',
    description: 'Route documents for approval based on criteria',
    category: 'Operations',
    icon: <FileText className="h-6 w-6" />,
    tags: ['approval', 'documents', 'process'],
    definition: {
      nodes: [
        {
          id: 'trigger-1',
          type: 'workflow',
          position: { x: 100, y: 100 },
          data: {
            nodeType: WorkflowNodeType.TRIGGER_EVENT,
            label: 'Document Submitted',
            config: {
              event_type: 'record_created',
              pipeline: 'documents'
            }
          }
        },
        {
          id: 'condition-1',
          type: 'workflow',
          position: { x: 300, y: 100 },
          data: {
            nodeType: WorkflowNodeType.CONDITION,
            label: 'Check Amount',
            config: {
              condition_type: 'greater_than',
              left_value: '{{record.amount}}',
              right_value: '10000'
            }
          }
        },
        {
          id: 'approval-1',
          type: 'workflow',
          position: { x: 500, y: 50 },
          data: {
            nodeType: WorkflowNodeType.APPROVAL,
            label: 'Manager Approval',
            config: {
              title: 'Document Approval Required',
              description: 'Please review and approve the document',
              assigned_to_id: '{{record.manager_id}}',
              timeout_hours: 24
            }
          }
        },
        {
          id: 'approval-2',
          type: 'workflow',
          position: { x: 500, y: 150 },
          data: {
            nodeType: WorkflowNodeType.APPROVAL,
            label: 'Director Approval',
            config: {
              title: 'High-Value Document Approval',
              description: 'Director approval required for amounts over $10,000',
              assigned_to_id: '{{env.DIRECTOR_ID}}',
              timeout_hours: 48
            }
          }
        }
      ],
      edges: [
        { id: 'e1', source: 'trigger-1', target: 'condition-1' },
        { id: 'e2', source: 'condition-1', target: 'approval-1', label: 'false' },
        { id: 'e3', source: 'condition-1', target: 'approval-2', label: 'true' }
      ]
    }
  }
];

export function WorkflowTemplates() {
  const router = useRouter();
  const [selectedTemplate, setSelectedTemplate] = useState<WorkflowTemplate | null>(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [workflowName, setWorkflowName] = useState('');
  const [workflowDescription, setWorkflowDescription] = useState('');
  const [creating, setCreating] = useState(false);

  const handleSelectTemplate = (template: WorkflowTemplate) => {
    setSelectedTemplate(template);
    setWorkflowName(template.name);
    setWorkflowDescription(template.description);
    setShowCreateDialog(true);
  };

  const handleCreateFromTemplate = async () => {
    if (!selectedTemplate) return;

    try {
      setCreating(true);
      const response = await workflowsApi.create({
        name: workflowName,
        description: workflowDescription,
        status: 'draft',
        trigger_type: 'manual',
        workflow_definition: selectedTemplate.definition
      });

      toast.success('Workflow created from template');
      router.push(`/workflows/${response.data.id}`);
    } catch (error) {
      console.error('Failed to create workflow:', error);
      toast.error('Failed to create workflow from template');
    } finally {
      setCreating(false);
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'Marketing':
        return <Mail className="h-4 w-4" />;
      case 'Sales':
        return <Target className="h-4 w-4" />;
      case 'Integration':
        return <RefreshCw className="h-4 w-4" />;
      case 'Operations':
        return <FileText className="h-4 w-4" />;
      default:
        return <Zap className="h-4 w-4" />;
    }
  };

  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {templates.map((template) => (
          <Card
            key={template.id}
            className="p-6 hover:shadow-lg transition-shadow cursor-pointer"
            onClick={() => handleSelectTemplate(template)}
          >
            <div className="flex items-start justify-between mb-4">
              <div className="p-3 bg-primary/10 rounded-lg">
                {template.icon}
              </div>
              <Badge variant="secondary">
                {template.category}
              </Badge>
            </div>

            <h3 className="font-semibold text-lg mb-2">{template.name}</h3>
            <p className="text-sm text-muted-foreground mb-4">
              {template.description}
            </p>

            <div className="flex flex-wrap gap-1">
              {template.tags.map((tag) => (
                <Badge key={tag} variant="outline" className="text-xs">
                  {tag}
                </Badge>
              ))}
            </div>

            <div className="mt-4 pt-4 border-t flex items-center justify-between text-sm text-muted-foreground">
              <span>{template.definition.nodes.length} nodes</span>
              <Button variant="ghost" size="sm">
                Use Template
              </Button>
            </div>
          </Card>
        ))}
      </div>

      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Workflow from Template</DialogTitle>
            <DialogDescription>
              Customize the workflow details before creating it from the template.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div>
              <Label htmlFor="name">Workflow Name</Label>
              <Input
                id="name"
                value={workflowName}
                onChange={(e) => setWorkflowName(e.target.value)}
                placeholder="Enter workflow name"
              />
            </div>

            <div>
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={workflowDescription}
                onChange={(e) => setWorkflowDescription(e.target.value)}
                placeholder="Enter workflow description"
                rows={3}
              />
            </div>

            {selectedTemplate && (
              <div className="p-4 bg-muted rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  {getCategoryIcon(selectedTemplate.category)}
                  <span className="font-medium">{selectedTemplate.name}</span>
                </div>
                <p className="text-sm text-muted-foreground">
                  This template includes {selectedTemplate.definition.nodes.length} nodes
                  and {selectedTemplate.definition.edges.length} connections.
                </p>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowCreateDialog(false)}
              disabled={creating}
            >
              Cancel
            </Button>
            <Button
              onClick={handleCreateFromTemplate}
              disabled={!workflowName || creating}
            >
              {creating ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Creating...
                </>
              ) : (
                'Create Workflow'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}