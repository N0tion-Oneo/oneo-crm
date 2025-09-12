import React, { useState, useEffect, useCallback, useRef } from 'react'
import { formatDistanceToNow, format, isToday, isYesterday, isSameDay } from 'date-fns'
import { User, Bot, Paperclip, Download, Image, FileText, Mail, MessageSquare, Briefcase, CheckCheck, Check, ArrowDown, Calendar, Loader2, ChevronDown, ChevronUp, Reply, Forward, CheckCircle, CircleDot } from 'lucide-react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'
import '@/styles/email-content.css'

interface Attachment {
  id: string
  filename: string
  size: number
  mime_type: string
  url: string | null
  pending?: boolean
}

interface Sender {
  id: string
  name: string
  display_name: string
  email?: string
  phone?: string
  avatar_url?: string
}

interface Message {
  id: string
  content: string
  subject?: string
  direction: 'inbound' | 'outbound'
  sender: Sender | null
  sender_name?: string  // Direct sender name from backend
  conversation_subject?: string
  channel_type: string
  sent_at: string | null
  received_at: string | null
  status?: string
  contact_email?: string
  contact_phone?: string
  created_at: string
  // Optional fields that might not exist
  attachments?: Attachment[]
  html_content?: string  // HTML version of email content
  read_at?: string
  delivered_at?: string
  metadata?: {
    from?: { name?: string; email?: string } | string
    to?: Array<{ name?: string; email?: string }> | string
    cc?: Array<{ name?: string; email?: string }>
    bcc?: Array<{ name?: string; email?: string }>
    account_owner_name?: string
    sender_name?: string
    contact_name?: string
    [key: string]: any
  }
  recipients?: {
    to?: Array<{ name?: string; email?: string }>
    cc?: Array<{ name?: string; email?: string }>
    bcc?: Array<{ name?: string; email?: string }>
  }
}

interface ConversationThreadProps {
  conversationId: string
  recordId: string
  onReply?: (message: any) => void
  onReplyAll?: (message: any) => void
  onForward?: (message: any) => void
  onConversationUpdate?: (conversationId: string, updates: any) => void
  isEmail?: boolean
}

export function ConversationThread({
  conversationId,
  recordId,
  onReply,
  onReplyAll,
  onForward,
  onConversationUpdate,
  isEmail
}: ConversationThreadProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showScrollButton, setShowScrollButton] = useState(false)
  const [conversationType, setConversationType] = useState<'email' | 'message' | 'calendar'>('message')
  const [expandedEmails, setExpandedEmails] = useState<Set<string>>(new Set())
  const [hasMoreMessages, setHasMoreMessages] = useState(true)
  const [initialLoadComplete, setInitialLoadComplete] = useState(false)
  const messageOffsetRef = useRef(0)
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const hasMarkedAsReadRef = useRef<string | null>(null)
  const loadMoreTriggerRef = useRef<HTMLDivElement>(null)
  const scrollContainerRef = useRef<HTMLDivElement | null>(null)
  const isInitialLoadRef = useRef(true)
  
  // Helper to detect if content is HTML
  const isHtmlContent = (content: string): boolean => {
    if (!content) return false
    // Check for common HTML tags
    const htmlPattern = /<(html|body|div|p|br|table|h[1-6]|span|a|img|strong|em|ul|ol|li)/i
    return htmlPattern.test(content)
  }
  
  // Helper to sanitize and prepare HTML for display
  const prepareHtmlContent = (content: string): string => {
    if (!content) return ''
    
    // If content looks like it might be escaped HTML, unescape it
    if (content.includes('&lt;') || content.includes('&gt;') || content.includes('&quot;')) {
      const textarea = document.createElement('textarea')
      textarea.innerHTML = content
      content = textarea.value
    }
    
    // Remove dangerous scripts and styles for security and to prevent CSS leakage
    let sanitized = content
    sanitized = sanitized.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
    sanitized = sanitized.replace(/<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>/gi, '') // Remove style tags to prevent CSS leakage
    sanitized = sanitized.replace(/\son\w+\s*=\s*"[^"]*"/gi, '')
    sanitized = sanitized.replace(/\son\w+\s*=\s*'[^']*'/gi, '')
    sanitized = sanitized.replace(/javascript:/gi, '')
    
    // Fix hidden images by removing display:none and max-width:0 styles
    sanitized = sanitized.replace(
      /<img([^>]*?)style\s*=\s*["']([^"']*?)["']/gi,
      (match, prefix, styles) => {
        // Remove display:none and max-width:0 from inline styles
        let cleanedStyles = styles
          .replace(/display\s*:\s*none\s*;?/gi, '')
          .replace(/max-width\s*:\s*0(?:px)?\s*;?/gi, '')
          .replace(/max-height\s*:\s*0(?:px)?\s*;?/gi, '')
          .replace(/width\s*:\s*0(?:px)?\s*;?/gi, '')
          .replace(/height\s*:\s*0(?:px)?\s*;?/gi, '')
          .replace(/visibility\s*:\s*hidden\s*;?/gi, '')
          .replace(/opacity\s*:\s*0\s*;?/gi, '')
          .trim()
          
        // If no styles left, remove the style attribute entirely
        if (!cleanedStyles || cleanedStyles === ';') {
          return `<img${prefix}`
        }
        return `<img${prefix}style="${cleanedStyles}"`
      }
    )
    
    // Remove CID images that don't work
    sanitized = sanitized.replace(/<img[^>]*src=["']?cid:[^"'\s>]+["']?[^>]*>/gi, '')
    
    return sanitized
  }
  
  // Helper to get a readable sender name
  const getSenderName = (message: Message): string => {
    // For WhatsApp/LinkedIn, check metadata for enriched names
    if ((message.channel_type === 'whatsapp' || message.channel_type === 'linkedin') && message.metadata) {
      // For outbound, use account owner name if available
      if (message.direction === 'outbound' && message.metadata.account_owner_name) {
        return message.metadata.account_owner_name
      }
      // For inbound, use contact name from metadata
      if (message.direction === 'inbound' && message.metadata.contact_name) {
        return message.metadata.contact_name
      }
    }
    
    // For outbound messages, use the sender_name from backend
    if (message.direction === 'outbound') {
      return message.sender_name || message.sender?.name || 'Unknown Sender'
    }
    
    // Check for actual name
    if (message.sender?.name) {
      return message.sender.name
    }
    
    // Check display name
    if (message.sender?.display_name) {
      // Format phone numbers better
      if (message.sender.display_name.match(/^\+?\d+$/)) {
        return formatPhoneNumber(message.sender.display_name)
      }
      
      // Clean up LinkedIn IDs
      if (message.sender.display_name.startsWith('LinkedIn:')) {
        return 'LinkedIn Contact'
      }
      
      return message.sender.display_name
    }
    
    // Fallback to email without domain
    if (message.sender?.email) {
      return message.sender.email.split('@')[0]
    }
    
    // Final fallback
    return message.channel_type === 'whatsapp' ? 'WhatsApp Contact' : 
           message.channel_type === 'linkedin' ? 'LinkedIn Contact' : 
           'Unknown'
  }
  
  // Helper to make URLs clickable in plain text
  const makeUrlsClickable = (text: string): string => {
    if (!text) return ''
    
    // Regular expression to match URLs
    const urlRegex = /(https?:\/\/[^\s<>"\{\}\\^\[\]`]+)/gi
    
    // Replace URLs with clickable links
    return text.replace(urlRegex, (url) => {
      // Clean up the URL (remove trailing punctuation)
      const cleanUrl = url.replace(/[.,;:!?]+$/, '')
      // Truncate display text if URL is too long
      const displayText = cleanUrl.length > 60 ? cleanUrl.substring(0, 57) + '...' : cleanUrl
      return `<a href="${cleanUrl}" target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 underline break-all">${displayText}</a>`
    })
  }
  
  // Helper to format phone numbers
  const formatPhoneNumber = (phone: string): string => {
    // Remove any non-digit characters
    const cleaned = phone.replace(/\D/g, '')
    
    // Format based on length
    if (cleaned.length === 10) {
      // US format: (xxx) xxx-xxxx
      return `(${cleaned.slice(0, 3)}) ${cleaned.slice(3, 6)}-${cleaned.slice(6)}`
    } else if (cleaned.length === 11 && cleaned[0] === '1') {
      // US with country code: +1 (xxx) xxx-xxxx
      return `+1 (${cleaned.slice(1, 4)}) ${cleaned.slice(4, 7)}-${cleaned.slice(7)}`
    } else if (cleaned.length > 10) {
      // International format: +xx xxx xxx xxxx
      return `+${cleaned.slice(0, 2)} ${cleaned.slice(2, 5)} ${cleaned.slice(5, 8)} ${cleaned.slice(8)}`
    }
    
    return phone // Return original if can't format
  }

  // Helper to get date label for grouping
  const getDateLabel = (date: Date): string => {
    if (isToday(date)) return 'Today'
    if (isYesterday(date)) return 'Yesterday'
    return format(date, 'EEEE, MMMM d, yyyy')
  }

  // Helper to get initials for avatar
  const getInitials = (name: string): string => {
    if (!name || name === 'Unknown') return '?'
    const parts = name.split(' ')
    if (parts.length >= 2) {
      return `${parts[0][0]}${parts[1][0]}`.toUpperCase()
    }
    return name.slice(0, 2).toUpperCase()
  }

  // Scroll to bottom function
  const scrollToBottom = (smooth = true) => {
    messagesEndRef.current?.scrollIntoView({ 
      behavior: smooth ? 'smooth' : 'auto' 
    })
  }

  // Handle scroll to detect if user is at bottom
  const handleScroll = useCallback((e: any) => {
    const { scrollTop, scrollHeight, clientHeight } = e.target
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 100
    setShowScrollButton(!isAtBottom)
  }, [])

  // Fetch messages for the conversation
  const fetchMessages = useCallback(async (append: boolean = false) => {
    if (!conversationId || !recordId) return

    const offset = append ? messageOffsetRef.current : 0
    
    if (append) {
      setIsLoadingMore(true)
    } else {
      setIsLoading(true)
      messageOffsetRef.current = 0 // Reset offset for fresh load
    }
    setError(null)

    try {
      const response = await api.get(
        `/api/v1/communications/records/${recordId}/conversation-messages/`,
        {
          params: {
            conversation_id: conversationId,
            limit: 30,
            offset: offset
          }
        }
      )
      // Handle paginated response
      const data = response.data
      let fetchedMessages = []
      if (data.results) {
        fetchedMessages = data.results
      } else if (Array.isArray(data)) {
        fetchedMessages = data
      } else {
        console.error('Unexpected message response format:', data)
        fetchedMessages = []
      }
      
      // Update pagination state
      let hasMore = false
      if (data.results) {
        // Check if there are more messages to load
        hasMore = Boolean(data.next) || (data.count > offset + fetchedMessages.length)
        setHasMoreMessages(hasMore)
      } else {
        // Legacy response format - guess based on fetched count
        hasMore = fetchedMessages.length === 30
        setHasMoreMessages(hasMore)
      }
      
      // Update offset for next fetch
      messageOffsetRef.current = offset + fetchedMessages.length
      
      // Log message statuses for debugging
      console.log('Fetched messages for conversation:', {
        conversationId,
        messageCount: fetchedMessages.length,
        offset,
        newOffset: messageOffsetRef.current,
        totalCount: data.count,
        hasMore,
        append
      })
      
      if (append) {
        // Always append older messages at the end (since newest are at top)
        setMessages(prev => [...prev, ...fetchedMessages])
      } else {
        setMessages(fetchedMessages)
      }
    } catch (err) {
      console.error('Failed to fetch messages:', err)
      setError('Failed to load messages')
    } finally {
      setIsLoading(false)
      setIsLoadingMore(false)
    }
  }, [conversationId, recordId])

  // Load more messages for infinite scroll
  const loadMoreMessages = useCallback(async () => {
    if (!hasMoreMessages || isLoadingMore) return
    await fetchMessages(true)
  }, [fetchMessages, hasMoreMessages, isLoadingMore])

  // Set up IntersectionObserver for infinite scroll
  useEffect(() => {
    if (!hasMoreMessages || isLoadingMore || isLoading || messages.length === 0) return
    
    // Wait for initial load to complete
    if (!initialLoadComplete) {
      console.log('Waiting for initial load to complete before setting up IntersectionObserver')
      return
    }
    
    // Find the actual scroll container
    const findScrollContainer = () => {
      // Try to use the stored reference first
      if (scrollContainerRef.current) {
        return scrollContainerRef.current
      }
      
      // Try to find by class selector
      const element = document.querySelector('.flex-1.min-h-0.overflow-y-auto')
      if (element) {
        console.log('Found scroll container by selector')
        return element as HTMLDivElement
      }
      
      // Fallback to searching from trigger
      let parent: HTMLElement | null = loadMoreTriggerRef.current
      while (parent) {
        const style = window.getComputedStyle(parent)
        if (style.overflowY === 'auto' || style.overflowY === 'scroll') {
          console.log('Found scroll container:', parent.className)
          return parent as HTMLDivElement
        }
        parent = parent.parentElement
      }
      console.log('No scroll container found, using null for viewport')
      return null
    }
    
    // Set up observer
    const scrollContainer = findScrollContainer()
    if (!scrollContainerRef.current && scrollContainer) {
      scrollContainerRef.current = scrollContainer as HTMLDivElement
    }
    
    console.log('Setting up IntersectionObserver', { 
      hasScrollContainer: !!scrollContainer,
      hasTrigger: !!loadMoreTriggerRef.current,
      hasMoreMessages,
      messageCount: messages.length,
      isInitialLoad: isInitialLoadRef.current
    })
    
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          console.log('IntersectionObserver triggered:', { 
            isIntersecting: entry.isIntersecting,
            intersectionRatio: entry.intersectionRatio,
            hasMoreMessages,
            isLoadingMore,
            isInitialLoad: isInitialLoadRef.current
          })
          
          if (entry.isIntersecting && hasMoreMessages && !isLoadingMore && !isLoading && initialLoadComplete) {
            console.log('Loading more messages...')
            loadMoreMessages()
          }
        })
      },
      {
        root: scrollContainer,
        rootMargin: '100px',
        threshold: 0
      }
    )
    
    const trigger = loadMoreTriggerRef.current
    if (trigger) {
      console.log('Observing trigger element')
      observer.observe(trigger)
    }
    
    return () => {
      if (trigger) {
        observer.unobserve(trigger)
      }
    }
  }, [hasMoreMessages, isLoadingMore, isLoading, messages.length, loadMoreMessages, initialLoadComplete])

  // Mark message as read - Define this before any useEffect that uses it
  const markAsRead = useCallback(async (messageId: string) => {
    try {
      // For WhatsApp and LinkedIn, mark the entire conversation as read
      if (conversationType === 'message') {
        console.log('Marking conversation as read:', { conversationId, recordId, conversationType })
        const response = await api.post(
          `/api/v1/communications/records/${recordId}/mark-conversation-read/`,
          { conversation_id: conversationId }
        )
        
        console.log('Mark as read response:', response.data)
        
        // Update all messages in the conversation to read
        setMessages(prev => prev.map(msg => ({
          ...msg,
          status: 'read',
          read_at: new Date().toISOString()
        })))
        
        // Update unread count from the backend response
        if (onConversationUpdate) {
          const unreadCount = response.data?.unread_count ?? 0
          console.log('Updating conversation unread count to:', unreadCount)
          onConversationUpdate(conversationId, { unread_count: unreadCount })
        }
      } else {
        // For email, mark individual message as read
        const response = await api.post(
          `/api/v1/communications/messages/${messageId}/mark_read/`,
          {}
        )
        
        // Update local state
        setMessages(prev => prev.map(msg => 
          msg.id === messageId 
            ? { 
                ...msg, 
                status: 'read',
                read_at: new Date().toISOString() 
              }
            : msg
        ))
        
        // If the parent has an onUnreadCountChange callback, call it
        if (onConversationUpdate && response.data?.unread_count !== undefined) {
          // Update the conversation's unread count
          onConversationUpdate(conversationId, { unread_count: response.data.unread_count })
        }
      }
    } catch (err: any) {
      console.error('Failed to mark message as read:', err)
      console.error('Error details:', {
        message: err.message,
        response: err.response?.data,
        status: err.response?.status
      })
    }
  }, [conversationId, conversationType, recordId, onConversationUpdate])

  // Fetch messages when conversation changes
  useEffect(() => {
    // Reset pagination when conversation changes
    messageOffsetRef.current = 0
    setHasMoreMessages(true)
    setMessages([]) // Clear messages immediately for better UX
    // Reset the marked as read flag when conversation changes
    hasMarkedAsReadRef.current = null
    // Reset initial load flag for new conversation
    isInitialLoadRef.current = true
    setInitialLoadComplete(false)
    fetchMessages(false) // fresh load
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId, recordId]) // Don't include fetchMessages to avoid infinite loop

  // Set conversation type and initial load complete
  useEffect(() => {
    if (messages.length > 0 && !isLoading) {
      // Determine conversation type based on channel
      const firstMessage = messages[0]
      if (firstMessage.channel_type === 'gmail' || firstMessage.channel_type === 'email') {
        setConversationType('email')
        // Auto-expand the latest email (which is now first)
        setExpandedEmails(new Set([messages[0].id]))
      } else if (firstMessage.channel_type === 'calendar') {
        setConversationType('calendar')
      } else {
        setConversationType('message')
      }
      
      // Mark initial load as complete
      setTimeout(() => {
        isInitialLoadRef.current = false
        setInitialLoadComplete(true)
      }, 200)
    }
  }, [messages.length, isLoading])
  
  // Auto-mark WhatsApp/LinkedIn conversations as read when viewed
  useEffect(() => {
    console.log('Auto-mark effect running:', {
      isLoading,
      messageCount: messages.length,
      conversationType,
      conversationId,
      hasMarkedAsReadRef: hasMarkedAsReadRef.current
    })
    
    // Skip if loading or no messages
    if (isLoading || messages.length === 0) {
      console.log('Skipping auto-mark: loading or no messages')
      return
    }
    
    // Skip if we've already marked this conversation as read
    if (hasMarkedAsReadRef.current === conversationId) {
      console.log('Skipping auto-mark: already marked this conversation')
      return
    }
    
    console.log('Conversation type check:', { conversationType, isMessage: conversationType === 'message' })
    
    if (conversationType === 'message') {
      // Log each message's status
      messages.forEach((msg, index) => {
        console.log(`Message ${index}:`, {
          id: msg.id,
          direction: msg.direction,
          status: msg.status,
          statusType: typeof msg.status,
          isInbound: msg.direction === 'inbound',
          isNotRead: msg.status !== 'read',
          wouldBeUnread: msg.direction === 'inbound' && msg.status !== 'read'
        })
      })
      
      const hasUnread = messages.some(msg => msg.direction === 'inbound' && msg.status !== 'read')
      console.log('Has unread messages?', hasUnread)
      
      if (hasUnread) {
        console.log('Setting timeout to mark as read...')
        // Mark the conversation as read after a short delay to ensure user has seen it
        const timer = setTimeout(() => {
          console.log('Timeout fired - marking WhatsApp/LinkedIn conversation as read:', conversationId)
          hasMarkedAsReadRef.current = conversationId
          markAsRead(messages[0].id) // Pass any message ID, will mark whole conversation
        }, 500)
        return () => {
          console.log('Cleanup: clearing timeout')
          clearTimeout(timer)
        }
      } else {
        console.log('No unread messages found')
      }
    } else {
      console.log('Not a message conversation (is email)')
    }
  }, [conversationType, conversationId, messages, isLoading, markAsRead]) // Depend on messages array itself, not just length

  // Toggle email expansion and mark as read when expanding
  const toggleEmailExpanded = useCallback((messageId: string) => {
    setExpandedEmails(prev => {
      const newSet = new Set(prev)
      if (newSet.has(messageId)) {
        newSet.delete(messageId)
      } else {
        newSet.add(messageId)
        // Mark as read when expanding (opening) the email
        const message = messages.find(m => m.id === messageId)
        // Only mark as read if it's an inbound message that's not already read
        if (message && message.direction === 'inbound' && message.status !== 'read') {
          markAsRead(messageId)
        }
      }
      return newSet
    })
  }, [messages, markAsRead])

  const getAttachmentIcon = (mimeType: string) => {
    if (mimeType.startsWith('image/')) return <Image className="w-4 h-4" />
    if (mimeType.includes('pdf')) return <FileText className="w-4 h-4" />
    return <Paperclip className="w-4 h-4" />
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 space-y-4">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
        <p className="text-sm text-gray-500">Loading messages...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64 text-red-500">
        {error}
      </div>
    )
  }

  if (messages.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        No messages in this conversation
      </div>
    )
  }

  // Get channel-specific styling
  const getChannelStyle = (channelType: string, direction: string) => {
    const isOutbound = direction === 'outbound'
    
    switch (channelType) {
      case 'gmail':
      case 'email':
        return {
          bubble: isOutbound 
            ? 'bg-blue-500 text-white' 
            : 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white border border-gray-200 dark:border-gray-700',
          icon: <Mail className="w-4 h-4" />,
          accent: 'text-blue-600 dark:text-blue-400'
        }
      case 'whatsapp':
        return {
          bubble: isOutbound 
            ? 'bg-green-500 text-white' 
            : 'bg-green-50 dark:bg-green-900/20 text-gray-900 dark:text-white border border-green-200 dark:border-green-800',
          icon: <MessageSquare className="w-4 h-4" />,
          accent: 'text-green-600 dark:text-green-400'
        }
      case 'linkedin':
        return {
          bubble: isOutbound 
            ? 'bg-indigo-500 text-white' 
            : 'bg-indigo-50 dark:bg-indigo-900/20 text-gray-900 dark:text-white border border-indigo-200 dark:border-indigo-800',
          icon: <Briefcase className="w-4 h-4" />,
          accent: 'text-indigo-600 dark:text-indigo-400'
        }
      default:
        return {
          bubble: isOutbound 
            ? 'bg-gray-500 text-white' 
            : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white',
          icon: <MessageSquare className="w-4 h-4" />,
          accent: 'text-gray-600 dark:text-gray-400'
        }
    }
  }

  // Handle attachment download through API client
  const handleAttachmentDownload = async (attachment: Attachment) => {
    if (!attachment.url) return
    
    try {
      // Parse the URL to get the path
      const url = new URL(attachment.url, window.location.origin)
      const path = url.pathname + url.search
      
      // Use the api client to make the request with proper tenant context
      const response = await api.get(path, {
        responseType: 'blob'
      })
      
      // Extract the filename from Content-Disposition header if available
      let filename = attachment.filename
      const contentDisposition = response.headers?.['content-disposition']
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/)
        if (filenameMatch) {
          filename = filenameMatch[1]
        }
      }
      
      // Get the content type from response headers
      const contentType = response.headers?.['content-type'] || attachment.mime_type || 'application/octet-stream'
      
      // Create a download link from the blob with the correct content type
      const blob = new Blob([response.data], { type: contentType })
      const downloadUrl = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = downloadUrl
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(downloadUrl)
    } catch (error: any) {
      console.error('Failed to download attachment:', error)
      
      // Show user-friendly error message
      let errorMessage = 'Failed to download attachment'
      if (error.response?.status === 503) {
        errorMessage = 'Service temporarily unavailable. Please try again in a few moments.'
      } else if (error.response?.status === 404) {
        errorMessage = 'Attachment not found. It may have been deleted or expired.'
      } else if (error.response?.data?.error) {
        errorMessage = error.response.data.error
      }
      
      // You could show a toast notification here if you have a toast system
      alert(errorMessage)
    }
  }

  // Render email thread (Gmail/Outlook style)
  const renderEmailThread = () => {
    return (
      <div className="w-full h-full bg-gray-50 dark:bg-gray-900">
        <div className="space-y-2 p-4">
          {messages.map((message, index) => {
            const isExpanded = expandedEmails.has(message.id)
            const isLatest = index === messages.length - 1
            
            return (
              <div 
                key={message.id} 
                className={cn(
                  "border rounded-lg bg-white dark:bg-gray-800 transition-all duration-200 overflow-hidden",
                  isExpanded ? "shadow-md" : "shadow-sm hover:shadow-md"
                )}
              >
              {/* Collapsible email header */}
              <button
                onClick={() => toggleEmailExpanded(message.id)}
                className="w-full text-left p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-3 flex-1">
                    <Avatar className="h-9 w-9">
                      <AvatarImage src={message.sender?.avatar_url} />
                      <AvatarFallback className="text-xs">
                        {getInitials(getSenderName(message))}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2">
                        <span className="font-medium text-sm text-gray-900 dark:text-white">
                          {getSenderName(message)}
                        </span>
                        {message.sender?.email && !isExpanded && (
                          <span className="text-xs text-gray-500 truncate">
                            {message.sender.email}
                          </span>
                        )}
                      </div>
                      {!isExpanded && (
                        <div className="mt-1">
                          {message.subject && (
                            <p className="text-sm text-gray-700 dark:text-gray-300 font-medium truncate">
                              {message.subject}
                            </p>
                          )}
                          <p className="text-xs text-gray-600 dark:text-gray-400 truncate">
                            {message.content.replace(/<[^>]*>/g, '').substring(0, 100)}...
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center space-x-2 ml-2">
                    <span className="text-xs text-gray-500 whitespace-nowrap">
                      {format(new Date(message.sent_at || message.received_at || message.created_at), 'MMM d, h:mm a')}
                    </span>
                    {isExpanded ? (
                      <ChevronUp className="w-4 h-4 text-gray-400" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-gray-400" />
                    )}
                  </div>
                </div>
              </button>
              
              {/* Expanded email content */}
              {isExpanded && (
                <>
                  <div className="border-t border-gray-200 dark:border-gray-700" />
                  
                  {/* Full email header when expanded */}
                  <div className="px-4 py-3 bg-gray-50 dark:bg-gray-800/50">
                    <div className="space-y-1 text-sm">
                      {/* From field */}
                      <div className="flex items-start">
                        <span className="text-gray-500 w-16">From:</span>
                        <span className="text-gray-900 dark:text-white flex-1">
                          {(() => {
                            const from = message.metadata?.from
                            if (typeof from === 'object' && from) {
                              return from.name ? `${from.name} <${from.email || ''}>` : from.email || getSenderName(message)
                            }
                            // Fallback to standard sender info
                            const senderName = getSenderName(message)
                            if (message.sender?.email) {
                              return `${senderName} <${message.sender.email}>`
                            }
                            return senderName
                          })()}
                        </span>
                      </div>
                      
                      {/* To field */}
                      <div className="flex items-start">
                        <span className="text-gray-500 w-16">To:</span>
                        <span className="text-gray-900 dark:text-white flex-1">
                          {(() => {
                            const to = message.metadata?.to
                            if (Array.isArray(to) && to.length > 0) {
                              return to.map(recipient => 
                                recipient.name ? `${recipient.name} <${recipient.email || ''}>` : recipient.email || ''
                              ).filter(Boolean).join(', ')
                            } else if (typeof to === 'string') {
                              return to
                            }
                            // Fallback to contact_email
                            return message.contact_email || 'Unknown'
                          })()}
                        </span>
                      </div>
                      
                      {/* CC field */}
                      {message.metadata?.cc && message.metadata.cc.length > 0 && (
                        <div className="flex items-start">
                          <span className="text-gray-500 w-16">Cc:</span>
                          <span className="text-gray-900 dark:text-white flex-1">
                            {message.metadata.cc.map(recipient => 
                              recipient.name ? `${recipient.name} <${recipient.email || ''}>` : recipient.email || ''
                            ).filter(Boolean).join(', ')}
                          </span>
                        </div>
                      )}
                      
                      {/* BCC field */}
                      {message.metadata?.bcc && message.metadata.bcc.length > 0 && (
                        <div className="flex items-start">
                          <span className="text-gray-500 w-16">Bcc:</span>
                          <span className="text-gray-900 dark:text-white flex-1">
                            {message.metadata.bcc.map(recipient => 
                              recipient.name ? `${recipient.name} <${recipient.email || ''}>` : recipient.email || ''
                            ).filter(Boolean).join(', ')}
                          </span>
                        </div>
                      )}
                      
                      {/* Subject field */}
                      {message.subject && (
                        <div className="flex items-start">
                          <span className="text-gray-500 w-16">Subject:</span>
                          <span className="text-gray-900 dark:text-white font-medium flex-1">{message.subject}</span>
                        </div>
                      )}
                      
                      {/* Date field */}
                      <div className="flex items-start">
                        <span className="text-gray-500 w-16">Date:</span>
                        <span className="text-gray-700 dark:text-gray-300 flex-1">
                          {format(new Date(message.sent_at || message.received_at || message.created_at), 'EEEE, MMMM d, yyyy \'at\' h:mm a')}
                        </span>
                      </div>
                    </div>
                  </div>
                  
                  {/* Email body with full HTML rendering */}
                  <div className="px-4 py-4">
                    <div className="overflow-auto max-h-[600px] overflow-x-hidden">
                      {/* Use html_content if available, otherwise fall back to content */}
                      {message.html_content || isHtmlContent(message.content) ? (
                        <div 
                          className="email-html-content email-content-isolate"
                          style={{
                            transform: 'scale(0.85)',
                            transformOrigin: 'top left',
                            width: '117.6%', // Compensate for 0.85 scale (1/0.85 = 1.176)
                            contain: 'layout style paint' // CSS containment to prevent leakage
                          }}
                          dangerouslySetInnerHTML={{ 
                            __html: prepareHtmlContent(message.html_content || message.content) 
                          }}
                        />
                      ) : (
                        <div 
                          className="whitespace-pre-wrap text-sm text-gray-800 dark:text-gray-200 break-words"
                          dangerouslySetInnerHTML={{ 
                            __html: makeUrlsClickable(message.content || '') 
                          }}
                        />
                      )}
                    </div>
                  </div>

                  {/* Attachments */}
                  {message.attachments && message.attachments.length > 0 && (
                    <div className="px-4 pb-4">
                      <div className="border-t border-gray-200 dark:border-gray-700 pt-3">
                        <p className="text-xs font-medium text-gray-500 mb-2">
                          {message.attachments.length} Attachment{message.attachments.length > 1 ? 's' : ''}
                        </p>
                        <div className="grid grid-cols-2 gap-2">
                          {message.attachments.map((attachment) => (
                            <div
                              key={attachment.id}
                              className={cn(
                                "flex items-center justify-between p-2 border rounded",
                                attachment.pending 
                                  ? "opacity-60 cursor-not-allowed bg-gray-50 dark:bg-gray-800" 
                                  : "hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer"
                              )}
                              onClick={() => {
                                if (!attachment.pending && attachment.url) {
                                  handleAttachmentDownload(attachment)
                                }
                              }}
                              title={attachment.pending ? "Attachment processing, please wait..." : "Click to download"}
                            >
                              <div className="flex items-center space-x-2 min-w-0">
                                {getAttachmentIcon(attachment.mime_type)}
                                <div className="min-w-0">
                                  <p className="text-xs font-medium truncate">{attachment.filename}</p>
                                  <p className="text-xs text-gray-500">
                                    {formatFileSize(attachment.size)}
                                    {attachment.pending && " • Processing..."}
                                  </p>
                                </div>
                              </div>
                              {attachment.pending ? (
                                <Loader2 className="w-3 h-3 text-gray-400 flex-shrink-0 ml-2 animate-spin" />
                              ) : (
                                <Download className="w-3 h-3 text-gray-400 flex-shrink-0 ml-2" />
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Email actions */}
                  {isEmail && (
                    <div className="px-4 py-2 bg-gray-50 dark:bg-gray-800/50 border-t border-gray-200 dark:border-gray-700">
                      <div className="flex items-center space-x-2">
                        <Button 
                          size="sm" 
                          variant="ghost" 
                          className="text-xs"
                          onClick={() => onReply && onReply(message)}
                        >
                          <Reply className="w-3 h-3 mr-1" />
                          Reply
                        </Button>
                        {message.recipients && ((message.recipients.to?.length ?? 0) > 1 || (message.recipients.cc?.length ?? 0) > 0) && (
                          <Button 
                            size="sm" 
                            variant="ghost" 
                            className="text-xs"
                            onClick={() => onReplyAll && onReplyAll(message)}
                          >
                            <Reply className="w-3 h-3 mr-1" />
                            Reply All
                          </Button>
                        )}
                        <Button 
                          size="sm" 
                          variant="ghost" 
                          className="text-xs"
                          onClick={() => onForward && onForward(message)}
                        >
                          <Forward className="w-3 h-3 mr-1" />
                          Forward
                        </Button>
                        {message.direction === 'inbound' && (
                          <Button 
                            size="sm" 
                            variant="ghost" 
                            className="text-xs ml-auto"
                            onClick={async (e) => {
                              e.stopPropagation()
                              const isRead = message.status === 'read'
                              
                              try {
                                // Update message status using api client
                                const response = await api.post(
                                  `/api/v1/communications/records/${recordId}/messages/${message.id}/mark-${isRead ? 'unread' : 'read'}/`,
                                  {}
                                )
                                
                                if (response.data.success) {
                                  // Update local state
                                  setMessages(prev => prev.map(m => 
                                    m.id === message.id 
                                      ? { ...m, status: isRead ? 'delivered' : 'read' }
                                      : m
                                  ))
                                  
                                  // Notify parent to update conversation
                                  if (onConversationUpdate) {
                                    onConversationUpdate(conversationId, {})
                                  }
                                }
                              } catch (error) {
                                console.error('Error marking message:', error)
                              }
                            }}
                          >
                            {message.status === 'read' ? (
                              <>
                                <CircleDot className="w-3 h-3 mr-1" />
                                Mark as unread
                              </>
                            ) : (
                              <>
                                <CheckCircle className="w-3 h-3 mr-1" />
                                Mark as read
                              </>
                            )}
                          </Button>
                        )}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          )
        })}
        
        {/* Load more trigger at the BOTTOM for older messages - only for email view */}
        {conversationType === 'email' && (hasMoreMessages || isLoadingMore) && (
          <div 
            ref={loadMoreTriggerRef}
            className="flex items-center justify-center py-4 min-h-[60px]"
          >
            {isLoadingMore ? (
              <div className="flex items-center space-x-2 text-gray-500">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-sm">Loading older messages...</span>
              </div>
            ) : (
              <div className="text-sm text-gray-400">
                {/* Invisible element to trigger loading */}
                <span style={{ opacity: 0 }}>Load trigger</span>
              </div>
            )}
          </div>
        )}
        </div>
      </div>
    )
  }

  // Render message thread (WhatsApp/LinkedIn chat style)
  const renderMessageThread = () => {
    // Sort all messages by timestamp (newest first, same as email)
    const sortedMessages = [...messages].sort((a, b) => {
      const aTime = new Date(a.sent_at || a.received_at || a.created_at).getTime()
      const bTime = new Date(b.sent_at || b.received_at || b.created_at).getTime()
      return bTime - aTime // Newest first for consistency
    })

    // Group sorted messages by date
    const messagesByDate: { [key: string]: Message[] } = {}
    sortedMessages.forEach((message) => {
      // Use sent_at for outbound, received_at for inbound, or created_at as fallback
      const timestamp = message.sent_at || message.received_at || message.created_at
      const date = new Date(timestamp)
      const dateKey = format(date, 'yyyy-MM-dd')
      if (!messagesByDate[dateKey]) {
        messagesByDate[dateKey] = []
      }
      messagesByDate[dateKey].push(message)
    })

    // Sort date keys reverse chronologically (newest first)
    const sortedDateKeys = Object.keys(messagesByDate).sort().reverse()

    return (
      <div className="w-full h-full bg-gray-50 dark:bg-gray-900">
        <div className="space-y-6 p-4">
          {sortedDateKeys.map((dateKey) => {
            const dateMessages = messagesByDate[dateKey]
            // Get the first message's timestamp for the date label
            const firstMessage = dateMessages[0]
            const timestamp = firstMessage.sent_at || firstMessage.received_at || firstMessage.created_at
            const date = new Date(timestamp)
            return (
              <div key={dateKey}>
                {/* Date separator */}
                <div className="flex items-center justify-center my-4">
                  <div className="flex items-center space-x-2 px-3 py-1 bg-gray-100 dark:bg-gray-800 rounded-full">
                    <Calendar className="w-3 h-3 text-gray-500" />
                    <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
                      {getDateLabel(date)}
                    </span>
                  </div>
                </div>

                {/* Messages for this date */}
                {dateMessages.map((message, index) => {
                  const channelStyle = getChannelStyle(message.channel_type, message.direction)
                  const showTime = index === 0 || 
                    (dateMessages[index - 1].sent_at && message.sent_at && 
                     new Date(dateMessages[index - 1].sent_at!).getTime() + 60000 < new Date(message.sent_at!).getTime())
                  
                  return (
                    <div
                      key={message.id}
                      className={cn(
                        "flex flex-col mb-2",
                        message.direction === 'outbound' ? "items-end" : "items-start"
                      )}
                    >
                      {/* Show sender name above message */}
                      <div className={cn(
                        "text-xs mb-1 px-2",
                        message.direction === 'outbound' ? "text-blue-600 dark:text-blue-400" : "text-gray-600 dark:text-gray-400"
                      )}>
                        {getSenderName(message)}
                      </div>
                      
                      <div className={cn(
                        "max-w-[70%] rounded-2xl px-4 py-2",
                        channelStyle.bubble
                      )}>
                        {/* Message content with clickable URLs */}
                        <div 
                          className="text-sm whitespace-pre-wrap break-words"
                          dangerouslySetInnerHTML={{ 
                            __html: makeUrlsClickable(message.content || '') 
                          }}
                        />
                        
                        {/* Time and status */}
                        <div className={cn(
                          "flex items-center space-x-1 mt-1",
                          message.direction === 'outbound' ? "justify-end" : "justify-start"
                        )}>
                          <span className="text-xs opacity-60">
                            {format(new Date(message.sent_at || message.received_at || message.created_at), 'h:mm a')}
                          </span>
                          {message.channel_type === 'whatsapp' && message.direction === 'outbound' && (
                            <div className="flex items-center">
                              {message.read_at ? (
                                <CheckCheck className="w-3 h-3 text-blue-500" />
                              ) : message.delivered_at ? (
                                <CheckCheck className="w-3 h-3 opacity-60" />
                              ) : (
                                <Check className="w-3 h-3 opacity-60" />
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )
          })}
          
          {/* Load more trigger at the BOTTOM for older messages */}
          {conversationType === 'message' && (hasMoreMessages || isLoadingMore) && (
            <div 
              ref={loadMoreTriggerRef}
              className="flex items-center justify-center py-4 min-h-[60px]"
            >
              {isLoadingMore ? (
                <div className="flex items-center space-x-2 text-gray-500">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="text-sm">Loading older messages...</span>
                </div>
              ) : (
                <div className="text-sm text-gray-400">
                  {/* Invisible element to trigger loading */}
                  <span style={{ opacity: 0 }}>Load trigger</span>
                </div>
              )}
            </div>
          )}
          
          {/* Scroll to bottom reference */}
          <div ref={messagesEndRef} />
        </div>

        {/* Scroll to bottom button */}
        {showScrollButton && (
          <Button
            size="sm"
            variant="secondary"
            className="absolute bottom-4 right-4 rounded-full shadow-lg"
            onClick={() => scrollToBottom()}
          >
            <ArrowDown className="w-4 h-4" />
          </Button>
        )}
      </div>
    )
  }

  // Render based on conversation type
  return conversationType === 'email' ? renderEmailThread() : renderMessageThread()
}