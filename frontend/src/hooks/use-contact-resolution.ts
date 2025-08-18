'use client'

import { useState, useEffect } from 'react'
import { communicationsApi } from '@/lib/api'
import { useToast } from '@/hooks/use-toast'

interface ContactRecord {
  id: string
  title: string
  pipeline_id: string
  pipeline_name: string
  data: Record<string, any>
}

interface UnmatchedMessage {
  id: string
  contact_email: string
  content: string
  created_at: string
  unmatched_contact_data?: {
    email?: string
    phone?: string
    name?: string
    [key: string]: any
  }
  needs_manual_resolution?: boolean
  domain_validated?: boolean
  needs_domain_review?: boolean
  channel_name?: string
  conversation?: {
    id: string
    subject?: string
  }
}

interface DomainWarningMessage extends UnmatchedMessage {
  contact_record?: ContactRecord
  relationship_context?: {
    domain_validated: boolean
    validation_status: string
    message_domain?: string
    pipeline_context: Array<{
      pipeline_name: string
      pipeline_id: string
      relationship_type: string
      record_title: string
      record_id: string
    }>
  }
}

export function useContactResolution() {
  const [unmatchedMessages, setUnmatchedMessages] = useState<UnmatchedMessage[]>([])
  const [domainWarnings, setDomainWarnings] = useState<DomainWarningMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [unmatchedCount, setUnmatchedCount] = useState(0)
  const [warningsCount, setWarningsCount] = useState(0)
  
  const { toast } = useToast()

  // Load unmatched contacts
  const loadUnmatchedContacts = async () => {
    try {
      setLoading(true)
      const response = await communicationsApi.getUnmatchedContacts()
      const messages = response.data || []
      setUnmatchedMessages(messages)
      setUnmatchedCount(messages.length)
    } catch (error: any) {
      console.error('Error loading unmatched contacts:', error)
      toast({
        title: "Failed to load unmatched contacts",
        description: error.response?.data?.error || "An error occurred",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  // Load domain validation warnings
  const loadDomainWarnings = async () => {
    try {
      setLoading(true)
      const response = await communicationsApi.getDomainValidationWarnings()
      const warnings = response.data || []
      setDomainWarnings(warnings)
      setWarningsCount(warnings.length)
    } catch (error: any) {
      console.error('Error loading domain warnings:', error)
      toast({
        title: "Failed to load domain warnings",
        description: error.response?.data?.error || "An error occurred",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  // Connect contact to message
  const connectContact = async (
    messageId: string, 
    contactId: string, 
    overrideReason?: string
  ): Promise<{ success: boolean; domainValidated: boolean }> => {
    try {
      const response = await communicationsApi.connectContact(messageId, {
        contact_id: contactId,
        override_reason: overrideReason
      })

      // Remove from unmatched list if successful
      setUnmatchedMessages(prev => prev.filter(msg => msg.id !== messageId))
      setDomainWarnings(prev => prev.filter(msg => msg.id !== messageId))
      setUnmatchedCount(prev => Math.max(0, prev - 1))
      setWarningsCount(prev => Math.max(0, prev - 1))

      toast({
        title: "Contact connected",
        description: "Message successfully connected to contact",
      })

      return {
        success: true,
        domainValidated: response.data.domain_validated
      }
    } catch (error: any) {
      console.error('Error connecting contact:', error)
      toast({
        title: "Connection failed",
        description: error.response?.data?.error || "Failed to connect contact",
        variant: "destructive",
      })
      return { success: false, domainValidated: false }
    }
  }

  // Create new contact from message
  const createContact = async (
    messageId: string,
    pipelineId: string,
    contactData: Record<string, any>
  ): Promise<{ success: boolean; contactId?: string }> => {
    try {
      const response = await communicationsApi.createContact(messageId, {
        pipeline_id: pipelineId,
        contact_data: contactData
      })

      // Remove from unmatched list if successful
      setUnmatchedMessages(prev => prev.filter(msg => msg.id !== messageId))
      setUnmatchedCount(prev => Math.max(0, prev - 1))

      toast({
        title: "Contact created",
        description: "New contact created and connected to message",
      })

      return {
        success: true,
        contactId: response.data.contact_id
      }
    } catch (error: any) {
      console.error('Error creating contact:', error)
      toast({
        title: "Creation failed",
        description: error.response?.data?.error || "Failed to create contact",
        variant: "destructive",
      })
      return { success: false }
    }
  }

  // Refresh all data
  const refresh = async () => {
    await Promise.all([
      loadUnmatchedContacts(),
      loadDomainWarnings()
    ])
  }

  // Initial load
  useEffect(() => {
    refresh()
  }, [])

  return {
    // Data
    unmatchedMessages,
    domainWarnings,
    unmatchedCount,
    warningsCount,
    loading,
    
    // Actions
    connectContact,
    createContact,
    refresh,
    loadUnmatchedContacts,
    loadDomainWarnings
  }
}

// Hook for getting contact resolution status for a specific message
export function useMessageContactStatus(message: any) {
  const getResolutionStatus = () => {
    if (!message) return { status: 'none', needsAction: false }

    // Has matched contact
    if (message.contact_record || message.contact_info) {
      // Check domain validation
      if (message.needs_domain_review || !message.domain_validated) {
        return {
          status: 'domain-warning',
          needsAction: true,
          contactRecord: message.contact_record || message.contact_info,
          domainValidated: message.domain_validated,
          relationshipContext: message.relationship_context
        }
      }
      
      return {
        status: 'matched',
        needsAction: false,
        contactRecord: message.contact_record || message.contact_info,
        domainValidated: true
      }
    }

    // Needs manual resolution
    if (message.needs_manual_resolution) {
      return {
        status: 'unmatched',
        needsAction: true,
        unmatchedData: message.unmatched_contact_data
      }
    }

    return { status: 'none', needsAction: false }
  }

  return getResolutionStatus()
}