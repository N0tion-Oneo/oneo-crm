'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import { MessageSquare, Mail, Phone, Search, Filter, Paperclip, Send, MoreVertical, Archive, Reply, Forward, Star, StarOff, Users, TrendingUp, Clock, CheckCircle2, AlertCircle, Plus, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { useToast } from '@/hooks/use-toast'
import { useAuth } from '@/features/auth/context'
import { communicationsApi } from '@/lib/api'
import { MessageComposer } from '@/components/communications/message-composer'
import { WhatsAppIdentityHandler } from '@/components/communications/WhatsAppIdentityHandler'
import { ContactResolutionBadge, ContactResolutionIndicator } from '@/components/communications/contact-resolution-badge'
import { ContactResolutionDialog } from '@/components/communications/contact-resolution-dialog'
import { RecordDetailDrawer } from '@/components/pipelines/record-detail-drawer'
import { useContactResolution, useMessageContactStatus } from '@/hooks/use-contact-resolution'
import { useWebSocket, type RealtimeMessage } from '@/contexts/websocket-context'
import { pipelinesApi } from '@/lib/api'
import ConversationTimeline from '@/components/communications/conversation-timeline'
import CommunicationAnalytics from '@/components/communications/communication-analytics'
import SmartCompose from '@/components/communications/smart-compose'
import { useUnifiedInbox } from '@/hooks/use-unified-inbox'
import { MessageContent } from '@/components/MessageContent'
import { formatDistanceToNow } from 'date-fns'
import GmailInboxRefactored from '@/components/communications/email/GmailInboxRefactored'
import { WhatsAppInboxLive } from '@/components/communications/WhatsAppInboxLive'
import LinkedInInbox from '@/components/communications/LinkedInInbox'

// Enhanced types that combine old and new functionality
interface Message {
  id: string
  type: 'email' | 'linkedin' | 'whatsapp' | 'sms'
  subject?: string
  content: string
  direction: 'inbound' | 'outbound'
  contact_email: string
  sender: {
    name: string
    email?: string
    avatar?: string
    platform_id?: string
  }
  recipient: {
    name: string
    email?: string
  }
  timestamp: string
  is_read: boolean
  is_starred: boolean
  attachments?: Array<{
    name: string
    size: number
    type: string
    url: string
  }>
  conversation_id: string
  account_id: string
  external_id: string
  metadata?: {
    contact_name?: string
    sender_attendee_id?: string
    chat_id?: string
    from?: string
    to?: string
    is_sender?: number
    profile_picture?: string
    seen?: boolean
    delivery_status?: string
    raw_webhook_data?: {
      body?: string | {
        html?: string
        text?: string
      }
      formatted_content?: {
        html?: string
        text?: string
      }
    }
  }
  channel?: {
    name: string
    channel_type: string
  }
}

interface Conversation {
  id: string
  database_id?: string
  participants?: Array<{
    name: string
    email?: string
    avatar?: string
    platform: string
  }>
  last_message: Message
  unread_count: number
  type: 'email' | 'linkedin' | 'whatsapp' | 'sms'
  created_at: string
  updated_at: string
  primary_contact?: {
    id: string
    name: string
    email?: string
    pipeline_name: string
  }
  needs_manual_resolution?: boolean
  domain_validated?: boolean
  needs_domain_review?: boolean
}

interface UnifiedRecord {
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

interface InboxFilters {
  search: string
  type: 'all' | 'email' | 'linkedin' | 'whatsapp' | 'sms'
  status: 'all' | 'unread' | 'starred'
  account: string
}

export default function InboxPage() {
  // Channel-specific inbox state
  const [activeChannelTab, setActiveChannelTab] = useState<'unified' | 'gmail' | 'whatsapp' | 'linkedin'>('unified')
  
  // View mode state: 'conversations' (old style) or 'records' (new unified style)
  const [viewMode, setViewMode] = useState<'conversations' | 'records'>('records')
  
  // Old conversation-based states
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingMessages, setLoadingMessages] = useState(false)
  const [composing, setComposing] = useState(false)
  const [replyText, setReplyText] = useState('')
  const [filters, setFilters] = useState<InboxFilters>({
    search: '',
    type: 'all',
    status: 'all',
    account: 'all'
  })
  
  // Message composer and resolution states
  const [composeDialogOpen, setComposeDialogOpen] = useState(false)
  const [replyingTo, setReplyingTo] = useState<Message | null>(null)
  const [accountConnections, setAccountConnections] = useState<any[]>([])
  const [contactResolutionOpen, setContactResolutionOpen] = useState(false)
  const [selectedMessageForResolution, setSelectedMessageForResolution] = useState<any>(null)
  
  // Contact viewing states
  const [contactViewerOpen, setContactViewerOpen] = useState(false)
  const [selectedContactRecord, setSelectedContactRecord] = useState<any>(null)
  const [selectedContactPipeline, setSelectedContactPipeline] = useState<any>(null)
  
  // Records view search and filter states
  const [recordsSearchQuery, setRecordsSearchQuery] = useState('')
  const [recordsFilter, setRecordsFilter] = useState<'all' | 'unread' | 'recent' | 'unconnected'>('all')
  
  // WebSocket states
  const [wsStatus, setWsStatus] = useState<string>('disconnected')
  const [conversationSubscriptionId, setConversationSubscriptionId] = useState<string | null>(null)
  
  // New unified inbox state
  const [showSmartCompose, setShowSmartCompose] = useState(false)
  
  const { toast } = useToast()
  const { tenant, user, isAuthenticated, isLoading: authLoading } = useAuth()
  
  // Contact resolution hook
  const { unmatchedCount, warningsCount, refresh: refreshContactResolution } = useContactResolution()
  
  // New unified inbox hook (only used in records view mode)
  const {
    inboxData,
    selectedRecord,
    channelAvailability,
    loading: unifiedLoading,
    loadingChannels,
    fetchInbox,
    selectRecord,
    refreshRecord,
    markAsRead,
    updateInboxData,
    isConnected: unifiedWSConnected,
    error: unifiedError
  } = useUnifiedInbox()

  // Real-time message handler for both conversation and records views
  const handleNewMessage = useCallback((message: any) => {
    console.log('🔥 Real-time message received:', message)
    
    // Add message to current conversation if it's open (Conversations view)
    if (viewMode === 'conversations' && selectedConversation && message.conversation_id === selectedConversation.id) {
      setMessages(prev => {
        // Check if message already exists to prevent duplicates
        const exists = prev.some(msg => msg.id === message.id)
        if (exists) return prev
        
        // Add new message
        return [...prev, message].sort((a, b) => 
          new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
        )
      })
    }
    
    // Update conversation list with new last message (Conversations view)
    setConversations(prev => prev.map(conv => {
      if (conv.id === message.conversation_id) {
        // Only increment unread count if message is inbound AND conversation is not currently selected
        const shouldIncrementUnread = message.direction === 'inbound' && 
          (!selectedConversation || selectedConversation.id !== message.conversation_id)
        
        return {
          ...conv,
          last_message: message,
          unread_count: shouldIncrementUnread ? conv.unread_count + 1 : conv.unread_count,
          updated_at: message.timestamp
        }
      }
      return conv
    }).sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()))
    
    // Update records view if we have inbox data (Records view)
    if (viewMode === 'records' && inboxData?.conversations) {
      // Find which conversation this message belongs to
      const conversation = inboxData.conversations.find(conv => conv.id === message.conversation_id)
      
      if (conversation && conversation.primary_contact) {
        console.log('🔄 Updating record data for message:', message.id)
        
        // Update the conversations array in inboxData
        const updatedConversations = inboxData.conversations.map(conv => {
          if (conv.id === message.conversation_id) {
            const shouldIncrementUnread = message.direction === 'inbound'
            
            return {
              ...conv,
              last_message: message,
              unread_count: shouldIncrementUnread ? (conv.unread_count || 0) + 1 : conv.unread_count,
              updated_at: message.timestamp
            }
          }
          return conv
        })
        
        // Refresh the unified inbox data to get updated record groupings
        fetchInbox()
      }
    }
    
    // Show toast for new messages when conversation is not selected
    if (message.direction === 'inbound' && (!selectedConversation || message.conversation_id !== selectedConversation.id)) {
      // Use WhatsApp identity handler for display
      const displayInfo = message.type === 'whatsapp' 
        ? WhatsAppIdentityHandler.formatMessageDisplay(message, user?.email)
        : { senderName: message.sender?.name || 'Unknown', isFromBusiness: false }
      
      if (!displayInfo.isFromBusiness) {
        toast({
          title: `New message from ${displayInfo.senderName}`,
          description: message.content.replace(/<[^>]*>/g, '').slice(0, 100) + (message.content.length > 100 ? '...' : ''),
        })
      }
    }
  }, [selectedConversation, viewMode, inboxData, selectedRecord, updateInboxData, toast, user?.email])

  // Real-time conversation update handler
  const handleConversationUpdate = useCallback((conversation: any) => {
    console.log('🔥 Real-time conversation update:', conversation)
    
    setConversations(prev => {
      // Check if conversation already exists
      const existingIndex = prev.findIndex(conv => conv.id === conversation.id)
      
      if (existingIndex >= 0) {
        // Update existing conversation
        const updated = [...prev]
        updated[existingIndex] = { ...updated[existingIndex], ...conversation }
        return updated.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
      } else {
        // Add new conversation
        return [conversation, ...prev].sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
      }
    })
  }, [])

  // WebSocket connection status handler
  const handleConnectionStatusChange = useCallback((status: string) => {
    console.log('🔌 WebSocket status changed:', status)
    setWsStatus(status)
    
    if (status === 'connected') {
      toast({
        title: "Real-time messaging connected",
        description: "You'll now receive messages instantly",
      })
    } else if (status === 'error') {
      toast({
        title: "Real-time connection error",
        description: "Messages may not update in real-time",
        variant: "destructive",
      })
    }
  }, [toast])

  // Use centralized WebSocket connection
  const {
    isConnected: wsConnected,
    connectionStatus: wsConnectionStatus,
    subscribe,
    unsubscribe
  } = useWebSocket()

  // Subscribe to communication channel updates when WebSocket connects
  useEffect(() => {
    if (!wsConnected || !accountConnections.length) return

    const subscriptions: string[] = []

    // Subscribe to all communication channels for conversation list updates
    accountConnections.forEach(connection => {
      if (connection.canSendMessages && connection.channelId) {
        const channelId = connection.channelId  // Use the actual Channel ID from backend
        console.log(`🔔 Subscribing to channel updates: channel_${channelId}`)
        
        const channelSubscriptionId = subscribe(`channel_${channelId}`, (message: RealtimeMessage) => {
          console.log('📨 Channel update received:', message)
          
          // Handle conversation list updates - backend sends conversation data directly
          if (message.type === 'new_conversation' && message.conversation) {
            handleConversationUpdate(message.conversation)
          }
        })
        subscriptions.push(channelSubscriptionId)
      }
    })

    console.log(`✅ WebSocket subscribed to ${subscriptions.length} communication channels`)
    
    return () => {
      // Cleanup subscriptions
      subscriptions.forEach(id => unsubscribe(id))
    }
  }, [wsConnected, accountConnections, subscribe, unsubscribe, handleConversationUpdate])

  // Cleanup conversation subscription on unmount
  useEffect(() => {
    return () => {
      if (conversationSubscriptionId) {
        unsubscribe(conversationSubscriptionId)
      }
    }
  }, [conversationSubscriptionId, unsubscribe])

  // Load conversations and account connections
  useEffect(() => {
    if (isAuthenticated && !authLoading && user && tenant && viewMode === 'conversations') {
      loadConversations()
      loadAccountConnections()
    }
  }, [isAuthenticated, authLoading, user, tenant, filters, viewMode])

  // Load unified inbox data for Records view
  useEffect(() => {
    if (isAuthenticated && !authLoading && user && tenant && viewMode === 'records') {
      console.log('🔄 Loading Records view data...')
      fetchInbox()
      loadAccountConnections() // Also load account connections for compose functionality
    }
  }, [isAuthenticated, authLoading, user, tenant, viewMode, fetchInbox])

  const loadAccountConnections = async () => {
    try {
      const response = await communicationsApi.getConnections()
      setAccountConnections(response.data.results || response.data || [])
    } catch (error) {
      console.error('Error loading account connections:', error)
    }
  }

  const loadConversations = async () => {
    try {
      setLoading(true)
      const response = await communicationsApi.getUnifiedInbox(filters)
      const conversations = response.data.conversations || []
      
      console.log(`📨 Loaded ${conversations.length} conversations:`)      
      setConversations(conversations)
    } catch (error: any) {
      console.error('Error loading conversations:', error)
      toast({
        title: "Failed to load conversations",
        description: error.response?.data?.error || "An error occurred",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const loadMessages = async (conversationId: string) => {
    try {
      setLoadingMessages(true)
      const response = await communicationsApi.getConversationMessages(conversationId)
      setMessages(response.data.messages || [])
    } catch (error: any) {
      console.error('Error loading messages:', error)
      toast({
        title: "Failed to load messages",
        description: error.response?.data?.error || "An error occurred",
        variant: "destructive",
      })
    } finally {
      setLoadingMessages(false)
    }
  }

  const handleConversationSelect = (conversation: Conversation) => {
    // Unsubscribe from previous conversation
    if (conversationSubscriptionId) {
      unsubscribe(conversationSubscriptionId)
      setConversationSubscriptionId(null)
    }

    setSelectedConversation(conversation)
    loadMessages(conversation.id)
    
    // Subscribe to real-time updates for this conversation
    if (wsConnected) {
      const subscriptionId = conversation.database_id || conversation.id
      console.log(`🔔 Subscribing to conversation: conversation_${subscriptionId}`)
      const newSubscriptionId = subscribe(`conversation_${subscriptionId}`, (message: RealtimeMessage) => {
        console.log('📨 Conversation message received:', message)
        
        if (message.type === 'message_update' && message.message) {
          handleNewMessage(message.message)
        }
      })
      setConversationSubscriptionId(newSubscriptionId)
    }
    
    // Mark conversation as read
    if (conversation.unread_count > 0) {
      markConversationAsRead(conversation.id)
    }
  }

  const markConversationAsRead = async (conversationId: string) => {
    try {
      await communicationsApi.markConversationAsRead(conversationId)
      // Update local state
      setConversations(prev => prev.map(conv => 
        conv.id === conversationId 
          ? { ...conv, unread_count: 0 }
          : conv
      ))
    } catch (error) {
      console.error('Error marking conversation as read:', error)
    }
  }

  const handleSendReply = async () => {
    if (!selectedConversation || !replyText.trim() || composing) return

    setComposing(true)
    try {
      const newMessage = {
        conversation_id: selectedConversation.id,
        content: replyText.trim(),
        type: selectedConversation.type
      }

      await communicationsApi.sendMessage(newMessage)
      
      // Reload messages
      loadMessages(selectedConversation.id)
      
      // Clear reply text
      setReplyText('')
      
      toast({
        title: "Message sent",
        description: "Your message has been sent successfully.",
      })
    } catch (error: any) {
      console.error('Error sending message:', error)
      toast({
        title: "Failed to send message",
        description: error.response?.data?.error || "An error occurred",
        variant: "destructive",
      })
    } finally {
      setComposing(false)
    }
  }

  const handleContactResolution = (message: any) => {
    console.log('🔍 Opening contact resolution dialog for message:', message)
    setSelectedMessageForResolution(message)
    setContactResolutionOpen(true)
  }

  const handleViewContact = async (contactRecord: any) => {
    try {
      console.log('🔍 handleViewContact called with:', contactRecord)
      
      const pipelinesResponse = await pipelinesApi.list()
      const pipelines = pipelinesResponse.data.results || pipelinesResponse.data || []
      
      let basicPipeline = pipelines.find((p: any) => p.name === contactRecord.pipeline_name)
      if (!basicPipeline && pipelines.length > 0) {
        basicPipeline = pipelines[0]
      }
      
      if (!basicPipeline) {
        throw new Error('No pipelines found')
      }
      
      const fullPipelineResponse = await pipelinesApi.get(basicPipeline.id)
      let pipeline = fullPipelineResponse.data
      
      if (!pipeline.fields || !Array.isArray(pipeline.fields)) {
        pipeline.fields = []
      }
      
      let record = null
      
      try {
        const recordResponse = await pipelinesApi.getRecord(pipeline.id, contactRecord.id)
        record = recordResponse.data
      } catch (recordError) {
        console.error('❌ Failed to load record from selected pipeline:', recordError)
        
        let foundRecord = null
        let foundPipeline = null
        
        for (const testPipeline of pipelines) {
          try {
            const testResponse = await pipelinesApi.getRecord(testPipeline.id, contactRecord.id)
            foundRecord = testResponse.data
            foundPipeline = testPipeline
            break
          } catch (e) {
            // Record not in this pipeline, continue searching
          }
        }
        
        if (foundRecord && foundPipeline) {
          const correctPipelineResponse = await pipelinesApi.get(foundPipeline.id)
          pipeline = correctPipelineResponse.data
          record = foundRecord
        } else {
          throw new Error(`Record ${contactRecord.id} not found in any pipeline`)
        }
      }
      
      if (!record) {
        throw new Error('No record data found')
      }
      
      const formattedRecord = {
        ...record,
        data: record.data || {},
        id: record.id,
        title: record.title,
        created_at: record.created_at,
        updated_at: record.updated_at,
        pipeline: record.pipeline
      }
      
      setSelectedContactRecord(formattedRecord)
      setSelectedContactPipeline(pipeline)
      setContactViewerOpen(true)
    } catch (error) {
      console.error('❌ Error loading contact details:', error)
      toast({
        title: "Error",
        description: "Failed to load contact details",
        variant: "destructive",
      })
    }
  }

  const handleContactAction = (conversation: any) => {
    console.log('🔍 handleContactAction called with conversation:', conversation)
    
    if (conversation.primary_contact) {
      handleViewContact(conversation.primary_contact)
    } else {
      // Create a message object compatible with ContactResolutionDialog
      const messageForResolution = {
        id: conversation.id,
        contact_email: conversation.last_message?.contact_email || conversation.participants?.[0]?.email || '',
        needs_manual_resolution: conversation.needs_manual_resolution,
        domain_validated: conversation.domain_validated,
        needs_domain_review: conversation.needs_domain_review,
        unmatched_contact_data: {
          email: conversation.last_message?.contact_email || conversation.participants?.[0]?.email,
          name: conversation.participants?.[0]?.name,
          phone: conversation.last_message?.contact_phone || conversation.participants?.[0]?.phone
        }
      }
      
      console.log('🔍 Created message for resolution:', messageForResolution)
      handleContactResolution(messageForResolution)
    }
  }

  const handleResolutionComplete = async (messageId: string, contactRecord: any) => {
    console.log(`🔗 Contact resolution completed for message ${messageId}:`, contactRecord)
    
    if (viewMode === 'conversations') {
      await loadConversations()
    } else {
      await fetchInbox()
    }
    await refreshContactResolution()
    
    toast({
      title: "Contact resolved",
      description: `Message connected to ${contactRecord.title}`,
    })
  }

  const getMessageTypeIcon = (type: string) => {
    switch (type) {
      case 'email': return <Mail className="w-4 h-4" />
      case 'linkedin': return <MessageSquare className="w-4 h-4" />
      case 'whatsapp': return <MessageSquare className="w-4 h-4" />
      case 'sms': return <Phone className="w-4 h-4" />
      default: return <MessageSquare className="w-4 h-4" />
    }
  }

  const getMessageTypeBadge = (type: string) => {
    const safeType = type || 'unknown'
    
    const colors = {
      email: 'bg-blue-100 text-blue-800',
      linkedin: 'bg-blue-600 text-white',
      whatsapp: 'bg-green-100 text-green-800',
      sms: 'bg-purple-100 text-purple-800',
      unknown: 'bg-gray-100 text-gray-800'
    }
    
    return (
      <Badge className={`${colors[safeType as keyof typeof colors] || colors.unknown} text-xs`}>
        {safeType.toUpperCase()}
      </Badge>
    )
  }

  const getChannelIcon = (channelType: string) => {
    switch (channelType) {
      case 'whatsapp': return <MessageSquare className="h-4 w-4" />
      case 'linkedin': return <MessageSquare className="h-4 w-4" />
      case 'gmail':
      case 'outlook':
      case 'mail': return <Mail className="h-4 w-4" />
      case 'phone': return <Phone className="h-4 w-4" />
      case 'instagram': return <MessageSquare className="h-4 w-4" />
      default: return <MessageSquare className="h-4 w-4" />
    }
  }

  const getChannelColor = (channelType: string) => {
    switch (channelType) {
      case 'whatsapp': return 'bg-green-500'
      case 'linkedin': return 'bg-blue-600'
      case 'gmail': return 'bg-red-500'
      case 'outlook': return 'bg-blue-500'
      case 'instagram': return 'bg-purple-500'
      default: return 'bg-gray-500'
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'available': return 'text-green-600 bg-green-50 border-green-200'
      case 'limited': return 'text-yellow-600 bg-yellow-50 border-yellow-200'
      case 'historical': return 'text-blue-600 bg-blue-50 border-blue-200'
      default: return 'text-gray-600 bg-gray-50 border-gray-200'
    }
  }

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diffInHours = (now.getTime() - date.getTime()) / (1000 * 60 * 60)
    
    if (diffInHours < 24) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    } else if (diffInHours < 168) { // 7 days
      return date.toLocaleDateString([], { weekday: 'short' })
    } else {
      return date.toLocaleDateString([], { month: 'short', day: 'numeric' })
    }
  }

  const currentLoading = viewMode === 'conversations' ? loading : unifiedLoading
  const currentError = viewMode === 'conversations' ? null : unifiedError

  // Filter records or get unconnected conversations based on filter criteria
  const { filteredRecords, unconnectedConversations } = useMemo(() => {
    if (!inboxData) return { filteredRecords: [], unconnectedConversations: [] }
    
    // Handle unconnected conversations separately
    if (recordsFilter === 'unconnected') {
      let unconnected = inboxData.conversations?.filter(conv => !conv.primary_contact) || []
      
      // Apply search filter to unconnected conversations
      if (recordsSearchQuery.trim()) {
        const query = recordsSearchQuery.toLowerCase()
        unconnected = unconnected.filter(conv => 
          (conv.participants?.[0]?.name || '').toLowerCase().includes(query) ||
          (conv.last_message?.content || '').replace(/<[^>]*>/g, '').toLowerCase().includes(query) ||
          conv.type.toLowerCase().includes(query)
        )
      }
      
      return { 
        filteredRecords: [], 
        unconnectedConversations: unconnected.sort((a, b) => 
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
        )
      }
    }
    
    // Handle regular record filtering
    let filtered = inboxData.records || []
    
    // Apply search filter
    if (recordsSearchQuery.trim()) {
      const query = recordsSearchQuery.toLowerCase()
      filtered = filtered.filter(record => 
        record.title.toLowerCase().includes(query) ||
        record.pipeline_name.toLowerCase().includes(query) ||
        record.available_channels.some(channel => channel.toLowerCase().includes(query))
      )
    }
    
    // Apply status filter
    switch (recordsFilter) {
      case 'unread':
        filtered = filtered.filter(record => record.total_unread > 0)
        break
      case 'recent':
        // Show records with activity in the last 7 days
        const sevenDaysAgo = new Date()
        sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7)
        filtered = filtered.filter(record => 
          new Date(record.last_activity) >= sevenDaysAgo
        )
        break
      // 'all' case doesn't need filtering
    }
    
    return { filteredRecords: filtered, unconnectedConversations: [] }
  }, [inboxData, recordsSearchQuery, recordsFilter])

  if (currentLoading) {
    return (
      <div className="h-screen flex flex-col items-center justify-center overflow-hidden">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
        <p className="mt-4 text-gray-600">Loading inbox...</p>
      </div>
    )
  }

  if (currentError) {
    return (
      <div className="h-screen flex flex-col items-center justify-center overflow-hidden p-6">
        <div className="text-center">
          <AlertCircle className="h-16 w-16 mx-auto text-red-500 mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Failed to load inbox</h2>
          <p className="text-gray-600 mb-6">{currentError}</p>
          <div className="flex gap-3 justify-center">
            <Button 
              onClick={() => {
                if (viewMode === 'conversations') {
                  loadConversations()
                } else {
                  fetchInbox()
                }
              }}
              className="flex items-center gap-2"
            >
              <RefreshCw className="h-4 w-4" />
              Try Again
            </Button>
            <Button 
              variant="outline" 
              onClick={() => setViewMode(viewMode === 'conversations' ? 'records' : 'conversations')}
            >
              Switch to {viewMode === 'conversations' ? 'Records' : 'Conversations'} View
            </Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="w-full flex flex-col overflow-hidden" 
         style={{ height: 'calc(100vh - 64px)', maxHeight: 'calc(100vh - 64px)' }}>
      <div className="h-full flex flex-col overflow-hidden"
           style={{ height: '100%', maxHeight: '100%' }}>
        <div className="flex items-center justify-between px-6 py-4 flex-shrink-0 border-b bg-white dark:bg-gray-900 dark:border-gray-700">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Communications Inbox</h1>
              {(unmatchedCount > 0 || warningsCount > 0) && (
                <div className="flex gap-2">
                  {unmatchedCount > 0 && (
                    <Badge variant="destructive" className="text-xs">
                      {unmatchedCount} Unmatched
                    </Badge>
                  )}
                  {warningsCount > 0 && (
                    <Badge variant="secondary" className="text-xs bg-yellow-100 text-yellow-800">
                      {warningsCount} Warnings
                    </Badge>
                  )}
                </div>
              )}
            </div>
            <p className="text-gray-600 dark:text-gray-400">
              {activeChannelTab === 'unified' 
                ? (viewMode === 'conversations' ? 'Channel-based conversation view' : 'Record-centric unified view')
                : `${activeChannelTab.charAt(0).toUpperCase() + activeChannelTab.slice(1)} messages and conversations`
              }
            </p>
          </div>
          
          <div className="flex items-center space-x-2">
            {/* View Mode Toggle */}
            <div className="flex items-center space-x-1">
              <Button
                variant={viewMode === 'conversations' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('conversations')}
              >
                <MessageSquare className="w-4 h-4 mr-2" />
                Conversations
              </Button>
              <Button
                variant={viewMode === 'records' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('records')}
              >
                <Users className="w-4 h-4 mr-2" />
                Records
              </Button>
            </div>
            
            {/* WebSocket Status Indicator */}
            <div className="flex items-center space-x-2 text-sm">
              <div className={`w-2 h-2 rounded-full ${
                (viewMode === 'conversations' ? wsConnected : unifiedWSConnected) ? 'bg-green-500' : 'bg-red-500'
              }`}></div>
              <span className="text-gray-600 dark:text-gray-400">
                {(viewMode === 'conversations' ? wsConnected : unifiedWSConnected) ? 'Real-time' : 'Offline'}
              </span>
            </div>
            
            <Button variant="outline" onClick={() => {
              if (viewMode === 'conversations') {
                setComposeDialogOpen(true)
              } else {
                setShowSmartCompose(true)
              }
            }}>
              <Send className="w-4 h-4 mr-2" />
              Compose
            </Button>
          </div>
        </div>

        {/* Channel Tabs */}
        <div className="px-6 py-2 border-b bg-white dark:bg-gray-900 dark:border-gray-700">
          <Tabs value={activeChannelTab} onValueChange={(value) => setActiveChannelTab(value as any)}>
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="unified" className="flex items-center gap-2">
                <MessageSquare className="w-4 h-4" />
                Unified
              </TabsTrigger>
              <TabsTrigger value="gmail" className="flex items-center gap-2">
                <Mail className="w-4 h-4" />
                Gmail
              </TabsTrigger>
              <TabsTrigger value="whatsapp" className="flex items-center gap-2">
                <MessageSquare className="w-4 h-4" />
                WhatsApp
              </TabsTrigger>
              <TabsTrigger value="linkedin" className="flex items-center gap-2">
                <MessageSquare className="w-4 h-4" />
                LinkedIn
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>

        {/* Render based on active channel tab */}
        {activeChannelTab === 'unified' ? (
          renderUnifiedInbox()
        ) : (
          renderChannelSpecificInbox(activeChannelTab)
        )}
      </div>
    </div>
  )

  // Unified inbox render function
  function renderUnifiedInbox() {
    return (
      <>
        {/* Render based on view mode */}
        {viewMode === 'conversations' ? (
          <>
            {/* Original Conversations View */}
            {/* Filters */}
            <div className="mx-6 my-4 flex-shrink-0">
              <Card>
                <CardContent className="p-3">
                <div className="flex items-center space-x-4">
                  <div className="flex-1">
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                      <Input
                        placeholder="Search conversations..."
                        value={filters.search}
                        onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
                        className="pl-10"
                      />
                    </div>
                  </div>
                  
                  <Select value={filters.type} onValueChange={(value: any) => setFilters(prev => ({ ...prev, type: value }))}>
                    <SelectTrigger className="w-32">
                      <SelectValue placeholder="Type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Types</SelectItem>
                      <SelectItem value="email">Email</SelectItem>
                      <SelectItem value="linkedin">LinkedIn</SelectItem>
                      <SelectItem value="whatsapp">WhatsApp</SelectItem>
                      <SelectItem value="sms">SMS</SelectItem>
                    </SelectContent>
                  </Select>
                  
                  <Select value={filters.status} onValueChange={(value: any) => setFilters(prev => ({ ...prev, status: value }))}>
                    <SelectTrigger className="w-32">
                      <SelectValue placeholder="Status" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All</SelectItem>
                      <SelectItem value="unread">Unread</SelectItem>
                      <SelectItem value="starred">Starred</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                </CardContent>
              </Card>
            </div>

            {/* Main Content */}
            <div className="px-6 pb-4 overflow-hidden" style={{ height: 'calc(100vh - 220px)' }}>
              <div className="h-full grid grid-cols-12 gap-4">
              {/* Conversations List */}
              <div className="col-span-4 h-full overflow-hidden">
                <Card className="h-full flex flex-col">
                  <CardHeader className="py-3 flex-shrink-0">
                    <CardTitle className="text-base">Conversations</CardTitle>
                    <CardDescription className="text-sm">
                      {conversations.length} conversation{conversations.length !== 1 ? 's' : ''}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="p-0 flex-1 overflow-hidden">
                    <ScrollArea style={{ height: 'calc(100vh - 300px)' }}>
                      {conversations.length === 0 ? (
                        <div className="p-8 text-center text-gray-500">
                          <MessageSquare className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                          <p>No conversations found</p>
                        </div>
                      ) : (
                        <div className="space-y-1">
                          {conversations.map((conversation) => (
                            <div
                              key={conversation.id}
                              className={`p-4 cursor-pointer border-b hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors ${
                                selectedConversation?.id === conversation.id ? 'bg-blue-50 dark:bg-blue-900/20 border-l-4 border-l-blue-500' : ''
                              }`}
                              onClick={() => handleConversationSelect(conversation)}
                            >
                              <div className="flex items-start justify-between">
                                <div className="flex items-start space-x-3 flex-1 min-w-0">
                                  {/* Profile Picture */}
                                  <div className="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0">
                                    {getMessageTypeIcon(conversation.type)}
                                  </div>
                                  
                                  <div className="flex-1 min-w-0">
                                    <div className="flex items-center justify-between mb-1">
                                      <div className="flex items-center space-x-2">
                                        <h3 className={`text-sm font-medium truncate ${
                                          conversation.unread_count > 0 ? 'font-semibold' : ''
                                        }`}>
                                          {conversation.participants?.[0]?.name || 'Unknown'}
                                        </h3>
                                        {getMessageTypeBadge(conversation.type)}
                                        {/* Contact Resolution Badge */}
                                        <ContactResolutionBadge
                                          contactRecord={conversation.primary_contact ? {
                                            id: conversation.primary_contact.id,
                                            title: conversation.primary_contact.name,
                                            pipeline_id: '',
                                            pipeline_name: conversation.primary_contact.pipeline_name,
                                            data: {}
                                          } : null}
                                          needsResolution={conversation.needs_manual_resolution}
                                          domainValidated={conversation.domain_validated}
                                          needsDomainReview={conversation.needs_domain_review}
                                          className="text-xs"
                                          onClick={() => handleContactAction(conversation)}
                                        />
                                      </div>
                                      <span className="text-xs text-gray-500 flex-shrink-0 ml-2">
                                        {formatTimestamp(conversation.updated_at)}
                                      </span>
                                    </div>
                                    
                                    {/* Contact Resolution Status */}
                                    <div className="flex items-center justify-between mb-2">
                                      <ContactResolutionIndicator 
                                        contactRecord={conversation.primary_contact ? {
                                          id: conversation.primary_contact.id,
                                          title: conversation.primary_contact.name,
                                          pipeline_id: '',
                                          pipeline_name: conversation.primary_contact.pipeline_name,
                                          data: {}
                                        } : null}
                                        needsResolution={conversation.needs_manual_resolution}
                                        domainValidated={conversation.domain_validated}
                                        needsDomainReview={conversation.needs_domain_review}
                                        onClick={() => handleContactAction(conversation)}
                                      />
                                      
                                      {conversation.unread_count > 0 && (
                                        <Badge variant="destructive" className="text-xs ml-2">
                                          {conversation.unread_count}
                                        </Badge>
                                      )}
                                    </div>
                                    
                                    <div className={`text-sm text-gray-600 dark:text-gray-400 truncate ${
                                      conversation.unread_count > 0 ? 'font-medium' : ''
                                    }`}>
                                      {conversation.last_message ? (
                                        <>
                                          {/* For emails, show subject line if available, otherwise truncated plain text content */}
                                          {conversation.type === 'email' && conversation.last_message.subject ? (
                                            <span className="font-medium">
                                              {conversation.last_message.subject}
                                            </span>
                                          ) : (
                                            /* For non-emails or emails without subjects, show content preview as plain text */
                                            <span>
                                              {conversation.last_message.content
                                                ?.replace(/<[^>]*>/g, '')  // Strip HTML tags
                                                ?.slice(0, 100) || 'No content'}
                                            </span>
                                          )}
                                        </>
                                      ) : 'No messages'}
                                    </div>
                                  </div>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </ScrollArea>
                  </CardContent>
                </Card>
              </div>
              
              {/* Messages View */}
              <div className="col-span-8 h-full overflow-hidden">
                {selectedConversation ? (
                  <Card className="h-full flex flex-col">
                    <CardHeader className="py-3 flex-shrink-0">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                          <div className="w-6 h-6 rounded-full bg-gray-200 flex items-center justify-center">
                            {getMessageTypeIcon(selectedConversation.type)}
                          </div>
                          <div>
                            <CardTitle className="text-base">
                              {selectedConversation.participants?.[0]?.name || 'Unknown'}
                            </CardTitle>
                            <div className="text-xs text-muted-foreground">
                              {getMessageTypeBadge(selectedConversation.type)}
                            </div>
                          </div>
                        </div>
                        
                        <div className="flex items-center space-x-2">
                          <ContactResolutionBadge 
                            contactRecord={selectedConversation.primary_contact ? {
                              id: selectedConversation.primary_contact.id,
                              title: selectedConversation.primary_contact.name,
                              pipeline_id: '',
                              pipeline_name: selectedConversation.primary_contact.pipeline_name,
                              data: {}
                            } : null}
                            needsResolution={selectedConversation.needs_manual_resolution}
                            domainValidated={selectedConversation.domain_validated}
                            needsDomainReview={selectedConversation.needs_domain_review}
                            onClick={() => handleContactResolution(selectedConversation.last_message)}
                          />
                          <Button variant="ghost" size="sm">
                            <MoreVertical className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    </CardHeader>
                    
                    {/* Messages */}
                    <CardContent className="flex-1 p-0 overflow-hidden">
                      <ScrollArea style={{ height: 'calc(100vh - 400px)' }}>
                        <div className="p-4">
                        {loadingMessages ? (
                          <div className="flex items-center justify-center h-32">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                          </div>
                        ) : (
                          <div className="space-y-4">
                            {messages.map((message) => (
                              message.type === 'email' ? (
                                // Email layout - use full width with email-style formatting
                                <div key={message.id} className="w-full border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800">
                                  <div className="border-b border-gray-200 dark:border-gray-700 px-4 py-3">
                                    <div className="flex justify-between items-start">
                                      <div>
                                        {message.subject && (
                                          <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
                                            {message.subject}
                                          </h3>
                                        )}
                                        <div className="text-sm text-gray-600 dark:text-gray-400">
                                          <span className="font-medium">
                                            {message.direction === 'outbound' ? 'You' : message.sender?.name || 'Unknown Sender'}
                                          </span>
                                          {message.sender?.email && (
                                            <span className="ml-1">&lt;{message.sender.email}&gt;</span>
                                          )}
                                        </div>
                                      </div>
                                      <div className="text-xs text-gray-500 dark:text-gray-400">
                                        {new Date(message.timestamp).toLocaleString()}
                                      </div>
                                    </div>
                                  </div>
                                  <div className="px-4 py-4">
                                    <MessageContent 
                                      content={message.content}
                                      isEmail={message.type === 'email'}
                                      metadata={message.metadata}
                                      className="text-gray-900 dark:text-white"
                                    />
                                  </div>
                                </div>
                              ) : (
                                // Chat bubble layout for non-email messages
                                <div key={message.id} className={`flex ${
                                  message.direction === 'outbound' ? 'justify-end' : 'justify-start'
                                }`}>
                                  <div className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                                    message.direction === 'outbound' 
                                      ? 'bg-blue-500 text-white' 
                                      : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white'
                                  }`}>
                                  {message.subject && (
                                    <div className="font-semibold text-sm mb-1">
                                      {message.subject}
                                    </div>
                                  )}
                                  <div className="text-sm">
                                    <MessageContent 
                                      content={message.content}
                                      isEmail={message.type === 'email'}
                                      metadata={message.metadata}
                                    />
                                  </div>
                                    <div className={`text-xs mt-1 ${
                                      message.direction === 'outbound' 
                                        ? 'text-blue-100' 
                                        : 'text-gray-500'
                                    }`}>
                                      {formatTimestamp(message.timestamp)}
                                    </div>
                                  </div>
                                </div>
                              )
                            ))}
                          </div>
                        )}
                        </div>
                      </ScrollArea>
                    </CardContent>
                    
                    {/* Reply Box */}
                    <div className="p-4 border-t flex-shrink-0">
                      <div className="flex space-x-2">
                        <Textarea
                          placeholder="Type your reply..."
                          value={replyText}
                          onChange={(e) => setReplyText(e.target.value)}
                          className="flex-1 min-h-[80px]"
                          onKeyPress={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey && !composing && replyText.trim()) {
                              e.preventDefault()
                              handleSendReply()
                            }
                          }}
                        />
                        <div className="flex flex-col space-y-2">
                          <Button
                            onClick={handleSendReply}
                            disabled={!replyText.trim() || composing}
                            size="sm"
                          >
                            <Send className="w-4 h-4" />
                          </Button>
                          <Button variant="ghost" size="sm">
                            <Paperclip className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  </Card>
                ) : (
                  <Card className="h-full flex flex-col">
                    <CardContent className="flex-1 flex items-center justify-center">
                      <div className="text-center text-gray-500">
                        <MessageSquare className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                        <p>Select a conversation to view messages</p>
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>
              </div>
            </div>
          </>
        ) : (
          <>
            {/* New Records View */}
            {/* Records Filters */}
            <div className="mx-6 my-4 flex-shrink-0">
              <Card>
                <CardContent className="p-3">
                  <div className="flex items-center space-x-4">
                    <div className="flex-1">
                      <div className="relative">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                        <Input
                          placeholder="Search records..."
                          value={recordsSearchQuery}
                          onChange={(e) => setRecordsSearchQuery(e.target.value)}
                          className="pl-10"
                        />
                      </div>
                    </div>
                    
                    <Tabs 
                      value={recordsFilter} 
                      onValueChange={(value) => setRecordsFilter(value as 'all' | 'unread' | 'recent' | 'unconnected')}
                    >
                      <TabsList className="grid grid-cols-4 h-8">
                        <TabsTrigger value="all" className="text-xs">All</TabsTrigger>
                        <TabsTrigger value="unread" className="text-xs">Unread</TabsTrigger>
                        <TabsTrigger value="recent" className="text-xs">Recent</TabsTrigger>
                        <TabsTrigger value="unconnected" className="text-xs">Unconnected</TabsTrigger>
                      </TabsList>
                    </Tabs>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Records Main Content */}
            <div className="px-6 pb-4 overflow-hidden" style={{ height: 'calc(100vh - 220px)' }}>
              <div className="h-full grid grid-cols-12 gap-4">
                {/* Left Panel - Record List */}
                <div className="col-span-4 h-full overflow-hidden">
                  <Card className="h-full flex flex-col">
                    <CardHeader className="py-3 flex-shrink-0">
                      <CardTitle className="text-base text-gray-900 dark:text-white">Records</CardTitle>
                      <CardDescription className="text-sm">
                        {filteredRecords.length} record{filteredRecords.length !== 1 ? 's' : ''}
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="p-0 flex-1 overflow-hidden">
                      <ScrollArea style={{ height: 'calc(100vh - 300px)' }}>
                        <div className="space-y-1">
                          {recordsFilter === 'unconnected' ? (
                      /* Unconnected Conversations */
                      unconnectedConversations && unconnectedConversations.length > 0 ? (
                        unconnectedConversations.map((conversation) => (
                          <Card 
                            key={conversation.id}
                            className="mb-2 cursor-pointer transition-colors hover:bg-gray-50"
                            onClick={() => {
                              // Switch to conversations view and select this conversation
                              setViewMode('conversations')
                              setSelectedConversation(conversation)
                              loadMessages(conversation.id)
                            }}
                          >
                            <CardContent className="p-4">
                              <div className="flex items-start justify-between">
                                <div className="flex-1">
                                  <div className="flex items-center gap-2 mb-1">
                                    <h3 className="font-medium text-sm">
                                      {conversation.participants?.[0]?.name || 'Unknown Contact'}
                                    </h3>
                                    <Badge variant="outline" className="text-xs bg-orange-50 text-orange-700 border-orange-200">
                                      Unconnected
                                    </Badge>
                                    {conversation.unread_count > 0 && (
                                      <Badge variant="destructive" className="text-xs">
                                        {conversation.unread_count}
                                      </Badge>
                                    )}
                                  </div>
                                  
                                  <p className="text-xs text-gray-500 mb-2 capitalize">{conversation.type} conversation</p>
                                  
                                  {/* Channel indicator */}
                                  <div className="flex items-center gap-2 mb-2">
                                    <div 
                                      className={`p-1 rounded-full text-white ${getChannelColor(conversation.type)}`}
                                      title={conversation.type}
                                    >
                                      {getChannelIcon(conversation.type)}
                                    </div>
                                    <span className="text-xs text-gray-600">{conversation.type}</span>
                                  </div>
                                  
                                  {/* Last message preview */}
                                  {conversation.last_message && (
                                    <div className="text-xs text-gray-600 mb-2 line-clamp-2">
                                      {/* For emails, show subject line if available, otherwise truncated plain text content */}
                                      {conversation.type === 'email' && conversation.last_message.subject ? (
                                        <span className="font-medium">
                                          {conversation.last_message.subject}
                                        </span>
                                      ) : (
                                        /* For non-emails or emails without subjects, show content preview as plain text */
                                        <span>
                                          {conversation.last_message.content
                                            ?.replace(/<[^>]*>/g, '')  // Strip HTML tags
                                            ?.slice(0, 100) || 'No content'}
                                        </span>
                                      )}
                                    </div>
                                  )}
                                  
                                  {/* Last activity */}
                                  <div className="flex items-center gap-1 text-xs text-gray-400">
                                    <Clock className="h-3 w-3" />
                                    {formatDistanceToNow(new Date(conversation.updated_at), { addSuffix: true })}
                                  </div>
                                </div>
                                
                                <div className="flex flex-col gap-1">
                                  <Button 
                                    variant="ghost" 
                                    size="sm"
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      handleContactResolution(conversation.last_message)
                                    }}
                                    className="text-xs"
                                    title="Resolve contact"
                                  >
                                    Connect
                                  </Button>
                                  <Button variant="ghost" size="sm">
                                    <MoreVertical className="h-4 w-4" />
                                  </Button>
                                </div>
                              </div>
                            </CardContent>
                          </Card>
                        ))
                      ) : (
                        /* Empty state for unconnected conversations */
                        <div className="text-center py-12 px-4">
                          <MessageSquare className="h-16 w-16 mx-auto text-gray-300 mb-4" />
                          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">No unconnected conversations</h3>
                          <p className="text-gray-500 mb-6">
                            {recordsSearchQuery ? 
                              `No unconnected conversations found for "${recordsSearchQuery}". Try a different search term.` :
                              "All conversations have been connected to contacts. New unmatched messages will appear here."
                            }
                          </p>
                          {recordsSearchQuery && (
                            <Button 
                              variant="outline" 
                              onClick={() => setRecordsSearchQuery('')}
                            >
                              Clear Search
                            </Button>
                          )}
                        </div>
                      )
                    ) : (
                      /* Connected Records */
                      filteredRecords && filteredRecords.length > 0 ? (
                        filteredRecords.map((record) => (
                      <Card 
                        key={record.id}
                        className={`mb-2 cursor-pointer transition-colors hover:bg-gray-50 ${
                          selectedRecord?.id === record.id ? 'ring-2 ring-blue-500' : ''
                        }`}
                        onClick={() => selectRecord(record)}
                      >
                        <CardContent className="p-4">
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <h3 className="font-medium text-sm">{record.title}</h3>
                                {record.total_unread > 0 && (
                                  <Badge variant="destructive" className="text-xs">
                                    {record.total_unread}
                                  </Badge>
                                )}
                              </div>
                              
                              <p className="text-xs text-gray-500 mb-2">{record.pipeline_name}</p>
                              
                              {/* Channel indicators */}
                              <div className="flex items-center gap-1 mb-2">
                                {record.available_channels.map((channelType) => (
                                  <div 
                                    key={channelType}
                                    className={`p-1 rounded-full text-white ${getChannelColor(channelType)}`}
                                    title={channelType}
                                  >
                                    {getChannelIcon(channelType)}
                                  </div>
                                ))}
                              </div>
                              
                              {/* Last activity */}
                              <div className="flex items-center gap-1 text-xs text-gray-400">
                                <Clock className="h-3 w-3" />
                                {formatDistanceToNow(new Date(record.last_activity), { addSuffix: true })}
                              </div>
                            </div>
                            
                            <Button variant="ghost" size="sm">
                              <MoreVertical className="h-4 w-4" />
                            </Button>
                          </div>
                        </CardContent>
                      </Card>
                        ))
                      ) : (
                      <div className="text-center py-12 px-4">
                        {recordsSearchQuery || recordsFilter !== 'all' ? (
                          <>
                            <Search className="h-16 w-16 mx-auto text-gray-300 mb-4" />
                            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">No records match your filters</h3>
                            <p className="text-gray-500 mb-6">
                              {recordsSearchQuery && `No records found for "${recordsSearchQuery}". `}
                              {recordsFilter === 'unread' && "No records with unread messages. "}
                              {recordsFilter === 'recent' && "No records with recent activity. "}
                              Try adjusting your search or filters.
                            </p>
                            <div className="flex gap-2 justify-center">
                              {recordsSearchQuery && (
                                <Button 
                                  variant="outline" 
                                  onClick={() => setRecordsSearchQuery('')}
                                >
                                  Clear Search
                                </Button>
                              )}
                              {recordsFilter !== 'all' && (
                                <Button 
                                  variant="outline" 
                                  onClick={() => setRecordsFilter('all')}
                                >
                                  Show All
                                </Button>
                              )}
                            </div>
                          </>
                        ) : (
                          <>
                            <MessageSquare className="h-16 w-16 mx-auto text-gray-300 mb-4" />
                            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">No records found</h3>
                            <p className="text-gray-500 mb-6">
                              {inboxData ? 
                                "No conversations with resolved contacts yet. Messages will appear here once contacts are matched." :
                                "Loading records..."
                              }
                            </p>
                            <Button 
                              variant="outline" 
                              onClick={() => setViewMode('conversations')}
                              className="mb-2"
                            >
                              Switch to Conversations View
                            </Button>
                          </>
                        )
                      }
                      </div>
                    )
                  )}
                        </div>
                      </ScrollArea>
                    </CardContent>
                  </Card>
                </div>

                {/* Right Panel - Record Details */}
                <div className="col-span-8 h-full overflow-hidden">
                  {selectedRecord ? (
                    <Card className="h-full flex flex-col">
                      {/* Header */}
                      <CardHeader className="py-3 flex-shrink-0">
                        <div className="flex items-center justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-3 mb-2">
                              <CardTitle className="text-base text-gray-900 dark:text-white">{selectedRecord.title}</CardTitle>
                            {selectedRecord.total_unread > 0 && (
                              <Badge variant="destructive">
                                {selectedRecord.total_unread} unread
                              </Badge>
                            )}
                          </div>
                          <CardDescription className="text-xs">
                            {selectedRecord.pipeline_name} • Last activity: {formatDistanceToNow(new Date(selectedRecord.last_activity), { addSuffix: true })} • {selectedRecord.available_channels.length} channel{selectedRecord.available_channels.length !== 1 ? 's' : ''}
                          </CardDescription>
                          
                          {/* Channel quick overview */}
                          <div className="flex items-center gap-2 mt-2">
                            {selectedRecord.available_channels.map((channelType) => {
                              const channelData = selectedRecord.channels[channelType]
                              return (
                                <div 
                                  key={channelType} 
                                  className="flex items-center gap-1 px-2 py-1 rounded-md bg-gray-100 text-xs"
                                  title={`${channelData?.conversation_count || 0} conversations, ${channelData?.unread_count || 0} unread`}
                                >
                                  <div className={`p-0.5 rounded-full text-white ${getChannelColor(channelType)}`}>
                                    {getChannelIcon(channelType)}
                                  </div>
                                  <span className="font-medium">{channelType}</span>
                                  {channelData?.unread_count > 0 && (
                                    <Badge variant="secondary" className="h-4 text-xs ml-1">
                                      {channelData.unread_count}
                                    </Badge>
                                  )}
                                </div>
                              )
                            })}
                          </div>
                        </div>
                        
                        <div className="flex items-center gap-2">
                          <Button variant="outline" size="sm">
                            <Star className="h-4 w-4" />
                          </Button>
                          <Button variant="outline" size="sm">
                            <Archive className="h-4 w-4" />
                          </Button>
                          <Button size="sm" onClick={() => setShowSmartCompose(true)}>
                            <Plus className="h-4 w-4 mr-2" />
                            New Message
                          </Button>
                        </div>
                      </div>
                    </CardHeader>

                    {/* Content Area */}
                    <CardContent className="flex-1 p-0 overflow-hidden">
                      <Tabs defaultValue="timeline" className="h-full flex flex-col">
                        <TabsList className="mx-4 mt-3 flex-shrink-0">
                          <TabsTrigger value="timeline">Timeline</TabsTrigger>
                          <TabsTrigger value="channels">Channels</TabsTrigger>
                          <TabsTrigger value="analytics">Analytics</TabsTrigger>
                        </TabsList>
                        
                        <TabsContent value="timeline" className="mx-4 mb-4 mt-2 overflow-hidden" style={{ height: 'calc(100vh - 340px)' }}>
                          {/* Show messages from all conversations for this Record */}
                          <div className="h-full flex flex-col">
                            <div className="mb-4 flex-shrink-0">
                              <h3 className="text-lg font-semibold mb-2 text-gray-900 dark:text-white">Conversation History</h3>
                              <p className="text-gray-600 text-sm">All messages across channels for {selectedRecord.title}</p>
                            </div>
                            
                            <ScrollArea className="flex-1 min-h-0 border rounded-lg">
                              <div className="p-4 space-y-4">
                                {/* Get conversations for this Record and display messages */}
                                {inboxData?.conversations
                                  ?.filter(conv => conv.primary_contact?.id === selectedRecord.id)
                                  ?.map(conversation => (
                                    <div key={conversation.id} className="space-y-2">
                                      <div className="flex items-center gap-2 mb-2">
                                        {getChannelIcon(conversation.type)}
                                        <Badge variant="outline" className="text-xs">
                                          {conversation.type?.toUpperCase()}
                                        </Badge>
                                        <span className="text-xs text-gray-500">
                                          {conversation.updated_at ? formatDistanceToNow(new Date(conversation.updated_at)) + ' ago' : ''}
                                        </span>
                                      </div>
                                      
                                      {/* Last message preview */}
                                      {conversation.last_message && (
                                        <Card className="border-l-4 border-l-blue-500">
                                          <CardContent className="p-3">
                                            <div className="flex justify-between items-start mb-1">
                                              <span className="text-sm font-medium">
                                                {conversation.last_message.direction === 'inbound' ? 
                                                  conversation.last_message.sender?.name || 'Unknown' : 'You'
                                                }
                                              </span>
                                              <span className="text-xs text-gray-500">
                                                {conversation.last_message.timestamp ? 
                                                  formatDistanceToNow(new Date(conversation.last_message.timestamp)) + ' ago' : ''
                                                }
                                              </span>
                                            </div>
                                            <div className="text-sm text-gray-700">
                                              {conversation.last_message.subject && (
                                                <span className="font-medium">{conversation.last_message.subject}: </span>
                                              )}
                                              <MessageContent 
                                                content={conversation.last_message.content || 'No content'}
                                                isEmail={conversation.type === 'email'}
                                                className="inline"
                                              />
                                            </div>
                                            {conversation.unread_count > 0 && (
                                              <Badge variant="destructive" className="text-xs mt-2">
                                                {conversation.unread_count} unread
                                              </Badge>
                                            )}
                                            
                                            {/* Button to load full conversation */}
                                            <Button 
                                              variant="ghost" 
                                              size="sm" 
                                              className="mt-2"
                                              onClick={() => {
                                                // Load messages for this conversation
                                                setSelectedConversation(conversation)
                                                loadMessages(conversation.id)
                                                // Switch to conversations view to see full timeline
                                                setViewMode('conversations')
                                              }}
                                            >
                                              View Full Conversation
                                            </Button>
                                          </CardContent>
                                        </Card>
                                      )}
                                    </div>
                                  )) || []
                                }
                                
                                {(!inboxData?.conversations?.filter(conv => conv.primary_contact?.id === selectedRecord.id)?.length) && (
                                  <div className="text-center text-gray-500 py-8">
                                    No conversations found for this contact
                                  </div>
                                )}
                              </div>
                            </ScrollArea>
                          </div>
                        </TabsContent>
                        
                        <TabsContent value="channels" className="mx-4 mb-4 mt-2 overflow-hidden" style={{ height: 'calc(100vh - 340px)' }}>
                          <div className="h-full flex flex-col overflow-hidden">
                            <div className="mb-4 flex-shrink-0">
                              <h3 className="text-lg font-semibold mb-2 text-gray-900 dark:text-white">Channel Summary</h3>
                              <p className="text-gray-600 text-sm">Communication statistics for {selectedRecord.title}</p>
                            </div>
                            
                            <ScrollArea className="flex-1 min-h-0">
                              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
                              {selectedRecord.available_channels.map((channelType) => {
                                const channelData = selectedRecord.channels[channelType]
                                return (
                                  <Card key={channelType}>
                                    <CardContent className="p-4">
                                      <div className="flex items-center justify-between mb-3">
                                        <div className="flex items-center gap-2">
                                          <div className={`p-2 rounded-full text-white ${getChannelColor(channelType)}`}>
                                            {getChannelIcon(channelType)}
                                          </div>
                                          <h4 className="font-medium capitalize">{channelType}</h4>
                                        </div>
                                        
                                        {channelData?.unread_count > 0 && (
                                          <Badge variant="destructive" className="text-xs">
                                            {channelData.unread_count} unread
                                          </Badge>
                                        )}
                                      </div>
                                      
                                      <div className="space-y-2 text-sm">
                                        <div className="flex justify-between">
                                          <span className="text-gray-600">Conversations</span>
                                          <span className="font-medium">{channelData?.conversation_count || 0}</span>
                                        </div>
                                        <div className="flex justify-between">
                                          <span className="text-gray-600">Messages</span>
                                          <span className="font-medium">{channelData?.message_count || 0}</span>
                                        </div>
                                        <div className="flex justify-between">
                                          <span className="text-gray-600">Last Activity</span>
                                          <span className="font-medium">
                                            {channelData?.last_activity 
                                              ? formatDistanceToNow(new Date(channelData.last_activity), { addSuffix: true })
                                              : 'None'
                                            }
                                          </span>
                                        </div>
                                      </div>
                                      
                                      {channelData?.last_message_preview && (
                                        <div className="mt-3 pt-3 border-t">
                                          <p className="text-xs text-gray-500">Latest message:</p>
                                          <p className="text-xs text-gray-700 mt-1 line-clamp-2">
                                            {channelData.last_message_preview}
                                          </p>
                                        </div>
                                      )}
                                      
                                      <div className="mt-3 pt-3 border-t flex gap-2">
                                        <Button 
                                          variant="outline" 
                                          size="sm" 
                                          className="flex-1"
                                          onClick={() => {
                                            // Filter conversations by this channel and show them in timeline
                                            // For now, switch to timeline tab
                                            (document.querySelector('[value="timeline"]') as HTMLElement)?.click()
                                          }}
                                        >
                                          View Messages
                                        </Button>
                                        {channelData?.unread_count > 0 && (
                                          <Button 
                                            variant="ghost" 
                                            size="sm"
                                            onClick={() => markAsRead(selectedRecord.id, channelType)}
                                          >
                                            Mark Read
                                          </Button>
                                        )}
                                      </div>
                                    </CardContent>
                                  </Card>
                                )
                              })}
                            </div>
                            
                              {/* Additional Channel Information */}
                              <Card>
                              <CardHeader>
                                <CardTitle className="text-base text-gray-900 dark:text-white">Channel Statistics</CardTitle>
                              </CardHeader>
                              <CardContent>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                                  <div>
                                    <div className="text-2xl font-bold text-blue-600">
                                      {selectedRecord.available_channels.length}
                                    </div>
                                    <div className="text-sm text-gray-600">Active Channels</div>
                                  </div>
                                  <div>
                                    <div className="text-2xl font-bold text-green-600">
                                      {String(Object.values(selectedRecord.channels).reduce((sum, channel: any) => sum + (channel.conversation_count || 0), 0))}
                                    </div>
                                    <div className="text-sm text-gray-600">Total Conversations</div>
                                  </div>
                                  <div>
                                    <div className="text-2xl font-bold text-orange-600">
                                      {String(Object.values(selectedRecord.channels).reduce((sum, channel: any) => sum + (channel.message_count || 0), 0))}
                                    </div>
                                    <div className="text-sm text-gray-600">Total Messages</div>
                                  </div>
                                  <div>
                                    <div className="text-2xl font-bold text-red-600">
                                      {selectedRecord.total_unread}
                                    </div>
                                    <div className="text-sm text-gray-600">Unread Messages</div>
                                  </div>
                                </div>
                              </CardContent>
                              </Card>
                            </ScrollArea>
                          </div>
                        </TabsContent>
                        
                        <TabsContent value="analytics" className="mx-4 mb-4 mt-2 overflow-hidden" style={{ height: 'calc(100vh - 340px)' }}>
                          <CommunicationAnalytics 
                            recordId={selectedRecord.id}
                            recordTitle={selectedRecord.title}
                            className="h-full"
                          />
                        </TabsContent>
                      </Tabs>
                    </CardContent>
                    </Card>
                  ) : (
                    <Card className="h-full flex flex-col">
                      <CardContent className="flex-1 flex items-center justify-center">
                        <div className="text-center text-gray-500">
                          <MessageSquare className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                          <p>Select a record to view communication timeline</p>
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </div>
              </div>
            </div>
          </>
        )}

        {/* Dialogs and Modals */}
        {composeDialogOpen && (
          <MessageComposer
            open={composeDialogOpen}
            onOpenChange={setComposeDialogOpen}
            accountConnections={accountConnections}
          />
        )}

        {contactResolutionOpen && selectedMessageForResolution && (
          <ContactResolutionDialog
            isOpen={contactResolutionOpen}
            onClose={() => {
              setContactResolutionOpen(false)
              setSelectedMessageForResolution(null)
            }}
            message={selectedMessageForResolution}
            onResolutionComplete={handleResolutionComplete}
          />
        )}

        {contactViewerOpen && selectedContactRecord && selectedContactPipeline && (
          <RecordDetailDrawer
            isOpen={contactViewerOpen}
            onClose={() => setContactViewerOpen(false)}
            onSave={async (updatedRecord) => {
              // Handle record save if needed
              console.log('Record updated:', updatedRecord)
            }}
            record={selectedContactRecord}
            pipeline={selectedContactPipeline}
          />
        )}

        {/* Smart Compose Dialog for Records View */}
        {showSmartCompose && selectedRecord && (
          <div 
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
            onClick={(e) => {
              if (e.target === e.currentTarget) {
                setShowSmartCompose(false)
              }
            }}
          >
            <div className="max-w-4xl w-full mx-4 max-h-[90vh] overflow-auto">
              <SmartCompose
                recordId={selectedRecord.id}
                recordTitle={selectedRecord.title}
                onSent={(messageId, channel) => {
                  console.log('Message sent:', messageId, 'via', channel)
                  setShowSmartCompose(false)
                  fetchInbox()
                }}
                onCancel={() => setShowSmartCompose(false)}
                className="shadow-xl"
              />
            </div>
          </div>
        )}
      </>
    )
  }

  // Channel-specific inbox render function
  function renderChannelSpecificInbox(channel: string) {
    const containerHeight = 'calc(100vh - 180px)' // Adjust for header and tabs
    
    switch (channel) {
      case 'gmail':
        return (
          <div style={{ height: containerHeight }} className="overflow-hidden">
            <GmailInboxRefactored className="h-full" />
          </div>
        )
      case 'whatsapp':
        return (
          <div style={{ height: containerHeight }}>
            <WhatsAppInboxLive className="h-full" />
          </div>
        )
      case 'linkedin':
        return (
          <div style={{ height: containerHeight }}>
            <LinkedInInbox className="h-full" />
          </div>
        )
      default:
        return (
          <div className="p-6">
            <Card>
              <CardContent className="p-8 text-center">
                <div className="mb-4">
                  <MessageSquare className="w-16 h-16 mx-auto text-gray-400" />
                </div>
                <h2 className="text-2xl font-bold mb-2">
                  {channel.charAt(0).toUpperCase() + channel.slice(1)} Inbox
                </h2>
                <p className="text-gray-600 mb-6">
                  Channel-specific inbox for {channel} messages with optimized layout and features.
                </p>
                <Badge variant="outline" className="bg-blue-50 text-blue-700">
                  Coming Soon
                </Badge>
              </CardContent>
            </Card>
          </div>
        )
    }
  }
}