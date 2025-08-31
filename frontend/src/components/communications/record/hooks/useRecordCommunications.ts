import { useState, useEffect, useCallback } from 'react'
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
  const [stats, setStats] = useState<CommunicationStats | null>(null)
  const [syncStatus, setSyncStatus] = useState<SyncJob[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
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
      return
    }

    try {
      console.log('Fetching communication profile for record:', recordIdStr, 'type:', typeof recordIdStr)
      // Don't add auth header explicitly - axios interceptor handles it
      const response = await api.get(
        `/api/v1/communications/records/${recordIdStr}/profile/`
      )
      console.log('Profile response:', response.data)
      setProfile(response.data)
    } catch (err) {
      console.error('Failed to fetch communication profile:', err)
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
        // Single channel mode - map frontend 'email' to backend channel types
        params.mode = 'channel'
        // Map 'email' tab to gmail (or could be outlook, office365)
        params.channel_type = channelType === 'email' ? 'gmail' : channelType
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
      await api.post(
        `/api/v1/communications/records/${recordIdStr}/mark_read/`,
        {}
      )
      
      // Update local state
      setProfile(prev => prev ? { ...prev, total_unread: 0 } : prev)
      setStats(prev => prev ? { ...prev, total_unread: 0 } : prev)
    } catch (err) {
      console.error('Failed to mark as read:', err)
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
          fetchConversations(),
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
  }, [recordIdStr, accessToken, fetchProfile, fetchConversations, fetchStats, fetchSyncStatus])

  // Poll for sync status updates if sync is in progress
  useEffect(() => {
    if (!profile?.sync_in_progress) return

    const interval = setInterval(() => {
      fetchSyncStatus()
      fetchProfile()
    }, 5000) // Poll every 5 seconds

    return () => clearInterval(interval)
  }, [profile?.sync_in_progress, fetchSyncStatus, fetchProfile])

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
    stats,
    syncStatus,
    isLoading,
    error,
    triggerSync,
    markAsRead,
    refreshData,
    fetchConversations,  // Expose for channel filtering
    fetchConversationMessages  // Expose for message pagination
  }
}