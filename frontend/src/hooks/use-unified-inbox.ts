import { useState, useEffect, useCallback } from 'react'
import { useWebSocket, RealtimeMessage } from '@/contexts/websocket-context'
import { api } from '@/lib/api'

// Transform conversations into Record-grouped format
function transformConversationsToRecords(conversations: any[]): { records: InboxRecord[] } {
  console.log('🔄 Transforming conversations to records:', conversations?.length || 0, 'conversations')
  
  const recordMap = new Map<number, InboxRecord>()
  let unmatched_conversations = 0
  
  conversations.forEach(conversation => {
    const primaryContact = conversation.primary_contact
    if (!primaryContact) {
      unmatched_conversations++
      console.log('⚠️ Skipping conversation without primary_contact for record grouping:', conversation.id)
      return
    }
    
    const recordId = primaryContact.id
    
    // Initialize or get existing record
    let record = recordMap.get(recordId)
    if (!record) {
      record = {
        id: recordId,
        title: primaryContact.name || primaryContact.title || 'Unknown Contact',
        pipeline_name: primaryContact.pipeline_name || 'Unknown Pipeline',
        total_unread: 0,
        last_activity: conversation.updated_at,
        preferred_channel: conversation.type,
        channels: {},
        available_channels: []
      }
      recordMap.set(recordId, record)
      console.log('✅ Created new record:', record.id, record.title)
    }
    
    // Update record with conversation data
    const channelType = conversation.type
    if (!record.channels[channelType]) {
      record.channels[channelType] = {
        channel_type: channelType,
        conversation_count: 0,
        message_count: conversation.message_count || 0,
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
    channelSummary.message_count += conversation.message_count || 0
    
    // Update last message preview
    if (conversation.last_message?.content) {
      channelSummary.last_message_preview = conversation.last_message.content.substring(0, 100)
    }
    
    // Update activity timing
    const conversationTime = new Date(conversation.updated_at).getTime()
    const channelTime = new Date(channelSummary.last_activity).getTime()
    
    if (conversationTime > channelTime) {
      channelSummary.last_activity = conversation.updated_at
    }
    
    // Update record totals
    record.total_unread += conversation.unread_count || 0
    
    const recordTime = new Date(record.last_activity).getTime()
    if (conversationTime > recordTime) {
      record.last_activity = conversation.updated_at
      record.preferred_channel = channelType
    }
    
    // Update available channels
    if (!record.available_channels.includes(channelType)) {
      record.available_channels.push(channelType)
    }
  })
  
  const records = Array.from(recordMap.values()).sort((a, b) => 
    new Date(b.last_activity).getTime() - new Date(a.last_activity).getTime()
  )
  
  console.log('✅ Transformation complete:', {
    total_conversations: conversations?.length || 0,
    unmatched_conversations,
    records_created: records.length,
    total_unread: records.reduce((sum, record) => sum + record.total_unread, 0)
  })
  
  return { records }
}

// Types
interface InboxRecord {
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
  records: InboxRecord[]
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
  selectedRecord: InboxRecord | null
  channelAvailability: ChannelAvailability[]
  
  // Loading states
  loading: boolean
  loadingChannels: boolean
  
  // Actions
  fetchInbox: (options?: { page?: number; limit?: number; forceRefresh?: boolean }) => Promise<void>
  refreshInbox: () => Promise<void>  // Explicit refresh with loading state
  selectRecord: (record: InboxRecord) => void
  refreshRecord: (recordId: number) => Promise<void>
  markAsRead: (recordId: number, channelType: string) => Promise<void>
  updateInboxData: (updater: (prev: UnifiedInboxData | null) => UnifiedInboxData | null) => void
  
  // Real-time updates
  isConnected: boolean
  
  // Error handling
  error: string | null
}

export function useUnifiedInbox(): UseUnifiedInboxReturn {
  const [inboxData, setInboxData] = useState<UnifiedInboxData | null>(null)
  const [selectedRecord, setSelectedRecord] = useState<InboxRecord | null>(null)
  const [channelAvailability, setChannelAvailability] = useState<ChannelAvailability[]>([])
  const [loading, setLoading] = useState(false)  // Start as false - only show loading when actually needed
  const [loadingChannels, setLoadingChannels] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [initialLoad, setInitialLoad] = useState(true)  // Track if this is the first load

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
    console.log('📨 Message type:', message.type)
    console.log('📨 Message payload:', message.payload)
    console.log('📨 Message data:', message.data)
    
    switch (message.type) {
      case 'message_update':
        handleMessageUpdate(message.message || message.payload)
        break
      case 'conversation_update':
        handleConversationUpdate(message.conversation || message.payload)
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

  // Handle message updates - only update the specific conversation/record
  function handleMessageUpdate(messageData: any) {
    console.log('📨 Processing message update:', messageData)
    
    if (!inboxData || !messageData) return
    
    const { conversation_id, message } = messageData
    
    // Find and update only the affected record/conversation
    setInboxData(prev => {
      if (!prev) return prev
      
      // Find which record contains this conversation
      const updatedRecords = prev.records.map(record => {
        // Check if any of this record's channels contain the updated conversation
        const updatedChannels = { ...record.channels }
        let recordUpdated = false
        
        Object.keys(updatedChannels).forEach(channelType => {
          const channel = updatedChannels[channelType]
          
          // Update conversation if it belongs to this channel/record
          if (conversation_id && (record as any).conversations) {
            const conversationExists = (record as any).conversations.some((conv: any) => 
              conv.database_id === conversation_id || conv.id === conversation_id
            )
            
            if (conversationExists) {
              // Update last message preview and activity time
              channel.last_message_preview = message?.content?.substring(0, 100) || ''
              channel.last_activity = messageData.timestamp || new Date().toISOString()
              
              // Increment unread count if message is inbound
              if (message?.direction === 'inbound' || message?.direction === 'in') {
                channel.unread_count = (channel.unread_count || 0) + 1
                record.total_unread = (record.total_unread || 0) + 1
              }
              
              recordUpdated = true
              console.log(`✅ Updated record ${record.id} for new message in conversation ${conversation_id}`)
            }
          }
        })
        
        return recordUpdated ? { ...record, channels: updatedChannels, last_activity: messageData.timestamp || record.last_activity } : record
      })
      
      // Sort records by last activity to show most recent first
      updatedRecords.sort((a, b) => new Date(b.last_activity).getTime() - new Date(a.last_activity).getTime())
      
      // Also update the raw conversations array for consistency
      const updatedConversations = prev.conversations.map(conv => {
        if (conv.database_id === conversation_id || conv.id === conversation_id) {
          return {
            ...conv,
            updated_at: messageData.timestamp || conv.updated_at,
            last_message: message || conv.last_message,
            unread_count: message?.direction === 'inbound' ? (conv.unread_count || 0) + 1 : conv.unread_count
          }
        }
        return conv
      })

      return {
        ...prev,
        records: updatedRecords,
        conversations: updatedConversations
      }
    })
  }

  // Handle conversation updates - only update the specific conversation's metadata
  function handleConversationUpdate(conversationData: any) {
    console.log('💬 Processing conversation update:', conversationData)
    
    if (!inboxData || !conversationData) return
    
    const { conversation_id, message_count, unread_count, last_message_at } = conversationData
    
    // Find and update only the affected conversation
    setInboxData(prev => {
      if (!prev) return prev
      
      const updatedRecords = prev.records.map(record => {
        // Check if this record contains the updated conversation
        const updatedChannels = { ...record.channels }
        let recordUpdated = false
        
        Object.keys(updatedChannels).forEach(channelType => {
          const channel = updatedChannels[channelType]
          
          // Update conversation stats if this channel contains the conversation
          if (conversation_id && (record as any).conversations) {
            const conversationExists = (record as any).conversations.some((conv: any) => 
              conv.database_id === conversation_id || conv.id === conversation_id
            )
            
            if (conversationExists) {
              // Update conversation metadata
              if (message_count !== undefined) channel.message_count = message_count
              if (unread_count !== undefined) {
                const unreadDelta = unread_count - (channel.unread_count || 0)
                channel.unread_count = unread_count
                record.total_unread = Math.max(0, (record.total_unread || 0) + unreadDelta)
              }
              if (last_message_at) {
                channel.last_activity = last_message_at
                record.last_activity = last_message_at
              }
              
              recordUpdated = true
              console.log(`✅ Updated conversation stats for record ${record.id}, conversation ${conversation_id}`)
            }
          }
        })
        
        return recordUpdated ? { ...record, channels: updatedChannels } : record
      })
      
      // Sort records by last activity
      updatedRecords.sort((a, b) => new Date(b.last_activity).getTime() - new Date(a.last_activity).getTime())
      
      return {
        ...prev,
        records: updatedRecords
      }
    })
  }

  // Fetch unified inbox data
  const fetchInbox = useCallback(async (options: { page?: number; limit?: number; forceRefresh?: boolean } = {}) => {
    try {
      // Only show loading on initial load or forced refresh
      if (initialLoad || options.forceRefresh) {
        setLoading(true)
      }
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
      if (initialLoad) {
        setInitialLoad(false)  // Mark initial load as complete
      }
    }
  }, [selectedRecord, initialLoad])

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
  const selectRecord = useCallback((record: InboxRecord) => {
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
    console.log('🔌 Setting up WebSocket subscriptions...')
    console.log('🔌 WebSocket connected:', isConnected)
    console.log('🔌 WebSocket status:', connectionStatus)
    
    const generalSubscription = subscribe('unified_inbox_updates', handleWebSocketMessage)
    console.log('📡 Subscribed to unified_inbox_updates with ID:', generalSubscription)
    
    // Subscribe to record-specific updates if a record is selected
    let recordSubscription: string | null = null
    if (selectedRecord) {
      recordSubscription = subscribe(`record_${selectedRecord.id}_communications`, handleWebSocketMessage)
      console.log(`📡 Subscribed to record ${selectedRecord.id} communications with ID:`, recordSubscription)
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

  // Explicit refresh function that shows loading
  const refreshInbox = useCallback(async () => {
    await fetchInbox({ forceRefresh: true })
  }, [fetchInbox])

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
    refreshInbox,
    selectRecord,
    refreshRecord,
    markAsRead,
    updateInboxData: (updater) => {
      setInboxData(updater)
      // Update selected record if it's affected
      setSelectedRecord(prev => {
        if (!prev) return prev
        const newInboxData = updater(inboxData)
        if (!newInboxData) return prev
        
        const updatedRecord = newInboxData.records.find(record => record.id === prev.id)
        return updatedRecord || prev
      })
    },
    
    // Real-time
    isConnected,
    
    // Error handling
    error
  }
}