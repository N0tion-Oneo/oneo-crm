'use client'

import React, { useState, useEffect, useCallback, useRef } from 'react'
import { Mail, Search, Filter, Archive, Reply, Forward, Star, StarOff, MoreVertical, Paperclip, RefreshCw, Trash, Send, X, Folder, Edit, Plus, Link, Unlink, User, Users, UserPlus, Cloud, ChevronDown, ChevronRight, ChevronLeft, ChevronsLeft, ChevronsRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue, SelectSeparator } from '@/components/ui/select'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { SafeAvatar } from '@/components/communications/SafeAvatar'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { useToast } from '@/hooks/use-toast'
import { MessageContent } from '@/components/MessageContent'
import { formatDistanceToNow } from 'date-fns'
import { emailService, EmailAccount, EmailThread, EmailMessage, EmailFolder } from '@/services/emailService'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { ContactLinkDialog } from './ContactLinkDialog'
import { useWebSocket } from '@/contexts/websocket-context'
import { useAuth } from '@/features/auth/context'

interface GmailInboxProps {
  className?: string
}

export default function GmailInbox({ className }: GmailInboxProps) {
  const [accounts, setAccounts] = useState<EmailAccount[]>([])
  const [selectedAccount, setSelectedAccount] = useState<EmailAccount | null>(null)
  const [threads, setThreads] = useState<EmailThread[]>([])
  const [selectedThread, setSelectedThread] = useState<EmailThread | null>(null)
  const [threadMessages, setThreadMessages] = useState<EmailMessage[]>([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [messagesLoading, setMessagesLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterStatus, setFilterStatus] = useState<'all' | 'unread' | 'starred'>('all')
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(0)
  const [total, setTotal] = useState(0)
  const itemsPerPage = 20
  const [folders, setFolders] = useState<EmailFolder[]>([])
  const [selectedFolder, setSelectedFolder] = useState<string>('INBOX')
  const [composeOpen, setComposeOpen] = useState(false)
  const [replyMode, setReplyMode] = useState<'reply' | 'forward' | null>(null)
  const [replyToMessage, setReplyToMessage] = useState<EmailMessage | null>(null)
  const [linkDialogOpen, setLinkDialogOpen] = useState(false)
  const [linkDialogThread, setLinkDialogThread] = useState<EmailThread | null>(null)
  const [composeTo, setComposeTo] = useState('')
  const [composeCc, setComposeCc] = useState('')
  const [composeBcc, setComposeBcc] = useState('')
  const [composeSubject, setComposeSubject] = useState('')
  const [composeBody, setComposeBody] = useState('')
  const [sending, setSending] = useState(false)
  const [collapsedMessages, setCollapsedMessages] = useState<Set<string>>(new Set())
  const { toast } = useToast()
  const { subscribe, unsubscribe } = useWebSocket()
  const { user } = useAuth()
  const subscriptionRef = useRef<string | null>(null)

  // Load email accounts on mount
  useEffect(() => {
    loadAccounts()
  }, [])

  // Load threads when account is selected
  useEffect(() => {
    if (selectedAccount) {
      setCurrentPage(1)  // Reset to first page when account changes
      loadThreads(1)
      loadFolders()
    }
  }, [selectedAccount])

  // Load threads when folder changes
  useEffect(() => {
    if (selectedAccount && selectedFolder) {
      setCurrentPage(1)  // Reset to first page when folder changes
      loadThreads(1)
    }
  }, [selectedFolder])
  
  // Subscribe to email storage updates via WebSocket
  useEffect(() => {
    if (!selectedAccount || !user?.id) return
    
    // The backend uses user_{user_id}_email channel pattern
    const channel = `user_${user.id}_email`
    
    // Subscribe to storage updates
    subscriptionRef.current = subscribe(channel, (message) => {
      console.log('📨 Email storage update received:', message)
      
      // Handle email_thread_stored event
      if (message.type === 'email_thread_stored' || message.type === 'sync_progress_update') {
        const threadId = message.thread_id || message.payload?.thread_id
        const stored = message.stored !== undefined ? message.stored : message.payload?.stored
        
        if (threadId) {
          console.log(`📨 Updating thread ${threadId} storage status to: ${stored ? 'stored' : 'syncing'}`)
          
          // Update the thread's storage status in the list
          setThreads(prevThreads => 
            prevThreads.map(thread => {
              if (thread.id === threadId) {
                return {
                  ...thread,
                  stored: stored,
                  should_store: stored ? false : thread.should_store // Clear should_store if stored
                }
              }
              return thread
            })
          )
          
          // Also update selected thread if it matches
          setSelectedThread(prev => {
            if (prev?.id === threadId) {
              return {
                ...prev,
                stored: stored,
                should_store: stored ? false : prev.should_store
              }
            }
            return prev
          })
          
          // Show toast notification
          if (stored) {
            toast({
              title: "Email Stored",
              description: `Email thread has been saved to the CRM database`,
              variant: "default"
            })
          }
        }
      }
    })
    
    console.log(`🔌 Subscribed to email storage updates on channel: ${channel}`)
    
    // Cleanup subscription on unmount or account change
    return () => {
      if (subscriptionRef.current) {
        unsubscribe(subscriptionRef.current)
        console.log(`🔌 Unsubscribed from email storage updates`)
      }
    }
  }, [selectedAccount, user, subscribe, unsubscribe, toast])

  const loadAccounts = async () => {
    try {
      const result = await emailService.getAccounts()
      if (result.success && result.accounts.length > 0) {
        setAccounts(result.accounts)
        // Auto-select first account
        setSelectedAccount(result.accounts[0])
      } else if (result.accounts.length === 0) {
        toast({
          title: 'No email accounts',
          description: 'No email accounts connected. Please connect an email account first.',
          variant: 'default'
        })
      }
    } catch (error) {
      console.error('Failed to load email accounts:', error)
      toast({
        title: 'Error loading accounts',
        description: 'Failed to load email accounts. Please try again.',
        variant: 'destructive'
      })
    } finally {
      setLoading(false)
    }
  }

  const loadThreads = async (page = 1, refresh = false) => {
    if (!selectedAccount) {
      console.log('No selected account, skipping load')
      return
    }
    
    console.log(`📧 Loading email page ${page} (cursor-based, limit: ${itemsPerPage})`)
    
    try {
      setLoading(true)
      
      // Use cursor-based pagination with page parameter
      const result = await emailService.getEmailInbox({
        account_id: selectedAccount.account_id,
        folder: selectedFolder,
        limit: itemsPerPage,
        page: page,  // Use page instead of offset
        search: searchQuery,
        refresh: refresh
      })
      
      console.log(`📧 API response:`, {
        success: result.success,
        conversations: result.conversations?.length || 0,
        page: result.page || page,
        total_pages: result.total_pages,
        has_more: result.has_more
      })
      
      if (result.success) {
        // Update threads - this should trigger a re-render
        const newThreads = result.conversations || []
        console.log(`📧 Setting ${newThreads.length} threads for page ${page}`)
        setThreads(newThreads)
        
        // Update pagination state
        setCurrentPage(result.page || page)
        
        // Calculate total pages
        let calculatedTotalPages = 0
        if (result.total_pages !== undefined) {
          calculatedTotalPages = result.total_pages
        } else if (result.total) {
          // Fallback to calculating from total
          calculatedTotalPages = Math.ceil(result.total / itemsPerPage)
        } else {
          // Estimate based on has_more
          calculatedTotalPages = page + (result.has_more ? 1 : 0)
        }
        setTotalPages(calculatedTotalPages)
        
        const totalCount = result.total || newThreads.length
        setTotal(totalCount)
        
        console.log(`📧 Page ${page} loaded successfully:`, {
          threads: newThreads.length,
          currentPage: page,
          totalPages: calculatedTotalPages,
          total: totalCount
        })
      } else {
        console.error('📧 API returned error:', result)
        toast({
          title: 'Failed to load emails',
          description: result.error || 'Unknown error occurred',
          variant: 'destructive'
        })
      }
    } catch (error) {
      console.error('📧 Failed to load threads:', error)
      toast({
        title: 'Error loading emails',
        description: 'Failed to load email threads. Please try again.',
        variant: 'destructive'
      })
    } finally {
      setLoading(false)
    }
  }

  const loadFolders = async () => {
    if (!selectedAccount) return
    
    try {
      const result = await emailService.getFolders(selectedAccount.account_id)
      if (result.success && result.folders) {
        setFolders(result.folders)
      }
    } catch (error) {
      console.error('Error loading folders:', error)
      // Don't show error toast for folders, just continue with default folders
      setFolders([])
    }
  }

  const loadThreadMessages = async (thread: EmailThread) => {
    try {
      setMessagesLoading(true)
      // Use the thread's account_id from channel_specific, or fall back to selected account
      const accountId = thread.channel_specific?.account_id || selectedAccount?.account_id || selectedAccount?.id
      // Use thread.id since that's what the inbox returns (not thread_id)
      const result = await emailService.getThreadMessages(thread.id, accountId)
      
      if (result.success) {
        setThreadMessages(result.messages)
        
        // Mark thread as read if it has unread messages
        if (thread.unread_count > 0) {
          // Update local state only - backend will handle read status through sync
          setThreads(prev => prev.map(t => 
            t.id === thread.id
              ? { ...t, unread_count: 0 }
              : t
          ))
          
          // Note: In a local-first architecture, read status is typically handled
          // through the sync process, not individual API calls
        }
      }
    } catch (error) {
      console.error('Failed to load messages:', error)
      toast({
        title: 'Error loading messages',
        description: 'Failed to load email messages. Please try again.',
        variant: 'destructive'
      })
    } finally {
      setMessagesLoading(false)
    }
  }

  const handleThreadSelect = (thread: EmailThread) => {
    setSelectedThread(thread)
    loadThreadMessages(thread)
  }

  const handleSync = async () => {
    if (!selectedAccount) return
    
    setSyncing(true)
    try {
      // Force refresh the current page (clears cursor cache)
      await loadThreads(currentPage, true)
      
      toast({
        title: 'Emails refreshed',
        description: 'Fetched latest emails from your inbox',
      })
      
      // Also trigger a background sync for deep sync
      emailService.syncEmail(selectedAccount.account_id, {
        sync_type: 'incremental',
        days_back: 7
      }).then(result => {
        if (!result.success) {
          console.error('Background sync failed:', result.error)
        }
      })
    } catch (error) {
      console.error('Refresh error:', error)
      toast({
        title: 'Refresh error',
        description: 'Failed to refresh emails',
        variant: 'destructive'
      })
    } finally {
      setSyncing(false)
    }
  }


  const handleDelete = async () => {
    if (!selectedThread || !selectedAccount) return
    
    try {
      // For now, just remove from local state
      setThreads(prev => prev.filter(t => t.id !== selectedThread.id))
      setSelectedThread(null)
      setThreadMessages([])
      
      toast({
        title: 'Success',
        description: 'Email thread deleted',
      })
    } catch (error) {
      console.error('Error deleting thread:', error)
      toast({
        title: 'Error',
        description: 'Failed to delete thread',
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

  const handleReply = (message?: EmailMessage) => {
    if (!selectedThread || !selectedAccount) return
    
    const targetMessage = message || threadMessages[threadMessages.length - 1]
    if (!targetMessage) return
    
    setReplyMode('reply')
    setReplyToMessage(targetMessage)
    setComposeTo(targetMessage.sender.email)
    setComposeSubject(`Re: ${targetMessage.subject || selectedThread.subject || ''}`)
    setComposeBody(`\n\n---\nOn ${targetMessage.sent_at ? new Date(targetMessage.sent_at).toLocaleString() : 'Unknown date'}, ${targetMessage.sender.name || targetMessage.sender.email} wrote:\n${targetMessage.content}`)
    setComposeOpen(true)
  }

  const handleForward = () => {
    if (!selectedThread || !threadMessages.length) return
    
    const lastMessage = threadMessages[threadMessages.length - 1]
    setReplyMode('forward')
    setReplyToMessage(lastMessage)
    setComposeTo('')
    setComposeSubject(`Fwd: ${lastMessage.subject || selectedThread.subject || ''}`)
    setComposeBody(`\n\n--- Forwarded message ---\nFrom: ${lastMessage.sender.name || lastMessage.sender.email}\nDate: ${lastMessage.sent_at ? new Date(lastMessage.sent_at).toLocaleString() : 'Unknown date'}\nSubject: ${lastMessage.subject || ''}\n\n${lastMessage.content}`)
    setComposeOpen(true)
  }

  const handleCompose = () => {
    setReplyMode(null)
    setReplyToMessage(null)
    setComposeTo('')
    setComposeCc('')
    setComposeBcc('')
    setComposeSubject('')
    setComposeBody('')
    setComposeOpen(true)
  }

  const handleSendEmail = async () => {
    if (!selectedAccount) return
    
    setSending(true)
    try {
      const toRecipients = composeTo.split(',').map(e => e.trim()).filter(e => e)
      const ccRecipients = composeCc ? composeCc.split(',').map(e => e.trim()).filter(e => e) : []
      const bccRecipients = composeBcc ? composeBcc.split(',').map(e => e.trim()).filter(e => e) : []
      
      if (toRecipients.length === 0) {
        toast({
          title: 'Error',
          description: 'Please enter at least one recipient',
          variant: 'destructive'
        })
        setSending(false)
        return
      }
      
      const result = await emailService.sendEmail({
        account_id: selectedAccount.account_id,
        to: toRecipients,
        cc: ccRecipients,
        bcc: bccRecipients,
        subject: composeSubject,
        body: composeBody,
        reply_to_message_id: replyMode === 'reply' && replyToMessage ? replyToMessage.external_id : undefined
      })
      
      if (result.success) {
        toast({
          title: 'Success',
          description: 'Email sent successfully',
        })
        setComposeOpen(false)
        // Reload threads to show the sent email
        loadThreads(true)
      } else {
        throw new Error(result.error || 'Failed to send email')
      }
    } catch (error: any) {
      console.error('Error sending email:', error)
      toast({
        title: 'Error',
        description: error.message || 'Failed to send email',
        variant: 'destructive'
      })
    } finally {
      setSending(false)
    }
  }

  // Filter threads based on search and filter status
  const filteredThreads = threads.filter(thread => {
    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      const subjectMatch = (thread.subject || '').toLowerCase().includes(query)
      const participantMatch = thread.participants && thread.participants.some(p => {
        // Participants are always objects from our backend
        return (p.email || '').toLowerCase().includes(query) ||
               (p.name || '').toLowerCase().includes(query)
      })
      
      // Also search in linked contact/company names
      const contactMatch = thread.linked_records?.contacts?.some(c => 
        (c.name || '').toLowerCase().includes(query)
      )
      const companyMatch = thread.linked_records?.companies?.some(c => 
        (c.pipeline || '').toLowerCase().includes(query)
      )
      
      if (!subjectMatch && !participantMatch && !contactMatch && !companyMatch) {
        return false
      }
    }

    // Apply status filter
    switch (filterStatus) {
      case 'unread':
        return thread.unread_count > 0
      case 'starred':
        // For now, we don't have starred status in the backend
        return false
      default:
        return true
    }
  })

  const getParticipantDisplay = (thread: EmailThread) => {
    if (!thread.participants || thread.participants.length === 0) {
      return { names: 'Unknown', email: '', initial: '?', count: 0 }
    }
    
    // Filter out the current user's email if we have it
    const otherParticipants = selectedAccount?.email 
      ? thread.participants.filter(p => p.email !== selectedAccount.email)
      : thread.participants
    
    // If all participants were the current user, show the current user
    const displayParticipants = otherParticipants.length > 0 ? otherParticipants : thread.participants
    
    // Get up to 3 participant names for display
    const participantNames = displayParticipants.slice(0, 3).map(participant => {
      // Participants are always objects from our backend
      const name = participant.name || participant.email?.split('@')[0] || 'Unknown'
      // If name is email, just show the part before @
      return name.includes('@') ? name.split('@')[0] : name
    })
    
    // Create display string
    let displayNames = participantNames[0]
    if (displayParticipants.length === 2) {
      displayNames = participantNames.join(' & ')
    } else if (displayParticipants.length > 2) {
      displayNames = participantNames.slice(0, 2).join(', ')
      if (displayParticipants.length > 3) {
        displayNames += ` +${displayParticipants.length - 2}`
      } else if (participantNames[2]) {
        displayNames += `, ${participantNames[2]}`
      }
    }
    
    const firstParticipant = displayParticipants[0]
    const email = firstParticipant?.email || ''
    const initial = participantNames[0]?.charAt(0).toUpperCase() || '?'
    
    return { 
      names: displayNames || 'Unknown', 
      email, 
      initial,
      count: displayParticipants.length 
    }
  }

  const formatRelativeDate = (date: Date) => {
    const now = new Date()
    const diffInHours = (now.getTime() - date.getTime()) / (1000 * 60 * 60)
    
    if (diffInHours < 1) {
      return formatDistanceToNow(date, { addSuffix: true })
    } else if (diffInHours < 24) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    } else if (diffInHours < 48) {
      return 'Yesterday'
    } else if (diffInHours < 168) { // 7 days
      return date.toLocaleDateString([], { weekday: 'short' })
    } else {
      return date.toLocaleDateString([], { month: 'short', day: 'numeric' })
    }
  }

  if (loading && threads.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-500"></div>
        <p className="ml-4 text-gray-600">Loading email...</p>
      </div>
    )
  }

  return (
    <div className={`h-full flex flex-col ${className}`}>
      {/* Header with Account Selection and Filters */}
      <div className="p-4 border-b bg-white dark:bg-gray-900 flex-shrink-0">
        <div className="flex items-center space-x-4 mb-3">
          {/* Account Selection */}
          {accounts.length > 0 && (
            <Select 
              value={selectedAccount?.id || ''} 
              onValueChange={(value) => {
                const account = accounts.find(a => a.id === value)
                setSelectedAccount(account || null)
              }}
            >
              <SelectTrigger className="w-64">
                <Mail className="w-4 h-4 mr-2" />
                <SelectValue placeholder="Select email account" />
              </SelectTrigger>
              <SelectContent>
                {accounts.map(account => (
                  <SelectItem key={account.id} value={account.id}>
                    {account.email} ({account.provider})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}

          {/* Compose Button */}
          <Button 
            size="sm"
            onClick={handleCompose}
            disabled={!selectedAccount}
          >
            <Plus className="w-4 h-4 mr-2" />
            Compose
          </Button>

          {/* Sync Button */}
          <Button 
            variant="outline" 
            size="sm"
            onClick={handleSync}
            disabled={!selectedAccount || syncing}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${syncing ? 'animate-spin' : ''}`} />
            {syncing ? 'Syncing...' : 'Sync'}
          </Button>

          {/* Stats */}
          {selectedAccount && (
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <Badge variant="outline">
                Page {currentPage} of {totalPages || 1}
              </Badge>
              <Badge variant="outline">
                {total || threads.length} total
              </Badge>
              {threads.filter(t => t.unread_count > 0).length > 0 && (
                <Badge variant="destructive">
                  {threads.filter(t => t.unread_count > 0).length} unread
                </Badge>
              )}
            </div>
          )}
        </div>

        {/* Search and Filters */}
        <div className="flex items-center space-x-4">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <Input
                placeholder="Search email conversations..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>
          
          {/* Folder Selection */}
          <Select value={selectedFolder} onValueChange={setSelectedFolder}>
            <SelectTrigger className="w-40">
              <Folder className="w-4 h-4 mr-2" />
              <SelectValue placeholder="Folder" />
            </SelectTrigger>
            <SelectContent className="max-h-[400px] overflow-y-auto">
              {/* Show all folders from UniPile */}
              {folders.length > 0 ? (
                <>
                  {/* Primary folders first */}
                  {folders
                    .filter(f => ['inbox', 'sent', 'drafts', 'trash', 'spam', 'all', 'important', 'starred'].includes(f.role || ''))
                    .map(folder => (
                      <SelectItem 
                        key={folder.id || folder.provider_id} 
                        value={folder.provider_id || folder.id || folder.name}
                      >
                        <div className="flex items-center justify-between w-full">
                          <span className="font-medium">{folder.name}</span>
                          {folder.nb_mails !== undefined && folder.nb_mails > 0 && (
                            <span className="ml-2 text-xs text-muted-foreground">
                              {folder.nb_mails}
                            </span>
                          )}
                        </div>
                      </SelectItem>
                    ))
                  }
                  
                  {/* Separator if there are custom folders */}
                  {folders.some(f => !['inbox', 'sent', 'drafts', 'trash', 'spam', 'all', 'important', 'starred'].includes(f.role || '')) && 
                   folders.some(f => ['inbox', 'sent', 'drafts', 'trash', 'spam', 'all', 'important', 'starred'].includes(f.role || '')) && (
                    <SelectSeparator />
                  )}
                  
                  {/* Custom/Label folders */}
                  {folders
                    .filter(f => !['inbox', 'sent', 'drafts', 'trash', 'spam', 'all', 'important', 'starred'].includes(f.role || ''))
                    .sort((a, b) => a.name.localeCompare(b.name))
                    .map(folder => (
                      <SelectItem 
                        key={folder.id || folder.provider_id} 
                        value={folder.provider_id || folder.id || folder.name}
                      >
                        <div className="flex items-center justify-between w-full">
                          <span>{folder.name}</span>
                          {folder.nb_mails !== undefined && folder.nb_mails > 0 && (
                            <span className="ml-2 text-xs text-muted-foreground">
                              {folder.nb_mails}
                            </span>
                          )}
                        </div>
                      </SelectItem>
                    ))
                  }
                </>
              ) : (
                // Fallback to default folders if no folders loaded
                <>
                  <SelectItem value="INBOX">Inbox</SelectItem>
                  <SelectItem value="[Gmail]/Sent Mail">Sent</SelectItem>
                  <SelectItem value="[Gmail]/Drafts">Drafts</SelectItem>
                  <SelectItem value="[Gmail]/Trash">Trash</SelectItem>
                  <SelectItem value="[Gmail]/Spam">Spam</SelectItem>
                </>
              )}
            </SelectContent>
          </Select>

          <Select value={filterStatus} onValueChange={(value: any) => setFilterStatus(value)}>
            <SelectTrigger className="w-32">
              <SelectValue placeholder="Filter" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="unread">Unread</SelectItem>
              <SelectItem value="starred">Starred</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Thread List */}
        <div className="w-1/3 min-w-[300px] max-w-[400px] border-r bg-gray-50 dark:bg-gray-900/50 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto">
            {!selectedAccount ? (
              <div className="p-8 text-center text-gray-500">
                <Mail className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                <p>No email account connected</p>
                <p className="text-sm mt-2">Please connect an email account to view messages</p>
              </div>
            ) : filteredThreads.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <Mail className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                <p>No emails found</p>
                {searchQuery && <p className="text-sm mt-2">Try adjusting your search</p>}
              </div>
            ) : (
              <div className="space-y-1 p-2 pb-12">
                {filteredThreads.map((thread, index) => {
                  const participant = getParticipantDisplay(thread)
                  const isSelected = selectedThread?.id === thread.id
                  
                  return (
                    <div
                      key={thread.id || `thread-${index}`}
                      className={`cursor-pointer transition-colors border-b hover:bg-white dark:hover:bg-gray-800 ${
                        isSelected ? 'bg-white dark:bg-gray-800 border-l-2 border-l-red-500' : ''
                      } px-4 py-3`}
                      onClick={() => handleThreadSelect(thread)}
                    >
                        {/* Storage Status & Link Indicators - Now at the top */}
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-1 flex-wrap">
                          {/* Storage indicator */}
                          {thread.stored ? (
                            <div className="flex items-center gap-1 bg-purple-50 px-2 py-0.5 rounded-full" title="Saved to Oneo CRM">
                              <Cloud className="w-3 h-3 text-purple-600" />
                              <span className="text-xs text-purple-600 font-medium">Saved</span>
                            </div>
                          ) : thread.should_store ? (
                            <div className="flex items-center gap-1 bg-yellow-50 px-2 py-0.5 rounded-full" title="Syncing to CRM database (matches contact)">
                              <Cloud className="w-3 h-3 text-yellow-600 animate-pulse" />
                              <span className="text-xs text-yellow-600 font-medium">Syncing</span>
                            </div>
                          ) : null}
                          
                          {/* Show individual chip for each contact from linked_records */}
                          {thread.linked_records?.contacts?.map((contact, idx) => (
                            <div key={`contact-${idx}`} className="flex items-center gap-1 bg-green-50 px-2 py-0.5 rounded-full" 
                                 title={`Contact: ${contact.title || contact.name}`}>
                              <User className="w-3 h-3 text-green-600" />
                              <span className="text-xs text-green-600 font-medium">
                                {contact.title || contact.name || 'Contact'}
                              </span>
                            </div>
                          ))}
                          
                          {/* Show individual chip for each contact from participants (if not in linked_records) */}
                          {!thread.linked_records?.contacts?.length && thread.participants?.filter(p => p.has_contact).map((participant, idx) => {
                            const recordTitle = participant.contact_record_title || participant.contact_record_name || participant.name || 'Contact'
                            return (
                              <div key={`participant-contact-${idx}`} className="flex items-center gap-1 bg-green-50 px-2 py-0.5 rounded-full"
                                   title={`Contact: ${recordTitle}`}>
                                <User className="w-3 h-3 text-green-600" />
                                <span className="text-xs text-green-600 font-medium">
                                  {recordTitle}
                                </span>
                              </div>
                            )
                          })}
                          
                          {/* Show pipeline chips for contacts */}
                          {(() => {
                            const contactPipelines = new Set()
                            // Collect pipelines from participants
                            thread.participants?.forEach(p => {
                              if (p.has_contact && p.contact_pipeline) {
                                contactPipelines.add(p.contact_pipeline)
                              }
                            })
                            return Array.from(contactPipelines).map((pipeline: string, idx) => (
                              <div key={`contact-pipeline-${idx}`} className="flex items-center gap-1 bg-orange-50 px-2 py-0.5 rounded-full"
                                   title={`Pipeline: ${pipeline}`}>
                                <svg className="w-3 h-3 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                                </svg>
                                <span className="text-xs text-orange-600 font-medium">
                                  {pipeline}
                                </span>
                              </div>
                            ))
                          })()}
                          
                          {/* Show individual chip for each company from linked_records */}
                          {thread.linked_records?.companies?.map((company, idx) => (
                            <div key={`company-${idx}`} className="flex items-center gap-1 bg-blue-50 px-2 py-0.5 rounded-full"
                                 title={`Company: ${company.title || company.name || 'Unknown Company'}`}>
                              <Users className="w-3 h-3 text-blue-600" />
                              <span className="text-xs text-blue-600 font-medium">
                                {company.title || company.name || 'Unknown'}
                              </span>
                            </div>
                          ))}
                          
                          {/* Show individual chip for each company from participants (if not in linked_records) */}
                          {!thread.linked_records?.companies?.length && thread.participants?.filter(p => p.has_secondary).map((participant, idx) => {
                            const companyTitle = participant.secondary_record_title || participant.secondary_record_name || 'Company'
                            return (
                              <div key={`participant-company-${idx}`} className="flex items-center gap-1 bg-blue-50 px-2 py-0.5 rounded-full"
                                   title={`Company: ${companyTitle}`}>
                                <Users className="w-3 h-3 text-blue-600" />
                                <span className="text-xs text-blue-600 font-medium">
                                  {companyTitle}
                                </span>
                              </div>
                            )
                          })}
                          
                          {/* Show pipeline chips for companies */}
                          {(() => {
                            const companyPipelines = new Set()
                            // Collect pipelines from linked_records
                            thread.linked_records?.companies?.forEach(c => {
                              if (c.pipeline) {
                                companyPipelines.add(c.pipeline)
                              }
                            })
                            // Collect pipelines from participants
                            thread.participants?.forEach(p => {
                              if (p.has_secondary && p.secondary_pipeline) {
                                companyPipelines.add(p.secondary_pipeline)
                              }
                            })
                            return Array.from(companyPipelines).map((pipeline: string, idx) => (
                              <div key={`company-pipeline-${idx}`} className="flex items-center gap-1 bg-indigo-50 px-2 py-0.5 rounded-full"
                                   title={`Pipeline: ${pipeline}`}>
                                <svg className="w-3 h-3 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                                </svg>
                                <span className="text-xs text-indigo-600 font-medium">
                                  {pipeline}
                                </span>
                              </div>
                            ))
                          })()}
                          
                          {/* Show link button if can link */}
                          {thread.can_link && !thread.stored ? (
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                setLinkDialogThread(thread)
                                setLinkDialogOpen(true)
                              }}
                              className="flex items-center gap-1 bg-gray-50 hover:bg-gray-100 px-2 py-0.5 rounded-full transition-colors"
                              title="Link to CRM record"
                            >
                              <Link className="w-3 h-3 text-gray-600" />
                              <span className="text-xs text-gray-600 font-medium">Link</span>
                            </button>
                          ) : null}
                        
                          {/* Show unlinked if no matches */}
                          {thread.participants && !thread.participants.some(p => p.has_contact || p.has_secondary) && !thread.stored && (
                            <div className="flex items-center gap-1 bg-gray-50 px-2 py-0.5 rounded-full">
                              <Unlink className="w-3 h-3 text-gray-400" />
                              <span className="text-xs text-gray-400">Not linked</span>
                            </div>
                          )}
                          </div>
                          
                          {/* Timestamp on the right */}
                          <div className="text-xs text-gray-500">
                            {formatDistanceToNow(new Date(thread.last_message_at || thread.created_at || new Date()), { addSuffix: true })}
                          </div>
                        </div>
                        
                        {/* Main content - Names, subject, preview */}
                        <div className="flex items-start justify-between">
                          <div className="flex items-start space-x-3 flex-1 min-w-0">
                            {/* Avatar - Show group icon for multiple participants */}
                            {participant.count > 2 ? (
                              <div className="w-8 h-8 flex-shrink-0 bg-blue-100 rounded-full flex items-center justify-center">
                                <Users className="w-4 h-4 text-blue-700" />
                              </div>
                            ) : (
                              <SafeAvatar
                                src=""
                                fallbackText={participant.initial}
                                className="w-8 h-8 flex-shrink-0"
                                fallbackClassName="bg-red-100 text-red-700 text-xs"
                              />
                            )}
                            
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center justify-between mb-1">
                                <h3 className={`text-sm truncate ${
                                  thread.unread_count > 0 ? 'font-bold' : 'font-medium'
                                }`} title={participant.count > 3 ? `${participant.count} participants` : participant.names}>
                                  {participant.names}
                                </h3>
                              </div>
                              
                              <p className={`text-sm mb-1 truncate ${
                                thread.unread_count > 0 ? 'font-bold text-gray-900' : 'text-gray-700'
                              }`}>
                                {thread.subject || '(No subject)'}
                              </p>
                              
                              <div className="flex items-center justify-between">
                                <span className="text-xs text-gray-500">
                                  {participant.count > 0 ? (
                                    <>
                                      {participant.count} participant{participant.count !== 1 ? 's' : ''} • 
                                    </>
                                  ) : null}
                                  {thread.message_count} message{thread.message_count !== 1 ? 's' : ''}
                                </span>
                                {thread.unread_count > 0 && (
                                  <Badge variant="destructive" className="text-xs">
                                    {thread.unread_count} new
                                  </Badge>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                    </div>
                  )
                })}
                
                {/* Pagination Controls */}
                {totalPages > 1 && (
                  <div className="p-3 border-t bg-gray-50 dark:bg-gray-800">
                    <div className="flex items-center justify-between">
                      <div className="text-xs text-gray-600 dark:text-gray-400">
                        Page {currentPage} of {totalPages} ({total} total)
                      </div>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            console.log('📧 First page button clicked')
                            loadThreads(1)
                          }}
                          disabled={currentPage === 1 || loading}
                          className="h-8 w-8 p-0"
                        >
                          <ChevronsLeft className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            console.log(`📧 Previous page button clicked (going to page ${currentPage - 1})`)
                            loadThreads(currentPage - 1)
                          }}
                          disabled={currentPage === 1 || loading}
                          className="h-8 w-8 p-0"
                        >
                          <ChevronLeft className="w-4 h-4" />
                        </Button>
                        
                        {/* Page numbers */}
                        {(() => {
                          const pages = []
                          const maxButtons = 5
                          let startPage = Math.max(1, currentPage - Math.floor(maxButtons / 2))
                          let endPage = Math.min(totalPages, startPage + maxButtons - 1)
                          
                          if (endPage - startPage < maxButtons - 1) {
                            startPage = Math.max(1, endPage - maxButtons + 1)
                          }
                          
                          for (let i = startPage; i <= endPage; i++) {
                            pages.push(
                              <Button
                                key={i}
                                variant={i === currentPage ? "default" : "outline"}
                                size="sm"
                                onClick={() => {
                                  console.log(`📧 Page ${i} button clicked`)
                                  loadThreads(i)
                                }}
                                disabled={loading}
                                className="h-8 w-8 p-0"
                              >
                                {i}
                              </Button>
                            )
                          }
                          return pages
                        })()}
                        
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            console.log(`📧 Next page button clicked (going to page ${currentPage + 1})`)
                            loadThreads(currentPage + 1)
                          }}
                          disabled={currentPage === totalPages || loading}
                          className="h-8 w-8 p-0"
                        >
                          <ChevronRight className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            console.log(`📧 Last page button clicked (going to page ${totalPages})`)
                            loadThreads(totalPages)
                          }}
                          disabled={currentPage === totalPages || loading}
                          className="h-8 w-8 p-0"
                        >
                          <ChevronsRight className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Message View */}
        <div className="flex-1 bg-white dark:bg-gray-900 flex flex-col overflow-hidden">
          {selectedThread ? (
            <div className="h-full flex flex-col">
              {/* Thread Header - Fixed height */}
              <div className="p-4 border-b flex-shrink-0">
                {/* Contact Link Status Banner */}
                {!selectedThread.contact_linked && (
                  <div className="mb-3 p-2 bg-yellow-50 border border-yellow-200 rounded-lg flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Unlink className="w-4 h-4 text-yellow-600" />
                      <span className="text-sm text-yellow-800">
                        This conversation is not linked to a contact
                        {selectedThread.contact_confidence && selectedThread.contact_confidence > 0.3 && (
                          <span className="font-medium ml-1">
                            ({Math.round(selectedThread.contact_confidence * 100)}% potential match found)
                          </span>
                        )}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button 
                        size="sm" 
                        variant="outline"
                        onClick={() => {
                          setLinkDialogThread(selectedThread)
                          setLinkDialogOpen(true)
                        }}
                        className="text-xs"
                      >
                        <Link className="w-3 h-3 mr-1" />
                        Link to Contact
                      </Button>
                      <Button 
                        size="sm" 
                        variant="default"
                        onClick={() => {
                          setLinkDialogThread(selectedThread)
                          setLinkDialogOpen(true)
                        }}
                        className="text-xs bg-yellow-600 hover:bg-yellow-700"
                      >
                        <UserPlus className="w-3 h-3 mr-1" />
                        Create Contact
                      </Button>
                    </div>
                  </div>
                )}
                
                {/* Linked Contact Banner */}
                {selectedThread.contact_linked && (
                  <div className="mb-3 p-2 bg-green-50 border border-green-200 rounded-lg flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Link className="w-4 h-4 text-green-600" />
                      <span className="text-sm text-green-800">
                        Linked to: <span className="font-medium">{selectedThread.contact_name || 'Contact'}</span>
                      </span>
                    </div>
                    <Button 
                      size="sm" 
                      variant="ghost"
                      onClick={() => console.log('View contact', selectedThread.contact_id)}
                      className="text-xs text-green-700 hover:text-green-800"
                    >
                      <User className="w-3 h-3 mr-1" />
                      View Contact
                    </Button>
                  </div>
                )}
                
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <SafeAvatar
                      src=""
                      fallbackText={getParticipantDisplay(selectedThread).initial}
                      className="w-10 h-10"
                      fallbackClassName="bg-red-100 text-red-700"
                    />
                    <div className="flex-1">
                      <h2 className="text-lg font-bold">{selectedThread.subject || '(No subject)'}</h2>
                      <div className="flex items-center gap-2 text-sm text-gray-600">
                        <span>
                          {selectedThread.participants?.length || 0} participant{selectedThread.participants?.length !== 1 ? 's' : ''} • 
                          {selectedThread.message_count} message{selectedThread.message_count !== 1 ? 's' : ''}
                        </span>
                      </div>
                      {/* Show participant emails in a collapsible list */}
                      {selectedThread.participants && selectedThread.participants.length > 0 && (
                        <div className="mt-1 flex flex-wrap gap-1">
                          {selectedThread.participants.slice(0, 3).map((p, idx) => (
                            <span key={idx} className="inline-flex items-center gap-1 text-xs text-gray-500">
                              {p.has_contact && <User className="w-3 h-3 text-green-600" />}
                              <span title={p.email}>{p.name || p.email}</span>
                              {idx < Math.min(selectedThread.participants.length - 1, 2) && <span>,</span>}
                            </span>
                          ))}
                          {selectedThread.participants.length > 3 && (
                            <span className="text-xs text-gray-500">
                              +{selectedThread.participants.length - 3} more
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
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

              {/* Messages - Scrollable area */}
              <div className="flex-1 overflow-y-auto p-6 pb-16">
                {messagesLoading ? (
                  <div className="flex items-center justify-center h-32">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-red-500"></div>
                  </div>
                ) : threadMessages.length === 0 ? (
                  <div className="text-center text-gray-500">
                    <p>No messages found in this thread</p>
                  </div>
                ) : (
                  <div className="space-y-4 pb-8">
                    {threadMessages.map((message, index) => {
                      const messageId = message.id || message.external_id || `message-${index}`
                      const isCollapsed = collapsedMessages.has(messageId)
                      
                      return (
                        <div key={messageId} className="bg-white border rounded-lg">
                          {/* Message Header - Always visible */}
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
                                  {message.sent_at 
                                    ? new Date(message.sent_at).toLocaleString()
                                    : 'Unknown time'}
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
                                    metadata={message.metadata}
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
                                        <Button 
                                          variant="ghost" 
                                          size="sm" 
                                          className="ml-auto flex-shrink-0"
                                          onClick={() => {
                                            // TODO: Implement download
                                            console.log('Download attachment:', attachment.id)
                                          }}
                                        >
                                          Download
                                        </Button>
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
              </div>
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

      {/* Compose/Reply Dialog */}
      <Dialog open={composeOpen} onOpenChange={setComposeOpen}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {replyMode === 'reply' ? 'Reply to Email' : replyMode === 'forward' ? 'Forward Email' : 'New Email'}
            </DialogTitle>
            <DialogDescription>
              {selectedAccount && `Sending from ${selectedAccount.email}`}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <div className="grid gap-2">
              <Label htmlFor="to">To</Label>
              <Input
                id="to"
                placeholder="recipient@example.com, another@example.com"
                value={composeTo}
                onChange={(e) => setComposeTo(e.target.value)}
                disabled={sending}
              />
            </div>
            
            <div className="grid gap-2">
              <Label htmlFor="cc">CC</Label>
              <Input
                id="cc"
                placeholder="cc@example.com"
                value={composeCc}
                onChange={(e) => setComposeCc(e.target.value)}
                disabled={sending}
              />
            </div>
            
            <div className="grid gap-2">
              <Label htmlFor="bcc">BCC</Label>
              <Input
                id="bcc"
                placeholder="bcc@example.com"
                value={composeBcc}
                onChange={(e) => setComposeBcc(e.target.value)}
                disabled={sending}
              />
            </div>
            
            <div className="grid gap-2">
              <Label htmlFor="subject">Subject</Label>
              <Input
                id="subject"
                placeholder="Email subject"
                value={composeSubject}
                onChange={(e) => setComposeSubject(e.target.value)}
                disabled={sending}
              />
            </div>
            
            <div className="grid gap-2">
              <Label htmlFor="body">Message</Label>
              <Textarea
                id="body"
                placeholder="Type your message here..."
                value={composeBody}
                onChange={(e) => setComposeBody(e.target.value)}
                rows={12}
                disabled={sending}
              />
            </div>
          </div>
          
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setComposeOpen(false)}
              disabled={sending}
            >
              Cancel
            </Button>
            <Button
              onClick={handleSendEmail}
              disabled={sending || !composeTo.trim() || !composeSubject.trim()}
            >
              {sending ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                  Sending...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4 mr-2" />
                  Send
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
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
            loadThreads()
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