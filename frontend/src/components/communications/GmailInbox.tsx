'use client'

import React, { useState, useEffect, useCallback, useRef } from 'react'
import { Mail, MailOpen, Search, Filter, Archive, Reply, Forward, Star, StarOff, MoreVertical, Paperclip, RefreshCw, Trash, Send, X, Folder, Edit, Plus, Link, Unlink, User, Users, UserPlus, Cloud, ChevronDown, ChevronRight, ChevronLeft, ChevronsLeft, ChevronsRight } from 'lucide-react'
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
  const [hasMorePages, setHasMorePages] = useState(false)
  const [totalPages, setTotalPages] = useState(0) // Keep for backwards compatibility
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
  const editorRef = useRef<HTMLDivElement>(null)
  const [editorKey, setEditorKey] = useState(0)
  const lastOpenState = useRef(false)

  // When dialog opens, increment key to force editor remount
  useEffect(() => {
    // Only run when dialog transitions from closed to open
    if (composeOpen && !lastOpenState.current) {
      // Force editor to remount with new content
      setEditorKey(prev => prev + 1)
      
      // Set initial content after remount
      setTimeout(() => {
        if (editorRef.current && composeBody) {
          editorRef.current.innerHTML = composeBody
          
          // Place cursor at the beginning for replies/forwards
          if (replyMode && editorRef.current.firstChild) {
            const range = document.createRange()
            const sel = window.getSelection()
            range.setStart(editorRef.current.firstChild, 0)
            range.collapse(true)
            sel?.removeAllRanges()
            sel?.addRange(range)
          }
        }
      }, 0)
    }
    
    // Track the last open state
    lastOpenState.current = composeOpen
  }, [composeOpen, composeBody, replyMode]) // Include all dependencies

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
  
  // Load threads when filter changes
  useEffect(() => {
    if (selectedAccount) {
      setCurrentPage(1)  // Reset to first page when filter changes
      loadThreads(1)
    }
  }, [filterStatus])
  
  // Subscribe to email storage updates via WebSocket
  useEffect(() => {
    if (!selectedAccount || !user?.id) return
    
    // The backend uses user_{user_id}_email channel pattern
    const channel = `user_${user.id}_email`
    
    // Subscribe to storage updates
    subscriptionRef.current = subscribe(channel, (message) => {
      console.log('📨 Email storage update received:', message)
      
      // Handle email_thread_stored event
      if ((message as any).type === 'email_thread_stored' || (message as any).type === 'sync_progress_update') {
        const threadId = (message as any).thread_id || message.payload?.thread_id
        const stored = (message as any).stored !== undefined ? (message as any).stored : message.payload?.stored
        
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
            if (prev && prev.id === threadId) {
              return {
                ...prev,
                stored: stored,
                should_store: stored ? false : prev.should_store
              } as EmailThread
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
        refresh: refresh,
        filter: filterStatus  // Pass filter parameter to API
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
        
        // For cursor-based pagination, we don't know exact totals
        // Store has_more flag instead
        const hasMore = result.has_more || false
        setHasMorePages(hasMore)
        
        // Don't show misleading total pages or count
        // With cursor pagination, we don't know the grand total
        setTotalPages(0)
        setTotal(0)
        
        console.log(`📧 Page ${page} loaded successfully:`, {
          threads: newThreads.length,
          currentPage: page,
          hasMore: hasMore
        })
      } else {
        console.error('📧 API returned error:', result)
        toast({
          title: 'Failed to load emails',
          description: (result as any).error || 'Unknown error occurred',
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
      // Use external_thread_id if available (this is the UniPile ID)
      // Otherwise use the thread.id (which might be the same)
      const emailIdToDelete = selectedThread.external_thread_id || selectedThread.id
      
      // Call UniPile API to delete the email
      const result = await emailService.deleteEmail(selectedAccount.account_id, emailIdToDelete)
      
      if (result.success) {
        // Remove from local state after successful deletion
        setThreads(prev => prev.filter(t => t.id !== selectedThread.id))
        setSelectedThread(null)
        setThreadMessages([])
        
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

  const handleReply = (message?: EmailMessage) => {
    if (!selectedThread || !selectedAccount) return
    
    const targetMessage = message || threadMessages[threadMessages.length - 1]
    if (!targetMessage) return
    
    setReplyMode('reply')
    setReplyToMessage(targetMessage)
    setComposeTo(targetMessage.sender.email)
    setComposeSubject(`Re: ${targetMessage.subject || selectedThread.subject || ''}`)
    
    // Create HTML-formatted reply with proper separation
    const replyBody = `<br><br><br>
<div style="border-top: 1px solid #ccc; padding-top: 10px; margin-top: 20px;">
  <div style="color: #666; font-size: 14px; margin-bottom: 10px;">
    On ${targetMessage.sent_at ? new Date(targetMessage.sent_at).toLocaleString() : 'Unknown date'}, ${targetMessage.sender.name || targetMessage.sender.email} wrote:
  </div>
  <blockquote style="margin: 0 0 0 10px; padding-left: 10px; border-left: 2px solid #ccc;">
    ${targetMessage.content}
  </blockquote>
</div>`
    
    setComposeBody(replyBody)
    setComposeOpen(true)
  }

  const handleForward = () => {
    if (!selectedThread || !threadMessages.length) return
    
    const lastMessage = threadMessages[threadMessages.length - 1]
    setReplyMode('forward')
    setReplyToMessage(lastMessage)
    setComposeTo('')
    setComposeSubject(`Fwd: ${lastMessage.subject || selectedThread.subject || ''}`)
    
    // Create HTML-formatted forward with proper separation
    const forwardBody = `<br><br><br>
<div style="border: 1px solid #ccc; padding: 15px; margin-top: 20px; background-color: #f9f9f9;">
  <div style="font-weight: bold; margin-bottom: 10px;">––––––––– Forwarded Message –––––––––</div>
  <div style="color: #666; font-size: 14px; margin-bottom: 10px;">
    <strong>From:</strong> ${lastMessage.sender.name || lastMessage.sender.email} &lt;${lastMessage.sender.email}&gt;<br>
    <strong>Date:</strong> ${lastMessage.sent_at ? new Date(lastMessage.sent_at).toLocaleString() : 'Unknown date'}<br>
    <strong>Subject:</strong> ${lastMessage.subject || selectedThread.subject || '(No subject)'}<br>
    <strong>To:</strong> ${lastMessage.recipients?.to?.join(', ') || 'Unknown recipients'}
  </div>
  <div style="margin-top: 15px;">
    ${lastMessage.content}
  </div>
</div>`
    
    setComposeBody(forwardBody)
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
    // Clear the editor
    if (editorRef.current) {
      editorRef.current.innerHTML = ''
    }
    setComposeOpen(true)
  }

  const handleMarkAsRead = async (thread: EmailThread, e: React.MouseEvent) => {
    e.stopPropagation() // Prevent thread selection
    
    if (!selectedAccount || !thread.external_thread_id) return
    
    try {
      // Mark thread as read in backend
      await emailService.markThreadAsRead(selectedAccount.account_id, thread.external_thread_id)
      
      // Update local state
      setThreads(prev => prev.map(t => 
        t.id === thread.id 
          ? { ...t, unread_count: 0, is_unread: false }
          : t
      ))
      
      toast({
        title: 'Marked as read',
        description: 'Email marked as read successfully'
      })
    } catch (error) {
      console.error('Failed to mark as read:', error)
      toast({
        title: 'Error',
        description: 'Failed to mark email as read',
        variant: 'destructive'
      })
    }
  }
  
  const handleMarkAsUnread = async (thread: EmailThread, e: React.MouseEvent) => {
    e.stopPropagation() // Prevent thread selection
    
    if (!selectedAccount || !thread.external_thread_id) return
    
    try {
      // Mark thread as unread in backend
      await emailService.markThreadAsUnread(selectedAccount.account_id, thread.external_thread_id)
      
      // Update local state
      setThreads(prev => prev.map(t => 
        t.id === thread.id 
          ? { ...t, unread_count: Math.max(1, t.unread_count), is_unread: true }
          : t
      ))
      
      toast({
        title: 'Marked as unread',
        description: 'Email marked as unread successfully'
      })
    } catch (error) {
      console.error('Failed to mark as unread:', error)
      toast({
        title: 'Error',
        description: 'Failed to mark email as unread',
        variant: 'destructive'
      })
    }
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
        // Reset compose form
        setComposeTo('')
        setComposeCc('')
        setComposeBcc('')
        setComposeSubject('')
        setComposeBody('')
        setReplyMode(null)
        setReplyToMessage(null)
        // Clear the editor
        if (editorRef.current) {
          editorRef.current.innerHTML = ''
        }
        // Reload threads to show the sent email (refresh current page)
        loadThreads(currentPage, true)
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

  // Search filtering is still done client-side, status filtering is done server-side
  const filteredThreads = threads.filter(thread => {
    // Apply search filter (client-side only for now)
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

    // Status filtering is now done server-side, so we don't filter here
    return true
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
      {/* Header with Account Selection and Filters - Single Row */}
      <div className="p-4 border-b bg-white dark:bg-gray-900 flex-shrink-0">
        <div className="flex items-center gap-3">
          {/* Account Selection */}
          {accounts.length > 0 && (
            <Select 
              value={selectedAccount?.id || ''} 
              onValueChange={(value) => {
                const account = accounts.find(a => a.id === value)
                setSelectedAccount(account || null)
              }}
            >
              <SelectTrigger className="w-52">
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

          {/* Search Bar */}
          <div className="flex-1 max-w-md">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <Input
                placeholder="Search email conversations..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 h-9"
              />
            </div>
          </div>

          {/* Compose Button */}
          <Button 
            size="sm"
            onClick={handleCompose}
            disabled={!selectedAccount}
          >
            <Plus className="w-4 h-4 mr-2" />
            Compose
          </Button>

          {/* Folder Selection */}
          <Select value={selectedFolder} onValueChange={setSelectedFolder}>
            <SelectTrigger className="w-32">
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

          {/* Filter Status */}
          <Select value={filterStatus} onValueChange={(value: any) => setFilterStatus(value)}>
            <SelectTrigger className="w-28">
              <SelectValue placeholder="Filter" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="unread">Unread</SelectItem>
              <SelectItem value="starred">Starred</SelectItem>
            </SelectContent>
          </Select>

          {/* Sync Button */}
          <Button 
            variant="outline" 
            size="sm"
            onClick={handleSync}
            disabled={!selectedAccount || syncing}
          >
            <RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
          </Button>
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
                      className={`cursor-pointer transition-colors border-b relative ${
                        isSelected 
                          ? 'bg-white dark:bg-gray-800 border-l-2 border-l-red-500' 
                          : (thread as any).is_unread || thread.unread_count > 0
                            ? 'bg-blue-50/70 hover:bg-blue-50 dark:bg-blue-900/10 dark:hover:bg-blue-900/20 border-l-2 border-l-blue-500'
                            : 'hover:bg-white dark:hover:bg-gray-800'
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
                            return Array.from(contactPipelines).map((pipeline, idx) => (
                              <div key={`contact-pipeline-${idx}`} className="flex items-center gap-1 bg-orange-50 px-2 py-0.5 rounded-full"
                                   title={`Pipeline: ${String(pipeline)}`}>
                                <svg className="w-3 h-3 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                                </svg>
                                <span className="text-xs text-orange-600 font-medium">
                                  {String(pipeline)}
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
                            return Array.from(companyPipelines).map((pipeline, idx) => (
                              <div key={`company-pipeline-${idx}`} className="flex items-center gap-1 bg-indigo-50 px-2 py-0.5 rounded-full"
                                   title={`Pipeline: ${String(pipeline)}`}>
                                <svg className="w-3 h-3 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                                </svg>
                                <span className="text-xs text-indigo-600 font-medium">
                                  {String(pipeline)}
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
                          
                          {/* Right side - Mark as read/unread icon and timestamp */}
                          <div className="flex items-center gap-2">
                            {/* Mark as read/unread button */}
                            <button
                              onClick={(e) => {
                                if ((thread as any).is_unread || thread.unread_count > 0) {
                                  handleMarkAsRead(thread, e)
                                } else {
                                  handleMarkAsUnread(thread, e)
                                }
                              }}
                              className="p-1 hover:bg-gray-100 rounded transition-colors"
                              title={(thread as any).is_unread || thread.unread_count > 0 ? "Mark as read" : "Mark as unread"}
                            >
                              {(thread as any).is_unread || thread.unread_count > 0 ? (
                                <Mail className="w-4 h-4 text-blue-600" />
                              ) : (
                                <MailOpen className="w-4 h-4 text-gray-400" />
                              )}
                            </button>
                            
                            {/* Timestamp */}
                            <div className="text-xs text-gray-500">
                              {formatDistanceToNow(new Date(thread.last_message_at || thread.created_at || new Date()), { addSuffix: true })}
                            </div>
                          </div>
                        </div>
                        
                        {/* Main content - Names, subject, preview */}
                        <div className="flex items-start justify-between">
                          <div className="flex items-start space-x-3 flex-1 min-w-0">
                            {/* Avatar with unread indicator - Show group icon for multiple participants */}
                            <div className="relative flex-shrink-0">
                              {participant.count > 2 ? (
                                <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                                  <Users className="w-4 h-4 text-blue-700" />
                                </div>
                              ) : (
                                <SafeAvatar
                                  src=""
                                  fallbackText={participant.initial}
                                  className="w-8 h-8"
                                  fallbackClassName="bg-red-100 text-red-700 text-xs"
                                />
                              )}
                              {/* Unread indicator dot */}
                              {((thread as any).is_unread || thread.unread_count > 0) && (
                                <div className="absolute -top-1 -right-1 w-3 h-3 bg-blue-600 rounded-full border-2 border-white" />
                              )}
                            </div>
                            
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
                {(currentPage > 1 || hasMorePages) && (
                  <div className="p-3 border-t bg-gray-50 dark:bg-gray-800">
                    <div className="flex items-center justify-between">
                      <div className="text-xs text-gray-600 dark:text-gray-400">
                        Page {currentPage} {threads.length > 0 && `(${threads.length} emails)`}
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
                        
                        {/* Current page indicator - simpler for cursor pagination */}
                        <div className="flex items-center gap-1">
                          {/* Show a few recent page numbers for easy navigation */}
                          {currentPage > 2 && (
                            <>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => loadThreads(1)}
                                disabled={loading}
                                className="h-8 w-8 p-0"
                              >
                                1
                              </Button>
                              <span className="px-1 text-gray-400">...</span>
                            </>
                          )}
                          
                          {currentPage > 1 && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => loadThreads(currentPage - 1)}
                              disabled={loading}
                              className="h-8 w-8 p-0"
                            >
                              {currentPage - 1}
                            </Button>
                          )}
                          
                          <Button
                            variant="default"
                            size="sm"
                            disabled={true}
                            className="h-8 w-10 p-0"
                          >
                            {currentPage}
                          </Button>
                          
                          {hasMorePages && (
                            <>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => loadThreads(currentPage + 1)}
                                disabled={loading}
                                className="h-8 w-8 p-0"
                              >
                                {currentPage + 1}
                              </Button>
                              <span className="px-1 text-gray-400">...</span>
                            </>
                          )}
                        </div>
                        
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            console.log(`📧 Next page button clicked (going to page ${currentPage + 1})`)
                            loadThreads(currentPage + 1)
                          }}
                          disabled={!hasMorePages || loading}
                          className="h-8 w-8 p-0"
                        >
                          <ChevronRight className="w-4 h-4" />
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
              <div className="space-y-2">
                {/* Rich text editor toolbar */}
                <div className="flex items-center gap-1 p-2 border rounded-t-md bg-gray-50 dark:bg-gray-800">
                  <button
                    type="button"
                    onClick={() => document.execCommand('bold', false)}
                    className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
                    title="Bold"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 4h8a4 4 0 014 4 4 4 0 01-4 4H6z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 12h10a4 4 0 014 4 4 4 0 01-4 4H6z" />
                    </svg>
                  </button>
                  <button
                    type="button"
                    onClick={() => document.execCommand('italic', false)}
                    className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
                    title="Italic"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 4h4M14 4l-4 16m-2 0h4" />
                    </svg>
                  </button>
                  <button
                    type="button"
                    onClick={() => document.execCommand('underline', false)}
                    className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
                    title="Underline"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 4v7a5 5 0 0010 0V4M5 21h14" />
                    </svg>
                  </button>
                  <div className="w-px h-6 bg-gray-300 dark:bg-gray-600 mx-1" />
                  <button
                    type="button"
                    onClick={() => document.execCommand('insertUnorderedList', false)}
                    className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
                    title="Bullet List"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                    </svg>
                  </button>
                  <button
                    type="button"
                    onClick={() => document.execCommand('insertOrderedList', false)}
                    className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
                    title="Numbered List"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
                    </svg>
                  </button>
                  <div className="w-px h-6 bg-gray-300 dark:bg-gray-600 mx-1" />
                  <button
                    type="button"
                    onClick={() => {
                      const url = prompt('Enter URL:')
                      if (url) document.execCommand('createLink', false, url)
                    }}
                    className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
                    title="Insert Link"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                    </svg>
                  </button>
                  <button
                    type="button"
                    onClick={() => document.execCommand('removeFormat', false)}
                    className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded ml-auto"
                    title="Clear Formatting"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 14l9-5-9-5-9 5 9 5z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17.5l3 3m0 0l3-3m-3 3v-6" />
                    </svg>
                  </button>
                </div>
                {/* Rich text editor content area */}
                <div
                  key={editorKey}
                  ref={editorRef}
                  id="body"
                  contentEditable={!sending}
                  className="min-h-[300px] p-3 border rounded-b-md bg-white dark:bg-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 overflow-y-auto"
                  onInput={(e) => {
                    // Update state to keep track of content
                    setComposeBody(e.currentTarget.innerHTML)
                  }}
                  style={{ minHeight: '300px', maxHeight: '500px' }}
                  suppressContentEditableWarning={true}
                />
              </div>
            </div>
          </div>
          
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setComposeOpen(false)
                // Clear editor content
                if (editorRef.current) {
                  editorRef.current.innerHTML = ''
                }
              }}
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
          threadParticipants={(linkDialogThread.participants || []).map(p => ({
            email: p.email || '',
            name: p.name
          }))}
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