import { useState, useEffect, useCallback } from 'react'
import { useWebSocket, RealtimeMessage } from '@/contexts/websocket-context'
import { api } from '@/lib/api'

// Transform conversations into Record-grouped format
function transformConversationsToRecords(conversations: any[]): { records: Record[] } {
  const recordMap = new Map<number, Record>()
  
  conversations.forEach(conversation => {
    const primaryContact = conversation.primary_contact
    if (!primaryContact) return
    
    const recordId = primaryContact.id
    
    // Initialize or get existing record
    let record = recordMap.get(recordId)
    if (!record) {
      record = {
        id: recordId,
        title: primaryContact.name || 'Unknown Contact',
        pipeline_name: primaryContact.pipeline_name || 'Unknown Pipeline',
        total_unread: 0,
        last_activity: conversation.updated_at,
        preferred_channel: conversation.type,
        channels: {},
        available_channels: []
      }
      recordMap.set(recordId, record)
    }
    
    // Update record with conversation data
    const channelType = conversation.type
    if (!record.channels[channelType]) {
      record.channels[channelType] = {
        channel_type: channelType,
        conversation_count: 0,
        message_count: 0,
        unread_count: 0,
        last_activity: conversation.updated_at,
        last_message_preview: '',
        threading_info: {
          has_threads: false,
          thread_groups: []
        }
      }
    }
    
    // Update channel summary
    const channelSummary = record.channels[channelType]
    channelSummary.conversation_count += 1
    channelSummary.unread_count += conversation.unread_count || 0
    channelSummary.last_message_preview = conversation.last_message?.content || ''
    
    if (new Date(conversation.updated_at) > new Date(channelSummary.last_activity)) {
      channelSummary.last_activity = conversation.updated_at
    }
    
    // Update record totals
    record.total_unread += conversation.unread_count || 0
    if (new Date(conversation.updated_at) > new Date(record.last_activity)) {
      record.last_activity = conversation.updated_at
      record.preferred_channel = channelType
    }
    
    // Update available channels
    if (!record.available_channels.includes(channelType)) {
      record.available_channels.push(channelType)
    }
  })
  
  return {
    records: Array.from(recordMap.values()).sort((a, b) => 
      new Date(b.last_activity).getTime() - new Date(a.last_activity).getTime()
    )
  }
}

// Types
interface Record {
  id: number
  title: string
  pipeline_name: string
  total_unread: number
  last_activity: string
  preferred_channel: string
  channels: Record<string, ChannelSummary>
  available_channels: string[]
}

interface ChannelSummary {
  channel_type: string
  conversation_count: number
  message_count: number
  unread_count: number
  last_activity: string
  last_message_preview: string
  threading_info: {
    has_threads: boolean
    thread_groups: Array<{
      id: string
      type: string
      strategy: string
      conversations: number
    }>
  }
}

interface UnifiedInboxData {
  records: Record[]
  conversations: any[] // Raw conversation data from API
  total_count: number
  has_next: boolean
  has_previous: boolean
  current_page: number
  total_pages: number
}

interface ChannelAvailability {
  channel_type: string
  display_name: string
  status: 'available' | 'limited' | 'historical' | 'unavailable'
  user_connected: boolean
  contact_info_available: boolean
  has_history: boolean
  priority: number
  limitations: string[]
  history?: {
    total_messages: number
    last_contact: string
    response_rate: number
    engagement_score: number
  }
}

interface UseUnifiedInboxReturn {
  // Data
  inboxData: UnifiedInboxData | null
  selectedRecord: Record | null
  channelAvailability: ChannelAvailability[]
  
  // Loading states
  loading: boolean
  loadingChannels: boolean
  
  // Actions
  fetchInbox: (options?: { page?: number; limit?: number }) => Promise<void>
  selectRecord: (record: Record) => void
  refreshRecord: (recordId: number) => Promise<void>
  markAsRead: (recordId: number, channelType: string) => Promise<void>
  
  // Real-time updates
  isConnected: boolean
  
  // Error handling
  error: string | null
}

export function useUnifiedInbox(): UseUnifiedInboxReturn {
  const [inboxData, setInboxData] = useState<UnifiedInboxData | null>(null)
  const [selectedRecord, setSelectedRecord] = useState<Record | null>(null)
  const [channelAvailability, setChannelAvailability] = useState<ChannelAvailability[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingChannels, setLoadingChannels] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Use centralized WebSocket context (same as working Conversations view)
  const {
    isConnected,
    connectionStatus,
    subscribe,
    unsubscribe,
    sendMessage
  } = useWebSocket()

  // Handle WebSocket messages
  const handleWebSocketMessage = useCallback((message: RealtimeMessage) => {
    console.log('📨 Unified Inbox WebSocket message:', message)
    
    switch (message.type) {
      case 'message_update':
        handleMessageUpdate(message.message || message.payload)
        break
      case 'new_conversation':
        handleConversationUpdate(message.conversation || message.payload)
        break
      case 'activity_update':
        // Handle activity updates that might include communication changes
        const activityData = message.data || message.payload
        if (activityData && activityData.type === 'communication') {
          handleUnifiedInboxUpdate(activityData)
        }
        break
      default:
        console.log('Unhandled unified inbox WebSocket message type:', message.type)
    }
  }, [])

  // Handle unified inbox updates
  function handleUnifiedInboxUpdate(updateData: any) {
    if (!inboxData) return

    const { message_id, conversation_id, channel_type, direction, contact_record, unread } = updateData

    // Update record in inbox data
    if (contact_record) {
      setInboxData(prev => {
        if (!prev) return prev

        const updatedRecords = prev.records.map(record => {
          if (record.id === contact_record.id) {
            // Update unread count
            const unreadDelta = unread && direction === 'inbound' ? 1 : 0
            
            // Update channel info
            const updatedChannels = { ...record.channels }
            if (updatedChannels[channel_type]) {
              updatedChannels[channel_type] = {
                ...updatedChannels[channel_type],
                unread_count: updatedChannels[channel_type].unread_count + unreadDelta,
                last_activity: updateData.timestamp,
                last_message_preview: updateData.content_preview || ''
              }
            }

            return {
              ...record,
              total_unread: record.total_unread + unreadDelta,
              last_activity: updateData.timestamp,
              channels: updatedChannels
            }
          }
          return record
        })

        // Sort records by last activity (most recent first)
        updatedRecords.sort((a, b) => 
          new Date(b.last_activity).getTime() - new Date(a.last_activity).getTime()
        )

        return {
          ...prev,
          records: updatedRecords
        }
      })

      // Update selected record if it matches
      if (selectedRecord && selectedRecord.id === contact_record.id) {
        setSelectedRecord(prev => {
          if (!prev) return prev
          
          const unreadDelta = unread && direction === 'inbound' ? 1 : 0
          const updatedChannels = { ...prev.channels }
          
          if (updatedChannels[channel_type]) {
            updatedChannels[channel_type] = {
              ...updatedChannels[channel_type],
              unread_count: updatedChannels[channel_type].unread_count + unreadDelta,
              last_activity: updateData.timestamp,
              last_message_preview: updateData.content_preview || ''
            }
          }

          return {
            ...prev,
            total_unread: prev.total_unread + unreadDelta,
            last_activity: updateData.timestamp,
            channels: updatedChannels
          }
        })
      }
    }
  }

  // Handle message updates
  function handleMessageUpdate(message: any) {
    // This could trigger updates to the conversation timeline
    // Implementation depends on timeline component
    console.log('Message update received:', message)
  }

  // Handle conversation updates
  function handleConversationUpdate(conversation: any) {
    // This could trigger updates to conversation metadata
    console.log('Conversation update received:', conversation)
  }

  // Fetch unified inbox data
  const fetchInbox = useCallback(async (options: { page?: number; limit?: number } = {}) => {
    try {
      setLoading(true)
      setError(null)
      
      const params: any = {}
      if (options.page) params.offset = (options.page - 1) * (options.limit || 50)
      if (options.limit) params.limit = options.limit
      
      const response = await api.get('/api/v1/communications/local-inbox/', { params })
      
      const rawData = response.data
      
      // Transform conversation data into Record-grouped format
      const transformedData = transformConversationsToRecords(rawData.conversations || [])
      
      setInboxData({
        records: transformedData.records,
        conversations: rawData.conversations || [],
        total_count: transformedData.records.length,
        has_next: false, // Simple implementation - could add pagination later
        has_previous: false,
        current_page: 1,
        total_pages: 1
      })
      
      // Auto-select first record if none selected
      if (transformedData.records.length > 0 && !selectedRecord) {
        setSelectedRecord(transformedData.records[0])
        // Skip channel availability fetching for now - use data from conversations
      }
      
    } catch (error: any) {
      console.error('Error fetching unified inbox:', error)
      setError(error.response?.data?.error || error.message || 'Failed to fetch inbox')
    } finally {
      setLoading(false)
    }
  }, [selectedRecord])

  // Fetch channel availability for a record
  const fetchChannelAvailability = useCallback(async (recordId: number) => {
    try {
      setLoadingChannels(true)
      
      const response = await api.get(`/api/v1/communications/records/${recordId}/channels/`)
      
      const data = response.data
      setChannelAvailability(data.available_channels || [])
      
    } catch (error: any) {
      console.error('Error fetching channel availability:', error)
    } finally {
      setLoadingChannels(false)
    }
  }, [])

  // Select a record
  const selectRecord = useCallback((record: Record) => {
    setSelectedRecord(record)
    // Use available_channels from the record instead of separate API call
    setChannelAvailability(
      record.available_channels.map(channelType => ({
        channel_type: channelType,
        display_name: channelType.charAt(0).toUpperCase() + channelType.slice(1),
        status: 'available' as const,
        user_connected: true,
        contact_info_available: true,
        has_history: true,
        priority: 1,
        limitations: []
      }))
    )
  }, [])

  // Refresh a specific record
  const refreshRecord = useCallback(async (recordId: number) => {
    try {
      // Just refresh inbox data for now - skip cache invalidation
      await fetchInbox()
      
    } catch (error: any) {
      console.error('Error refreshing record:', error)
    }
  }, [fetchInbox])

  // Mark conversation as read
  const markAsRead = useCallback(async (recordId: number, channelType: string) => {
    try {
      // Find conversations for this record and channel type from our data
      if (!inboxData?.conversations) return
      
      const conversationsToMarkRead = inboxData.conversations.filter(conversation => 
        conversation.primary_contact?.id === recordId && 
        conversation.type === channelType
      )
      
      // Mark each conversation as read using the working API
      for (const conversation of conversationsToMarkRead) {
        await api.post(`/api/v1/communications/conversations/${conversation.id}/mark-read/`)
      }
      
      // Update local state
      setInboxData(prev => {
        if (!prev) return prev
        
        const updatedRecords = prev.records.map(record => {
          if (record.id === recordId) {
            const channelUnread = record.channels[channelType]?.unread_count || 0
            const updatedChannels = { ...record.channels }
            
            if (updatedChannels[channelType]) {
              updatedChannels[channelType] = {
                ...updatedChannels[channelType],
                unread_count: 0
              }
            }
            
            return {
              ...record,
              total_unread: record.total_unread - channelUnread,
              channels: updatedChannels
            }
          }
          return record
        })
        
        return {
          ...prev,
          records: updatedRecords
        }
      })
      
      // Update selected record
      if (selectedRecord && selectedRecord.id === recordId) {
        setSelectedRecord(prev => {
          if (!prev) return prev
          
          const channelUnread = prev.channels[channelType]?.unread_count || 0
          const updatedChannels = { ...prev.channels }
          
          if (updatedChannels[channelType]) {
            updatedChannels[channelType] = {
              ...updatedChannels[channelType],
              unread_count: 0
            }
          }
          
          return {
            ...prev,
            total_unread: prev.total_unread - channelUnread,
            channels: updatedChannels
          }
        })
      }
      
    } catch (error: any) {
      console.error('Error marking as read:', error)
    }
  }, [selectedRecord, inboxData])

  // Initial load
  useEffect(() => {
    fetchInbox()
  }, [fetchInbox])

  // Subscribe to unified inbox channels using centralized WebSocket
  useEffect(() => {
    if (!isConnected) return
    
    console.log('📡 Setting up unified inbox WebSocket subscriptions')
    
    // Subscribe to general communication updates
    const generalSubscription = subscribe('unified_inbox_updates', handleWebSocketMessage)
    
    // Subscribe to record-specific updates if a record is selected
    let recordSubscription: string | null = null
    if (selectedRecord) {
      recordSubscription = subscribe(`record_${selectedRecord.id}_communications`, handleWebSocketMessage)
      console.log(`📡 Subscribed to record ${selectedRecord.id} communications`)
    }
    
    // Cleanup subscriptions
    return () => {
      unsubscribe(generalSubscription)
      if (recordSubscription) {
        unsubscribe(recordSubscription)
      }
      console.log('📡 Unified inbox unsubscribed from communication channels')
    }
  }, [isConnected, selectedRecord, subscribe, unsubscribe, handleWebSocketMessage])

  return {
    // Data
    inboxData,
    selectedRecord,
    channelAvailability,
    
    // Loading states
    loading,
    loadingChannels,
    
    // Actions
    fetchInbox,
    selectRecord,
    refreshRecord,
    markAsRead,
    
    // Real-time
    isConnected,
    
    // Error handling
    error
  }
}