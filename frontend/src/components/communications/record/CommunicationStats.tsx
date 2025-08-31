import React from 'react'
import { MessageSquare, Mail, Clock, Users } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

interface CommunicationStats {
  total_conversations: number
  total_messages: number
  total_unread: number
  last_activity: string | null
  channels: string[]
  participants_count: number
}

interface CommunicationStatsProps {
  stats: CommunicationStats | null
}

export function CommunicationStats({ stats }: CommunicationStatsProps) {
  if (!stats) {
    return null
  }

  const statItems = [
    {
      icon: <MessageSquare className="w-4 h-4" />,
      label: 'Conversations',
      value: stats.total_conversations
    },
    {
      icon: <Mail className="w-4 h-4" />,
      label: 'Messages',
      value: stats.total_messages
    },
    {
      icon: <Users className="w-4 h-4" />,
      label: 'Participants',
      value: stats.participants_count
    }
  ]

  return (
    <div className="flex items-center space-x-6">
      {/* Main stats */}
      {statItems.map((item, index) => (
        <div key={index} className="flex items-center space-x-2">
          <div className="text-gray-500 dark:text-gray-400">
            {item.icon}
          </div>
          <div>
            <p className="text-2xl font-semibold text-gray-900 dark:text-white">
              {item.value}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {item.label}
            </p>
          </div>
        </div>
      ))}

      {/* Unread badge */}
      {stats.total_unread > 0 && (
        <div className="flex items-center space-x-2">
          <div className="relative">
            <Mail className="w-5 h-5 text-red-500" />
            <span className="absolute -top-2 -right-2 bg-red-500 text-white text-xs rounded-full px-1.5 py-0.5">
              {stats.total_unread}
            </span>
          </div>
          <span className="text-sm text-gray-600 dark:text-gray-400">
            Unread
          </span>
        </div>
      )}

      {/* Last activity */}
      {stats.last_activity && (
        <div className="flex items-center space-x-2 text-sm text-gray-500 dark:text-gray-400">
          <Clock className="w-4 h-4" />
          <span>
            Last activity {formatDistanceToNow(new Date(stats.last_activity), { addSuffix: true })}
          </span>
        </div>
      )}

      {/* Active channels */}
      {stats.channels.length > 0 && (
        <div className="flex items-center space-x-2">
          <span className="text-xs text-gray-500 dark:text-gray-400">
            Active channels:
          </span>
          <div className="flex space-x-1">
            {stats.channels.map((channel) => (
              <span
                key={channel}
                className="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-800 rounded"
              >
                {channel}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}