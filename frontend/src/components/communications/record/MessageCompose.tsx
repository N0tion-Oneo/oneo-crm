import React, { useState, useRef, useEffect } from 'react'
import { Send, Paperclip, X, ChevronDown, ChevronUp, MessageSquare, Phone } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { api } from '@/lib/api'
import { toast } from '@/hooks/use-toast'

interface Attachment {
  id: string
  filename: string
  size: number
  content_type: string
  data?: string // Base64 encoded data
  file?: File // Original file object
}

interface MessageComposeProps {
  conversationId: string | null
  recordId: string
  onMessageSent?: () => void
  replyTo?: any // Message to reply to
  onCancelReply?: () => void
  channelType: 'whatsapp' | 'linkedin'
  defaultRecipient?: string // For new messages at record level (phone for WhatsApp, name for LinkedIn)
}

export function MessageCompose({
  conversationId,
  recordId,
  onMessageSent,
  replyTo,
  onCancelReply,
  channelType,
  defaultRecipient
}: MessageComposeProps) {
  const [to, setTo] = useState(() => {
    if (typeof defaultRecipient === 'string') return defaultRecipient
    return ''
  })
  const [text, setText] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [accounts, setAccounts] = useState<any[]>([])
  const [selectedAccountId, setSelectedAccountId] = useState<string>('')
  const [isExpanded, setIsExpanded] = useState(false)
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Fetch accounts on mount
  useEffect(() => {
    const fetchAccounts = async () => {
      try {
        console.log(`🔍 Fetching ${channelType} accounts...`)
        
        // Get user connections for the specific channel type
        const response = await api.get('/api/v1/communications/connections/')
        console.log('📥 Connections response:', response.data)
        
        // Handle paginated response
        const allConnections = response.data.results || response.data
        
        // The API returns camelCase fields
        const connections = allConnections.filter((conn: any) => 
          conn.channelType === channelType && conn.isActive !== false
        )
        
        console.log(`📋 Filtered ${channelType} connections:`, connections)
        
        if (connections.length > 0) {
          setAccounts(connections)
          // Auto-select first account - API returns 'externalAccountId'
          setSelectedAccountId(connections[0].externalAccountId || connections[0].id)
          console.log(`✅ Set ${connections.length} ${channelType} accounts, selected:`, connections[0].externalAccountId || connections[0].id)
        } else {
          console.log(`⚠️ No ${channelType} accounts found`)
        }
      } catch (error) {
        console.error('❌ Failed to fetch accounts:', error)
      }
    }
    fetchAccounts()
  }, [channelType])
  
  // Initialize recipient for new messages
  useEffect(() => {
    if (defaultRecipient && !conversationId && !replyTo) {
      // Ensure defaultRecipient is a string
      const recipientStr = typeof defaultRecipient === 'string' ? defaultRecipient : String(defaultRecipient || '')
      setTo(recipientStr)
    }
  }, [defaultRecipient, conversationId, replyTo])
  
  // Auto-expand when replying
  useEffect(() => {
    if (replyTo) {
      setIsExpanded(true)
      // Focus on text input
      setTimeout(() => textareaRef.current?.focus(), 100)
    }
  }, [replyTo])
  
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
        if (replyTo && onCancelReply) {
          onCancelReply()
        }
      }
    }
    
    window.addEventListener('keydown', handleKeyPress)
    return () => window.removeEventListener('keydown', handleKeyPress)
  }, [isExpanded, replyTo, onCancelReply])

  const handleSend = async () => {
    console.log('🚀 MessageCompose: handleSend called', {
      conversationId,
      to,
      text,
      selectedAccountId,
      channelType,
      recordId,
      hostname: window.location.hostname,
      apiBaseUrl: `http://${window.location.hostname}:8000`
    })
    
    // Validate inputs
    if (!text.trim()) {
      toast({
        title: "Error",
        description: "Please enter a message",
        variant: "destructive"
      })
      return
    }

    if (!conversationId && !to.trim()) {
      toast({
        title: "Error", 
        description: `Please enter a ${channelType === 'whatsapp' ? 'phone number' : 'LinkedIn profile'}`,
        variant: "destructive"
      })
      return
    }

    if (!selectedAccountId) {
      toast({
        title: "Error",
        description: `Please select a ${channelType} account`,
        variant: "destructive"
      })
      return
    }

    setIsSending(true)

    try {
      // Build request data
      const requestData: any = {
        from_account_id: selectedAccountId,
        text: text.trim(),
        conversation_id: conversationId
      }
      
      // Add recipient for new conversations
      if (!conversationId && to) {
        requestData.to = to.trim()
      }
      
      // Add attachments if any
      if (attachments.length > 0) {
        requestData.attachments = attachments.map(att => ({
          filename: att.filename,
          content_type: att.content_type,
          data: att.data
        }))
      }

      // Send message via record communications API
      const endpoint = `/api/v1/communications/records/${recordId}/send_message/`
      console.log('📤 MessageCompose: Sending request')
      console.log('   Endpoint:', endpoint)
      console.log('   Full URL:', `http://${window.location.hostname}:8000${endpoint}`)
      console.log('   Request data:', requestData)
      
      const response = await api.post(endpoint, requestData)
      
      console.log('✅ MessageCompose: Success Response:', response.data)

      if (response.data.success) {
        toast({
          title: "Message Sent",
          description: `${channelType === 'whatsapp' ? 'WhatsApp' : 'LinkedIn'} message sent successfully`
        })

        // Clear form
        setText('')
        setTo('')
        setAttachments([])
        setIsExpanded(false)

        // Notify parent
        if (onMessageSent) {
          onMessageSent()
        }
      } else {
        throw new Error(response.data.error || 'Failed to send message')
      }
    } catch (error: any) {
      console.error('❌ MessageCompose: Failed to send message')
      console.error('   Error object:', error)
      console.error('   Error response:', error.response)
      console.error('   Error status:', error.response?.status)
      console.error('   Error data:', error.response?.data)
      console.error('   Error config:', error.config)
      console.error('   Request URL:', error.config?.url)
      console.error('   Request baseURL:', error.config?.baseURL)
      
      // Extract meaningful error message
      let errorMessage = 'Failed to send message'
      if (error.response?.data?.error) {
        errorMessage = error.response.data.error
      } else if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail
      } else if (error.response?.data?.message) {
        errorMessage = error.response.data.message
      } else if (error.message) {
        errorMessage = error.message
      }
      
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive"
      })
    } finally {
      setIsSending(false)
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files) return

    Array.from(files).forEach(file => {
      // Check file size (10MB limit for messaging)
      if (file.size > 10 * 1024 * 1024) {
        toast({
          title: "File too large",
          description: `${file.name} exceeds 10MB limit`,
          variant: "destructive"
        })
        return
      }

      // Read file as base64
      const reader = new FileReader()
      reader.onload = (evt) => {
        const base64 = evt.target?.result as string
        const attachment: Attachment = {
          id: `${Date.now()}-${Math.random()}`,
          filename: file.name,
          size: file.size,
          content_type: file.type || 'application/octet-stream',
          data: base64.split(',')[1], // Remove data:type;base64, prefix
          file
        }
        setAttachments(prev => [...prev, attachment])
      }
      reader.readAsDataURL(file)
    })

    // Clear input
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const removeAttachment = (id: string) => {
    setAttachments(prev => prev.filter(a => a.id !== id))
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return Math.round(bytes / 1024) + ' KB'
    return Math.round(bytes / (1024 * 1024) * 10) / 10 + ' MB'
  }

  const getPlaceholder = () => {
    if (channelType === 'whatsapp') {
      return conversationId ? 'Type a message...' : 'Enter phone number (e.g., +1234567890)'
    } else {
      return conversationId ? 'Type a message...' : 'Enter LinkedIn profile ID or name'
    }
  }

  const getIcon = () => {
    return channelType === 'whatsapp' ? 
      <Phone className="w-4 h-4" /> : 
      <MessageSquare className="w-4 h-4" />
  }

  // Collapsed view
  if (!isExpanded) {
    return (
      <div className="border rounded-lg p-3">
        <Button
          onClick={() => setIsExpanded(true)}
          variant="ghost"
          className="w-full justify-start text-muted-foreground"
        >
          {getIcon()}
          <span className="ml-2">
            {replyTo ? 'Reply to message' : `Send ${channelType === 'whatsapp' ? 'WhatsApp' : 'LinkedIn'} message`}
          </span>
        </Button>
      </div>
    )
  }

  // Expanded view
  return (
    <div className="border rounded-lg">
      {/* Header */}
      <div className="border-b px-4 py-2 flex items-center justify-between bg-muted/50">
        <div className="flex items-center gap-2">
          {getIcon()}
          <span className="font-medium">
            {replyTo ? 'Reply' : `New ${channelType === 'whatsapp' ? 'WhatsApp' : 'LinkedIn'} Message`}
          </span>
        </div>
        <Button
          onClick={() => {
            setIsExpanded(false)
            if (onCancelReply) onCancelReply()
          }}
          variant="ghost"
          size="sm"
        >
          <ChevronUp className="w-4 h-4" />
        </Button>
      </div>

      {/* Body */}
      <div className="p-4 space-y-3">
        {/* Account selector */}
        <div>
          <Label>From</Label>
          <Select value={selectedAccountId} onValueChange={setSelectedAccountId}>
            <SelectTrigger>
              <SelectValue placeholder={`Select ${channelType} account`} />
            </SelectTrigger>
            <SelectContent>
              {accounts.map(account => (
                <SelectItem key={account.externalAccountId || account.id} value={account.externalAccountId || account.id}>
                  {account.accountName || account.externalAccountId || 'Unknown Account'}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* To field for new conversations */}
        {!conversationId && (
          <div>
            <Label>To</Label>
            <Input
              value={to}
              onChange={(e) => setTo(e.target.value)}
              placeholder={getPlaceholder()}
            />
          </div>
        )}

        {/* Message text */}
        <div>
          <Label>Message</Label>
          <Textarea
            ref={textareaRef}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Type your message..."
            rows={4}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && e.ctrlKey) {
                e.preventDefault()
                handleSend()
              }
            }}
          />
        </div>

        {/* Attachments */}
        {attachments.length > 0 && (
          <div className="space-y-2">
            <Label>Attachments</Label>
            {attachments.map(att => (
              <div key={att.id} className="flex items-center justify-between p-2 border rounded">
                <div className="flex items-center gap-2">
                  <Paperclip className="w-4 h-4 text-muted-foreground" />
                  <span className="text-sm">{att.filename}</span>
                  <span className="text-xs text-muted-foreground">({formatFileSize(att.size)})</span>
                </div>
                <Button
                  onClick={() => removeAttachment(att.id)}
                  variant="ghost"
                  size="sm"
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            ))}
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-between pt-2">
          <div className="flex items-center gap-2">
            <input
              ref={fileInputRef}
              type="file"
              multiple
              className="hidden"
              onChange={handleFileSelect}
              accept="image/*,video/*,audio/*,.pdf,.doc,.docx,.xls,.xlsx"
            />
            <Button
              onClick={() => fileInputRef.current?.click()}
              variant="ghost"
              size="sm"
              disabled={isSending}
            >
              <Paperclip className="w-4 h-4" />
            </Button>
          </div>
          
          <div className="flex items-center gap-2">
            <Button
              onClick={() => {
                setIsExpanded(false)
                if (onCancelReply) onCancelReply()
              }}
              variant="ghost"
              disabled={isSending}
            >
              Cancel
            </Button>
            <Button
              onClick={handleSend}
              disabled={isSending || !text.trim() || !selectedAccountId}
            >
              <Send className="w-4 h-4 mr-2" />
              Send
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}