'use client'

import { Settings, Search, Play, Loader2, Info, Zap } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { useState } from 'react'
import { useToast } from '@/hooks/use-toast'

interface ProcessingSettingsProps {
  settings: any
  onUpdateSettings: (updates: any) => void
  onProcessBatch: (dryRun: boolean) => Promise<void>
  saving: boolean
  canEdit: boolean
  canRunBatch: boolean
}

export function ProcessingSettings({
  settings,
  onUpdateSettings,
  onProcessBatch,
  saving,
  canEdit,
  canRunBatch
}: ProcessingSettingsProps) {
  const { toast } = useToast()
  const [processing, setProcessing] = useState(false)
  const [processingDryRun, setProcessingDryRun] = useState(false)

  if (!settings) return null

  const handleProcessBatch = async (dryRun: boolean) => {
    if (dryRun) {
      setProcessingDryRun(true)
    } else {
      setProcessing(true)
    }

    try {
      await onProcessBatch(dryRun)
    } catch (error) {
      toast({
        title: dryRun ? "Dry Run Failed" : "Processing Failed",
        description: "An error occurred during batch processing",
        variant: "destructive",
      })
    } finally {
      setProcessing(false)
      setProcessingDryRun(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Batch Configuration */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            <div>
              <CardTitle>Batch Processing Configuration</CardTitle>
              <CardDescription>
                Configure batch processing settings and limits
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-2 gap-6">
            {/* Batch Size */}
            <div className="space-y-2">
              <Label htmlFor="batch-size">Batch Size</Label>
              <Input
                id="batch-size"
                type="number"
                min="1"
                max="1000"
                value={settings.batch_size}
                disabled={saving || !canEdit}
                onChange={(e) => onUpdateSettings({ 
                  batch_size: parseInt(e.target.value) 
                })}
              />
              <p className="text-xs text-gray-500">
                Number of participants to process per batch
              </p>
            </div>

            {/* Max Creates Per Hour */}
            <div className="space-y-2">
              <Label htmlFor="rate-limit">Max Creates Per Hour</Label>
              <Input
                id="rate-limit"
                type="number"
                min="1"
                max="10000"
                value={settings.max_creates_per_hour || 100}
                disabled={saving || !canEdit}
                onChange={(e) => onUpdateSettings({ 
                  max_creates_per_hour: parseInt(e.target.value) 
                })}
              />
              <p className="text-xs text-gray-500">
                Rate limit for auto-creation to prevent overload
              </p>
            </div>
          </div>

          {/* Real-time Creation Toggle */}
          <div className="flex items-center justify-between p-4 border rounded-lg bg-gray-50/50 dark:bg-gray-900/20">
            <div className="flex items-center gap-3">
              <Zap className="h-5 w-5 text-yellow-500" />
              <div className="space-y-0.5">
                <Label>Real-time Creation</Label>
                <p className="text-sm text-gray-500">
                  Process participants immediately as they meet criteria
                </p>
              </div>
            </div>
            <Badge variant={settings.enable_real_time_creation ? "default" : "secondary"}>
              {settings.enable_real_time_creation ? "Enabled" : "Disabled"}
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Manual Processing */}
      <Card>
        <CardHeader>
          <CardTitle>Manual Batch Processing</CardTitle>
          <CardDescription>
            Manually trigger batch processing for eligible participants
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Processing Stats */}
          <div className="grid grid-cols-3 gap-4">
            <div className="p-3 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {settings.batch_size || 100}
              </div>
              <p className="text-xs text-gray-500">Batch Size</p>
            </div>
            <div className="p-3 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {settings.min_messages_before_create || 1}
              </div>
              <p className="text-xs text-gray-500">Min Messages</p>
            </div>
            <div className="p-3 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {settings.auto_create_enabled ? 'ON' : 'OFF'}
              </div>
              <p className="text-xs text-gray-500">Auto-Create</p>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3">
            <Button
              variant="outline"
              onClick={() => handleProcessBatch(true)}
              disabled={!canRunBatch || processingDryRun || processing}
              className="flex-1"
            >
              {processingDryRun ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Running Dry Run...
                </>
              ) : (
                <>
                  <Search className="h-4 w-4 mr-2" />
                  Dry Run
                </>
              )}
            </Button>
            <Button
              onClick={() => handleProcessBatch(false)}
              disabled={!canRunBatch || processing || processingDryRun || !settings.auto_create_enabled}
              className="flex-1"
            >
              {processing ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Process Batch
                </>
              )}
            </Button>
          </div>

          {!canRunBatch && (
            <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
              <p className="text-sm text-red-800 dark:text-red-200">
                You don't have permission to run batch processing
              </p>
            </div>
          )}

          {!settings.auto_create_enabled && (
            <div className="p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
              <p className="text-sm text-amber-800 dark:text-amber-200">
                Auto-creation is currently disabled. Enable it to process batches.
              </p>
            </div>
          )}

          {/* Info Box */}
          <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
            <div className="flex gap-2">
              <Info className="h-4 w-4 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-blue-800 dark:text-blue-200 space-y-1">
                <p>
                  <strong>Dry Run:</strong> Preview what would be created without making changes
                </p>
                <p>
                  <strong>Process Batch:</strong> Actually create contact records for eligible participants
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}