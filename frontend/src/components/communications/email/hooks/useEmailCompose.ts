import { useState, useCallback, useRef } from 'react'
import { emailService } from '@/services/emailService'
import { useToast } from '@/hooks/use-toast'
import { EmailAccount, EmailThread, EmailMessage, ReplyMode } from '../utils/emailTypes'
import { formatReplyBody, formatForwardBody, parseEmailAddresses } from '../utils/emailFormatters'

interface UseEmailComposeProps {
  selectedAccount: EmailAccount | null
  selectedThread: EmailThread | null
  threadMessages: EmailMessage[]
  onEmailSent?: (page: number) => void
}

export const useEmailCompose = ({ 
  selectedAccount, 
  selectedThread,
  threadMessages,
  onEmailSent 
}: UseEmailComposeProps) => {
  const [composeOpen, setComposeOpen] = useState(false)
  const [replyMode, setReplyMode] = useState<ReplyMode>(null)
  const [replyToMessage, setReplyToMessage] = useState<EmailMessage | null>(null)
  
  // Compose fields
  const [composeTo, setComposeTo] = useState('')
  const [composeCc, setComposeCc] = useState('')
  const [composeBcc, setComposeBcc] = useState('')
  const [composeSubject, setComposeSubject] = useState('')
  const [composeBody, setComposeBody] = useState('')
  const [sending, setSending] = useState(false)
  
  // Editor refs
  const editorRef = useRef<HTMLDivElement>(null)
  const [editorKey, setEditorKey] = useState(0)
  const lastOpenState = useRef(false)
  
  const { toast } = useToast()

  const resetCompose = useCallback(() => {
    setReplyMode(null)
    setReplyToMessage(null)
    setComposeTo('')
    setComposeCc('')
    setComposeBcc('')
    setComposeSubject('')
    setComposeBody('')
    if (editorRef.current) {
      editorRef.current.innerHTML = ''
    }
  }, [])

  const handleCompose = useCallback(() => {
    resetCompose()
    setComposeOpen(true)
  }, [resetCompose])

  const handleReply = useCallback((message?: EmailMessage) => {
    if (!selectedThread || !selectedAccount) return
    
    const targetMessage = message || threadMessages[threadMessages.length - 1]
    if (!targetMessage) return
    
    setReplyMode('reply')
    setReplyToMessage(targetMessage)
    setComposeTo(targetMessage.sender.email)
    setComposeSubject(`Re: ${targetMessage.subject || selectedThread.subject || ''}`)
    
    const replyBody = formatReplyBody(targetMessage, selectedThread.subject)
    setComposeBody(replyBody)
    setComposeOpen(true)
  }, [selectedThread, selectedAccount, threadMessages])

  const handleForward = useCallback(() => {
    if (!selectedThread || !threadMessages.length) return
    
    const lastMessage = threadMessages[threadMessages.length - 1]
    setReplyMode('forward')
    setReplyToMessage(lastMessage)
    setComposeTo('')
    setComposeSubject(`Fwd: ${lastMessage.subject || selectedThread.subject || ''}`)
    
    const forwardBody = formatForwardBody(lastMessage, selectedThread.subject)
    setComposeBody(forwardBody)
    setComposeOpen(true)
  }, [selectedThread, threadMessages])

  const handleSendEmail = useCallback(async () => {
    if (!selectedAccount) return
    
    setSending(true)
    try {
      const toRecipients = parseEmailAddresses(composeTo)
      const ccRecipients = composeCc ? parseEmailAddresses(composeCc) : []
      const bccRecipients = composeBcc ? parseEmailAddresses(composeBcc) : []
      
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
        resetCompose()
        
        // Trigger refresh
        if (onEmailSent) {
          onEmailSent(1) // Reload first page
        }
      } else {
        throw new Error(result.error || 'Failed to send email')
      }
    } catch (error: any) {
      console.error('Failed to send email:', error)
      toast({
        title: 'Error',
        description: error.message || 'Failed to send email',
        variant: 'destructive'
      })
    } finally {
      setSending(false)
    }
  }, [
    selectedAccount,
    composeTo,
    composeCc,
    composeBcc,
    composeSubject,
    composeBody,
    replyMode,
    replyToMessage,
    resetCompose,
    onEmailSent,
    toast
  ])

  const closeCompose = useCallback(() => {
    setComposeOpen(false)
    if (editorRef.current) {
      editorRef.current.innerHTML = ''
    }
  }, [])

  return {
    // State
    composeOpen,
    replyMode,
    replyToMessage,
    composeTo,
    composeCc,
    composeBcc,
    composeSubject,
    composeBody,
    sending,
    
    // Setters
    setComposeOpen,
    setComposeTo,
    setComposeCc,
    setComposeBcc,
    setComposeSubject,
    setComposeBody,
    
    // Actions
    handleCompose,
    handleReply,
    handleForward,
    handleSendEmail,
    closeCompose,
    
    // Editor refs
    editorRef,
    editorKey,
    setEditorKey,
    lastOpenState
  }
}