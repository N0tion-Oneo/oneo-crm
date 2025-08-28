import { EmailAccount, EmailThread, EmailMessage, EmailFolder } from '@/services/emailService'

// Component-specific types
export interface GmailInboxProps {
  className?: string
}

export interface ComposeState {
  to: string
  cc: string
  bcc: string
  subject: string
  body: string
}

export type ReplyMode = 'reply' | 'forward' | null

export interface EmailFilters {
  searchQuery: string
  filterStatus: 'all' | 'unread' | 'starred'
  selectedFolder: string
}

export interface PaginationState {
  currentPage: number
  hasMorePages: boolean
  totalPages: number
  total: number
  itemsPerPage: number
}

export interface EmailUIState {
  loading: boolean
  syncing: boolean
  messagesLoading: boolean
  sending: boolean
  composeOpen: boolean
  replyMode: ReplyMode
  collapsedMessages: Set<string>
  linkDialogOpen: boolean
}

// Re-export service types for convenience
export type {
  EmailAccount,
  EmailThread,
  EmailMessage,
  EmailFolder
}