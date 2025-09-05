import { useState, useEffect, useCallback, useMemo } from 'react'
import { emailService } from '@/services/emailService'
import { useToast } from '@/hooks/use-toast'
import { EmailAccount, EmailThread, EmailMessage, EmailFolder } from '../utils/emailTypes'
import { DEFAULT_FOLDER, DEFAULT_ITEMS_PER_PAGE } from '../utils/emailConstants'

interface UseEmailThreadsProps {
  selectedAccount: EmailAccount | null
}

export const useEmailThreads = ({ selectedAccount }: UseEmailThreadsProps) => {
  const [threads, setThreads] = useState<EmailThread[]>([])
  const [selectedThread, setSelectedThread] = useState<EmailThread | null>(null)
  const [threadMessages, setThreadMessages] = useState<EmailMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [messagesLoading, setMessagesLoading] = useState(false)
  const [syncing, setSyncing] = useState(false)
  
  // Filters and pagination
  const [searchQuery, setSearchQuery] = useState('')
  const [filterStatus, setFilterStatus] = useState<'all' | 'unread' | 'starred'>('all')
  const [selectedFolder, setSelectedFolder] = useState<string>(DEFAULT_FOLDER)
  const [currentPage, setCurrentPage] = useState(1)
  const [hasMorePages, setHasMorePages] = useState(false)
  const [total, setTotal] = useState(0)
  
  // Folders
  const [folders, setFolders] = useState<EmailFolder[]>([])
  
  const { toast } = useToast()

  // Load threads
  const loadThreads = useCallback(async (page = 1, refresh = false) => {
    if (!selectedAccount) {
      console.log('No selected account, skipping load')
      return
    }
    
    console.log(`📧 Loading email page ${page} (cursor-based, limit: ${DEFAULT_ITEMS_PER_PAGE})`)
    
    try {
      setLoading(true)
      
      const result = await emailService.getEmailInbox({
        account_id: selectedAccount.account_id,
        folder: selectedFolder,
        limit: DEFAULT_ITEMS_PER_PAGE,
        page: page,
        search: searchQuery,
        refresh: refresh,
        filter: filterStatus
      })
      
      if (result.success) {
        const newThreads = result.conversations || []
        setThreads(newThreads)
        setCurrentPage(result.page || page)
        
        const hasMore = result.has_more || false
        setHasMorePages(hasMore)
        setTotal(0) // With cursor pagination, we don't know the grand total
        
        console.log(`📧 Page ${page} loaded successfully: ${newThreads.length} threads`)
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
  }, [selectedAccount, selectedFolder, searchQuery, filterStatus, toast])

  // Load thread messages
  const loadThreadMessages = useCallback(async (thread: EmailThread) => {
    if (!selectedAccount) return
    
    setMessagesLoading(true)
    try {
      const result = await emailService.getThreadMessages(thread.id, selectedAccount.account_id)
      
      if (result.success) {
        setThreadMessages(result.messages)
        
        // Mark thread as read if it has unread messages
        if (thread.unread_count > 0) {
          const updatedThreads = threads.map(t => 
            t.id === thread.id ? { ...t, unread_count: 0 } : t
          )
          setThreads(updatedThreads)
        }
      } else {
        toast({
          title: 'Failed to load messages',
          description: 'Could not load thread messages',
          variant: 'destructive'
        })
      }
    } catch (error) {
      console.error('Failed to load thread messages:', error)
      toast({
        title: 'Error',
        description: 'Failed to load thread messages',
        variant: 'destructive'
      })
    } finally {
      setMessagesLoading(false)
    }
  }, [selectedAccount, threads, toast])

  // Load folders
  const loadFolders = useCallback(async () => {
    if (!selectedAccount) return
    
    try {
      const result = await emailService.getFolders(selectedAccount.account_id)
      
      if (result.success) {
        setFolders(result.folders)
        
        // If current folder is not in the list, reset to INBOX
        const folderExists = result.folders.some(
          f => f.provider_id === selectedFolder || f.id === selectedFolder
        )
        if (!folderExists && selectedFolder !== DEFAULT_FOLDER) {
          setSelectedFolder(DEFAULT_FOLDER)
        }
      }
    } catch (error) {
      console.error('Failed to load folders:', error)
    }
  }, [selectedAccount, selectedFolder])

  // Sync emails
  const syncEmails = useCallback(async () => {
    if (!selectedAccount) return
    
    setSyncing(true)
    try {
      const result = await emailService.syncEmail(selectedAccount.account_id, {
        sync_type: 'incremental',
        days_back: 7
      })
      
      if (result.success) {
        toast({
          title: 'Sync started',
          description: 'Email synchronization has been started in the background',
        })
        
        // Reload threads after a delay
        setTimeout(() => {
          loadThreads(currentPage, true)
        }, 2000)
      } else {
        throw new Error(result.error || 'Sync failed')
      }
    } catch (error: any) {
      console.error('Sync error:', error)
      toast({
        title: 'Sync failed',
        description: error.message || 'Failed to sync emails',
        variant: 'destructive'
      })
    } finally {
      setSyncing(false)
    }
  }, [selectedAccount, currentPage, loadThreads, toast])

  // Select thread
  const selectThread = useCallback((thread: EmailThread | null) => {
    setSelectedThread(thread)
    if (thread) {
      loadThreadMessages(thread)
    } else {
      setThreadMessages([])
    }
  }, [loadThreadMessages])

  // Filtered threads for search
  const filteredThreads = useMemo(() => {
    if (!searchQuery) return threads
    
    const query = searchQuery.toLowerCase()
    return threads.filter(thread => {
      const subject = thread.subject?.toLowerCase() || ''
      const participants = thread.participants?.map(p => 
        `${p.email} ${p.name}`.toLowerCase()
      ).join(' ') || ''
      
      return subject.includes(query) || participants.includes(query)
    })
  }, [threads, searchQuery])

  // Load threads when account or folder changes
  useEffect(() => {
    if (selectedAccount) {
      setCurrentPage(1)
      loadThreads(1)
      loadFolders()
    }
  }, [selectedAccount, selectedFolder])

  // Load threads when filter changes
  useEffect(() => {
    if (selectedAccount) {
      setCurrentPage(1)
      loadThreads(1)
    }
  }, [filterStatus])

  return {
    // Thread data
    threads: filteredThreads,
    selectedThread,
    threadMessages,
    
    // Loading states
    loading,
    messagesLoading,
    syncing,
    
    // Filters
    searchQuery,
    setSearchQuery,
    filterStatus,
    setFilterStatus,
    selectedFolder,
    setSelectedFolder,
    
    // Pagination
    currentPage,
    hasMorePages,
    total,
    
    // Folders
    folders,
    
    // Actions
    loadThreads,
    selectThread,
    syncEmails,
    setThreads
  }
}