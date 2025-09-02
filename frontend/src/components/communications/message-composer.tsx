'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { Send, Paperclip, X, User, AtSign, Hash, Bold, Italic, Underline, Link } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { useToast } from '@/hooks/use-toast'
import { communicationsApi } from '@/lib/api'
import { EnhancedRichEditor } from './enhanced-rich-editor'

interface Attachment {
  id: string
  name: string
  size: number
  type: string
  url?: string
  file?: File
  uploading?: boolean
  storage_path?: string
  uploaded_at?: string
  account_id?: string
  conversation_id?: string
  user_id?: number
}

interface MessageComposerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  conversationId?: string
  recipientType?: 'new' | 'reply'
  defaultRecipient?: {
    name: string
    email?: string
    platform?: string
    platform_id?: string
  }
  accountConnections: Array<{
    id: string
    channelType: string
    accountName: string
    canSendMessages: boolean
  }>
}

export function MessageComposer({
  open,
  onOpenChange,
  conversationId,
  recipientType = 'new',
  defaultRecipient,
  accountConnections
}: MessageComposerProps) {
  const [selectedAccount, setSelectedAccount] = useState<string>('')
  const [recipient, setRecipient] = useState('')
  const [subject, setSubject] = useState('')
  const [content, setContent] = useState('')
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [sending, setSending] = useState(false)
  const [isRichText, setIsRichText] = useState(false)
  
  // Draft functionality
  const [autoSaveEnabled, setAutoSaveEnabled] = useState(true)
  const [lastAutoSave, setLastAutoSave] = useState<Date | null>(null)
  const [isDraftLoaded, setIsDraftLoaded] = useState(false)
  const [currentDraftId, setCurrentDraftId] = useState<string | null>(null)
  const [savingDraft, setSavingDraft] = useState(false)
  
  const fileInputRef = useRef<HTMLInputElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const { toast } = useToast()

  // Get available accounts that can send messages
  const availableAccounts = accountConnections.filter(acc => acc.canSendMessages)

  // Reset form when dialog opens/closes
  useEffect(() => {
    if (open) {
      if (defaultRecipient) {
        setRecipient(defaultRecipient.email || defaultRecipient.name || '')
      }
      // Auto-select first available account if only one option
      if (availableAccounts.length === 1) {
        setSelectedAccount(availableAccounts[0].id)
      }
    } else {
      // Reset form
      setSelectedAccount('')
      setRecipient('')
      setSubject('')
      setContent('')
      setAttachments([])
      setSending(false)
      setIsDraftLoaded(false)
      setCurrentDraftId(null)
      setLastAutoSave(null)
      setSavingDraft(false)
    }
  }, [open, defaultRecipient?.email, defaultRecipient?.name, availableAccounts.length])

  // Auto-save functionality
  const autoSaveDraft = useCallback(async () => {
    if (!autoSaveEnabled || !content.trim() || !selectedAccount) {
      return
    }

    try {
      setSavingDraft(true)
      const draftData = {
        content: content.trim(),
        subject: subject.trim(),
        recipient: recipient.trim(),
        account_connection_id: selectedAccount,
        conversation_id: conversationId,
        recipient_type: recipientType,
        attachments: attachments.filter(att => !att.uploading)
      }

      await communicationsApi.autoSaveDraft(draftData)
      setLastAutoSave(new Date())
    } catch (error) {
      console.error('Failed to auto-save draft:', error)
      // Don't show error toast for auto-save failures to avoid annoying users
    } finally {
      setSavingDraft(false)
    }
  }, [autoSaveEnabled, content, selectedAccount, subject, recipient, conversationId, recipientType, attachments])

  // Auto-save timer (30 seconds after last change)
  useEffect(() => {
    if (!open || !autoSaveEnabled) return

    const timeoutId = setTimeout(() => {
      autoSaveDraft()
    }, 30000) // 30 seconds

    return () => clearTimeout(timeoutId)
  }, [open, autoSaveEnabled, content, subject, recipient, selectedAccount, autoSaveDraft])

  // Load draft when dialog opens
  useEffect(() => {
    if (open && !isDraftLoaded) {
      loadDraftForContext()
    }
  }, [open, isDraftLoaded])

  const loadDraftForContext = async () => {
    try {
      const params: any = {}
      if (conversationId) params.conversation_id = conversationId
      if (selectedAccount) params.account_connection_id = selectedAccount
      if (recipient) params.recipient = recipient

      const response = await communicationsApi.getDraftForContext(params)
      
      if (response.data.has_draft) {
        const draft = response.data.draft
        const shouldRecover = confirm(
          `You have an unsaved draft from ${new Date(draft.updated_at).toLocaleString()}. Would you like to recover it?`
        )
        
        if (shouldRecover) {
          setContent(draft.content || '')
          setSubject(draft.subject || '')
          setRecipient(draft.recipient || '')
          setSelectedAccount(draft.account_connection_id || '')
          setAttachments(draft.attachments_data || [])
          setCurrentDraftId(draft.id)
          
          toast({
            title: "Draft recovered",
            description: "Your previous draft has been restored.",
          })
        }
      }
    } catch (error) {
      console.error('Failed to load draft:', error)
    } finally {
      setIsDraftLoaded(true)
    }
  }

  const saveManualDraft = async () => {
    const draftName = prompt('Enter a name for this draft:')
    if (!draftName?.trim()) return

    try {
      setSavingDraft(true)
      const draftData = {
        content: content.trim(),
        subject: subject.trim(),
        recipient: recipient.trim(),
        account_connection_id: selectedAccount,
        conversation_id: conversationId,
        recipient_type: recipientType,
        attachments: attachments.filter(att => !att.uploading),
        draft_name: draftName.trim()
      }

      await communicationsApi.saveManualDraft(draftData)
      
      toast({
        title: "Draft saved",
        description: `Draft "${draftName}" has been saved successfully.`,
      })
    } catch (error) {
      console.error('Failed to save draft:', error)
      toast({
        title: "Failed to save draft",
        description: "There was an error saving your draft. Please try again.",
        variant: "destructive",
      })
    } finally {
      setSavingDraft(false)
    }
  }

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    if (!files) return

    Array.from(files).forEach(async (file) => {
      // Create temporary attachment while uploading
      const tempAttachment: Attachment = {
        id: Math.random().toString(36).substr(2, 9),
        name: file.name,
        size: file.size,
        type: file.type,
        file,
        uploading: true
      }
      setAttachments(prev => [...prev, tempAttachment])

      try {
        // Upload the file
        const formData = new FormData()
        formData.append('file', file)
        formData.append('account_id', selectedAccount)
        if (conversationId) {
          formData.append('conversation_id', conversationId)
        }

        const uploadResponse = await communicationsApi.uploadAttachment(formData)
        const uploadedAttachment = uploadResponse.data.attachment

        // Update the attachment with uploaded data
        setAttachments(prev => prev.map(att => 
          att.id === tempAttachment.id 
            ? { ...uploadedAttachment, uploading: false }
            : att
        ))

        toast({
          title: "File uploaded",
          description: `${file.name} has been uploaded successfully.`,
        })
      } catch (error) {
        console.error('Error uploading file:', error)
        
        // Remove failed upload
        setAttachments(prev => prev.filter(att => att.id !== tempAttachment.id))
        
        toast({
          title: "Upload failed",
          description: `Failed to upload ${file.name}. Please try again.`,
          variant: "destructive",
        })
      }
    })

    // Clear the input
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const removeAttachment = async (id: string) => {
    const attachment = attachments.find(att => att.id === id)
    if (!attachment) return

    // If file is uploading, just remove from local state
    if (attachment.uploading) {
      setAttachments(prev => prev.filter(att => att.id !== id))
      return
    }

    // If file was uploaded, try to delete from server
    try {
      if (attachment.url || attachment.storage_path) {
        await communicationsApi.deleteAttachment(id)
      }
      setAttachments(prev => prev.filter(att => att.id !== id))
    } catch (error) {
      console.error('Error deleting attachment:', error)
      // Still remove from UI even if server deletion fails
      setAttachments(prev => prev.filter(att => att.id !== id))
      toast({
        title: "Warning",
        description: "Attachment removed from message, but may still exist on server.",
        variant: "destructive",
      })
    }
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const convertMarkdownToHtml = (markdown: string): string => {
    let html = markdown
    
    // Convert links: [text](url) to <a href="url">text</a>
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>')
    
    // Convert bold: **text** to <strong>text</strong>
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    
    // Convert italic: *text* to <em>text</em>  
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>')
    
    // Convert underline: _text_ to <u>text</u>
    html = html.replace(/_([^_]+)_/g, '<u>$1</u>')
    
    // Convert line breaks to <br>
    html = html.replace(/\n/g, '<br>')
    
    return html
  }

  const insertTextAtCursor = (insertText: string, wrapText = false) => {
    if (!textareaRef.current) return

    const textarea = textareaRef.current
    const start = textarea.selectionStart
    const end = textarea.selectionEnd
    const selectedText = content.substring(start, end)

    let newText
    if (wrapText && selectedText) {
      newText = content.substring(0, start) + insertText + selectedText + insertText + content.substring(end)
    } else {
      newText = content.substring(0, start) + insertText + content.substring(end)
    }

    setContent(newText)

    // Set cursor position after the inserted text
    setTimeout(() => {
      const newCursorPos = wrapText ? end + insertText.length : start + insertText.length
      textarea.setSelectionRange(newCursorPos, newCursorPos)
      textarea.focus()
    }, 0)
  }

  const handleRichTextAction = (action: string) => {
    switch (action) {
      case 'bold':
        insertTextAtCursor('**', true)
        break
      case 'italic':
        insertTextAtCursor('*', true)
        break
      case 'underline':
        insertTextAtCursor('_', true)
        break
      case 'link':
        const url = prompt('Enter URL:')
        if (url) {
          const text = textareaRef.current?.value.substring(
            textareaRef.current.selectionStart,
            textareaRef.current.selectionEnd
          ) || 'Link'
          insertTextAtCursor(`[${text}](${url})`)
        }
        break
      case 'mention':
        insertTextAtCursor('@')
        break
      case 'hashtag':
        insertTextAtCursor('#')
        break
    }
  }

  const handleSend = async () => {
    if (!selectedAccount || !content.trim()) {
      toast({
        title: "Missing Information",
        description: "Please select an account and enter a message.",
        variant: "destructive",
      })
      return
    }

    if (recipientType === 'new' && !recipient.trim()) {
      toast({
        title: "Missing Recipient",
        description: "Please enter a recipient for the new message.",
        variant: "destructive",
      })
      return
    }

    // Check if any files are still uploading
    const uploadingFiles = attachments.filter(att => att.uploading)
    if (uploadingFiles.length > 0) {
      toast({
        title: "Files Still Uploading",
        description: "Please wait for all files to finish uploading before sending.",
        variant: "destructive",
      })
      return
    }

    setSending(true)
    try {
      // Check if this is an email account
      const selectedAccountData = accountConnections.find(acc => acc.id === selectedAccount)
      const isEmailAccount = selectedAccountData?.channelType === 'gmail' || 
                            selectedAccountData?.channelType === 'outlook' || 
                            selectedAccountData?.channelType === 'email'
      
      // For emails, content is already HTML from the rich editor
      // For other messages, we might need to convert markdown
      const messageContent = content.trim()
      
      const messageData = {
        conversation_id: conversationId,
        content: messageContent,
        account_id: selectedAccount,
        attachments: attachments.filter(att => !att.uploading).map(att => ({
          id: att.id,
          name: att.name,
          size: att.size,
          type: att.type,
          url: att.url,
          storage_path: att.storage_path,
          uploaded_at: att.uploaded_at,
          account_id: att.account_id,
          conversation_id: att.conversation_id,
          user_id: att.user_id
        })),
        recipient: recipientType === 'new' ? recipient : undefined,
        subject: subject.trim() || undefined
      }

      // Use the enhanced attachment-aware API endpoint
      if (attachments.length > 0) {
        await communicationsApi.sendMessageWithAttachments(messageData)
      } else {
        // Use the simple API for messages without attachments
        const simpleMessageData = {
          conversation_id: conversationId,
          content: messageContent,
          type: accountConnections.find(acc => acc.id === selectedAccount)?.channelType || 'email',
          recipient: recipientType === 'new' ? recipient : undefined,
          subject: subject.trim() || undefined
        }
        await communicationsApi.sendMessage(simpleMessageData)
      }

      toast({
        title: "Message Sent",
        description: attachments.length > 0 
          ? `Your message with ${attachments.length} attachment${attachments.length === 1 ? '' : 's'} has been sent successfully.`
          : "Your message has been sent successfully.",
      })

      onOpenChange(false)
    } catch (error) {
      console.error('Error sending message:', error)
      toast({
        title: "Failed to Send",
        description: "There was an error sending your message. Please try again.",
        variant: "destructive",
      })
    } finally {
      setSending(false)
    }
  }

  const selectedAccountData = accountConnections.find(acc => acc.id === selectedAccount)
  const isEmailType = selectedAccountData?.channelType === 'gmail' || 
                     selectedAccountData?.channelType === 'outlook' || 
                     selectedAccountData?.channelType === 'mail'

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>
            {recipientType === 'reply' ? 'Reply to Message' : 'Compose New Message'}
          </DialogTitle>
          <DialogDescription>
            Send a message using your connected communication accounts.
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 space-y-4 overflow-y-auto">
          {/* Account Selection */}
          <div className="space-y-2">
            <Label htmlFor="account">Send From</Label>
            <Select value={selectedAccount} onValueChange={setSelectedAccount}>
              <SelectTrigger>
                <SelectValue placeholder="Select an account to send from" />
              </SelectTrigger>
              <SelectContent>
                {availableAccounts.map((account) => (
                  <SelectItem key={account.id} value={account.id}>
                    <div className="flex items-center space-x-2">
                      <span className="capitalize">{account.channelType}</span>
                      <span className="text-muted-foreground">-</span>
                      <span>{account.accountName}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {availableAccounts.length === 0 && (
              <p className="text-sm text-muted-foreground">
                No accounts available for sending messages. Please connect an account first.
              </p>
            )}
          </div>

          {/* Recipient (for new messages) */}
          {recipientType === 'new' && (
            <div className="space-y-2">
              <Label htmlFor="recipient">
                To {isEmailType ? '(Email)' : '(Username/ID)'}
              </Label>
              <Input
                id="recipient"
                value={recipient}
                onChange={(e) => setRecipient(e.target.value)}
                placeholder={isEmailType ? "recipient@example.com" : "Username or user ID"}
              />
            </div>
          )}

          {/* Subject (for email) */}
          {isEmailType && (
            <div className="space-y-2">
              <Label htmlFor="subject">Subject</Label>
              <Input
                id="subject"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="Enter email subject"
              />
            </div>
          )}

          {/* Message Content */}
          <div className="space-y-2">
            <Label htmlFor="content">Message</Label>
            {isEmailType ? (
              // Rich HTML editor for emails
              <EnhancedRichEditor
                value={content}
                onChange={setContent}
                placeholder="Compose your email..."
                className="min-h-[200px]"
              />
            ) : (
              // Simple textarea with markdown toolbar for other message types
              <>
                {/* Rich Text Toolbar for non-email messages */}
                <div className="flex items-center space-x-1 p-2 border rounded-md bg-muted/20">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => handleRichTextAction('bold')}
                    title="Bold (**text**)"
                  >
                    <Bold className="w-4 h-4" />
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => handleRichTextAction('italic')}
                    title="Italic (*text*)"
                  >
                    <Italic className="w-4 h-4" />
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => handleRichTextAction('underline')}
                    title="Underline (_text_)"
                  >
                    <Underline className="w-4 h-4" />
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => handleRichTextAction('link')}
                    title="Link [text](url)"
                  >
                    <Link className="w-4 h-4" />
                  </Button>
                  <Separator orientation="vertical" className="h-6" />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => handleRichTextAction('mention')}
                    title="Mention @username"
                  >
                    <AtSign className="w-4 h-4" />
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => handleRichTextAction('hashtag')}
                    title="Hashtag #tag"
                  >
                    <Hash className="w-4 h-4" />
                  </Button>
                </div>
                <Textarea
                  ref={textareaRef}
                  id="content"
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  placeholder="Type your message here..."
                  className="min-h-[120px] resize-none"
                  rows={6}
                />
                <p className="text-xs text-muted-foreground">
                  Supports markdown formatting: **bold**, *italic*, _underline_, [links](url)
                </p>
              </>
            )}
          </div>

          {/* Attachments */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Attachments</Label>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => fileInputRef.current?.click()}
                disabled={!selectedAccount}
                title={!selectedAccount ? "Please select an account first" : "Add files to your message"}
              >
                <Paperclip className="w-4 h-4 mr-2" />
                Add Files
              </Button>
            </div>
            
            <input
              ref={fileInputRef}
              type="file"
              multiple
              className="hidden"
              onChange={handleFileSelect}
              accept="image/*,video/*,.pdf,.doc,.docx,.txt,.csv,.xlsx"
            />

            {attachments.length > 0 && (
              <div className="space-y-2 max-h-32 overflow-y-auto">
                {attachments.map((attachment) => (
                  <div
                    key={attachment.id}
                    className={`flex items-center justify-between p-2 border rounded-md ${
                      attachment.uploading ? 'bg-blue-50 border-blue-200' : 'bg-muted/20'
                    }`}
                  >
                    <div className="flex items-center space-x-2 flex-1 min-w-0">
                      <Paperclip className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2">
                          <p className="text-sm font-medium truncate">{attachment.name}</p>
                          {attachment.uploading && (
                            <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-500"></div>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {formatFileSize(attachment.size)}
                          {attachment.uploading && ' - Uploading...'}
                        </p>
                      </div>
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => removeAttachment(attachment.id)}
                      disabled={attachment.uploading}
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-between pt-4 border-t">
          <div className="flex items-center space-x-2 text-sm text-muted-foreground">
            {selectedAccountData && (
              <Badge variant="outline" className="capitalize">
                {selectedAccountData.channelType}
              </Badge>
            )}
            {attachments.length > 0 && (
              <Badge variant="secondary">
                {attachments.length} attachment{attachments.length !== 1 ? 's' : ''}
              </Badge>
            )}
            {/* Draft status */}
            {savingDraft && (
              <Badge variant="outline" className="text-blue-600">
                Saving draft...
              </Badge>
            )}
            {lastAutoSave && !savingDraft && (
              <Badge variant="outline" className="text-green-600">
                Saved {lastAutoSave.toLocaleTimeString()}
              </Badge>
            )}
          </div>

          <div className="flex space-x-2">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={saveManualDraft}
              disabled={sending || savingDraft || !content.trim()}
              title="Save as named draft"
            >
              Save Draft
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={sending}
            >
              Cancel
            </Button>
            <Button
              onClick={handleSend}
              disabled={sending || !content.trim() || !selectedAccount}
            >
              {sending ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Sending...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4 mr-2" />
                  Send Message
                </>
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}