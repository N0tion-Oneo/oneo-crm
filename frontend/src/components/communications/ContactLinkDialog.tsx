import React, { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Search, UserPlus, Link, Loader2, Check } from 'lucide-react'
import { api } from '@/lib/api'
import { emailService } from '@/services/emailService'

interface ContactLinkDialogProps {
  open: boolean
  onClose: () => void
  threadId: string
  threadParticipants: Array<{
    email: string
    name?: string
  }>
  onSuccess?: () => void
}

interface Pipeline {
  id: string
  name: string
  record_label: string
}

interface Contact {
  id: string
  name: string
  email: string
  pipeline_name: string
}

export function ContactLinkDialog({ 
  open, 
  onClose, 
  threadId, 
  threadParticipants,
  onSuccess 
}: ContactLinkDialogProps) {
  const [mode, setMode] = useState<'search' | 'create'>('search')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  
  // Search mode state
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<Contact[]>([])
  const [selectedContact, setSelectedContact] = useState<string | null>(null)
  const [searching, setSearching] = useState(false)
  
  // Create mode state
  const [pipelines, setPipelines] = useState<Pipeline[]>([])
  const [selectedPipeline, setSelectedPipeline] = useState<string>('')
  const [newContactEmail, setNewContactEmail] = useState('')
  const [newContactName, setNewContactName] = useState('')
  
  // Load pipelines when dialog opens
  useEffect(() => {
    if (open) {
      loadPipelines()
      // Pre-populate email from first participant
      if (threadParticipants.length > 0) {
        setNewContactEmail(threadParticipants[0].email)
        setNewContactName(threadParticipants[0].name || '')
      }
    } else {
      // Reset state when dialog closes
      setMode('search')
      setSearchQuery('')
      setSearchResults([])
      setSelectedContact(null)
      setSelectedPipeline('')
      setError(null)
      setSuccess(false)
    }
  }, [open, threadParticipants])
  
  // Load pipelines for create mode
  const loadPipelines = async () => {
    try {
      const response = await api.get('/api/v1/pipelines/')
      if (response.data.results) {
        setPipelines(response.data.results)
        // Select first pipeline by default
        if (response.data.results.length > 0) {
          setSelectedPipeline(response.data.results[0].id)
        }
      }
    } catch (error) {
      console.error('Error loading pipelines:', error)
    }
  }
  
  // Search for contacts
  const searchContacts = async () => {
    if (!searchQuery.trim()) return
    
    setSearching(true)
    setError(null)
    
    try {
      // Search across all pipelines
      const response = await api.get('/api/v1/search/', {
        params: {
          q: searchQuery,
          limit: 10
        }
      })
      
      if (response.data.results) {
        // Format results for display
        const contacts = response.data.results.map((result: any) => ({
          id: result.id,
          name: result.data.name || result.data.full_name || result.data.first_name || 'Unknown',
          email: result.data.email || 'No email',
          pipeline_name: result.pipeline_name
        }))
        setSearchResults(contacts)
      } else {
        setSearchResults([])
      }
    } catch (error) {
      console.error('Error searching contacts:', error)
      setError('Failed to search contacts')
    } finally {
      setSearching(false)
    }
  }
  
  // Link thread to selected contact
  const handleLinkContact = async () => {
    if (!selectedContact) {
      setError('Please select a contact')
      return
    }
    
    setLoading(true)
    setError(null)
    
    try {
      const result = await emailService.linkThreadToContact(threadId, selectedContact)
      
      if (result.success) {
        setSuccess(true)
        
        // Check if we need to sync history
        if (result.error?.includes('not found in local storage')) {
          // Thread not stored yet, trigger sync
          const syncResult = await emailService.syncThreadHistory(threadId)
          if (!syncResult.success) {
            console.error('Failed to sync thread history:', syncResult.error)
          }
        }
        
        // Close dialog after a short delay
        setTimeout(() => {
          onSuccess?.()
          onClose()
        }, 1500)
      } else {
        setError(result.error || 'Failed to link contact')
      }
    } catch (error) {
      setError('Failed to link contact to thread')
    } finally {
      setLoading(false)
    }
  }
  
  // Create new contact and link
  const handleCreateContact = async () => {
    if (!newContactEmail || !selectedPipeline) {
      setError('Email and pipeline are required')
      return
    }
    
    setLoading(true)
    setError(null)
    
    try {
      const result = await emailService.createContactFromThread(threadId, {
        email: newContactEmail,
        name: newContactName,
        pipeline_id: selectedPipeline
      })
      
      if (result.success) {
        setSuccess(true)
        
        // Trigger history sync for the new contact
        const syncResult = await emailService.syncThreadHistory(threadId)
        if (!syncResult.success) {
          console.error('Failed to sync thread history:', syncResult.error)
        }
        
        // Close dialog after a short delay
        setTimeout(() => {
          onSuccess?.()
          onClose()
        }, 1500)
      } else {
        setError(result.error || 'Failed to create contact')
      }
    } catch (error) {
      setError('Failed to create contact')
    } finally {
      setLoading(false)
    }
  }
  
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Link Email Thread to Contact</DialogTitle>
        </DialogHeader>
        
        {success ? (
          <div className="flex flex-col items-center py-8">
            <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center mb-4">
              <Check className="w-6 h-6 text-green-600" />
            </div>
            <p className="text-green-600 font-medium">
              {mode === 'search' ? 'Contact linked successfully!' : 'Contact created and linked!'}
            </p>
          </div>
        ) : (
          <>
            {/* Mode selector */}
            <div className="flex gap-2 mb-4">
              <Button
                variant={mode === 'search' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setMode('search')}
                className="flex-1"
              >
                <Search className="w-4 h-4 mr-2" />
                Search Existing
              </Button>
              <Button
                variant={mode === 'create' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setMode('create')}
                className="flex-1"
              >
                <UserPlus className="w-4 h-4 mr-2" />
                Create New
              </Button>
            </div>
            
            {/* Search mode */}
            {mode === 'search' && (
              <div className="space-y-4">
                <div>
                  <Label>Search for Contact</Label>
                  <div className="flex gap-2 mt-1">
                    <Input
                      placeholder="Name, email, or ID"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && searchContacts()}
                    />
                    <Button
                      onClick={searchContacts}
                      disabled={searching || !searchQuery.trim()}
                    >
                      {searching ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Search className="w-4 h-4" />
                      )}
                    </Button>
                  </div>
                </div>
                
                {/* Search results */}
                {searchResults.length > 0 && (
                  <div>
                    <Label>Select Contact</Label>
                    <div className="mt-1 space-y-2 max-h-60 overflow-y-auto">
                      {searchResults.map((contact) => (
                        <div
                          key={contact.id}
                          className={`p-3 border rounded-lg cursor-pointer hover:bg-gray-50 ${
                            selectedContact === contact.id ? 'border-blue-500 bg-blue-50' : ''
                          }`}
                          onClick={() => setSelectedContact(contact.id)}
                        >
                          <div className="font-medium">{contact.name}</div>
                          <div className="text-sm text-gray-500">{contact.email}</div>
                          <div className="text-xs text-gray-400">{contact.pipeline_name}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
            
            {/* Create mode */}
            {mode === 'create' && (
              <div className="space-y-4">
                <div>
                  <Label>Email</Label>
                  <Select
                    value={newContactEmail}
                    onValueChange={setNewContactEmail}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select email" />
                    </SelectTrigger>
                    <SelectContent>
                      {threadParticipants.map((participant) => (
                        <SelectItem key={participant.email} value={participant.email}>
                          {participant.email}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                
                <div>
                  <Label>Name (optional)</Label>
                  <Input
                    value={newContactName}
                    onChange={(e) => setNewContactName(e.target.value)}
                    placeholder="Contact name"
                  />
                </div>
                
                <div>
                  <Label>Pipeline</Label>
                  <Select
                    value={selectedPipeline}
                    onValueChange={setSelectedPipeline}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select pipeline" />
                    </SelectTrigger>
                    <SelectContent>
                      {pipelines.map((pipeline) => (
                        <SelectItem key={pipeline.id} value={pipeline.id}>
                          {pipeline.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            )}
            
            {/* Error message */}
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            
            {/* Actions */}
            <div className="flex justify-end gap-2 mt-4">
              <Button variant="outline" onClick={onClose} disabled={loading}>
                Cancel
              </Button>
              <Button
                onClick={mode === 'search' ? handleLinkContact : handleCreateContact}
                disabled={
                  loading ||
                  (mode === 'search' && !selectedContact) ||
                  (mode === 'create' && (!newContactEmail || !selectedPipeline))
                }
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <Link className="w-4 h-4 mr-2" />
                    {mode === 'search' ? 'Link Contact' : 'Create & Link'}
                  </>
                )}
              </Button>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}