import React, { useState } from 'react'
import { RefreshCw, CheckCircle, AlertCircle, Clock, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { formatDistanceToNow } from 'date-fns'
import { cn } from '@/lib/utils'

interface SyncJob {
  id: string
  job_type: string
  status: string
  progress_percentage: number
  current_step: string
  messages_found: number
  conversations_found: number
  new_links_created: number
  error_message?: string
  started_at: string | null
  completed_at: string | null
  created_at: string
  trigger_reason: string
}

interface RecordCommunicationProfile {
  id: string
  sync_in_progress: boolean
  last_full_sync: string | null
  sync_status: Record<string, any>
}

interface SyncStatusIndicatorProps {
  profile: RecordCommunicationProfile | null
  syncStatus: SyncJob[]
  onSync: () => Promise<void>
}

export function SyncStatusIndicator({
  profile,
  syncStatus,
  onSync
}: SyncStatusIndicatorProps) {
  const [isSyncing, setIsSyncing] = useState(false)

  const handleSync = async () => {
    setIsSyncing(true)
    try {
      await onSync()
    } finally {
      // Keep spinning for a bit to show progress
      setTimeout(() => setIsSyncing(false), 2000)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'failed':
        return <AlertCircle className="w-4 h-4 text-red-500" />
      case 'in_progress':
        return <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
      default:
        return <Clock className="w-4 h-4 text-gray-500" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
      case 'failed':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
      case 'in_progress':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
    }
  }

  const latestJob = syncStatus[0]
  const isCurrentlySyncing = profile?.sync_in_progress || latestJob?.status === 'in_progress'

  return (
    <div className="flex items-center space-x-2">
      {/* Last sync time */}
      {profile?.last_full_sync && !isCurrentlySyncing && (
        <span className="text-xs text-gray-500 dark:text-gray-400">
          Last synced {formatDistanceToNow(new Date(profile.last_full_sync), { addSuffix: true })}
        </span>
      )}

      {/* Current sync progress */}
      {isCurrentlySyncing && latestJob && (
        <div className="flex items-center space-x-2">
          <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
          <span className="text-xs text-blue-600 dark:text-blue-400">
            {latestJob.current_step || 'Syncing...'}
          </span>
          {latestJob.progress_percentage > 0 && (
            <span className="text-xs text-gray-500">
              {latestJob.progress_percentage}%
            </span>
          )}
        </div>
      )}

      {/* Sync history popover */}
      {syncStatus.length > 0 && (
        <Popover>
          <PopoverTrigger asChild>
            <Button variant="ghost" size="sm">
              <Clock className="w-4 h-4" />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-96" align="end">
            <div className="space-y-4">
              <h4 className="font-medium text-sm">Sync History</h4>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {syncStatus.slice(0, 5).map((job) => (
                  <div
                    key={job.id}
                    className="flex items-start space-x-2 p-2 rounded border border-gray-200 dark:border-gray-700"
                  >
                    {getStatusIcon(job.status)}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium">
                          {job.trigger_reason}
                        </span>
                        <Badge
                          variant="outline"
                          className={cn('text-xs', getStatusColor(job.status))}
                        >
                          {job.status}
                        </Badge>
                      </div>
                      
                      {job.status === 'completed' && (
                        <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                          Found {job.conversations_found} conversations, {job.messages_found} messages
                          {job.new_links_created > 0 && ` (${job.new_links_created} new)`}
                        </div>
                      )}
                      
                      {job.status === 'failed' && job.error_message && (
                        <div className="mt-1 text-xs text-red-500">
                          {job.error_message}
                        </div>
                      )}
                      
                      <div className="mt-1 text-xs text-gray-400">
                        {formatDistanceToNow(new Date(job.created_at), { addSuffix: true })}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </PopoverContent>
        </Popover>
      )}

      {/* Sync button */}
      <Button
        onClick={handleSync}
        disabled={isSyncing || isCurrentlySyncing}
        size="sm"
        variant="outline"
      >
        <RefreshCw className={cn(
          "w-4 h-4 mr-2",
          (isSyncing || isCurrentlySyncing) && "animate-spin"
        )} />
        {isCurrentlySyncing ? 'Syncing...' : 'Sync'}
      </Button>
    </div>
  )
}