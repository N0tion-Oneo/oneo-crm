import React, { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Paperclip, X, ChevronDown, ChevronUp, Mail, File, Image, FileText, PenTool } from 'lucide-react'
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
import { EnhancedRichEditor } from '../enhanced-rich-editor'
import { tenantSettingsAPI } from '@/lib/api/tenant-settings'
import { EmailSignaturePreview } from '../EmailSignaturePreview'

interface Attachment {
  id: string
  filename: string
  size: number
  content_type: string
  data?: string // Base64 encoded data
  file?: File // Original file object
}

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
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [bodyContent, setBodyContent] = useState<string>('')
  const [emailSignature, setEmailSignature] = useState<string>('')
  const [includeSignature, setIncludeSignature] = useState(true)
  const [signatureEnabled, setSignatureEnabled] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

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
  
  // Fetch email signature when component mounts or expands
  useEffect(() => {
    const fetchSignature = async () => {
      try {
        const result = await tenantSettingsAPI.renderEmailSignature()
        if (result.enabled && result.signature_html) {
          setEmailSignature(result.signature_html)
          setSignatureEnabled(true)
          // Don't add signature to the editor content - we'll display it separately
        }
      } catch (error) {
        console.error('Failed to fetch email signature:', error)
      }
    }
    
    if (isExpanded) {
      fetchSignature()
    }
  }, [isExpanded])
  
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
        const quotedBody = formatQuotedReply(replyTo)
        setBodyContent(`<br><br>${quotedBody}`)
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
        const quotedBody = formatQuotedReply(replyTo)
        setBodyContent(`<br><br>${quotedBody}`)
      } else if (replyMode === 'forward') {
        setTo('')
        setCc('')
        setBcc('')
        setSubject(`Fwd: ${replyTo.subject || ''}`.replace(/^(Fwd: )+/, 'Fwd: '))
        
        // Set forward body
        const quotedBody = formatQuotedForward(replyTo)
        setBodyContent(`<br><br>${quotedBody}`)
      }
    } else if (!replyMode) {
      // Clear fields when not replying
      setTo('')
      setCc('')
      setBcc('')
      setSubject('')
      setBodyContent('')
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

  const handleSignatureToggle = () => {
    setIncludeSignature(!includeSignature)
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

    // Combine body content with signature if enabled
    let body = bodyContent
    if (includeSignature && emailSignature) {
      body = `${bodyContent}<br><br>${emailSignature}`
    }
    
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
        body: body
      }
      
      // Only include reply fields if this is actually a reply
      if (replyTo?.id && replyMode) {
        payload.reply_to_message_id = replyTo.id
        payload.reply_mode = replyMode
      }
      
      // Only include conversation_id if it exists
      if (conversationId) {
        payload.conversation_id = conversationId
      }
      
      // Add attachments if any
      if (attachments.length > 0) {
        payload.attachments = attachments.map(att => ({
          filename: att.filename,
          content_type: att.content_type,
          data: att.data // Base64 encoded data
        }))
      }
      
      const response = await api.post(
        `/api/v1/communications/records/${recordId}/send_email/`,
        payload
      )
      
      // Check if the response was successful
      if (!response.data.success) {
        throw new Error(response.data.error || 'Failed to send email')
      }

      // Clear form
      setTo('')
      setCc('')
      setBcc('')
      setSubject('')
      setAttachments([])
      setBodyContent('')
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

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return

    const newAttachments: Attachment[] = []
    
    for (let i = 0; i < files.length; i++) {
      const file = files[i]
      
      // Check file size (25MB limit)
      if (file.size > 25 * 1024 * 1024) {
        toast({
          title: 'File too large',
          description: `${file.name} exceeds 25MB limit`,
          variant: 'destructive'
        })
        continue
      }

      // Convert to base64
      const reader = new FileReader()
      const base64Promise = new Promise<string>((resolve) => {
        reader.onload = () => {
          const base64 = reader.result as string
          resolve(base64.split(',')[1]) // Remove data:type;base64, prefix
        }
      })
      reader.readAsDataURL(file)
      
      const base64Data = await base64Promise

      newAttachments.push({
        id: Math.random().toString(36).substr(2, 9),
        filename: file.name,
        size: file.size,
        content_type: file.type || 'application/octet-stream',
        data: base64Data,
        file: file
      })
    }

    setAttachments(prev => [...prev, ...newAttachments])
    
    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const removeAttachment = (id: string) => {
    setAttachments(prev => prev.filter(a => a.id !== id))
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  const getAttachmentIcon = (mimeType: string) => {
    if (mimeType.startsWith('image/')) return <Image className="w-4 h-4" />
    if (mimeType.includes('pdf')) return <FileText className="w-4 h-4" />
    return <File className="w-4 h-4" />
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
        <div className="flex flex-col max-h-[500px]">
          {/* Header and scrollable content */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3 max-h-[450px]">
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

            {/* Rich HTML Email Editor */}
            <div className="my-2">
              <EnhancedRichEditor
                value={bodyContent}
                onChange={setBodyContent}
                placeholder="Compose your email..."
                className="min-h-[120px]"
              />
            </div>
            
            {/* Email Signature Section */}
            {signatureEnabled && (
              <div className="mt-3 border-t border-gray-200 dark:border-gray-700 pt-3">
                <div className="flex items-center justify-between mb-2">
                  <button
                    type="button"
                    onClick={handleSignatureToggle}
                    className="flex items-center gap-1.5 px-2 py-1 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
                  >
                    <PenTool className="w-3.5 h-3.5" />
                    <span className="text-xs">
                      Email Signature
                    </span>
                    <input
                      type="checkbox"
                      checked={includeSignature}
                      onChange={() => {}}
                      className="ml-2 h-3.5 w-3.5"
                    />
                  </button>
                </div>
                
                {/* Signature Preview */}
                {includeSignature && emailSignature && (
                  <div className="mt-2 bg-white rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                    <EmailSignaturePreview html={emailSignature} />
                  </div>
                )}
              </div>
            )}
            
            {/* Attachments */}
            {attachments.length > 0 && (
              <div className="p-3 border rounded-lg border-gray-200 dark:border-gray-700">
                <div className="text-xs font-medium text-gray-500 mb-2">
                  {attachments.length} attachment{attachments.length > 1 ? 's' : ''}
                </div>
                <div className="flex flex-wrap gap-2">
                  {attachments.map(attachment => (
                    <div
                      key={attachment.id}
                      className="flex items-center gap-2 px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded-md"
                    >
                      {getAttachmentIcon(attachment.content_type)}
                      <span className="text-xs">{attachment.filename}</span>
                      <span className="text-xs text-gray-500">({formatFileSize(attachment.size)})</span>
                      <button
                        onClick={() => removeAttachment(attachment.id)}
                        className="text-gray-400 hover:text-red-500"
                        title="Remove attachment"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
          
          {/* Fixed Actions bar */}
          <div className="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
            <div className="flex items-center justify-between">
              {/* Hidden file input */}
              <input
                ref={fileInputRef}
                type="file"
                multiple
                onChange={handleFileSelect}
                className="hidden"
                accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.txt,.csv,.zip"
              />
              
              <Button
                variant="ghost"
                size="sm"
                disabled={isSending}
                title="Add attachment"
                onClick={() => fileInputRef.current?.click()}
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
        </div>
      )}
    </div>
  )
}