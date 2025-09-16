import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Card } from '@/components/ui/card';
import { Workflow } from '../types';

interface WorkflowSettingsProps {
  workflow: Workflow;
  onChange: (updates: Partial<Workflow>) => void;
}

export function WorkflowSettings({ workflow, onChange }: WorkflowSettingsProps) {
  return (
    <div className="space-y-6">
      {/* Basic Settings */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Basic Settings</h3>
        <div className="space-y-4">
          <div>
            <Label htmlFor="name">Workflow Name</Label>
            <Input
              id="name"
              value={workflow.name}
              onChange={(e) => onChange({ name: e.target.value })}
              placeholder="Enter workflow name"
            />
          </div>

          <div>
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={workflow.description || ''}
              onChange={(e) => onChange({ description: e.target.value })}
              placeholder="Describe what this workflow does"
              rows={3}
            />
          </div>

          <div>
            <Label htmlFor="status">Status</Label>
            <Select
              value={workflow.status}
              onValueChange={(value) => onChange({ status: value as 'active' | 'inactive' | 'draft' })}
            >
              <SelectTrigger id="status">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="inactive">Inactive</SelectItem>
                <SelectItem value="draft">Draft</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label htmlFor="trigger">Trigger Type</Label>
            <Select
              value={workflow.trigger_type}
              onValueChange={(value) => onChange({ trigger_type: value })}
            >
              <SelectTrigger id="trigger">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="manual">Manual</SelectItem>
                <SelectItem value="schedule">Schedule</SelectItem>
                <SelectItem value="webhook">Webhook</SelectItem>
                <SelectItem value="event">Event</SelectItem>
                <SelectItem value="record_created">Record Created</SelectItem>
                <SelectItem value="record_updated">Record Updated</SelectItem>
                <SelectItem value="form_submitted">Form Submitted</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </Card>

      {/* Execution Settings */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Execution Settings</h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <Label htmlFor="retry">Retry on Failure</Label>
              <p className="text-sm text-muted-foreground">
                Automatically retry failed nodes
              </p>
            </div>
            <Switch
              id="retry"
              checked={workflow.definition.settings?.retry_on_failure || false}
              onCheckedChange={(checked) =>
                onChange({
                  definition: {
                    ...workflow.definition,
                    settings: {
                      ...workflow.definition.settings,
                      retry_on_failure: checked
                    }
                  }
                })
              }
            />
          </div>

          <div>
            <Label htmlFor="timeout">Max Execution Time (seconds)</Label>
            <Input
              id="timeout"
              type="number"
              value={workflow.definition.settings?.max_execution_time || 3600}
              onChange={(e) =>
                onChange({
                  definition: {
                    ...workflow.definition,
                    settings: {
                      ...workflow.definition.settings,
                      max_execution_time: parseInt(e.target.value)
                    }
                  }
                })
              }
              placeholder="3600"
            />
          </div>
        </div>
      </Card>

      {/* Notification Settings */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Notifications</h3>
        <div className="space-y-4">
          <div>
            <Label htmlFor="emails">Notification Emails</Label>
            <Textarea
              id="emails"
              value={workflow.definition.settings?.notification_emails?.join('\n') || ''}
              onChange={(e) =>
                onChange({
                  definition: {
                    ...workflow.definition,
                    settings: {
                      ...workflow.definition.settings,
                      notification_emails: e.target.value.split('\n').filter(email => email.trim())
                    }
                  }
                })
              }
              placeholder="Enter email addresses (one per line)"
              rows={3}
            />
            <p className="text-sm text-muted-foreground mt-1">
              Receive notifications when workflow completes or fails
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}