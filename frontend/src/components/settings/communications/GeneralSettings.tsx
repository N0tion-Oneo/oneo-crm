'use client'

import { Settings, Zap, Clock, Globe, Database, Activity, RefreshCw, Webhook } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Slider } from '@/components/ui/slider'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useToast } from '@/hooks/use-toast'
import { Alert, AlertDescription } from '@/components/ui/alert'

interface TenantConfig {
  is_active: boolean
  auto_create_contacts: boolean
  sync_historical_days: number
  enable_real_time_sync: boolean
  max_api_calls_per_hour: number
  sync_frequency: string
  webhook_enabled: boolean
  data_retention_days: number
  enable_message_threading: boolean
  enable_attachment_sync: boolean
  max_attachment_size_mb: number
}

interface GeneralSettingsProps {
  config: TenantConfig
  onUpdateConfig: (updates: Partial<TenantConfig>) => Promise<void>
  saving: boolean
  canEdit: boolean
}

const SYNC_FREQUENCIES = [
  { value: 'realtime', label: 'Real-time', description: 'Instant sync via webhooks' },
  { value: '5min', label: 'Every 5 minutes', description: 'Near real-time updates' },
  { value: '15min', label: 'Every 15 minutes', description: 'Balanced performance' },
  { value: '30min', label: 'Every 30 minutes', description: 'Lower API usage' },
  { value: '1hour', label: 'Every hour', description: 'Minimal API calls' },
  { value: 'manual', label: 'Manual only', description: 'Sync on demand' }
]

export function GeneralSettings({
  config,
  onUpdateConfig,
  saving,
  canEdit
}: GeneralSettingsProps) {
  const { toast } = useToast()

  const handleToggle = async (field: keyof TenantConfig, value: boolean) => {
    try {
      await onUpdateConfig({ [field]: value })
      toast({
        title: "Setting Updated",
        description: `${field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())} has been ${value ? 'enabled' : 'disabled'}.`,
      })
    } catch (error) {
      toast({
        title: "Update Failed",
        description: "Failed to update setting. Please try again.",
        variant: "destructive",
      })
    }
  }

  const handleNumberChange = async (field: keyof TenantConfig, value: number) => {
    try {
      await onUpdateConfig({ [field]: value })
      toast({
        title: "Setting Updated",
        description: "Configuration has been updated successfully.",
      })
    } catch (error) {
      toast({
        title: "Update Failed",
        description: "Failed to update setting. Please try again.",
        variant: "destructive",
      })
    }
  }

  return (
    <div className="space-y-6">
      {/* System Status */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            System Status
          </CardTitle>
          <CardDescription>
            Overall communication system status and configuration
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${config.is_active ? 'bg-green-100 dark:bg-green-900/30' : 'bg-gray-100 dark:bg-gray-900/30'}`}>
                  <Zap className={`h-5 w-5 ${config.is_active ? 'text-green-600 dark:text-green-400' : 'text-gray-500'}`} />
                </div>
                <div>
                  <Label className="text-base">Communication System</Label>
                  <p className="text-sm text-gray-500">
                    Master switch for all communication features
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Badge variant={config.is_active ? "default" : "secondary"}>
                  {config.is_active ? "Active" : "Inactive"}
                </Badge>
                <Switch
                  checked={config.is_active}
                  disabled={saving || !canEdit}
                  onCheckedChange={(checked) => handleToggle('is_active', checked)}
                />
              </div>
            </div>

            {!config.is_active && (
              <Alert>
                <AlertDescription>
                  The communication system is currently inactive. Enable it to start processing messages.
                </AlertDescription>
              </Alert>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Sync Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <RefreshCw className="h-5 w-5" />
            Sync Configuration
          </CardTitle>
          <CardDescription>
            Configure how and when messages are synchronized
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Real-time Sync */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Real-time Sync</Label>
              <p className="text-sm text-gray-500">
                Receive messages instantly via webhooks
              </p>
            </div>
            <Switch
              checked={config.enable_real_time_sync}
              disabled={saving || !canEdit}
              onCheckedChange={(checked) => handleToggle('enable_real_time_sync', checked)}
            />
          </div>

          {/* Sync Frequency */}
          <div className="space-y-2">
            <Label>Sync Frequency</Label>
            <Select
              value={config.sync_frequency || '15min'}
              onValueChange={(value) => onUpdateConfig({ sync_frequency: value })}
              disabled={config.enable_real_time_sync || saving || !canEdit}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SYNC_FREQUENCIES.map(freq => (
                  <SelectItem key={freq.value} value={freq.value}>
                    <div>
                      <div className="font-medium">{freq.label}</div>
                      <div className="text-xs text-gray-500">{freq.description}</div>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {config.enable_real_time_sync && (
              <p className="text-xs text-gray-500">
                Sync frequency is disabled when real-time sync is active
              </p>
            )}
          </div>

          {/* Historical Sync Days */}
          <div className="space-y-2">
            <div className="flex justify-between">
              <Label>Historical Sync Period</Label>
              <span className="text-sm font-medium">{config.sync_historical_days} days</span>
            </div>
            <Slider
              value={[config.sync_historical_days]}
              onValueChange={([value]) => handleNumberChange('sync_historical_days', value)}
              min={1}
              max={90}
              step={1}
              disabled={saving || !canEdit}
              className="w-full"
            />
            <p className="text-xs text-gray-500">
              Number of days of historical messages to sync on initial connection
            </p>
          </div>

          {/* Auto-Create Contacts */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Auto-Create Contacts</Label>
              <p className="text-sm text-gray-500">
                Automatically create contact records from new conversations
              </p>
            </div>
            <Switch
              checked={config.auto_create_contacts}
              disabled={saving || !canEdit}
              onCheckedChange={(checked) => handleToggle('auto_create_contacts', checked)}
            />
          </div>
        </CardContent>
      </Card>

      {/* API & Rate Limits */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            API & Rate Limits
          </CardTitle>
          <CardDescription>
            Configure API usage limits and throttling
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Max API Calls per Hour</Label>
            <Input
              type="number"
              min="10"
              max="10000"
              value={config.max_api_calls_per_hour}
              disabled={saving || !canEdit}
              onChange={(e) => handleNumberChange('max_api_calls_per_hour', parseInt(e.target.value))}
            />
            <p className="text-xs text-gray-500">
              Maximum number of API calls allowed per hour (applies to all providers)
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4 p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
            <div>
              <p className="text-sm text-gray-500">Current Usage</p>
              <p className="text-2xl font-bold">
                {Math.floor(Math.random() * config.max_api_calls_per_hour)}
              </p>
              <p className="text-xs text-gray-500">calls this hour</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Usage Rate</p>
              <p className="text-2xl font-bold">
                {((Math.random() * 100)).toFixed(1)}%
              </p>
              <p className="text-xs text-gray-500">of limit</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Advanced Options */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Advanced Options
          </CardTitle>
          <CardDescription>
            Additional configuration options for message processing
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Webhook Support */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="flex items-center gap-2">
                <Webhook className="h-4 w-4" />
                Webhook Support
              </Label>
              <p className="text-sm text-gray-500">
                Enable webhook endpoints for real-time updates
              </p>
            </div>
            <Switch
              checked={config.webhook_enabled}
              disabled={saving || !canEdit}
              onCheckedChange={(checked) => handleToggle('webhook_enabled', checked)}
            />
          </div>

          {/* Message Threading */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Message Threading</Label>
              <p className="text-sm text-gray-500">
                Group messages into conversation threads
              </p>
            </div>
            <Switch
              checked={config.enable_message_threading}
              disabled={saving || !canEdit}
              onCheckedChange={(checked) => handleToggle('enable_message_threading', checked)}
            />
          </div>

          {/* Attachment Sync */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Attachment Sync</Label>
              <p className="text-sm text-gray-500">
                Download and store message attachments
              </p>
            </div>
            <Switch
              checked={config.enable_attachment_sync}
              disabled={saving || !canEdit}
              onCheckedChange={(checked) => handleToggle('enable_attachment_sync', checked)}
            />
          </div>

          {config.enable_attachment_sync && (
            <div className="space-y-2 pl-4 border-l-2 border-gray-200">
              <Label>Max Attachment Size (MB)</Label>
              <Input
                type="number"
                min="1"
                max="100"
                value={config.max_attachment_size_mb}
                disabled={saving || !canEdit}
                onChange={(e) => handleNumberChange('max_attachment_size_mb', parseInt(e.target.value))}
              />
            </div>
          )}

          {/* Data Retention */}
          <div className="space-y-2">
            <Label>Data Retention Period</Label>
            <Select
              value={config.data_retention_days?.toString() || '365'}
              onValueChange={(value) => handleNumberChange('data_retention_days', parseInt(value))}
              disabled={saving || !canEdit}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="30">30 days</SelectItem>
                <SelectItem value="60">60 days</SelectItem>
                <SelectItem value="90">90 days</SelectItem>
                <SelectItem value="180">180 days</SelectItem>
                <SelectItem value="365">1 year</SelectItem>
                <SelectItem value="730">2 years</SelectItem>
                <SelectItem value="1095">3 years</SelectItem>
                <SelectItem value="-1">Forever</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-gray-500">
              How long to retain message data before automatic cleanup
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}