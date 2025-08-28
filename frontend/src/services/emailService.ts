// Email Service for backend communication
import { api } from '@/lib/api'

export interface EmailAccount {
  id: string
  account_id: string
  provider: 'gmail' | 'outlook' | 'email' | 'mail'
  email: string
  status: string
  last_sync: string | null
  channel_id: string | null
  folders: string[]
}

export interface Participant {
  id: string
  email?: string
  phone?: string
  name: string
  role: string
  has_contact: boolean
  contact_id?: string
  confidence: number
  // Secondary record (company via domain)
  has_secondary: boolean
  secondary_id?: string
  secondary_pipeline?: string
  secondary_confidence?: number
  secondary_method?: string
}

export interface EmailThread {
  id: string
  thread_id?: string
  external_thread_id?: string
  conversation_id?: string  // For stored threads
  subject: string
  participants: Participant[]
  participant_count?: number
  has_contact_match?: boolean
  message_count: number
  unread_count: number
  last_message_at: string | null
  created_at: string | null
  folder?: string
  channel_type?: string
  channel_name?: string
  has_attachments?: boolean
  // New fields for selective storage
  source?: 'stored' | 'live' | 'merged'
  stored?: boolean
  should_store?: boolean
  storage_reason?: 'contact_match' | 'company_match' | 'manual_link' | 'none'
  linked_records?: {
    contacts: Array<{ id: string; name: string; confidence: number }>
    companies: Array<{ id: string; pipeline: string; confidence: number }>
  }
  can_link?: boolean
  channel_specific?: {
    folder?: string
    labels?: string[]
    has_attachments?: boolean
    account_email?: string
    account_id?: string
  }
  contact_linked?: boolean
  contact_confidence?: number
  contact_id?: string
  contact_name?: string
}

export interface EmailMessage {
  id: string
  external_id: string
  subject: string
  content: string
  from: string
  sender: {
    email: string
    name: string
  }
  recipients: {
    to: string[]
    cc: string[]
    bcc: string[]
  }
  sent_at: string | null
  direction: 'inbound' | 'outbound'
  status: string
  has_attachments: boolean
  attachments: Array<{
    id: string
    filename: string
    size: number
    content_type: string
  }>
}

export interface EmailFolder {
  id: string
  name: string
  role?: 'inbox' | 'sent' | 'archive' | 'drafts' | 'trash' | 'spam' | 'all' | 'important' | 'starred' | 'unknown'
  provider_id: string
  nb_mails?: number
  account_id: string
  // Legacy fields for compatibility
  type?: 'inbox' | 'sent' | 'drafts' | 'trash' | 'spam' | 'custom'
  unread_count?: number
  total_count?: number
}

class EmailService {
  async getAccounts(): Promise<{ success: boolean; accounts: EmailAccount[] }> {
    try {
      const response = await api.get('/api/v1/communications/email/accounts/')
      return response.data
    } catch (error) {
      console.error('Error fetching email accounts:', error)
      return { success: false, accounts: [] }
    }
  }

  async getEmailInbox(options?: {
    account_id?: string
    folder?: string
    limit?: number
    offset?: number
    page?: number  // New: page-based pagination
    search?: string
    refresh?: boolean
    filter?: string  // New: filter by status (all, unread, starred)
  }): Promise<{
    success: boolean
    conversations: EmailThread[]
    total?: number
    page?: number
    total_pages?: number
    has_more: boolean
    connections: Array<{
      id: string
      account_id: string
      email: string
      provider: string
    }>
  }> {
    try {
      const params: any = {}
      if (options?.account_id) params.account_id = options.account_id
      if (options?.folder) params.folder = options.folder
      if (options?.limit) params.limit = options.limit
      if (options?.page !== undefined) {
        // Use page-based pagination if page is provided
        params.page = options.page
      } else if (options?.offset !== undefined) {
        // Fallback to offset for compatibility
        params.offset = options.offset
      }
      if (options?.search) params.search = options.search
      if (options?.refresh) params.refresh = options.refresh
      if (options?.filter) params.filter = options.filter

      const response = await api.get('/api/v1/communications/email/inbox/', { params })
      return response.data
    } catch (error) {
      console.error('Error fetching email inbox:', error)
      return {
        success: false,
        conversations: [],
        total: 0,
        has_more: false,
        connections: []
      }
    }
  }

  async getParticipantInbox(options?: {
    channel_type?: string
    has_contact?: boolean
    limit?: number
    offset?: number
  }): Promise<{
    success: boolean
    conversations: EmailThread[]
    total: number
    has_more: boolean
  }> {
    try {
      const params: any = {}
      if (options?.channel_type) params.channel_type = options.channel_type
      if (options?.has_contact !== undefined) params.has_contact = options.has_contact ? 'true' : 'false'
      if (options?.limit) params.limit = options.limit
      if (options?.offset) params.offset = options.offset

      const response = await api.get('/api/v1/communications/inbox/participant/', { params })
      return response.data
    } catch (error) {
      console.error('Error fetching participant inbox:', error)
      return {
        success: false,
        conversations: [],
        total: 0,
        has_more: false
      }
    }
  }

  async getThreads(accountId?: string, options?: {
    limit?: number
    offset?: number
    force_sync?: boolean
    folder?: string
    source?: 'stored' | 'live' | 'merged'  // New option for data source
  }): Promise<{ 
    success: boolean
    threads: EmailThread[]
    has_more: boolean
    total: number
    source?: string
    stored_count?: number
    live_count?: number
  }> {
    try {
      // Always use participant inbox for email threads - it handles both stored and live
      const result = await this.getParticipantInbox({
        channel_type: 'email',
        limit: options?.limit || 20,
        offset: options?.offset || 0
      })
      
      return {
        success: result.success,
        threads: result.conversations || [],
        has_more: result.has_more || false,
        total: result.total || 0,
        source: 'participant'
      }
    } catch (error) {
      console.error('Error fetching email threads:', error)
      return { 
        success: false, 
        threads: [], 
        has_more: false,
        total: 0
      }
    }
  }

  async getMergedThreads(accountId: string, options?: {
    limit?: number
    offset?: number
    folder?: string
  }): Promise<{ 
    success: boolean
    threads: EmailThread[]
    has_more: boolean
    total: number
    stored_count: number
    live_count: number
  }> {
    // Use participant inbox which already merges stored and live
    const result = await this.getParticipantInbox({
      channel_type: 'email',
      limit: options?.limit || 20,
      offset: options?.offset || 0
    })
    
    return {
      success: result.success,
      threads: result.conversations || [],
      has_more: result.has_more || false,
      total: result.total || 0,
      stored_count: result.conversations?.filter(c => c.stored).length || 0,
      live_count: result.conversations?.filter(c => !c.stored).length || 0
    }
  }

  async getLiveThreads(accountId: string, options?: {
    limit?: number
    cursor?: string
    folder?: string
  }): Promise<{ 
    success: boolean
    threads: EmailThread[]
    cursor?: string
    has_more: boolean
    total: number
  }> {
    try {
      const params: any = {
        account_id: accountId,
        limit: options?.limit || 20,
        folder: options?.folder || 'INBOX'
      }

      if (options?.cursor) {
        params.cursor = options.cursor
      }

      const response = await api.get('/api/v1/communications/email/threads/live/', { params })
      return response.data
    } catch (error) {
      console.error('Error fetching live email threads:', error)
      return { 
        success: false, 
        threads: [], 
        has_more: false,
        total: 0
      }
    }
  }

  async getThreadMessages(threadId: string, accountId?: string): Promise<{
    success: boolean
    messages: EmailMessage[]
    thread: EmailThread | null
    source?: string
  }> {
    try {
      const params: any = {}
      if (accountId) {
        params.account_id = accountId
      }
      const response = await api.get(`/api/v1/communications/email/threads/${threadId}/messages/`, { params })
      return response.data
    } catch (error) {
      console.error('Error fetching thread messages:', error)
      return {
        success: false,
        messages: [],
        thread: null
      }
    }
  }

  async sendEmail(data: {
    account_id: string
    to: string[]
    subject: string
    body: string
    cc?: string[]
    bcc?: string[]
    reply_to_message_id?: string
  }): Promise<{ success: boolean; message_id?: string; error?: string }> {
    try {
      const response = await api.post('/api/v1/communications/email/send/', data)
      return response.data
    } catch (error: any) {
      console.error('Error sending email:', error)
      return { 
        success: false, 
        error: error.response?.data?.error || error.message || 'Failed to send email'
      }
    }
  }

  async updateEmail(emailId: string, data: {
    unread?: boolean
    folders?: string[]
  }): Promise<{ success: boolean; error?: string }> {
    try {
      const response = await api.put(`/api/v1/communications/email/emails/${emailId}/`, data)
      return response.data
    } catch (error: any) {
      console.error('Error updating email:', error)
      return { 
        success: false, 
        error: error.response?.data?.error || error.message || 'Failed to update email'
      }
    }
  }

  async getFolders(accountId: string): Promise<{
    success: boolean
    folders: EmailFolder[]
  }> {
    try {
      const response = await api.get('/api/v1/communications/email/folders/', {
        params: { account_id: accountId }
      })
      return response.data
    } catch (error: any) {
      console.error('Error fetching folders:', error)
      // Log more details about the error
      if (error.response) {
        console.error('Response data:', error.response.data)
        console.error('Response status:', error.response.status)
        console.error('Response headers:', error.response.headers)
      }
      return { success: false, folders: [] }
    }
  }

  async syncEmail(accountId: string, options?: {
    sync_type?: 'comprehensive' | 'incremental'
    days_back?: number
  }): Promise<{
    success: boolean
    sync_job_id?: string
    celery_task_id?: string
    message?: string
    error?: string
  }> {
    try {
      const response = await api.post('/api/v1/communications/email/sync/', {
        account_id: accountId,
        sync_type: options?.sync_type || 'incremental',
        options: {
          days_back: options?.days_back || 7
        }
      })
      return response.data
    } catch (error: any) {
      console.error('Error starting sync:', error)
      return {
        success: false,
        error: error.response?.data?.error || error.message || 'Failed to start sync'
      }
    }
  }

  async linkThreadToContact(threadId: string, contactId: string): Promise<{
    success: boolean
    message?: string
    error?: string
  }> {
    try {
      const response = await api.post(`/api/v1/communications/email/threads/${threadId}/link-contact/`, {
        contact_id: contactId
      })
      return response.data
    } catch (error: any) {
      console.error('Error linking thread to contact:', error)
      return {
        success: false,
        error: error.response?.data?.error || error.message || 'Failed to link thread to contact'
      }
    }
  }

  async createContactFromThread(threadId: string, data: {
    email: string
    name?: string
    pipeline_id: string
  }): Promise<{
    success: boolean
    contact_id?: string
    message?: string
    error?: string
  }> {
    try {
      const response = await api.post(`/api/v1/communications/email/threads/${threadId}/create-contact/`, data)
      return response.data
    } catch (error: any) {
      console.error('Error creating contact from thread:', error)
      return {
        success: false,
        error: error.response?.data?.error || error.message || 'Failed to create contact'
      }
    }
  }

  async syncThreadHistory(threadId: string): Promise<{
    success: boolean
    sync_job_id?: string
    message?: string
    error?: string
  }> {
    try {
      const response = await api.post(`/api/v1/communications/email/threads/${threadId}/sync-history/`)
      return response.data
    } catch (error: any) {
      console.error('Error syncing thread history:', error)
      return {
        success: false,
        error: error.response?.data?.error || error.message || 'Failed to sync thread history'
      }
    }
  }
  async linkEmailConversation(threadId: string, options: {
    record_type: 'contact' | 'company'
    record_id: string
    participant_email: string
  }): Promise<{ success: boolean; message?: string; error?: string }> {
    try {
      const response = await api.post(`/api/v1/communications/email/conversations/${threadId}/link/`, {
        link_to: {
          record_type: options.record_type,
          record_id: options.record_id
        },
        participant_email: options.participant_email
      })
      return response.data
    } catch (error: any) {
      console.error('Error linking email conversation:', error)
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to link conversation'
      }
    }
  }

  // Mark emails as read
  async markEmailsAsRead(accountId: string, emailIds: string[]): Promise<any> {
    try {
      const response = await api.post('/api/v1/communications/email/mark-read/', {
        account_id: accountId,
        email_ids: emailIds
      })
      return response.data
    } catch (error) {
      console.error('Failed to mark emails as read:', error)
      throw error
    }
  }

  // Mark emails as unread
  async markEmailsAsUnread(accountId: string, emailIds: string[]): Promise<any> {
    try {
      const response = await api.post('/api/v1/communications/email/mark-unread/', {
        account_id: accountId,
        email_ids: emailIds
      })
      return response.data
    } catch (error) {
      console.error('Failed to mark emails as unread:', error)
      throw error
    }
  }

  // Mark entire thread as read
  async markThreadAsRead(accountId: string, threadId: string): Promise<any> {
    try {
      const response = await api.post('/api/v1/communications/email/thread/mark-read/', {
        account_id: accountId,
        thread_id: threadId
      })
      return response.data
    } catch (error) {
      console.error('Failed to mark thread as read:', error)
      throw error
    }
  }

  // Mark entire thread as unread
  async markThreadAsUnread(accountId: string, threadId: string): Promise<any> {
    try {
      const response = await api.post('/api/v1/communications/email/thread/mark-unread/', {
        account_id: accountId,
        thread_id: threadId
      })
      return response.data
    } catch (error) {
      console.error('Failed to mark thread as unread:', error)
      throw error
    }
  }

  // Delete email or thread (moves to trash in UniPile)
  async deleteEmail(accountId: string, emailId: string): Promise<{
    success: boolean
    message?: string
    error?: string
  }> {
    try {
      const response = await api.delete(`/api/v1/communications/email/emails/${emailId}/delete/`, {
        params: { account_id: accountId }
      })
      return response.data
    } catch (error: any) {
      console.error('Failed to delete email:', error)
      return {
        success: false,
        error: error.response?.data?.error || error.message || 'Failed to delete email'
      }
    }
  }
}

export const emailService = new EmailService()