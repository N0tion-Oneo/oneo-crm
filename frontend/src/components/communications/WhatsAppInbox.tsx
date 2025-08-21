'use client'

import React, { useState, useEffect, useRef, useCallback } from 'react'
import { MessageSquare, Search, Filter, Phone, Video, MoreVertical, Paperclip, Send, Smile, Image, RefreshCw, MapPin, Contact, History } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { ScrollArea } from '@/components/ui/scroll-area'
import { SafeAvatar } from '@/components/communications/SafeAvatar'
import { useToast } from '@/hooks/use-toast'
import { MessageContent } from '@/components/MessageContent'
import { formatDistanceToNow } from 'date-fns'
import { api } from '@/lib/api'
import { useWebSocket, type RealtimeMessage } from '@/contexts/websocket-context'

// Helper function to safely format dates
const formatSafeDate = (dateString: string | undefined | null): string => {
  if (!dateString) return 'No date'
  
  try {
    const date = new Date(dateString)
    if (isNaN(date.getTime())) return 'Invalid date'
    return formatDistanceToNow(date)
  } catch (error) {
    console.error('Error formatting date:', dateString, error)
    return 'Invalid date'
  }
}

// Helper function to safely format time
const formatSafeTime = (dateString: string | undefined | null): string => {
  if (!dateString) return 'No time'
  
  try {
    const date = new Date(dateString)
    if (isNaN(date.getTime())) return 'Invalid time'
    return date.toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch (error) {
    console.error('Error formatting time:', dateString, error)
    return 'Invalid time'
  }
}

// Based on Unipile Chat/Messaging API: /api/v1/chats/{chat_id}/messages
interface WhatsAppMessage {
  id: string
  text?: string
  html?: string
  type: 'text' | 'image' | 'video' | 'audio' | 'document' | 'location' | 'contact'
  direction: 'in' | 'out'
  chat_id: string
  date: string
  status: 'pending' | 'sent' | 'delivered' | 'read' | 'failed'
  attendee_id?: string  // For 'in' direction messages
  attachments?: Array<{
    id: string
    type: 'image' | 'video' | 'audio' | 'document'
    filename?: string
    url?: string
    thumbnail_url?: string
    size?: number
    mime_type?: string
  }>
  location?: {
    latitude: number
    longitude: number
    address?: string
  }
  contact?: {
    name: string
    phone: string
    vcard?: string
  }
  quoted_message_id?: string  // For replies
  account_id: string
}

// Based on Unipile Chat API: /api/v1/chats
interface WhatsAppChat {
  id: string
  provider_chat_id: string  // WhatsApp's internal chat ID
  name?: string  // Group name or contact name
  picture_url?: string
  is_group: boolean
  is_muted: boolean
  is_pinned: boolean
  is_archived: boolean
  unread_count: number
  last_message_date: string
  account_id: string
  attendees: Array<{
    id: string
    name?: string
    phone?: string
    picture_url?: string
    is_admin?: boolean  // For group chats
  }>
  latest_message?: WhatsAppMessage
  member_count?: number  // For group chats
}

// Chat attendee details from /api/v1/chat_attendees/{id}
interface WhatsAppAttendee {
  id: string
  name?: string
  phone?: string
  picture_url?: string
  provider_id: string  // WhatsApp user ID
  is_business_account: boolean
  status?: string  // WhatsApp status message
  last_seen?: string
  account_id: string
}

interface WhatsAppInboxProps {
  className?: string
}

export default function WhatsAppInbox({ className }: WhatsAppInboxProps) {
  const [chats, setChats] = useState<WhatsAppChat[]>([])
  const [selectedChat, setSelectedChat] = useState<WhatsAppChat | null>(null)
  // Attendees are now included directly in chat data, no separate state needed
  const [messages, setMessages] = useState<WhatsAppMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [loadingMessages, setLoadingMessages] = useState(false)
  const [loadingMoreChats, setLoadingMoreChats] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [chatCursor, setChatCursor] = useState<string | null>(null)
  const [hasMoreChats, setHasMoreChats] = useState(true)
  const [messageCursor, setMessageCursor] = useState<string | null>(null)
  const [hasMoreMessages, setHasMoreMessages] = useState(true)
  const [loadingMoreMessages, setLoadingMoreMessages] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterStatus, setFilterStatus] = useState<'all' | 'unread' | 'groups' | 'archived'>('all')
  const [accountConnections, setAccountConnections] = useState<Array<{
    id: string
    connection_id?: string
    provider: 'whatsapp'
    phone: string
    status: 'active' | 'error' | 'syncing'
    business_account: boolean
    auth_status?: string
    last_sync_at?: string
  }>>([])
  const [replyText, setReplyText] = useState('')
  const [composing, setComposing] = useState(false)
  const [selectedFiles, setSelectedFiles] = useState<FileList | null>(null)
  const [attachmentPreviews, setAttachmentPreviews] = useState<Array<{
    file: File
    type: 'image' | 'video' | 'audio' | 'document'
    preview?: string
  }>>([])
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [syncingChat, setSyncingChat] = useState<string | null>(null)
  const { toast } = useToast()

  // Cleanup attachment previews on unmount
  useEffect(() => {
    return () => {
      attachmentPreviews.forEach(preview => {
        if (preview.preview) {
          URL.revokeObjectURL(preview.preview)
        }
      })
    }
  }, [])

  // WebSocket integration for real-time updates
  const {
    isConnected: wsConnected,
    connectionStatus: wsConnectionStatus,
    subscribe,
    unsubscribe
  } = useWebSocket()

  // Handle real-time WebSocket messages
  const handleWebSocketMessage = useCallback((message: RealtimeMessage) => {
    console.log('🚨 === WEBSOCKET MESSAGE RECEIVED ===')
    console.log('📨 Full message object:', JSON.stringify(message, null, 2))
    console.log('📨 Message type:', message.type)
    console.log('📨 Has message key:', !!message.message)
    console.log('📨 Has payload key:', !!message.payload)
    console.log('📨 Has data key:', !!message.data)
    console.log('📨 Selected chat ID:', selectedChat?.id)
    console.log('🚨 ======================================')
    
    switch (message.type) {
      case 'new_message':
        console.log('🟢 Processing new_message')
        const newMessageData = message.message || message.payload || message.data
        console.log('🟢 Message data to process:', newMessageData)
        handleNewMessage(newMessageData)
        break
      case 'message_update':
        console.log('🟡 Processing message_update')
        const updateMessageData = message.message || message.payload || message.data
        console.log('🟡 Update data to process:', updateMessageData)
        console.log('🟡 Full WebSocket message:', message)
        handleMessageUpdate(updateMessageData, message.conversation_id)
        break
      case 'message_status_update':
        console.log('🔵 Processing message_status_update')
        const statusMessageData = message.message || message.payload || message.data
        console.log('🔵 Status data to process:', statusMessageData)
        console.log('🔵 Full WebSocket message:', message)
        handleMessageUpdate(statusMessageData, message.conversation_id)
        break
      case 'conversation_update':
        console.log('🟣 Processing conversation_update')
        const convUpdateData = message.conversation || message.payload || message.data
        console.log('🟣 Conversation data to process:', convUpdateData)
        handleConversationUpdate(convUpdateData)
        break
      case 'new_conversation':
        console.log('🟠 Processing new_conversation')
        const newConvData = message.conversation || message.payload || message.data
        console.log('🟠 New conversation data to process:', newConvData)
        handleNewConversation(newConvData)
        break
      default:
        console.log('❌ Unhandled WhatsApp WebSocket message type:', message.type)
        console.log('❌ Available message types should be: new_message, message_update, message_status_update, conversation_update, new_conversation')
    }
  }, [selectedChat])

  // Handle message updates (status changes, etc.)
  const handleMessageUpdate = useCallback((messageData: any, websocketConversationId?: string) => {
    console.log('🔄 === MESSAGE UPDATE HANDLER ===')
    console.log('🔄 Processing message update:', messageData)
    console.log('🔄 Message ID:', messageData?.id)
    console.log('🔄 New Status:', messageData?.status)
    console.log('🔄 ================================')
    
    if (!messageData || !messageData.id) {
      console.log('❌ No message data or ID, skipping update')
      return
    }
    
    const messageId = messageData.id
    
    // Update message in the messages list
    setMessages(prev => {
      console.log(`🔄 Current messages count: ${prev.length}`)
      console.log(`🔄 Looking for message ID: ${messageId}`)
      console.log(`🔄 Message IDs in list:`, prev.map(m => m.id))
      
      const updated = prev.map(existingMessage => {
        if (existingMessage.id === messageId) {
          console.log(`🔄 ✅ FOUND MESSAGE - Updating status: ${existingMessage.status} → ${messageData.status}`)
          return {
            ...existingMessage,
            status: messageData.status || existingMessage.status,
            // Update other fields as needed
            text: messageData.text || existingMessage.text,
            date: messageData.date || existingMessage.date,
          }
        }
        return existingMessage
      })
      
      // Check if we actually updated anything
      const wasUpdated = updated.some(msg => msg.id === messageId)
      if (!wasUpdated) {
        console.log(`❌ Message ${messageId} not found in current messages list`)
        console.log(`❌ Available message IDs:`, prev.map(m => `${m.id} (${m.status})`))
        return prev
      }
      
      console.log(`✅ Successfully updated message ${messageId}`)
      return updated
    })
    
    // Also update the chat list if this affects the latest message
    // Note: The WebSocket event has conversation_id at the root level (external thread ID)
    // while messageData.conversation_id is the database UUID. We need the external thread ID for matching.
    const conversation_id = websocketConversationId || messageData.conversation_id || messageData.conversation || messageData.chat_id
    console.log(`🔄 CHAT LIST UPDATE CHECK: conversation_id=${conversation_id}, messageId=${messageId}`)
    console.log(`🔄 Available IDs:`, {
      websocketConversationId,
      'messageData.conversation_id': messageData.conversation_id,
      'messageData.conversation': messageData.conversation,
      'messageData.chat_id': messageData.chat_id
    })
    
    if (conversation_id) {
      setChats(prev => {
        console.log(`🔄 Checking ${prev.length} chats for conversation ${conversation_id}`)
        
        return prev.map(chat => {
          const chatMatches = chat.id === conversation_id || chat.provider_chat_id === conversation_id
          const isLatestMessage = chat.latest_message?.id === messageId
          
          console.log(`🔄 Chat ${chat.name}: matches=${chatMatches}, latestMsgId=${chat.latest_message?.id}, isLatest=${isLatestMessage}`)
          
          if (chatMatches && isLatestMessage) {
            console.log(`🔄 ✅ UPDATING chat list status: ${chat.latest_message.status} → ${messageData.status}`)
            return {
              ...chat,
              latest_message: {
                ...chat.latest_message,
                status: messageData.status || chat.latest_message.status
              }
            }
          }
          return chat
        })
      })
    }
  }, [])

  // Handle new incoming messages
  const handleNewMessage = useCallback((messageData: any) => {
    console.log('📨 Processing new WhatsApp message:', messageData)
    
    if (!messageData) return
    
    // Handle both old format (conversation_id, message) and new format (direct message data)
    const message = messageData.message || messageData
    
    // Debug conversation ID extraction
    console.log('🔍 CONVERSATION ID EXTRACTION:', {
      'messageData.conversation_id': messageData.conversation_id,
      'message?.conversation_id': message?.conversation_id,
      'message?.metadata?.chat_id': message?.metadata?.chat_id,
      'messageData.metadata?.chat_id': messageData.metadata?.chat_id,
      'messageData structure': Object.keys(messageData),
      'message.metadata structure': message?.metadata ? Object.keys(message.metadata) : 'no metadata'
    })
    
    // Extract conversation ID from multiple possible sources
    const conversation_id = (
      messageData.conversation_id ||           // Direct conversation_id
      message?.conversation_id ||              // Message conversation_id  
      message?.metadata?.chat_id ||            // Webhook messages have chat_id in metadata
      messageData.metadata?.chat_id ||         // Alternative metadata location
      messageData.external_thread_id ||        // API messages might use this
      message?.external_thread_id ||           // Message external thread ID
      (selectedChat?.id)                       // Fallback to selected chat for API messages
    )
    
    // Update messages if this is the currently selected chat
    console.log('🔍 ID MATCHING DEBUG:', {
      messageConversationId: conversation_id,
      selectedChatId: selectedChat?.id,
      selectedChatProviderId: selectedChat?.provider_chat_id,
      willUpdate: selectedChat && (conversation_id === selectedChat.id || conversation_id === selectedChat.provider_chat_id)
    })
    
    if (selectedChat && (conversation_id === selectedChat.id || conversation_id === selectedChat.provider_chat_id)) {
      setMessages(prev => {
        // Check if message already exists to prevent duplicates
        const exists = prev.some(msg => msg.id === message.id)
        console.log('🔍 DUPLICATE CHECK:', {
          messageId: message.id,
          exists: exists,
          existingMessageIds: prev.map(m => m.id),
          totalMessages: prev.length
        })
        
        if (exists) {
          console.log('⚠️  Message already exists, skipping duplicate')
          return prev
        }
        
        // Debug attachment data mapping
        console.log('🔍 ATTACHMENT DEBUG:', {
          'message.attachments': message.attachments,
          'message.metadata?.attachments': message.metadata?.attachments,
          'message.metadata': message.metadata,
          finalAttachments: (message.attachments || message.metadata?.attachments) || []
        })
        
        // Transform and add new message
        const newMessage: WhatsAppMessage = {
          id: message.id,
          text: message.text || message.content,
          html: message.html,
          type: mapMessageType(message.type),
          direction: message.direction,
          chat_id: selectedChat.id,
          date: message.date || message.created_at || new Date().toISOString(),
          status: message.status || 'sent',
          attendee_id: message.attendee_id || message.from_id,
          attachments: ((message.attachments || message.metadata?.attachments) || []).map((att: any) => ({
            id: att.id,
            type: att.type,
            filename: att.filename,
            url: att.url,
            thumbnail_url: att.thumbnail_url,
            size: att.size,
            mime_type: att.mime_type
          })),
          location: message.location,
          contact: message.contact,
          quoted_message_id: message.quoted_message_id,
          account_id: selectedChat.account_id
        }
        
        // Add to beginning of array (newest first) and sort
        const updated = [newMessage, ...prev].sort((a, b) => 
          new Date(b.date).getTime() - new Date(a.date).getTime()
        )
        
        console.log(`✅ Added new message to chat ${selectedChat.id}:`, newMessage.text?.substring(0, 50))
        return updated
      })
    }
    
    // Update chat list with new message
    setChats(prev => {
      const updated = prev.map(chat => {
        if (chat.id === conversation_id || chat.provider_chat_id === conversation_id) {
          const isInbound = message.direction === 'in' || message.direction === 'inbound'
          // Always increment unread for inbound messages (for testing unread badges)
          const shouldIncrementUnread = isInbound
          // Original logic: const shouldIncrementUnread = isInbound && (!selectedChat || selectedChat.id !== chat.id)
          const messageTimestamp = message.date || message.created_at || new Date().toISOString()
          
          console.log(`🔄 Updating chat ${chat.id} (${chat.name}) with new message at:`, messageTimestamp)
          console.log(`🔄 Unread count: ${chat.unread_count} → ${shouldIncrementUnread ? chat.unread_count + 1 : chat.unread_count} (isInbound: ${isInbound}, shouldIncrement: ${shouldIncrementUnread})`)
          
          return {
            ...chat,
            latest_message: {
              id: message.id,
              text: message.text || message.content,
              type: mapMessageType(message.type),
              direction: message.direction,
              chat_id: chat.id,
              date: messageTimestamp,
              status: message.status || 'sent',
              attendee_id: message.attendee_id,
              attachments: message.attachments || message.metadata?.attachments || [],
              account_id: chat.account_id
            },
            unread_count: shouldIncrementUnread ? chat.unread_count + 1 : chat.unread_count,
            last_message_date: messageTimestamp
          }
        }
        return chat
      })
      
      // Sort by newest message timestamp  
      const sorted = updated.sort((a, b) => new Date(b.last_message_date).getTime() - new Date(a.last_message_date).getTime())
      
      return sorted
    })
    
    // Show toast notification for new inbound messages
    if ((message.direction === 'in' || message.direction === 'inbound') && 
        (!selectedChat || conversation_id !== selectedChat.id)) {
      const chatName = chats.find(c => c.id === conversation_id || c.provider_chat_id === conversation_id)?.name || 'Unknown'
      toast({
        title: `New WhatsApp message from ${chatName}`,
        description: (message.text || message.content || 'New message').substring(0, 100),
      })
    }
  }, [selectedChat, chats, toast])

  // Handle conversation updates (metadata changes)
  const handleConversationUpdate = useCallback((conversationData: any) => {
    console.log('💬 Processing WhatsApp conversation update:', conversationData)
    
    if (!conversationData) return
    
    const { conversation_id, message_count, unread_count, last_message_at } = conversationData
    
    setChats(prev => prev.map(chat => {
      if (chat.id === conversation_id || chat.provider_chat_id === conversation_id) {
        return {
          ...chat,
          unread_count: unread_count !== undefined ? unread_count : chat.unread_count,
          last_message_date: last_message_at || chat.last_message_date
        }
      }
      return chat
    }))
    
    // Update selected chat if it matches
    if (selectedChat && (selectedChat.id === conversation_id || selectedChat.provider_chat_id === conversation_id)) {
      setSelectedChat(prev => prev ? {
        ...prev,
        unread_count: unread_count !== undefined ? unread_count : prev.unread_count,
        last_message_date: last_message_at || prev.last_message_date
      } : prev)
    }
  }, [selectedChat])

  // Handle new conversations
  const handleNewConversation = useCallback((conversationData: any) => {
    console.log('🆕 Processing new WhatsApp conversation:', conversationData)
    
    if (!conversationData) return
    
    // Transform the conversation data to WhatsApp chat format
    const newChat: WhatsAppChat = {
      id: conversationData.id,
      provider_chat_id: conversationData.provider_chat_id || conversationData.chat_id,
      name: conversationData.name || conversationData.title,
      picture_url: conversationData.picture_url,
      is_group: conversationData.is_group || false,
      is_muted: conversationData.is_muted || false,
      is_pinned: conversationData.is_pinned || false,
      is_archived: conversationData.is_archived || false,
      unread_count: conversationData.unread_count || 1, // New conversation likely has unread messages
      last_message_date: conversationData.last_message_date || conversationData.updated_at || new Date().toISOString(),
      account_id: conversationData.account_id || (accountConnections[0]?.id || ''),
      attendees: (conversationData.attendees || []).map((att: any) => ({
        id: att.id,
        name: att.name,
        phone: att.phone,
        picture_url: att.picture_url,
        provider_id: att.provider_id,
        is_admin: att.is_admin || false,
        is_business_account: att.is_business_account || false
      })),
      latest_message: conversationData.latest_message,
      member_count: conversationData.member_count
    }
    
    // Add to chat list if it doesn't exist
    setChats(prev => {
      const exists = prev.some(chat => chat.id === newChat.id || chat.provider_chat_id === newChat.provider_chat_id)
      if (exists) return prev
      
      return [newChat, ...prev].sort((a, b) => 
        new Date(b.last_message_date).getTime() - new Date(a.last_message_date).getTime()
      )
    })
    
    // Show notification
    toast({
      title: `New WhatsApp conversation`,
      description: `New conversation with ${newChat.name || 'Unknown contact'}`,
    })
  }, [accountConnections, toast])

  // Subscribe to WhatsApp-specific WebSocket channels
  useEffect(() => {
    if (!wsConnected) return
    
    console.log('📡 Setting up WhatsApp WebSocket subscriptions')
    
    const subscriptions: string[] = []
    
    // Subscribe ONLY to conversation-specific channel (the only one that works)
    if (selectedChat) {
      const chatSubscription = subscribe(`conversation_${selectedChat.id}`, handleWebSocketMessage)
      subscriptions.push(chatSubscription)
      console.log(`📡 ✅ CORRECTLY Subscribed to conversation_${selectedChat.id} with ID:`, chatSubscription)
      
      // Also subscribe to unified inbox updates for general communication changes
      const inboxSubscription = subscribe('unified_inbox_updates', handleWebSocketMessage)
      subscriptions.push(inboxSubscription)
      console.log('📡 ✅ CORRECTLY Subscribed to unified_inbox_updates with ID:', inboxSubscription)
    } else {
      console.log('📡 ⚠️ No selected chat - cannot subscribe to conversation channel')
    }
    
    // Cleanup subscriptions
    return () => {
      subscriptions.forEach(id => unsubscribe(id))
      console.log('📡 WhatsApp unsubscribed from all channels')
    }
  }, [wsConnected, accountConnections, selectedChat, subscribe, unsubscribe, handleWebSocketMessage])

  // No periodic refresh needed - timestamps should be instant from backend

  // Handle file selection for attachments
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return

    const newPreviews: typeof attachmentPreviews = []
    
    Array.from(files).forEach((file) => {
      const fileType = file.type.split('/')[0]
      let type: 'image' | 'video' | 'audio' | 'document' = 'document'
      
      if (fileType === 'image') type = 'image'
      else if (fileType === 'video') type = 'video'  
      else if (fileType === 'audio') type = 'audio'
      
      const preview: typeof attachmentPreviews[0] = {
        file,
        type,
      }
      
      // Generate preview URL for images
      if (type === 'image') {
        preview.preview = URL.createObjectURL(file)
      }
      
      newPreviews.push(preview)
    })
    
    setAttachmentPreviews(prev => [...prev, ...newPreviews])
    setSelectedFiles(files)
    
    // Clear the input so the same file can be selected again
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  // Remove attachment from preview
  const removeAttachment = (index: number) => {
    setAttachmentPreviews(prev => {
      const removed = prev[index]
      // Clean up preview URL to prevent memory leaks
      if (removed.preview) {
        URL.revokeObjectURL(removed.preview)
      }
      return prev.filter((_, i) => i !== index)
    })
  }

  // Clear all attachments
  const clearAttachments = () => {
    attachmentPreviews.forEach(preview => {
      if (preview.preview) {
        URL.revokeObjectURL(preview.preview)
      }
    })
    setAttachmentPreviews([])
    setSelectedFiles(null)
  }

  // Handle attachment download/preview
  const handleAttachmentClick = async (messageId: string, attachment: WhatsAppMessage['attachments'][0]) => {
    if (!attachment) return

    try {
      // For images, show preview in new tab
      if (attachment.type === 'image' && attachment.url) {
        window.open(attachment.url, '_blank')
        return
      }

      // For locations, open in maps
      if (attachment.type === 'location') {
        const location = messages.find(m => m.id === messageId)?.location
        if (location) {
          const mapsUrl = `https://maps.google.com?q=${location.latitude},${location.longitude}`
          window.open(mapsUrl, '_blank')
          return
        }
      }

      // For contacts, show contact info
      if (attachment.type === 'contact') {
        const contact = messages.find(m => m.id === messageId)?.contact
        if (contact) {
          toast({
            title: "Contact Information",
            description: `Name: ${contact.name}\nPhone: ${contact.phone}`,
            duration: 5000,
          })
          return
        }
      }

      // For other attachments, download via our API
      const response = await api.get(
        `/api/v1/communications/messages/${messageId}/attachments/${attachment.id}/download/`,
        {
          responseType: 'blob' // Important for file downloads
        }
      )

      // Create download link
      const blob = new Blob([response.data], { 
        type: attachment.mime_type || 'application/octet-stream' 
      })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = attachment.filename || `attachment_${attachment.id}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)

      toast({
        title: "Attachment downloaded",
        description: `${attachment.filename} has been downloaded successfully.`,
      })

    } catch (error: any) {
      console.error('Failed to download attachment:', error)
      toast({
        title: "Download failed",
        description: error.response?.data?.error || "Failed to download attachment.",
        variant: "destructive",
      })
    }
  }

  // Profile pictures are now loaded efficiently on the backend with chat data

  // Enhanced avatar component using SafeAvatar for error handling
  const EnhancedAvatar = ({ chat, size = 'w-10 h-10' }: { chat: WhatsAppChat, size?: string }) => {
    // Use picture_url from chat data (loaded efficiently on backend)
    const pictureUrl = chat.picture_url || chat.attendees[0]?.picture_url
    const fallbackText = chat.is_group ? 'G' : (chat.name?.charAt(0) || chat.attendees[0]?.name?.charAt(0) || 'W')
    
    return (
      <SafeAvatar
        src={pictureUrl}
        fallbackText={fallbackText}
        className={size}
        fallbackClassName="bg-green-100 text-green-700"
      />
    )
  }

  // Sync chat history for a specific chat
  const handleChatHistorySync = async (chat: WhatsAppChat, fullSync: boolean = false) => {
    if (!chat || syncingChat === chat.id) return

    setSyncingChat(chat.id)

    try {
      const response = await api.post(`/api/v1/communications/whatsapp/chats/${chat.id}/sync/`, {
        full_sync: fullSync,
        since: fullSync ? null : new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString() // Last 7 days for partial sync
      })

      if (response.data?.success) {
        const syncId = response.data.sync_id
        const estimatedMessages = response.data.estimated_messages || 0

        toast({
          title: "Chat sync started",
          description: `${fullSync ? 'Full' : 'Recent'} history sync initiated for ${chat.name || 'this chat'}. ${estimatedMessages > 0 ? `Estimated ${estimatedMessages} messages to sync.` : ''}`,
        })

        // Poll for sync status
        const pollSyncStatus = async () => {
          try {
            const statusResponse = await api.get(
              `/api/v1/communications/whatsapp/chats/${chat.id}/sync/status/`,
              { params: { sync_id: syncId } }
            )

            if (statusResponse.data?.success) {
              const status = statusResponse.data.status
              const progress = statusResponse.data.progress || 0
              const syncedMessages = statusResponse.data.synced_messages || 0

              if (status === 'completed') {
                setSyncingChat(null)
                toast({
                  title: "Chat sync completed",
                  description: `Successfully synced ${syncedMessages} messages for ${chat.name || 'this chat'}.`,
                })

                // Reload messages for the current chat
                if (selectedChat?.id === chat.id) {
                  handleChatSelect(chat)
                }
                return
              } else if (status === 'failed' || status === 'error') {
                setSyncingChat(null)
                toast({
                  title: "Chat sync failed",
                  description: statusResponse.data.error || "Failed to sync chat history.",
                  variant: "destructive",
                })
                return
              } else if (status === 'in_progress' || status === 'running') {
                // Continue polling
                setTimeout(pollSyncStatus, 3000) // Poll every 3 seconds
                return
              }
            }

            // If we get here, something went wrong
            setTimeout(pollSyncStatus, 5000) // Try again in 5 seconds
          } catch (error) {
            console.error('Failed to check sync status:', error)
            setTimeout(pollSyncStatus, 10000) // Retry in 10 seconds
          }
        }

        // Start polling after a short delay
        setTimeout(pollSyncStatus, 2000)

      } else {
        throw new Error(response.data?.error || 'Failed to start chat sync')
      }

    } catch (error: any) {
      console.error('Failed to sync chat history:', error)
      setSyncingChat(null)

      toast({
        title: "Failed to start sync",
        description: error.response?.data?.error || error.message || "Failed to start chat history sync.",
        variant: "destructive",
      })
    }
  }

  // Load WhatsApp chats and account connections from real Unipile API
  useEffect(() => {
    // Only load if we don't already have chats to prevent unnecessary flashing
    if (chats.length === 0) {
      loadWhatsAppData()
    }
  }, [])

  const loadWhatsAppData = async () => {
    try {
      // Only show loading if we don't have any data yet
      if (chats.length === 0) {
        setLoading(true)
      }
      
      // Load WhatsApp account connections
      const accountsResponse = await api.get('/api/v1/communications/whatsapp/accounts/')
      const connections = accountsResponse.data?.accounts || []
      
      // Set account connections
      setAccountConnections(connections.map((account: any) => ({
        id: account.id,
        connection_id: account.connection_id,
        provider: 'whatsapp' as const,
        phone: account.phone || account.identifier,
        status: account.status === 'active' && account.auth_status === 'authenticated' ? 'active' : 'error',
        business_account: account.is_business || false,
        auth_status: account.auth_status,
        last_sync_at: account.last_sync_at
      })))

      if (connections.length === 0) {
        setLoading(false)
        return
      }

      // Reset pagination state and load first batch of chats
      setChatCursor(null)
      setHasMoreChats(true)
      // Don't clear chats here - let loadMoreChats handle it to prevent flash
      
      // Load initial batch of chats (10 conversations)
      await loadMoreChats(connections, true)
      
    } catch (error: any) {
      console.error('Failed to load WhatsApp data:', error)
      
      // Show specific error based on response
      const errorMessage = error.response?.data?.error || error.message || 'Unknown error occurred'
      const errorType = error.response?.data?.error_type
      
      toast({
        title: errorType === 'connection_error' ? "Connection Error" : "Failed to load WhatsApp data",
        description: errorMessage,
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const loadMoreChats = async (connections?: any[], isInitialLoad = false) => {
    if (!isInitialLoad && (loadingMoreChats || !hasMoreChats)) return
    
    try {
      setLoadingMoreChats(true)
      
      // Use provided connections or current account connections
      const accountsToUse = connections || accountConnections
      if (accountsToUse.length === 0) return

      const allChats: WhatsAppChat[] = []
      let newCursor = chatCursor
      let hasMoreData = false

      // For multi-account setups, we need to handle pagination differently
      // We'll load from the first account that still has more data
      const accountToLoad = accountsToUse[0] // For now, load from first account
      
      console.log(`🔄 Loading chats for account ${accountToLoad.id}, cursor: ${chatCursor}`)
      
      try {
        // Get chats for this account with pagination using local-first endpoint
        const chatsResponse = await api.get('/api/v1/communications/whatsapp/chats/', {
          params: { 
            account_id: accountToLoad.id,
            limit: 15, // Load 15 chats consistently
            ...(chatCursor && { cursor: chatCursor }),
            force_sync: isInitialLoad ? 'false' : 'false' // Use cached data for better performance
          }
        })
        
        console.log(`📊 Chat response for account ${accountToLoad.id}:`, chatsResponse.data)
        console.log(`📊 Raw API URL called:`, chatsResponse.config?.url)
        console.log(`📊 API response timestamp:`, new Date().toISOString())
        
        const accountChats = chatsResponse.data?.chats || []
        newCursor = chatsResponse.data?.cursor
        hasMoreData = chatsResponse.data?.has_more || false
        
        console.log(`📊 Account ${accountToLoad.id}: loaded ${accountChats.length} chats, cursor: ${newCursor}, hasMore: ${hasMoreData}`)
        
        // Update pagination state based on this account's response
        setHasMoreChats(hasMoreData)
          
        // Transform API response to WhatsApp chat format
        for (const chatData of accountChats) {
          // Debug timestamp and unread count data from backend
          console.log(`🔍 Chat "${chatData.name}" debug:`, {
            chatId: chatData.id,
            unread_count: chatData.unread_count,
            latest_message_date: chatData.latest_message?.date,
            latest_message_created_at: chatData.latest_message?.created_at,
            last_message_date: chatData.last_message_date,
            updated_at: chatData.updated_at,
            latest_message_text: chatData.latest_message?.text?.substring(0, 50),
            finalTimestamp: chatData.latest_message?.date || chatData.latest_message?.created_at || chatData.last_message_date || chatData.updated_at,
            priorityOrder: [
              { source: 'latest_message.date', value: chatData.latest_message?.date },
              { source: 'latest_message.created_at', value: chatData.latest_message?.created_at },
              { source: 'last_message_date', value: chatData.last_message_date },
              { source: 'updated_at', value: chatData.updated_at }
            ]
          })
          
          // Additional debug: which timestamp will be used?
          const selectedTimestamp = chatData.latest_message?.date || chatData.latest_message?.created_at || chatData.last_message_date || chatData.updated_at
          console.log(`🔍 Chat "${chatData.name}" will use timestamp:`, selectedTimestamp)
          
          // Check if timestamps match
          if (chatData.last_message_date && chatData.latest_message?.date) {
            const timeDiff = Math.abs(new Date(chatData.last_message_date).getTime() - new Date(chatData.latest_message.date).getTime())
            if (timeDiff > 1000) { // More than 1 second difference
              console.warn(`⚠️ Chat "${chatData.name}" timestamp mismatch: last_message_date=${chatData.last_message_date} vs latest_message.date=${chatData.latest_message.date}`)
            }
          }
          
          const transformedChat: WhatsAppChat = {
            id: chatData.id,
            provider_chat_id: chatData.provider_chat_id || chatData.chat_id,
            name: chatData.name || chatData.title,
            picture_url: chatData.picture_url,
            is_group: chatData.is_group || false,
            is_muted: chatData.is_muted || false,
            is_pinned: chatData.is_pinned || false,
            is_archived: chatData.is_archived || false,
            unread_count: chatData.unread_count || 0,
            last_message_date: chatData.latest_message?.date || chatData.latest_message?.created_at || chatData.last_message_date || chatData.updated_at,
            account_id: accountToLoad.id,
            attendees: (chatData.attendees || []).map((att: any) => ({
              id: att.id,
              name: att.name,
              phone: att.phone,
              picture_url: att.picture_url,
              provider_id: att.provider_id,
              is_admin: att.is_admin || false,
              is_business_account: att.is_business_account || false
            })),
            latest_message: chatData.latest_message ? {
              id: chatData.latest_message.id,
              text: chatData.latest_message.text || chatData.latest_message.content,
              type: mapMessageType(chatData.latest_message.type),
              direction: chatData.latest_message.direction,
              chat_id: chatData.id,
              date: chatData.latest_message.date || chatData.latest_message.created_at,
              status: chatData.latest_message.status || 'sent',
              attendee_id: chatData.latest_message.attendee_id,
              attachments: chatData.latest_message.attachments || [],
              account_id: accountToLoad.id
            } : undefined,
            member_count: chatData.member_count
          }
          
          // Debug final unread count
          console.log(`🔍 Final chat "${transformedChat.name}" unread_count: ${transformedChat.unread_count}`)
          
          allChats.push(transformedChat)
        }
        
      } catch (error) {
        console.error(`Failed to load data for WhatsApp account ${accountToLoad.id}:`, error)
      }

      // Update cursor for next page
      console.log(`🔄 Updating pagination: cursor=${newCursor}, hasMore=${hasMoreData}`)
      setChatCursor(newCursor)

      // Sort chats by last message date (most recent first)
      allChats.sort((a, b) => new Date(b.last_message_date).getTime() - new Date(a.last_message_date).getTime())
      
      // Append to existing chats or replace for initial load
      if (isInitialLoad) {
        console.log(`🔄 Initial load: setting ${allChats.length} chats`)
        // Only replace if we don't have chats or if the data is significantly different
        setChats(prev => {
          // If we already have chats, merge intelligently to prevent flash
          if (prev.length > 0) {
            // Create a map of existing chats by ID for quick lookup
            const existingChatMap = new Map(prev.map(chat => [chat.id, chat]))
            
            // Merge new chats with existing ones, updating where necessary
            const mergedChats = allChats.map(newChat => {
              const existing = existingChatMap.get(newChat.id)
              if (existing) {
                // Update existing chat with new data
                return {
                  ...existing,
                  ...newChat,
                  // Preserve any real-time updates that might be newer
                  latest_message: newChat.latest_message?.date > (existing.latest_message?.date || '') 
                    ? newChat.latest_message 
                    : existing.latest_message,
                  last_message_date: newChat.last_message_date > existing.last_message_date 
                    ? newChat.last_message_date 
                    : existing.last_message_date
                }
              }
              return newChat
            })
            
            // Add any existing chats that weren't in the new list
            const newChatIds = new Set(allChats.map(chat => chat.id))
            const remainingExisting = prev.filter(chat => !newChatIds.has(chat.id))
            
            return [...mergedChats, ...remainingExisting].sort((a, b) => 
              new Date(b.last_message_date).getTime() - new Date(a.last_message_date).getTime()
            )
          }
          
          // If no existing chats, just set the new ones
          return allChats
        })
      } else {
        console.log(`🔄 Loading more: appending ${allChats.length} chats to existing list`)
        setChats(prev => [...prev, ...allChats])
      }
      
    } catch (error) {
      console.error('Failed to load more chats:', error)
    } finally {
      setLoadingMoreChats(false)
    }
  }

  // Helper function to map message types from API to frontend
  const mapMessageType = (apiType: string): WhatsAppMessage['type'] => {
    switch (apiType?.toLowerCase()) {
      case 'image': return 'image'
      case 'video': return 'video'
      case 'audio': return 'audio'
      case 'document': return 'document'
      case 'location': return 'location'
      case 'contact': return 'contact'
      default: return 'text'
    }
  }

  // Sync WhatsApp data with Unipile API using comprehensive sync
  const handleSync = async () => {
    console.log('🔄 Sync button clicked!')
    console.log('🔄 Current syncing state:', syncing)
    
    if (syncing) {
      console.log('❌ Already syncing, returning early')
      return
    }
    
    console.log('🔄 Setting syncing to true')
    setSyncing(true)
    try {
      console.log('🔄 Making POST request to /api/v1/communications/whatsapp/sync/')
      // Call the dedicated comprehensive sync endpoint
      const syncResponse = await api.post('/api/v1/communications/whatsapp/sync/')
      console.log('✅ Sync response received:', syncResponse.data)
      
      if (syncResponse.data?.success) {
        const syncResults = syncResponse.data.sync_results || []
        const totalConversations = syncResults.reduce((sum: number, result: any) => sum + (result.conversations_synced || 0), 0)
        const totalMessages = syncResults.reduce((sum: number, result: any) => sum + (result.messages_synced || 0), 0)
        
        toast({
          title: "Comprehensive sync completed",
          description: `Synced ${totalConversations} conversations and ${totalMessages} messages with full attendee data.`,
        })
      } else {
        throw new Error(syncResponse.data?.error || 'Sync failed')
      }
      
      // After successful sync, reload conversations with fresh data
      setChatCursor(null)
      setHasMoreChats(true)
      
      // Load fresh conversations
      const accountsToUse = accountConnections
      if (accountsToUse.length > 0) {
        const accountToLoad = accountsToUse[0]
        
        const chatsResponse = await api.get('/api/v1/communications/whatsapp/chats/', {
          params: { 
            account_id: accountToLoad.id,
            limit: 15,
            force_sync: 'false' // Use fresh synced data from database
          }
        })
        
        const accountChats = chatsResponse.data?.chats || []
        const transformedChats: WhatsAppChat[] = []
        
        // Transform API response to WhatsApp chat format
        for (const chatData of accountChats) {
          const transformedChat: WhatsAppChat = {
            id: chatData.id,
            provider_chat_id: chatData.provider_chat_id || chatData.chat_id,
            name: chatData.name || chatData.title,
            picture_url: chatData.picture_url,
            is_group: chatData.is_group || false,
            is_muted: chatData.is_muted || false,
            is_pinned: chatData.is_pinned || false,
            is_archived: chatData.is_archived || false,
            unread_count: chatData.unread_count || 0,
            last_message_date: chatData.latest_message?.date || chatData.latest_message?.created_at || chatData.last_message_date || chatData.updated_at,
            account_id: accountToLoad.id,
            attendees: (chatData.attendees || []).map((att: any) => ({
              id: att.id,
              name: att.name,
              phone: att.phone,
              picture_url: att.picture_url,
              provider_id: att.provider_id,
              is_admin: att.is_admin || false,
              is_business_account: att.is_business_account || false
            })),
            latest_message: chatData.latest_message ? {
              id: chatData.latest_message.id,
              text: chatData.latest_message.text || chatData.latest_message.content,
              type: mapMessageType(chatData.latest_message.type),
              direction: chatData.latest_message.direction,
              chat_id: chatData.id,
              date: chatData.latest_message.date || chatData.latest_message.created_at,
              status: chatData.latest_message.status || 'sent',
              attendee_id: chatData.latest_message.attendee_id,
              attachments: chatData.latest_message.attachments || [],
              account_id: accountToLoad.id
            } : undefined,
            member_count: chatData.member_count
          }
          
          transformedChats.push(transformedChat)
        }
        
        // Sort and update chats
        transformedChats.sort((a, b) => new Date(b.last_message_date).getTime() - new Date(a.last_message_date).getTime())
        setChats(transformedChats)
        setChatCursor(chatsResponse.data?.cursor)
        setHasMoreChats(chatsResponse.data?.has_more || false)
      }
      
      toast({
        title: "Sync completed",
        description: "WhatsApp data has been refreshed from the server.",
      })
    } catch (error: any) {
      console.error('❌ Failed to sync WhatsApp data:', error)
      console.error('❌ Error details:', {
        message: error.message,
        response: error.response?.data,
        status: error.response?.status
      })
      
      toast({
        title: "Sync failed",
        description: error.response?.data?.error || error.message || "Failed to synchronize WhatsApp data.",
        variant: "destructive",
      })
    } finally {
      console.log('🔄 Setting syncing to false')
      setSyncing(false)
    }
  }

  const filteredChats = chats.filter(chat => {
    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      if (!chat.name?.toLowerCase().includes(query) &&
          !chat.attendees.some(att => att.name?.toLowerCase().includes(query) || att.phone?.includes(query)) &&
          !chat.latest_message?.text?.toLowerCase().includes(query)) {
        return false
      }
    }

    // Apply status filter
    switch (filterStatus) {
      case 'unread':
        return chat.unread_count > 0
      case 'groups':
        return chat.is_group
      case 'archived':
        return chat.is_archived
      default:
        return !chat.is_archived  // Hide archived by default
    }
  }).sort((a, b) => {
    // Sort by most recent message first
    const aTime = new Date(a.latest_message?.date || a.last_message_date).getTime()
    const bTime = new Date(b.latest_message?.date || b.last_message_date).getTime()
    
    // Debug timestamp issues only when needed
    if (isNaN(aTime) || isNaN(bTime)) {
      console.warn('🕐 Invalid timestamp detected:', {
        chatA: { name: a.name, timestamp: a.latest_message?.date || a.last_message_date, parsed: aTime },
        chatB: { name: b.name, timestamp: b.latest_message?.date || b.last_message_date, parsed: bTime }
      })
    }
    
    return bTime - aTime // Most recent first
  })

  const handleChatSelect = async (chat: WhatsAppChat) => {
    console.log(`📱 Selected chat "${chat.name}" - comparing timestamps:`, {
      chatListTimestamp: {
        latest_message_date: chat.latest_message?.date,
        last_message_date: chat.last_message_date,
        displayed: formatSafeDate(chat.latest_message?.date || chat.last_message_date)
      },
      latest_message_text: chat.latest_message?.text?.substring(0, 100)
    })
    
    setSelectedChat(chat)
    setLoadingMessages(true)
    
    // Reset message pagination state
    setMessageCursor(null)
    setHasMoreMessages(true)
    
    try {
      // Load initial 20 messages for this chat using local-first endpoint
      console.log('🔍 Loading messages for chat:', chat.id)
      const messagesResponse = await api.get(`/api/v1/communications/whatsapp/chats/${chat.id}/messages/`, {
        params: { 
          limit: 20,
          force_sync: 'false' // Use cached data for instant loading
        }
      })
      console.log('📨 Messages API response:', messagesResponse.data)
      const chatMessages = messagesResponse.data?.messages || []
      setMessageCursor(messagesResponse.data?.cursor)
      setHasMoreMessages(messagesResponse.data?.has_more || false)
      console.log('📨 Extracted chat messages:', chatMessages)
      
      // Transform API messages to WhatsApp message format
      const transformedMessages: WhatsAppMessage[] = chatMessages.map((msgData: any) => {
        // Debug API attachment data structure
        if (msgData.metadata?.attachments || msgData.attachments) {
          console.log('🔍 API ATTACHMENT DEBUG for message', msgData.id, ':', {
            'msgData.attachments': msgData.attachments,
            'msgData.metadata?.attachments': msgData.metadata?.attachments,
            'msgData.metadata': msgData.metadata,
            finalAttachments: (msgData.attachments || msgData.metadata?.attachments) || []
          })
        }
        
        return {
        id: msgData.id,
        text: msgData.text || msgData.content,
        html: msgData.html,
        type: mapMessageType(msgData.type),
        direction: msgData.direction,
        chat_id: chat.id,
        date: msgData.date || msgData.created_at,
        status: msgData.status || 'sent',
        attendee_id: msgData.attendee_id || msgData.from_id,
        attachments: ((msgData.attachments || msgData.metadata?.attachments) || []).map((att: any) => ({
          id: att.id,
          type: att.type,
          filename: att.filename,
          url: att.url,
          thumbnail_url: att.thumbnail_url,
          size: att.size,
          mime_type: att.mime_type
        })),
          location: msgData.location,
          contact: msgData.contact,
          quoted_message_id: msgData.quoted_message_id,
          account_id: chat.account_id
        }
      })
      
      // Sort messages by date (newest first)
      transformedMessages.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
      
      // Debug: Compare chat list timestamp vs actual latest message
      const actualLatestMessage = transformedMessages[0] // First message is newest
      console.log(`📊 Chat "${chat.name}" timestamp comparison:`, {
        chatListShows: {
          latest_message_date: chat.latest_message?.date,
          last_message_date: chat.last_message_date,
          formatted: formatSafeDate(chat.latest_message?.date || chat.last_message_date)
        },
        actualLatestMessage: actualLatestMessage ? {
          date: actualLatestMessage.date,
          text: actualLatestMessage.text?.substring(0, 100),
          formatted: formatSafeDate(actualLatestMessage.date)
        } : 'NO_MESSAGES',
        timeDifference: actualLatestMessage ? 
          Math.abs(new Date(actualLatestMessage.date).getTime() - new Date(chat.latest_message?.date || chat.last_message_date).getTime()) / 1000 / 60 / 60 + ' hours'
          : 'N/A'
      })
      
      console.log('✅ Setting messages state with:', transformedMessages.length, 'messages')
      setMessages(transformedMessages)
      
      // Mark as read if needed
      if (chat.unread_count > 0) {
        try {
          await api.patch(`/api/v1/communications/whatsapp/chats/${chat.id}/`, {
            unread_count: 0,
            account_id: chat.account_id
          })
          
          // Update local state immediately for better UX
          setChats(prev => prev.map(c =>
            c.id === chat.id ? { ...c, unread_count: 0 } : c
          ))
          
          // Also update the current chat's unread count if it's the selected one
          if (selectedChat?.id === chat.id) {
            setSelectedChat(prev => prev ? { ...prev, unread_count: 0 } : prev)
          }
        } catch (error) {
          console.error('Failed to mark chat as read:', error)
        }
      }
      
    } catch (error: any) {
      console.error('Failed to load messages:', error)
      
      // Show specific error based on response
      const errorMessage = error.response?.data?.error || error.message || 'Could not load messages'
      const errorType = error.response?.data?.error_type
      const isConnectionError = errorType === 'connection_error'
      
      toast({
        title: isConnectionError ? "Connection Error" : "Failed to load messages",
        description: errorMessage,
        variant: "destructive",
      })
      setMessages([])
    } finally {
      setLoadingMessages(false)
    }
  }

  const loadMoreMessages = async () => {
    if (!selectedChat || loadingMoreMessages || !hasMoreMessages || !messageCursor) return
    
    setLoadingMoreMessages(true)
    
    try {
      console.log('🔍 Loading more messages for chat:', selectedChat.id, 'cursor:', messageCursor)
      const messagesResponse = await api.get(`/api/v1/communications/whatsapp/chats/${selectedChat.id}/messages/`, {
        params: { 
          limit: 20,
          cursor: messageCursor,
          force_sync: 'false' // Use cached data for pagination
        }
      })
      
      const chatMessages = messagesResponse.data?.messages || []
      setMessageCursor(messagesResponse.data?.cursor)
      setHasMoreMessages(messagesResponse.data?.has_more || false)
      
      // Transform and add to existing messages
      const transformedMessages: WhatsAppMessage[] = chatMessages.map((msgData: any) => ({
        id: msgData.id,
        text: msgData.text || msgData.content,
        html: msgData.html,
        type: mapMessageType(msgData.type),
        direction: msgData.direction,
        chat_id: selectedChat.id,
        date: msgData.date || msgData.created_at,
        status: msgData.status || 'sent',
        attendee_id: msgData.attendee_id || msgData.from_id,
        attachments: ((msgData.attachments || msgData.metadata?.attachments) || []).map((att: any) => ({
          id: att.id,
          type: att.type,
          filename: att.filename,
          url: att.url,
          thumbnail_url: att.thumbnail_url,
          size: att.size,
          mime_type: att.mime_type
        })),
        location: msgData.location,
        contact: msgData.contact,
        quoted_message_id: msgData.quoted_message_id,
        account_id: selectedChat.account_id
      }))
      
      // Sort newest first and append to existing messages
      transformedMessages.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
      
      setMessages(prev => [...prev, ...transformedMessages])
      
    } catch (error) {
      console.error('Failed to load more messages:', error)
    } finally {
      setLoadingMoreMessages(false)
    }
  }

  const handleSendMessage = async () => {
    if (!selectedChat || (!replyText.trim() && attachmentPreviews.length === 0) || composing) return

    const messageText = replyText.trim()
    const hasAttachments = attachmentPreviews.length > 0
    setComposing(true)
    setReplyText('') // Clear input immediately for better UX
    
    try {
      console.log('🚀 Attempting to send message to chat:', selectedChat.id)
      console.log('🚀 Has attachments:', hasAttachments, 'files:', attachmentPreviews.length)
      
      // Send message using real Unipile API
      let response
      
      if (hasAttachments) {
        // First upload attachments, then send message with attachment references
        const uploadedAttachments = []
        
        console.log(`🗂️ Uploading ${attachmentPreviews.length} attachments...`)
        console.log(`🗂️ Selected chat account_id:`, selectedChat.account_id)
        console.log(`🗂️ Account connections:`, accountConnections)
        
        // Find the correct account connection ID
        const accountConnection = accountConnections.find(conn => 
          conn.unipile_account_id === selectedChat.account_id || conn.id === selectedChat.account_id
        )
        
        if (!accountConnection) {
          throw new Error(`Could not find account connection for account_id: ${selectedChat.account_id}`)
        }
        
        console.log(`🗂️ Using account connection full object:`, accountConnection)
        console.log(`🗂️ Using account connection database ID:`, accountConnection.connection_id)
        console.log(`🗂️ Account connection database ID type:`, typeof accountConnection.connection_id)
        
        for (let i = 0; i < attachmentPreviews.length; i++) {
          const preview = attachmentPreviews[i]
          console.log(`🗂️ Uploading file ${i + 1}/${attachmentPreviews.length}: ${preview.file.name}`)
          
          const formData = new FormData()
          formData.append('file', preview.file)
          formData.append('account_id', accountConnection.connection_id) // Use database connection ID
          formData.append('conversation_id', selectedChat.id)
          
          // Debug what's in the FormData
          console.log(`🗂️ FormData entries:`)
          for (let pair of formData.entries()) {
            console.log(`  ${pair[0]}: ${pair[1]} (type: ${typeof pair[1]})`)
          }
          
          try {
            const uploadResponse = await api.post(
              `/api/v1/communications/attachments/upload/`,
              formData,
              {
                headers: {
                  'Content-Type': 'multipart/form-data'
                }
              }
            )
            
            uploadedAttachments.push(uploadResponse.data.attachment)
            console.log(`✅ Successfully uploaded: ${preview.file.name}`)
          } catch (uploadError) {
            console.error(`❌ Failed to upload ${preview.file.name}:`, uploadError)
            console.error('❌ Upload error details:', uploadError.response?.data)
            console.error('❌ Upload error status:', uploadError.response?.status)
            throw new Error(`Failed to upload ${preview.file.name}: ${uploadError.response?.data?.error || uploadError.response?.data?.details || uploadError.message}`)
          }
        }
        
        console.log(`✅ All attachments uploaded successfully: ${uploadedAttachments.length} files`)
        
        // Send message with attachment references using general endpoint
        console.log(`📤 Sending message with ${uploadedAttachments.length} attachments...`)
        console.log(`📤 Message data:`, {
          content: messageText.trim() || '', // Allow empty content if attachments exist
          account_id: accountConnection.connection_id,
          conversation_id: selectedChat.id,
          attachments: uploadedAttachments
        })
        
        try {
          response = await api.post(`/api/v1/communications/inbox/send-message-with-attachments/`, {
            content: messageText.trim() || '', // Allow empty content if attachments exist
            account_id: accountConnection.connection_id, // Use database connection ID
            conversation_id: selectedChat.id,
            attachments: uploadedAttachments
          })
          
          console.log(`✅ Message with attachments sent successfully!`)
        } catch (sendError) {
          console.error(`❌ Failed to send message with attachments:`, sendError)
          console.error(`❌ Send error details:`, sendError.response?.data)
          console.error(`❌ Send error status:`, sendError.response?.status)
          throw new Error(`Failed to send message with attachments: ${sendError.response?.data?.error || sendError.response?.data?.details || sendError.message}`)
        }
      } else {
        // Regular JSON for text-only messages using WhatsApp endpoint
        response = await api.post(`/api/v1/communications/whatsapp/chats/${selectedChat.id}/send/`, {
          text: messageText,
          type: 'text'
        })
      }
      
      const sentMessage = response.data?.message
      
      console.log('🔍 SEND MESSAGE ID DEBUG:', {
        apiResponseId: sentMessage?.id,
        apiResponseType: typeof sentMessage?.id,
        apiResponseText: sentMessage?.text || sentMessage?.content,
        fullSentMessage: sentMessage
      })
      
      if (sentMessage) {
        // Create properly formatted message from API response
        const newMessage: WhatsAppMessage = {
          id: sentMessage.id,
          text: sentMessage.text || messageText,
          type: 'text',
          direction: 'out',
          chat_id: selectedChat.id,
          date: sentMessage.date || new Date().toISOString(),
          status: sentMessage.status || 'sent',
          account_id: selectedChat.account_id,
          // Add attachment data if present
          attachments: hasAttachments ? (sentMessage.attachments || []).map((att: any) => ({
            id: att.id,
            type: att.type,
            filename: att.filename,
            url: att.url,
            thumbnail_url: att.thumbnail_url,
            size: att.size,
            mime_type: att.mime_type
          })) : []
        }

        // Only add immediate message for text-only messages
        // Attachment messages will come through webhook with proper UniPile data
        if (!hasAttachments) {
          // Add to local messages (newest first) - with duplicate check
          setMessages(prev => {
            const exists = prev.some(msg => msg.id === newMessage.id)
            console.log('🚀 SEND MESSAGE DUPLICATE CHECK:', {
              messageId: newMessage.id,
              exists: exists,
              action: exists ? 'SKIP_DUPLICATE' : 'ADD_MESSAGE'
            })
            
            if (exists) {
              console.log('⚠️  Sent message already exists, skipping duplicate')
              return prev
            }
            
            return [newMessage, ...prev]
          })
        } else {
          console.log('📎 Attachment message sent - waiting for webhook confirmation instead of immediate UI update')
        }

        // Only update chat lists for text-only messages
        // Attachment messages will update via webhook
        if (!hasAttachments) {
          // Update chat's latest message
          setChats(prev => prev.map(chat =>
            chat.id === selectedChat.id
              ? { 
                  ...chat, 
                  latest_message: newMessage,
                  last_message_date: newMessage.date
                }
              : chat
          ))

          // Update selected chat
          setSelectedChat(prev => prev ? {
            ...prev,
            latest_message: newMessage,
            last_message_date: newMessage.date
          } : null)
        }
        
        // Clear attachments after successful send
        clearAttachments()
        
        toast({
          title: "Message sent",
          description: hasAttachments ? 
            `Your WhatsApp message with ${attachmentPreviews.length} attachment(s) has been sent successfully.` :
            "Your WhatsApp message has been sent successfully.",
        })
      }
      
    } catch (error: any) {
      console.error('Failed to send message:', error)
      
      // Restore the text if sending failed
      setReplyText(messageText)
      
      // Show specific error message based on response
      const errorMessage = error.response?.data?.error || error.message || "An error occurred while sending your message."
      const errorType = error.response?.data?.error_type
      const isConnectionError = errorType === 'connection_error'
      
      toast({
        title: isConnectionError ? "Connection Error" : "Failed to send message",
        description: errorMessage,
        variant: "destructive",
      })
    } finally {
      setComposing(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-500"></div>
        <p className="ml-4 text-gray-600">Loading WhatsApp conversations...</p>
      </div>
    )
  }

  // Show empty state if no WhatsApp accounts are connected
  if (accountConnections.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center text-gray-500 max-w-md">
          <MessageSquare className="w-16 h-16 mx-auto mb-4 text-gray-300" />
          <h3 className="text-lg font-medium mb-2">No WhatsApp Accounts Connected</h3>
          <p className="mb-4">
            Connect your WhatsApp Business account via Unipile to start managing conversations directly from your CRM.
          </p>
          <Button 
            onClick={() => window.location.href = '/communications/connections'} 
            className="bg-green-600 hover:bg-green-700 text-white"
          >
            <MessageSquare className="w-4 h-4 mr-2" />
            Connect WhatsApp Account
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className={`h-full flex flex-col ${className}`}>
      {/* Filters */}
      <div className="flex-shrink-0 p-4 border-b bg-white dark:bg-gray-900">
        <div className="flex items-center space-x-4">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <Input
                placeholder="Search WhatsApp conversations..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>
          
          <Select value={filterStatus} onValueChange={(value: any) => setFilterStatus(value)}>
            <SelectTrigger className="w-32">
              <SelectValue placeholder="Filter" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="unread">Unread</SelectItem>
              <SelectItem value="groups">Groups</SelectItem>
              <SelectItem value="archived">Archived</SelectItem>
            </SelectContent>
          </Select>

          <div className="flex items-center gap-2">
            {/* WebSocket Status Indicator */}
            <div className="flex items-center space-x-2 text-sm">
              <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
              <span className="text-gray-600 dark:text-gray-400 text-xs">
                {wsConnected ? 'Real-time' : 'Offline'}
              </span>
            </div>
            
            <Button
              variant="outline"
              size="sm"
              onClick={handleSync}
              disabled={syncing}
              className="flex items-center gap-2"
            >
              <RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
              {syncing ? 'Syncing...' : 'Sync'}
            </Button>
            
            {accountConnections.map(conn => (
              <Badge 
                key={conn.id} 
                variant="outline" 
                className={`${
                  conn.status === 'active' 
                    ? 'bg-green-50 text-green-700' 
                    : 'bg-red-50 text-red-700'
                }`}
              >
                <MessageSquare className="w-3 h-3 mr-1" />
                {conn.phone || 'Connected'} 
                {conn.business_account && ' (Business)'}
                {conn.status !== 'active' && (
                  <span className="text-xs ml-1">({conn.auth_status || 'Error'})</span>
                )}
              </Badge>
            ))}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 grid grid-cols-12 gap-0 min-h-0">
        {/* Conversation List */}
        <div className="col-span-4 border-r bg-white dark:bg-gray-900 flex flex-col min-h-0">
          <div 
            className="flex-1 overflow-y-auto"
            onScroll={(e) => {
              const target = e.target as HTMLDivElement
              const { scrollTop, scrollHeight, clientHeight } = target
              const distanceFromBottom = scrollHeight - scrollTop - clientHeight
              
              // Debug scroll position (throttle to avoid spam)
              if (Math.random() < 0.1) { // Only log 10% of scroll events
                console.log(`📜 Scroll: ${distanceFromBottom}px from bottom, hasMore: ${hasMoreChats}, loading: ${loadingMoreChats}`)
              }
              
              // Check if user scrolled near bottom (within 100px)
              if (distanceFromBottom < 100 && hasMoreChats && !loadingMoreChats) {
                console.log('🔄 Triggering loadMoreChats from scroll')
                loadMoreChats()
              }
            }}
          >
            {filteredChats.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <MessageSquare className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                <p>No WhatsApp chats found</p>
              </div>
            ) : (
              <div className="space-y-0">
                {filteredChats.map((chat) => (
                  <div
                    key={chat.id}
                    className={`p-4 cursor-pointer border-b hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors ${
                      selectedChat?.id === chat.id ? 'bg-green-50 dark:bg-green-900/20 border-l-4 border-l-green-500' : ''
                    }`}
                    onClick={() => handleChatSelect(chat)}
                  >
                    <div className="flex items-start space-x-3">
                      <div className="relative">
                        <EnhancedAvatar chat={chat} />
                        {/* Pin indicator */}
                        {chat.is_pinned && (
                          <div className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-green-500 border border-white" />
                        )}
                      </div>
                      
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-1">
                          <div className="flex items-center gap-1">
                            <h3 className={`text-sm font-medium truncate ${
                              chat.unread_count > 0 ? 'font-bold' : ''
                            }`}>
                              {chat.name || (chat.attendees[0]?.name) || 'Unknown'}
                            </h3>
                            {chat.is_group && <span className="text-xs text-gray-400">(Group)</span>}
                            {chat.is_muted && <span className="text-xs text-gray-400">🔇</span>}
                          </div>
                          <div className="flex items-center gap-1 flex-shrink-0 ml-2">
                            <span 
                              className="text-xs text-gray-500" 
                              title={`Chat: ${chat.name}
Latest msg date: ${chat.latest_message?.date}
Last msg date: ${chat.last_message_date}
Using: ${chat.latest_message?.date || chat.last_message_date}
Latest msg text: ${chat.latest_message?.text?.substring(0, 50)}`}
                              onClick={() => {
                                console.log(`🔍 Clicked timestamp for ${chat.name}:`, {
                                  chat,
                                  latest_message: chat.latest_message,
                                  timestamp_used: chat.latest_message?.date || chat.last_message_date,
                                  formatted: formatSafeDate(chat.latest_message?.date || chat.last_message_date)
                                })
                              }}
                            >
                              {formatSafeDate(chat.latest_message?.date || chat.last_message_date)}
                            </span>
                            {chat.unread_count > 0 && (
                              <Badge variant="destructive" className="text-xs ml-1">
                                {chat.unread_count}
                              </Badge>
                            )}
                          </div>
                        </div>
                        
                        {/* Last message preview */}
                        <div className="flex items-center justify-between">
                          <p className={`text-xs text-gray-600 truncate flex-1 ${
                            chat.unread_count > 0 ? 'font-medium' : ''
                          }`}>
                            {chat.latest_message ? (
                              <>
                                {chat.latest_message.direction === 'out' && (
                                  <span className="text-blue-600 mr-1">You: </span>
                                )}
                                {chat.latest_message.text || `${chat.latest_message.type} message`}
                              </>
                            ) : 'No messages'}
                          </p>
                          
                          <div className="flex items-center gap-1 ml-2">
                            {chat.latest_message?.direction === 'out' && (
                              <div className={`flex items-center justify-center w-5 h-5 rounded-full text-xs ${
                                chat.latest_message.status === 'read' ? 'bg-blue-500 text-white' :
                                chat.latest_message.status === 'delivered' ? 'bg-gray-600 text-white' :
                                chat.latest_message.status === 'sent' ? 'bg-gray-600 text-white' : 
                                chat.latest_message.status === 'pending' ? 'bg-gray-600' : 'bg-red-500 text-white'
                              }`}>
                                {chat.latest_message.status === 'pending' ? (
                                  <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-white"></div>
                                ) : chat.latest_message.status === 'read' ? '✓✓' :
                                 chat.latest_message.status === 'delivered' ? '✓✓' :
                                 chat.latest_message.status === 'sent' ? '✓' : '❌'}
                              </div>
                            )}
                          </div>
                        </div>
                        
                        {/* Chat metadata */}
                        <div className="flex items-center justify-between mt-1">
                          <div className="flex items-center gap-2">
                            {chat.is_group && (
                              <span className="text-xs text-gray-400">
                                {chat.member_count || chat.attendees.length || '2+'} participants
                              </span>
                            )}
                            {chat.is_archived && (
                              <Badge variant="outline" className="text-xs bg-gray-50">
                                Archived
                              </Badge>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
                
                {/* Infinite scroll loading indicator */}
                {loadingMoreChats && (
                  <div className="p-4 text-center">
                    <RefreshCw className="w-4 h-4 animate-spin mx-auto text-gray-400" />
                    <p className="text-sm text-gray-500 mt-2">Loading more conversations...</p>
                  </div>
                )}
                
                {/* End of conversations indicator */}
                {!hasMoreChats && filteredChats.length > 0 && (
                  <div className="p-4 text-center text-gray-400 text-sm">
                    No more conversations to load
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Chat View */}
        <div className="col-span-8 bg-gray-50 dark:bg-gray-900 flex flex-col min-h-0">
          {selectedChat ? (
            <>
              {/* Chat Header */}
              <div className="flex-shrink-0 p-4 bg-white dark:bg-gray-800 border-b">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <EnhancedAvatar chat={selectedChat} />
                    <div>
                      <h2 className="font-semibold">
                        {selectedChat.name || selectedChat.attendees[0]?.name || 'Unknown'}
                      </h2>
                      <p className="text-xs text-gray-500">
                        {selectedChat.is_group 
                          ? `${selectedChat.attendees.length} participants • ${messages.length} messages`
                          : `${messages.length} messages`
                        }
                      </p>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    {/* Refresh Messages Button */}
                    <Button 
                      variant="ghost" 
                      size="sm"
                      onClick={async () => {
                        if (!selectedChat) return
                        setLoadingMessages(true)
                        try {
                          // Force fresh messages from API
                          const messagesResponse = await api.get(`/api/v1/communications/whatsapp/chats/${selectedChat.id}/messages/`, {
                            params: { 
                              limit: 20,
                              force_sync: 'true' // Force API sync for fresh data
                            }
                          })
                          
                          const chatMessages = messagesResponse.data?.messages || []
                          setMessageCursor(messagesResponse.data?.cursor)
                          setHasMoreMessages(messagesResponse.data?.has_more || false)
                          
                          // Transform messages
                          const transformedMessages: WhatsAppMessage[] = chatMessages.map((msgData: any) => ({
                            id: msgData.id,
                            text: msgData.text || msgData.content,
                            html: msgData.html,
                            type: mapMessageType(msgData.type),
                            direction: msgData.direction,
                            chat_id: selectedChat.id,
                            date: msgData.date || msgData.created_at,
                            status: msgData.status || 'sent',
                            attendee_id: msgData.attendee_id || msgData.from_id,
                            attachments: ((msgData.attachments || msgData.metadata?.attachments) || []).map((att: any) => ({
                              id: att.id,
                              type: att.type,
                              filename: att.filename,
                              url: att.url,
                              thumbnail_url: att.thumbnail_url,
                              size: att.size,
                              mime_type: att.mime_type
                            })),
                            location: msgData.location,
                            contact: msgData.contact,
                            quoted_message_id: msgData.quoted_message_id,
                            account_id: selectedChat.account_id
                          }))
                          
                          // Sort and set messages
                          transformedMessages.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
                          setMessages(transformedMessages)
                          
                          toast({
                            title: "Messages refreshed",
                            description: "Latest messages have been loaded from the server.",
                          })
                        } catch (error) {
                          console.error('Failed to refresh messages:', error)
                          toast({
                            title: "Refresh failed",
                            description: "Failed to refresh messages from the server.",
                            variant: "destructive",
                          })
                        } finally {
                          setLoadingMessages(false)
                        }
                      }}
                      title="Refresh messages from server"
                    >
                      <RefreshCw className="w-4 h-4" />
                    </Button>
                    
                    {/* Chat History Sync Button */}
                    <Popover>
                      <PopoverTrigger asChild>
                        <Button 
                          variant="ghost" 
                          size="sm"
                          disabled={syncingChat === selectedChat.id}
                          title="Sync chat history"
                        >
                          {syncingChat === selectedChat.id ? (
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-green-500"></div>
                          ) : (
                            <History className="w-4 h-4" />
                          )}
                        </Button>
                      </PopoverTrigger>
                      <PopoverContent className="w-48 p-2" align="end">
                        <div className="space-y-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="w-full justify-start text-left"
                            onClick={() => handleChatHistorySync(selectedChat, false)}
                            disabled={syncingChat === selectedChat.id}
                          >
                            <History className="w-4 h-4 mr-2" />
                            Sync Recent (7 days)
                          </Button>
                          <div className="h-px bg-gray-200 dark:bg-gray-700 my-1" />
                          <Button
                            variant="ghost"
                            size="sm"
                            className="w-full justify-start text-left"
                            onClick={() => handleChatHistorySync(selectedChat, true)}
                            disabled={syncingChat === selectedChat.id}
                          >
                            <RefreshCw className="w-4 h-4 mr-2" />
                            Full History Sync
                          </Button>
                        </div>
                      </PopoverContent>
                    </Popover>

                    {!selectedChat.is_group && (
                      <>
                        <Button variant="ghost" size="sm">
                          <Phone className="w-4 h-4" />
                        </Button>
                        <Button variant="ghost" size="sm">
                          <Video className="w-4 h-4" />
                        </Button>
                      </>
                    )}
                    <Button variant="ghost" size="sm">
                      <MoreVertical className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </div>

              {/* Messages */}
              <ScrollArea 
                className="flex-1 min-h-0"
                onScrollCapture={(e) => {
                  const target = e.target as HTMLDivElement
                  const { scrollTop, scrollHeight, clientHeight } = target
                  
                  // Check if user scrolled near bottom (within 100px) - for infinite scroll
                  if (scrollHeight - scrollTop - clientHeight < 100 && hasMoreMessages && !loadingMoreMessages) {
                    loadMoreMessages()
                  }
                }}
              >
                <div className="p-4">
                {loadingMessages ? (
                  <div className="flex items-center justify-center h-64">
                    <div className="flex items-center gap-2 text-gray-500">
                      <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-green-500"></div>
                      <p>Loading messages...</p>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {console.log('🎨 Rendering messages:', messages.length, 'items') || ''}
                    {messages.length === 0 && (
                      <div className="flex items-center justify-center h-32 text-gray-500">
                        No messages in this chat yet
                      </div>
                    )}
                    {messages.map((message) => (
                    <div
                      key={message.id}
                      className={`flex ${message.direction === 'out' ? 'justify-end' : 'justify-start'} mb-1`}
                    >
                      <div className={`flex flex-col ${message.direction === 'out' ? 'items-end' : 'items-start'}`}>
                        <div
                          className={`max-w-xs lg:max-w-md rounded-lg px-4 py-2 ${
                            message.direction === 'out'
                              ? 'bg-green-500 text-white'
                              : 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white'
                          }`}
                        >
                        {/* Group chat sender name */}
                        {selectedChat.is_group && message.direction === 'in' && (
                          <p className="text-xs font-medium text-green-600 mb-1">
                            {selectedChat.attendees.find(att => att.id === message.attendee_id)?.name || 'Unknown'}
                          </p>
                        )}
                        
                        {/* Message content */}
                        <div className="text-sm">
                          {message.text ? (
                            <MessageContent
                              content={message.text}
                              isEmail={false}
                            />
                          ) : (
                            <div className="text-gray-500 italic">
                              {message.type} message
                            </div>
                          )}
                        </div>

                        {/* Attachments */}
                        {message.attachments && message.attachments.length > 0 && (
                          <div className="mt-2 space-y-2">
                            {message.attachments.map((attachment, index) => (
                              <div 
                                key={attachment.id || attachment.attachment_id || `attachment-${index}`} 
                                className="bg-black bg-opacity-10 rounded p-2 cursor-pointer hover:bg-opacity-20 transition-all"
                                onClick={() => handleAttachmentClick(message.id, attachment)}
                                title={`Click to ${attachment.type === 'image' ? 'preview' : 'download'} ${attachment.filename || attachment.type}`}
                              >
                                {attachment.type === 'image' ? (
                                  <div className="flex items-center gap-2">
                                    <Image className="w-4 h-4" />
                                    <span className="text-xs">{attachment.filename || 'Image'}</span>
                                    {attachment.size && (
                                      <span className="text-xs text-gray-400">
                                        ({(attachment.size / 1024).toFixed(1)}KB)
                                      </span>
                                    )}
                                    <span className="text-xs text-gray-400 ml-auto">Click to preview</span>
                                  </div>
                                ) : attachment.type === 'video' ? (
                                  <div className="flex items-center gap-2">
                                    <Video className="w-4 h-4" />
                                    <span className="text-xs">{attachment.filename || 'Video'}</span>
                                    {attachment.size && (
                                      <span className="text-xs text-gray-400">
                                        ({(attachment.size / 1024 / 1024).toFixed(1)}MB)
                                      </span>
                                    )}
                                    <span className="text-xs text-gray-400 ml-auto">Click to download</span>
                                  </div>
                                ) : attachment.type === 'audio' ? (
                                  <div className="flex items-center gap-2">
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-2v13M9 19c0 1.105-.895 2-2 2s-2-.895-2-2 .895-2 2-2 2 .895 2 2zm12-2c0 1.105-.895 2-2 2s-2-.895-2-2 .895-2 2-2 2 .895 2 2zM9 10l12-2" />
                                    </svg>
                                    <span className="text-xs">{attachment.filename || 'Audio'}</span>
                                    {attachment.size && (
                                      <span className="text-xs text-gray-400">
                                        ({(attachment.size / 1024).toFixed(1)}KB)
                                      </span>
                                    )}
                                    <span className="text-xs text-gray-400 ml-auto">Click to download</span>
                                  </div>
                                ) : attachment.type === 'location' ? (
                                  <div className="flex items-center gap-2">
                                    <MapPin className="w-4 h-4" />
                                    <span className="text-xs">Shared Location</span>
                                    <span className="text-xs text-gray-400 ml-auto">Click to view in maps</span>
                                  </div>
                                ) : attachment.type === 'contact' ? (
                                  <div className="flex items-center gap-2">
                                    <Contact className="w-4 h-4" />
                                    <span className="text-xs">Contact Card</span>
                                    <span className="text-xs text-gray-400 ml-auto">Click to view</span>
                                  </div>
                                ) : (
                                  <div className="flex items-center gap-2">
                                    <Paperclip className="w-4 h-4" />
                                    <span className="text-xs">{attachment.filename || attachment.type}</span>
                                    {attachment.size && (
                                      <span className="text-xs text-gray-400">
                                        ({(attachment.size / 1024).toFixed(1)}KB)
                                      </span>
                                    )}
                                    <span className="text-xs text-gray-400 ml-auto">Click to download</span>
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Timestamp inside bubble */}
                        <div className="flex items-center justify-end mt-1">
                          <div className={`text-xs ${
                            message.direction === 'out'
                              ? 'text-green-100'
                              : 'text-gray-500 dark:text-gray-400'
                          }`}>
                            {formatSafeTime(message.date)}
                          </div>
                        </div>
                        </div>
                        
                        {/* Status icon outside bubble - bottom left */}
                        {message.direction === 'out' && (
                          <div className="flex items-center gap-1 mt-1">
                            <div className={`flex items-center justify-center w-6 h-6 rounded-full text-sm ${
                              message.status === 'read' ? 'bg-blue-500 text-white' :
                              message.status === 'delivered' ? 'bg-gray-600 text-white' :
                              message.status === 'sent' ? 'bg-gray-600 text-white' : 
                              message.status === 'pending' ? 'bg-gray-600' : 'bg-red-500 text-white'
                            }`}>
                              {message.status === 'pending' ? (
                                <div className="animate-spin rounded-full h-3.5 w-3.5 border-b-2 border-white"></div>
                              ) : message.status === 'read' ? '✓✓' :
                               message.status === 'delivered' ? '✓✓' :
                               message.status === 'sent' ? '✓' : '❌'}
                            </div>
                          </div>
                        )}
                      </div>
                      </div>
                    ))}
                    
                    {/* Infinite scroll loading indicator */}
                    {loadingMoreMessages && (
                      <div className="p-4 text-center">
                        <RefreshCw className="w-4 h-4 animate-spin mx-auto text-gray-400" />
                        <p className="text-sm text-gray-500 mt-2">Loading more messages...</p>
                      </div>
                    )}
                  </div>
                )}
                </div>
              </ScrollArea>

              {/* Message Input */}
              <div className="flex-shrink-0 p-4 bg-white dark:bg-gray-800 border-t">
                {/* Attachment Previews */}
                {attachmentPreviews.length > 0 && (
                  <div className="mb-3 flex flex-wrap gap-2">
                    {attachmentPreviews.map((preview, index) => (
                      <div 
                        key={preview.id || `preview-${index}`}
                        className="relative bg-gray-100 dark:bg-gray-700 rounded-lg p-2 flex items-center gap-2 max-w-xs"
                      >
                        {preview.type === 'image' && preview.preview ? (
                          <img 
                            src={preview.preview} 
                            alt="Preview" 
                            className="w-12 h-12 rounded object-cover"
                          />
                        ) : (
                          <div className="w-12 h-12 bg-gray-200 dark:bg-gray-600 rounded flex items-center justify-center">
                            {preview.type === 'video' ? (
                              <Video className="w-6 h-6" />
                            ) : preview.type === 'audio' ? (
                              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-2v13M9 19c0 1.105-.895 2-2 2s-2-.895-2-2 .895-2 2-2 2 .895 2 2zm12-2c0 1.105-.895 2-2 2s-2-.895-2-2 .895-2 2-2 2 .895 2 2zM9 10l12-2" />
                              </svg>
                            ) : (
                              <Paperclip className="w-6 h-6" />
                            )}
                          </div>
                        )}
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium truncate">
                            {preview.file.name}
                          </p>
                          <p className="text-xs text-gray-500">
                            {(preview.file.size / 1024).toFixed(1)}KB
                          </p>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="w-6 h-6 p-0"
                          onClick={() => removeAttachment(index)}
                        >
                          ×
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
                
                <div className="flex items-end space-x-2">
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    onChange={handleFileSelect}
                    className="hidden"
                    accept="image/*,video/*,audio/*,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx"
                  />
                  <Button 
                    variant="ghost" 
                    size="sm"
                    onClick={() => fileInputRef.current?.click()}
                    title="Attach files"
                  >
                    <Paperclip className="w-4 h-4" />
                  </Button>
                  <Textarea
                    placeholder="Type a message..."
                    value={replyText}
                    onChange={(e) => setReplyText(e.target.value)}
                    className="flex-1 min-h-[40px] max-h-32 resize-none"
                    onKeyPress={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey && !composing && (replyText.trim() || attachmentPreviews.length > 0)) {
                        e.preventDefault()
                        handleSendMessage()
                      }
                    }}
                  />
                  <Button variant="ghost" size="sm">
                    <Smile className="w-4 h-4" />
                  </Button>
                  <Button
                    onClick={handleSendMessage}
                    disabled={(!replyText.trim() && attachmentPreviews.length === 0) || composing}
                    className="bg-green-500 hover:bg-green-600 text-white"
                    size="sm"
                  >
                    <Send className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </>
          ) : (
            <div className="h-full flex items-center justify-center">
              <div className="text-center text-gray-500">
                <MessageSquare className="w-16 h-16 mx-auto mb-4 text-gray-300" />
                <h3 className="text-lg font-medium mb-2">Select a chat to start messaging</h3>
                <p>Choose a conversation from the left to view your WhatsApp messages</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}