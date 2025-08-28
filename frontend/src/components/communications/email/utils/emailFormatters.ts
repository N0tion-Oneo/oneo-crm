import { formatDistanceToNow } from 'date-fns'
import { EmailMessage, EmailThread } from './emailTypes'
import { EMAIL_STYLES } from './emailConstants'

/**
 * Format date for display
 */
export const formatEmailDate = (date: string | null | undefined): string => {
  if (!date) return 'Unknown date'
  
  try {
    return new Date(date).toLocaleString()
  } catch {
    return 'Invalid date'
  }
}

/**
 * Format relative date
 */
export const formatRelativeDate = (date: string | null | undefined): string => {
  if (!date) return ''
  
  try {
    return formatDistanceToNow(new Date(date), { addSuffix: true })
  } catch {
    return ''
  }
}

/**
 * Get participant display name and email
 */
export const getParticipantDisplay = (thread: EmailThread) => {
  const mainParticipant = thread.participants?.[0]
  if (!mainParticipant) return { name: 'Unknown', email: '', initials: 'U' }
  
  const name = mainParticipant.name || mainParticipant.email || 'Unknown'
  const email = mainParticipant.email || ''
  const initials = name.charAt(0).toUpperCase()
  
  return { name, email, initials }
}

/**
 * Format reply email body with quoted content
 */
export const formatReplyBody = (message: EmailMessage, threadSubject?: string): string => {
  const date = formatEmailDate(message.sent_at)
  const sender = message.sender.name || message.sender.email
  
  return `<br><br><br>
<div style="${Object.entries(EMAIL_STYLES.REPLY_SEPARATOR).map(([k, v]) => `${k.replace(/([A-Z])/g, '-$1').toLowerCase()}: ${v}`).join('; ')}">
  <div style="${Object.entries(EMAIL_STYLES.REPLY_HEADER).map(([k, v]) => `${k.replace(/([A-Z])/g, '-$1').toLowerCase()}: ${v}`).join('; ')}">
    On ${date}, ${sender} wrote:
  </div>
  <blockquote style="${Object.entries(EMAIL_STYLES.BLOCKQUOTE).map(([k, v]) => `${k.replace(/([A-Z])/g, '-$1').toLowerCase()}: ${v}`).join('; ')}">
    ${message.content}
  </blockquote>
</div>`
}

/**
 * Format forward email body with quoted content
 */
export const formatForwardBody = (message: EmailMessage, threadSubject?: string): string => {
  const date = formatEmailDate(message.sent_at)
  const sender = message.sender.name || message.sender.email
  const recipients = message.recipients?.to?.join(', ') || 'Unknown recipients'
  const subject = message.subject || threadSubject || '(No subject)'
  
  return `<br><br><br>
<div style="${Object.entries(EMAIL_STYLES.FORWARD_CONTAINER).map(([k, v]) => `${k.replace(/([A-Z])/g, '-$1').toLowerCase()}: ${v}`).join('; ')}">
  <div style="font-weight: bold; margin-bottom: 10px;">––––––––– Forwarded Message –––––––––</div>
  <div style="${Object.entries(EMAIL_STYLES.REPLY_HEADER).map(([k, v]) => `${k.replace(/([A-Z])/g, '-$1').toLowerCase()}: ${v}`).join('; ')}">
    <strong>From:</strong> ${sender} &lt;${message.sender.email}&gt;<br>
    <strong>Date:</strong> ${date}<br>
    <strong>Subject:</strong> ${subject}<br>
    <strong>To:</strong> ${recipients}
  </div>
  <div style="margin-top: 15px;">
    ${message.content}
  </div>
</div>`
}

/**
 * Format file size for display
 */
export const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
}

/**
 * Extract email addresses from a comma-separated string
 */
export const parseEmailAddresses = (emailString: string): string[] => {
  return emailString
    .split(',')
    .map(e => e.trim())
    .filter(e => e.length > 0)
}

/**
 * Get folder display name
 */
export const getFolderDisplayName = (folder: { name: string; role?: string }): string => {
  // Use role-based name if available
  if (folder.role) {
    const roleNames: Record<string, string> = {
      inbox: 'Inbox',
      sent: 'Sent',
      drafts: 'Drafts',
      trash: 'Trash',
      spam: 'Spam',
      all: 'All Mail',
      important: 'Important',
      starred: 'Starred',
      archive: 'Archive'
    }
    return roleNames[folder.role] || folder.name
  }
  return folder.name
}

/**
 * Check if a folder is a system folder
 */
export const isSystemFolder = (folderRole: string | undefined): boolean => {
  if (!folderRole) return false
  return ['inbox', 'sent', 'drafts', 'trash', 'spam', 'all', 'important', 'starred'].includes(folderRole)
}