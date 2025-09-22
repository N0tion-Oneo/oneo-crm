'use client';

import { useState, useEffect } from 'react';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import {
  RotateCw, Clock, Package, AlertCircle, Info,
  PlayCircle, PauseCircle, CheckCircle, XCircle
} from 'lucide-react';

interface NodeSettingsTabProps {
  nodeData: any;
  onUpdate: (data: any) => void;
}

interface NodeSettings {
  retryOnFail?: boolean;
  maxRetries?: number;
  retryDelay?: number;
  executeOnce?: boolean;
  continueOnFail?: boolean;
  pauseBeforeExecution?: boolean;
  timeout?: number;
  batchSize?: number;
  notes?: string;
}

export function NodeSettingsTab({
  nodeData,
  onUpdate
}: NodeSettingsTabProps) {
  const [settings, setSettings] = useState<NodeSettings>(nodeData.settings || {
    retryOnFail: false,
    maxRetries: 3,
    retryDelay: 1000,
    executeOnce: false,
    continueOnFail: false,
    pauseBeforeExecution: false,
    timeout: 30000,
    batchSize: 10,
    notes: ''
  });

  // Sync settings state when nodeData changes (e.g., when switching tabs back)
  useEffect(() => {
    setSettings(nodeData.settings || {
      retryOnFail: false,
      maxRetries: 3,
      retryDelay: 1000,
      executeOnce: false,
      continueOnFail: false,
      pauseBeforeExecution: false,
      timeout: 30000,
      batchSize: 10,
      notes: ''
    });
  }, [nodeData.settings]);

  const updateSettings = (key: keyof NodeSettings, value: any) => {
    const newSettings = { ...settings, [key]: value };
    setSettings(newSettings);
    onUpdate({ ...nodeData, settings: newSettings });
  };

  return (
    <div className="space-y-6">
      {/* Execution Settings */}
      <div>
        <h4 className="text-sm font-medium mb-4 flex items-center gap-2">
          <PlayCircle className="h-4 w-4 text-muted-foreground" />
          Execution Settings
        </h4>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <Label htmlFor="execute-once" className="text-sm font-normal">
                Execute Once
              </Label>
              <p className="text-xs text-muted-foreground">
                Run node only for the first item received
              </p>
            </div>
            <Switch
              id="execute-once"
              checked={settings.executeOnce}
              onCheckedChange={(checked) => updateSettings('executeOnce', checked)}
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <Label htmlFor="pause-before" className="text-sm font-normal">
                Pause Before Execution
              </Label>
              <p className="text-xs text-muted-foreground">
                Wait for manual confirmation before running
              </p>
            </div>
            <Switch
              id="pause-before"
              checked={settings.pauseBeforeExecution}
              onCheckedChange={(checked) => updateSettings('pauseBeforeExecution', checked)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="timeout" className="text-sm">
              Timeout (ms)
            </Label>
            <Input
              id="timeout"
              type="number"
              value={settings.timeout}
              onChange={(e) => updateSettings('timeout', parseInt(e.target.value) || 30000)}
              placeholder="30000"
            />
            <p className="text-xs text-muted-foreground">
              Maximum time to wait for node execution
            </p>
          </div>
        </div>
      </div>

      <Separator />

      {/* Error Handling */}
      <div>
        <h4 className="text-sm font-medium mb-4 flex items-center gap-2">
          <AlertCircle className="h-4 w-4 text-muted-foreground" />
          Error Handling
        </h4>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <Label htmlFor="retry-on-fail" className="text-sm font-normal">
                Retry On Fail
              </Label>
              <p className="text-xs text-muted-foreground">
                Automatically retry when execution fails
              </p>
            </div>
            <Switch
              id="retry-on-fail"
              checked={settings.retryOnFail}
              onCheckedChange={(checked) => updateSettings('retryOnFail', checked)}
            />
          </div>

          {settings.retryOnFail && (
            <>
              <div className="space-y-2 pl-4 border-l-2 border-muted">
                <Label htmlFor="max-retries" className="text-sm">
                  Max Retries
                </Label>
                <Select
                  value={String(settings.maxRetries)}
                  onValueChange={(value) => updateSettings('maxRetries', parseInt(value))}
                >
                  <SelectTrigger id="max-retries">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {[1, 2, 3, 5, 10].map(num => (
                      <SelectItem key={num} value={String(num)}>
                        {num} {num === 1 ? 'retry' : 'retries'}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2 pl-4 border-l-2 border-muted">
                <Label htmlFor="retry-delay" className="text-sm">
                  Retry Delay (ms)
                </Label>
                <Input
                  id="retry-delay"
                  type="number"
                  value={settings.retryDelay}
                  onChange={(e) => updateSettings('retryDelay', parseInt(e.target.value) || 1000)}
                  placeholder="1000"
                />
                <p className="text-xs text-muted-foreground">
                  Wait time between retry attempts
                </p>
              </div>
            </>
          )}

          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <Label htmlFor="continue-on-fail" className="text-sm font-normal">
                Continue On Fail
              </Label>
              <p className="text-xs text-muted-foreground">
                Continue workflow even if this node fails
              </p>
            </div>
            <Switch
              id="continue-on-fail"
              checked={settings.continueOnFail}
              onCheckedChange={(checked) => updateSettings('continueOnFail', checked)}
            />
          </div>
        </div>
      </div>

      <Separator />

      {/* Batching */}
      <div>
        <h4 className="text-sm font-medium mb-4 flex items-center gap-2">
          <Package className="h-4 w-4 text-muted-foreground" />
          Batching
        </h4>
        <div className="space-y-2">
          <Label htmlFor="batch-size" className="text-sm">
            Batch Size
          </Label>
          <Select
            value={String(settings.batchSize)}
            onValueChange={(value) => updateSettings('batchSize', parseInt(value))}
          >
            <SelectTrigger id="batch-size">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {[1, 5, 10, 25, 50, 100].map(size => (
                <SelectItem key={size} value={String(size)}>
                  {size} items
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">
            Process items in batches to improve performance
          </p>
        </div>
      </div>

      <Separator />

      {/* Notes */}
      <div>
        <h4 className="text-sm font-medium mb-4 flex items-center gap-2">
          <Info className="h-4 w-4 text-muted-foreground" />
          Notes
        </h4>
        <Textarea
          value={settings.notes}
          onChange={(e) => updateSettings('notes', e.target.value)}
          placeholder="Add notes about this node's configuration or purpose..."
          rows={4}
          className="text-sm"
        />
        <p className="text-xs text-muted-foreground mt-2">
          Document this node's purpose for team members
        </p>
      </div>

      {/* Settings Summary */}
      <div className="p-3 bg-muted/50 rounded-lg">
        <h4 className="text-xs font-medium mb-2">Active Settings</h4>
        <div className="flex flex-wrap gap-1.5">
          {settings.executeOnce && (
            <Badge variant="secondary" className="text-xs">
              <CheckCircle className="h-3 w-3 mr-1" />
              Execute Once
            </Badge>
          )}
          {settings.retryOnFail && (
            <Badge variant="secondary" className="text-xs">
              <RotateCw className="h-3 w-3 mr-1" />
              Retry {settings.maxRetries}x
            </Badge>
          )}
          {settings.continueOnFail && (
            <Badge variant="secondary" className="text-xs">
              <XCircle className="h-3 w-3 mr-1" />
              Continue on Fail
            </Badge>
          )}
          {settings.pauseBeforeExecution && (
            <Badge variant="secondary" className="text-xs">
              <PauseCircle className="h-3 w-3 mr-1" />
              Manual Confirmation
            </Badge>
          )}
          {!settings.executeOnce && !settings.retryOnFail && !settings.continueOnFail && !settings.pauseBeforeExecution && (
            <span className="text-xs text-muted-foreground">Default settings</span>
          )}
        </div>
      </div>
    </div>
  );
}