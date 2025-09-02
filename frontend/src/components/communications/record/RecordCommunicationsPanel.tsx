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
  CheckCircle
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
import { api } from '@/lib/api'

interface RecordCommunicationsPanelProps {
  recordId: string
  pipelineId: string
}

export function RecordCommunicationsPanel({ 
  recordId
}: RecordCommunicationsPanelProps) {
  const [selectedConversation, setSelectedConversation] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'email' | 'whatsapp' | 'linkedin'>('email')
  const [loadingChannel, setLoadingChannel] = useState<string | null>(null)
  const [replyTo, setReplyTo] = useState<any>(null)
  const [replyMode, setReplyMode] = useState<'reply' | 'reply-all' | 'forward' | null>(null)
  
  const {
    profile,
    conversations,
    stats,
    syncStatus,
    syncJustCompleted,
    isLoading,
    error,
    triggerSync,
    markAsRead,
    updateConversation,
    refreshData,
    fetchConversations
  } = useRecordCommunications(recordId)


  // Clear conversations and selection when tab changes
  useEffect(() => {
    // Clear selected conversation when switching tabs
    setSelectedConversation(null)
    // Clear reply state when switching tabs
    setReplyTo(null)
    setReplyMode(null)
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

  if (!conversations.length && !profile?.sync_in_progress && !loadingChannel) {
    return (
      <div className="flex flex-col h-full max-h-[800px] min-h-[500px] bg-gray-50 dark:bg-gray-900">
        <div className="flex items-center justify-center h-full">
          <div className="text-center space-y-4">
            <div className="flex justify-center">
              <div className="rounded-full bg-gray-100 dark:bg-gray-800 p-4">
                <MessageSquare className="w-8 h-8 text-gray-400" />
              </div>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                No communications yet
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Start syncing to see emails, messages, and conversations
              </p>
            </div>
            <Button onClick={handleSync} size="sm">
              <RefreshCw className="w-4 h-4 mr-2" />
              Start Sync
            </Button>
          </div>
        </div>
      </div>
    )
  }

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
                  />
                )}
              </div>
            </div>

            {/* Conversation detail - Takes remaining space */}
            <div className="flex-1 h-full flex flex-col bg-white dark:bg-gray-800 overflow-hidden">
              {selectedConversation ? (
                <>
                  {/* Messages area with native scroll */}
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
                  {/* Reply area - Fixed at bottom */}
                  <div className="flex-shrink-0">
                    {activeTab === 'email' ? (
                      <EmailCompose
                        conversationId={selectedConversation}
                        recordId={recordId}
                        replyTo={replyTo}
                        replyMode={replyMode}
                        onCancelReply={handleCancelReply}
                        onMessageSent={() => fetchConversations(activeTab)}
                      />
                    ) : (
                      <MessageCompose
                        conversationId={selectedConversation}
                        recordId={recordId}
                        replyTo={replyTo}
                        onCancelReply={handleCancelReply}
                        onMessageSent={() => fetchConversations(activeTab)}
                        channelType={activeTab as 'whatsapp' | 'linkedin'}
                      />
                    )}
                  </div>
                </>
              ) : (
                <div className="flex items-center justify-center h-full text-gray-500">
                  <div className="text-center">
                    <MessageSquare className="w-12 h-12 mx-auto mb-3 text-gray-400" />
                    <p className="text-sm">Select a conversation to view messages</p>
                  </div>
                </div>
              )}
            </div>
          </div>
      </div>
    </div>
  )
}