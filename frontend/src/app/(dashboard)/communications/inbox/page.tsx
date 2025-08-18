'use client'

import { useState, useEffect, useCallback } from 'react'
import { MessageSquare, Mail, Phone, Search, Filter, Paperclip, Send, MoreVertical, Archive, Reply, Forward, Star, StarOff } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useToast } from '@/hooks/use-toast'
import { useAuth } from '@/features/auth/context'
import { communicationsApi } from '@/lib/api'
import { MessageComposer } from '@/components/communications/message-composer'
import { WhatsAppIdentityHandler } from '@/components/communications/WhatsAppIdentityHandler'
import { ContactResolutionBadge, ContactResolutionIndicator } from '@/components/communications/contact-resolution-badge'
import { ContactResolutionDialog } from '@/components/communications/contact-resolution-dialog'
import { useContactResolution, useMessageContactStatus } from '@/hooks/use-contact-resolution'
import { useWebSocket, type RealtimeMessage } from '@/contexts/websocket-context'

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
  // WhatsApp-specific metadata
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
  database_id?: string  // UUID used for WebSocket subscriptions
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
  // Contact integration
  primary_contact?: {
    id: string
    name: string
    email?: string
    pipeline_name: string
  }
  // Contact resolution fields
  needs_manual_resolution?: boolean
  domain_validated?: boolean
  needs_domain_review?: boolean
}

interface InboxFilters {
  search: string
  type: 'all' | 'email' | 'linkedin' | 'whatsapp' | 'sms'
  status: 'all' | 'unread' | 'starred'
  account: string
}

export default function InboxPage() {
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
  
  // Message composer states
  const [composeDialogOpen, setComposeDialogOpen] = useState(false)
  const [replyingTo, setReplyingTo] = useState<Message | null>(null)
  const [accountConnections, setAccountConnections] = useState<any[]>([])
  
  // Contact resolution states
  const [contactResolutionOpen, setContactResolutionOpen] = useState(false)
  const [selectedMessageForResolution, setSelectedMessageForResolution] = useState<Message | null>(null)
  
  // WebSocket connection state
  const [wsStatus, setWsStatus] = useState<string>('disconnected')
  const [conversationSubscriptionId, setConversationSubscriptionId] = useState<string | null>(null)
  
  const { toast } = useToast()
  const { tenant, user, isAuthenticated, isLoading: authLoading } = useAuth()
  
  // Contact resolution hook
  const { unmatchedCount, warningsCount, refresh: refreshContactResolution } = useContactResolution()

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
    if (isAuthenticated && !authLoading && user && tenant) {
      loadConversations()
      loadAccountConnections()
    }
  }, [isAuthenticated, authLoading, user, tenant, filters])

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
      // This would be a new API endpoint for unified inbox
      const response = await communicationsApi.getUnifiedInbox(filters)
      const conversations = response.data.conversations || []
      
      console.log(`📨 Loaded ${conversations.length} conversations:`)
      conversations.forEach((conv: any, index: number) => {
        console.log(`   ${index + 1}. Type: ${conv.type}, Participants:`, conv.participants?.map((p: any) => ({ name: p.name, id: p.id })) || 'None')
        console.log(`      Primary Contact:`, conv.primary_contact ? { name: conv.primary_contact.name, id: conv.primary_contact.id } : 'None')
        console.log(`      Last Message ID: ${conv.last_message?.id}`)
      })
      
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
      // This would be a new API endpoint for conversation messages
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
      // Use database_id for WebSocket subscription (backend broadcasts to conversation_{UUID})
      const subscriptionId = conversation.database_id || conversation.id
      console.log(`🔔 Subscribing to conversation: conversation_${subscriptionId}`)
      const newSubscriptionId = subscribe(`conversation_${subscriptionId}`, (message: RealtimeMessage) => {
        console.log('📨 Conversation message received:', message)
        
        // Handle new messages in the current conversation - backend sends message data directly
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

  const handleContactResolution = (message: Message) => {
    setSelectedMessageForResolution(message)
    setContactResolutionOpen(true)
  }

  const handleResolutionComplete = async (messageId: string, contactRecord: any) => {
    console.log(`🔗 Contact resolution completed for message ${messageId}:`, contactRecord)
    
    // Refresh conversations to show updated contact status
    console.log(`🔄 Refreshing conversations after contact resolution...`)
    await loadConversations()
    await refreshContactResolution()
    
    console.log(`✅ Refresh completed, conversations should now show connected contact`)
    
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
    // Handle undefined/null type
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

  if (loading) {
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
            <p className="text-gray-600 dark:text-gray-400">All your communications in one place</p>
          </div>
          
          <div className="flex items-center space-x-2">
            {/* WebSocket Status Indicator */}
            <div className="flex items-center space-x-2 text-sm">
              <div className={`w-2 h-2 rounded-full ${
                wsConnected ? 'bg-green-500' : 'bg-red-500'
              }`}></div>
              <span className="text-gray-600 dark:text-gray-400">
                {wsConnected ? 'Real-time' : 'Offline'}
              </span>
            </div>
            
            <Button variant="outline" onClick={() => setComposeDialogOpen(true)}>
              <Send className="w-4 h-4 mr-2" />
              Compose
            </Button>
          </div>
        </div>

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
                              {conversation.type === 'whatsapp' ? (
                                (() => {
                                  // Get customer contact (never business) from conversation
                                  const customerContact = WhatsAppIdentityHandler.getCustomerContactFromConversation([conversation.last_message] as any);
                                  
                                  if (!customerContact) {
                                    return (
                                      <div className="w-10 h-10 rounded-full bg-gray-300 flex items-center justify-center text-sm font-medium flex-shrink-0">
                                        ?
                                      </div>
                                    );
                                  }
                                  
                                  return (
                                    <div className="w-10 h-10 rounded-full bg-gray-300 flex items-center justify-center text-sm font-medium overflow-hidden flex-shrink-0">
                                      {customerContact.profile_picture ? (
                                        <img 
                                          src={customerContact.profile_picture} 
                                          alt={customerContact.name}
                                          className="w-full h-full object-cover"
                                          onError={(e) => {
                                            e.currentTarget.style.display = 'none';
                                            const sibling = e.currentTarget.nextElementSibling as HTMLElement;
                                            if (sibling) sibling.style.display = 'flex';
                                          }}
                                        />
                                      ) : null}
                                      <span className={`${customerContact.profile_picture ? 'hidden' : 'flex'} items-center justify-center w-full h-full`}>
                                        {customerContact.name?.charAt(0).toUpperCase() || '?'}
                                      </span>
                                    </div>
                                  );
                                })()
                              ) : (
                                <div className="w-10 h-10 rounded-full bg-gray-300 flex items-center justify-center text-sm font-medium flex-shrink-0">
                                  {(conversation.participants?.[0]?.name || 'Unknown').charAt(0).toUpperCase()}
                                </div>
                              )}
                              
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center space-x-2 mb-1">
                                  {getMessageTypeIcon(conversation.type)}
                                  <span className={`font-medium truncate ${conversation.unread_count > 0 ? 'font-bold' : ''}`}>
                                    {conversation.type === 'whatsapp' && conversation.last_message ? (
                                      (() => {
                                        // Get customer contact from conversation (never business)
                                        const customerContact = WhatsAppIdentityHandler.getCustomerContactFromConversation([conversation.last_message] as any);
                                        
                                        if (!customerContact) {
                                          console.warn('⚠️ No customer contact found in conversation');
                                          return 'Unknown Contact';
                                        }
                                        
                                        return customerContact.name || 'Unknown Contact';
                                      })()
                                    ) : (
                                      conversation.participants?.[0]?.name || 'Unknown'
                                    )}
                                  </span>
                                  {conversation.unread_count > 0 && (
                                    <Badge variant="destructive" className="text-xs">
                                      {conversation.unread_count}
                                    </Badge>
                                  )}
                                </div>
                                <p className={`text-sm text-gray-600 dark:text-gray-400 truncate ${conversation.unread_count > 0 ? 'font-semibold' : ''}`}>
                                  {conversation.type === 'whatsapp' && conversation.last_message ? (
                                    (() => {
                                      const message = conversation.last_message as any;
                                      const isFromBusiness = WhatsAppIdentityHandler.isBusinessAccount(message.contact_email);
                                      const directionLabel = message.direction === 'outbound' || isFromBusiness ? 'You: ' : '';
                                      return `${directionLabel}${message.subject || message.content}`;
                                    })()
                                  ) : (
                                    conversation.last_message?.subject || conversation.last_message?.content
                                  )}
                                </p>
                                <div className="flex items-center justify-between mt-1">
                                  <div className="flex items-center space-x-2">
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
                                      onClick={() => handleContactResolution(conversation.last_message)}
                                    />
                                  </div>
                                  <span className="text-xs text-gray-500">
                                    {formatTimestamp(conversation.updated_at)}
                                  </span>
                                </div>
                                {/* Contact pipeline info */}
                                {conversation.primary_contact && (
                                  <div className="text-xs text-gray-500 mt-1 flex items-center">
                                    <span className="text-blue-600">CRM:</span> {conversation.primary_contact.pipeline_name}
                                  </div>
                                )}
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

          {/* Message Thread */}
          <div className="col-span-8">
            <Card className="h-full flex flex-col">
              {selectedConversation ? (
                <>
                  {/* Conversation Header */}
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <CardTitle className="flex items-center space-x-2">
                          {getMessageTypeIcon(selectedConversation.type)}
                          <span>
                            {(() => {
                              // Special handling for WhatsApp to show customer name, never business
                              if (selectedConversation.type === 'whatsapp' && selectedConversation.last_message) {
                                const customerContact = WhatsAppIdentityHandler.getCustomerContactFromConversation([selectedConversation.last_message] as any);
                                return customerContact?.name || 'Unknown Contact';
                              }
                              return selectedConversation.participants?.[0]?.name;
                            })()}
                          </span>
                          {getMessageTypeBadge(selectedConversation.type)}
                        </CardTitle>
                        <CardDescription>
                          {(() => {
                            // For WhatsApp, show phone number instead of email
                            if (selectedConversation.type === 'whatsapp' && selectedConversation.last_message) {
                              const message = selectedConversation.last_message as any;
                              const phoneNumber = message.contact_email?.replace('@s.whatsapp.net', '');
                              return phoneNumber ? `+${phoneNumber}` : selectedConversation.participants?.[0]?.email;
                            }
                            return selectedConversation.participants?.[0]?.email;
                          })()}
                        </CardDescription>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Button variant="outline" size="sm">
                          <Star className="w-4 h-4" />
                        </Button>
                        <Button variant="outline" size="sm">
                          <Archive className="w-4 h-4" />
                        </Button>
                        <Button variant="outline" size="sm">
                          <MoreVertical className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  </CardHeader>

                  <Separator />

                  {/* Messages */}
                  <CardContent className="flex-1 p-0">
                    <ScrollArea className="h-[calc(100vh-400px)] p-4">
                      {loadingMessages ? (
                        <div className="text-center py-8">
                          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
                          <p className="mt-2 text-sm text-gray-600">Loading messages...</p>
                        </div>
                      ) : messages.length === 0 ? (
                        <div className="text-center py-8 text-gray-500">
                          <MessageSquare className="w-8 h-8 mx-auto mb-2 text-gray-400" />
                          <p>No messages in this conversation</p>
                        </div>
                      ) : (
                        <div className="space-y-4">
                          {messages.map((message) => {
                            // Use WhatsApp identity handling for WhatsApp messages
                            const messageDisplay = message.type === 'whatsapp' 
                              ? WhatsAppIdentityHandler.formatMessageDisplay(message as any, user?.email)
                              : {
                                  senderName: message.sender.name,
                                  isFromBusiness: false,
                                  isFromCurrentUser: message.sender.email === user?.email,
                                  displayAvatar: message.sender.avatar
                                };

                            return (
                              <div
                                key={message.id}
                                className={`flex ${messageDisplay.isFromCurrentUser ? 'justify-end' : 'justify-start'}`}
                              >
                                <div className="flex items-start space-x-2 max-w-[70%]">
                                  {/* Profile picture for customer messages */}
                                  {!messageDisplay.isFromCurrentUser && (
                                    <div className="w-8 h-8 rounded-full bg-gray-300 flex items-center justify-center text-xs font-medium overflow-hidden">
                                      {messageDisplay.displayAvatar ? (
                                        <img 
                                          src={messageDisplay.displayAvatar} 
                                          alt={messageDisplay.senderName}
                                          className="w-full h-full object-cover"
                                          onError={(e) => {
                                            // Fallback to initials if image fails
                                            const target = e.currentTarget as HTMLImageElement;
                                            const nextElement = target.nextElementSibling as HTMLElement;
                                            target.style.display = 'none';
                                            if (nextElement) nextElement.style.display = 'block';
                                          }}
                                        />
                                      ) : null}
                                      <span className={messageDisplay.displayAvatar ? 'hidden' : 'block'}>
                                        {messageDisplay.senderName.charAt(0).toUpperCase()}
                                      </span>
                                    </div>
                                  )}
                                  
                                  <div className={`${
                                    messageDisplay.isFromCurrentUser 
                                      ? 'bg-blue-500 text-white' 
                                      : 'bg-gray-100 dark:bg-gray-800'
                                  } rounded-lg p-3`}>
                                    {/* Sender name for non-current user messages */}
                                    {!messageDisplay.isFromCurrentUser && message.type === 'whatsapp' && (
                                      <div className="font-medium text-xs mb-1 text-gray-600 dark:text-gray-400">
                                        {messageDisplay.senderName}
                                      </div>
                                    )}
                                    
                                    {message.subject && (
                                      <div className="font-medium text-sm mb-1 border-b border-gray-200 dark:border-gray-700 pb-1">
                                        {message.subject}
                                      </div>
                                    )}
                                    <div className="text-sm whitespace-pre-wrap">
                                      {message.content}
                                    </div>
                                    
                                    {/* WhatsApp delivery status */}
                                    {message.type === 'whatsapp' && message.metadata?.delivery_status && messageDisplay.isFromCurrentUser && (
                                      <div className="text-xs opacity-70 mt-1">
                                        {message.metadata.delivery_status === 'delivered' && '✓✓'}
                                        {message.metadata.delivery_status === 'read' && '✓✓ Read'}
                                        {message.metadata.delivery_status === 'sent' && '✓'}
                                      </div>
                                    )}
                                    
                                    {message.attachments && message.attachments.length > 0 && (
                                      <div className="mt-2 pt-2 border-t border-gray-200 dark:border-gray-700">
                                        {message.attachments.map((attachment, index) => (
                                          <div key={index} className="flex items-center space-x-2 text-xs">
                                            <Paperclip className="w-3 h-3" />
                                            <span>{attachment.name}</span>
                                          </div>
                                        ))}
                                      </div>
                                    )}
                                    <div className="text-xs opacity-70 mt-1">
                                      {formatTimestamp(message.timestamp)}
                                    </div>
                                  </div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </ScrollArea>
                  </CardContent>

                  <Separator />

                  {/* Reply Area */}
                  <div className="p-4">
                    <div className="flex items-end space-x-2">
                      <div className="flex-1">
                        <Textarea
                          placeholder={`Reply to ${selectedConversation.participants?.[0]?.name || 'Contact'}...`}
                          value={replyText}
                          onChange={(e) => setReplyText(e.target.value)}
                          className="min-h-[80px]"
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                              handleSendReply()
                            }
                          }}
                        />
                      </div>
                      <div className="flex flex-col space-y-2">
                        <Button variant="outline" size="sm">
                          <Paperclip className="w-4 h-4" />
                        </Button>
                        <Button onClick={handleSendReply} disabled={!replyText.trim()}>
                          <Send className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                    <div className="flex items-center justify-between mt-2">
                      <div className="flex space-x-2">
                        <Button 
                          variant="ghost" 
                          size="sm"
                          onClick={() => {
                            setReplyingTo(messages[messages.length - 1])
                            setComposeDialogOpen(true)
                          }}
                        >
                          <Reply className="w-4 h-4 mr-1" />
                          Reply
                        </Button>
                        <Button variant="ghost" size="sm">
                          <Forward className="w-4 h-4 mr-1" />
                          Forward
                        </Button>
                      </div>
                      <p className="text-xs text-gray-500">
                        Press Cmd+Enter to send
                      </p>
                    </div>
                  </div>
                </>
              ) : (
                <CardContent className="flex-1 flex items-center justify-center">
                  <div className="text-center text-gray-500">
                    <MessageSquare className="w-16 h-16 mx-auto mb-4 text-gray-400" />
                    <h3 className="text-lg font-medium mb-2">Select a conversation</h3>
                    <p>Choose a conversation from the left to start messaging</p>
                  </div>
                </CardContent>
              )}
            </Card>
          </div>
        </div>

        {/* Message Composer Dialog */}
        <MessageComposer
          open={composeDialogOpen}
          onOpenChange={(open) => {
            setComposeDialogOpen(open)
            if (!open) {
              setReplyingTo(null)
            }
          }}
          conversationId={replyingTo ? selectedConversation?.id : undefined}
          recipientType={replyingTo ? 'reply' : 'new'}
          defaultRecipient={replyingTo ? {
            name: replyingTo.sender.name,
            email: replyingTo.sender.email,
            platform: replyingTo.type,
            platform_id: replyingTo.sender.platform_id
          } : undefined}
          accountConnections={accountConnections}
        />

        {/* Contact Resolution Dialog */}
        <ContactResolutionDialog
          message={selectedMessageForResolution}
          isOpen={contactResolutionOpen}
          onClose={() => {
            setContactResolutionOpen(false)
            setSelectedMessageForResolution(null)
          }}
          onResolutionComplete={handleResolutionComplete}
        />
      </div>
    </div>
  )
}