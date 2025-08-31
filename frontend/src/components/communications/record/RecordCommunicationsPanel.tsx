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
import { CommunicationStats } from './CommunicationStats'
import { SyncStatusIndicator } from './SyncStatusIndicator'
import { QuickReply } from './QuickReply'
import { TestCommunications } from './TestCommunications'
import '@/styles/communications.css'

interface RecordCommunicationsPanelProps {
  recordId: string
  pipelineId: string
}

export function RecordCommunicationsPanel({ 
  recordId, 
  pipelineId 
}: RecordCommunicationsPanelProps) {
  const [selectedConversation, setSelectedConversation] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'all' | 'email' | 'whatsapp' | 'linkedin'>('all')
  
  const {
    profile,
    conversations,
    stats,
    syncStatus,
    isLoading,
    error,
    triggerSync,
    refreshData,
    fetchConversations
  } = useRecordCommunications(recordId)

  // Debug logging
  useEffect(() => {
    console.log('RecordCommunicationsPanel Debug:', {
      recordId,
      recordIdType: typeof recordId,
      pipelineId,
      pipelineIdType: typeof pipelineId,
      isLoading,
      profile,
      conversations: conversations?.length,
      stats,
      error
    })
  }, [recordId, pipelineId, isLoading, profile, conversations, stats, error])

  // Fetch conversations when tab changes or component mounts
  useEffect(() => {
    if (!isLoading && fetchConversations) {
      // Smart mode for 'all', specific channel otherwise
      fetchConversations(activeTab)
    }
  }, [activeTab, fetchConversations, isLoading])

  // Use conversations directly since they're already filtered by the API
  const filteredConversations = conversations

  // Handle sync trigger
  const handleSync = async () => {
    // Always force sync when manually triggered from UI
    await triggerSync(true)
  }

  if (isLoading && !profile) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
        </div>
        <TestCommunications recordId={recordId} />
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
      <div className="flex flex-col items-center justify-center h-64 space-y-4">
        <MessageSquare className="w-12 h-12 text-gray-400" />
        <p className="text-sm text-gray-600 dark:text-gray-400">
          No communications found
        </p>
        <p className="text-xs text-gray-500 dark:text-gray-500">
          Communications will appear here when synced
        </p>
        <Button onClick={handleSync} variant="outline" size="sm">
          <RefreshCw className="w-4 h-4 mr-2" />
          Sync Communications
        </Button>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full max-h-[800px] min-h-[500px] overflow-hidden bg-gray-50 dark:bg-gray-900">
      {/* Header with stats and sync status - Fixed height */}
      <div className="flex-shrink-0 border-b border-gray-200 dark:border-gray-700 p-4 bg-white dark:bg-gray-800">
        <div className="flex items-center justify-between mb-4">
          <CommunicationStats stats={stats} />
          <SyncStatusIndicator 
            profile={profile}
            syncStatus={syncStatus}
            onSync={handleSync}
          />
        </div>

        {/* Channel tabs */}
        <Tabs value={activeTab} onValueChange={(value: any) => setActiveTab(value)}>
          <TabsList className="w-full">
            <TabsTrigger value="all" className="flex-1">
              All ({stats?.total_conversations || 0})
            </TabsTrigger>
            <TabsTrigger value="email" className="flex-1">
              <Mail className="w-4 h-4 mr-1" />
              Email {(stats?.channel_breakdown?.email || stats?.channel_breakdown?.gmail) && 
                     `(${(stats.channel_breakdown.email || stats.channel_breakdown.gmail).conversations})`}
            </TabsTrigger>
            <TabsTrigger value="whatsapp" className="flex-1">
              <Phone className="w-4 h-4 mr-1" />
              WhatsApp {stats?.channel_breakdown?.whatsapp && `(${stats.channel_breakdown.whatsapp.conversations})`}
            </TabsTrigger>
            <TabsTrigger value="linkedin" className="flex-1">
              <Users className="w-4 h-4 mr-1" />
              LinkedIn {stats?.channel_breakdown?.linkedin && `(${stats.channel_breakdown.linkedin.conversations})`}
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Main content area - Flexible height with min-h-0 for proper scrolling */}
      <div className="flex-1 min-h-0 flex">
        {/* Conversation list - Fixed width with scrolling */}
        <div className="w-80 flex-shrink-0 border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden flex flex-col">
          <ScrollArea className="flex-1 communications-scrollbar">
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
                <ScrollArea className="h-full communications-scrollbar smooth-scroll">
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
      </div>
    </div>
  )
}