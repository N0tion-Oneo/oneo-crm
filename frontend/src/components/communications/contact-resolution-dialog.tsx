'use client'

import { useState, useEffect, useCallback } from 'react'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { RecordDetailDrawer } from '@/components/pipelines/record-detail-drawer'
import { useToast } from '@/hooks/use-toast'
import { 
  User, 
  Plus, 
  Search, 
  AlertTriangle, 
  CheckCircle, 
  Mail, 
  Phone, 
  Building, 
  Link as LinkIcon,
  Shield,
  X,
  Info
} from 'lucide-react'
import { pipelinesApi, communicationsApi } from '@/lib/api'
import { FieldResolver } from '@/lib/field-system/field-registry'

interface ContactRecord {
  id: string
  title: string
  pipeline_id: string
  pipeline_name: string
  data: Record<string, any>
}

interface Message {
  id: string
  contact_email: string
  contact_record?: ContactRecord
  unmatched_contact_data?: {
    email?: string
    phone?: string
    name?: string
    [key: string]: any
  }
  needs_manual_resolution?: boolean
  domain_validated?: boolean
  needs_domain_review?: boolean
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

interface Pipeline {
  id: string
  name: string
  description?: string
  fields: Array<{
    id: string
    name: string
    field_type: string
    label: string
    is_required: boolean
  }>
}

interface ContactResolutionDialogProps {
  message: Message | null
  isOpen: boolean
  onClose: () => void
  onResolutionComplete: (messageId: string, contactRecord: ContactRecord) => void
}

export function ContactResolutionDialog({
  message,
  isOpen,
  onClose,
  onResolutionComplete
}: ContactResolutionDialogProps) {
  const [activeTab, setActiveTab] = useState<'view' | 'connect' | 'create'>('view')
  const [pipelines, setPipelines] = useState<Pipeline[]>([])
  const [searchResults, setSearchResults] = useState<ContactRecord[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [isSearching, setIsSearching] = useState(false)
  const [selectedPipeline, setSelectedPipeline] = useState<string>('')
  const [selectedContact, setSelectedContact] = useState<ContactRecord | null>(null)
  const [loading, setLoading] = useState(false)
  const [showRecordDrawer, setShowRecordDrawer] = useState(false)
  const [drawerMode, setDrawerMode] = useState<'view' | 'create'>('view')
  const [overrideReason, setOverrideReason] = useState('')
  
  const { toast } = useToast()

  // Debounced search function
  const debouncedSearchContacts = useCallback(
    debounce((query: string) => {
      searchContacts(query)
    }, 500),
    [pipelines] // Re-create debounced function when pipelines change
  )

  // Helper function for debouncing
  function debounce<T extends (...args: any[]) => any>(
    func: T,
    delay: number
  ): (...args: Parameters<T>) => void {
    let timeoutId: NodeJS.Timeout
    return (...args: Parameters<T>) => {
      clearTimeout(timeoutId)
      timeoutId = setTimeout(() => func(...args), delay)
    }
  }

  // Load pipelines on mount
  useEffect(() => {
    if (isOpen) {
      loadPipelines()
    }
  }, [isOpen])

  // Determine initial tab based on message state
  useEffect(() => {
    if (message) {
      if (message.contact_record) {
        setActiveTab('view')
      } else if (message.needs_manual_resolution) {
        setActiveTab('connect')
      }
    }
  }, [message])

  const loadPipelines = async () => {
    try {
      const response = await pipelinesApi.list()
      const pipelinesData = response.data.results || response.data || []
      
      // Load fields for each pipeline since list endpoint doesn't include them
      const pipelinesWithFields = await Promise.all(
        pipelinesData.map(async (pipeline: any) => {
          try {
            const fieldsResponse = await pipelinesApi.getFields(pipeline.id)
            const fields = fieldsResponse.data.results || fieldsResponse.data || []
            return {
              ...pipeline,
              fields: fields
            }
          } catch (fieldsError) {
            console.error(`Error loading fields for pipeline ${pipeline.id}:`, fieldsError)
            // Return pipeline with empty fields array if fields can't be loaded
            return {
              ...pipeline,
              fields: []
            }
          }
        })
      )
      
      console.log('Loaded pipelines with fields:', pipelinesWithFields.map(p => ({
        id: p.id,
        name: p.name,
        hasFields: !!p.fields,
        fieldsLength: p.fields?.length,
        fieldsType: typeof p.fields
      })))
      setPipelines(pipelinesWithFields)
    } catch (error) {
      console.error('Error loading pipelines:', error)
      toast({
        title: "Failed to load pipelines",
        description: "Unable to load available pipelines",
        variant: "destructive",
      })
    }
  }

  const searchContacts = async (query: string) => {
    if (!query.trim()) {
      setSearchResults([])
      setIsSearching(false)
      return
    }

    try {
      setIsSearching(true)
      setLoading(true)
      console.log('🔍 Searching contacts with query:', query)
      console.log('🔍 Available pipelines for search:', pipelines.map(p => ({ id: p.id, name: p.name })))
      
      // Search across all pipelines for contacts
      const promises = pipelines.map(pipeline => {
        console.log(`🔍 Searching pipeline ${pipeline.name} (${pipeline.id}) with params:`, { search: query, limit: 5 })
        return pipelinesApi.getRecords(pipeline.id, { search: query, limit: 5 })
      })
      
      const responses = await Promise.allSettled(promises)
      const allResults: ContactRecord[] = []
      
      console.log(`🔍 Received ${responses.length} responses from pipelines`)
      
      responses.forEach((response, index) => {
        if (response.status === 'fulfilled') {
          const records = response.value.data.results || response.value.data || []
          console.log(`🔍 Pipeline ${pipelines[index].name} returned ${records.length} records for query "${query}":`, records.map((r: any) => ({ id: r.id, title: r.title })))
          records.forEach((record: any) => {
            allResults.push({
              id: record.id,
              title: record.title,
              pipeline_id: pipelines[index].id,
              pipeline_name: pipelines[index].name,
              data: record.data
            })
          })
        } else {
          console.error(`🔍 Search failed for pipeline ${pipelines[index].name}:`, response.reason)
        }
      })
      
      console.log(`🔍 Total search results found: ${allResults.length}`)
      console.log(`🔍 Search results:`, allResults.map(r => ({ id: r.id, title: r.title, pipeline: r.pipeline_name })))
      setSearchResults(allResults)
    } catch (error) {
      console.error('Error searching contacts:', error)
      toast({
        title: "Search failed",
        description: "Unable to search for contacts",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
      setIsSearching(false)
    }
  }

  const handleConnectContact = async (contactRecord: ContactRecord) => {
    if (!message) return

    try {
      setLoading(true)
      const response = await communicationsApi.connectContact(message.id, {
        contact_id: contactRecord.id,
        override_reason: overrideReason
      })

      toast({
        title: "Contact connected",
        description: `Message connected to ${contactRecord.title}`,
      })

      onResolutionComplete(message.id, contactRecord)
      onClose()
    } catch (error: any) {
      console.error('Error connecting contact:', error)
      toast({
        title: "Connection failed",
        description: error.response?.data?.error || "Failed to connect contact",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const handleCreateContact = (pipelineId: string) => {
    const pipeline = pipelines.find(p => p.id === pipelineId)
    if (!pipeline) return

    setSelectedPipeline(pipelineId)
    setDrawerMode('create')
    setShowRecordDrawer(true)
  }

  const handleRecordSave = async (recordId: string, data: any) => {
    if (!message || drawerMode !== 'create') return

    try {
      // Connect the newly created contact to the message
      const contactRecord: ContactRecord = {
        id: recordId,
        title: data.title || data.name || 'New Contact',
        pipeline_id: selectedPipeline,
        pipeline_name: pipelines.find(p => p.id === selectedPipeline)?.name || 'Unknown',
        data
      }

      await handleConnectContact(contactRecord)
    } catch (error) {
      console.error('Error connecting new contact:', error)
    }
  }

  const handleViewContact = (contactRecord: ContactRecord) => {
    setSelectedContact(contactRecord)
    setDrawerMode('view')
    setShowRecordDrawer(true)
  }

  // Helper function to convert ContactRecord to RecordData format
  const convertContactToRecordData = (contact: ContactRecord) => {
    return {
      id: contact.id,
      data: contact.data,
      created_at: new Date().toISOString(), // Default values since we don't have them
      updated_at: new Date().toISOString()
    }
  }

  // Helper function to convert Pipeline to expected format
  const convertPipelineFormat = (pipeline: Pipeline) => {
    return {
      ...pipeline,
      description: pipeline.description || '', // Ensure description is always a string
      fields: pipeline.fields.map((field, index) => ({
        ...field,
        display_order: index, // Add display_order based on array index
        display_name: field.label, // Map label to display_name
        is_visible_in_list: true, // Default visibility
        is_visible_in_detail: true // Default visibility
      }))
    }
  }

  // Helper function to get field icon based on field type and name
  const getFieldIcon = (fieldName: string, fieldType: string) => {
    const name = fieldName.toLowerCase()
    
    // Email fields
    if (name.includes('email') || fieldType === 'email') {
      return <Mail className="w-3 h-3" />
    }
    
    // Phone fields
    if (name.includes('phone') || name.includes('mobile') || name.includes('tel') || fieldType === 'phone') {
      return <Phone className="w-3 h-3" />
    }
    
    // Company/Organization fields
    if (name.includes('company') || name.includes('organization') || name.includes('employer') || name.includes('business')) {
      return <Building className="w-3 h-3" />
    }
    
    // URL/LinkedIn fields
    if (name.includes('linkedin') || name.includes('url') || name.includes('website') || fieldType === 'url') {
      return <LinkIcon className="w-3 h-3" />
    }
    
    // Default user icon
    return <User className="w-3 h-3" />
  }

  // Helper function to determine if field should be shown as a badge vs detail
  const isContextField = (fieldName: string) => {
    const name = fieldName.toLowerCase()
    return name.includes('status') || name.includes('role') || name.includes('stage') || 
           name.includes('position') || name.includes('level') || name.includes('type')
  }

  // Helper function to render contact fields dynamically
  const renderContactFields = (contact: ContactRecord) => {
    const pipeline = pipelines.find(p => p.id === contact.pipeline_id)
    
    if (!pipeline) {
      console.error('Pipeline not found for contact:', contact.pipeline_id, 'Available pipelines:', pipelines.map(p => ({ id: p.id, name: p.name })))
      return []
    }
    
    if (!pipeline.fields || !Array.isArray(pipeline.fields)) {
      console.warn('Pipeline fields not loaded or invalid:', pipeline)
      return []
    }

    const contactFields: JSX.Element[] = []
    
    // Get important fields to display (contact-related fields)
    const priorityFields = pipeline.fields.filter(field => {
      const name = field.name.toLowerCase()
      const type = field.field_type.toLowerCase()
      const label = (field.label || '').toLowerCase()
      
      return (
        // Email fields
        name.includes('email') || type === 'email' || label.includes('email') ||
        // Phone fields  
        name.includes('phone') || name.includes('mobile') || name.includes('tel') || type === 'phone' || label.includes('phone') ||
        // Company/Organization fields
        name.includes('company') || name.includes('organization') || name.includes('employer') || name.includes('business') ||
        label.includes('company') || label.includes('organization') || label.includes('employer') ||
        // Social/Contact fields
        name.includes('linkedin') || name.includes('url') || name.includes('website') || type === 'url' ||
        label.includes('linkedin') || label.includes('website') ||
        // Address fields
        name.includes('address') || type === 'address' || label.includes('address') ||
        // Name fields (for person contacts)
        name.includes('name') || name.includes('title') || name.includes('first') || name.includes('last') ||
        label.includes('name') || label.includes('title')
      ) && !isContextField(field.name)
    })

    // Debug contact field processing
    if (process.env.NODE_ENV === 'development') {
      console.log(`🔍 Processing contact fields for ${contact.title}:`)
      console.log(`🔍 Available pipeline fields:`, priorityFields.map(f => ({ name: f.name, label: f.label, type: f.field_type })))
      console.log(`🔍 Contact data keys:`, Object.keys(contact.data))
    }

    priorityFields.forEach(field => {
      // Try multiple ways to map field names to data keys
      const possibleKeys = [
        field.name, // Direct match
        field.name.toLowerCase().replace(/\s+/g, '_'), // "Company Name" -> "company_name"
        field.name.toLowerCase().replace(/\s+/g, ''), // "Company Name" -> "companyname"
        field.label?.toLowerCase().replace(/\s+/g, '_'), // Use label if available
      ].filter(Boolean)
      
      let value = null
      let matchedKey = null
      
      // Try each possible key
      for (const key of possibleKeys) {
        if (contact.data[key] !== undefined && contact.data[key] !== null) {
          value = contact.data[key]
          matchedKey = key
          break
        }
      }
      
      // Debug field matching in development
      if (process.env.NODE_ENV === 'development' && value) {
        console.log(`✅ Found value for field "${field.name}" using key "${matchedKey}": ${value}`)
      }
      
      if (value) {
        
        // Convert field to the format expected by FieldResolver
        const fieldForResolver = {
          name: field.name,
          field_type: field.field_type,
          display_name: field.label || field.name,
          ...field
        }
        
        // Format the value properly using the field system (using 'table' context for compact display)
        const formattedValue = FieldResolver.formatValue(fieldForResolver, value, 'table')
        
        contactFields.push(
          <div key={field.name} className="flex items-center gap-2 text-sm text-gray-600">
            {getFieldIcon(field.name, field.field_type)}
            <span className="text-xs text-gray-500 min-w-0 flex-shrink-0">{field.label || field.name}:</span>
            <div className="truncate min-w-0 flex-1">
              {typeof formattedValue === 'string' ? (
                <span>{formattedValue}</span>
              ) : (
                <div className="inline-flex items-center gap-1">{formattedValue}</div>
              )}
            </div>
          </div>
        )
      }
    })

    return contactFields
  }

  // Helper function to render context badges
  const renderContextBadges = (contact: ContactRecord) => {
    const pipeline = pipelines.find(p => p.id === contact.pipeline_id)
    
    if (!pipeline) {
      console.warn('Pipeline not found for context badges:', contact.pipeline_id)
      return []
    }
    
    if (!pipeline.fields || !Array.isArray(pipeline.fields)) {
      console.warn('Pipeline fields not properly loaded for context badges:', pipeline)
      return []
    }

    const badges: JSX.Element[] = []
    
    // Get context fields (status, role, etc.)
    const contextFields = pipeline.fields.filter(field => isContextField(field.name))
    
    contextFields.forEach(field => {
      // Try multiple ways to map field names to data keys
      const possibleKeys = [
        field.name,
        field.name.toLowerCase().replace(/\s+/g, '_'),
        field.name.toLowerCase().replace(/\s+/g, ''),
        field.label?.toLowerCase().replace(/\s+/g, '_'),
      ].filter(Boolean)
      
      let value = null
      for (const key of possibleKeys) {
        if (contact.data[key] !== undefined && contact.data[key] !== null) {
          value = contact.data[key]
          break
        }
      }
      
      if (value) {
        // Convert field to the format expected by FieldResolver
        const fieldForResolver = {
          name: field.name,
          field_type: field.field_type,
          display_name: field.label || field.name,
          ...field
        }
        
        // Format the value properly using the field system (using 'table' context for compact display)
        const formattedValue = FieldResolver.formatValue(fieldForResolver, value, 'table')
        
        badges.push(
          <Badge key={field.name} variant="secondary" className="text-xs">
            {field.name.toLowerCase().includes('location') ? '📍 ' : ''}
            {typeof formattedValue === 'string' ? (
              formattedValue
            ) : (
              <div className="inline-flex items-center gap-1">{formattedValue}</div>
            )}
          </Badge>
        )
      }
    })

    return badges
  }

  // Helper function to render match indicators dynamically
  const renderMatchIndicators = (contact: ContactRecord, unmatchedData: any) => {
    const pipeline = pipelines.find(p => p.id === contact.pipeline_id)
    
    if (!pipeline) {
      console.warn('Pipeline not found for match indicators:', contact.pipeline_id)
      return null
    }
    
    if (!pipeline.fields || !Array.isArray(pipeline.fields)) {
      console.warn('Pipeline fields not properly loaded for match indicators:', pipeline)
      return null
    }

    const matches: JSX.Element[] = []
    
    // Check all pipeline fields for potential matches
    pipeline.fields.forEach(field => {
      // Try multiple ways to map field names to data keys
      const possibleKeys = [
        field.name,
        field.name.toLowerCase().replace(/\s+/g, '_'),
        field.name.toLowerCase().replace(/\s+/g, ''),
        field.label?.toLowerCase().replace(/\s+/g, '_'),
      ].filter(Boolean)
      
      let contactValue = null
      for (const key of possibleKeys) {
        if (contact.data[key] !== undefined && contact.data[key] !== null) {
          contactValue = contact.data[key]
          break
        }
      }
      
      if (contactValue && unmatchedData) {
        // Check for direct field matches
        Object.keys(unmatchedData).forEach(unmatchedKey => {
          const unmatchedValue = unmatchedData[unmatchedKey]
          
          // Format both values for comparison
          const fieldForResolver = {
            name: field.name,
            field_type: field.field_type,
            display_name: field.label || field.name,
            ...field
          }
          
          const formattedContactValue = FieldResolver.formatValue(fieldForResolver, contactValue, 'table')
          const contactValueStr = typeof formattedContactValue === 'string' ? formattedContactValue : contactValue.toString()
          
          if (unmatchedValue && contactValueStr.toLowerCase() === unmatchedValue.toString().toLowerCase()) {
            matches.push(
              <span key={`${field.name}-${unmatchedKey}`} className="inline-flex items-center gap-1 text-green-600 mr-2">
                <CheckCircle className="w-3 h-3" /> {field.label || field.name} matches
              </span>
            )
          }
        })
        
        // Special case for email domain matching (if unmatched has email and contact has email)
        if (field.name.toLowerCase().includes('email') && unmatchedData.email && contactValueStr.includes('@')) {
          const contactDomain = contactValueStr.split('@')[1]?.toLowerCase()
          const unmatchedDomain = unmatchedData.email.split('@')[1]?.toLowerCase()
          
          if (contactDomain && unmatchedDomain && contactDomain === unmatchedDomain) {
            matches.push(
              <span key={`${field.name}-domain`} className="inline-flex items-center gap-1 text-yellow-600 mr-2">
                <CheckCircle className="w-3 h-3" /> Email domain matches
              </span>
            )
          }
        }
      }
    })

    if (matches.length === 0) return null

    return (
      <div className="text-xs text-gray-500 space-y-1">
        <div className="font-medium">Potential Matches:</div>
        <div className="flex flex-wrap gap-1">
          {matches}
        </div>
      </div>
    )
  }

  if (!message) return null

  const hasMatchedContact = message.contact_record
  const hasUnmatchedData = message.unmatched_contact_data
  const needsDomainReview = message.needs_domain_review || !message.domain_validated
  const relationshipContext = message.relationship_context

  return (
    <>
      <Dialog open={isOpen} onOpenChange={onClose}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <User className="w-5 h-5" />
              Contact Resolution
            </DialogTitle>
            <DialogDescription>
              Manage contact information for message from {message.contact_email}
            </DialogDescription>
          </DialogHeader>

          <Tabs value={activeTab} onValueChange={(value: any) => setActiveTab(value)}>
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="view" disabled={!hasMatchedContact}>
                <CheckCircle className="w-4 h-4 mr-2" />
                View Contact
              </TabsTrigger>
              <TabsTrigger value="connect">
                <LinkIcon className="w-4 h-4 mr-2" />
                Connect Existing
              </TabsTrigger>
              <TabsTrigger value="create">
                <Plus className="w-4 h-4 mr-2" />
                Create New
              </TabsTrigger>
            </TabsList>

            {/* View Matched Contact */}
            <TabsContent value="view" className="space-y-4">
              {hasMatchedContact ? (
                <div className="space-y-4">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center justify-between">
                        <span>Matched Contact</span>
                        <Badge variant="default" className="bg-green-100 text-green-800">
                          <CheckCircle className="w-3 h-3 mr-1" />
                          Connected
                        </Badge>
                      </CardTitle>
                      <CardDescription>
                        This message is connected to the following contact record
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="flex items-center justify-between p-4 border rounded-lg">
                        <div>
                          <h3 className="font-medium">{message.contact_record?.title}</h3>
                          <p className="text-sm text-gray-600">{message.contact_record?.pipeline_name}</p>
                          <p className="text-xs text-gray-500">ID: {message.contact_record?.id}</p>
                        </div>
                        <Button 
                          variant="outline"
                          onClick={() => message.contact_record && handleViewContact(message.contact_record)}
                        >
                          View Details
                        </Button>
                      </div>

                      {/* Domain Validation Status */}
                      {needsDomainReview && relationshipContext && (
                        <Alert variant="warning">
                          <AlertTriangle className="h-4 w-4" />
                          <AlertDescription className="space-y-2">
                            <div>
                              <strong>Domain Validation Warning</strong>
                            </div>
                            <div className="text-sm space-y-1">
                              <p>Status: {relationshipContext.validation_status}</p>
                              {relationshipContext.message_domain && (
                                <p>Message domain: {relationshipContext.message_domain}</p>
                              )}
                              {relationshipContext.pipeline_context.length > 0 && (
                                <div>
                                  <p>Related records found:</p>
                                  <ul className="list-disc list-inside pl-4">
                                    {relationshipContext.pipeline_context.map((context, index) => (
                                      <li key={index} className="text-xs">
                                        {context.record_title} ({context.pipeline_name})
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                            </div>
                          </AlertDescription>
                        </Alert>
                      )}
                    </CardContent>
                  </Card>
                </div>
              ) : (
                <Card>
                  <CardContent className="text-center py-8">
                    <User className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-medium mb-2">No Contact Matched</h3>
                    <p className="text-gray-600 mb-4">
                      This message hasn't been connected to a contact record yet.
                    </p>
                    <div className="flex gap-2 justify-center">
                      <Button variant="outline" onClick={() => setActiveTab('connect')}>
                        Connect Existing
                      </Button>
                      <Button onClick={() => setActiveTab('create')}>
                        Create New Contact
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            {/* Connect Existing Contact */}
            <TabsContent value="connect" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Connect to Existing Contact</CardTitle>
                  <CardDescription>
                    Search for an existing contact to connect this message to
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Message Contact Info */}
                  {hasUnmatchedData && (
                    <Alert variant="info">
                      <Info className="h-4 w-4" />
                      <AlertDescription>
                        <div className="space-y-1">
                          <strong>Contact information from message:</strong>
                          {hasUnmatchedData.email && <div>📧 {hasUnmatchedData.email}</div>}
                          {hasUnmatchedData.phone && <div>📞 {hasUnmatchedData.phone}</div>}
                          {hasUnmatchedData.name && <div>👤 {hasUnmatchedData.name}</div>}
                        </div>
                      </AlertDescription>
                    </Alert>
                  )}

                  {/* Search Input */}
                  <div className="space-y-2">
                    <Label htmlFor="search">Search Contacts</Label>
                    <Input
                      id="search"
                      placeholder="Search by name, email, or phone..."
                      value={searchQuery}
                      onChange={(e) => {
                        setSearchQuery(e.target.value)
                        debouncedSearchContacts(e.target.value)
                      }}
                    />
                  </div>

                  {/* Search Debug Info */}
                  {process.env.NODE_ENV === 'development' && (
                    <div className="text-xs text-gray-500 bg-gray-100 p-2 rounded">
                      Debug: Query="{searchQuery}" | Results={searchResults.length} | Searching={isSearching.toString()}
                    </div>
                  )}

                  {/* Search Results */}
                  {isSearching && (
                    <div className="text-center py-4">
                      <div className="text-sm text-gray-500">Searching...</div>
                    </div>
                  )}
                  {!isSearching && searchResults.length > 0 && (
                    <div className="space-y-2">
                      <Label>Search Results</Label>
                      <div className="space-y-3 max-h-80 overflow-y-auto">
                        {searchResults.map((contact) => (
                          <div 
                            key={contact.id}
                            className="flex items-start justify-between p-4 border rounded-lg hover:bg-gray-50 transition-colors"
                          >
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-2">
                                <h4 className="font-semibold text-gray-900 truncate">{contact.title}</h4>
                                <Badge variant="outline" className="text-xs">
                                  {contact.pipeline_name}
                                </Badge>
                              </div>
                              
                              {/* Contact Details */}
                              <div className="space-y-1 mb-3">
                                {renderContactFields(contact)}
                              </div>

                              {/* Additional Context */}
                              <div className="flex flex-wrap gap-1">
                                {renderContextBadges(contact)}
                              </div>

                              {/* Match Indicators */}
                              {hasUnmatchedData && (
                                <div className="mt-2 pt-2 border-t border-gray-100">
                                  {renderMatchIndicators(contact, hasUnmatchedData)}
                                </div>
                              )}
                            </div>
                            
                            <div className="flex flex-col gap-2 ml-4">
                              <Button 
                                size="sm"
                                onClick={() => handleConnectContact(contact)}
                                disabled={loading}
                                className="whitespace-nowrap"
                              >
                                Connect
                              </Button>
                              <Button 
                                size="sm"
                                variant="outline"
                                onClick={() => handleViewContact(contact)}
                                disabled={loading}
                                className="whitespace-nowrap"
                              >
                                <User className="w-3 h-3 mr-1" />
                                View
                              </Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Domain Override for Warnings */}
                  {needsDomainReview && (
                    <div className="space-y-2">
                      <Label htmlFor="override">Override Reason (Required for Domain Warnings)</Label>
                      <Textarea
                        id="override"
                        placeholder="Explain why you're connecting this contact despite domain validation warnings..."
                        value={overrideReason}
                        onChange={(e) => setOverrideReason(e.target.value)}
                      />
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            {/* Create New Contact */}
            <TabsContent value="create" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Create New Contact</CardTitle>
                  <CardDescription>
                    Create a new contact record and connect it to this message
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Message Contact Info */}
                  {hasUnmatchedData && (
                    <Alert variant="info">
                      <Info className="h-4 w-4" />
                      <AlertDescription>
                        <div className="space-y-1">
                          <strong>Information will be pre-filled from message:</strong>
                          {hasUnmatchedData.email && <div>📧 {hasUnmatchedData.email}</div>}
                          {hasUnmatchedData.phone && <div>📞 {hasUnmatchedData.phone}</div>}
                          {hasUnmatchedData.name && <div>👤 {hasUnmatchedData.name}</div>}
                        </div>
                      </AlertDescription>
                    </Alert>
                  )}

                  {/* Pipeline Selection */}
                  <div className="space-y-2">
                    <Label htmlFor="pipeline">Select Pipeline</Label>
                    <Select value={selectedPipeline} onValueChange={setSelectedPipeline}>
                      <SelectTrigger>
                        <SelectValue placeholder="Choose a pipeline for the new contact" />
                      </SelectTrigger>
                      <SelectContent>
                        {pipelines.map((pipeline) => (
                          <SelectItem key={pipeline.id} value={pipeline.id}>
                            <div>
                              <div className="font-medium">{pipeline.name}</div>
                              {pipeline.description && (
                                <div className="text-xs text-gray-500">{pipeline.description}</div>
                              )}
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {selectedPipeline && (
                    <Button 
                      onClick={() => handleCreateContact(selectedPipeline)}
                      className="w-full"
                    >
                      <Plus className="w-4 h-4 mr-2" />
                      Create Contact in {pipelines.find(p => p.id === selectedPipeline)?.name}
                    </Button>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>

          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button variant="outline" onClick={onClose}>
              Close
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Record Detail Drawer */}
      {showRecordDrawer && selectedPipeline && (
        <RecordDetailDrawer
          record={drawerMode === 'view' && selectedContact ? convertContactToRecordData(selectedContact) : null}
          pipeline={convertPipelineFormat(pipelines.find(p => p.id === selectedPipeline)!)}
          isOpen={showRecordDrawer}
          onClose={() => setShowRecordDrawer(false)}
          onSave={handleRecordSave}
          isReadOnly={drawerMode === 'view'}
        />
      )}
    </>
  )
}