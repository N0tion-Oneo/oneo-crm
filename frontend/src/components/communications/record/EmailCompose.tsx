import React, { useState, useRef, useEffect } from 'react'
import { Send, Paperclip, X, ChevronDown, ChevronUp, Mail } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { api } from '@/lib/api'
import { toast } from '@/hooks/use-toast'
import { emailService } from '@/services/emailService'

interface EmailComposeProps {
  conversationId: string | null
  recordId: string
  onMessageSent?: () => void
  replyTo?: any // Email message to reply to
  replyMode?: 'reply' | 'reply-all' | 'forward' | null
  onCancelReply?: () => void
}

export function EmailCompose({
  conversationId,
  recordId,
  onMessageSent,
  replyTo,
  replyMode,
  onCancelReply
}: EmailComposeProps) {
  const [to, setTo] = useState('')
  const [cc, setCc] = useState('')
  const [bcc, setBcc] = useState('')
  const [subject, setSubject] = useState('')
  const [showCcBcc, setShowCcBcc] = useState(false)
  const [isSending, setIsSending] = useState(false)
  const [emailAccounts, setEmailAccounts] = useState<any[]>([])
  const [selectedAccountId, setSelectedAccountId] = useState<string>('')
  const [isExpanded, setIsExpanded] = useState(false)
  const editorRef = useRef<HTMLDivElement>(null)

  // Fetch email accounts on mount
  useEffect(() => {
    const fetchAccounts = async () => {
      try {
        const result = await emailService.getAccounts()
        if (result.success && result.accounts.length > 0) {
          setEmailAccounts(result.accounts)
          // Auto-select first account
          setSelectedAccountId(result.accounts[0].account_id)
        }
      } catch (error) {
        console.error('Failed to fetch email accounts:', error)
      }
    }
    fetchAccounts()
  }, [])
  
  // Add keyboard shortcut 'c' to open compose
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      // Only trigger if not already typing in an input/textarea
      const target = e.target as HTMLElement
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.contentEditable === 'true') {
        return
      }
      
      // 'c' key to compose
      if (e.key === 'c' && !isExpanded && !e.ctrlKey && !e.metaKey && !e.altKey) {
        e.preventDefault()
        setIsExpanded(true)
      }
      
      // Escape key to collapse
      if (e.key === 'Escape' && isExpanded) {
        e.preventDefault()
        setIsExpanded(false)
        if (replyMode && onCancelReply) {
          onCancelReply()
        }
      }
    }
    
    window.addEventListener('keydown', handleKeyPress)
    return () => window.removeEventListener('keydown', handleKeyPress)
  }, [isExpanded, replyMode, onCancelReply])

  // Initialize fields based on reply mode
  useEffect(() => {
    if (replyTo && replyMode) {
      // Auto-expand when replying
      setIsExpanded(true)
      
      if (replyMode === 'reply') {
        setTo(replyTo.sender?.email || replyTo.from || '')
        setSubject(`Re: ${replyTo.subject || ''}`.replace(/^(Re: )+/, 'Re: '))
        setCc('')
        setBcc('')
        
        // Set reply body with quoted text
        if (editorRef.current) {
          const quotedBody = formatQuotedReply(replyTo)
          editorRef.current.innerHTML = `<br><br>${quotedBody}`
          // Place cursor at the beginning
          const selection = window.getSelection()
          const range = document.createRange()
          range.selectNodeContents(editorRef.current)
          range.collapse(true)
          selection?.removeAllRanges()
          selection?.addRange(range)
        }
      } else if (replyMode === 'reply-all') {
        // Reply to sender and all recipients
        setTo(replyTo.sender?.email || replyTo.from || '')
        const ccList = [...(replyTo.recipients?.to || []), ...(replyTo.recipients?.cc || [])]
          .filter((email: string) => email !== replyTo.sender?.email)
          .join(', ')
        setCc(ccList)
        setSubject(`Re: ${replyTo.subject || ''}`.replace(/^(Re: )+/, 'Re: '))
        setBcc('')
        setShowCcBcc(true)
        
        // Set reply body
        if (editorRef.current) {
          const quotedBody = formatQuotedReply(replyTo)
          editorRef.current.innerHTML = `<br><br>${quotedBody}`
        }
      } else if (replyMode === 'forward') {
        setTo('')
        setCc('')
        setBcc('')
        setSubject(`Fwd: ${replyTo.subject || ''}`.replace(/^(Fwd: )+/, 'Fwd: '))
        
        // Set forward body
        if (editorRef.current) {
          const quotedBody = formatQuotedForward(replyTo)
          editorRef.current.innerHTML = `<br><br>${quotedBody}`
        }
      }
    } else if (!replyMode) {
      // Clear fields when not replying
      setTo('')
      setCc('')
      setBcc('')
      setSubject('')
      if (editorRef.current) {
        editorRef.current.innerHTML = ''
      }
      // Collapse when no reply mode
      setIsExpanded(false)
    }
  }, [replyTo, replyMode])

  const formatQuotedReply = (message: any) => {
    const date = new Date(message.sent_at).toLocaleString()
    const sender = message.sender?.name || message.sender?.email || message.from || 'Unknown'
    
    return `
      <div style="border-left: 2px solid #ccc; margin-left: 10px; padding-left: 10px; color: #666;">
        <div style="margin-bottom: 10px;">
          On ${date}, ${sender} wrote:
        </div>
        <div>${message.content || ''}</div>
      </div>
    `
  }

  const formatQuotedForward = (message: any) => {
    const date = new Date(message.sent_at).toLocaleString()
    const sender = message.sender?.name || message.sender?.email || message.from || 'Unknown'
    const to = message.recipients?.to?.join(', ') || ''
    
    return `
      <div style="border-left: 2px solid #ccc; margin-left: 10px; padding-left: 10px; color: #666;">
        <div style="margin-bottom: 10px;">
          ---------- Forwarded message ----------<br>
          From: ${sender}<br>
          Date: ${date}<br>
          Subject: ${message.subject || ''}<br>
          To: ${to}
        </div>
        <div>${message.content || ''}</div>
      </div>
    `
  }

  const handleSend = async () => {
    if (!selectedAccountId && emailAccounts.length > 0) {
      toast({
        title: 'No email account selected',
        description: 'Please select an email account to send from',
        variant: 'destructive'
      })
      return
    }

    if (!to.trim() || !subject.trim()) {
      toast({
        title: 'Missing required fields',
        description: 'Please enter recipients and subject',
        variant: 'destructive'
      })
      return
    }

    const body = editorRef.current?.innerHTML || ''
    if (!body.trim()) {
      toast({
        title: 'Empty message',
        description: 'Please enter a message',
        variant: 'destructive'
      })
      return
    }

    setIsSending(true)

    try {
      const payload: any = {
        from_account_id: selectedAccountId,
        to: to.split(',').map(e => e.trim()).filter(Boolean),
        cc: cc ? cc.split(',').map(e => e.trim()).filter(Boolean) : [],
        bcc: bcc ? bcc.split(',').map(e => e.trim()).filter(Boolean) : [],
        subject: subject,
        body: body,
        reply_to_message_id: replyTo?.id,
        reply_mode: replyMode
      }
      
      // Only include conversation_id if it exists
      if (conversationId) {
        payload.conversation_id = conversationId
      }
      
      await api.post(
        `/api/v1/communications/records/${recordId}/send_email/`,
        payload
      )

      // Clear form
      setTo('')
      setCc('')
      setBcc('')
      setSubject('')
      if (editorRef.current) {
        editorRef.current.innerHTML = ''
      }
      setShowCcBcc(false)
      
      // Collapse after sending
      setIsExpanded(false)
      
      // Clear reply mode
      if (onCancelReply) {
        onCancelReply()
      }
      
      toast({
        title: 'Email sent',
        description: 'Your email has been sent successfully.',
      })

      if (onMessageSent) {
        onMessageSent()
      }
    } catch (err: any) {
      console.error('Failed to send email:', err)
      toast({
        title: 'Failed to send email',
        description: err.response?.data?.error || 'An error occurred while sending the email.',
        variant: 'destructive'
      })
    } finally {
      setIsSending(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    // Ctrl/Cmd + Enter to send
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 transition-all duration-200 ease-in-out">
      {/* Collapsed view */}
      {!isExpanded && (
        <div className="flex items-center justify-between p-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors cursor-pointer"
             onClick={() => setIsExpanded(true)}>
          <div className="flex items-center gap-2">
            <Mail className="w-4 h-4 text-gray-600 dark:text-gray-400" />
            <div className="flex flex-col">
              <span className="text-sm text-gray-600 dark:text-gray-400">
                {replyMode ? (
                  replyMode === 'reply' ? 'Reply to email' : 
                  replyMode === 'reply-all' ? 'Reply to all' : 
                  'Forward email'
                ) : (
                  <>Compose email <span className="text-xs opacity-60">(press 'c')</span></>
                )}
              </span>
              {/* Show draft preview if there's content */}
              {(subject || to) && (
                <span className="text-xs text-gray-500 dark:text-gray-500 truncate max-w-md">
                  {to && <span>To: {to.split(',')[0]}{to.includes(',') ? '...' : ''}</span>}
                  {to && subject && ' • '}
                  {subject && <span>{subject}</span>}
                </span>
              )}
            </div>
          </div>
          <Button
            size="sm"
            variant="ghost"
            onClick={(e) => {
              e.stopPropagation()
              setIsExpanded(true)
            }}
          >
            <ChevronDown className="w-4 h-4" />
          </Button>
        </div>
      )}
      
      {/* Expanded view */}
      {isExpanded && (
        <div className="flex flex-col space-y-3 p-4">
          {/* Collapse button */}
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Compose Email</span>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                setIsExpanded(false)
                // Also cancel reply mode if active
                if (replyMode && onCancelReply) {
                  onCancelReply()
                }
              }}
            >
              <ChevronUp className="w-4 h-4" />
            </Button>
          </div>
          
          {/* Reply mode indicator */}
          {replyMode && (
            <div className="flex items-center justify-between px-3 py-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
              <span className="text-sm text-blue-700 dark:text-blue-300">
                {replyMode === 'reply' ? 'Replying to' : replyMode === 'reply-all' ? 'Replying to all' : 'Forwarding'} message
              </span>
              <Button
                size="sm"
                variant="ghost"
                onClick={onCancelReply}
                className="h-6 px-2"
              >
                <X className="w-3 h-3" />
              </Button>
            </div>
          )}

          {/* Email fields */}
          <div className="space-y-2">
        {/* From field - only show if multiple accounts */}
        {emailAccounts.length > 1 && (
          <div className="flex items-center space-x-2">
            <Label htmlFor="from" className="w-16 text-sm">From:</Label>
            <Select value={selectedAccountId} onValueChange={setSelectedAccountId}>
              <SelectTrigger className="flex-1">
                <SelectValue placeholder="Select email account" />
              </SelectTrigger>
              <SelectContent>
                {emailAccounts.map(account => (
                  <SelectItem key={account.account_id} value={account.account_id}>
                    <div className="flex items-center gap-2">
                      <Mail className="w-3 h-3" />
                      <span>{account.email}</span>
                      {account.provider && (
                        <span className="text-xs text-gray-500">({account.provider})</span>
                      )}
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
        
        {/* From field - single account display */}
        {emailAccounts.length === 1 && (
          <div className="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400">
            <Label className="w-16 text-sm">From:</Label>
            <div className="flex items-center gap-2">
              <Mail className="w-3 h-3" />
              <span>{emailAccounts[0].email}</span>
            </div>
          </div>
        )}
        
        <div className="flex items-center space-x-2">
          <Label htmlFor="to" className="w-16 text-sm">To:</Label>
          <Input
            id="to"
            type="email"
            placeholder="recipient@example.com, another@example.com"
            value={to}
            onChange={(e) => setTo(e.target.value)}
            disabled={isSending}
            className="flex-1"
          />
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setShowCcBcc(!showCcBcc)}
            className="text-xs"
          >
            {showCcBcc ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            <span className="ml-1">Cc/Bcc</span>
          </Button>
        </div>

        {showCcBcc && (
          <>
            <div className="flex items-center space-x-2">
              <Label htmlFor="cc" className="w-16 text-sm">Cc:</Label>
              <Input
                id="cc"
                type="email"
                placeholder="cc@example.com"
                value={cc}
                onChange={(e) => setCc(e.target.value)}
                disabled={isSending}
                className="flex-1"
              />
            </div>
            <div className="flex items-center space-x-2">
              <Label htmlFor="bcc" className="w-16 text-sm">Bcc:</Label>
              <Input
                id="bcc"
                type="email"
                placeholder="bcc@example.com"
                value={bcc}
                onChange={(e) => setBcc(e.target.value)}
                disabled={isSending}
                className="flex-1"
              />
            </div>
          </>
        )}

        <div className="flex items-center space-x-2">
          <Label htmlFor="subject" className="w-16 text-sm">Subject:</Label>
          <Input
            id="subject"
            placeholder="Email subject"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            disabled={isSending}
            className="flex-1"
          />
        </div>
          </div>

          {/* Rich text editor */}
          <div className="space-y-1">
        {/* Toolbar */}
        <div className="flex items-center gap-1 p-1 border rounded-t-md bg-gray-50 dark:bg-gray-900">
          <button
            type="button"
            onClick={() => document.execCommand('bold', false)}
            className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
            title="Bold"
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 4h4M14 4l-4 16m-2 0h4" />
            </svg>
          </button>
          <button
            type="button"
            onClick={() => document.execCommand('underline', false)}
            className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
            title="Underline"
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 4v7a5 5 0 0010 0V4M5 21h14" />
            </svg>
          </button>
          <div className="w-px h-4 bg-gray-300 dark:bg-gray-600 mx-1" />
          <button
            type="button"
            onClick={() => document.execCommand('insertUnorderedList', false)}
            className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
            title="Bullet List"
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <button
            type="button"
            onClick={() => document.execCommand('insertOrderedList', false)}
            className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
            title="Numbered List"
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
            </svg>
          </button>
          <div className="w-px h-4 bg-gray-300 dark:bg-gray-600 mx-1" />
          <button
            type="button"
            onClick={() => {
              const url = prompt('Enter URL:')
              if (url) document.execCommand('createLink', false, url)
            }}
            className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
            title="Insert Link"
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
            </svg>
          </button>
        </div>
        
        {/* Editor */}
        <div
          ref={editorRef}
          contentEditable={!isSending}
          className="min-h-[120px] max-h-[300px] p-3 border rounded-b-md bg-white dark:bg-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 overflow-y-auto"
          onKeyDown={handleKeyPress}
          suppressContentEditableWarning={true}
        />
          </div>

          {/* Actions */}
          <div className="flex items-center justify-between">
        <Button
          variant="ghost"
          size="sm"
          disabled={isSending}
          title="Add attachment"
        >
          <Paperclip className="w-4 h-4" />
        </Button>
        
        <div className="flex items-center space-x-2">
          <span className="text-xs text-gray-500">Ctrl+Enter to send</span>
          <Button
            onClick={handleSend}
            disabled={!to.trim() || !subject.trim() || isSending}
            size="sm"
          >
            <Send className="w-4 h-4 mr-1" />
            {isSending ? 'Sending...' : 'Send'}
          </Button>
        </div>
          </div>
        </div>
      )}
    </div>
  )
}