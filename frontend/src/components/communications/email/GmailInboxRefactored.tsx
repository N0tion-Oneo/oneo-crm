'use client'

import React, { useState, useEffect, useRef } from 'react'
import { Mail, Reply, Forward, Trash, MoreVertical, Paperclip, ChevronDown, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { MessageContent } from '@/components/MessageContent'
import { ContactLinkDialog } from '@/components/communications/ContactLinkDialog'
import { useWebSocket } from '@/contexts/websocket-context'
import { useAuth } from '@/features/auth/context'
import { useToast } from '@/hooks/use-toast'
import { emailService } from '@/services/emailService'

// Import custom hooks
import { useEmailAccounts } from './hooks/useEmailAccounts'
import { useEmailThreads } from './hooks/useEmailThreads'
import { useEmailCompose } from './hooks/useEmailCompose'

// Import components
import { EmailHeader } from './components/EmailHeader'
import { EmailThreadList } from './components/EmailThreadList'
import { EmailComposeDialog } from './components/EmailComposeDialog'

// Import utilities
import { formatEmailDate } from './utils/emailFormatters'
import { WS_CHANNELS } from './utils/emailConstants'
import { EmailMessage } from './utils/emailTypes'

interface GmailInboxRefactoredProps {
  className?: string
}

export default function GmailInboxRefactored({ className }: GmailInboxRefactoredProps) {
  // Custom hooks
  const { accounts, selectedAccount, loading: accountsLoading, selectAccount } = useEmailAccounts()
  const { 
    threads, 
    selectedThread, 
    threadMessages,
    loading: threadsLoading,
    messagesLoading,
    syncing,
    searchQuery,
    setSearchQuery,
    filterStatus,
    setFilterStatus,
    selectedFolder,
    setSelectedFolder,
    currentPage,
    hasMorePages,
    folders,
    loadThreads,
    selectThread,
    syncEmails,
    setThreads
  } = useEmailThreads({ selectedAccount })
  
  const {
    composeOpen,
    replyMode,
    composeTo,
    composeCc,
    composeBcc,
    composeSubject,
    composeBody,
    sending,
    setComposeOpen,
    setComposeTo,
    setComposeCc,
    setComposeBcc,
    setComposeSubject,
    setComposeBody,
    handleCompose,
    handleReply,
    handleForward,
    handleSendEmail,
    closeCompose,
    editorRef,
    editorKey,
    setEditorKey,
    lastOpenState
  } = useEmailCompose({ 
    selectedAccount, 
    selectedThread, 
    threadMessages,
    onEmailSent: loadThreads
  })
  
  // Local state
  const [linkDialogOpen, setLinkDialogOpen] = useState(false)
  const [linkDialogThread, setLinkDialogThread] = useState<any>(null)
  const [collapsedMessages, setCollapsedMessages] = useState<Set<string>>(new Set())
  
  // WebSocket and auth
  const { subscribe, unsubscribe } = useWebSocket()
  const { user } = useAuth()
  const { toast } = useToast()
  const subscriptionRef = useRef<string | null>(null)
  
  // Subscribe to email storage updates via WebSocket
  useEffect(() => {
    if (!selectedAccount || !user?.id) return
    
    const channel = WS_CHANNELS.EMAIL_USER(user.id)
    
    subscriptionRef.current = subscribe(channel, (message) => {
      console.log('📨 Email storage update received:', message)
      
      if (message.type === 'email_thread_stored' || message.type === 'sync_progress_update') {
        const threadId = message.thread_id || message.payload?.thread_id
        const stored = message.stored !== undefined ? message.stored : message.payload?.stored
        
        if (threadId) {
          setThreads(prevThreads => 
            prevThreads.map(thread => {
              if (thread.id === threadId) {
                return {
                  ...thread,
                  stored: stored === true,
                  can_link: stored !== true
                }
              }
              return thread
            })
          )
        }
      }
    })
    
    return () => {
      if (subscriptionRef.current) {
        unsubscribe(subscriptionRef.current)
        subscriptionRef.current = null
      }
    }
  }, [selectedAccount, user, subscribe, unsubscribe, setThreads])
  
  const handleLinkContact = (thread: any) => {
    setLinkDialogThread(thread)
    setLinkDialogOpen(true)
  }
  
  const handleDelete = async () => {
    if (!selectedThread || !selectedAccount) return
    
    const emailIdToDelete = threadMessages.length > 0 
      ? threadMessages[0].external_id 
      : selectedThread.external_thread_id || selectedThread.id
    
    try {
      const result = await emailService.deleteEmail(selectedAccount.account_id, emailIdToDelete)
      
      if (result.success) {
        setThreads(prev => prev.filter(t => t.id !== selectedThread.id))
        selectThread(null)
        
        toast({
          title: 'Success',
          description: result.message || 'Email moved to trash',
        })
      } else {
        throw new Error(result.error || 'Failed to delete email')
      }
    } catch (error: any) {
      console.error('Error deleting thread:', error)
      toast({
        title: 'Error',
        description: error.message || 'Failed to delete thread',
        variant: 'destructive'
      })
    }
  }
  
  const toggleMessageCollapse = (messageId: string) => {
    setCollapsedMessages(prev => {
      const newSet = new Set(prev)
      if (newSet.has(messageId)) {
        newSet.delete(messageId)
      } else {
        newSet.add(messageId)
      }
      return newSet
    })
  }
  
  const loading = accountsLoading || threadsLoading
  
  return (
    <div className={`flex flex-col h-full ${className || ''}`}>
      {/* Header */}
      <EmailHeader
        accounts={accounts}
        selectedAccount={selectedAccount}
        onAccountSelect={selectAccount}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        filterStatus={filterStatus}
        onFilterChange={setFilterStatus}
        selectedFolder={selectedFolder}
        onFolderChange={setSelectedFolder}
        folders={folders}
        syncing={syncing}
        onSync={syncEmails}
        onCompose={handleCompose}
        loading={loading}
      />
      
      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Thread List */}
        <div className="w-1/3 min-w-[300px] max-w-[400px] border-r bg-gray-50 dark:bg-gray-900/50 flex flex-col overflow-hidden">
          <EmailThreadList
            threads={threads}
            selectedThread={selectedThread}
            selectedAccount={selectedAccount}
            onSelectThread={selectThread}
            onThreadUpdate={setThreads}
            onLinkContact={handleLinkContact}
            currentPage={currentPage}
            hasMorePages={hasMorePages}
            onPageChange={loadThreads}
            loading={loading}
          />
        </div>
        
        {/* Thread View */}
        <div className="flex-1 flex flex-col overflow-hidden bg-white dark:bg-gray-950">
          {selectedThread && threadMessages.length > 0 ? (
            <div className="flex-1 flex flex-col overflow-hidden">
              {/* Thread Header */}
              <div className="border-b p-4 bg-gray-50 dark:bg-gray-900">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-semibold">
                      {selectedThread.subject || '(No subject)'}
                    </h2>
                    <div className="flex items-center gap-2 mt-1 text-sm text-gray-500">
                      <span>{threadMessages.length} messages</span>
                      {selectedThread.stored && (
                        <Badge variant="secondary">Stored</Badge>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    <Button 
                      variant="ghost" 
                      size="sm"
                      onClick={() => handleReply()}
                      title="Reply"
                    >
                      <Reply className="w-4 h-4" />
                    </Button>
                    <Button 
                      variant="ghost" 
                      size="sm"
                      onClick={handleForward}
                      title="Forward"
                    >
                      <Forward className="w-4 h-4" />
                    </Button>
                    <Button 
                      variant="ghost" 
                      size="sm"
                      onClick={handleDelete}
                      title="Delete"
                    >
                      <Trash className="w-4 h-4" />
                    </Button>
                    <Button variant="ghost" size="sm">
                      <MoreVertical className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </div>
              
              {/* Messages */}
              <ScrollArea className="flex-1">
                {messagesLoading ? (
                  <div className="flex items-center justify-center p-8">
                    <div className="text-center">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 dark:border-gray-100 mx-auto mb-4"></div>
                      <p className="text-gray-500">Loading messages...</p>
                    </div>
                  </div>
                ) : (
                  <div className="p-4 space-y-4">
                    {threadMessages.map((message) => {
                      const messageId = message.id || message.external_id
                      const isCollapsed = collapsedMessages.has(messageId)
                      
                      return (
                        <div key={messageId} className="bg-white border rounded-lg">
                          {/* Message Header */}
                          <div 
                            className="p-4 cursor-pointer hover:bg-gray-50 transition-colors"
                            onClick={() => toggleMessageCollapse(messageId)}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="p-0 h-auto"
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    toggleMessageCollapse(messageId)
                                  }}
                                >
                                  {isCollapsed ? (
                                    <ChevronRight className="w-4 h-4" />
                                  ) : (
                                    <ChevronDown className="w-4 h-4" />
                                  )}
                                </Button>
                                <Avatar className="w-6 h-6">
                                  <AvatarFallback className="bg-red-100 text-red-700 text-xs">
                                    {message.sender.name?.charAt(0) || message.sender.email.charAt(0).toUpperCase()}
                                  </AvatarFallback>
                                </Avatar>
                                <span className="font-medium text-sm">
                                  {message.sender.name || message.sender.email}
                                </span>
                                <Badge variant="outline" className="text-xs">
                                  {message.direction}
                                </Badge>
                              </div>
                              <div className="flex items-center gap-3">
                                <span className="text-xs text-gray-500">
                                  {formatEmailDate(message.sent_at)}
                                </span>
                                {message.has_attachments && (
                                  <Paperclip className="w-3 h-3 text-gray-400" />
                                )}
                              </div>
                            </div>
                            
                            {/* Show subject preview when collapsed */}
                            {isCollapsed && (
                              <div className="mt-2 ml-6 text-sm text-gray-600 truncate">
                                {message.subject || '(No subject)'}
                              </div>
                            )}
                          </div>
                          
                          {/* Message Details - Only visible when expanded */}
                          {!isCollapsed && (
                            <div className="p-4 pt-0 border-t border-gray-100">
                              <div className="text-sm text-gray-600 mb-4">
                                <div className="mb-1 break-words">
                                  <strong>From:</strong> {message.from}
                                </div>
                                {message.recipients.to.length > 0 && (
                                  <div className="mb-1 break-words">
                                    <strong>To:</strong> {message.recipients.to.join(', ')}
                                  </div>
                                )}
                                {message.recipients.cc.length > 0 && (
                                  <div className="mb-1 break-words">
                                    <strong>CC:</strong> {message.recipients.cc.join(', ')}
                                  </div>
                                )}
                                <div className="break-words">
                                  <strong>Subject:</strong> {message.subject || '(No subject)'}
                                </div>
                              </div>

                              {/* Message Body */}
                              <div className="prose prose-sm max-w-none overflow-auto max-h-96">
                                {message.content ? (
                                  <MessageContent
                                    content={message.content}
                                    isEmail={true}
                                    className="text-gray-900"
                                    metadata={(message as any).metadata}
                                  />
                                ) : (
                                  <div className="text-gray-500 italic">No content</div>
                                )}
                              </div>

                              {/* Attachments */}
                              {message.attachments && message.attachments.length > 0 && (
                                <div className="mt-4 pt-4 border-t">
                                  <p className="text-sm font-medium mb-2">
                                    Attachments ({message.attachments.length}):
                                  </p>
                                  <div className="space-y-2 max-h-40 overflow-y-auto">
                                    {message.attachments.map((attachment, idx) => (
                                      <div key={attachment.id || `attachment-${idx}`} className="flex items-center gap-2 p-2 bg-gray-50 rounded">
                                        <Paperclip className="w-4 h-4 text-gray-500 flex-shrink-0" />
                                        <div className="flex-1 min-w-0">
                                          <span className="text-sm font-medium truncate block">{attachment.filename}</span>
                                          <div className="text-xs text-gray-500">
                                            {attachment.content_type} • {(attachment.size / 1024).toFixed(1)}KB
                                          </div>
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                )}
              </ScrollArea>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center">
              <div className="text-center text-gray-500">
                <Mail className="w-16 h-16 mx-auto mb-4 text-gray-300" />
                <h3 className="text-lg font-medium mb-2">Select an email thread to read</h3>
                <p>Choose an email thread from the left to view your messages</p>
              </div>
            </div>
          )}
        </div>
      </div>
      
      {/* Compose Dialog */}
      <EmailComposeDialog
        open={composeOpen}
        onOpenChange={setComposeOpen}
        replyMode={replyMode}
        selectedAccount={selectedAccount}
        to={composeTo}
        cc={composeCc}
        bcc={composeBcc}
        subject={composeSubject}
        body={composeBody}
        sending={sending}
        onToChange={setComposeTo}
        onCcChange={setComposeCc}
        onBccChange={setComposeBcc}
        onSubjectChange={setComposeSubject}
        onBodyChange={setComposeBody}
        onSend={handleSendEmail}
        onCancel={closeCompose}
        editorRef={editorRef}
        editorKey={editorKey}
        lastOpenState={lastOpenState}
        setEditorKey={setEditorKey}
      />
      
      {/* Contact Link Dialog */}
      {linkDialogThread && (
        <ContactLinkDialog
          open={linkDialogOpen}
          onClose={() => {
            setLinkDialogOpen(false)
            setLinkDialogThread(null)
          }}
          threadId={linkDialogThread.id}
          threadParticipants={linkDialogThread.participants || []}
          onSuccess={() => {
            // Refresh the thread to show updated link status
            loadThreads(currentPage)
            toast({
              title: "Success",
              description: "Contact linked successfully"
            })
          }}
        />
      )}
    </div>
  )
}