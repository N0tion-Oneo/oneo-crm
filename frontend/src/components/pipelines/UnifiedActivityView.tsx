import React, { useState, useMemo } from 'react'
import { format, isToday, isYesterday, isSameDay } from 'date-fns'
import { 
  Mail, Phone, Users, MessageSquare, Calendar, 
  Edit, Plus, Trash2, Clock, History, 
  Filter, ChevronDown, ChevronRight, User,
  Send, ArrowDownLeft, ArrowUpRight, Activity
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
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

export function UnifiedActivityView({
  activities,
  communications,
  isLoadingActivities = false,
  isLoadingCommunications = false,
  onLoadMoreCommunications,
  hasMoreCommunications = false
}: UnifiedActivityViewProps) {
  const [expandedMessages, setExpandedMessages] = useState<Set<string>>(new Set())
  const [filter, setFilter] = useState<'all' | 'activities' | 'communications'>('all')

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

  // Merge and sort activities and communications
  const unifiedItems = useMemo(() => {
    const items: UnifiedActivityItem[] = []
    
    // Add activities
    if (filter !== 'communications') {
      activities.forEach(activity => {
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
    
    // Add communications
    if (filter !== 'activities') {
      communications.forEach(msg => {
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
    
    // Sort by timestamp (newest first)
    return items.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
  }, [activities, communications, filter])

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
    return format(date, 'MMMM d, yyyy')
  }

  // Get channel icon
  const getChannelIcon = (channelType: string) => {
    switch (channelType) {
      case 'email':
      case 'gmail':
      case 'outlook':
        return <Mail className="w-4 h-4" />
      case 'whatsapp':
        return <MessageSquare className="w-4 h-4" />
      case 'linkedin':
        return <Users className="w-4 h-4" />
      default:
        return <MessageSquare className="w-4 h-4" />
    }
  }

  // Get activity icon
  const getActivityIcon = (type: string, message?: string) => {
    switch (type) {
      case 'system':
        return message?.includes('created') ? 
          <Plus className="w-4 h-4 text-green-600 dark:text-green-400" /> :
          <Activity className="w-4 h-4 text-gray-600 dark:text-gray-400" />
      case 'field_change':
        return <Edit className="w-4 h-4 text-blue-600 dark:text-blue-400" />
      case 'stage_change':
        return <Trash2 className="w-4 h-4 text-red-600 dark:text-red-400" />
      case 'comment':
        return <Clock className="w-4 h-4 text-gray-600 dark:text-gray-400" />
      default:
        return <Activity className="w-4 h-4 text-gray-600 dark:text-gray-400" />
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

  // Strip HTML for preview
  const stripHtml = (html: string): string => {
    if (!html) return ''
    const tmp = document.createElement('div')
    tmp.innerHTML = html
    const text = tmp.textContent || tmp.innerText || ''
    return text.replace(/\s+/g, ' ').trim()
  }

  // Render activity item
  const renderActivityItem = (item: UnifiedActivityItem) => {
    if (item.type === 'communication' && item.communicationData) {
      const msg = item.communicationData
      const isExpanded = expandedMessages.has(item.id)
      const isEmail = msg.channel_type === 'email' || msg.channel_type === 'gmail'
      
      return (
        <div key={item.id} className="flex space-x-3">
          <div className="flex-shrink-0">
            <div className={cn(
              "w-8 h-8 rounded-full flex items-center justify-center",
              msg.direction === 'inbound' 
                ? "bg-blue-100 dark:bg-blue-900" 
                : "bg-green-100 dark:bg-green-900"
            )}>
              {getChannelIcon(msg.channel_type)}
            </div>
          </div>
          
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center space-x-2">
                  <span className="font-medium text-sm text-gray-900 dark:text-white">
                    {msg.sender_name || 'Unknown'}
                  </span>
                  <Badge variant="outline" className="text-xs">
                    {msg.channel_type}
                  </Badge>
                  {msg.direction === 'inbound' ? (
                    <ArrowDownLeft className="w-3 h-3 text-blue-500" />
                  ) : (
                    <ArrowUpRight className="w-3 h-3 text-green-500" />
                  )}
                </div>
                
                {isEmail && msg.subject && (
                  <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mt-1">
                    {msg.subject}
                  </p>
                )}
                
                {isEmail && msg.html_content ? (
                  <div className="mt-2">
                    <button
                      onClick={() => toggleMessageExpanded(item.id)}
                      className="flex items-center space-x-1 text-xs text-blue-600 dark:text-blue-400 hover:underline"
                    >
                      {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                      <span>{isExpanded ? 'Hide' : 'Show'} email content</span>
                    </button>
                    
                    {isExpanded && (
                      <div className="mt-2 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                        <div 
                          className="email-content text-sm"
                          dangerouslySetInnerHTML={{ 
                            __html: DOMPurify.sanitize(msg.html_content, {
                              ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'a', 'ul', 'ol', 'li', 'blockquote'],
                              ALLOWED_ATTR: ['href', 'target']
                            })
                          }}
                        />
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                    {stripHtml(msg.content).substring(0, 200)}
                    {stripHtml(msg.content).length > 200 && '...'}
                  </p>
                )}
              </div>
              
              <span className="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap ml-2">
                {format(item.timestamp, 'h:mm a')}
              </span>
            </div>
          </div>
        </div>
      )
    } else if (item.activityData) {
      const activity = item.activityData
      
      return (
        <div key={item.id} className="flex space-x-3">
          <div className="flex-shrink-0">
            <div className="w-8 h-8 bg-gray-200 dark:bg-gray-600 rounded-full flex items-center justify-center">
              {getActivityIcon(activity.type, activity.message)}
            </div>
          </div>
          
          <div className="flex-1 min-w-0">
            <div className="text-sm text-gray-900 dark:text-white">
              <span className="font-medium">
                {activity.user ? `${activity.user.first_name} ${activity.user.last_name}` : 'System'}
              </span>
              <div className="mt-1">
                {activity.message.split('\n').map((line, index) => (
                  <div key={index} className={index > 0 ? 'mt-1' : ''}>
                    {line}
                  </div>
                ))}
              </div>
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400 mt-2">
              {format(item.timestamp, 'h:mm a')}
            </div>
          </div>
        </div>
      )
    }
    
    return null
  }

  return (
    <div className="p-6">
      {/* Filter controls */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-gray-900 dark:text-white">
          Activity Timeline
        </h3>
        
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm">
              <Filter className="w-4 h-4 mr-2" />
              {filter === 'all' ? 'All Activity' : 
               filter === 'activities' ? 'Changes Only' : 'Communications Only'}
              <ChevronDown className="w-4 h-4 ml-2" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => setFilter('all')}>
              All Activity
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setFilter('activities')}>
              Changes Only
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setFilter('communications')}>
              Communications Only
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Timeline */}
      <div className="space-y-6">
        {Object.entries(groupedItems).map(([dateKey, items]) => (
          <div key={dateKey}>
            <div className="flex items-center mb-3">
              <div className="flex-1 border-t border-gray-200 dark:border-gray-700" />
              <span className="px-3 text-xs font-medium text-gray-500 dark:text-gray-400">
                {formatDateHeader(dateKey)}
              </span>
              <div className="flex-1 border-t border-gray-200 dark:border-gray-700" />
            </div>
            
            <div className="space-y-4">
              {items.map(item => renderActivityItem(item))}
            </div>
          </div>
        ))}
        
        {unifiedItems.length === 0 && (
          <div className="text-center py-8">
            <History className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-500 dark:text-gray-400">No activity yet</p>
          </div>
        )}
        
        {hasMoreCommunications && filter !== 'activities' && (
          <div className="text-center pt-4">
            <Button
              variant="outline"
              size="sm"
              onClick={onLoadMoreCommunications}
              disabled={isLoadingCommunications}
            >
              {isLoadingCommunications ? 'Loading...' : 'Load More'}
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}