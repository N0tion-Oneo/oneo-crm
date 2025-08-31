'use client'

import React, { useState, useEffect } from 'react'
import { 
  MessageSquare, 
  RefreshCw, 
  Mail, 
  Phone, 
  AlertCircle,
  Users,
  Loader2
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useRecordCommunications } from './hooks/useRecordCommunications'
import { ConversationList } from './ConversationList'
import { ConversationThread } from './ConversationThread'
import { SyncStatusIndicator } from './SyncStatusIndicator'
import { QuickReply } from './QuickReply'
import { MessageTimeline } from './MessageTimeline'

interface RecordCommunicationsPanelProps {
  recordId: string
  pipelineId: string
}

export function RecordCommunicationsPanel({ 
  recordId
}: RecordCommunicationsPanelProps) {
  const [selectedConversation, setSelectedConversation] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'all' | 'email' | 'whatsapp' | 'linkedin'>('all')
  
  const {
    profile,
    conversations,
    timelineMessages,
    stats,
    syncStatus,
    isLoading,
    error,
    hasMoreTimeline,
    triggerSync,
    refreshData,
    fetchConversations,
    fetchTimeline,
    loadMoreTimeline
  } = useRecordCommunications(recordId)


  // Fetch data when tab changes or component mounts
  useEffect(() => {
    if (!isLoading) {
      if (activeTab === 'all' && fetchTimeline) {
        // Fetch timeline for 'all' tab
        fetchTimeline(true) // Reset timeline
      } else if (fetchConversations) {
        // Fetch conversations for specific channels
        fetchConversations(activeTab)
      }
    }
  }, [activeTab, fetchConversations, fetchTimeline, isLoading])

  // Use conversations directly since they're already filtered by the API
  const filteredConversations = conversations

  // Handle sync trigger
  const handleSync = async () => {
    // Always force sync when manually triggered from UI
    await triggerSync(true)
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

  if (!conversations.length && !profile?.sync_in_progress) {
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
    <div className="flex flex-col h-full max-h-[800px] min-h-[500px] overflow-hidden bg-gray-50 dark:bg-gray-900">
      {/* Header with tabs and sync - Compact */}
      <div className="flex-shrink-0 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
        <div className="flex items-center justify-between p-3 gap-3">
          <Tabs value={activeTab} onValueChange={(value: any) => setActiveTab(value)} className="flex-1">
            <TabsList className="h-9">
              <TabsTrigger value="all" className="flex-1">
              <MessageSquare className="w-4 h-4 mr-1" />
              All
              {stats && stats.total_messages > 0 && (
                <span className="ml-1 text-xs">({stats.total_messages})</span>
              )}
            </TabsTrigger>
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
          />
        </div>
      </div>

      {/* Main content area - Flexible height with min-h-0 for proper scrolling */}
      <div className="flex-1 min-h-0 flex">
        {activeTab === 'all' ? (
          /* Timeline view for All tab - Full width */
          <div className="flex-1 min-w-0 bg-white dark:bg-gray-800">
            <MessageTimeline
              messages={timelineMessages}
              isLoading={isLoading}
              error={error}
              onLoadMore={loadMoreTimeline}
              hasMore={hasMoreTimeline}
            />
          </div>
        ) : (
          <>
            {/* Conversation list - Fixed width with scrolling */}
            <div className="w-80 flex-shrink-0 border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden flex flex-col">
              <ScrollArea className="flex-1">
                <ConversationList
                  conversations={filteredConversations}
                  selectedId={selectedConversation}
                  onSelect={setSelectedConversation}
                />
              </ScrollArea>
            </div>

            {/* Conversation detail - Flexible width with proper scrolling */}
            <div className="flex-1 min-w-0 flex flex-col bg-white dark:bg-gray-800">
              {selectedConversation ? (
                <>
                  {/* Messages area with scroll */}
                  <div className="flex-1 min-h-0 overflow-hidden">
                    <ScrollArea className="h-full">
                      <ConversationThread
                        conversationId={selectedConversation}
                        recordId={recordId}
                      />
                    </ScrollArea>
                  </div>
                  {/* Reply area - Fixed at bottom */}
                  <div className="flex-shrink-0 border-t border-gray-200 dark:border-gray-700 p-4 bg-gray-50 dark:bg-gray-900">
                    <QuickReply
                      conversationId={selectedConversation}
                      recordId={recordId}
                    />
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
          </>
        )}
      </div>
    </div>
  )
}