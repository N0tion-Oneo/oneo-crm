import { useState, useEffect, useCallback, useRef } from 'react'
import { useAuth } from '@/features/auth/context'
import { api } from '@/lib/api'
import Cookies from 'js-cookie'

interface CommunicationIdentifiers {
  email: string[]
  phone: string[]
  linkedin: string[]
  domain: string[]
}

interface RecordCommunicationProfile {
  id: string
  record: string
  pipeline: string
  communication_identifiers: CommunicationIdentifiers
  identifier_fields: string[]
  sync_status: Record<string, any>
  last_full_sync: string | null
  sync_in_progress: boolean
  total_conversations: number
  total_messages: number
  total_unread: number
  last_message_at: string | null
  auto_sync_enabled: boolean
  created_at: string
  updated_at: string
}

interface Participant {
  id: string
  name: string
  display_name: string
  email: string
  phone: string
  avatar_url: string
  has_contact: boolean
  resolution_confidence: number
  resolution_method: string
}

interface LastMessage {
  id: string
  content: string
  direction: string
  sent_at: string
  sender_name: string
}

interface Conversation {
  id: string
  subject: string
  channel_name: string
  channel_type: string
  participants: Participant[]
  last_message: LastMessage | null
  last_message_at: string | null
  message_count: number
  unread_count: number
  status: string
  priority: string
  created_at: string
  updated_at: string
}

interface CommunicationStats {
  total_conversations: number
  total_messages: number
  total_unread: number
  last_activity: string | null
  channels: string[]
  participants_count: number
  channel_breakdown?: Record<string, any>
  activity_timeline?: any[]
}

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
  duration?: number
  created_at: string
  trigger_reason: string
}

export function useRecordCommunications(recordId: string | number) {
  // Get access token directly from cookies since it's not in the auth context
  const accessToken = Cookies.get('oneo_access_token')
  const { isAuthenticated } = useAuth() // Still use auth context for authentication status
  
  const [profile, setProfile] = useState<RecordCommunicationProfile | null>(null)
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [timelineMessages, setTimelineMessages] = useState<any[]>([])
  const [stats, setStats] = useState<CommunicationStats | null>(null)
  const [syncStatus, setSyncStatus] = useState<SyncJob[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [timelineOffset, setTimelineOffset] = useState(0)
  const [hasMoreTimeline, setHasMoreTimeline] = useState(true)
  const [syncJustCompleted, setSyncJustCompleted] = useState(false)
  const previousSyncStatusRef = useRef<string | null>(null)
  
  // Convert recordId to string once
  const recordIdStr = recordId ? String(recordId) : ''

  // Fetch communication profile
  const fetchProfile = useCallback(async () => {
    if (!accessToken || !recordIdStr) {
      console.log('fetchProfile skipped - missing accessToken or recordId', { 
        accessToken: !!accessToken, 
        recordIdStr,
        recordIdType: typeof recordIdStr 
      })
      return null
    }

    try {
      console.log('Fetching communication profile for record:', recordIdStr, 'type:', typeof recordIdStr)
      // Don't add auth header explicitly - axios interceptor handles it
      const response = await api.get(
        `/api/v1/communications/records/${recordIdStr}/profile/`
      )
      console.log('Profile response:', response.data)
      setProfile(response.data)
      return response.data
    } catch (err) {
      console.error('Failed to fetch communication profile:', err)
      return null
    }
  }, [recordIdStr, accessToken])

  // Fetch conversations with smart loading or channel filter
  const fetchConversations = useCallback(async (channelType?: string) => {
    if (!accessToken || !recordIdStr) return
    
    try {
      const params: any = {}
      
      if (channelType === 'all' || !channelType) {
        // Use smart mode: all WhatsApp/LinkedIn + last 10 emails
        params.mode = 'smart'
      } else {
        // Single channel mode - backend will handle email type mapping
        params.mode = 'channel'
        // Send the channel type as-is, backend will map 'email' to all email types
        params.channel_type = channelType
        params.limit = channelType === 'email' ? 10 : 100 // Limit emails, get all for social
      }
      
      const response = await api.get(
        `/api/v1/communications/records/${recordIdStr}/conversations/`,
        { params }
      )
      // Handle paginated response
      const data = response.data
      if (data.results) {
        // Paginated response
        setConversations(data.results)
      } else if (Array.isArray(data)) {
        // Legacy non-paginated response
        setConversations(data)
      } else {
        console.error('Unexpected conversation response format:', data)
        setConversations([])
      }
    } catch (err) {
      console.error('Failed to fetch conversations:', err)
      setError('Failed to load conversations')
    }
  }, [recordIdStr, accessToken])

  // Fetch statistics
  const fetchStats = useCallback(async () => {
    if (!accessToken || !recordIdStr) return

    try {
      const response = await api.get(
        `/api/v1/communications/records/${recordIdStr}/stats/`
      )
      setStats(response.data)
    } catch (err) {
      console.error('Failed to fetch stats:', err)
    }
  }, [recordIdStr, accessToken])

  // Fetch sync status
  const fetchSyncStatus = useCallback(async () => {
    if (!accessToken || !recordIdStr) return

    try {
      const response = await api.get(
        `/api/v1/communications/records/${recordIdStr}/sync_status/`
      )
      setSyncStatus(response.data)
    } catch (err) {
      console.error('Failed to fetch sync status:', err)
    }
  }, [recordIdStr, accessToken])

  // Fetch messages for a specific conversation
  const fetchConversationMessages = useCallback(async (
    conversationId: string,
    limit: number = 30,
    offset: number = 0
  ) => {
    if (!accessToken || !recordIdStr || !conversationId) return null

    try {
      const response = await api.get(
        `/api/v1/communications/records/${recordIdStr}/conversation-messages/`,
        {
          params: {
            conversation_id: conversationId,
            limit,
            offset
          }
        }
      )
      return response.data
    } catch (err) {
      console.error('Failed to fetch conversation messages:', err)
      return null
    }
  }, [recordIdStr, accessToken])

  // Fetch timeline messages
  const fetchTimeline = useCallback(async (reset = false) => {
    console.log('fetchTimeline called', { reset, recordIdStr, hasAccessToken: !!accessToken })
    if (!accessToken || !recordIdStr) {
      console.log('fetchTimeline skipped - missing accessToken or recordId')
      return
    }

    try {
      const offset = reset ? 0 : timelineOffset
      const limit = 50
      
      console.log('Fetching timeline:', `/api/v1/communications/records/${recordIdStr}/timeline/`, { limit, offset })
      
      const response = await api.get(
        `/api/v1/communications/records/${recordIdStr}/timeline/`,
        { 
          params: { 
            limit,
            offset
          } 
        }
      )
      
      console.log('Timeline response:', response.data)
      
      // Handle paginated response
      const data = response.data
      let newMessages = []
      let totalCount = 0
      
      if (data.results) {
        // Paginated response
        newMessages = data.results
        totalCount = data.count || newMessages.length
      } else if (Array.isArray(data)) {
        // Legacy non-paginated response
        newMessages = data
        totalCount = data.length
      }
      
      console.log(`Timeline messages received: ${newMessages.length} messages`)
      
      if (reset) {
        setTimelineMessages(newMessages)
        setTimelineOffset(newMessages.length)
      } else {
        setTimelineMessages(prev => [...prev, ...newMessages])
        setTimelineOffset(prev => prev + newMessages.length)
      }
      
      // Check if there are more messages
      setHasMoreTimeline(timelineOffset + newMessages.length < totalCount || newMessages.length === limit)
      
    } catch (err) {
      console.error('Failed to fetch timeline:', err)
      setError('Failed to load timeline messages')
    }
  }, [recordIdStr, accessToken, timelineOffset])

  // Load more timeline messages
  const loadMoreTimeline = useCallback(() => {
    fetchTimeline(false)
  }, [fetchTimeline])

  // Trigger sync
  const triggerSync = useCallback(async (force = false) => {
    if (!accessToken || !recordIdStr) return

    try {
      const response = await api.post(
        `/api/v1/communications/records/${recordIdStr}/sync/`,
        { force }
      )
      
      // Update profile to show sync in progress
      setProfile(prev => prev ? { ...prev, sync_in_progress: true } : prev)
      
      // Refresh sync status
      await fetchSyncStatus()
      
      return response.data
    } catch (err: any) {
      console.error('Failed to trigger sync:', err)
      throw new Error(err.response?.data?.error || 'Failed to start sync')
    }
  }, [recordIdStr, accessToken, fetchSyncStatus])

  // Mark conversations as read
  const markAsRead = useCallback(async () => {
    if (!accessToken || !recordIdStr) return

    try {
      const response = await api.post(
        `/api/v1/communications/records/${recordIdStr}/mark_read/`,
        {}
      )
      
      console.log('Mark as read response:', response.data)
      
      // Update local state
      setProfile(prev => prev ? { ...prev, total_unread: 0 } : prev)
      setStats(prev => prev ? { ...prev, total_unread: 0 } : prev)
      
      // Update conversations to reset unread counts
      setConversations(prev => prev.map(conv => ({
        ...conv,
        unread_count: 0
      })))
      
      return response.data
    } catch (err) {
      console.error('Failed to mark as read:', err)
      throw err
    }
  }, [recordIdStr, accessToken])

  // Initial data fetch
  useEffect(() => {
    console.log('useRecordCommunications - Initial effect triggered', {
      recordId,
      recordIdStr,
      hasAccessToken: !!accessToken,
      accessTokenLength: accessToken?.length
    })
    
    if (!recordIdStr || !accessToken) {
      console.log('useRecordCommunications - Skipping fetch, missing:', {
        recordIdStr: !recordIdStr ? 'missing' : 'present',
        accessToken: !accessToken ? 'missing' : 'present'
      })
      return
    }

    const fetchData = async () => {
      console.log('useRecordCommunications - Starting data fetch')
      setIsLoading(true)
      setError(null)

      try {
        await Promise.all([
          fetchProfile(),
          // Don't fetch conversations here - let the component fetch based on active tab
          // fetchConversations(),
          fetchStats(),
          fetchSyncStatus()
        ])
        console.log('useRecordCommunications - All fetches completed')
      } catch (err) {
        console.error('useRecordCommunications - Fetch error:', err)
        setError('Failed to load communication data')
      } finally {
        setIsLoading(false)
        console.log('useRecordCommunications - Loading complete')
      }
    }

    fetchData()
  }, [recordIdStr, accessToken, fetchProfile, fetchStats, fetchSyncStatus])

  // Poll for sync status updates if sync is in progress
  useEffect(() => {
    if (!profile?.sync_in_progress && !syncStatus[0]?.status) return

    const currentJob = syncStatus[0]
    const previousStatus = previousSyncStatusRef.current

    // Check if sync just completed
    if (previousStatus === 'in_progress' && 
        currentJob?.status === 'completed' && 
        !profile?.sync_in_progress) {
      
      console.log('Sync just completed - refreshing all data')
      setSyncJustCompleted(true)
      
      // Refresh all data
      Promise.all([
        fetchConversations(),
        fetchStats(),
        fetchTimeline(true)
      ]).then(() => {
        console.log('Data refresh completed')
      })
      
      // Clear the sync completed flag after 5 seconds
      setTimeout(() => setSyncJustCompleted(false), 5000)
    }

    // Update previous status for next check
    if (currentJob) {
      previousSyncStatusRef.current = currentJob.status
    }
  }, [syncStatus, profile?.sync_in_progress, fetchConversations, fetchStats, fetchTimeline])

  // Separate polling effect for when sync is in progress
  useEffect(() => {
    if (!profile?.sync_in_progress) return

    const interval = setInterval(async () => {
      await fetchSyncStatus()
      await fetchProfile()
    }, 2000) // Poll every 2 seconds

    return () => clearInterval(interval)
  }, [profile?.sync_in_progress, fetchSyncStatus, fetchProfile])

  // Update a single conversation
  const updateConversation = useCallback((conversationId: string, updates: Partial<Conversation>) => {
    setConversations(prev => prev.map(conv => 
      conv.id === conversationId 
        ? { ...conv, ...updates }
        : conv
    ))
  }, [])

  // Refresh all data
  const refreshData = useCallback(async () => {
    await Promise.all([
      fetchProfile(),
      fetchConversations(),
      fetchStats(),
      fetchSyncStatus()
    ])
  }, [fetchProfile, fetchConversations, fetchStats, fetchSyncStatus])

  return {
    profile,
    conversations,
    timelineMessages,
    stats,
    syncStatus,
    syncJustCompleted,
    isLoading,
    error,
    hasMoreTimeline,
    triggerSync,
    markAsRead,
    updateConversation,
    refreshData,
    fetchConversations,  // Expose for channel filtering
    fetchConversationMessages,  // Expose for message pagination
    fetchTimeline,
    loadMoreTimeline
  }
}