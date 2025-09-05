import React, { useState, useMemo, useCallback, useRef, useEffect } from 'react'
import { format, isToday, isYesterday, isThisWeek, isThisMonth, parseISO, startOfDay, endOfDay } from 'date-fns'
import { 
  Mail, Phone, Users, MessageSquare, Calendar, 
  Edit, Plus, Trash2, Clock, History, 
  Filter, ChevronDown, ChevronRight, User,
  Send, ArrowDownLeft, ArrowUpRight, Activity,
  Search, X, Paperclip, Check, AlertCircle,
  ArrowRight, Eye, EyeOff, Loader2, FileText,
  Download, Archive, Reply, Forward, MoreVertical,
  ChevronUp, CalendarDays, CheckCircle2, XCircle
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { ScrollArea } from '@/components/ui/scroll-area'
import DOMPurify from 'dompurify'

// Activity type from record-detail-drawer
interface Activity {
  id: string
  type: 'field_change' | 'stage_change' | 'comment' | 'system'
  field?: string
  old_value?: any
  new_value?: any
  message: string
  user: {
    first_name: string
    last_name: string
    email: string
  }
  created_at: string
}

// Communication message type
interface TimelineMessage {
  id: string
  conversation_id: string
  channel_type: string
  channel_name: string
  direction: 'inbound' | 'outbound'
  content: string
  html_content?: string
  sent_at: string | null
  received_at: string | null
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
    account_owner_name?: string
    sender_name?: string
    contact_name?: string
    read?: boolean
    [key: string]: any
  }
}

// Unified activity item
interface UnifiedActivityItem {
  id: string
  type: 'field_change' | 'stage_change' | 'comment' | 'system' | 'communication'
  timestamp: Date
  
  // For activities
  activityData?: Activity
  
  // For communications
  communicationData?: TimelineMessage
}

interface UnifiedActivityViewProps {
  activities: Activity[]
  communications: TimelineMessage[]
  isLoadingActivities?: boolean
  isLoadingCommunications?: boolean
  onLoadMoreCommunications?: () => void
  hasMoreCommunications?: boolean
}

// Skeleton loader component
const ActivitySkeleton = () => (
  <div className="flex space-x-3 animate-pulse">
    <div className="relative flex flex-col items-center">
      <div className="w-10 h-10 bg-gray-200 dark:bg-gray-700 rounded-full" />
      <div className="w-0.5 h-full bg-gray-200 dark:bg-gray-700 mt-2" />
    </div>
    <div className="flex-1 space-y-2 py-1">
      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/4" />
      <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-3/4" />
      <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2" />
    </div>
  </div>
)

export function UnifiedActivityView({
  activities,
  communications,
  isLoadingActivities = false,
  isLoadingCommunications = false,
  onLoadMoreCommunications,
  hasMoreCommunications = false
}: UnifiedActivityViewProps) {
  const [expandedMessages, setExpandedMessages] = useState<Set<string>>(new Set())
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set())
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(new Set([
    'field_change', 'stage_change', 'comment', 'system', 'communication'
  ]))
  const [selectedChannels, setSelectedChannels] = useState<Set<string>>(new Set([
    'email', 'whatsapp', 'linkedin'
  ]))
  const [dateRange, setDateRange] = useState<{ start: Date | null; end: Date | null }>({
    start: null,
    end: null
  })
  const [density, setDensity] = useState<'comfortable' | 'compact'>('comfortable')
  const [showFilters, setShowFilters] = useState(false)
  const scrollAreaRef = useRef<HTMLDivElement>(null)

  // Parse timestamp helper
  const parseTimestamp = (timestamp: string | null | undefined): Date | null => {
    if (!timestamp || timestamp === 'null' || timestamp === 'undefined') {
      return null
    }
    
    try {
      const date = new Date(timestamp)
      if (isNaN(date.getTime()) || date.getFullYear() < 2000) {
        return null
      }
      return date
    } catch (error) {
      return null
    }
  }

  // Get timestamp for communication message
  const getMessageTimestamp = (msg: TimelineMessage): Date | null => {
    return parseTimestamp(msg.sent_at) || 
           parseTimestamp(msg.received_at) || 
           parseTimestamp(msg.created_at)
  }

  // Get initials for avatar
  const getInitials = (name: string): string => {
    if (!name || name === 'Unknown') return '?'
    const parts = name.split(' ')
    if (parts.length >= 2) {
      return `${parts[0][0]}${parts[1][0]}`.toUpperCase()
    }
    return name.slice(0, 2).toUpperCase()
  }

  // Strip HTML for preview
  const stripHtml = (html: string): string => {
    if (!html) return ''
    const tmp = document.createElement('div')
    tmp.innerHTML = html
    const text = tmp.textContent || tmp.innerText || ''
    return text.replace(/\s+/g, ' ').trim()
  }

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

  // Search filter function
  const matchesSearch = (item: UnifiedActivityItem): boolean => {
    if (!searchQuery) return true
    const query = searchQuery.toLowerCase()
    
    if (item.communicationData) {
      const msg = item.communicationData
      return (
        msg.sender_name?.toLowerCase().includes(query) ||
        msg.subject?.toLowerCase().includes(query) ||
        stripHtml(msg.content).toLowerCase().includes(query) ||
        msg.channel_type?.toLowerCase().includes(query)
      )
    }
    
    if (item.activityData) {
      const activity = item.activityData
      return (
        activity.message?.toLowerCase().includes(query) ||
        activity.field?.toLowerCase().includes(query) ||
        `${activity.user?.first_name} ${activity.user?.last_name}`.toLowerCase().includes(query)
      )
    }
    
    return false
  }

  // Date range filter
  const matchesDateRange = (item: UnifiedActivityItem): boolean => {
    if (!dateRange.start && !dateRange.end) return true
    
    const itemDate = startOfDay(item.timestamp)
    if (dateRange.start && itemDate < startOfDay(dateRange.start)) return false
    if (dateRange.end && itemDate > endOfDay(dateRange.end)) return false
    
    return true
  }

  // Merge and sort activities and communications
  const unifiedItems = useMemo(() => {
    const items: UnifiedActivityItem[] = []
    
    // Add activities
    if (selectedTypes.has('field_change') || selectedTypes.has('stage_change') || 
        selectedTypes.has('comment') || selectedTypes.has('system')) {
      activities.forEach(activity => {
        if (!selectedTypes.has(activity.type)) return
        
        const timestamp = parseTimestamp(activity.created_at)
        if (timestamp) {
          items.push({
            id: `activity-${activity.id}`,
            type: activity.type,
            timestamp,
            activityData: activity
          })
        }
      })
    }
    
    // Add communications with channel filtering
    if (selectedTypes.has('communication')) {
      communications.forEach(msg => {
        // Filter by channel - group email types together
        let channelGroup = msg.channel_type
        if (msg.channel_type === 'gmail' || msg.channel_type === 'outlook' || msg.channel_type === 'email') {
          channelGroup = 'email'
        }
        
        if (!selectedChannels.has(channelGroup)) return
        
        const timestamp = getMessageTimestamp(msg)
        if (timestamp) {
          items.push({
            id: `comm-${msg.id}`,
            type: 'communication',
            timestamp,
            communicationData: msg
          })
        }
      })
    }
    
    // Apply filters
    return items
      .filter(matchesSearch)
      .filter(matchesDateRange)
      .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
  }, [activities, communications, selectedTypes, selectedChannels, searchQuery, dateRange])

  // Group items by date
  const groupedItems = useMemo(() => {
    const groups: { [key: string]: UnifiedActivityItem[] } = {}
    
    unifiedItems.forEach(item => {
      const dateKey = format(item.timestamp, 'yyyy-MM-dd')
      if (!groups[dateKey]) {
        groups[dateKey] = []
      }
      groups[dateKey].push(item)
    })
    
    return groups
  }, [unifiedItems])

  // Format date header
  const formatDateHeader = (dateStr: string) => {
    const date = new Date(dateStr)
    if (isToday(date)) return 'Today'
    if (isYesterday(date)) return 'Yesterday'
    if (isThisWeek(date)) return format(date, 'EEEE')
    if (isThisMonth(date)) return format(date, 'MMMM d')
    return format(date, 'MMMM d, yyyy')
  }

  // Get channel icon with better styling
  const getChannelIcon = (channelType: string, direction?: string) => {
    const iconClass = cn(
      "w-5 h-5",
      direction === 'inbound' ? "text-blue-600 dark:text-blue-400" : "text-green-600 dark:text-green-400"
    )
    
    switch (channelType) {
      case 'email':
      case 'gmail':
      case 'outlook':
        return <Mail className={iconClass} />
      case 'whatsapp':
        return <MessageSquare className={iconClass} />
      case 'linkedin':
        return <Users className={iconClass} />
      default:
        return <MessageSquare className={iconClass} />
    }
  }

  // Get activity icon with better colors
  const getActivityIcon = (type: string, message?: string) => {
    switch (type) {
      case 'system':
        return message?.includes('created') ? 
          <Plus className="w-5 h-5 text-green-600 dark:text-green-400" /> :
          <Activity className="w-5 h-5 text-gray-600 dark:text-gray-400" />
      case 'field_change':
        return <Edit className="w-5 h-5 text-blue-600 dark:text-blue-400" />
      case 'stage_change':
        return <ArrowRight className="w-5 h-5 text-purple-600 dark:text-purple-400" />
      case 'comment':
        return <MessageSquare className="w-5 h-5 text-amber-600 dark:text-amber-400" />
      default:
        return <Activity className="w-5 h-5 text-gray-600 dark:text-gray-400" />
    }
  }

  // Toggle message expansion
  const toggleMessageExpanded = (id: string) => {
    setExpandedMessages(prev => {
      const newSet = new Set(prev)
      if (newSet.has(id)) {
        newSet.delete(id)
      } else {
        newSet.add(id)
      }
      return newSet
    })
  }

  // Toggle group collapse
  const toggleGroupCollapse = (dateKey: string) => {
    setCollapsedGroups(prev => {
      const newSet = new Set(prev)
      if (newSet.has(dateKey)) {
        newSet.delete(dateKey)
      } else {
        newSet.add(dateKey)
      }
      return newSet
    })
  }

  // Toggle type selection
  const toggleTypeSelection = (type: string) => {
    setSelectedTypes(prev => {
      const newSet = new Set(prev)
      if (newSet.has(type)) {
        newSet.delete(type)
      } else {
        newSet.add(type)
      }
      return newSet
    })
  }

  // Toggle channel selection
  const toggleChannelSelection = (channel: string) => {
    setSelectedChannels(prev => {
      const newSet = new Set(prev)
      if (newSet.has(channel)) {
        newSet.delete(channel)
      } else {
        newSet.add(channel)
      }
      return newSet
    })
  }

  // Format field value for display
  const formatFieldValue = (value: any): string => {
    if (value === null || value === undefined) return 'empty'
    if (typeof value === 'boolean') return value ? 'Yes' : 'No'
    if (typeof value === 'object') return JSON.stringify(value)
    return String(value)
  }

  // Render communication card
  const renderCommunicationCard = (item: UnifiedActivityItem, isLast: boolean) => {
    const msg = item.communicationData!
    const isExpanded = expandedMessages.has(item.id)
    const isEmail = msg.channel_type === 'email' || msg.channel_type === 'gmail' || msg.channel_type === 'outlook'
    const hasAttachments = msg.attachments && msg.attachments.length > 0
    const isRead = msg.metadata?.read !== false
    
    // For emails, show collapsed view with just subject
    if (isEmail) {
      return (
        <div className="flex space-x-3 group">
          {/* Timeline line and icon */}
          <div className="relative flex flex-col items-center">
            <div className={cn(
              "relative z-10 flex items-center justify-center rounded-full transition-all",
              density === 'compact' ? "w-8 h-8" : "w-10 h-10",
              msg.direction === 'inbound' 
                ? "bg-blue-100 dark:bg-blue-900/50 ring-2 ring-blue-500/20" 
                : "bg-green-100 dark:bg-green-900/50 ring-2 ring-green-500/20",
              "group-hover:ring-4"
            )}>
              {getChannelIcon(msg.channel_type, msg.direction)}
            </div>
            {!isLast && (
              <div className="w-0.5 flex-1 bg-gradient-to-b from-gray-300 to-gray-100 dark:from-gray-600 dark:to-gray-800 mt-2" />
            )}
          </div>
          
          {/* Content card - clickable for emails */}
          <div className={cn(
            "flex-1 bg-white dark:bg-gray-800 rounded-lg border shadow-sm hover:shadow-md transition-all",
            density === 'compact' ? "p-3" : "p-4",
            !isRead && "border-blue-500 bg-blue-50/50 dark:bg-blue-900/20"
          )}>
            {/* Clickable area for expand/collapse */}
            <div 
              className="cursor-pointer"
              onClick={() => toggleMessageExpanded(item.id)}
            >
              {/* Header */}
              <div className="flex items-start justify-between">
                <div className="flex items-center space-x-3 flex-1">
                  <Avatar className={density === 'compact' ? "h-8 w-8" : "h-10 w-10"}>
                    <AvatarFallback className="text-xs font-medium">
                      {getInitials(msg.sender_name)}
                    </AvatarFallback>
                  </Avatar>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      <span className="font-medium text-sm text-gray-900 dark:text-white">
                        {msg.sender_name || 'Unknown'}
                      </span>
                      {msg.direction === 'inbound' ? (
                        <ArrowDownLeft className="w-3 h-3 text-blue-500" />
                      ) : (
                        <ArrowUpRight className="w-3 h-3 text-green-500" />
                      )}
                      {!isRead && (
                        <Badge variant="default" className="text-xs px-1.5 py-0">
                          New
                        </Badge>
                      )}
                    </div>
                    
                    {/* Subject line - always visible for emails */}
                    {msg.subject && (
                      <div className="flex items-center mt-1">
                        <p className="font-medium text-sm text-gray-700 dark:text-gray-300 truncate flex-1">
                          {msg.subject}
                        </p>
                      </div>
                    )}
                    
                    {/* Show email only when collapsed */}
                    {!isExpanded && msg.sender_email && (
                      <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                        {msg.sender_email}
                      </p>
                    )}
                  </div>
                </div>
                
                <div className="flex items-center space-x-2 ml-2">
                  <Badge variant="outline" className="text-xs">
                    {msg.channel_type}
                  </Badge>
                  
                  <span className="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">
                    {format(item.timestamp, 'h:mm a')}
                  </span>
                  
                  {/* Expand/collapse indicator */}
                  <div className="text-gray-400">
                    {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </div>
                </div>
              </div>
              
              {/* Attachments indicator when collapsed */}
              {!isExpanded && hasAttachments && (
                <div className="flex items-center space-x-2 mt-2 ml-11">
                  <Paperclip className="w-3 h-3 text-gray-400" />
                  <span className="text-xs text-gray-500">
                    {msg.attachments?.length || 0} attachment{(msg.attachments?.length || 0) > 1 ? 's' : ''}
                  </span>
                </div>
              )}
            </div>
            
            {/* Expanded email content */}
            {isExpanded && (
              <>
                <div className="border-t border-gray-200 dark:border-gray-700 mt-3 pt-3">
                  {/* Full email details */}
                  {msg.sender_email && (
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
                      From: {msg.sender_email}
                    </p>
                  )}
                  
                  {/* Email body with proper formatting */}
                  <div className="email-content-wrapper overflow-auto max-h-[600px]">
                    {(msg.html_content || isHtmlContent(msg.content)) ? (
                      <div 
                        className="email-html-content"
                        style={{
                          transform: 'scale(0.85)',
                          transformOrigin: 'top left',
                          width: '117.6%', // Compensate for 0.85 scale (1/0.85 = 1.176)
                          contain: 'layout style paint' // CSS containment to prevent leakage
                        }}
                        dangerouslySetInnerHTML={{ 
                          __html: prepareHtmlContent(msg.html_content || msg.content)
                        }}
                      />
                    ) : (
                      <div className="whitespace-pre-wrap text-sm text-gray-700 dark:text-gray-300">
                        {msg.content}
                      </div>
                    )}
                  </div>
                  
                  {/* Attachments when expanded */}
                  {hasAttachments && (
                    <div className="mt-4 pt-3 border-t border-gray-200 dark:border-gray-700">
                      <div className="flex items-center space-x-2">
                        <Paperclip className="w-4 h-4 text-gray-400" />
                        <span className="text-sm text-gray-600 dark:text-gray-400">
                          {msg.attachments?.length || 0} attachment{(msg.attachments?.length || 0) > 1 ? 's' : ''}
                        </span>
                      </div>
                    </div>
                  )}
                  
                  {/* Quick actions */}
                  <div className="flex items-center space-x-2 mt-4 pt-3 border-t border-gray-200 dark:border-gray-700">
                    <Button variant="outline" size="sm" className="text-xs">
                      <Reply className="w-3 h-3 mr-1" />
                      Reply
                    </Button>
                    <Button variant="outline" size="sm" className="text-xs">
                      <Forward className="w-3 h-3 mr-1" />
                      Forward
                    </Button>
                    <Button variant="outline" size="sm" className="text-xs">
                      <Archive className="w-3 h-3 mr-1" />
                      Archive
                    </Button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )
    }
    
    // Non-email messages (WhatsApp, LinkedIn, etc.)
    return (
      <div className="flex space-x-3 group">
        {/* Timeline line and icon */}
        <div className="relative flex flex-col items-center">
          <div className={cn(
            "relative z-10 flex items-center justify-center rounded-full transition-all",
            density === 'compact' ? "w-8 h-8" : "w-10 h-10",
            msg.direction === 'inbound' 
              ? "bg-blue-100 dark:bg-blue-900/50 ring-2 ring-blue-500/20" 
              : "bg-green-100 dark:bg-green-900/50 ring-2 ring-green-500/20",
            "group-hover:ring-4"
          )}>
            {getChannelIcon(msg.channel_type, msg.direction)}
          </div>
          {!isLast && (
            <div className="w-0.5 flex-1 bg-gradient-to-b from-gray-300 to-gray-100 dark:from-gray-600 dark:to-gray-800 mt-2" />
          )}
        </div>
        
        {/* Content card */}
        <div className={cn(
          "flex-1 bg-white dark:bg-gray-800 rounded-lg border shadow-sm hover:shadow-md transition-all",
          density === 'compact' ? "p-3" : "p-4",
          !isRead && "border-blue-500 bg-blue-50/50 dark:bg-blue-900/20"
        )}>
          {/* Header */}
          <div className="flex items-start justify-between mb-2">
            <div className="flex items-center space-x-3">
              <Avatar className={density === 'compact' ? "h-8 w-8" : "h-10 w-10"}>
                <AvatarFallback className="text-xs font-medium">
                  {getInitials(msg.sender_name)}
                </AvatarFallback>
              </Avatar>
              
              <div>
                <div className="flex items-center space-x-2">
                  <span className="font-medium text-sm text-gray-900 dark:text-white">
                    {msg.sender_name || 'Unknown'}
                  </span>
                  {msg.direction === 'inbound' ? (
                    <ArrowDownLeft className="w-3 h-3 text-blue-500" />
                  ) : (
                    <ArrowUpRight className="w-3 h-3 text-green-500" />
                  )}
                  {!isRead && (
                    <Badge variant="default" className="text-xs px-1.5 py-0">
                      New
                    </Badge>
                  )}
                </div>
              </div>
            </div>
            
            <div className="flex items-center space-x-2">
              <Badge variant="outline" className="text-xs">
                {msg.channel_type}
              </Badge>
              
              <span className="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">
                {format(item.timestamp, 'h:mm a')}
              </span>
            </div>
          </div>
          
          {/* Message content */}
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {stripHtml(msg.content)}
          </p>
        </div>
      </div>
    )
  }

  // Render activity card
  const renderActivityCard = (item: UnifiedActivityItem, isLast: boolean) => {
    const activity = item.activityData!
    
    return (
      <div className="flex space-x-3 group">
        {/* Timeline line and icon */}
        <div className="relative flex flex-col items-center">
          <div className={cn(
            "relative z-10 flex items-center justify-center rounded-full transition-all",
            density === 'compact' ? "w-8 h-8" : "w-10 h-10",
            "bg-gray-100 dark:bg-gray-800 ring-2 ring-gray-200 dark:ring-gray-700",
            "group-hover:ring-4"
          )}>
            {getActivityIcon(activity.type, activity.message)}
          </div>
          {!isLast && (
            <div className="w-0.5 flex-1 bg-gradient-to-b from-gray-300 to-gray-100 dark:from-gray-600 dark:to-gray-800 mt-2" />
          )}
        </div>
        
        {/* Content */}
        <div className={cn(
          "flex-1 bg-white dark:bg-gray-800 rounded-lg border shadow-sm hover:shadow-md transition-all",
          density === 'compact' ? "p-3" : "p-4"
        )}>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center space-x-2 mb-1">
                <Avatar className="h-6 w-6">
                  <AvatarFallback className="text-xs">
                    {activity.user ? getInitials(`${activity.user.first_name} ${activity.user.last_name}`) : 'S'}
                  </AvatarFallback>
                </Avatar>
                <span className="font-medium text-sm text-gray-900 dark:text-white">
                  {activity.user ? `${activity.user.first_name} ${activity.user.last_name}` : 'System'}
                </span>
                <Badge variant="outline" className="text-xs">
                  {activity.type.replace('_', ' ')}
                </Badge>
              </div>
              
              {/* Activity message */}
              {activity.type === 'field_change' && activity.field ? (
                <div className="mt-2">
                  <p className="text-sm text-gray-700 dark:text-gray-300">
                    Changed <span className="font-medium">{activity.field}</span>
                  </p>
                  <div className="flex items-center space-x-2 mt-1">
                    <span className="text-xs px-2 py-1 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded">
                      {formatFieldValue(activity.old_value)}
                    </span>
                    <ArrowRight className="w-3 h-3 text-gray-400" />
                    <span className="text-xs px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded">
                      {formatFieldValue(activity.new_value)}
                    </span>
                  </div>
                </div>
              ) : (
                <div className="mt-1">
                  {activity.message.split('\n').map((line, index) => (
                    <p key={index} className="text-sm text-gray-700 dark:text-gray-300">
                      {line}
                    </p>
                  ))}
                </div>
              )}
            </div>
            
            <span className="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap ml-4">
              {format(item.timestamp, 'h:mm a')}
            </span>
          </div>
        </div>
      </div>
    )
  }

  // Render activity item
  const renderActivityItem = (item: UnifiedActivityItem, isLast: boolean) => {
    if (item.type === 'communication' && item.communicationData) {
      return renderCommunicationCard(item, isLast)
    } else if (item.activityData) {
      return renderActivityCard(item, isLast)
    }
    return null
  }

  // Quick filter presets
  const applyQuickFilter = (preset: string) => {
    switch (preset) {
      case 'today':
        setDateRange({ start: new Date(), end: new Date() })
        break
      case 'week':
        const weekAgo = new Date()
        weekAgo.setDate(weekAgo.getDate() - 7)
        setDateRange({ start: weekAgo, end: new Date() })
        break
      case 'month':
        const monthAgo = new Date()
        monthAgo.setMonth(monthAgo.getMonth() - 1)
        setDateRange({ start: monthAgo, end: new Date() })
        break
      case 'all':
        setDateRange({ start: null, end: null })
        break
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header with filters */}
      <div className={cn(
        "border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800",
        density === 'compact' ? "p-3" : "p-4"
      )}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center space-x-2">
            <History className="w-5 h-5" />
            <span>Activity Timeline</span>
            {unifiedItems.length > 0 && (
              <Badge variant="secondary">{unifiedItems.length}</Badge>
            )}
          </h3>
          
          <div className="flex items-center space-x-2">
            {/* Density toggle */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm">
                  {density === 'comfortable' ? 'Comfortable' : 'Compact'}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => setDensity('comfortable')}>
                  <Check className={cn("w-4 h-4 mr-2", density === 'comfortable' ? 'opacity-100' : 'opacity-0')} />
                  Comfortable
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setDensity('compact')}>
                  <Check className={cn("w-4 h-4 mr-2", density === 'compact' ? 'opacity-100' : 'opacity-0')} />
                  Compact
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
            
            {/* Filter toggle */}
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowFilters(!showFilters)}
              className={cn(showFilters && "bg-gray-100 dark:bg-gray-700")}
            >
              <Filter className="w-4 h-4 mr-2" />
              Filters
              {(searchQuery || dateRange.start || dateRange.end || selectedTypes.size < 5 || selectedChannels.size < 3) && (
                <Badge variant="default" className="ml-2 px-1.5 py-0">
                  Active
                </Badge>
              )}
            </Button>
          </div>
        </div>
        
        {/* Expandable filter section */}
        {showFilters && (
          <div className="space-y-3 pt-3 border-t border-gray-200 dark:border-gray-700">
            {/* Search bar */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                type="text"
                placeholder="Search activities..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 pr-10"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2"
                >
                  <X className="w-4 h-4 text-gray-400 hover:text-gray-600" />
                </button>
              )}
            </div>
            
            {/* Activity type filters */}
            <div className="flex flex-wrap gap-2">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300 mr-2">Types:</span>
              {[
                { id: 'communication', label: 'Communications', icon: Mail },
                { id: 'field_change', label: 'Field Changes', icon: Edit },
                { id: 'stage_change', label: 'Stage Changes', icon: ArrowRight },
                { id: 'comment', label: 'Comments', icon: MessageSquare },
                { id: 'system', label: 'System', icon: Activity }
              ].map(type => (
                <label
                  key={type.id}
                  className="flex items-center space-x-1 cursor-pointer"
                >
                  <Checkbox
                    checked={selectedTypes.has(type.id)}
                    onCheckedChange={() => toggleTypeSelection(type.id)}
                  />
                  <type.icon className="w-3 h-3" />
                  <span className="text-sm">{type.label}</span>
                </label>
              ))}
            </div>
            
            {/* Channel filters - only show when communications are selected */}
            {selectedTypes.has('communication') && (
              <div className="flex flex-wrap gap-2">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300 mr-2">Channels:</span>
                {[
                  { id: 'email', label: 'Email', icon: Mail },
                  { id: 'whatsapp', label: 'WhatsApp', icon: MessageSquare },
                  { id: 'linkedin', label: 'LinkedIn', icon: Users }
                ].map(channel => (
                  <label
                    key={channel.id}
                    className="flex items-center space-x-1 cursor-pointer"
                  >
                    <Checkbox
                      checked={selectedChannels.has(channel.id)}
                      onCheckedChange={() => toggleChannelSelection(channel.id)}
                    />
                    <channel.icon className="w-3 h-3" />
                    <span className="text-sm">{channel.label}</span>
                  </label>
                ))}
              </div>
            )}
            
            {/* Date range quick filters */}
            <div className="flex items-center space-x-2">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Date:</span>
              <div className="flex space-x-1">
                <Button
                  variant={dateRange.start?.toDateString() === new Date().toDateString() ? "default" : "outline"}
                  size="sm"
                  onClick={() => applyQuickFilter('today')}
                >
                  Today
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => applyQuickFilter('week')}
                >
                  Last 7 days
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => applyQuickFilter('month')}
                >
                  Last 30 days
                </Button>
                <Button
                  variant={!dateRange.start && !dateRange.end ? "default" : "outline"}
                  size="sm"
                  onClick={() => applyQuickFilter('all')}
                >
                  All time
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Timeline content */}
      <ScrollArea className="flex-1" ref={scrollAreaRef}>
        <div className={cn(
          "space-y-6",
          density === 'compact' ? "p-4" : "p-6"
        )}>
          {/* Loading state */}
          {(isLoadingActivities || isLoadingCommunications) && unifiedItems.length === 0 && (
            <div className="space-y-4">
              <ActivitySkeleton />
              <ActivitySkeleton />
              <ActivitySkeleton />
            </div>
          )}
          
          {/* Timeline groups */}
          {Object.entries(groupedItems).map(([dateKey, items], groupIndex) => {
            const isCollapsed = collapsedGroups.has(dateKey)
            
            return (
              <div key={dateKey} className="relative">
                {/* Date header */}
                <div className="sticky top-0 z-20 -mx-6 px-6 py-2 bg-gray-50/95 dark:bg-gray-900/95 backdrop-blur-sm">
                  <button
                    onClick={() => toggleGroupCollapse(dateKey)}
                    className="flex items-center space-x-2 text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
                  >
                    {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    <CalendarDays className="w-4 h-4" />
                    <span>{formatDateHeader(dateKey)}</span>
                    <Badge variant="secondary" className="ml-2">
                      {items.length}
                    </Badge>
                  </button>
                </div>
                
                {/* Timeline items */}
                {!isCollapsed && (
                  <div className="space-y-4 mt-4">
                    {items.map((item, index) => (
                      <div key={item.id} className="relative">
                        {renderActivityItem(item, index === items.length - 1 && groupIndex === Object.keys(groupedItems).length - 1)}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )
          })}
          
          {/* Empty state */}
          {unifiedItems.length === 0 && !isLoadingActivities && !isLoadingCommunications && (
            <div className="flex flex-col items-center justify-center py-12">
              <div className="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mb-4">
                <History className="w-8 h-8 text-gray-400" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-1">
                No activity found
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 text-center max-w-sm">
                {searchQuery || dateRange.start || selectedTypes.size < 5 || selectedChannels.size < 3
                  ? "Try adjusting your filters to see more results"
                  : "Activities and communications will appear here"}
              </p>
              {(searchQuery || dateRange.start || selectedTypes.size < 5 || selectedChannels.size < 3) && (
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-4"
                  onClick={() => {
                    setSearchQuery('')
                    setDateRange({ start: null, end: null })
                    setSelectedTypes(new Set(['field_change', 'stage_change', 'comment', 'system', 'communication']))
                    setSelectedChannels(new Set(['email', 'whatsapp', 'linkedin']))
                  }}
                >
                  Clear filters
                </Button>
              )}
            </div>
          )}
          
          {/* Load more button */}
          {hasMoreCommunications && selectedTypes.has('communication') && (
            <div className="flex justify-center pt-4">
              <Button
                variant="outline"
                onClick={onLoadMoreCommunications}
                disabled={isLoadingCommunications}
              >
                {isLoadingCommunications ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Loading...
                  </>
                ) : (
                  <>
                    <Download className="w-4 h-4 mr-2" />
                    Load More
                  </>
                )}
              </Button>
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  )
}