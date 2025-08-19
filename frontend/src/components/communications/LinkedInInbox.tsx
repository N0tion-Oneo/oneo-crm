'use client'

import React, { useState, useEffect } from 'react'
import { MessageSquare, Search, Filter, UserPlus, ExternalLink, MoreVertical, Send, ThumbsUp } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ScrollArea } from '@/components/ui/scroll-area'
import { SafeAvatar } from '@/components/communications/SafeAvatar'
import { useToast } from '@/hooks/use-toast'
import { MessageContent } from '@/components/MessageContent'
import { formatDistanceToNow } from 'date-fns'

// Based on Unipile LinkedIn Chat/Messaging API with LinkedIn-specific features
interface LinkedInMessage {
  id: string
  text?: string
  html?: string
  type: 'text' | 'inmail' | 'connection_request' | 'recommendation'
  direction: 'in' | 'out'
  chat_id: string
  date: string
  status: 'sent' | 'delivered' | 'read' | 'failed'
  attendee_id?: string
  is_inmail: boolean  // Premium InMail message
  inmail_credits_used?: number
  connection_request_id?: string  // If it's a connection request
  quoted_message_id?: string
  account_id: string
  linkedin_metadata?: {
    thread_id: string
    conversation_type: 'message' | 'inmail' | 'connection_request'
    premium_features_used: string[]
  }
}

// LinkedIn Chat with professional networking context
interface LinkedInChat {
  id: string
  provider_chat_id: string
  name?: string
  is_group: boolean  // Usually false for LinkedIn
  is_muted: boolean
  unread_count: number
  last_message_date: string
  account_id: string
  attendees: LinkedInAttendee[]
  latest_message?: LinkedInMessage
  conversation_type: 'message' | 'inmail' | 'connection_request'
  inmail_thread: boolean  // If this uses InMail credits
}

// LinkedIn-specific attendee with professional info
interface LinkedInAttendee {
  id: string
  name?: string
  profile_url?: string
  picture_url?: string
  linkedin_id: string  // LinkedIn member ID
  connection_level: '1st' | '2nd' | '3rd' | 'Out of network'
  title?: string
  company?: string
  location?: string
  industry?: string
  mutual_connections?: number
  is_premium: boolean
  is_recruiter: boolean
  is_hiring_manager: boolean
  account_id: string
}

// Available from /api/v1/linkedin/inmail_balance
interface InMailBalance {
  available_credits: number
  monthly_limit: number
  reset_date: string
  premium_account: boolean
}

interface LinkedInInboxProps {
  className?: string
}

export default function LinkedInInbox({ className }: LinkedInInboxProps) {
  const [chats, setChats] = useState<LinkedInChat[]>([])
  const [selectedChat, setSelectedChat] = useState<LinkedInChat | null>(null)
  const [attendees, setAttendees] = useState<LinkedInAttendee[]>([])
  const [messages, setMessages] = useState<LinkedInMessage[]>([])
  const [inmailBalance, setInmailBalance] = useState<InMailBalance | null>(null)
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterStatus, setFilterStatus] = useState<'all' | 'unread' | 'connections' | 'inmessages' | 'connection_requests'>('all')
  const [accountConnections, setAccountConnections] = useState<Array<{
    id: string
    provider: 'linkedin'
    email: string
    profile_url: string
    premium: boolean
    recruiter: boolean
    status: 'active' | 'error' | 'syncing'
  }>>([])
  const [replyText, setReplyText] = useState('')
  const [composing, setComposing] = useState(false)
  const { toast } = useToast()

  // Mock data based on actual Unipile LinkedIn API structure
  useEffect(() => {
    const mockConnections = [
      { 
        id: 'acc_li_1', 
        provider: 'linkedin' as const, 
        email: 'you@linkedin.com', 
        profile_url: 'https://linkedin.com/in/you',
        premium: true,
        recruiter: false,
        status: 'active' as const 
      }
    ]
    
    // Mock InMail balance from /api/v1/linkedin/inmail_balance
    const mockInmailBalance: InMailBalance = {
      available_credits: 15,
      monthly_limit: 30,
      reset_date: new Date(Date.now() + 15 * 24 * 60 * 60 * 1000).toISOString(),
      premium_account: true
    }
    
    // Mock LinkedIn attendees with professional data
    const mockAttendees: LinkedInAttendee[] = [
      {
        id: 'att_li_1',
        name: 'Emily Rodriguez',
        linkedin_id: 'emily-rodriguez-pm',
        profile_url: 'https://linkedin.com/in/emily-rodriguez',
        connection_level: '1st',
        title: 'Senior Product Manager',
        company: 'TechCorp Inc.',
        location: 'San Francisco Bay Area',
        industry: 'Technology',
        mutual_connections: 12,
        is_premium: false,
        is_recruiter: false,
        is_hiring_manager: true,
        account_id: 'acc_li_1'
      },
      {
        id: 'att_li_2',
        name: 'David Chen',
        linkedin_id: 'david-chen-ai',
        profile_url: 'https://linkedin.com/in/david-chen-ai',
        connection_level: '2nd',
        title: 'Startup Founder',
        company: 'InnovateAI',
        location: 'New York',
        industry: 'Artificial Intelligence',
        mutual_connections: 5,
        is_premium: true,
        is_recruiter: false,
        is_hiring_manager: false,
        account_id: 'acc_li_1'
      }
    ]
    
    // Simulate loading LinkedIn chats
    const mockChats: LinkedInChat[] = [
      {
        id: 'chat_li_1',
        provider_chat_id: 'li_thread_123',
        name: 'Emily Rodriguez',
        is_group: false,
        is_muted: false,
        unread_count: 1,
        last_message_date: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
        account_id: 'acc_li_1',
        attendees: [
          {
            id: 'att_li_1',
            name: 'Emily Rodriguez',
            linkedin_id: 'emily-rodriguez-pm',
            profile_url: 'https://linkedin.com/in/emily-rodriguez',
            connection_level: '1st',
            title: 'Senior Product Manager',
            company: 'TechCorp Inc.',
            mutual_connections: 12,
            is_premium: false,
            is_recruiter: false,
            is_hiring_manager: true,
            account_id: 'acc_li_1'
          }
        ],
        latest_message: {
          id: 'msg_li_1',
          text: 'Hi! I came across your profile and was impressed by your experience in product development. Would love to connect and potentially discuss some opportunities.',
          type: 'text',
          direction: 'in',
          chat_id: 'chat_li_1',
          date: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
          status: 'delivered',
          attendee_id: 'att_li_1',
          is_inmail: false,
          account_id: 'acc_li_1',
          linkedin_metadata: {
            thread_id: 'li_thread_123',
            conversation_type: 'message',
            premium_features_used: []
          }
        },
        conversation_type: 'message',
        inmail_thread: false
      },
      {
        id: 'chat_li_2',
        provider_chat_id: 'li_thread_456',
        name: 'David Chen',
        is_group: false,
        is_muted: false,
        unread_count: 0,
        last_message_date: new Date(Date.now() - 1.5 * 60 * 60 * 1000).toISOString(),
        account_id: 'acc_li_1',
        attendees: [
          {
            id: 'att_li_2',
            name: 'David Chen',
            linkedin_id: 'david-chen-ai',
            profile_url: 'https://linkedin.com/in/david-chen-ai',
            connection_level: '2nd',
            title: 'Startup Founder',
            company: 'InnovateAI',
            mutual_connections: 5,
            is_premium: true,
            is_recruiter: false,
            is_hiring_manager: false,
            account_id: 'acc_li_1'
          }
        ],
        latest_message: {
          id: 'msg_li_3',
          text: 'Absolutely! We\'re always looking for talented individuals. Are you open to exploring new opportunities?',
          type: 'text',
          direction: 'in',
          chat_id: 'chat_li_2',
          date: new Date(Date.now() - 1.5 * 60 * 60 * 1000).toISOString(),
          status: 'read',
          attendee_id: 'att_li_2',
          is_inmail: false,
          account_id: 'acc_li_1',
          linkedin_metadata: {
            thread_id: 'li_thread_456',
            conversation_type: 'message',
            premium_features_used: []
          }
        },
        conversation_type: 'message',
        inmail_thread: false
      },
      {
        id: 'chat_li_3',
        provider_chat_id: 'li_inmail_789',
        name: 'Sarah Thompson',
        is_group: false,
        is_muted: false,
        unread_count: 0,
        last_message_date: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(),
        account_id: 'acc_li_1',
        attendees: [
          {
            id: 'att_li_3',
            name: 'Sarah Thompson',
            linkedin_id: 'sarah-thompson-recruiter',
            profile_url: 'https://linkedin.com/in/sarah-thompson-recruiter',
            connection_level: 'Out of network',
            title: 'Recruiter',
            company: 'Global Talent Solutions',
            mutual_connections: 0,
            is_premium: true,
            is_recruiter: true,
            is_hiring_manager: true,
            account_id: 'acc_li_1'
          }
        ],
        latest_message: {
          id: 'msg_li_4',
          text: 'Hello! I have an exciting senior developer position that would be perfect for your background. Would you be interested in hearing more?',
          type: 'inmail',
          direction: 'in',
          chat_id: 'chat_li_3',
          date: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(),
          status: 'read',
          attendee_id: 'att_li_3',
          is_inmail: true,
          inmail_credits_used: 1,
          account_id: 'acc_li_1',
          linkedin_metadata: {
            thread_id: 'li_inmail_789',
            conversation_type: 'inmail',
            premium_features_used: ['inmail']
          }
        },
        conversation_type: 'inmail',
        inmail_thread: true
      }
    ]

    setTimeout(() => {
      setAccountConnections(mockConnections)
      setInmailBalance(mockInmailBalance)
      setAttendees(mockAttendees)
      setChats(mockChats)
      setLoading(false)
    }, 1000)
  }, [])

  const filteredChats = chats.filter(chat => {
    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      const attendee = chat.attendees[0]
      if (!attendee?.name?.toLowerCase().includes(query) &&
          !attendee?.company?.toLowerCase().includes(query) &&
          !chat.latest_message?.text?.toLowerCase().includes(query)) {
        return false
      }
    }

    // Apply status filter
    switch (filterStatus) {
      case 'unread':
        return chat.unread_count > 0
      case 'connections':
        return chat.attendees[0]?.connection_level === '1st'
      case 'inmessages':
        return chat.conversation_type === 'inmail'
      case 'connection_requests':
        return chat.conversation_type === 'connection_request'
      default:
        return true
    }
  })

  const handleChatSelect = async (chat: LinkedInChat) => {
    setSelectedChat(chat)
    
    // Load messages for this chat
    const mockMessages: LinkedInMessage[] = [
      chat.latest_message!
    ]
    setMessages(mockMessages)
    
    // Mark as read if needed
    if (chat.unread_count > 0) {
      setChats(prev => prev.map(c =>
        c.id === chat.id ? { ...c, unread_count: 0 } : c
      ))
    }
  }

  const handleSendMessage = async () => {
    if (!selectedChat || !replyText.trim() || composing) return

    setComposing(true)
    try {
      // Check if this requires InMail credits
      const needsInmail = selectedChat.attendees[0]?.connection_level === 'Out of network'
      
      const newMessage: LinkedInMessage = {
        id: `msg_${Date.now()}`,
        text: replyText.trim(),
        type: needsInmail ? 'inmail' : 'text',
        direction: 'out',
        chat_id: selectedChat.id,
        date: new Date().toISOString(),
        status: 'sent',
        is_inmail: needsInmail,
        inmail_credits_used: needsInmail ? 1 : 0,
        account_id: selectedChat.account_id,
        linkedin_metadata: {
          thread_id: selectedChat.provider_chat_id,
          conversation_type: needsInmail ? 'inmail' : 'message',
          premium_features_used: needsInmail ? ['inmail'] : []
        }
      }

      // Add to messages
      setMessages(prev => [...prev, newMessage])

      // Update chat
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

      // Update InMail balance if used
      if (needsInmail && inmailBalance) {
        setInmailBalance(prev => prev ? {
          ...prev,
          available_credits: prev.available_credits - 1
        } : null)
      }

      setReplyText('')
      toast({
        title: "Message sent",
        description: needsInmail ? "Your LinkedIn InMail has been sent successfully." : "Your LinkedIn message has been sent successfully.",
      })
    } catch (error) {
      toast({
        title: "Failed to send message",
        description: "An error occurred while sending your message.",
        variant: "destructive",
      })
    } finally {
      setComposing(false)
    }
  }

  const getConnectionLevelColor = (level: string) => {
    switch (level) {
      case '1st': return 'text-green-600 bg-green-50'
      case '2nd': return 'text-blue-600 bg-blue-50'
      case '3rd': return 'text-orange-600 bg-orange-50'
      default: return 'text-gray-600 bg-gray-50'
    }
  }

  const getConversationTypeIcon = (type: string) => {
    switch (type) {
      case 'inmessage': return '💼'
      case 'connection_request': return '🤝'
      default: return '💬'
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        <p className="ml-4 text-gray-600">Loading LinkedIn conversations...</p>
      </div>
    )
  }

  return (
    <div className={`h-full flex flex-col ${className}`}>
      {/* Filters */}
      <div className="p-4 border-b bg-white dark:bg-gray-900">
        <div className="flex items-center space-x-4">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <Input
                placeholder="Search LinkedIn conversations..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>
          
          <Select value={filterStatus} onValueChange={(value: any) => setFilterStatus(value)}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Filter" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="unread">Unread</SelectItem>
              <SelectItem value="connections">1st Connections</SelectItem>
              <SelectItem value="inmessages">InMail</SelectItem>
              <SelectItem value="connection_requests">Connection Requests</SelectItem>
            </SelectContent>
          </Select>

          <div className="flex items-center gap-2">
            {accountConnections.map(conn => (
              <Badge key={conn.id} variant="outline" className="bg-blue-50 text-blue-700">
                <MessageSquare className="w-3 h-3 mr-1" />
                {conn.email} {conn.premium && '(Premium)'}
              </Badge>
            ))}
            {inmailBalance && (
              <Badge variant="outline" className="bg-yellow-50 text-yellow-700">
                InMail: {inmailBalance.available_credits}/{inmailBalance.monthly_limit}
              </Badge>
            )}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 grid grid-cols-12 gap-0 overflow-hidden">
        {/* Conversation List */}
        <div className="col-span-4 border-r bg-white dark:bg-gray-900">
          <ScrollArea className="h-full">
            {filteredChats.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <MessageSquare className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                <p>No LinkedIn conversations found</p>
              </div>
            ) : (
              <div className="space-y-0">
                {filteredChats.map((chat) => (
                  <div
                    key={chat.id}
                    className={`p-4 cursor-pointer border-b hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors ${
                      selectedChat?.id === chat.id ? 'bg-blue-50 dark:bg-blue-900/20 border-l-4 border-l-blue-600' : ''
                    }`}
                    onClick={() => handleChatSelect(chat)}
                  >
                    <div className="flex items-start space-x-3">
                      <SafeAvatar
                        src={chat.attendees[0]?.picture_url}
                        fallbackText={chat.attendees[0]?.name?.charAt(0) || 'L'}
                        className="w-12 h-12"
                        fallbackClassName="bg-blue-100 text-blue-700 font-semibold"
                      />
                      
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-1">
                          <div className="flex items-center gap-2">
                            <h3 className={`text-sm font-medium truncate ${
                              chat.unread_count > 0 ? 'font-bold' : ''
                            }`}>
                              {chat.attendees[0]?.name || 'Unknown'}
                            </h3>
                            <span className="text-lg">{getConversationTypeIcon(chat.conversation_type)}</span>
                          </div>
                          <div className="flex items-center gap-1 flex-shrink-0 ml-2">
                            <span className="text-xs text-gray-500">
                              {formatDistanceToNow(new Date(chat.last_message_date))}
                            </span>
                            {chat.unread_count > 0 && (
                              <Badge variant="destructive" className="text-xs ml-1">
                                {chat.unread_count}
                              </Badge>
                            )}
                          </div>
                        </div>
                        
                        <div className="flex items-center gap-2 mb-2">
                          <Badge 
                            variant="outline" 
                            className={`text-xs ${getConnectionLevelColor(chat.attendees[0]?.connection_level || 'Out of network')}`}
                          >
                            {chat.attendees[0]?.connection_level || 'Out of network'}
                          </Badge>
                          {chat.conversation_type === 'inmail' && (
                            <Badge variant="outline" className="text-xs bg-yellow-50 text-yellow-700">
                              InMail
                            </Badge>
                          )}
                        </div>
                        
                        <p className="text-xs text-gray-600 truncate mb-1">
                          {chat.attendees[0]?.title || 'No title'}
                          {chat.attendees[0]?.company && ` at ${chat.attendees[0].company}`}
                        </p>

                        {chat.attendees[0]?.mutual_connections && chat.attendees[0].mutual_connections > 0 && (
                          <p className="text-xs text-gray-500 mb-2">
                            {chat.attendees[0].mutual_connections} mutual connections
                          </p>
                        )}
                        
                        {/* Last message preview */}
                        <p className={`text-xs text-gray-600 truncate ${
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
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </ScrollArea>
        </div>

        {/* Message View */}
        <div className="col-span-8 bg-gray-50 dark:bg-gray-900 flex flex-col">
          {selectedChat ? (
            <>
              {/* Message Header */}
              <div className="p-4 bg-white dark:bg-gray-800 border-b">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <SafeAvatar
                      src={selectedChat.attendees[0]?.picture_url}
                      fallbackText={selectedChat.attendees[0]?.name?.charAt(0) || 'L'}
                      className="w-12 h-12"
                      fallbackClassName="bg-blue-100 text-blue-700 font-semibold"
                    />
                    <div>
                      <div className="flex items-center gap-2">
                        <h2 className="font-semibold">{selectedChat.attendees[0]?.name || 'Unknown'}</h2>
                        <Badge 
                          variant="outline" 
                          className={`text-xs ${getConnectionLevelColor(selectedChat.attendees[0]?.connection_level || 'Out of network')}`}
                        >
                          {selectedChat.attendees[0]?.connection_level || 'Out of network'}
                        </Badge>
                      </div>
                      <p className="text-sm text-gray-600">
                        {selectedChat.attendees[0]?.title || 'No title'}
                        {selectedChat.attendees[0]?.company && ` at ${selectedChat.attendees[0].company}`}
                      </p>
                      {selectedChat.attendees[0]?.mutual_connections && selectedChat.attendees[0].mutual_connections > 0 && (
                        <p className="text-xs text-gray-500">
                          {selectedChat.attendees[0].mutual_connections} mutual connections
                        </p>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <Button variant="ghost" size="sm" asChild>
                      <a href={selectedChat.attendees[0]?.profile_url} target="_blank" rel="noopener noreferrer">
                        <ExternalLink className="w-4 h-4" />
                      </a>
                    </Button>
                    {selectedChat.attendees[0]?.connection_level !== '1st' && (
                      <Button variant="ghost" size="sm">
                        <UserPlus className="w-4 h-4" />
                      </Button>
                    )}
                    <Button variant="ghost" size="sm">
                      <MoreVertical className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </div>

              {/* Messages */}
              <ScrollArea className="flex-1 p-4">
                <div className="space-y-4">
                  {messages.map((message) => (
                    <div
                      key={message.id}
                      className={`flex ${message.direction === 'out' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`max-w-lg rounded-lg px-4 py-3 ${
                          message.direction === 'out'
                            ? 'bg-blue-600 text-white ml-12'
                            : 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white mr-12 shadow-sm border'
                        }`}
                      >
                        {/* Message content */}
                        <div className="text-sm leading-relaxed">
                          {message.text ? (
                            <MessageContent
                              content={message.text}
                              isEmail={false}
                            />
                          ) : message.html ? (
                            <MessageContent
                              content={message.html}
                              isEmail={true}
                            />
                          ) : (
                            <div className="text-gray-500 italic">
                              {message.type} message
                            </div>
                          )}
                          
                          {message.is_inmail && (
                            <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-800">
                              💼 InMail message ({message.inmail_credits_used} credit{message.inmail_credits_used !== 1 ? 's' : ''} used)
                            </div>
                          )}
                        </div>

                        {/* Timestamp and status */}
                        <div className="flex items-center justify-between mt-2">
                          <div
                            className={`text-xs ${
                              message.direction === 'out'
                                ? 'text-blue-100'
                                : 'text-gray-500 dark:text-gray-400'
                            }`}
                          >
                            {new Date(message.date).toLocaleString([], {
                              month: 'short',
                              day: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit'
                            })}
                          </div>
                          {message.direction === 'out' && (
                            <div className={`text-xs ${
                              message.status === 'read' ? 'text-blue-400' :
                              message.status === 'delivered' ? 'text-gray-400' :
                              message.status === 'sent' ? 'text-gray-300' : 'text-red-400'
                            }`}>
                              {message.status === 'read' ? '✓ Read' :
                               message.status === 'delivered' ? '✓ Delivered' :
                               message.status === 'sent' ? '✓ Sent' : '❌ Failed'}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>

              {/* Message Input */}
              <div className="p-4 bg-white dark:bg-gray-800 border-t">
                {selectedChat.conversation_type === 'inmail' && (
                  <div className="mb-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-yellow-800 text-sm">
                        <span>💼</span>
                        <span>This is an InMail conversation - premium feature</span>
                      </div>
                      {inmailBalance && (
                        <div className="text-xs text-yellow-600">
                          {inmailBalance.available_credits} credits remaining
                        </div>
                      )}
                    </div>
                  </div>
                )}
                
                <div className="flex items-end space-x-2">
                  <Textarea
                    placeholder="Write a professional message..."
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
                  <div className="flex flex-col gap-2">
                    <Button
                      onClick={handleSendMessage}
                      disabled={!replyText.trim() || composing}
                      className="bg-blue-600 hover:bg-blue-700 text-white"
                      size="sm"
                    >
                      <Send className="w-4 h-4" />
                    </Button>
                    <Button variant="ghost" size="sm">
                      <ThumbsUp className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="h-full flex items-center justify-center">
              <div className="text-center text-gray-500">
                <MessageSquare className="w-16 h-16 mx-auto mb-4 text-gray-300" />
                <h3 className="text-lg font-medium mb-2">Select a conversation to start messaging</h3>
                <p>Choose a LinkedIn conversation from the left to view professional messages</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}