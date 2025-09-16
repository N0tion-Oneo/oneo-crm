'use client';

import React, { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import {
  Clock,
  Calendar,
  Globe,
  Database,
  Mail,
  MessageSquare,
  GitBranch,
  Play,
  Zap,
  AlertCircle
} from 'lucide-react';

interface TriggerConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  workflow: any;
  initialTriggers?: any[];
  onSave: (triggers: any[]) => void;
}

const TRIGGER_TYPES = [
  { id: 'manual', name: 'Manual', icon: Play, description: 'Manually start workflow' },
  { id: 'scheduled', name: 'Schedule', icon: Clock, description: 'Run on a schedule' },
  { id: 'webhook', name: 'Webhook', icon: Globe, description: 'External API trigger' },
  { id: 'record_created', name: 'Record Created', icon: Database, description: 'When a record is created' },
  { id: 'record_updated', name: 'Record Updated', icon: Database, description: 'When a record is updated' },
  { id: 'record_deleted', name: 'Record Deleted', icon: Database, description: 'When a record is deleted' },
  { id: 'field_changed', name: 'Field Changed', icon: Database, description: 'When a specific field changes' },
  { id: 'api_endpoint', name: 'API Endpoint', icon: Globe, description: 'Custom API endpoint trigger' },
  { id: 'form_submitted', name: 'Form Submitted', icon: Database, description: 'When a form is submitted' },
  { id: 'email_received', name: 'Email Received', icon: Mail, description: 'When email is received' },
  { id: 'message_received', name: 'Message Received', icon: MessageSquare, description: 'When message is received' },
  { id: 'status_changed', name: 'Status Changed', icon: Database, description: 'When record status changes' },
  { id: 'date_reached', name: 'Date Reached', icon: Calendar, description: 'When a specific date is reached' },
  { id: 'condition_met', name: 'Condition Met', icon: Zap, description: 'When conditions are met' },
  { id: 'pipeline_stage_changed', name: 'Pipeline Stage', icon: GitBranch, description: 'When pipeline stage changes' },
  { id: 'engagement_threshold', name: 'Engagement Threshold', icon: Zap, description: 'When engagement threshold is met' },
  { id: 'workflow_completed', name: 'Workflow Completed', icon: GitBranch, description: 'When another workflow completes' }
];

export function TriggerConfigModal({ isOpen, onClose, workflow, initialTriggers, onSave }: TriggerConfigModalProps) {
  const [triggers, setTriggers] = useState(initialTriggers || []);
  const [selectedType, setSelectedType] = useState('manual');
  const [currentConfig, setCurrentConfig] = useState<any>({});

  // Update triggers when initialTriggers changes
  React.useEffect(() => {
    if (initialTriggers) {
      setTriggers(initialTriggers);
    }
  }, [initialTriggers]);

  const addTrigger = () => {
    const triggerType = TRIGGER_TYPES.find(t => t.id === selectedType);
    const newTrigger = {
      id: `trigger_${Date.now()}`,
      type: selectedType,
      name: triggerType?.name || '',
      enabled: true,
      config: { ...currentConfig }
    };
    setTriggers([...triggers, newTrigger]);
    setCurrentConfig({});
  };

  const removeTrigger = (triggerId: string) => {
    setTriggers(triggers.filter((t: any) => t.id !== triggerId));
  };

  const toggleTrigger = (triggerId: string) => {
    setTriggers(triggers.map((t: any) =>
      t.id === triggerId ? { ...t, enabled: !t.enabled } : t
    ));
  };

  const handleSave = () => {
    onSave(triggers);
    onClose();
  };

  const renderTriggerConfig = () => {
    switch (selectedType) {
      case 'scheduled':
      case 'schedule':
        return (
          <div className="space-y-4">
            <div>
              <Label>Cron Expression</Label>
              <Input
                placeholder="0 9 * * MON-FRI"
                value={currentConfig.cron || ''}
                onChange={(e) => setCurrentConfig({ ...currentConfig, cron: e.target.value })}
              />
              <p className="text-xs text-muted-foreground mt-1">
                e.g., "0 9 * * MON-FRI" runs at 9 AM on weekdays
              </p>
            </div>
            <div>
              <Label>Timezone</Label>
              <Select
                value={currentConfig.timezone || 'UTC'}
                onValueChange={(value) => setCurrentConfig({ ...currentConfig, timezone: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="UTC">UTC</SelectItem>
                  <SelectItem value="America/New_York">Eastern Time</SelectItem>
                  <SelectItem value="America/Chicago">Central Time</SelectItem>
                  <SelectItem value="America/Denver">Mountain Time</SelectItem>
                  <SelectItem value="America/Los_Angeles">Pacific Time</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        );

      case 'webhook':
        return (
          <div className="space-y-4">
            <div>
              <Label>Webhook URL</Label>
              <div className="flex items-center gap-2">
                <Input
                  readOnly
                  value={`${window.location.origin}/api/v1/workflows/${workflow?.id}/webhook`}
                  className="font-mono text-xs"
                />
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    navigator.clipboard.writeText(`${window.location.origin}/api/v1/workflows/${workflow?.id}/webhook`);
                  }}
                >
                  Copy
                </Button>
              </div>
            </div>
            <div>
              <Label>Secret Token (Optional)</Label>
              <Input
                type="password"
                placeholder="Enter a secret token for verification"
                value={currentConfig.secret || ''}
                onChange={(e) => setCurrentConfig({ ...currentConfig, secret: e.target.value })}
              />
            </div>
            <div>
              <Label>HTTP Method</Label>
              <Select
                value={currentConfig.method || 'POST'}
                onValueChange={(value) => setCurrentConfig({ ...currentConfig, method: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="POST">POST</SelectItem>
                  <SelectItem value="GET">GET</SelectItem>
                  <SelectItem value="PUT">PUT</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        );

      case 'record_created':
      case 'record_updated':
        return (
          <div className="space-y-4">
            <div>
              <Label>Pipeline</Label>
              <Select
                value={currentConfig.pipeline_id || ''}
                onValueChange={(value) => setCurrentConfig({ ...currentConfig, pipeline_id: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a pipeline" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="leads">Leads</SelectItem>
                  <SelectItem value="contacts">Contacts</SelectItem>
                  <SelectItem value="deals">Deals</SelectItem>
                  <SelectItem value="tickets">Tickets</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Filter Conditions (Optional)</Label>
              <Textarea
                placeholder='{"status": "new", "priority": "high"}'
                value={currentConfig.filters || ''}
                onChange={(e) => setCurrentConfig({ ...currentConfig, filters: e.target.value })}
                className="font-mono text-xs"
              />
              <p className="text-xs text-muted-foreground mt-1">
                JSON format for field conditions
              </p>
            </div>
          </div>
        );

      case 'message_received':
        return (
          <div className="space-y-4">
            <div>
              <Label>Channel</Label>
              <Select
                value={currentConfig.channel || 'any'}
                onValueChange={(value) => setCurrentConfig({ ...currentConfig, channel: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="any">Any Channel</SelectItem>
                  <SelectItem value="whatsapp">WhatsApp</SelectItem>
                  <SelectItem value="linkedin">LinkedIn</SelectItem>
                  <SelectItem value="sms">SMS</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>From Pattern</Label>
              <Input
                placeholder="+1234*"
                value={currentConfig.from_pattern || ''}
                onChange={(e) => setCurrentConfig({ ...currentConfig, from_pattern: e.target.value })}
              />
            </div>
            <div>
              <Label>Message Pattern</Label>
              <Input
                placeholder="Contains keyword..."
                value={currentConfig.message_pattern || ''}
                onChange={(e) => setCurrentConfig({ ...currentConfig, message_pattern: e.target.value })}
              />
            </div>
          </div>
        );

      case 'email_received':
        return (
          <div className="space-y-4">
            <div>
              <Label>From Address Pattern</Label>
              <Input
                placeholder="*@company.com"
                value={currentConfig.from_pattern || ''}
                onChange={(e) => setCurrentConfig({ ...currentConfig, from_pattern: e.target.value })}
              />
            </div>
            <div>
              <Label>Subject Pattern</Label>
              <Input
                placeholder="Support Request:*"
                value={currentConfig.subject_pattern || ''}
                onChange={(e) => setCurrentConfig({ ...currentConfig, subject_pattern: e.target.value })}
              />
            </div>
            <div className="flex items-center justify-between">
              <Label>Include Attachments</Label>
              <Switch
                checked={currentConfig.include_attachments || false}
                onCheckedChange={(checked) =>
                  setCurrentConfig({ ...currentConfig, include_attachments: checked })
                }
              />
            </div>
          </div>
        );

      case 'record_deleted':
        return (
          <div className="space-y-4">
            <div>
              <Label>Pipeline</Label>
              <Select
                value={currentConfig.pipeline_id || ''}
                onValueChange={(value) => setCurrentConfig({ ...currentConfig, pipeline_id: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a pipeline" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="leads">Leads</SelectItem>
                  <SelectItem value="contacts">Contacts</SelectItem>
                  <SelectItem value="deals">Deals</SelectItem>
                  <SelectItem value="tickets">Tickets</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        );

      case 'field_changed':
        return (
          <div className="space-y-4">
            <div>
              <Label>Pipeline</Label>
              <Select
                value={currentConfig.pipeline_id || ''}
                onValueChange={(value) => setCurrentConfig({ ...currentConfig, pipeline_id: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a pipeline" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="leads">Leads</SelectItem>
                  <SelectItem value="contacts">Contacts</SelectItem>
                  <SelectItem value="deals">Deals</SelectItem>
                  <SelectItem value="tickets">Tickets</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Field Name</Label>
              <Input
                placeholder="status, priority, owner, etc."
                value={currentConfig.field_name || ''}
                onChange={(e) => setCurrentConfig({ ...currentConfig, field_name: e.target.value })}
              />
            </div>
            <div>
              <Label>From Value (Optional)</Label>
              <Input
                placeholder="Previous value"
                value={currentConfig.from_value || ''}
                onChange={(e) => setCurrentConfig({ ...currentConfig, from_value: e.target.value })}
              />
            </div>
            <div>
              <Label>To Value (Optional)</Label>
              <Input
                placeholder="New value"
                value={currentConfig.to_value || ''}
                onChange={(e) => setCurrentConfig({ ...currentConfig, to_value: e.target.value })}
              />
            </div>
          </div>
        );

      case 'api_endpoint':
        return (
          <div className="space-y-4">
            <div>
              <Label>Endpoint URL</Label>
              <div className="flex items-center gap-2">
                <Input
                  readOnly
                  value={`${window.location.origin}/api/v1/workflows/${workflow?.id}/api-trigger`}
                  className="font-mono text-xs"
                />
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    navigator.clipboard.writeText(`${window.location.origin}/api/v1/workflows/${workflow?.id}/api-trigger`);
                  }}
                >
                  Copy
                </Button>
              </div>
            </div>
            <div>
              <Label>API Key (Optional)</Label>
              <Input
                type="password"
                placeholder="Enter API key for authentication"
                value={currentConfig.api_key || ''}
                onChange={(e) => setCurrentConfig({ ...currentConfig, api_key: e.target.value })}
              />
            </div>
            <div>
              <Label>Allowed Methods</Label>
              <Select
                value={currentConfig.methods || 'POST'}
                onValueChange={(value) => setCurrentConfig({ ...currentConfig, methods: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="POST">POST Only</SelectItem>
                  <SelectItem value="GET,POST">GET and POST</SelectItem>
                  <SelectItem value="ANY">Any Method</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        );

      case 'form_submitted':
        return (
          <div className="space-y-4">
            <div>
              <Label>Form</Label>
              <Select
                value={currentConfig.form_id || ''}
                onValueChange={(value) => setCurrentConfig({ ...currentConfig, form_id: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a form" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="contact">Contact Form</SelectItem>
                  <SelectItem value="lead">Lead Capture Form</SelectItem>
                  <SelectItem value="support">Support Request Form</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        );

      case 'status_changed':
        return (
          <div className="space-y-4">
            <div>
              <Label>Pipeline</Label>
              <Select
                value={currentConfig.pipeline_id || ''}
                onValueChange={(value) => setCurrentConfig({ ...currentConfig, pipeline_id: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a pipeline" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="leads">Leads</SelectItem>
                  <SelectItem value="contacts">Contacts</SelectItem>
                  <SelectItem value="deals">Deals</SelectItem>
                  <SelectItem value="tickets">Tickets</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>From Status</Label>
              <Input
                placeholder="Any status (leave empty)"
                value={currentConfig.from_status || ''}
                onChange={(e) => setCurrentConfig({ ...currentConfig, from_status: e.target.value })}
              />
            </div>
            <div>
              <Label>To Status</Label>
              <Input
                placeholder="new, qualified, closed, etc."
                value={currentConfig.to_status || ''}
                onChange={(e) => setCurrentConfig({ ...currentConfig, to_status: e.target.value })}
              />
            </div>
          </div>
        );

      case 'date_reached':
        return (
          <div className="space-y-4">
            <div>
              <Label>Date Field</Label>
              <Input
                placeholder="follow_up_date, expiry_date, etc."
                value={currentConfig.date_field || ''}
                onChange={(e) => setCurrentConfig({ ...currentConfig, date_field: e.target.value })}
              />
            </div>
            <div>
              <Label>Trigger Timing</Label>
              <Select
                value={currentConfig.timing || 'on_date'}
                onValueChange={(value) => setCurrentConfig({ ...currentConfig, timing: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="on_date">On the date</SelectItem>
                  <SelectItem value="before_1d">1 day before</SelectItem>
                  <SelectItem value="before_3d">3 days before</SelectItem>
                  <SelectItem value="before_7d">7 days before</SelectItem>
                  <SelectItem value="after_1d">1 day after</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Time of Day</Label>
              <Input
                type="time"
                value={currentConfig.time || '09:00'}
                onChange={(e) => setCurrentConfig({ ...currentConfig, time: e.target.value })}
              />
            </div>
          </div>
        );

      case 'condition_met':
        return (
          <div className="space-y-4">
            <div>
              <Label>Condition Expression</Label>
              <Textarea
                placeholder="record.status == 'qualified' AND record.score > 50"
                value={currentConfig.condition || ''}
                onChange={(e) => setCurrentConfig({ ...currentConfig, condition: e.target.value })}
                className="font-mono text-xs"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Use record.field_name to reference fields
              </p>
            </div>
            <div>
              <Label>Check Frequency</Label>
              <Select
                value={currentConfig.frequency || 'hourly'}
                onValueChange={(value) => setCurrentConfig({ ...currentConfig, frequency: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="realtime">Real-time</SelectItem>
                  <SelectItem value="hourly">Every hour</SelectItem>
                  <SelectItem value="daily">Daily</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        );

      case 'pipeline_stage_changed':
        return (
          <div className="space-y-4">
            <div>
              <Label>Pipeline</Label>
              <Select
                value={currentConfig.pipeline_id || ''}
                onValueChange={(value) => setCurrentConfig({ ...currentConfig, pipeline_id: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a pipeline" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="leads">Leads</SelectItem>
                  <SelectItem value="contacts">Contacts</SelectItem>
                  <SelectItem value="deals">Deals</SelectItem>
                  <SelectItem value="tickets">Tickets</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>From Stage</Label>
              <Input
                placeholder="Any stage (leave empty)"
                value={currentConfig.from_stage || ''}
                onChange={(e) => setCurrentConfig({ ...currentConfig, from_stage: e.target.value })}
              />
            </div>
            <div>
              <Label>To Stage</Label>
              <Input
                placeholder="qualification, negotiation, etc."
                value={currentConfig.to_stage || ''}
                onChange={(e) => setCurrentConfig({ ...currentConfig, to_stage: e.target.value })}
              />
            </div>
          </div>
        );

      case 'engagement_threshold':
        return (
          <div className="space-y-4">
            <div>
              <Label>Engagement Type</Label>
              <Select
                value={currentConfig.engagement_type || 'email'}
                onValueChange={(value) => setCurrentConfig({ ...currentConfig, engagement_type: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="email">Email Opens</SelectItem>
                  <SelectItem value="click">Link Clicks</SelectItem>
                  <SelectItem value="page_view">Page Views</SelectItem>
                  <SelectItem value="form_view">Form Views</SelectItem>
                  <SelectItem value="score">Engagement Score</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Threshold Value</Label>
              <Input
                type="number"
                placeholder="5"
                value={currentConfig.threshold || ''}
                onChange={(e) => setCurrentConfig({ ...currentConfig, threshold: e.target.value })}
              />
            </div>
            <div>
              <Label>Time Period</Label>
              <Select
                value={currentConfig.period || '7d'}
                onValueChange={(value) => setCurrentConfig({ ...currentConfig, period: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1d">Last 24 hours</SelectItem>
                  <SelectItem value="7d">Last 7 days</SelectItem>
                  <SelectItem value="30d">Last 30 days</SelectItem>
                  <SelectItem value="all">All time</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        );

      case 'workflow_completed':
        return (
          <div className="space-y-4">
            <div>
              <Label>Source Workflow</Label>
              <Select
                value={currentConfig.workflow_id || ''}
                onValueChange={(value) => setCurrentConfig({ ...currentConfig, workflow_id: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a workflow" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="onboarding">Customer Onboarding</SelectItem>
                  <SelectItem value="lead_nurture">Lead Nurture</SelectItem>
                  <SelectItem value="support_ticket">Support Ticket</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Status Filter</Label>
              <Select
                value={currentConfig.status_filter || 'any'}
                onValueChange={(value) => setCurrentConfig({ ...currentConfig, status_filter: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="any">Any Status</SelectItem>
                  <SelectItem value="success">Success Only</SelectItem>
                  <SelectItem value="failed">Failed Only</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        );

      default:
        return (
          <div className="text-center py-8 text-muted-foreground">
            <Zap className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>Manual trigger requires no configuration</p>
            <p className="text-sm mt-2">The workflow can be started manually from the UI or API</p>
          </div>
        );
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle>Configure Workflow Triggers</DialogTitle>
          <DialogDescription>
            Set up when and how this workflow should be triggered
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="add" className="flex-1">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="add">Add Trigger</TabsTrigger>
            <TabsTrigger value="manage">
              Manage Triggers
              {triggers.length > 0 && (
                <Badge className="ml-2" variant="secondary">
                  {triggers.length}
                </Badge>
              )}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="add" className="space-y-4">
            <div>
              <Label>Trigger Type</Label>
              <div className="grid grid-cols-2 gap-3 mt-2">
                {TRIGGER_TYPES.map((type) => {
                  const Icon = type.icon;
                  return (
                    <button
                      key={type.id}
                      onClick={() => setSelectedType(type.id)}
                      className={`flex items-start gap-3 p-3 rounded-lg border text-left transition-colors ${
                        selectedType === type.id
                          ? 'border-primary bg-primary/5'
                          : 'border-border hover:bg-muted/50'
                      }`}
                    >
                      <Icon className="h-5 w-5 mt-0.5 flex-shrink-0" />
                      <div>
                        <p className="font-medium text-sm">{type.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {type.description}
                        </p>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            <ScrollArea className="h-[250px] border rounded-lg p-4">
              {renderTriggerConfig()}
            </ScrollArea>

            <Button onClick={addTrigger} className="w-full">
              Add Trigger
            </Button>
          </TabsContent>

          <TabsContent value="manage" className="space-y-4">
            <ScrollArea className="h-[400px]">
              {triggers.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">
                  <AlertCircle className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No triggers configured</p>
                  <p className="text-sm mt-2">Add a trigger to automate this workflow</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {triggers.map((trigger: any) => {
                    const triggerType = TRIGGER_TYPES.find(t => t.id === trigger.type);
                    const Icon = triggerType?.icon || Zap;

                    return (
                      <div
                        key={trigger.id}
                        className="flex items-center justify-between p-3 border rounded-lg"
                      >
                        <div className="flex items-center gap-3">
                          <Icon className="h-5 w-5" />
                          <div>
                            <p className="font-medium">{trigger.name}</p>
                            <p className="text-xs text-muted-foreground">
                              {(trigger.type === 'schedule' || trigger.type === 'scheduled') && trigger.config.cron}
                              {trigger.type === 'webhook' && 'Webhook endpoint'}
                              {trigger.type === 'api_endpoint' && 'API endpoint trigger'}
                              {trigger.type === 'record_created' && `When ${trigger.config.pipeline_id || 'record'} created`}
                              {trigger.type === 'record_updated' && `When ${trigger.config.pipeline_id || 'record'} updated`}
                              {trigger.type === 'record_deleted' && `When ${trigger.config.pipeline_id || 'record'} deleted`}
                              {trigger.type === 'field_changed' && `When ${trigger.config.field_name || 'field'} changes`}
                              {trigger.type === 'form_submitted' && `Form: ${trigger.config.form_id || 'Any'}`}
                              {trigger.type === 'email_received' && `From: ${trigger.config.from_pattern || 'Any'}`}
                              {trigger.type === 'message_received' && `Channel: ${trigger.config.channel || 'Any'}`}
                              {trigger.type === 'status_changed' && `To status: ${trigger.config.to_status || 'Any'}`}
                              {trigger.type === 'date_reached' && `Field: ${trigger.config.date_field || 'Not set'}`}
                              {trigger.type === 'condition_met' && 'Custom condition'}
                              {trigger.type === 'pipeline_stage_changed' && `To stage: ${trigger.config.to_stage || 'Any'}`}
                              {trigger.type === 'engagement_threshold' && `${trigger.config.engagement_type || 'Engagement'}: ${trigger.config.threshold || '0'}`}
                              {trigger.type === 'workflow_completed' && `Workflow: ${trigger.config.workflow_id || 'Any'}`}
                              {trigger.type === 'manual' && 'Manual trigger'}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Switch
                            checked={trigger.enabled}
                            onCheckedChange={() => toggleTrigger(trigger.id)}
                          />
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => removeTrigger(trigger.id)}
                          >
                            Remove
                          </Button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </ScrollArea>
          </TabsContent>
        </Tabs>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSave}>
            Save Triggers
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}