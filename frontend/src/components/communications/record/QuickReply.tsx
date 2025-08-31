import React, { useState } from 'react'
import { Send, Paperclip, Smile } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { useAuth } from '@/features/auth/context'
import { api } from '@/lib/api'
import { toast } from '@/hooks/use-toast'
import Cookies from 'js-cookie'

interface QuickReplyProps {
  conversationId: string
  recordId: string
  onMessageSent?: () => void
}

export function QuickReply({
  conversationId,
  recordId,
  onMessageSent
}: QuickReplyProps) {
  // Get access token directly from cookies
  const accessToken = Cookies.get('oneo_access_token')
  const [message, setMessage] = useState('')
  const [isSending, setIsSending] = useState(false)

  const handleSend = async () => {
    if (!message.trim() || !accessToken) return

    setIsSending(true)

    try {
      await api.post(
        `/api/v1/communications/records/${recordId}/quick_reply/`,
        {
          conversation_id: conversationId,
          content: message,
          channel_type: 'email' // Default to email, could be dynamic based on conversation
        }
      )

      // Clear message
      setMessage('')
      
      // Show success toast
      toast({
        title: 'Message sent',
        description: 'Your message has been sent successfully.',
      })

      // Callback to refresh messages
      if (onMessageSent) {
        onMessageSent()
      }
    } catch (err: any) {
      console.error('Failed to send message:', err)
      toast({
        title: 'Failed to send message',
        description: err.response?.data?.error || 'An error occurred while sending the message.',
        variant: 'destructive'
      })
    } finally {
      setIsSending(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex items-end space-x-2">
      <div className="flex-1">
        <Textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type a message..."
          className="min-h-[60px] max-h-[120px] resize-none"
          disabled={isSending}
        />
      </div>
      
      <div className="flex space-x-1">
        <Button
          variant="ghost"
          size="icon"
          disabled={isSending}
          title="Add attachment"
        >
          <Paperclip className="w-4 h-4" />
        </Button>
        
        <Button
          variant="ghost"
          size="icon"
          disabled={isSending}
          title="Add emoji"
        >
          <Smile className="w-4 h-4" />
        </Button>
        
        <Button
          onClick={handleSend}
          disabled={!message.trim() || isSending}
          size="icon"
        >
          <Send className="w-4 h-4" />
        </Button>
      </div>
    </div>
  )
}