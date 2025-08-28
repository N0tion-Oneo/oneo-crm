// WhatsApp Service for live data fetching (similar to email approach)
import { api } from '@/lib/api'

export interface WhatsAppAccount {
  id: string
  account_id: string
  phone: string
  name: string
  status: string
  last_sync: string | null
}

export interface WhatsAppParticipant {
  id: string | null
  phone: string
  name: string
  has_contact: boolean
  contact_id?: string | null
  contact_name?: string | null
  confidence: number
  has_secondary: boolean
  secondary_id?: string | null
  secondary_pipeline?: string | null
  secondary_confidence?: number
}

export interface WhatsAppConversation {
  id: string
  external_thread_id: string
  name: string
  participants: WhatsAppParticipant[]
  participant_count: number
  is_group: boolean
  last_message: string
  last_message_at: string | null
  unread_count: number
  message_count: number
  
  // Storage status (key difference from old approach)
  source: 'live' | 'stored' | 'merged'
  stored: boolean
  should_store: boolean
  storage_reason: 'contact_match' | 'company_match' | 'manual_link' | 'none'
  can_link: boolean
  
  // Linked records
  linked_records?: {
    contacts: Array<{ id: string; name: string; confidence: number }>
    companies: Array<{ id: string; pipeline: string; confidence: number }>
  }
  
  channel_specific?: {
    account_id: string
    account_phone?: string
    is_group: boolean
    chat_type: 'individual' | 'group'
  }
}

export interface WhatsAppMessage {
  id: string
  external_id: string
  text: string
  from_attendee: {
    id: string
    phone_number: string
    name?: string
  }
  sent_at: string | null
  direction: 'inbound' | 'outbound'
  status: string
  attachments?: Array<{
    id: string
    file_name: string
    size: number
    content_type: string
    url?: string
  }>
}

class WhatsAppService {
  /**
   * Get WhatsApp chats using live data approach (like email)
   * Fetches from UniPile without storing
   */
  async getLiveInbox(options?: {
    account_id?: string
    chat_type?: 'individual' | 'group'
    limit?: number
    cursor?: string
    search?: string
  }): Promise<{
    success: boolean
    conversations: WhatsAppConversation[]
    has_more: boolean
    cursor?: string
    connections: Array<{
      id: string
      account_id: string
      phone: string
      name: string
    }>
  }> {
    try {
      const params: any = {}
      if (options?.account_id) params.account_id = options.account_id
      if (options?.chat_type) params.chat_type = options.chat_type
      if (options?.limit) params.limit = options.limit
      if (options?.cursor) params.cursor = options.cursor
      if (options?.search) params.search = options.search

      // Use the new live endpoint
      const response = await api.get('/api/v1/communications/whatsapp/inbox/live/', { params })
      return response.data
    } catch (error) {
      console.error('Error fetching live WhatsApp inbox:', error)
      return {
        success: false,
        conversations: [],
        has_more: false,
        connections: []
      }
    }
  }

  /**
   * Get stored WhatsApp conversations (old approach - for backwards compatibility)
   */
  async getStoredInbox(options?: {
    account_id?: string
    limit?: number
    offset?: number
  }): Promise<{
    success: boolean
    conversations: WhatsAppConversation[]
    total: number
    has_more: boolean
  }> {
    try {
      const params: any = {}
      if (options?.account_id) params.account_id = options.account_id
      if (options?.limit) params.limit = options.limit
      if (options?.offset) params.offset = options.offset

      const response = await api.get('/api/v1/communications/whatsapp/inbox/', { params })
      return response.data
    } catch (error) {
      console.error('Error fetching stored WhatsApp inbox:', error)
      return {
        success: false,
        conversations: [],
        total: 0,
        has_more: false
      }
    }
  }

  /**
   * Store a WhatsApp conversation when linking to contact/company
   */
  async storeConversation(chatId: string, options: {
    account_id: string
    link_to: {
      record_type: 'contact' | 'company'
      record_id: string
      participant_phone: string
    }
  }): Promise<{
    success: boolean
    message?: string
    conversation_id?: string
    error?: string
  }> {
    try {
      const response = await api.post(
        `/api/v1/communications/whatsapp/conversations/${chatId}/store/`,
        options
      )
      return response.data
    } catch (error: any) {
      console.error('Error storing WhatsApp conversation:', error)
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to store conversation'
      }
    }
  }

  /**
   * Get messages for a specific chat (live data)
   */
  async getChatMessages(chatId: string, accountId?: string): Promise<{
    success: boolean
    messages: WhatsAppMessage[]
    chat: WhatsAppConversation | null
    source?: string
  }> {
    try {
      const params: any = {}
      if (accountId) params.account_id = accountId

      // Use the new live messages endpoint
      const response = await api.get(
        `/api/v1/communications/whatsapp/chats/${chatId}/messages/live/`,
        { params }
      )
      return response.data
    } catch (error) {
      console.error('Error fetching chat messages:', error)
      return {
        success: false,
        messages: [],
        chat: null
      }
    }
  }

  /**
   * Send a WhatsApp message
   */
  async sendMessage(data: {
    account_id: string
    chat_id: string
    text: string
    attachments?: any[]
  }): Promise<{
    success: boolean
    message_id?: string
    error?: string
  }> {
    try {
      const response = await api.post(
        `/api/v1/communications/whatsapp/chats/${data.chat_id}/send/`,
        data
      )
      return response.data
    } catch (error: any) {
      console.error('Error sending WhatsApp message:', error)
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to send message'
      }
    }
  }

  /**
   * Link conversation to existing contact
   */
  async linkToContact(chatId: string, contactId: string): Promise<{
    success: boolean
    message?: string
    error?: string
  }> {
    try {
      const response = await api.post(
        `/api/v1/communications/whatsapp/conversations/${chatId}/link/`,
        { contact_id: contactId }
      )
      return response.data
    } catch (error: any) {
      console.error('Error linking to contact:', error)
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to link to contact'
      }
    }
  }

  /**
   * Get connected WhatsApp accounts
   */
  async getAccounts(): Promise<{
    success: boolean
    accounts: WhatsAppAccount[]
  }> {
    try {
      const response = await api.get('/api/v1/communications/whatsapp/accounts/')
      return response.data
    } catch (error) {
      console.error('Error fetching WhatsApp accounts:', error)
      return { success: false, accounts: [] }
    }
  }

  /**
   * Start background sync (now disabled by default)
   */
  async startBackgroundSync(options?: {
    sync_options?: {
      enabled?: boolean // Must explicitly enable
      max_conversations?: number
      max_messages_per_chat?: number
      days_back?: number
    }
  }): Promise<{
    success: boolean
    sync_jobs?: any[]
    error?: string
  }> {
    try {
      // Must explicitly enable sync
      const syncOptions = {
        enabled: false, // Default disabled
        ...options?.sync_options
      }

      const response = await api.post(
        '/api/v1/communications/whatsapp/sync/background/',
        { sync_options: syncOptions }
      )
      return response.data
    } catch (error: any) {
      console.error('Error starting background sync:', error)
      return {
        success: false,
        error: error.response?.data?.error || 'Background sync is disabled by default'
      }
    }
  }
}

export const whatsappService = new WhatsAppService()