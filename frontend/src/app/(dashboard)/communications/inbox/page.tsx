'use client'

import { useState, useEffect, useCallback } from 'react'
import { MessageSquare, Mail, Phone, Search, Filter, Paperclip, Send, MoreVertical, Archive, Reply, Forward, Star, StarOff, Users, TrendingUp, Clock, CheckCircle2, AlertCircle, Plus } from 'lucide-react'
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
import { formatDistanceToNow } from 'date-fns'

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
    isConnected: unifiedWSConnected,
    error: unifiedError
  } = useUnifiedInbox()

  // Real-time message handler
  const handleNewMessage = useCallback((message: any) => {
    console.log('🔥 Real-time message received:', message)
    
    // Add message to current conversation if it's open
    if (selectedConversation && message.conversation_id === selectedConversation.id) {
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
    
    // Update conversation list with new last message
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
    
    // Show toast for new messages when conversation is not selected
    if (message.direction === 'inbound' && (!selectedConversation || message.conversation_id !== selectedConversation.id)) {
      // Use WhatsApp identity handler for display
      const displayInfo = message.type === 'whatsapp' 
        ? WhatsAppIdentityHandler.formatMessageDisplay(message, user?.email)
        : { senderName: message.sender?.name || 'Unknown', isFromBusiness: false }
      
      if (!displayInfo.isFromBusiness) {
        toast({
          title: `New message from ${displayInfo.senderName}`,
          description: message.content.slice(0, 100) + (message.content.length > 100 ? '...' : ''),
        })
      }
    }
  }, [selectedConversation, toast, user?.email])

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
    if (!selectedConversation || !replyText.trim()) return

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
      const pipeline = fullPipelineResponse.data
      
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

  if (currentLoading) {
    return (
      <div className="p-6">
        <div className="max-w-full mx-auto">
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading inbox...</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 h-screen">
      <div className="max-w-full mx-auto h-full flex flex-col">
        <div className="flex items-center justify-between mb-6">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Unified Inbox</h1>
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
              {viewMode === 'conversations' ? 'Channel-based conversation view' : 'Record-centric unified view'}
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

        {/* Render based on view mode */}
        {viewMode === 'conversations' ? (
          <>
            {/* Original Conversations View */}
            {/* Filters */}
            <Card className="mb-4">
              <CardContent className="p-4">
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

            {/* Main Content */}
            <div className="flex-1 grid grid-cols-12 gap-4 min-h-0">
              {/* Conversations List */}
              <div className="col-span-4">
                <Card className="h-full">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg">Conversations</CardTitle>
                    <CardDescription>
                      {conversations.length} conversation{conversations.length !== 1 ? 's' : ''}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="p-0">
                    <ScrollArea className="h-[calc(100vh-300px)]">
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
                                        conversation={conversation}
                                        onAction={() => handleContactAction(conversation)}
                                      />
                                      
                                      {conversation.unread_count > 0 && (
                                        <Badge variant="destructive" className="text-xs ml-2">
                                          {conversation.unread_count}
                                        </Badge>
                                      )}
                                    </div>
                                    
                                    <p className={`text-sm text-gray-600 dark:text-gray-400 truncate ${
                                      conversation.unread_count > 0 ? 'font-medium' : ''
                                    }`}>
                                      {conversation.last_message?.content || 'No messages'}
                                    </p>
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
              <div className="col-span-8">
                {selectedConversation ? (
                  <Card className="h-full flex flex-col">
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                          <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
                            {getMessageTypeIcon(selectedConversation.type)}
                          </div>
                          <div>
                            <CardTitle className="text-lg">
                              {selectedConversation.participants?.[0]?.name || 'Unknown'}
                            </CardTitle>
                            <div className="text-sm text-muted-foreground">
                              {getMessageTypeBadge(selectedConversation.type)}
                            </div>
                          </div>
                        </div>
                        
                        <div className="flex items-center space-x-2">
                          <ContactResolutionBadge 
                            conversation={selectedConversation}
                            onResolve={() => handleContactResolution(selectedConversation.last_message)}
                            onViewContact={() => handleViewContact(selectedConversation.primary_contact)}
                          />
                          <Button variant="ghost" size="sm">
                            <MoreVertical className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    </CardHeader>
                    
                    {/* Messages */}
                    <CardContent className="flex-1 p-0 overflow-hidden">
                      <ScrollArea className="h-full p-4">
                        {loadingMessages ? (
                          <div className="flex items-center justify-center h-32">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                          </div>
                        ) : (
                          <div className="space-y-4">
                            {messages.map((message) => (
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
                                    {message.content}
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
                            ))}
                          </div>
                        )}
                      </ScrollArea>
                    </CardContent>
                    
                    {/* Reply Box */}
                    <div className="p-4 border-t">
                      <div className="flex space-x-2">
                        <Textarea
                          placeholder="Type your reply..."
                          value={replyText}
                          onChange={(e) => setReplyText(e.target.value)}
                          className="flex-1 min-h-[80px]"
                          onKeyPress={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
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
                  <Card className="h-full">
                    <CardContent className="flex items-center justify-center h-full">
                      <div className="text-center text-gray-500">
                        <MessageSquare className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                        <p>Select a conversation to view messages</p>
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>
            </div>
          </>
        ) : (
          <>
            {/* New Records View */}
            <div className="flex h-full">
              {/* Left Panel - Record List */}
              <div className="w-1/3 border-r bg-white">
                <div className="p-4 border-b">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold">Records</h2>
                    <Button size="sm" variant="outline">
                      <Filter className="h-4 w-4" />
                    </Button>
                  </div>
                  
                  {/* Search */}
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                    <Input
                      placeholder="Search records..."
                      className="pl-10"
                    />
                  </div>
                  
                  {/* Tabs */}
                  <Tabs defaultValue="all" className="mt-4">
                    <TabsList className="grid w-full grid-cols-3">
                      <TabsTrigger value="all">All</TabsTrigger>
                      <TabsTrigger value="unread">Unread</TabsTrigger>
                      <TabsTrigger value="recent">Recent</TabsTrigger>
                    </TabsList>
                  </Tabs>
                </div>

                {/* Records List */}
                <ScrollArea className="flex-1">
                  <div className="p-2">
                    {inboxData?.records.map((record) => (
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
                    )) || []}
                  </div>
                </ScrollArea>
              </div>

              {/* Right Panel - Record Details */}
              <div className="flex-1 flex flex-col">
                {selectedRecord ? (
                  <>
                    {/* Header */}
                    <div className="p-6 border-b bg-white">
                      <div className="flex items-center justify-between">
                        <div>
                          <h1 className="text-xl font-semibold">{selectedRecord.title}</h1>
                          <p className="text-gray-500">{selectedRecord.pipeline_name}</p>
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
                    </div>

                    {/* Content Area */}
                    <div className="flex-1 overflow-hidden">
                      <Tabs defaultValue="timeline" className="h-full flex flex-col">
                        <TabsList className="mx-6 mt-4">
                          <TabsTrigger value="timeline">Timeline</TabsTrigger>
                          <TabsTrigger value="channels">Channels</TabsTrigger>
                          <TabsTrigger value="analytics">Analytics</TabsTrigger>
                        </TabsList>
                        
                        <TabsContent value="timeline" className="flex-1 m-6 mt-4">
                          {/* Show messages from all conversations for this Record */}
                          <div className="h-full flex flex-col">
                            <div className="mb-4">
                              <h3 className="text-lg font-semibold mb-2">Conversation History</h3>
                              <p className="text-gray-600 text-sm">All messages across channels for {selectedRecord.title}</p>
                            </div>
                            
                            <ScrollArea className="flex-1 border rounded-lg">
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
                                            <p className="text-sm text-gray-700">
                                              {conversation.last_message.subject && (
                                                <span className="font-medium">{conversation.last_message.subject}: </span>
                                              )}
                                              {conversation.last_message.content || 'No content'}
                                            </p>
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
                        
                        <TabsContent value="channels" className="flex-1 m-6 mt-4">
                          <Card className="h-full">
                            <CardHeader>
                              <CardTitle className="flex items-center gap-2">
                                <Users className="h-5 w-5" />
                                Channel Availability
                              </CardTitle>
                            </CardHeader>
                            <CardContent>
                              <ScrollArea className="h-96">
                                <div className="space-y-4">
                                  {channelAvailability.map((channel) => (
                                    <div key={channel.channel_type} className="border rounded-lg p-4">
                                      <div className="flex items-center justify-between mb-2">
                                        <div className="flex items-center gap-3">
                                          <div className={`p-2 rounded-full text-white ${getChannelColor(channel.channel_type)}`}>
                                            {getChannelIcon(channel.channel_type)}
                                          </div>
                                          <div>
                                            <h4 className="font-medium">{channel.display_name}</h4>
                                            <p className="text-sm text-gray-500">Priority {channel.priority}</p>
                                          </div>
                                        </div>
                                        
                                        <Badge className={getStatusColor(channel.status)}>
                                          {channel.status}
                                        </Badge>
                                      </div>
                                      
                                      <div className="grid grid-cols-2 gap-4 text-sm">
                                        <div className="flex items-center gap-2">
                                          {channel.user_connected ? (
                                            <CheckCircle2 className="h-4 w-4 text-green-500" />
                                          ) : (
                                            <AlertCircle className="h-4 w-4 text-red-500" />
                                          )}
                                          <span>User Connected</span>
                                        </div>
                                        
                                        <div className="flex items-center gap-2">
                                          {channel.contact_info_available ? (
                                            <CheckCircle2 className="h-4 w-4 text-green-500" />
                                          ) : (
                                            <AlertCircle className="h-4 w-4 text-red-500" />
                                          )}
                                          <span>Contact Info</span>
                                        </div>
                                        
                                        {channel.has_history && (
                                          <div className="flex items-center gap-2">
                                            <TrendingUp className="h-4 w-4 text-blue-500" />
                                            <span>Has History</span>
                                          </div>
                                        )}
                                      </div>
                                      
                                      {channel.history && (
                                        <div className="mt-3 pt-3 border-t">
                                          <div className="grid grid-cols-3 gap-4 text-sm">
                                            <div>
                                              <p className="text-gray-500">Messages</p>
                                              <p className="font-medium">{channel.history.total_messages}</p>
                                            </div>
                                            <div>
                                              <p className="text-gray-500">Response Rate</p>
                                              <p className="font-medium">{channel.history.response_rate.toFixed(1)}%</p>
                                            </div>
                                            <div>
                                              <p className="text-gray-500">Engagement</p>
                                              <p className="font-medium">{channel.history.engagement_score.toFixed(1)}</p>
                                            </div>
                                          </div>
                                        </div>
                                      )}
                                      
                                      {channel.limitations.length > 0 && (
                                        <div className="mt-3 pt-3 border-t">
                                          <p className="text-sm text-gray-500 mb-1">Limitations:</p>
                                          <ul className="text-sm text-red-600">
                                            {channel.limitations.map((limitation, index) => (
                                              <li key={index}>• {limitation}</li>
                                            ))}
                                          </ul>
                                        </div>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </ScrollArea>
                            </CardContent>
                          </Card>
                        </TabsContent>
                        
                        <TabsContent value="analytics" className="flex-1 m-6 mt-4">
                          <CommunicationAnalytics 
                            recordId={selectedRecord.id}
                            recordTitle={selectedRecord.title}
                            className="h-full"
                          />
                        </TabsContent>
                      </Tabs>
                    </div>
                  </>
                ) : (
                  <div className="flex-1 flex items-center justify-center text-gray-500">
                    <div className="text-center">
                      <MessageSquare className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                      <p>Select a record to view communication timeline</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </>
        )}

        {/* Dialogs and Modals */}
        {composeDialogOpen && (
          <MessageComposer
            open={composeDialogOpen}
            onClose={() => setComposeDialogOpen(false)}
            onSent={() => {
              setComposeDialogOpen(false)
              if (viewMode === 'conversations') {
                loadConversations()
              } else {
                fetchInbox()
              }
            }}
            connections={accountConnections}
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
      </div>
    </div>
  )
}