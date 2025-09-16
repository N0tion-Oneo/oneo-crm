'use client'

import React, { useState, useEffect } from 'react'
import { 
  MessageSquare, 
  RefreshCw, 
  Mail, 
  Phone, 
  AlertCircle,
  Users,
  Loader2,
  CheckCircle,
  Plus,
  Calendar
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useRecordCommunications } from './hooks/useRecordCommunications'
import { ConversationList } from './ConversationList'
import { ConversationThread } from './ConversationThread'
import { SyncStatusIndicator } from './SyncStatusIndicator'
import { QuickReply } from './QuickReply'
import { EmailCompose } from './EmailCompose'
import { MessageCompose } from './MessageCompose'
import { EventScheduler } from './EventScheduler'
import { CallLogger } from './CallLogger'
import { MeetingCaptureSimple } from './MeetingCaptureSimple'
import { api } from '@/lib/api'

interface RecordCommunicationsPanelProps {
  recordId: string
  pipelineId: string
}

export function RecordCommunicationsPanel({ 
  recordId
}: RecordCommunicationsPanelProps) {
  const [selectedConversation, setSelectedConversation] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'email' | 'whatsapp' | 'linkedin' | 'calendar' | 'calls'>('email')
  const [loadingChannel, setLoadingChannel] = useState<string | null>(null)
  const [replyTo, setReplyTo] = useState<any>(null)
  const [replyMode, setReplyMode] = useState<'reply' | 'reply-all' | 'forward' | null>(null)
  const [isComposingNew, setIsComposingNew] = useState(false)
  
  const {
    profile,
    conversations,
    stats,
    syncStatus,
    syncJustCompleted,
    isLoading,
    isLoadingMore,
    error,
    hasMoreConversations,
    triggerSync,
    markAsRead,
    updateConversation,
    refreshData,
    fetchConversations,
    loadMoreConversations
  } = useRecordCommunications(recordId)


  // Clear conversations and selection when tab changes
  useEffect(() => {
    // Clear selected conversation when switching tabs
    setSelectedConversation(null)
    // Clear reply state when switching tabs
    setReplyTo(null)
    setReplyMode(null)
    // Clear composing new state
    setIsComposingNew(false)
    // Reset loading state
    setLoadingChannel(null)
  }, [activeTab])

  // Fetch data when tab changes or component mounts
  useEffect(() => {
    if (!isLoading && fetchConversations) {
      setLoadingChannel(activeTab)
      // Fetch conversations for specific channels
      fetchConversations(activeTab).then(() => {
        setLoadingChannel(null)
      })
    }
  }, [activeTab, fetchConversations, isLoading])

  // Use conversations directly since they're already filtered by the API
  const filteredConversations = conversations

  // Handle sync trigger
  const handleSync = async () => {
    // Always force sync when manually triggered from UI
    await triggerSync(true)
  }

  // Handle reply actions
  const handleReply = (message: any) => {
    setReplyTo(message)
    setReplyMode('reply')
  }

  const handleReplyAll = (message: any) => {
    setReplyTo(message)
    setReplyMode('reply-all')
  }

  const handleForward = (message: any) => {
    setReplyTo(message)
    setReplyMode('forward')
  }

  const handleCancelReply = () => {
    setReplyTo(null)
    setReplyMode(null)
  }

  if (isLoading && !profile) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 space-y-4">
        <AlertCircle className="w-12 h-12 text-red-500" />
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Failed to load communications
        </p>
        <Button onClick={refreshData} variant="outline" size="sm">
          <RefreshCw className="w-4 h-4 mr-2" />
          Retry
        </Button>
      </div>
    )
  }

  // Remove the blocking "No communications yet" screen entirely
  // Users can still sync via the sync button in the header or initiate new conversations

  return (
    <div className="relative flex flex-col h-full max-h-[800px] min-h-[500px] overflow-hidden bg-gray-50 dark:bg-gray-900">
      {/* Success notification when sync completes */}
      {syncJustCompleted && (
        <div className="absolute top-4 right-4 z-50 flex items-center gap-2 bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 px-4 py-2 rounded-lg shadow-lg">
          <CheckCircle className="w-4 h-4" />
          <span className="text-sm font-medium">Sync completed successfully!</span>
        </div>
      )}
      
      {/* Header with tabs and sync - Compact */}
      <div className="flex-shrink-0 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
        <div className="flex items-center justify-between p-3 gap-3">
          <Button
            onClick={() => {
              setIsComposingNew(true)
              setSelectedConversation(null)
              setReplyTo(null)
              setReplyMode(null)
            }}
            size="sm"
            variant="outline"
            className="mr-2"
          >
            <Plus className="w-4 h-4 mr-1" />
            {activeTab === 'calendar' ? 'New Event' : activeTab === 'calls' ? 'Log Call' : 'New'}
          </Button>
          <Tabs value={activeTab} onValueChange={(value: any) => setActiveTab(value)} className="flex-1">
            <TabsList className="h-9">
            <TabsTrigger value="email" className="flex-1">
              <Mail className="w-4 h-4 mr-1" />
              Email
              {(stats?.channel_breakdown?.email || stats?.channel_breakdown?.gmail) && (
                <span className="ml-1 text-xs">
                  ({(stats.channel_breakdown.email?.messages || 0) + (stats.channel_breakdown.gmail?.messages || 0)})
                </span>
              )}
            </TabsTrigger>
            <TabsTrigger value="whatsapp" className="flex-1">
              <Phone className="w-4 h-4 mr-1" />
              WhatsApp
              {stats?.channel_breakdown?.whatsapp && (
                <span className="ml-1 text-xs">({stats.channel_breakdown.whatsapp.messages || 0})</span>
              )}
            </TabsTrigger>
            <TabsTrigger value="linkedin" className="flex-1">
              <Users className="w-4 h-4 mr-1" />
              LinkedIn
              {stats?.channel_breakdown?.linkedin && (
                <span className="ml-1 text-xs">({stats.channel_breakdown.linkedin.messages || 0})</span>
              )}
            </TabsTrigger>
            <TabsTrigger value="calendar" className="flex-1">
              <Calendar className="w-4 h-4 mr-1" />
              Calendar
              {(stats?.channel_breakdown?.calendar || stats?.channel_breakdown?.scheduling) && (
                <span className="ml-1 text-xs">
                  ({(stats.channel_breakdown.calendar?.messages || 0) + (stats.channel_breakdown.scheduling?.messages || 0)})
                </span>
              )}
            </TabsTrigger>
            <TabsTrigger value="calls" className="flex-1">
              <Phone className="w-4 h-4 mr-1" />
              Calls
              {stats?.channel_breakdown?.calls && (
                <span className="ml-1 text-xs">({stats.channel_breakdown.calls.messages || 0})</span>
              )}
            </TabsTrigger>
          </TabsList>
          </Tabs>
          <SyncStatusIndicator 
            profile={profile}
            syncStatus={syncStatus}
            onSync={handleSync}
            onMarkAllRead={markAsRead}
          />
        </div>
      </div>

      {/* Main content area - Flexible height with min-h-0 for proper scrolling */}
      <div className="flex-1 min-h-0 relative">
          <div className="flex h-full overflow-hidden">
            {/* Conversation list - Fixed width sidebar */}
            <div className="w-80 h-full border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden flex flex-col flex-shrink-0">
              <div className="flex-1 overflow-y-auto overflow-x-hidden">
                {loadingChannel ? (
                  <div className="flex items-center justify-center h-32">
                    <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
                  </div>
                ) : (
                  <ConversationList
                    conversations={filteredConversations}
                    selectedId={selectedConversation}
                    onSelect={(id) => {
                      setSelectedConversation(id)
                      // Clear reply state when switching conversations
                      setReplyTo(null)
                      setReplyMode(null)
                      // Clear composing new state when selecting a conversation
                      setIsComposingNew(false)
                    }}
                    onMarkAsRead={async (conversationId, isUnread) => {
                      try {
                        // Use the api client which handles authentication and base URL automatically
                        const response = await api.post(
                          `/api/v1/communications/conversations/${conversationId}/mark-conversation-${isUnread ? 'unread' : 'read'}/`,
                          {}
                        )
                        
                        if (response.data.success) {
                          // Refresh the conversation list to show updated unread counts
                          // Maintain the current channel filter
                          await fetchConversations(activeTab)
                        }
                      } catch (error) {
                        console.error('Error marking conversation:', error)
                      }
                    }}
                    onLoadMore={() => loadMoreConversations(activeTab)}
                    hasMore={hasMoreConversations?.[activeTab] || false}
                    isLoadingMore={isLoadingMore}
                    channelType={activeTab}
                    onSync={handleSync}
                  />
                )}
              </div>
            </div>

            {/* Conversation detail - Takes remaining space */}
            <div className="flex-1 h-full flex flex-col bg-white dark:bg-gray-800 overflow-hidden">
              {selectedConversation || isComposingNew ? (
                <>
                  {/* Messages area with native scroll */}
                  {selectedConversation && (
                    <div className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden">
                      <ConversationThread
                        conversationId={selectedConversation}
                        recordId={recordId}
                        onReply={handleReply}
                        onReplyAll={handleReplyAll}
                        onForward={handleForward}
                        onConversationUpdate={updateConversation}
                        isEmail={activeTab === 'email'}
                      />
                    </div>
                  )}
                  
                  {/* New message/event area when composing new */}
                  {!selectedConversation && isComposingNew && (
                    activeTab === 'calendar' ? (
                      // For calendar, show EventScheduler in the main area
                      <div className="flex-1 min-h-0 overflow-y-auto">
                        <EventScheduler
                          recordId={recordId}
                          onEventScheduled={() => {
                            fetchConversations('calendar')
                            setIsComposingNew(false)
                          }}
                          onCancel={() => {
                            setIsComposingNew(false)
                          }}
                          defaultParticipant={{
                            email: profile?.communication_identifiers?.email?.[0],
                            name: undefined,
                            phone: profile?.communication_identifiers?.phone?.[0]
                          }}
                        />
                      </div>
                    ) : activeTab === 'calls' ? (
                      // For calls, show CallLogger in the main area
                      <div className="flex-1 min-h-0 overflow-y-auto">
                        <CallLogger
                          recordId={recordId}
                          onCallLogged={() => {
                            fetchConversations('calls')
                            setIsComposingNew(false)
                          }}
                          onCancel={() => {
                            setIsComposingNew(false)
                          }}
                          defaultParticipant={{
                            email: profile?.communication_identifiers?.email?.[0],
                            name: undefined,
                            phone: profile?.communication_identifiers?.phone?.[0]
                          }}
                        />
                      </div>
                    ) : (
                      // For other channels, show header with spacer
                      <div className="flex-1 min-h-0 flex flex-col">
                        <div className="border-b border-gray-200 dark:border-gray-700 p-4">
                          <div className="flex items-center justify-between">
                            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                              New {activeTab === 'email' ? 'Email' : activeTab === 'whatsapp' ? 'WhatsApp Message' : activeTab === 'linkedin' ? 'LinkedIn Message' : 'Message'}
                            </h3>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setIsComposingNew(false)
                                setReplyTo(null)
                                setReplyMode(null)
                              }}
                            >
                              Cancel
                            </Button>
                          </div>
                        </div>
                        <div className="flex-1" />
                      </div>
                    )
                  )}
                  
                  {/* Reply/compose area - Fixed at bottom */}
                  <div className="flex-shrink-0">
                    {(activeTab === 'calls') ? (
                      // Calls don't have a compose area at the bottom (shown in main area instead)
                      null
                    ) : activeTab === 'calendar' && selectedConversation ? (
                      // Calendar conversations can have notes, action items, and tasks added
                      <MeetingCaptureSimple
                        conversationId={selectedConversation}
                        recordId={recordId}
                        onContentAdded={() => {
                          fetchConversations(activeTab)
                        }}
                      />
                    ) : activeTab === 'email' ? (
                      <EmailCompose
                        conversationId={selectedConversation}
                        recordId={recordId}
                        replyTo={replyTo}
                        replyMode={replyMode}
                        onCancelReply={handleCancelReply}
                        onMessageSent={() => {
                          fetchConversations(activeTab)
                          setIsComposingNew(false)
                        }}
                        defaultRecipient={isComposingNew && !selectedConversation ? profile?.communication_identifiers?.email?.[0] : undefined}
                      />
                    ) : (
                      <MessageCompose
                        conversationId={selectedConversation}
                        recordId={recordId}
                        replyTo={replyTo}
                        onCancelReply={handleCancelReply}
                        onMessageSent={() => {
                          fetchConversations(activeTab)
                          setIsComposingNew(false)
                        }}
                        channelType={activeTab as 'whatsapp' | 'linkedin'}
                        defaultRecipient={isComposingNew && !selectedConversation ? 
                          (activeTab === 'whatsapp' ? profile?.communication_identifiers?.phone?.[0] : 
                           profile?.communication_identifiers?.linkedin?.[0]) : 
                          undefined}
                      />
                    )}
                  </div>
                </>
              ) : (
                <div className="flex items-center justify-center h-full text-gray-500">
                  <div className="text-center space-y-4">
                    <MessageSquare className="w-12 h-12 mx-auto text-gray-400" />
                    <p className="text-sm">Select a conversation or start a new one</p>
                    <Button
                      onClick={() => {
                        setIsComposingNew(true)
                        setSelectedConversation(null)
                        setReplyTo(null)
                        setReplyMode(null)
                      }}
                      size="sm"
                      className="mt-3"
                    >
                      <Plus className="w-4 h-4 mr-2" />
                      New {activeTab === 'email' ? 'Email' : activeTab === 'calendar' ? 'Event' : activeTab === 'calls' ? 'Call Log' : 'Message'}
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </div>
      </div>
    </div>
  )
}