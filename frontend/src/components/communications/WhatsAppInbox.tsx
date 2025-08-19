'use client'

import React, { useState, useEffect, useRef } from 'react'
import { MessageSquare, Search, Filter, Phone, Video, MoreVertical, Paperclip, Send, Smile, Image, RefreshCw, MapPin, Contact, History } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { useToast } from '@/hooks/use-toast'
import { MessageContent } from '@/components/MessageContent'
import { formatDistanceToNow } from 'date-fns'
import { api } from '@/lib/api'

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
  status: 'sent' | 'delivered' | 'read' | 'failed'
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
  const [attendees, setAttendees] = useState<WhatsAppAttendee[]>([])
  const [messages, setMessages] = useState<WhatsAppMessage[]>([])
  const [loading, setLoading] = useState(true)
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
  const [syncingChat, setSyncingChat] = useState<string | null>(null)
  const { toast } = useToast()

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
        `/api/v1/communications/whatsapp/messages/${messageId}/attachments/${attachment.id}/`,
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

  // Load profile picture for an attendee
  const loadAttendeeProfilePicture = async (attendeeId: string): Promise<string | null> => {
    try {
      const response = await api.get(`/api/v1/communications/whatsapp/attendees/${attendeeId}/picture/`)
      
      if (response.data?.success && response.data?.picture_url) {
        return response.data.picture_url
      }
      
      if (response.data?.success && response.data?.picture_data) {
        // Create blob URL from base64 data
        const base64Data = response.data.picture_data
        const mimeType = 'image/jpeg' // Default to JPEG for WhatsApp profile pics
        const blob = new Blob([Uint8Array.from(atob(base64Data), c => c.charCodeAt(0))], { type: mimeType })
        return URL.createObjectURL(blob)
      }
      
      return null
    } catch (error) {
      console.error(`Failed to load profile picture for attendee ${attendeeId}:`, error)
      return null
    }
  }

  // Global cache for picture URLs to prevent any duplicate requests across all components
  const pictureLoadingCache = useRef<Map<string, Promise<string | null>>>(new Map())
  const pictureUrlCache = useRef<Map<string, string | null>>(new Map())

  // Enhanced avatar component that loads profile pictures on demand
  const EnhancedAvatar = ({ chat, size = 'w-10 h-10', loadOnMount = false }: { chat: WhatsAppChat, size?: string, loadOnMount?: boolean }) => {
    const [profilePictureUrl, setProfilePictureUrl] = useState<string | null>(() => {
      // Initialize with cached URL if available, otherwise use chat.picture_url
      const attendeeToLoad = chat.attendees[0]
      if (attendeeToLoad?.id && pictureUrlCache.current.has(attendeeToLoad.id)) {
        return pictureUrlCache.current.get(attendeeToLoad.id)
      }
      return chat.picture_url || null
    })
    const [loading, setLoading] = useState(false)

    useEffect(() => {
      // Only load automatically if explicitly requested (for selected chat)
      if (!loadOnMount) return

      const loadProfilePicture = async () => {
        // For group chats, try to get the first attendee's picture
        const attendeeToLoad = chat.attendees[0]
        if (!attendeeToLoad?.id) return

        const cacheKey = attendeeToLoad.id

        // Check if we already have a cached URL
        if (pictureUrlCache.current.has(cacheKey)) {
          const cachedUrl = pictureUrlCache.current.get(cacheKey)
          if (cachedUrl !== profilePictureUrl) {
            setProfilePictureUrl(cachedUrl)
          }
          return
        }

        // Skip if we already have a picture
        if (profilePictureUrl) {
          // Cache the current URL
          pictureUrlCache.current.set(cacheKey, profilePictureUrl)
          return
        }

        // Check if we're already loading this picture
        if (pictureLoadingCache.current.has(cacheKey)) {
          // Wait for existing request to complete
          try {
            const cachedResult = await pictureLoadingCache.current.get(cacheKey)!
            if (cachedResult) {
              setProfilePictureUrl(cachedResult)
              pictureUrlCache.current.set(cacheKey, cachedResult)
            }
          } catch (error) {
            console.error('Error waiting for cached picture request:', error)
          }
          return
        }

        console.log(`🖼️ Loading profile picture for attendee: ${cacheKey}`)
        setLoading(true)
        
        // Create and cache the request promise
        const loadPromise = loadAttendeeProfilePicture(attendeeToLoad.id).finally(() => {
          // Remove from cache when done (whether success or failure)
          pictureLoadingCache.current.delete(cacheKey)
          setLoading(false)
        })
        
        pictureLoadingCache.current.set(cacheKey, loadPromise)

        try {
          const pictureUrl = await loadPromise
          if (pictureUrl) {
            setProfilePictureUrl(pictureUrl)
            // Cache the result for future use
            pictureUrlCache.current.set(cacheKey, pictureUrl)
            
            // Update the chat object in state
            setChats(prev => prev.map(c => 
              c.id === chat.id 
                ? { ...c, picture_url: pictureUrl }
                : c
            ))
          } else {
            // Cache null result to prevent future requests
            pictureUrlCache.current.set(cacheKey, null)
          }
        } catch (error) {
          console.error('Error loading profile picture:', error)
          // Cache null result to prevent retrying failed requests
          pictureUrlCache.current.set(cacheKey, null)
        }
      }

      loadProfilePicture()
    }, [chat.id, loadOnMount]) // Removed profilePictureUrl from deps to prevent unnecessary re-runs

    return (
      <Avatar className={size}>
        <AvatarImage src={profilePictureUrl || undefined} />
        <AvatarFallback className="bg-green-100 text-green-700">
          {loading ? (
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-green-500"></div>
          ) : (
            chat.is_group ? 'G' : (chat.name?.charAt(0) || chat.attendees[0]?.name?.charAt(0) || 'W')
          )}
        </AvatarFallback>
      </Avatar>
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
    loadWhatsAppData()
  }, [])

  const loadWhatsAppData = async () => {
    try {
      setLoading(true)
      
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
      setChats([])
      
      // Load initial batch of chats (10 conversations)
      await loadMoreChats(connections, true)
      
    } catch (error) {
      console.error('Failed to load WhatsApp data:', error)
      toast({
        title: "Failed to load WhatsApp data",
        description: "Please check your connection and try again.",
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
      const allAttendees: WhatsAppAttendee[] = []
      let newCursor = chatCursor

      for (const account of accountsToUse) {
        try {
          // Get chats for this account with pagination
          const chatsResponse = await api.get('/api/v1/communications/whatsapp/chats/', {
            params: { 
              account_id: account.id,
              limit: 10, // Load 10 conversations at a time
              ...(chatCursor && { cursor: chatCursor })
            }
          })
          
          const accountChats = chatsResponse.data?.chats || []
          newCursor = chatsResponse.data?.cursor
          const hasMore = chatsResponse.data?.has_more || false
          
          // Update pagination state
          setHasMoreChats(hasMore)
          
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
              last_message_date: chatData.last_message_date || chatData.updated_at,
              account_id: account.id,
              attendees: (chatData.attendees || []).map((att: any) => ({
                id: att.id,
                name: att.name,
                phone: att.phone,
                picture_url: att.picture_url,
                is_admin: att.is_admin || false
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
                account_id: account.id
              } : undefined,
              member_count: chatData.member_count
            }
            
            allChats.push(transformedChat)
          }

          // Load attendees only for initial load to avoid repeated calls
          if (isInitialLoad) {
            const attendeesResponse = await api.get('/api/v1/communications/whatsapp/attendees/', {
              params: { account_id: account.id }
            })
            
            const accountAttendees = attendeesResponse.data?.attendees || []
            
            // Transform attendees
            for (const attendeeData of accountAttendees) {
              const transformedAttendee: WhatsAppAttendee = {
                id: attendeeData.id,
                name: attendeeData.name,
                phone: attendeeData.phone,
                picture_url: attendeeData.picture_url,
                provider_id: attendeeData.provider_id,
                is_business_account: attendeeData.is_business_account || false,
                status: attendeeData.status,
                last_seen: attendeeData.last_seen,
                account_id: account.id
              }
              
              allAttendees.push(transformedAttendee)
            }
          }
          
        } catch (error) {
          console.error(`Failed to load data for WhatsApp account ${account.id}:`, error)
        }
      }

      // Update cursor for next page
      setChatCursor(newCursor)

      // Sort chats by last message date (most recent first)
      allChats.sort((a, b) => new Date(b.last_message_date).getTime() - new Date(a.last_message_date).getTime())
      
      // Append to existing chats or replace for initial load
      if (isInitialLoad) {
        setChats(allChats)
        setAttendees(allAttendees)
      } else {
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

  // Sync WhatsApp data with Unipile API
  const handleSync = async () => {
    if (syncing) return
    
    setSyncing(true)
    try {
      // Trigger sync for all WhatsApp accounts
      await api.post('/api/v1/communications/whatsapp/sync/')
      
      // Reload data after sync
      await loadWhatsAppData()
      
      toast({
        title: "Sync completed",
        description: "WhatsApp data has been synchronized successfully.",
      })
    } catch (error: any) {
      console.error('Failed to sync WhatsApp data:', error)
      toast({
        title: "Sync failed",
        description: error.response?.data?.error || "Failed to synchronize WhatsApp data.",
        variant: "destructive",
      })
    } finally {
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
  })

  const handleChatSelect = async (chat: WhatsAppChat) => {
    setSelectedChat(chat)
    setLoadingMessages(true)
    
    // Reset message pagination state
    setMessageCursor(null)
    setHasMoreMessages(true)
    
    try {
      // Load initial 20 messages for this chat from real Unipile API
      console.log('🔍 Loading messages for chat:', chat.id)
      const messagesResponse = await api.get(`/api/v1/communications/whatsapp/chats/${chat.id}/messages/`, {
        params: { limit: 20 }
      })
      console.log('📨 Messages API response:', messagesResponse.data)
      const chatMessages = messagesResponse.data?.messages || []
      setMessageCursor(messagesResponse.data?.cursor)
      setHasMoreMessages(messagesResponse.data?.has_more || false)
      console.log('📨 Extracted chat messages:', chatMessages)
      
      // Transform API messages to WhatsApp message format
      const transformedMessages: WhatsAppMessage[] = chatMessages.map((msgData: any) => ({
        id: msgData.id,
        text: msgData.text || msgData.content,
        html: msgData.html,
        type: mapMessageType(msgData.type),
        direction: msgData.direction,
        chat_id: chat.id,
        date: msgData.date || msgData.created_at,
        status: msgData.status || 'sent',
        attendee_id: msgData.attendee_id || msgData.from_id,
        attachments: (msgData.attachments || []).map((att: any) => ({
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
      }))
      
      // Sort messages by date (newest first)
      transformedMessages.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
      
      console.log('✅ Setting messages state with:', transformedMessages.length, 'messages')
      setMessages(transformedMessages)
      
      // Mark as read if needed
      if (chat.unread_count > 0) {
        try {
          await api.patch(`/api/v1/communications/whatsapp/chats/${chat.id}/`, {
            read: true
          })
          
          // Update local state
          setChats(prev => prev.map(c =>
            c.id === chat.id ? { ...c, unread_count: 0 } : c
          ))
        } catch (error) {
          console.error('Failed to mark chat as read:', error)
        }
      }
      
    } catch (error) {
      console.error('Failed to load messages:', error)
      toast({
        title: "Failed to load messages",
        description: "Could not load messages for this chat.",
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
          cursor: messageCursor
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
        attachments: (msgData.attachments || []).map((att: any) => ({
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
    if (!selectedChat || !replyText.trim() || composing) return

    const messageText = replyText.trim()
    setComposing(true)
    setReplyText('') // Clear input immediately for better UX
    
    try {
      // Send message using real Unipile API
      const response = await api.post(`/api/v1/communications/whatsapp/chats/${selectedChat.id}/send/`, {
        text: messageText,
        type: 'text'
      })
      
      const sentMessage = response.data?.message
      
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
          account_id: selectedChat.account_id
        }

        // Add to local messages (newest first)
        setMessages(prev => [newMessage, ...prev])

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
        
        toast({
          title: "Message sent",
          description: "Your WhatsApp message has been sent successfully.",
        })
      }
      
    } catch (error: any) {
      console.error('Failed to send message:', error)
      
      // Restore the text if sending failed
      setReplyText(messageText)
      
      // Show specific error message if available
      const errorMessage = error.response?.data?.error || error.message || "An error occurred while sending your message."
      
      toast({
        title: "Failed to send message",
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
          <ScrollArea 
            className="flex-1"
            onScrollCapture={(e) => {
              const target = e.target as HTMLDivElement
              const { scrollTop, scrollHeight, clientHeight } = target
              
              // Check if user scrolled near bottom (within 100px)
              if (scrollHeight - scrollTop - clientHeight < 100 && hasMoreChats && !loadingMoreChats) {
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
                        <EnhancedAvatar chat={chat} loadOnMount={false} />
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
                            <span className="text-xs text-gray-500">
                              {formatSafeDate(chat.last_message_date)}
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
                              <span className={`text-xs ${
                                chat.latest_message.status === 'read' ? 'text-blue-500' :
                                chat.latest_message.status === 'delivered' ? 'text-gray-500' :
                                chat.latest_message.status === 'sent' ? 'text-gray-400' : 'text-red-500'
                              }`}>
                                {chat.latest_message.status === 'read' ? '✓✓' :
                                 chat.latest_message.status === 'delivered' ? '✓✓' :
                                 chat.latest_message.status === 'sent' ? '✓' : '❌'}
                              </span>
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
          </ScrollArea>
        </div>

        {/* Chat View */}
        <div className="col-span-8 bg-gray-50 dark:bg-gray-900 flex flex-col min-h-0">
          {selectedChat ? (
            <>
              {/* Chat Header */}
              <div className="flex-shrink-0 p-4 bg-white dark:bg-gray-800 border-b">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <EnhancedAvatar chat={selectedChat} loadOnMount={true} />
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
                      className={`flex ${message.direction === 'out' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`max-w-xs lg:max-w-md rounded-lg px-4 py-2 ${
                          message.direction === 'out'
                            ? 'bg-green-500 text-white ml-12'
                            : 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white mr-12'
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
                            {message.attachments.map((attachment) => (
                              <div 
                                key={attachment.id} 
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

                        {/* Timestamp and status */}
                        <div className="flex items-center justify-between mt-1">
                          <div
                            className={`text-xs ${
                              message.direction === 'out'
                                ? 'text-green-100'
                                : 'text-gray-500 dark:text-gray-400'
                            }`}
                          >
                            {formatSafeTime(message.date)}
                          </div>
                          {message.direction === 'out' && (
                            <div className={`text-xs ${
                              message.status === 'read' ? 'text-blue-400' :
                              message.status === 'delivered' ? 'text-gray-300' :
                              message.status === 'sent' ? 'text-gray-400' : 'text-red-400'
                            }`}>
                              {message.status === 'read' ? '✓✓' :
                               message.status === 'delivered' ? '✓✓' :
                               message.status === 'sent' ? '✓' : '❌'}
                            </div>
                          )}
                        </div>
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
                <div className="flex items-end space-x-2">
                  <Button variant="ghost" size="sm">
                    <Paperclip className="w-4 h-4" />
                  </Button>
                  <Textarea
                    placeholder="Type a message..."
                    value={replyText}
                    onChange={(e) => setReplyText(e.target.value)}
                    className="flex-1 min-h-[40px] max-h-32 resize-none"
                    onKeyPress={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey && !composing && replyText.trim()) {
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
                    disabled={!replyText.trim() || composing}
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