'use client'

import { useEffect, useRef } from 'react'
import { useWebSocket, type RealtimeMessage } from '@/contexts/websocket-context'

interface UseWebSocketSubscriptionOptions {
  channel: string
  onMessage?: (message: RealtimeMessage) => void
  enabled?: boolean
}

/**
 * Hook for subscribing to WebSocket channels
 * Automatically handles subscription/unsubscription lifecycle
 */
export function useWebSocketSubscription({ 
  channel, 
  onMessage, 
  enabled = true 
}: UseWebSocketSubscriptionOptions) {
  const { subscribe, unsubscribe, isConnected, connectionStatus } = useWebSocket()
  const subscriptionIdRef = useRef<string | null>(null)
  const onMessageRef = useRef(onMessage)
  
  // Keep callback ref updated
  useEffect(() => {
    onMessageRef.current = onMessage
  }, [onMessage])
  
  // Handle subscription lifecycle
  useEffect(() => {
    if (!enabled || !channel) {
      return
    }
    
    // Subscribe to channel
    const handleMessage = (message: RealtimeMessage) => {
      onMessageRef.current?.(message)
    }
    
    subscriptionIdRef.current = subscribe(channel, handleMessage)
    
    // Cleanup subscription on unmount or dependency change
    return () => {
      if (subscriptionIdRef.current) {
        unsubscribe(subscriptionIdRef.current)
        subscriptionIdRef.current = null
      }
    }
  }, [channel, enabled, subscribe, unsubscribe])
  
  return {
    isConnected,
    connectionStatus,
    channel: enabled ? channel : null
  }
}

/**
 * Hook for subscribing to pipeline record updates
 */
export function usePipelineRecordsSubscription(
  pipelineId: string,
  onMessage?: (message: RealtimeMessage) => void,
  enabled = true
) {
  return useWebSocketSubscription({
    channel: `pipeline_records_${pipelineId}`,
    onMessage,
    enabled
  })
}

/**
 * Hook for subscribing to document (record) updates for collaborative editing
 */
export function useDocumentSubscription(
  recordId: string,
  onMessage?: (message: RealtimeMessage) => void,
  enabled = true
) {
  return useWebSocketSubscription({
    channel: `document_${recordId}`,
    onMessage,
    enabled
  })
}

/**
 * Hook for subscribing to pipeline updates
 */
export function usePipelineUpdatesSubscription(
  onMessage?: (message: RealtimeMessage) => void,
  enabled = true
) {
  return useWebSocketSubscription({
    channel: 'pipeline_updates',
    onMessage,
    enabled
  })
}

/**
 * Hook for subscribing to user presence updates
 */
export function useUserPresenceSubscription(
  onMessage?: (message: RealtimeMessage) => void,
  enabled = true
) {
  return useWebSocketSubscription({
    channel: 'user_presence',
    onMessage,
    enabled
  })
}

/**
 * Hook for subscribing to permission updates
 * Note: Users are automatically subscribed to permission channels on connection
 */
export function usePermissionUpdatesSubscription(
  onMessage?: (message: RealtimeMessage) => void,
  enabled = true
) {
  return useWebSocketSubscription({
    channel: 'permission_updates',
    onMessage,
    enabled
  })
}

/**
 * Hook for subscribing to pipelines overview updates (all pipeline record counts)
 */
export function usePipelinesOverviewSubscription(
  onMessage?: (message: RealtimeMessage) => void,
  enabled = true
) {
  return useWebSocketSubscription({
    channel: 'pipelines_overview',
    onMessage,
    enabled
  })
}