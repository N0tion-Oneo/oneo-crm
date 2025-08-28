// Pagination
export const DEFAULT_ITEMS_PER_PAGE = 20

// Default folder
export const DEFAULT_FOLDER = 'INBOX'

// Filter statuses
export const FILTER_STATUS = {
  ALL: 'all',
  UNREAD: 'unread',
  STARRED: 'starred'
} as const

// Folder roles/types
export const FOLDER_ROLES = {
  INBOX: 'inbox',
  SENT: 'sent',
  DRAFTS: 'drafts',
  TRASH: 'trash',
  SPAM: 'spam',
  ALL: 'all',
  IMPORTANT: 'important',
  STARRED: 'starred',
  ARCHIVE: 'archive'
} as const

// System folders (folders that should appear first in the list)
export const SYSTEM_FOLDERS = [
  FOLDER_ROLES.INBOX,
  FOLDER_ROLES.SENT,
  FOLDER_ROLES.DRAFTS,
  FOLDER_ROLES.TRASH,
  FOLDER_ROLES.SPAM,
  FOLDER_ROLES.ALL,
  FOLDER_ROLES.IMPORTANT,
  FOLDER_ROLES.STARRED
]

// Default fallback folders for providers
export const DEFAULT_FOLDERS = {
  GMAIL: {
    INBOX: 'INBOX',
    SENT: '[Gmail]/Sent Mail',
    DRAFTS: '[Gmail]/Drafts',
    TRASH: '[Gmail]/Trash',
    SPAM: '[Gmail]/Spam'
  },
  OUTLOOK: {
    INBOX: 'Inbox',
    SENT: 'Sent Items',
    DRAFTS: 'Drafts',
    TRASH: 'Deleted Items',
    SPAM: 'Junk Email'
  }
} as const

// WebSocket channel patterns
export const WS_CHANNELS = {
  EMAIL_USER: (userId: string) => `user_${userId}_email`
}

// Email template styles
export const EMAIL_STYLES = {
  REPLY_SEPARATOR: {
    borderTop: '1px solid #ccc',
    paddingTop: '10px',
    marginTop: '20px'
  },
  REPLY_HEADER: {
    color: '#666',
    fontSize: '14px',
    marginBottom: '10px'
  },
  BLOCKQUOTE: {
    margin: '0 0 0 10px',
    paddingLeft: '10px',
    borderLeft: '2px solid #ccc'
  },
  FORWARD_CONTAINER: {
    border: '1px solid #ccc',
    padding: '15px',
    marginTop: '20px',
    backgroundColor: '#f9f9f9'
  }
}