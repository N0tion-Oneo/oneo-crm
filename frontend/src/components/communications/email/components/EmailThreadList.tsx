import React, { useCallback } from 'react'
import { Mail, MailOpen, Star, StarOff, Trash, Link, Unlink, Paperclip, Building2, User, Users, Folder } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { EmailThread, EmailAccount } from '../utils/emailTypes'
import { formatRelativeDate, getParticipantDisplay } from '../utils/emailFormatters'
import { emailService } from '@/services/emailService'
import { useToast } from '@/hooks/use-toast'

interface EmailThreadListProps {
  threads: EmailThread[]
  selectedThread: EmailThread | null
  selectedAccount: EmailAccount | null
  onSelectThread: (thread: EmailThread) => void
  onThreadUpdate?: (threads: EmailThread[]) => void
  onLinkContact?: (thread: EmailThread) => void
  currentPage: number
  hasMorePages: boolean
  onPageChange: (page: number) => void
  loading?: boolean
}

export const EmailThreadList: React.FC<EmailThreadListProps> = ({
  threads,
  selectedThread,
  selectedAccount,
  onSelectThread,
  onThreadUpdate,
  onLinkContact,
  currentPage,
  hasMorePages,
  onPageChange,
  loading = false
}) => {
  const { toast } = useToast()

  const handleMarkAsRead = useCallback(async (thread: EmailThread, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!selectedAccount) return
    
    try {
      await emailService.markThreadAsRead(selectedAccount.account_id, thread.id)
      
      if (onThreadUpdate) {
        const updatedThreads = threads.map(t => 
          t.id === thread.id ? { ...t, unread_count: 0 } : t
        )
        onThreadUpdate(updatedThreads)
      }
      
      toast({
        title: 'Success',
        description: 'Thread marked as read',
      })
    } catch (error) {
      console.error('Failed to mark thread as read:', error)
      toast({
        title: 'Error',
        description: 'Failed to mark thread as read',
        variant: 'destructive'
      })
    }
  }, [selectedAccount, threads, onThreadUpdate, toast])

  const handleMarkAsUnread = useCallback(async (thread: EmailThread, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!selectedAccount) return
    
    try {
      await emailService.markThreadAsUnread(selectedAccount.account_id, thread.id)
      
      if (onThreadUpdate) {
        const updatedThreads = threads.map(t => 
          t.id === thread.id ? { ...t, unread_count: 1 } : t
        )
        onThreadUpdate(updatedThreads)
      }
      
      toast({
        title: 'Success',
        description: 'Thread marked as unread',
      })
    } catch (error) {
      console.error('Failed to mark thread as unread:', error)
      toast({
        title: 'Error',
        description: 'Failed to mark thread as unread',
        variant: 'destructive'
      })
    }
  }, [selectedAccount, threads, onThreadUpdate, toast])

  const handleLinkContact = useCallback((thread: EmailThread, e: React.MouseEvent) => {
    e.stopPropagation()
    if (onLinkContact) {
      onLinkContact(thread)
    }
  }, [onLinkContact])

  if (!selectedAccount) {
    return (
      <div className="p-8 text-center text-gray-500">
        <Mail className="w-12 h-12 mx-auto mb-4 text-gray-400" />
        <p>No email account connected</p>
        <p className="text-sm mt-2">Please connect an email account to view messages</p>
      </div>
    )
  }

  if (threads.length === 0 && !loading) {
    return (
      <div className="p-8 text-center text-gray-500">
        <Mail className="w-12 h-12 mx-auto mb-4 text-gray-400" />
        <p>No emails found</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto">
        <div className="space-y-1 p-2 pb-12">
          {threads.map((thread) => {
            const participant = getParticipantDisplay(thread)
            const isSelected = selectedThread?.id === thread.id
            
            return (
              <div
                key={thread.id}
                className={`
                  relative p-3 rounded-lg cursor-pointer transition-colors
                  ${isSelected ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-200' : 'hover:bg-gray-50 dark:hover:bg-gray-800'}
                  ${thread.unread_count > 0 ? 'font-semibold' : ''}
                `}
                onClick={() => onSelectThread(thread)}
              >
                <div className="flex items-start gap-3">
                  <Avatar className="w-8 h-8">
                    <AvatarFallback className={`text-xs ${thread.unread_count > 0 ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}>
                      {participant.initials}
                    </AvatarFallback>
                  </Avatar>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <span className={`truncate ${thread.unread_count > 0 ? 'font-semibold' : ''}`}>
                        {participant.name}
                      </span>
                      <span className="text-xs text-gray-500">
                        {formatRelativeDate(thread.last_message_at)}
                      </span>
                    </div>
                    
                    <div className="text-sm truncate mb-1">
                      {thread.subject || '(No subject)'}
                    </div>
                    
                    {/* Contact/Company Resolution Chips */}
                    <div className="flex flex-wrap items-center gap-1 mb-1">
                      {/* Show individual chip for each contact from linked_records */}
                      {thread.linked_records?.contacts?.map((contact, idx) => (
                        <div key={`contact-${idx}`} className="flex items-center gap-1 bg-green-50 dark:bg-green-900/30 px-2 py-0.5 rounded-full" 
                             title={`Contact: ${contact.title || contact.name}`}>
                          <User className="w-3 h-3 text-green-600 dark:text-green-400" />
                          <span className="text-xs text-green-600 dark:text-green-400 font-medium truncate max-w-[100px]">
                            {contact.title || contact.name || 'Contact'}
                          </span>
                        </div>
                      ))}
                      
                      {/* Show individual chip for each contact from participants (if not in linked_records) */}
                      {!thread.linked_records?.contacts?.length && thread.participants?.filter(p => p.has_contact).map((participant, idx) => {
                        const recordTitle = participant.contact_record_title || participant.contact_record_name || participant.name || 'Contact'
                        return (
                          <div key={`participant-contact-${idx}`} className="flex items-center gap-1 bg-green-50 dark:bg-green-900/30 px-2 py-0.5 rounded-full"
                               title={`Contact: ${recordTitle}`}>
                            <User className="w-3 h-3 text-green-600 dark:text-green-400" />
                            <span className="text-xs text-green-600 dark:text-green-400 font-medium truncate max-w-[100px]">
                              {recordTitle}
                            </span>
                          </div>
                        )
                      })}
                      
                      {/* Show contact pipeline chips */}
                      {(() => {
                        const contactPipelines = new Set<string>()
                        // Collect pipelines from participants
                        thread.participants?.forEach(p => {
                          if (p.has_contact && p.contact_pipeline) {
                            contactPipelines.add(p.contact_pipeline)
                          }
                        })
                        return Array.from(contactPipelines).map((pipeline, idx) => (
                          <div key={`contact-pipeline-${idx}`} className="flex items-center gap-1 bg-orange-50 dark:bg-orange-900/30 px-2 py-0.5 rounded-full"
                               title={`Pipeline: ${pipeline}`}>
                            <Folder className="w-3 h-3 text-orange-600 dark:text-orange-400" />
                            <span className="text-xs text-orange-600 dark:text-orange-400 font-medium truncate max-w-[100px]">
                              {pipeline}
                            </span>
                          </div>
                        ))
                      })()}
                      
                      {/* Show individual chip for each company from linked_records */}
                      {thread.linked_records?.companies?.map((company, idx) => (
                        <div key={`company-${idx}`} className="flex items-center gap-1 bg-blue-50 dark:bg-blue-900/30 px-2 py-0.5 rounded-full"
                             title={`Company: ${company.title || company.name || 'Unknown Company'}`}>
                          <Building2 className="w-3 h-3 text-blue-600 dark:text-blue-400" />
                          <span className="text-xs text-blue-600 dark:text-blue-400 font-medium truncate max-w-[100px]">
                            {company.title || company.name || 'Unknown'}
                          </span>
                        </div>
                      ))}
                      
                      {/* Show individual chip for each company from participants (if not in linked_records) */}
                      {!thread.linked_records?.companies?.length && thread.participants?.filter(p => p.has_secondary).map((participant, idx) => {
                        const companyTitle = participant.secondary_record_title || participant.secondary_record_name || 'Company'
                        return (
                          <div key={`participant-company-${idx}`} className="flex items-center gap-1 bg-blue-50 dark:bg-blue-900/30 px-2 py-0.5 rounded-full"
                               title={`Company: ${companyTitle}`}>
                            <Building2 className="w-3 h-3 text-blue-600 dark:text-blue-400" />
                            <span className="text-xs text-blue-600 dark:text-blue-400 font-medium truncate max-w-[100px]">
                              {companyTitle}
                            </span>
                          </div>
                        )
                      })}
                      
                      {/* Show company pipeline chips */}
                      {(() => {
                        const companyPipelines = new Set<string>()
                        // Collect pipelines from linked_records
                        thread.linked_records?.companies?.forEach(c => {
                          if (c.pipeline) {
                            companyPipelines.add(c.pipeline)
                          }
                        })
                        // Collect pipelines from participants
                        thread.participants?.forEach(p => {
                          if (p.has_secondary && p.secondary_pipeline) {
                            companyPipelines.add(p.secondary_pipeline)
                          }
                        })
                        return Array.from(companyPipelines).map((pipeline, idx) => (
                          <div key={`company-pipeline-${idx}`} className="flex items-center gap-1 bg-indigo-50 dark:bg-indigo-900/30 px-2 py-0.5 rounded-full"
                               title={`Pipeline: ${pipeline}`}>
                            <Folder className="w-3 h-3 text-indigo-600 dark:text-indigo-400" />
                            <span className="text-xs text-indigo-600 dark:text-indigo-400 font-medium truncate max-w-[100px]">
                              {pipeline}
                            </span>
                          </div>
                        ))
                      })()}
                      
                      {/* Show unlinked if no matches */}
                      {thread.participants && !thread.participants.some(p => p.has_contact || p.has_secondary) && 
                       !thread.linked_records?.contacts?.length && !thread.linked_records?.companies?.length && !thread.stored && (
                        <div className="flex items-center gap-1 bg-gray-50 dark:bg-gray-800 px-2 py-0.5 rounded-full">
                          <Unlink className="w-3 h-3 text-gray-400" />
                          <span className="text-xs text-gray-400">Not linked</span>
                        </div>
                      )}
                    </div>
                    
                    <div className="flex items-center gap-2 text-xs text-gray-500">
                      {thread.unread_count > 0 && (
                        <Badge variant="secondary" className="text-xs px-1 py-0">
                          {thread.unread_count} unread
                        </Badge>
                      )}
                      {thread.has_attachments && (
                        <Paperclip className="w-3 h-3" />
                      )}
                      {thread.message_count > 1 && (
                        <span>{thread.message_count} messages</span>
                      )}
                      
                      {/* Storage Status */}
                      {thread.stored && !thread.participants?.[0]?.has_contact && (
                        <Badge variant="outline" className="text-xs px-1 py-0">
                          Stored
                        </Badge>
                      )}
                      {thread.can_link && (
                        <Badge variant="secondary" className="text-xs px-1 py-0 bg-yellow-50 text-yellow-700">
                          Can Link
                        </Badge>
                      )}
                    </div>
                  </div>
                  
                  {/* Action buttons */}
                  <div className="flex items-center gap-1">
                    {thread.unread_count > 0 ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 w-6 p-0"
                        onClick={(e) => handleMarkAsRead(thread, e)}
                        title="Mark as read"
                      >
                        <MailOpen className="w-3.5 h-3.5" />
                      </Button>
                    ) : (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 w-6 p-0"
                        onClick={(e) => handleMarkAsUnread(thread, e)}
                        title="Mark as unread"
                      >
                        <Mail className="w-3.5 h-3.5" />
                      </Button>
                    )}
                    
                    {thread.can_link && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 w-6 p-0"
                        onClick={(e) => handleLinkContact(thread, e)}
                        title="Link to contact"
                      >
                        <Link className="w-3.5 h-3.5" />
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>
      
      {/* Pagination */}
      {(currentPage > 1 || hasMorePages) && (
        <div className="border-t bg-white dark:bg-gray-900 p-2">
          <div className="flex items-center justify-between">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onPageChange(currentPage - 1)}
              disabled={currentPage === 1 || loading}
            >
              Previous
            </Button>
            
            <span className="text-sm text-gray-500">
              Page {currentPage}
            </span>
            
            <Button
              variant="outline"
              size="sm"
              onClick={() => onPageChange(currentPage + 1)}
              disabled={!hasMorePages || loading}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}