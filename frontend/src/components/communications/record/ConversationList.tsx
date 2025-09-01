import React from 'react'
import { formatDistanceToNow } from 'date-fns'
import { Mail, Phone, Users, MessageSquare, User, AtSign, Briefcase, Hash, Circle } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'

interface Participant {
  id: string
  name: string
  display_name: string
  email: string
  phone: string
}

interface LastMessage {
  content: string
  direction: string
  sent_at: string
  sender_name: string
}

interface Conversation {
  id: string
  subject: string
  channel_name: string
  channel_type: string
  account_name?: string
  participants: Participant[]
  last_message: LastMessage | null
  last_message_at: string | null
  message_count: number
  unread_count: number
  status: string
  priority: string
}

interface ConversationListProps {
  conversations: Conversation[]
  selectedId: string | null
  onSelect: (id: string) => void
}

export function ConversationList({
  conversations,
  selectedId,
  onSelect
}: ConversationListProps) {
  // Strip HTML tags and decode entities for message preview
  const stripHtml = (html: string): string => {
    if (!html) return ''
    
    // Create a temporary div to parse HTML
    const tmp = document.createElement('div')
    tmp.innerHTML = html
    
    // Get text content which automatically strips tags and decodes entities
    const text = tmp.textContent || tmp.innerText || ''
    
    // Clean up extra whitespace
    return text.replace(/\s+/g, ' ').trim()
  }
  
  const getChannelConfig = (channelType: string) => {
    switch (channelType) {
      case 'email':
      case 'gmail':
      case 'outlook':
      case 'office365':
        return {
          icon: <Mail className="w-4 h-4" />,
          color: 'text-blue-600 dark:text-blue-400',
          bgColor: 'bg-blue-50 dark:bg-blue-900/20',
          borderColor: 'border-blue-200 dark:border-blue-800',
          label: 'Email'
        }
      case 'whatsapp':
        return {
          icon: <MessageSquare className="w-4 h-4" />,
          color: 'text-green-600 dark:text-green-400',
          bgColor: 'bg-green-50 dark:bg-green-900/20',
          borderColor: 'border-green-200 dark:border-green-800',
          label: 'WhatsApp'
        }
      case 'linkedin':
        return {
          icon: <Briefcase className="w-4 h-4" />,
          color: 'text-indigo-600 dark:text-indigo-400',
          bgColor: 'bg-indigo-50 dark:bg-indigo-900/20',
          borderColor: 'border-indigo-200 dark:border-indigo-800',
          label: 'LinkedIn'
        }
      default:
        return {
          icon: <MessageSquare className="w-4 h-4" />,
          color: 'text-gray-600 dark:text-gray-400',
          bgColor: 'bg-gray-50 dark:bg-gray-900/20',
          borderColor: 'border-gray-200 dark:border-gray-800',
          label: channelType
        }
    }
  }

  const getParticipantDisplay = (participants: Participant[]) => {
    if (participants.length === 0) return 'Unknown'
    if (participants.length === 1) return participants[0].display_name
    return `${participants[0].display_name} +${participants.length - 1}`
  }

  const getInitials = (name: string) => {
    if (!name || name === 'Unknown') return '?'
    const parts = name.split(' ')
    if (parts.length >= 2) {
      return `${parts[0][0]}${parts[1][0]}`.toUpperCase()
    }
    return name.slice(0, 2).toUpperCase()
  }

  if (conversations.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-500">
        <MessageSquare className="w-8 h-8 mb-2" />
        <p className="text-sm">No conversations yet</p>
      </div>
    )
  }

  return (
    <div className="divide-y divide-gray-100 dark:divide-gray-800">
      {conversations.map((conversation) => {
        const channelConfig = getChannelConfig(conversation.channel_type)
        const primaryParticipant = conversation.participants[0]
        const participantName = primaryParticipant?.display_name || 'Unknown'
        const isEmail = conversation.channel_type === 'email' || conversation.channel_type === 'gmail'
        
        return (
          <div
            key={conversation.id}
            onClick={() => onSelect(conversation.id)}
            className={cn(
              "relative px-4 py-3 cursor-pointer transition-colors duration-150 overflow-hidden",
              "hover:bg-gray-50 dark:hover:bg-gray-800/50",
              selectedId === conversation.id 
                ? "bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-500"
                : "border-l-4 border-transparent"
            )}
          >
            <div className="flex items-start space-x-3 overflow-hidden">
              {/* Channel icon instead of avatar for cleaner look */}
              <div className={cn(
                "flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center mt-0.5",
                channelConfig.bgColor
              )}>
                <div className={channelConfig.color}>
                  {channelConfig.icon}
                </div>
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0 overflow-hidden">
                {/* Header row */}
                <div className="flex items-start justify-between gap-2 mb-0.5">
                  <div className="flex-1 min-w-0">
                    <h4 className="text-sm font-medium text-gray-900 dark:text-white truncate">
                      {getParticipantDisplay(conversation.participants)}
                    </h4>
                    <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                      {conversation.channel_name}
                    </p>
                  </div>
                  <span className="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap flex-shrink-0">
                    {conversation.last_message_at && 
                      formatDistanceToNow(new Date(conversation.last_message_at), { 
                        addSuffix: false 
                      })
                    }
                  </span>
                </div>

                {/* Subject for emails or last message for chats */}
                {isEmail && conversation.subject ? (
                  <div className="text-sm font-medium text-gray-700 dark:text-gray-300 break-words whitespace-normal max-h-10 overflow-hidden">
                    {conversation.subject}
                  </div>
                ) : null}

                {/* Last message preview */}
                {conversation.last_message && (
                  <p className={cn(
                    "text-sm truncate",
                    conversation.unread_count > 0 
                      ? "text-gray-900 dark:text-gray-100 font-medium" 
                      : "text-gray-600 dark:text-gray-400"
                  )}>
                    {conversation.last_message.direction === 'outbound' && 'You: '}
                    {stripHtml(conversation.last_message.content)}
                  </p>
                )}

                {/* Unread badge */}
                {conversation.unread_count > 0 && (
                  <div className="mt-1">
                    <Badge variant="default" className="h-5 px-1.5 text-xs">
                      {conversation.unread_count} new
                    </Badge>
                  </div>
                )}
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}