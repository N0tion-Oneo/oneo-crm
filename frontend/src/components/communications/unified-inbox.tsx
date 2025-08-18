"use client"

import React, { useState, useEffect, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
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
  Send,
  Search,
  Filter,
  MoreVertical,
  Star,
  Archive,
  Users,
  TrendingUp,
  Clock,
  CheckCircle2,
  AlertCircle,
  Plus
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { useUnifiedInbox } from '@/hooks/use-unified-inbox'
import ConversationTimeline from './conversation-timeline'
import CommunicationAnalytics from './communication-analytics'
import SmartCompose from './smart-compose'

// Types
interface Record {
  id: number
  title: string
  pipeline_name: string
  total_unread: number
  last_activity: string
  preferred_channel: string
  channels: Record<string, ChannelSummary>
  available_channels: string[]
}

interface ChannelSummary {
  channel_type: string
  conversation_count: number
  message_count: number
  unread_count: number
  last_activity: string
  last_message_preview: string
  threading_info: {
    has_threads: boolean
    thread_groups: Array<{
      id: string
      type: string
      strategy: string
      conversations: number
    }>
  }
}

interface ChannelAvailability {
  channel_type: string
  display_name: string
  status: 'available' | 'limited' | 'historical' | 'unavailable'
  user_connected: boolean
  contact_info_available: boolean
  has_history: boolean
  priority: number
  limitations: string[]
  history?: {
    total_messages: number
    last_contact: string
    response_rate: number
    engagement_score: number
  }
}

interface UnifiedInboxData {
  records: Record[]
  total_count: number
  has_next: boolean
  has_previous: boolean
  current_page: number
  total_pages: number
}

export default function UnifiedInbox() {
  const router = useRouter()
  const [searchQuery, setSearchQuery] = useState('')
  const [activeTab, setActiveTab] = useState('all')
  const [showFilters, setShowFilters] = useState(false)
  const [showCompose, setShowCompose] = useState(false)

  // Handle escape key to close compose dialog
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && showCompose) {
        setShowCompose(false)
      }
    }
    
    if (showCompose) {
      document.addEventListener('keydown', handleEscape)
      return () => document.removeEventListener('keydown', handleEscape)
    }
  }, [showCompose])

  // Use unified inbox hook
  const {
    inboxData,
    selectedRecord,
    channelAvailability,
    loading,
    loadingChannels,
    fetchInbox,
    selectRecord,
    refreshRecord,
    markAsRead,
    isConnected,
    error
  } = useUnifiedInbox()

  // Filter records based on search and tab
  const filteredRecords = useMemo(() => {
    if (!inboxData) return []
    
    let filtered = inboxData.records
    
    // Search filter
    if (searchQuery) {
      filtered = filtered.filter(record => 
        record.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        record.pipeline_name.toLowerCase().includes(searchQuery.toLowerCase())
      )
    }
    
    // Tab filter
    switch (activeTab) {
      case 'unread':
        filtered = filtered.filter(record => record.total_unread > 0)
        break
      case 'recent':
        filtered = filtered.filter(record => {
          const lastActivity = new Date(record.last_activity)
          const oneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000)
          return lastActivity > oneDayAgo
        })
        break
      default:
        // 'all' - no additional filtering
        break
    }
    
    return filtered
  }, [inboxData, searchQuery, activeTab])

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

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'available': return 'text-green-600 bg-green-50 border-green-200'
      case 'limited': return 'text-yellow-600 bg-yellow-50 border-yellow-200'
      case 'historical': return 'text-blue-600 bg-blue-50 border-blue-200'
      default: return 'text-gray-600 bg-gray-50 border-gray-200'
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="flex h-full">
      {/* Left Panel - Record List */}
      <div className="w-1/3 border-r bg-white">
        <div className="p-4 border-b">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Unified Inbox</h2>
            <Button size="sm" variant="outline" onClick={() => setShowFilters(!showFilters)}>
              <Filter className="h-4 w-4" />
            </Button>
          </div>
          
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              placeholder="Search contacts..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          
          {/* Tabs */}
          <Tabs value={activeTab} onValueChange={setActiveTab} className="mt-4">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="all">All</TabsTrigger>
              <TabsTrigger value="unread">Unread</TabsTrigger>
              <TabsTrigger value="recent">Recent</TabsTrigger>
            </TabsList>
          </Tabs>
        </div>

        {/* Records List */}
        <ScrollArea className="flex-1">
          <div className="p-2">
            {filteredRecords.map((record) => (
              <Card 
                key={record.id}
                className={`mb-2 cursor-pointer transition-colors hover:bg-gray-50 ${
                  selectedRecord?.id === record.id ? 'ring-2 ring-blue-500' : ''
                }`}
                onClick={() => selectRecord(record)}
              >
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-medium text-sm">{record.title}</h3>
                        {record.total_unread > 0 && (
                          <Badge variant="destructive" className="text-xs">
                            {record.total_unread}
                          </Badge>
                        )}
                      </div>
                      
                      <p className="text-xs text-gray-500 mb-2">{record.pipeline_name}</p>
                      
                      {/* Channel indicators */}
                      <div className="flex items-center gap-1 mb-2">
                        {record.available_channels.map((channelType) => (
                          <div 
                            key={channelType}
                            className={`p-1 rounded-full text-white ${getChannelColor(channelType)}`}
                            title={channelType}
                          >
                            {getChannelIcon(channelType)}
                          </div>
                        ))}
                      </div>
                      
                      {/* Last activity */}
                      <div className="flex items-center gap-1 text-xs text-gray-400">
                        <Clock className="h-3 w-3" />
                        {formatDistanceToNow(new Date(record.last_activity), { addSuffix: true })}
                      </div>
                    </div>
                    
                    <Button variant="ghost" size="sm">
                      <MoreVertical className="h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </ScrollArea>
      </div>

      {/* Right Panel - Record Details */}
      <div className="flex-1 flex flex-col">
        {selectedRecord ? (
          <>
            {/* Header */}
            <div className="p-6 border-b bg-white">
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-xl font-semibold">{selectedRecord.title}</h1>
                  <p className="text-gray-500">{selectedRecord.pipeline_name}</p>
                </div>
                
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm">
                    <Star className="h-4 w-4" />
                  </Button>
                  <Button variant="outline" size="sm">
                    <Archive className="h-4 w-4" />
                  </Button>
                  <Button size="sm" onClick={() => setShowCompose(true)}>
                    <Plus className="h-4 w-4 mr-2" />
                    New Message
                  </Button>
                </div>
              </div>
            </div>

            {/* Content Area */}
            <div className="flex-1 overflow-hidden">
              <Tabs defaultValue="timeline" className="h-full flex flex-col">
                <TabsList className="mx-6 mt-4">
                  <TabsTrigger value="timeline">Timeline</TabsTrigger>
                  <TabsTrigger value="channels">Channels</TabsTrigger>
                  <TabsTrigger value="analytics">Analytics</TabsTrigger>
                </TabsList>
                
                <TabsContent value="timeline" className="flex-1 m-6 mt-4">
                  <ConversationTimeline 
                    recordId={selectedRecord.id}
                    recordTitle={selectedRecord.title}
                    className="h-full"
                  />
                </TabsContent>
                
                <TabsContent value="channels" className="flex-1 m-6 mt-4">
                  <Card className="h-full">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Users className="h-5 w-5" />
                        Channel Availability
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <ScrollArea className="h-96">
                        <div className="space-y-4">
                          {channelAvailability.map((channel) => (
                            <div key={channel.channel_type} className="border rounded-lg p-4">
                              <div className="flex items-center justify-between mb-2">
                                <div className="flex items-center gap-3">
                                  <div className={`p-2 rounded-full text-white ${getChannelColor(channel.channel_type)}`}>
                                    {getChannelIcon(channel.channel_type)}
                                  </div>
                                  <div>
                                    <h4 className="font-medium">{channel.display_name}</h4>
                                    <p className="text-sm text-gray-500">Priority {channel.priority}</p>
                                  </div>
                                </div>
                                
                                <Badge className={getStatusColor(channel.status)}>
                                  {channel.status}
                                </Badge>
                              </div>
                              
                              <div className="grid grid-cols-2 gap-4 text-sm">
                                <div className="flex items-center gap-2">
                                  {channel.user_connected ? (
                                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                                  ) : (
                                    <AlertCircle className="h-4 w-4 text-red-500" />
                                  )}
                                  <span>User Connected</span>
                                </div>
                                
                                <div className="flex items-center gap-2">
                                  {channel.contact_info_available ? (
                                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                                  ) : (
                                    <AlertCircle className="h-4 w-4 text-red-500" />
                                  )}
                                  <span>Contact Info</span>
                                </div>
                                
                                {channel.has_history && (
                                  <div className="flex items-center gap-2">
                                    <TrendingUp className="h-4 w-4 text-blue-500" />
                                    <span>Has History</span>
                                  </div>
                                )}
                              </div>
                              
                              {channel.history && (
                                <div className="mt-3 pt-3 border-t">
                                  <div className="grid grid-cols-3 gap-4 text-sm">
                                    <div>
                                      <p className="text-gray-500">Messages</p>
                                      <p className="font-medium">{channel.history.total_messages}</p>
                                    </div>
                                    <div>
                                      <p className="text-gray-500">Response Rate</p>
                                      <p className="font-medium">{channel.history.response_rate.toFixed(1)}%</p>
                                    </div>
                                    <div>
                                      <p className="text-gray-500">Engagement</p>
                                      <p className="font-medium">{channel.history.engagement_score.toFixed(1)}</p>
                                    </div>
                                  </div>
                                </div>
                              )}
                              
                              {channel.limitations.length > 0 && (
                                <div className="mt-3 pt-3 border-t">
                                  <p className="text-sm text-gray-500 mb-1">Limitations:</p>
                                  <ul className="text-sm text-red-600">
                                    {channel.limitations.map((limitation, index) => (
                                      <li key={index}>• {limitation}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </ScrollArea>
                    </CardContent>
                  </Card>
                </TabsContent>
                
                <TabsContent value="analytics" className="flex-1 m-6 mt-4">
                  <CommunicationAnalytics 
                    recordId={selectedRecord.id}
                    recordTitle={selectedRecord.title}
                    className="h-full"
                  />
                </TabsContent>
              </Tabs>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-500">
            <div className="text-center">
              <MessageSquare className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <p>Select a contact to view their communication timeline</p>
            </div>
          </div>
        )}
      </div>
      
      {/* Smart Compose Dialog */}
      {showCompose && selectedRecord && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              setShowCompose(false)
            }
          }}
        >
          <div className="max-w-4xl w-full mx-4 max-h-[90vh] overflow-auto">
            <SmartCompose
              recordId={selectedRecord.id}
              recordTitle={selectedRecord.title}
              onSent={(messageId, channel) => {
                console.log('Message sent:', messageId, 'via', channel)
                setShowCompose(false)
                // Optionally refresh the conversation timeline
              }}
              onCancel={() => setShowCompose(false)}
              className="shadow-xl"
            />
          </div>
        </div>
      )}
    </div>
  )
}