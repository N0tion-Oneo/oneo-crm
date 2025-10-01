// useRealtimeUpdates - Hook for handling WebSocket real-time updates
import { useEffect, useCallback } from 'react'
import { Record, Pipeline } from '@/types/records'
import { usePipelineRecordsSubscription } from '@/hooks/use-websocket-subscription'
import { type RealtimeMessage } from '@/contexts/websocket-context'
import { RealtimeEventService } from '@/services/records'

export interface UseRealtimeUpdatesReturn {
  isConnected: boolean
}

export interface RealtimeUpdateCallbacks {
  onRecordCreate?: (record: Record) => void
  onRecordUpdate?: (record: Record) => void
  onRecordDelete?: (recordId: string) => void
  onError?: (error: Error) => void
}

export function useRealtimeUpdates(
  pipeline: Pipeline,
  callbacks: RealtimeUpdateCallbacks
): UseRealtimeUpdatesReturn {
  const { 
    onRecordCreate = () => {}, 
    onRecordUpdate = () => {}, 
    onRecordDelete = () => {},
    onError = () => {}
  } = callbacks

  const handleRealtimeMessage = useCallback((message: RealtimeMessage) => {
    RealtimeEventService.processMessage(
      message,
      pipeline.id,
      {
        onRecordCreate,
        onRecordUpdate,
        onRecordDelete,
        onError
      }
    )
  }, [pipeline.id, onRecordCreate, onRecordUpdate, onRecordDelete, onError])

  // Debug pipeline ID before subscribing
  console.log('🔍 DEBUGGING: useRealtimeUpdates pipeline ID:', {
    pipelineId: pipeline.id,
    pipelineIdType: typeof pipeline.id,
    pipelineName: pipeline.name,
    channelName: `pipeline_records_${pipeline.id}`
  })

  // Subscribe to pipeline record updates
  const { isConnected } = usePipelineRecordsSubscription(
    pipeline.id,
    handleRealtimeMessage
  )

  // Log connection status changes
  useEffect(() => {
    RealtimeEventService.logConnectionStatus(
      pipeline.id, 
      isConnected, 
      0 // recordCount will be managed by the component using this hook
    )
  }, [pipeline.id, isConnected])

  return {
    isConnected
  }
}