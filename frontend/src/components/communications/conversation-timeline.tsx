"use client"

import React, { useState, useEffect, useRef, useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Separator } from '@/components/ui/separator'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { 
  MessageSquare, 
  Phone, 
  Mail, 
  Linkedin, 
  Instagram,
  MessageCircle,
  Clock,
  CheckCircle2,
  Circle,
  Eye,
  EyeOff,
  Star,
  Reply,
  Forward,
  MoreHorizontal,
  Paperclip,
  Image as ImageIcon,
  File,
  Download,
  ExternalLink,
  Filter,
  Search,
  Calendar,
  User,
  Building
} from 'lucide-react'
import { formatDistanceToNow, format, isSameDay, isToday, isYesterday } from 'date-fns'

// Types
interface TimelineMessage {
  id: string
  content: string
  subject: string
  direction: 'inbound' | 'outbound'
  status: 'pending' | 'sent' | 'delivered' | 'read' | 'failed'
  created_at: string
  sent_at: string | null
  channel: {
    type: string
    name: string
    icon: string
  }
  conversation_id: string
  metadata: Record<string, any>
  contact_email: string
  contact_phone: string
  attachments: Array<{
    filename: string
    content_type: string
    size: number
    download_url?: string
  }>
  thread_info?: {
    thread_id: string
    thread_type: string
    strategy: string
  }
}

interface ConversationTimelineProps {
  recordId: number
  recordTitle: string
  className?: string
}

interface TimelineData {
  record: {
    id: number
    title: string
    pipeline_name: string
    data: Record<string, any>
  }
  messages: TimelineMessage[]
  available_channels: Array<{
    type: string
    icon: string
    name: string
    connected: boolean
    can_send: boolean
  }>
  pagination: {
    total_count: number
    has_next: boolean
    has_previous: boolean
    current_page: number
    total_pages: number
  }
}

export default function ConversationTimeline({ recordId, recordTitle, className = "" }: ConversationTimelineProps) {
  const [timelineData, setTimelineData] = useState<TimelineData | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedChannels, setSelectedChannels] = useState<Set<string>>(new Set())
  const [searchQuery, setSearchQuery] = useState('')
  const [showOnlyUnread, setShowOnlyUnread] = useState(false)
  const [selectedMessage, setSelectedMessage] = useState<TimelineMessage | null>(null)
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Fetch timeline data
  useEffect(() => {
    fetchTimeline()
  }, [recordId])

  const fetchTimeline = async () => {
    try {
      setLoading(true)
      const response = await fetch(`/api/v1/communications/records/${recordId}/timeline/`)
      
      if (response.ok) {
        const data = await response.json()
        setTimelineData(data)
        
        // Initialize with all channels selected
        if (data.available_channels) {
          setSelectedChannels(new Set(data.available_channels.map((ch: any) => ch.type)))
        }
      }
    } catch (error) {
      console.error('Error fetching timeline:', error)
    } finally {
      setLoading(false)
    }
  }

  // Filter messages based on search, channels, and read status
  const filteredMessages = useMemo(() => {
    if (!timelineData) return []
    
    let filtered = timelineData.messages
    
    // Channel filter
    if (selectedChannels.size > 0) {
      filtered = filtered.filter(message => selectedChannels.has(message.channel.type))
    }
    
    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter(message =>
        message.content.toLowerCase().includes(query) ||
        message.subject.toLowerCase().includes(query) ||
        message.contact_email.toLowerCase().includes(query)
      )
    }
    
    // Unread filter
    if (showOnlyUnread) {
      filtered = filtered.filter(message => 
        message.direction === 'inbound' && 
        message.status !== 'read'
      )
    }
    
    return filtered
  }, [timelineData, selectedChannels, searchQuery, showOnlyUnread])

  // Group messages by date
  const messagesByDate = useMemo(() => {
    const groups: Record<string, TimelineMessage[]> = {}
    
    filteredMessages.forEach(message => {
      const date = new Date(message.created_at)
      const dateKey = format(date, 'yyyy-MM-dd')
      
      if (!groups[dateKey]) {
        groups[dateKey] = []
      }
      groups[dateKey].push(message)
    })
    
    // Sort each group by time
    Object.keys(groups).forEach(dateKey => {
      groups[dateKey].sort((a, b) => 
        new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      )
    })
    
    return groups
  }, [filteredMessages])

  // Channel toggle handler
  const toggleChannel = (channelType: string) => {
    setSelectedChannels(prev => {
      const newSet = new Set(prev)
      if (newSet.has(channelType)) {
        newSet.delete(channelType)
      } else {
        newSet.add(channelType)
      }
      return newSet
    })
  }

  // Message actions
  const markAsRead = async (messageId: string) => {
    // Implementation for marking message as read
    console.log('Mark as read:', messageId)
  }

  const replyToMessage = (message: TimelineMessage) => {
    // Implementation for replying to message
    console.log('Reply to message:', message)
  }

  const forwardMessage = (message: TimelineMessage) => {
    // Implementation for forwarding message
    console.log('Forward message:', message)
  }

  // Helper functions
  const getChannelIcon = (channelType: string) => {
    switch (channelType) {
      case 'whatsapp': return <MessageCircle className="h-4 w-4" />
      case 'linkedin': return <Linkedin className="h-4 w-4" />
      case 'gmail':
      case 'outlook':
      case 'mail': return <Mail className="h-4 w-4" />
      case 'phone': return <Phone className="h-4 w-4" />
      case 'instagram': return <Instagram className="h-4 w-4" />
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

  const getStatusIcon = (status: string, direction: string) => {
    if (direction === 'outbound') {
      switch (status) {
        case 'sent': return <CheckCircle2 className="h-3 w-3 text-blue-500" />
        case 'delivered': return <CheckCircle2 className="h-3 w-3 text-green-500" />
        case 'read': return <Eye className="h-3 w-3 text-green-600" />
        case 'failed': return <Circle className="h-3 w-3 text-red-500" />
        default: return <Clock className="h-3 w-3 text-gray-400" />
      }
    } else {
      return status === 'read' ? <EyeOff className="h-3 w-3 text-gray-400" /> : <Circle className="h-3 w-3 text-blue-500" />
    }
  }

  const formatDateHeader = (dateKey: string) => {
    const date = new Date(dateKey + 'T00:00:00')
    
    if (isToday(date)) {
      return 'Today'
    } else if (isYesterday(date)) {
      return 'Yesterday'
    } else {
      return format(date, 'EEEE, MMMM d, yyyy')
    }
  }

  const formatMessageTime = (timestamp: string) => {
    return format(new Date(timestamp), 'h:mm a')
  }

  const getAttachmentIcon = (contentType: string) => {
    if (contentType.startsWith('image/')) {
      return <ImageIcon className="h-4 w-4" />
    } else {
      return <File className="h-4 w-4" />
    }
  }

  if (loading) {
    return (
      <Card className={className}>
        <CardContent className="p-6">
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={className}>
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            Conversation Timeline
            <Badge variant="secondary">
              {filteredMessages.length} messages
            </Badge>
          </CardTitle>
          
          <div className="flex items-center gap-2">
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => setShowOnlyUnread(!showOnlyUnread)}
              className={showOnlyUnread ? 'bg-blue-50 border-blue-200' : ''}
            >
              <Eye className="h-4 w-4 mr-1" />
              {showOnlyUnread ? 'Show All' : 'Unread Only'}
            </Button>
            
            <Button variant="outline" size="sm">
              <Filter className="h-4 w-4" />
            </Button>
          </div>
        </div>
        
        {/* Search and Channel Filters */}
        <div className="space-y-3">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search messages..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          
          {/* Channel Filters */}
          {timelineData?.available_channels && (
            <div className="flex flex-wrap gap-2">
              {timelineData.available_channels.map((channel) => (
                <Button
                  key={channel.type}
                  variant="outline"
                  size="sm"
                  onClick={() => toggleChannel(channel.type)}
                  className={`h-8 ${
                    selectedChannels.has(channel.type) 
                      ? 'bg-blue-50 border-blue-200 text-blue-700' 
                      : 'hover:bg-gray-50'
                  }`}
                >
                  <div className={`p-1 rounded-full text-white mr-2 ${getChannelColor(channel.type)}`}>
                    {getChannelIcon(channel.type)}
                  </div>
                  {channel.name}
                </Button>
              ))}
            </div>
          )}
        </div>
      </CardHeader>
      
      <CardContent className="p-0">
        <ScrollArea className="h-[600px]" ref={scrollAreaRef}>
          <div className="p-4 space-y-6">
            {Object.keys(messagesByDate)
              .sort((a, b) => a.localeCompare(b))
              .map((dateKey) => (
                <div key={dateKey}>
                  {/* Date Header */}
                  <div className="flex items-center gap-4 mb-4">
                    <Separator className="flex-1" />
                    <div className="flex items-center gap-2 px-3 py-1 bg-gray-100 rounded-full text-sm text-gray-600">
                      <Calendar className="h-3 w-3" />
                      {formatDateHeader(dateKey)}
                    </div>
                    <Separator className="flex-1" />
                  </div>
                  
                  {/* Messages for this date */}
                  <div className="space-y-4">
                    {messagesByDate[dateKey].map((message) => (
                      <div
                        key={message.id}
                        className={`flex gap-3 ${
                          message.direction === 'outbound' ? 'flex-row-reverse' : ''
                        }`}
                      >
                        {/* Avatar */}
                        <Avatar className="h-8 w-8 shrink-0">
                          {message.direction === 'outbound' ? (
                            <AvatarFallback className="bg-blue-100 text-blue-700">
                              <User className="h-4 w-4" />
                            </AvatarFallback>
                          ) : (
                            <AvatarFallback className="bg-gray-100 text-gray-700">
                              {message.contact_email ? message.contact_email.charAt(0).toUpperCase() : 'C'}
                            </AvatarFallback>
                          )}
                        </Avatar>
                        
                        {/* Message Content */}
                        <div className={`flex-1 max-w-[70%] ${message.direction === 'outbound' ? 'text-right' : ''}`}>
                          {/* Message Header */}
                          <div className={`flex items-center gap-2 mb-1 ${message.direction === 'outbound' ? 'flex-row-reverse' : ''}`}>
                            <div className={`p-1 rounded-full text-white ${getChannelColor(message.channel.type)}`}>
                              {getChannelIcon(message.channel.type)}
                            </div>
                            
                            <span className="text-sm font-medium">
                              {message.direction === 'outbound' ? 'You' : (message.contact_email || 'Contact')}
                            </span>
                            
                            <span className="text-xs text-gray-500">
                              {formatMessageTime(message.created_at)}
                            </span>
                            
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger>
                                  {getStatusIcon(message.status, message.direction)}
                                </TooltipTrigger>
                                <TooltipContent>
                                  <p>{message.status.charAt(0).toUpperCase() + message.status.slice(1)}</p>
                                </TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                          </div>
                          
                          {/* Message Body */}
                          <div 
                            className={`p-3 rounded-lg ${
                              message.direction === 'outbound'
                                ? 'bg-blue-500 text-white'
                                : 'bg-gray-100 text-gray-900'
                            }`}
                          >
                            {/* Subject (if exists) */}
                            {message.subject && (
                              <div className={`font-medium mb-2 pb-2 border-b ${
                                message.direction === 'outbound' 
                                  ? 'border-blue-400' 
                                  : 'border-gray-200'
                              }`}>
                                {message.subject}
                              </div>
                            )}
                            
                            {/* Content */}
                            <div className="whitespace-pre-wrap break-words">
                              {message.content}
                            </div>
                            
                            {/* Attachments */}
                            {message.attachments.length > 0 && (
                              <div className="mt-3 pt-3 border-t border-opacity-30">
                                <div className="flex items-center gap-1 mb-2">
                                  <Paperclip className="h-3 w-3" />
                                  <span className="text-xs">
                                    {message.attachments.length} attachment{message.attachments.length > 1 ? 's' : ''}
                                  </span>
                                </div>
                                
                                <div className="space-y-1">
                                  {message.attachments.map((attachment, index) => (
                                    <div key={index} className="flex items-center gap-2 text-xs">
                                      {getAttachmentIcon(attachment.content_type)}
                                      <span className="flex-1 truncate">{attachment.filename}</span>
                                      {attachment.download_url && (
                                        <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                                          <Download className="h-3 w-3" />
                                        </Button>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            
                            {/* Threading info */}
                            {message.thread_info && (
                              <div className="mt-2 pt-2 border-t border-opacity-30 text-xs opacity-75">
                                Thread: {message.thread_info.thread_type} ({message.thread_info.strategy})
                              </div>
                            )}
                          </div>
                          
                          {/* Message Actions */}
                          <div className={`flex items-center gap-1 mt-1 ${message.direction === 'outbound' ? 'flex-row-reverse' : ''}`}>
                            <Button 
                              variant="ghost" 
                              size="sm" 
                              className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100"
                              onClick={() => replyToMessage(message)}
                            >
                              <Reply className="h-3 w-3" />
                            </Button>
                            
                            <Button 
                              variant="ghost" 
                              size="sm" 
                              className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100"
                              onClick={() => forwardMessage(message)}
                            >
                              <Forward className="h-3 w-3" />
                            </Button>
                            
                            {message.direction === 'inbound' && message.status !== 'read' && (
                              <Button 
                                variant="ghost" 
                                size="sm" 
                                className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100"
                                onClick={() => markAsRead(message.id)}
                              >
                                <Eye className="h-3 w-3" />
                              </Button>
                            )}
                            
                            <Button 
                              variant="ghost" 
                              size="sm" 
                              className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100"
                            >
                              <MoreHorizontal className="h-3 w-3" />
                            </Button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            
            {filteredMessages.length === 0 && (
              <div className="text-center py-12 text-gray-500">
                <MessageSquare className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                <p>No messages found matching your filters</p>
                {searchQuery && (
                  <Button 
                    variant="link" 
                    onClick={() => setSearchQuery('')}
                    className="mt-2"
                  >
                    Clear search
                  </Button>
                )}
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}