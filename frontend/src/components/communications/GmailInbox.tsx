'use client'

import React, { useState, useEffect } from 'react'
import { Mail, Search, Filter, Archive, Reply, Forward, Star, StarOff, MoreVertical, Paperclip } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { useToast } from '@/hooks/use-toast'
import { MessageContent } from '@/components/MessageContent'
import { formatDistanceToNow } from 'date-fns'

// Based on Unipile Email API: /api/v1/emails
interface GmailMessage {
  id: string
  subject: string
  from: {
    name?: string
    address: string
  }
  to: Array<{
    name?: string
    address: string
  }>
  cc?: Array<{
    name?: string
    address: string
  }>
  bcc?: Array<{
    name?: string
    address: string
  }>
  body: {
    text?: string
    html?: string
  }
  headers: Record<string, string>
  date: string
  folder_id: string
  folder_name: string
  is_read: boolean
  is_starred: boolean
  attachments?: Array<{
    id: string
    filename: string
    size: number
    content_type: string
    // Accessible via /api/v1/emails/{email_id}/attachments/{attachment_id}
  }>
  account_id: string
  provider: 'gmail' | 'outlook' | 'yahoo'
}

// Unipile groups emails by conversation/thread
interface GmailThread {
  subject: string
  participants: Array<{
    name?: string
    address: string
  }>
  messages: GmailMessage[]
  unread_count: number
  latest_message_date: string
  folder_name: string
}

// Available email folders via /api/v1/emails/folders
interface EmailFolder {
  id: string
  name: string
  type: 'inbox' | 'sent' | 'drafts' | 'trash' | 'spam' | 'custom'
  unread_count: number
  total_count: number
}

interface GmailInboxProps {
  className?: string
}

export default function GmailInbox({ className }: GmailInboxProps) {
  const [threads, setThreads] = useState<GmailThread[]>([])
  const [selectedThread, setSelectedThread] = useState<GmailThread | null>(null)
  const [folders, setFolders] = useState<EmailFolder[]>([])
  const [selectedFolder, setSelectedFolder] = useState<string>('inbox')
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterStatus, setFilterStatus] = useState<'all' | 'unread' | 'starred'>('all')
  const [accountConnections, setAccountConnections] = useState<Array<{
    id: string
    provider: 'gmail' | 'outlook' | 'yahoo'
    email: string
    status: 'active' | 'error' | 'syncing'
  }>>([])
  const { toast } = useToast()

  // Mock data based on actual Unipile API structure
  useEffect(() => {
    // Simulate loading email folders first
    const mockFolders: EmailFolder[] = [
      { id: 'inbox', name: 'Inbox', type: 'inbox', unread_count: 3, total_count: 45 },
      { id: 'sent', name: 'Sent', type: 'sent', unread_count: 0, total_count: 12 },
      { id: 'drafts', name: 'Drafts', type: 'drafts', unread_count: 0, total_count: 2 },
      { id: 'spam', name: 'Spam', type: 'spam', unread_count: 1, total_count: 5 }
    ]
    
    const mockConnections = [
      { id: 'acc_1', provider: 'gmail' as const, email: 'you@gmail.com', status: 'active' as const },
      { id: 'acc_2', provider: 'outlook' as const, email: 'you@outlook.com', status: 'active' as const }
    ]
    
    // Simulate loading email threads
    const mockThreads: GmailThread[] = [
      {
        subject: 'Project Update - Q4 Planning',
        participants: [
          { name: 'John Smith', address: 'john.smith@company.com' }
        ],
        messages: [
          {
            id: 'msg_1',
            subject: 'Project Update - Q4 Planning',
            from: { name: 'John Smith', address: 'john.smith@company.com' },
            to: [{ name: 'You', address: 'you@gmail.com' }],
            body: {
              html: '<p>Hi there,</p><p>I wanted to share our <strong>Q4 planning updates</strong> with the team. Please review the attached documents and let me know your thoughts.</p><p>Best regards,<br>John</p>',
              text: 'Hi there,\n\nI wanted to share our Q4 planning updates with the team. Please review the attached documents and let me know your thoughts.\n\nBest regards,\nJohn'
            },
            headers: {
              'Message-ID': '<msg123@company.com>',
              'In-Reply-To': '',
              'References': ''
            },
            date: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
            folder_id: 'inbox',
            folder_name: 'Inbox',
            is_read: false,
            is_starred: false,
            attachments: [
              { id: 'att_1', filename: 'Q4_Plan.pdf', size: 245760, content_type: 'application/pdf' }
            ],
            account_id: 'acc_1',
            provider: 'gmail'
          }
        ],
        unread_count: 1,
        latest_message_date: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
        folder_name: 'Inbox'
      },
      {
        subject: 'Meeting Follow-up',
        participants: [
          { name: 'Sarah Johnson', address: 'sarah@example.com' }
        ],
        messages: [
          {
            id: 'msg_2',
            subject: 'Meeting Follow-up',
            from: { name: 'Sarah Johnson', address: 'sarah@example.com' },
            to: [{ name: 'You', address: 'you@gmail.com' }],
            body: {
              html: '<p>Thanks for the great meeting today!</p><p>As discussed, here are the action items:</p><ul><li>Review the proposal</li><li>Schedule follow-up call</li><li>Send contract details</li></ul>',
              text: 'Thanks for the great meeting today!\n\nAs discussed, here are the action items:\n- Review the proposal\n- Schedule follow-up call\n- Send contract details'
            },
            headers: {
              'Message-ID': '<msg456@example.com>',
              'In-Reply-To': '',
              'References': ''
            },
            date: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
            folder_id: 'inbox',
            folder_name: 'Inbox',
            is_read: true,
            is_starred: true,
            account_id: 'acc_1',
            provider: 'gmail'
          }
        ],
        unread_count: 0,
        latest_message_date: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
        folder_name: 'Inbox'
      }
    ]

    setTimeout(() => {
      setFolders(mockFolders)
      setAccountConnections(mockConnections)
      setThreads(mockThreads)
      setLoading(false)
    }, 1000)
  }, [])

  const filteredThreads = threads.filter(thread => {
    // Filter by folder
    if (selectedFolder !== 'all' && thread.folder_name.toLowerCase() !== selectedFolder) {
      return false
    }
    
    // Apply search filter
    if (searchQuery && !thread.subject.toLowerCase().includes(searchQuery.toLowerCase()) &&
        !thread.participants.some(p => p.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
                                     p.address.toLowerCase().includes(searchQuery.toLowerCase()))) {
      return false
    }

    // Apply status filter
    switch (filterStatus) {
      case 'unread':
        return thread.unread_count > 0
      case 'starred':
        return thread.messages.some(msg => msg.is_starred)
      default:
        return true
    }
  })

  const handleThreadSelect = (thread: GmailThread) => {
    setSelectedThread(thread)
    
    // Mark as read if needed - simulate Unipile PUT /api/v1/emails/{email_id}
    if (thread.unread_count > 0) {
      setThreads(prev => prev.map(t =>
        t.subject === thread.subject && t.latest_message_date === thread.latest_message_date
          ? { ...t, unread_count: 0, messages: t.messages.map(msg => ({ ...msg, is_read: true })) }
          : t
      ))
      
      // TODO: Call actual Unipile API to mark emails as read
      // PUT /api/v1/emails/{email_id} with { "read": true }
    }
  }

  const toggleStar = (thread: GmailThread, event: React.MouseEvent) => {
    event.stopPropagation()
    setThreads(prev => prev.map(t =>
      t.subject === thread.subject && t.latest_message_date === thread.latest_message_date
        ? { ...t, messages: t.messages.map(msg => ({ ...msg, is_starred: !msg.is_starred })) }
        : t
    ))
    
    // TODO: Call actual Unipile API to star/unstar emails
    // PUT /api/v1/emails/{email_id} with { "starred": true/false }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-500"></div>
        <p className="ml-4 text-gray-600">Loading Gmail inbox...</p>
      </div>
    )
  }

  return (
    <div className={`h-full flex flex-col ${className}`}>
      {/* Filters */}
      <div className="p-4 border-b bg-white dark:bg-gray-900">
        <div className="flex items-center space-x-4">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <Input
                placeholder="Search Gmail conversations..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>
          
          <Select value={selectedFolder} onValueChange={setSelectedFolder}>
            <SelectTrigger className="w-32">
              <SelectValue placeholder="Folder" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Folders</SelectItem>
              {folders.map(folder => (
                <SelectItem key={folder.id} value={folder.name.toLowerCase()}>
                  {folder.name} ({folder.unread_count})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          
          <Select value={filterStatus} onValueChange={(value: any) => setFilterStatus(value)}>
            <SelectTrigger className="w-32">
              <SelectValue placeholder="Filter" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="unread">Unread</SelectItem>
              <SelectItem value="starred">Starred</SelectItem>
            </SelectContent>
          </Select>

          <div className="flex items-center gap-2">
            {accountConnections.map(conn => (
              <Badge key={conn.id} variant="outline" className="bg-red-50 text-red-700">
                <Mail className="w-3 h-3 mr-1" />
                {conn.email} ({conn.provider})
              </Badge>
            ))}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 grid grid-cols-12 gap-0 overflow-hidden">
        {/* Conversation List */}
        <div className="col-span-4 border-r bg-gray-50 dark:bg-gray-900/50">
          <ScrollArea className="h-full">
            {filteredThreads.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <Mail className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                <p>No emails found in {selectedFolder}</p>
              </div>
            ) : (
              <div className="space-y-1 p-2">
                {filteredThreads.map((thread, index) => (
                  <Card
                    key={`${thread.subject}-${index}`}
                    className={`cursor-pointer transition-colors hover:bg-white dark:hover:bg-gray-800 ${
                      selectedThread?.subject === thread.subject && selectedThread?.latest_message_date === thread.latest_message_date ? 'ring-2 ring-red-500 bg-white dark:bg-gray-800' : ''
                    }`}
                    onClick={() => handleThreadSelect(thread)}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex items-start space-x-3 flex-1 min-w-0">
                          <Avatar className="w-8 h-8 flex-shrink-0">
                            <AvatarImage src="" />
                            <AvatarFallback className="bg-red-100 text-red-700 text-xs">
                              {thread.participants[0]?.name?.charAt(0) || thread.participants[0]?.address?.charAt(0)?.toUpperCase() || 'E'}
                            </AvatarFallback>
                          </Avatar>
                          
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between mb-1">
                              <h3 className={`text-sm font-medium truncate ${
                                thread.unread_count > 0 ? 'font-bold' : ''
                              }`}>
                                {thread.participants[0]?.name || thread.participants[0]?.address || 'Unknown'}
                              </h3>
                              <div className="flex items-center gap-1 flex-shrink-0 ml-2">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-6 w-6 p-0"
                                  onClick={(e) => toggleStar(thread, e)}
                                >
                                  {thread.messages.some(msg => msg.is_starred) ? (
                                    <Star className="w-3 h-3 text-yellow-400 fill-current" />
                                  ) : (
                                    <StarOff className="w-3 h-3 text-gray-400" />
                                  )}
                                </Button>
                                <span className="text-xs text-gray-500">
                                  {formatDistanceToNow(new Date(thread.latest_message_date))}
                                </span>
                              </div>
                            </div>
                            
                            <p className={`text-sm font-medium mb-1 truncate ${
                              thread.unread_count > 0 ? 'font-bold' : ''
                            }`}>
                              {thread.subject}
                            </p>
                            
                            <p className="text-xs text-gray-500 truncate">
                              {thread.messages[0]?.body?.text?.slice(0, 80) || thread.messages[0]?.body?.html?.replace(/<[^>]*>/g, '')?.slice(0, 80) || 'No preview'}
                            </p>

                            <div className="flex items-center justify-between mt-1">
                              <span className="text-xs text-gray-400">
                                {thread.folder_name} • {thread.messages.length} message{thread.messages.length !== 1 ? 's' : ''}
                              </span>
                              {thread.unread_count > 0 && (
                                <Badge variant="destructive" className="text-xs">
                                  {thread.unread_count} new
                                </Badge>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </ScrollArea>
        </div>

        {/* Email View */}
        <div className="col-span-8 bg-white dark:bg-gray-900">
          {selectedThread ? (
            <div className="h-full flex flex-col">
              {/* Email Header */}
              <div className="p-4 border-b">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <Avatar className="w-10 h-10">
                      <AvatarImage src="" />
                      <AvatarFallback className="bg-red-100 text-red-700">
                        {selectedThread.participants[0]?.name?.charAt(0) || selectedThread.participants[0]?.address?.charAt(0)?.toUpperCase() || 'E'}
                      </AvatarFallback>
                    </Avatar>
                    <div>
                      <h2 className="text-lg font-bold">{selectedThread.subject}</h2>
                      <p className="text-sm text-gray-600">
                        Thread with {selectedThread.participants.length} participant{selectedThread.participants.length !== 1 ? 's' : ''} • {selectedThread.messages.length} message{selectedThread.messages.length !== 1 ? 's' : ''}
                      </p>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <Button variant="ghost" size="sm">
                      <Reply className="w-4 h-4" />
                    </Button>
                    <Button variant="ghost" size="sm">
                      <Forward className="w-4 h-4" />
                    </Button>
                    <Button variant="ghost" size="sm">
                      <Archive className="w-4 h-4" />
                    </Button>
                    <Button variant="ghost" size="sm">
                      <MoreVertical className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
                
                <div className="text-xs text-gray-500">
                  Latest: {new Date(selectedThread.latest_message_date).toLocaleString()}
                </div>
              </div>

              {/* Email Thread Content */}
              <ScrollArea className="flex-1 p-6">
                {selectedThread.messages.map((message, index) => (
                  <div key={message.id} className="mb-6">
                    {index > 0 && <Separator className="my-4" />}
                    
                    <div className="bg-white border rounded-lg p-4">
                      {/* Message Header with Unipile structure */}
                      <div className="border-b border-gray-100 pb-3 mb-4">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <Avatar className="w-6 h-6">
                              <AvatarFallback className="bg-red-100 text-red-700 text-xs">
                                {message.from.name?.charAt(0) || message.from.address.charAt(0).toUpperCase()}
                              </AvatarFallback>
                            </Avatar>
                            <span className="font-medium text-sm">
                              {message.from.name || message.from.address}
                            </span>
                            <Badge variant="outline" className="text-xs">
                              {message.provider}
                            </Badge>
                          </div>
                          <div className="text-right">
                            <div className="text-xs text-gray-500">
                              {new Date(message.date).toLocaleString()}
                            </div>
                            <div className="text-xs text-gray-400">
                              {message.folder_name}
                            </div>
                          </div>
                        </div>
                        
                        <div className="text-sm text-gray-600">
                          <div className="mb-1">
                            <strong>From:</strong> {message.from.name ? `${message.from.name} <${message.from.address}>` : message.from.address}
                          </div>
                          <div className="mb-1">
                            <strong>To:</strong> {message.to.map(recipient => 
                              recipient.name ? `${recipient.name} <${recipient.address}>` : recipient.address
                            ).join(', ')}
                          </div>
                          {message.cc && message.cc.length > 0 && (
                            <div className="mb-1">
                              <strong>CC:</strong> {message.cc.map(recipient => 
                                recipient.name ? `${recipient.name} <${recipient.address}>` : recipient.address
                              ).join(', ')}
                            </div>
                          )}
                          <div>
                            <strong>Subject:</strong> {message.subject}
                          </div>
                        </div>
                      </div>

                      {/* Message Body */}
                      <div className="prose max-w-none">
                        {message.body.html ? (
                          <MessageContent
                            content={message.body.html}
                            isEmail={true}
                            className="text-gray-900"
                          />
                        ) : (
                          <div className="whitespace-pre-wrap text-gray-900">
                            {message.body.text}
                          </div>
                        )}
                      </div>

                      {/* Attachments - Unipile structure */}
                      {message.attachments && message.attachments.length > 0 && (
                        <div className="mt-4 pt-4 border-t">
                          <p className="text-sm font-medium mb-2">Attachments ({message.attachments.length}):</p>
                          <div className="space-y-2">
                            {message.attachments.map((attachment) => (
                              <div key={attachment.id} className="flex items-center gap-2 p-2 bg-gray-50 rounded">
                                <Paperclip className="w-4 h-4 text-gray-500" />
                                <div className="flex-1">
                                  <span className="text-sm font-medium">{attachment.filename}</span>
                                  <div className="text-xs text-gray-500">
                                    {attachment.content_type} • {(attachment.size / 1024).toFixed(1)}KB
                                  </div>
                                </div>
                                <Button 
                                  variant="ghost" 
                                  size="sm" 
                                  className="ml-auto"
                                  onClick={() => {
                                    // TODO: Implement Unipile attachment download
                                    // GET /api/v1/emails/{email_id}/attachments/{attachment_id}
                                    console.log('Download attachment:', attachment.id)
                                  }}
                                >
                                  Download
                                </Button>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </ScrollArea>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center">
              <div className="text-center text-gray-500">
                <Mail className="w-16 h-16 mx-auto mb-4 text-gray-300" />
                <h3 className="text-lg font-medium mb-2">Select an email thread to read</h3>
                <p>Choose an email thread from the left to view your messages</p>
                {folders.length > 0 && (
                  <div className="mt-4">
                    <p className="text-sm text-gray-400">Available folders:</p>
                    <div className="flex flex-wrap gap-2 justify-center mt-2">
                      {folders.map(folder => (
                        <Badge key={folder.id} variant="outline" className="text-xs">
                          {folder.name} ({folder.unread_count}/{folder.total_count})
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}