'use client'

import React, { useState, useEffect, useRef, useCallback } from 'react'
import { MessageSquare, Search, Phone, Users, Send, RefreshCw, Link2, Database, Cloud, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { SafeAvatar } from '@/components/communications/SafeAvatar'
import { useToast } from '@/hooks/use-toast'
import { formatDistanceToNow } from 'date-fns'
import { whatsappService, type WhatsAppConversation, type WhatsAppMessage } from '@/services/whatsappService'
import { cn } from '@/lib/utils'

interface WhatsAppInboxLiveProps {
  className?: string
}

export function WhatsAppInboxLive({ className }: WhatsAppInboxLiveProps) {
  // State
  const [conversations, setConversations] = useState<WhatsAppConversation[]>([])
  const [selectedConversation, setSelectedConversation] = useState<WhatsAppConversation | null>(null)
  const [messages, setMessages] = useState<WhatsAppMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [messagesLoading, setMessagesLoading] = useState(false)
  const [sending, setSending] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState<'all' | 'individual' | 'group'>('all')
  const [showStorageFilter, setShowStorageFilter] = useState<'all' | 'stored' | 'not_stored' | 'can_link'>('all')
  const [selectedAccount, setSelectedAccount] = useState<string>('')
  const [accounts, setAccounts] = useState<any[]>([])
  const [cursor, setCursor] = useState<string | undefined>()
  const [hasMore, setHasMore] = useState(false)
  const [newMessage, setNewMessage] = useState('')
  const [linkDialogOpen, setLinkDialogOpen] = useState(false)
  const [linkingConversation, setLinkingConversation] = useState<WhatsAppConversation | null>(null)
  
  const { toast } = useToast()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })

  // Load accounts on mount
  useEffect(() => {
    loadAccounts()
  }, [])

  // Load conversations when filters change
  useEffect(() => {
    if (selectedAccount) {
      loadConversations(true) // Reset cursor on filter change
    }
  }, [selectedAccount, filterType])

  // Scroll to bottom when messages change
  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const loadAccounts = async () => {
    try {
      const result = await whatsappService.getAccounts()
      console.log('WhatsApp accounts response:', result)
      if (result.success && result.accounts.length > 0) {
        setAccounts(result.accounts)
        // Backend returns 'id' not 'account_id'
        setSelectedAccount(result.accounts[0].id || result.accounts[0].account_id)
      }
    } catch (error) {
      console.error('Failed to load accounts:', error)
    }
  }

  const loadConversations = async (reset = false) => {
    if (!selectedAccount) {
      console.log('No selected account, skipping conversation load')
      return
    }
    
    console.log('Loading conversations for account:', selectedAccount)
    setLoading(true)
    try {
      const result = await whatsappService.getLiveInbox({
        account_id: selectedAccount,
        chat_type: filterType === 'all' ? undefined : filterType,
        limit: 20,
        cursor: reset ? undefined : cursor,
        search: searchQuery
      })

      console.log('Conversations response:', result)
      // Log first conversation to see participant structure
      if (result.conversations && result.conversations.length > 0) {
        console.log('First conversation participants:', result.conversations[0].participants)
      }
      if (result.success) {
        if (reset) {
          setConversations(result.conversations || [])
        } else {
          setConversations(prev => [...prev, ...(result.conversations || [])])
        }
        setCursor(result.cursor)
        setHasMore(result.has_more || false)
      } else {
        console.error('Failed to load conversations:', result)
        toast({
          title: 'Error',
          description: result.error || 'Failed to load conversations',
          variant: 'destructive'
        })
      }
    } catch (error) {
      console.error('Error loading conversations:', error)
      toast({
        title: 'Error',
        description: 'Failed to load conversations',
        variant: 'destructive'
      })
    } finally {
      setLoading(false)
    }
  }

  const loadMessages = async (conversation: WhatsAppConversation) => {
    if (!selectedAccount) return
    
    setMessagesLoading(true)
    try {
      const result = await whatsappService.getChatMessages(
        conversation.id,
        selectedAccount
      )

      if (result.success) {
        setMessages(result.messages)
        setSelectedConversation(conversation)
      } else {
        toast({
          title: 'Error',
          description: 'Failed to load messages',
          variant: 'destructive'
        })
      }
    } catch (error) {
      console.error('Error loading messages:', error)
      toast({
        title: 'Error',
        description: 'Failed to load messages',
        variant: 'destructive'
      })
    } finally {
      setMessagesLoading(false)
    }
  }

  const sendMessage = async () => {
    if (!selectedConversation || !selectedAccount || !newMessage.trim()) return

    setSending(true)
    try {
      const result = await whatsappService.sendMessage({
        account_id: selectedAccount,
        chat_id: selectedConversation.id,
        text: newMessage.trim()
      })

      if (result.success) {
        setNewMessage('')
        // Reload messages to show the sent message
        await loadMessages(selectedConversation)
        toast({
          title: 'Success',
          description: 'Message sent'
        })
      } else {
        throw new Error(result.error || 'Failed to send message')
      }
    } catch (error: any) {
      console.error('Error sending message:', error)
      toast({
        title: 'Error',
        description: error.message || 'Failed to send message',
        variant: 'destructive'
      })
    } finally {
      setSending(false)
    }
  }

  const handleLinkConversation = (conversation: WhatsAppConversation) => {
    setLinkingConversation(conversation)
    setLinkDialogOpen(true)
  }

  const handleStoreAndLink = async () => {
    if (!linkingConversation || !selectedAccount) return

    try {
      // This would typically open a contact selector dialog
      // For now, we'll just show a success message
      toast({
        title: 'Link to Contact',
        description: 'Contact selection UI coming soon',
      })
      setLinkDialogOpen(false)
    } catch (error) {
      console.error('Error linking conversation:', error)
      toast({
        title: 'Error',
        description: 'Failed to link conversation',
        variant: 'destructive'
      })
    }
  }

  // Filter conversations based on search and storage filter
  const filteredConversations = conversations.filter(conv => {
    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      const matchesSearch = 
        conv.name.toLowerCase().includes(query) ||
        conv.last_message.toLowerCase().includes(query) ||
        conv.participants.some(p => 
          p.name.toLowerCase().includes(query) ||
          p.phone.includes(query)
        )
      if (!matchesSearch) return false
    }

    // Storage filter
    if (showStorageFilter !== 'all') {
      if (showStorageFilter === 'stored' && !conv.stored) return false
      if (showStorageFilter === 'not_stored' && conv.stored) return false
      if (showStorageFilter === 'can_link' && !conv.can_link) return false
    }

    return true
  })

  const formatTime = (dateString: string | null) => {
    if (!dateString) return ''
    try {
      return formatDistanceToNow(new Date(dateString), { addSuffix: true })
    } catch {
      return ''
    }
  }

  const getConversationDisplay = (conversation: WhatsAppConversation) => {
    // For group chats, show the group name
    if (conversation.is_group) {
      return conversation.name || 'Group Chat'
    }
    
    // For 1-on-1 chats, show participant names
    if (conversation.participants && conversation.participants.length > 0) {
      // Filter out self
      const otherParticipants = conversation.participants.filter((p: any) => !p.is_self)
      
      if (otherParticipants.length > 0) {
        // Show other participant's name
        return otherParticipants.map((p: any) => p.name || p.phone || 'Unknown').join(', ')
      } else if (conversation.participants.length > 0) {
        // If only self, show first participant (fallback)
        return conversation.participants[0].name || conversation.name || 'WhatsApp Chat'
      }
    }
    
    // Fallback to conversation name
    return conversation.name || 'WhatsApp Chat'
  }

  const getStorageIcon = (conv: WhatsAppConversation) => {
    if (conv.stored) {
      return <Database className="w-3.5 h-3.5 text-green-500" />
    } else if (conv.should_store) {
      return <AlertCircle className="w-3.5 h-3.5 text-yellow-500" />
    } else {
      return <Cloud className="w-3.5 h-3.5 text-gray-400" />
    }
  }

  const getStorageTooltip = (conv: WhatsAppConversation) => {
    if (conv.stored) {
      return 'Stored locally'
    } else if (conv.should_store) {
      return `Should be stored (${conv.storage_reason})`
    } else if (conv.can_link) {
      return 'Can be linked to contact'
    } else {
      return 'Live data from WhatsApp'
    }
  }

  return (
    <div className={cn('h-full flex flex-col', className)}>
      {/* Header */}
      <div className="p-4 border-b bg-white dark:bg-gray-900">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold">WhatsApp Inbox (Live)</h2>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="gap-1">
              <Cloud className="w-3 h-3" />
              Live Mode
            </Badge>
            {selectedAccount ? (
              <Button
                size="sm"
                variant="outline"
                onClick={() => loadConversations(true)}
                disabled={loading}
              >
                <RefreshCw className={cn('w-4 h-4', loading && 'animate-spin')} />
              </Button>
            ) : null}
          </div>
        </div>

        {/* Filters */}
        <div className="flex gap-2">
          {accounts.length > 0 ? (
            <Select value={selectedAccount} onValueChange={setSelectedAccount}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Select account" />
              </SelectTrigger>
              <SelectContent>
                {accounts.map(account => (
                  <SelectItem key={account.id || account.account_id} value={account.id || account.account_id}>
                    {account.name || account.phone}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : null}

          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <Input
              placeholder="Search conversations..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>

          <Select value={filterType} onValueChange={(v: any) => setFilterType(v)}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Chats</SelectItem>
              <SelectItem value="individual">Individual</SelectItem>
              <SelectItem value="group">Groups</SelectItem>
            </SelectContent>
          </Select>

          <Select value={showStorageFilter} onValueChange={(v: any) => setShowStorageFilter(v)}>
            <SelectTrigger className="w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="stored">Stored</SelectItem>
              <SelectItem value="not_stored">Not Stored</SelectItem>
              <SelectItem value="can_link">Can Link</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Conversations List */}
        <div className="w-96 border-r flex flex-col">
          <ScrollArea className="flex-1">
            <div className="p-2 space-y-1">
              {filteredConversations.map((conversation) => (
                <div
                  key={conversation.id}
                  onClick={() => loadMessages(conversation)}
                  className={cn(
                    'p-3 rounded-lg cursor-pointer transition-colors',
                    'hover:bg-gray-100 dark:hover:bg-gray-800',
                    selectedConversation?.id === conversation.id && 
                    'bg-gray-100 dark:bg-gray-800'
                  )}
                >
                  <div className="flex items-start gap-3">
                    <SafeAvatar
                      name={conversation.name}
                      size="md"
                      className="flex-shrink-0"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                          <h3 className="font-semibold text-sm truncate" title={`${conversation.participant_count || 0} participant(s)`}>
                            {getConversationDisplay(conversation)}
                          </h3>
                          {conversation.is_group ? (
                            <Users className="w-3.5 h-3.5 text-gray-400" />
                          ) : null}
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <div className="inline-flex">
                                  {getStorageIcon(conversation)}
                                </div>
                              </TooltipTrigger>
                              <TooltipContent>
                                {getStorageTooltip(conversation)}
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        </div>
                        <span className="text-xs text-gray-500">
                          {formatTime(conversation.last_message_at)}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 truncate">
                        {conversation.last_message}
                      </p>
                      <div className="flex items-center justify-between mt-1">
                        <div className="flex items-center gap-2">
                          {conversation.unread_count > 0 ? (
                            <Badge variant="destructive" className="text-xs px-1.5 h-5">
                              {conversation.unread_count}
                            </Badge>
                          ) : null}
                          {conversation.linked_records?.contacts && conversation.linked_records.contacts.length > 0 ? (
                            <Badge variant="outline" className="text-xs px-1.5 h-5">
                              {conversation.linked_records.contacts.length} contact{conversation.linked_records.contacts.length > 1 ? 's' : ''}
                            </Badge>
                          ) : null}
                        </div>
                        {conversation.can_link ? (
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-6 px-2 text-xs"
                            onClick={(e) => {
                              e.stopPropagation()
                              handleLinkConversation(conversation)
                            }}
                          >
                            <Link2 className="w-3 h-3 mr-1" />
                            Link
                          </Button>
                        ) : null}
                      </div>
                    </div>
                  </div>
                </div>
              ))}

              {hasMore ? (
                <Button
                  variant="ghost"
                  className="w-full"
                  onClick={() => loadConversations(false)}
                  disabled={loading}
                >
                  Load More
                </Button>
              ) : null}
            </div>
          </ScrollArea>
        </div>

        {/* Messages Area */}
        <div className="flex-1 flex flex-col">
          {selectedConversation ? (
            <>
              {/* Chat Header */}
              <div className="p-4 border-b bg-white dark:bg-gray-900">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <SafeAvatar
                      name={getConversationDisplay(selectedConversation)}
                      size="sm"
                    />
                    <div>
                      <h3 className="font-semibold">{getConversationDisplay(selectedConversation)}</h3>
                      <div className="flex items-center gap-2 text-sm text-gray-500">
                        {selectedConversation.is_group ? (
                          <span>{selectedConversation.participant_count} participants</span>
                        ) : null}
                        {selectedConversation.stored ? (
                          <Badge variant="outline" className="text-xs">Stored</Badge>
                        ) : null}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {selectedConversation.can_link ? (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleLinkConversation(selectedConversation)}
                      >
                        <Link2 className="w-4 h-4 mr-2" />
                        Link to Contact
                      </Button>
                    ) : null}
                  </div>
                </div>
              </div>

              {/* Messages */}
              <ScrollArea className="flex-1 p-4">
                {messagesLoading ? (
                  <div className="flex items-center justify-center h-32">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {messages.map((message) => (
                      <div
                        key={message.id}
                        className={cn(
                          'flex',
                          message.direction === 'outbound' ? 'justify-end' : 'justify-start'
                        )}
                      >
                        <div
                          className={cn(
                            'max-w-[70%] rounded-lg px-4 py-2',
                            message.direction === 'outbound'
                              ? 'bg-primary text-primary-foreground'
                              : 'bg-gray-100 dark:bg-gray-800'
                          )}
                        >
                          {message.direction === 'inbound' ? (
                            <div className="font-semibold text-sm mb-1">
                              {message.from_attendee?.name || message.from_attendee?.phone_number}
                            </div>
                          ) : null}
                          <p className="text-sm">{message.text}</p>
                          <span className="text-xs opacity-70 mt-1 block">
                            {formatTime(message.sent_at)}
                          </span>
                        </div>
                      </div>
                    ))}
                    <div ref={messagesEndRef} />
                  </div>
                )}
              </ScrollArea>

              {/* Message Input */}
              <div className="p-4 border-t bg-white dark:bg-gray-900">
                <div className="flex gap-2">
                  <Textarea
                    placeholder="Type a message..."
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault()
                        sendMessage()
                      }
                    }}
                    className="resize-none"
                    rows={1}
                  />
                  <Button
                    onClick={sendMessage}
                    disabled={sending || !newMessage.trim()}
                  >
                    <Send className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-gray-500">
              Select a conversation to start messaging
            </div>
          )}
        </div>
      </div>

      {/* Link Dialog */}
      <Dialog open={linkDialogOpen} onOpenChange={setLinkDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Link Conversation to Contact</DialogTitle>
            <DialogDescription>
              This conversation will be stored locally and linked to a CRM contact.
              You can then track all interactions with this contact.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            {linkingConversation ? (
              <div className="space-y-2">
                <p className="text-sm">
                  <strong>Conversation:</strong> {linkingConversation.name}
                </p>
                <p className="text-sm">
                  <strong>Messages:</strong> {linkingConversation.message_count}
                </p>
                <p className="text-sm">
                  <strong>Type:</strong> {linkingConversation.is_group ? 'Group' : 'Individual'}
                </p>
              </div>
            ) : null}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setLinkDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleStoreAndLink}>
              Select Contact & Link
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}