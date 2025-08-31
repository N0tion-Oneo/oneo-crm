import React, { useState, useEffect, useCallback, useRef } from 'react'
import { formatDistanceToNow, format, isToday, isYesterday, isSameDay } from 'date-fns'
import { User, Bot, Paperclip, Download, Image, FileText, Mail, MessageSquare, Briefcase, CheckCheck, Check, ArrowDown, Calendar, Loader2, ChevronDown, ChevronUp, Reply, Forward } from 'lucide-react'
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
  url: string
}

interface Sender {
  id: string
  name: string
  display_name: string
  email?: string
  phone?: string
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
  sent_at: string
  received_at?: string
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
}

interface ConversationThreadProps {
  conversationId: string
  recordId: string
}

export function ConversationThread({
  conversationId,
  recordId
}: ConversationThreadProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showScrollButton, setShowScrollButton] = useState(false)
  const [conversationType, setConversationType] = useState<'email' | 'message'>('message')
  const [expandedEmails, setExpandedEmails] = useState<Set<string>>(new Set())
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  
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
    
    // Remove dangerous scripts for security
    let sanitized = content
    sanitized = sanitized.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
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
  const fetchMessages = useCallback(async () => {
    if (!conversationId || !recordId) return

    setIsLoading(true)
    setError(null)

    try {
      const response = await api.get(
        `/api/v1/communications/records/${recordId}/conversation-messages/`,
        {
          params: {
            conversation_id: conversationId,
            limit: 30,
            offset: 0
          }
        }
      )
      // Handle paginated response
      const data = response.data
      if (data.results) {
        setMessages(data.results)
      } else if (Array.isArray(data)) {
        setMessages(data)
      } else {
        console.error('Unexpected message response format:', data)
        setMessages([])
      }
    } catch (err) {
      console.error('Failed to fetch messages:', err)
      setError('Failed to load messages')
    } finally {
      setIsLoading(false)
    }
  }, [conversationId, recordId])

  useEffect(() => {
    fetchMessages()
  }, [fetchMessages])

  // Auto-scroll to bottom when messages load
  useEffect(() => {
    if (messages.length > 0 && !isLoading) {
      scrollToBottom(false) // Instant scroll on initial load
      // Determine conversation type based on channel
      const firstMessage = messages[0]
      if (firstMessage.channel_type === 'gmail' || firstMessage.channel_type === 'email') {
        setConversationType('email')
        // Auto-expand the latest email
        setExpandedEmails(new Set([messages[messages.length - 1].id]))
      } else {
        setConversationType('message')
      }
    }
  }, [messages.length, isLoading])

  // Toggle email expansion
  const toggleEmailExpanded = (messageId: string) => {
    setExpandedEmails(prev => {
      const newSet = new Set(prev)
      if (newSet.has(messageId)) {
        newSet.delete(messageId)
      } else {
        newSet.add(messageId)
      }
      return newSet
    })
  }

  // Mark message as read
  const markAsRead = useCallback(async (messageId: string) => {
    try {
      await api.post(
        `/api/v1/communications/messages/${messageId}/mark_read/`,
        {}
      )
      
      // Update local state
      setMessages(prev => prev.map(msg => 
        msg.id === messageId 
          ? { ...msg, read_at: new Date().toISOString() }
          : msg
      ))
    } catch (err) {
      console.error('Failed to mark message as read:', err)
    }
  }, [])

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

  // Render email thread (Gmail/Outlook style)
  const renderEmailThread = () => {
    return (
      <div className="space-y-2 p-4 bg-gray-50 dark:bg-gray-900">
        {messages.map((message, index) => {
          const isExpanded = expandedEmails.has(message.id)
          const isLatest = index === messages.length - 1
          
          return (
            <div 
              key={message.id} 
              className={cn(
                "border rounded-lg bg-white dark:bg-gray-800 transition-all duration-200",
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
                      {format(new Date(message.sent_at), 'MMM d, h:mm a')}
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
                          {format(new Date(message.sent_at), 'EEEE, MMMM d, yyyy \'at\' h:mm a')}
                        </span>
                      </div>
                    </div>
                  </div>
                  
                  {/* Email body with full HTML rendering */}
                  <div className="px-4 py-4 max-h-[600px] overflow-y-auto">
                    {/* Use html_content if available, otherwise fall back to content */}
                    {message.html_content || isHtmlContent(message.content) ? (
                      <div 
                        className="email-html-content email-body-container"
                        dangerouslySetInnerHTML={{ 
                          __html: prepareHtmlContent(message.html_content || message.content) 
                        }}
                      />
                    ) : (
                      <div 
                        className="whitespace-pre-wrap text-sm text-gray-800 dark:text-gray-200"
                        dangerouslySetInnerHTML={{ 
                          __html: makeUrlsClickable(message.content || '') 
                        }}
                      />
                    )}
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
                              className="flex items-center justify-between p-2 border rounded hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer"
                              onClick={() => window.open(attachment.url, '_blank')}
                            >
                              <div className="flex items-center space-x-2 min-w-0">
                                {getAttachmentIcon(attachment.mime_type)}
                                <div className="min-w-0">
                                  <p className="text-xs font-medium truncate">{attachment.filename}</p>
                                  <p className="text-xs text-gray-500">{formatFileSize(attachment.size)}</p>
                                </div>
                              </div>
                              <Download className="w-3 h-3 text-gray-400 flex-shrink-0 ml-2" />
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Email actions */}
                  <div className="px-4 py-2 bg-gray-50 dark:bg-gray-800/50 border-t border-gray-200 dark:border-gray-700">
                    <div className="flex items-center space-x-2">
                      <Button size="sm" variant="ghost" className="text-xs">
                        <Reply className="w-3 h-3 mr-1" />
                        Reply
                      </Button>
                      <Button size="sm" variant="ghost" className="text-xs">
                        <Forward className="w-3 h-3 mr-1" />
                        Forward
                      </Button>
                      {message.direction === 'inbound' && !message.read_at && (
                        <Button 
                          size="sm" 
                          variant="ghost" 
                          className="text-xs ml-auto"
                          onClick={(e) => {
                            e.stopPropagation()
                            markAsRead(message.id)
                          }}
                        >
                          Mark as read
                        </Button>
                      )}
                    </div>
                  </div>
                </>
              )}
            </div>
          )
        })}
      </div>
    )
  }

  // Render message thread (WhatsApp/LinkedIn chat style)
  const renderMessageThread = () => {
    // Group messages by date for chat style
    const messagesByDate: { [key: string]: Message[] } = {}
    messages.forEach((message) => {
      const date = new Date(message.sent_at)
      const dateKey = format(date, 'yyyy-MM-dd')
      if (!messagesByDate[dateKey]) {
        messagesByDate[dateKey] = []
      }
      messagesByDate[dateKey].push(message)
    })

    return (
      <div className="relative">
        <div className="space-y-6 p-4">
          {Object.entries(messagesByDate).map(([dateKey, dateMessages]) => {
            const date = new Date(dateMessages[0].sent_at)
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
                    new Date(dateMessages[index - 1].sent_at).getTime() + 60000 < new Date(message.sent_at).getTime()
                  
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
                            {format(new Date(message.sent_at), 'h:mm a')}
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