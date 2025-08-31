import React, { useState, useEffect, useRef, useCallback } from 'react'
import { format, isToday, isYesterday, isSameDay } from 'date-fns'
import { 
  Mail, Phone, Users, MessageSquare, Calendar, ChevronDown, 
  ChevronRight, User, Loader2, AlertCircle, ExternalLink,
  Send, ArrowDownLeft, ArrowUpRight
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import DOMPurify from 'dompurify'

interface TimelineMessage {
  id: string
  conversation_id: string
  channel_type: string
  channel_name: string
  direction: 'inbound' | 'outbound'
  content: string
  html_content?: string
  sent_at: string
  created_at: string
  sender_name: string
  sender_email?: string
  contact_name?: string
  contact_email?: string
  subject?: string
  status?: string
  attachments?: any[]
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

interface MessageTimelineProps {
  messages: TimelineMessage[]
  isLoading: boolean
  error: string | null
  onLoadMore?: () => void
  hasMore?: boolean
}

export function MessageTimeline({
  messages,
  isLoading,
  error,
  onLoadMore,
  hasMore = false
}: MessageTimelineProps) {
  const [expandedMessages, setExpandedMessages] = useState<Set<string>>(new Set())
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const loadMoreRef = useRef<HTMLDivElement>(null)

  // Group messages by date
  const groupedMessages = React.useMemo(() => {
    const groups: { [date: string]: TimelineMessage[] } = {}
    
    messages.forEach(message => {
      const date = format(new Date(message.sent_at), 'yyyy-MM-dd')
      if (!groups[date]) {
        groups[date] = []
      }
      groups[date].push(message)
    })
    
    // Sort dates in descending order (newest first)
    return Object.entries(groups).sort((a, b) => b[0].localeCompare(a[0]))
  }, [messages])

  // Helper functions
  const getChannelIcon = (channelType: string) => {
    switch (channelType) {
      case 'email':
      case 'gmail':
        return <Mail className="w-4 h-4" />
      case 'whatsapp':
        return <Phone className="w-4 h-4" />
      case 'linkedin':
        return <Users className="w-4 h-4" />
      default:
        return <MessageSquare className="w-4 h-4" />
    }
  }

  const getChannelColor = (channelType: string) => {
    switch (channelType) {
      case 'email':
      case 'gmail':
        return 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
      case 'whatsapp':
        return 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
      case 'linkedin':
        return 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900 dark:text-indigo-300'
      default:
        return 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'
    }
  }

  const getDateLabel = (date: Date): string => {
    if (isToday(date)) return 'Today'
    if (isYesterday(date)) return 'Yesterday'
    return format(date, 'EEEE, MMMM d, yyyy')
  }

  const getInitials = (name: string): string => {
    if (!name || name === 'Unknown') return '?'
    const parts = name.split(' ')
    if (parts.length >= 2) {
      return `${parts[0][0]}${parts[1][0]}`.toUpperCase()
    }
    return name.slice(0, 2).toUpperCase()
  }

  const toggleMessageExpanded = (messageId: string) => {
    setExpandedMessages(prev => {
      const newSet = new Set(prev)
      if (newSet.has(messageId)) {
        newSet.delete(messageId)
      } else {
        newSet.add(messageId)
      }
      return newSet
    })
  }

  const makeUrlsClickable = (text: string): string => {
    if (!text) return ''
    const urlRegex = /(https?:\/\/[^\s<>"\{\}\\^\[\]`]+)/gi
    return text.replace(urlRegex, (url) => {
      const cleanUrl = url.replace(/[.,;:!?]+$/, '')
      const displayText = cleanUrl.length > 60 ? cleanUrl.substring(0, 57) + '...' : cleanUrl
      return `<a href="${cleanUrl}" target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 underline break-all">${displayText}</a>`
    })
  }

  const isHtmlContent = (content: string): boolean => {
    if (!content) return false
    const htmlRegex = /<[^>]*>/
    return htmlRegex.test(content)
  }

  const prepareHtmlContent = (html: string): string => {
    if (!html) return ''
    
    // First unescape HTML entities
    const textarea = document.createElement('textarea')
    textarea.innerHTML = html
    let unescapedHtml = textarea.value
    
    // Remove CID images
    unescapedHtml = unescapedHtml.replace(/<img[^>]*src=["']cid:[^"']*["'][^>]*>/gi, '')
    
    // Remove style tags but keep the elements
    unescapedHtml = unescapedHtml.replace(/style\s*=\s*["'][^"']*["']/gi, '')
    
    // Sanitize with DOMPurify
    const clean = DOMPurify.sanitize(unescapedHtml, {
      ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'a', 'ul', 'ol', 'li', 'blockquote', 
                     'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div', 'span', 'img', 'table', 
                     'thead', 'tbody', 'tr', 'td', 'th', 'b', 'i'],
      ALLOWED_ATTR: ['href', 'target', 'rel', 'src', 'alt', 'width', 'height'],
      ALLOW_DATA_ATTR: false
    })
    
    return clean
  }

  // Render message content based on type
  const renderMessageContent = (message: TimelineMessage) => {
    const isExpanded = expandedMessages.has(message.id)
    const isEmail = message.channel_type === 'email' || message.channel_type === 'gmail'
    
    if (isEmail) {
      // Email messages - collapsible with full HTML
      return (
        <div className="mt-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => toggleMessageExpanded(message.id)}
            className="mb-2"
          >
            {isExpanded ? <ChevronDown className="w-4 h-4 mr-1" /> : <ChevronRight className="w-4 h-4 mr-1" />}
            {isExpanded ? 'Hide email' : 'Show email'}
          </Button>
          
          {isExpanded && (
            <div className="border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900">
              {/* Email header */}
              <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                {message.subject && (
                  <h3 className="font-semibold text-lg mb-2">{message.subject}</h3>
                )}
                <div className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                  {/* From field */}
                  <div className="flex">
                    <span className="font-medium w-12">From:</span>
                    <span className="flex-1">
                      {(() => {
                        const from = message.metadata?.from
                        if (typeof from === 'object' && from) {
                          return from.name ? `${from.name} <${from.email || ''}>` : from.email || message.sender_name || 'Unknown'
                        }
                        return message.sender_name || 'Unknown'
                      })()}
                    </span>
                  </div>
                  
                  {/* To field */}
                  <div className="flex">
                    <span className="font-medium w-12">To:</span>
                    <span className="flex-1">
                      {(() => {
                        const to = message.metadata?.to
                        if (Array.isArray(to) && to.length > 0) {
                          return to.map(recipient => 
                            recipient.name ? `${recipient.name} <${recipient.email || ''}>` : recipient.email || ''
                          ).filter(Boolean).join(', ')
                        } else if (typeof to === 'string') {
                          return to
                        }
                        return message.contact_name || message.contact_email || 'Unknown'
                      })()}
                    </span>
                  </div>
                  
                  {/* CC field */}
                  {message.metadata?.cc && message.metadata.cc.length > 0 && (
                    <div className="flex">
                      <span className="font-medium w-12">Cc:</span>
                      <span className="flex-1">
                        {message.metadata.cc.map(recipient => 
                          recipient.name ? `${recipient.name} <${recipient.email || ''}>` : recipient.email || ''
                        ).filter(Boolean).join(', ')}
                      </span>
                    </div>
                  )}
                  
                  {/* BCC field */}
                  {message.metadata?.bcc && message.metadata.bcc.length > 0 && (
                    <div className="flex">
                      <span className="font-medium w-12">Bcc:</span>
                      <span className="flex-1">
                        {message.metadata.bcc.map(recipient => 
                          recipient.name ? `${recipient.name} <${recipient.email || ''}>` : recipient.email || ''
                        ).filter(Boolean).join(', ')}
                      </span>
                    </div>
                  )}
                  
                  {/* Date */}
                  <div className="flex">
                    <span className="font-medium w-12">Date:</span>
                    <span className="flex-1">
                      {format(new Date(message.sent_at), 'EEEE, MMMM d, yyyy \'at\' h:mm a')}
                    </span>
                  </div>
                </div>
              </div>
              
              {/* Email body */}
              <div className="p-4 max-h-[400px] overflow-y-auto">
                {message.html_content || isHtmlContent(message.content) ? (
                  <div 
                    className="email-html-content"
                    dangerouslySetInnerHTML={{ 
                      __html: prepareHtmlContent(message.html_content || message.content) 
                    }}
                  />
                ) : (
                  <div 
                    className="whitespace-pre-wrap text-sm"
                    dangerouslySetInnerHTML={{ 
                      __html: makeUrlsClickable(message.content || '') 
                    }}
                  />
                )}
              </div>
            </div>
          )}
          
          {!isExpanded && (
            <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
              {message.content ? message.content.substring(0, 150) + '...' : 'No content'}
            </p>
          )}
        </div>
      )
    } else {
      // Chat messages - always show full content with clickable URLs
      return (
        <div 
          className="mt-2 text-sm whitespace-pre-wrap break-words"
          dangerouslySetInnerHTML={{ 
            __html: makeUrlsClickable(message.content || '') 
          }}
        />
      )
    }
  }

  // Handle infinite scroll
  useEffect(() => {
    if (!loadMoreRef.current || !hasMore || isLoading) return

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && onLoadMore) {
          onLoadMore()
        }
      },
      { threshold: 0.1 }
    )

    observer.observe(loadMoreRef.current)
    return () => observer.disconnect()
  }, [hasMore, isLoading, onLoadMore])

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 space-y-4">
        <AlertCircle className="w-12 h-12 text-red-500" />
        <p className="text-sm text-gray-600 dark:text-gray-400">{error}</p>
      </div>
    )
  }

  if (isLoading && messages.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    )
  }

  if (messages.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 space-y-4">
        <MessageSquare className="w-12 h-12 text-gray-400" />
        <p className="text-sm text-gray-600 dark:text-gray-400">
          No messages found
        </p>
      </div>
    )
  }

  return (
    <ScrollArea className="h-full" ref={scrollAreaRef}>
      <div className="p-4 space-y-6">
        {groupedMessages.map(([date, dateMessages]) => (
          <div key={date}>
            {/* Date separator */}
            <div className="flex items-center justify-center my-4">
              <div className="flex items-center space-x-2 px-3 py-1 bg-gray-100 dark:bg-gray-800 rounded-full">
                <Calendar className="w-3 h-3 text-gray-500" />
                <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
                  {getDateLabel(new Date(date))}
                </span>
              </div>
            </div>

            {/* Messages for this date */}
            <div className="space-y-4">
              {dateMessages.map((message) => (
                <div
                  key={message.id}
                  className={cn(
                    "flex gap-3 p-4 rounded-lg transition-colors",
                    "hover:bg-gray-50 dark:hover:bg-gray-800/50",
                    "border border-gray-200 dark:border-gray-700"
                  )}
                >
                  {/* Avatar and direction indicator */}
                  <div className="flex-shrink-0">
                    <div className="relative">
                      <Avatar className="w-10 h-10">
                        <AvatarFallback className={cn(
                          message.direction === 'outbound' 
                            ? "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300"
                            : "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300"
                        )}>
                          {getInitials((() => {
                            // Use enriched name from metadata when available
                            if ((message.channel_type === 'whatsapp' || message.channel_type === 'linkedin') && message.metadata) {
                              if (message.direction === 'outbound' && message.metadata.account_owner_name) {
                                return message.metadata.account_owner_name
                              }
                              if (message.direction === 'inbound' && message.metadata.contact_name) {
                                return message.metadata.contact_name
                              }
                            }
                            return message.sender_name || 'Unknown'
                          })())}
                        </AvatarFallback>
                      </Avatar>
                      <div className={cn(
                        "absolute -bottom-1 -right-1 w-5 h-5 rounded-full flex items-center justify-center",
                        message.direction === 'outbound' 
                          ? "bg-blue-500 text-white" 
                          : "bg-green-500 text-white"
                      )}>
                        {message.direction === 'outbound' 
                          ? <Send className="w-3 h-3" />
                          : <ArrowDownLeft className="w-3 h-3" />
                        }
                      </div>
                    </div>
                  </div>

                  {/* Message content */}
                  <div className="flex-1 min-w-0">
                    {/* Header with sender, channel, and time */}
                    <div className="flex items-start justify-between mb-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={cn(
                          "font-medium text-sm",
                          message.direction === 'outbound' ? "text-blue-600 dark:text-blue-400" : ""
                        )}>
                          {(() => {
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
                            return message.sender_name || 'Unknown'
                          })()}
                        </span>
                        {(() => {
                          // Determine recipient name
                          let recipientName = null
                          
                          // For WhatsApp/LinkedIn, check metadata
                          if ((message.channel_type === 'whatsapp' || message.channel_type === 'linkedin') && message.metadata) {
                            if (message.direction === 'outbound' && message.metadata.contact_name) {
                              recipientName = message.metadata.contact_name
                            } else if (message.direction === 'inbound') {
                              // Try recipient_user_name first, then account_owner_name for backward compatibility
                              recipientName = message.metadata.recipient_user_name || message.metadata.account_owner_name || message.metadata.user_name
                            }
                          }
                          
                          // Fallback to message.contact_name
                          if (!recipientName) {
                            recipientName = message.contact_name
                          }
                          
                          if (recipientName) {
                            return (
                              <>
                                <span className="text-gray-400">
                                  {message.direction === 'outbound' ? '→' : '←'}
                                </span>
                                <span className={cn(
                                  "text-sm",
                                  message.direction === 'inbound' 
                                    ? "text-blue-600 dark:text-blue-400 font-medium" 
                                    : "text-gray-600 dark:text-gray-400"
                                )}>
                                  {recipientName}
                                </span>
                              </>
                            )
                          }
                          return null
                        })()}
                        <Badge 
                          variant="secondary" 
                          className={cn("text-xs", getChannelColor(message.channel_type))}
                        >
                          {getChannelIcon(message.channel_type)}
                          <span className="ml-1">{message.channel_type}</span>
                        </Badge>
                        <Badge 
                          variant={message.direction === 'outbound' ? 'default' : 'secondary'}
                          className="text-xs"
                        >
                          {message.direction === 'outbound' ? 'Sent' : 'Received'}
                        </Badge>
                      </div>
                      <span className="text-xs text-gray-500 ml-2">
                        {format(new Date(message.sent_at), 'h:mm a')}
                      </span>
                    </div>

                    {/* Subject for emails */}
                    {message.subject && (
                      <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        {message.subject}
                      </div>
                    )}

                    {/* Message content */}
                    {renderMessageContent(message)}

                    {/* Attachments indicator */}
                    {message.attachments && message.attachments.length > 0 && (
                      <div className="mt-2 text-xs text-gray-500">
                        📎 {message.attachments.length} attachment{message.attachments.length > 1 ? 's' : ''}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}

        {/* Load more indicator */}
        {hasMore && (
          <div ref={loadMoreRef} className="flex justify-center py-4">
            {isLoading ? (
              <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
            ) : (
              <Button variant="outline" size="sm" onClick={onLoadMore}>
                Load more messages
              </Button>
            )}
          </div>
        )}
      </div>
    </ScrollArea>
  )
}