'use client'

import { useState, useEffect, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, Users, Send, Check, Search, X } from 'lucide-react'
import { useToast } from '@/hooks/use-toast'
import { api } from '@/lib/api'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { ScrollArea } from '@/components/ui/scroll-area'

interface Props {
  meetingTypeId: string
  pipelineId: string
  meetingType?: any  // Full meeting type data passed from parent
  onClose?: () => void
}

interface PipelineRecord {
  id: string
  data: Record<string, any>
  display_value?: string
}

interface PipelineField {
  id: string
  name: string
  slug: string
  field_type: string
  display_name?: string
}

export default function FacilitatorMeetingInitiator({ meetingTypeId, pipelineId, meetingType: passedMeetingType, onClose }: Props) {
  const [records, setRecords] = useState<PipelineRecord[]>([])
  const [loadingRecords, setLoadingRecords] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [success, setSuccess] = useState(false)
  
  const [participant1Id, setParticipant1Id] = useState('')
  const [participant2Id, setParticipant2Id] = useState('')
  const [participant1Details, setParticipant1Details] = useState<any>(null)
  const [participant2Details, setParticipant2Details] = useState<any>(null)
  
  // Search states
  const [participant1Search, setParticipant1Search] = useState('')
  const [participant2Search, setParticipant2Search] = useState('')
  const [open1, setOpen1] = useState(false)
  const [open2, setOpen2] = useState(false)
  
  const [meetingType, setMeetingType] = useState<any>(null)
  const [selectedFields, setSelectedFields] = useState<PipelineField[]>([])
  const [loadingMeetingType, setLoadingMeetingType] = useState(true)
  
  const { toast } = useToast()
  
  // Filter records based on search
  const filteredRecords1 = records.filter(record => {
    if (!participant1Search) return true
    const searchLower = participant1Search.toLowerCase()
    
    // Search in display value
    if (record.display_value?.toLowerCase().includes(searchLower)) return true
    
    // Search in all data fields
    const recordData = { ...record.data, ...record }
    return Object.values(recordData).some(value => {
      if (typeof value === 'string') {
        return value.toLowerCase().includes(searchLower)
      }
      if (typeof value === 'object' && value?.number) {
        return value.number.includes(participant1Search)
      }
      return false
    })
  })
  
  const filteredRecords2 = records.filter(record => {
    if (!participant2Search) return true
    const searchLower = participant2Search.toLowerCase()
    
    // Search in display value
    if (record.display_value?.toLowerCase().includes(searchLower)) return true
    
    // Search in all data fields
    const recordData = { ...record.data, ...record }
    return Object.values(recordData).some(value => {
      if (typeof value === 'string') {
        return value.toLowerCase().includes(searchLower)
      }
      if (typeof value === 'object' && value?.number) {
        return value.number.includes(participant2Search)
      }
      return false
    })
  })
  
  // Helper function to format field names
  const formatFieldName = (key: string) => {
    return key
      .replace(/_/g, ' ')
      .replace(/\b\w/g, char => char.toUpperCase())
  }
  
  // Helper function to render field value
  const renderFieldValue = (value: any) => {
    if (value === null || value === undefined) return 'N/A'
    if (typeof value === 'boolean') return value ? 'Yes' : 'No'
    
    // Handle phone number object
    if (typeof value === 'object' && value.number) {
      const countryCode = value.country_code || ''
      const number = value.number || ''
      return `${countryCode} ${number}`.trim()
    }
    
    // Handle address or other objects
    if (typeof value === 'object') {
      // Check if it's an empty object
      if (Object.keys(value).length === 0) return 'Not provided'
      // For other objects, try to display meaningfully
      return JSON.stringify(value, null, 2)
    }
    
    return String(value)
  }
  
  
  useEffect(() => {
    fetchMeetingTypeDetails()
    fetchRecords() // Fetch records immediately for searching
  }, [pipelineId, meetingTypeId, passedMeetingType])
  
  const fetchMeetingTypeDetails = async () => {
    try {
      setLoadingMeetingType(true)
      
      // Use passed meeting type data if available, otherwise set minimal data
      const meetingData = passedMeetingType || { 
        id: meetingTypeId,
        pipeline: pipelineId,
        booking_form_config: {}
      }
      console.log('Meeting type data:', meetingData)
      setMeetingType(meetingData)
      
      if (pipelineId) {
        try {
          const pipelineStage = meetingData.pipeline_stage
          
          console.log('Meeting type config:', {
            pipelineStage,
            bookingFormConfig: meetingData.booking_form_config
          })

          // Fetch dynamic form for the stage
          if (pipelineStage) {
            // Fetch the dynamic form for this stage
            const formResponse = await api.get(`/api/v1/pipelines/${pipelineId}/forms/stage/${pipelineStage}/public/`)
            console.log('Dynamic form response:', formResponse.data)
            
            if (formResponse.data && formResponse.data.fields) {
              const formFields = formResponse.data.fields
              console.log('Using dynamic form fields:', formFields.map((f: any) => ({ id: f.id, slug: f.slug, name: f.name })))
              setSelectedFields(formFields)
            } else {
              console.log('No fields in dynamic form response')
              setSelectedFields([])
            }
          } else {
            console.log('No pipeline stage configured')
            setSelectedFields([])
          }
        } catch (fieldsError) {
          console.error('Failed to fetch pipeline fields:', fieldsError)
          setSelectedFields([])
        }
      }
    } catch (error) {
      console.error('Failed to fetch meeting type details:', error)
    } finally {
      setLoadingMeetingType(false)
    }
  }
  
  const fetchRecords = async () => {
    try {
      let allRecords: any[] = []
      let nextUrl: string | null = `/api/v1/pipelines/${pipelineId}/records/?page_size=100`
      
      // Fetch all pages of records
      while (nextUrl) {
        const response = await api.get(nextUrl)
        const data = response.data
        
        // Add records from this page
        const pageRecords = data.results || data || []
        allRecords = [...allRecords, ...pageRecords]
        
        console.log(`Fetched page with ${pageRecords.length} records. Total so far: ${allRecords.length}`)
        
        // Check if there's a next page
        if (data.next) {
          // Extract the path and query from the next URL
          const url = new URL(data.next)
          nextUrl = `${url.pathname}${url.search}`
        } else {
          nextUrl = null
        }
      }
      
      console.log(`Total records fetched: ${allRecords.length}`)
      
      // Process records to extract display values dynamically
      const processedRecords = allRecords.map((record: any) => {
        // Build display value from first available name/email field
        let displayValue = ''
        const nameParts: string[] = []
        
        // Strategy 1: Look for first_name and last_name fields
        if (record.data.first_name) {
          nameParts.push(record.data.first_name)
        }
        if (record.data.last_name) {
          nameParts.push(record.data.last_name)
        }
        
        if (nameParts.length > 0) {
          displayValue = nameParts.join(' ')
        } else {
          // Strategy 2: Look for a full_name or name field
          if (record.data.full_name) {
            displayValue = record.data.full_name
          } else if (record.data.name) {
            displayValue = record.data.name
          } else {
            // Strategy 3: Look for any field with 'name' in the slug
            for (const [fieldSlug, value] of Object.entries(record.data)) {
              if (value && fieldSlug.toLowerCase().includes('name')) {
                displayValue = String(value)
                break
              }
            }
            
            // Strategy 4: Fall back to email if no name found
            if (!displayValue) {
              for (const [fieldSlug, value] of Object.entries(record.data)) {
                if (value && fieldSlug.toLowerCase().includes('email')) {
                  displayValue = String(value)
                  break
                }
              }
            }
            
            // Strategy 5: Use first non-empty field from form fields
            if (!displayValue && selectedFields.length > 0) {
              for (const field of selectedFields) {
                const value = record.data[field.slug]
                if (value) {
                  displayValue = String(value)
                  break
                }
              }
            }
          }
        }
        
        // Fallback to ID if no display value found
        if (!displayValue) {
          displayValue = `Record ${record.id}`
        }
        
        return {
          ...record,
          display_value: displayValue
        }
      })
      
      setRecords(processedRecords)
    } catch (error) {
      console.error('Failed to fetch records:', error)
      toast({
        title: 'Failed to load contacts',
        description: 'Unable to load pipeline records',
        variant: 'destructive'
      })
    } finally {
      setLoadingRecords(false)
    }
  }
  
  const handleSubmit = async () => {
    if (!participant1Id || !participant2Id) {
      toast({
        title: 'Select participants',
        description: 'Please select both participants',
        variant: 'destructive'
      })
      return
    }
    
    if (participant1Id === participant2Id) {
      toast({
        title: 'Invalid selection',
        description: 'Please select different participants',
        variant: 'destructive'
      })
      return
    }
    
    setSubmitting(true)
    try {
      const response = await api.post(
        '/api/v1/communications/scheduling/facilitator/initiate/',
        {
          meeting_type_id: meetingTypeId,
          participant_1_record_id: participant1Id,
          participant_2_record_id: participant2Id
        }
      )
      
      setSuccess(true)
      toast({
        title: 'Meeting initiated',
        description: response.data.message || 'Invitation sent to Participant 1'
      })
      
      // Close after 2 seconds
      setTimeout(() => {
        if (onClose) onClose()
      }, 2000)
      
    } catch (error: any) {
      console.error('Failed to initiate meeting:', error)
      toast({
        title: 'Failed to initiate meeting',
        description: error.response?.data?.error || 'Please try again',
        variant: 'destructive'
      })
    } finally {
      setSubmitting(false)
    }
  }
  
  if (success) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col items-center text-center space-y-4">
            <div className="h-12 w-12 rounded-full bg-green-100 flex items-center justify-center">
              <Check className="h-6 w-6 text-green-600" />
            </div>
            <div>
              <h3 className="font-semibold">Meeting Initiated!</h3>
              <p className="text-sm text-muted-foreground mt-1">
                An invitation has been sent to the first participant
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }
  
  return (
    <Card>
      <CardHeader>
        <CardTitle>Initiate Facilitator Meeting</CardTitle>
        <CardDescription>
          Select two participants from your pipeline. The first participant will receive a link to configure the meeting.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {loadingRecords || loadingMeetingType ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        ) : records.length === 0 ? (
          <Alert>
            <AlertDescription>
              No records found in this pipeline. Please add contacts first.
            </AlertDescription>
          </Alert>
        ) : (
          <>
            <div className="space-y-2">
              <Label htmlFor="participant1">Participant 1</Label>
              <Popover open={open1} onOpenChange={setOpen1}>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    role="combobox"
                    aria-expanded={open1}
                    className="w-full justify-between font-normal"
                  >
                    {participant1Details ? (
                      <span className="truncate">{participant1Details.display_value}</span>
                    ) : (
                      <span className="text-muted-foreground">Search and select first participant</span>
                    )}
                    <Search className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-[400px] p-2" align="start">
                  <div className="space-y-2">
                    <div className="flex items-center px-2">
                      <Search className="h-4 w-4 mr-2 text-muted-foreground" />
                      <Input
                        placeholder="Search by name, email, or phone..."
                        value={participant1Search}
                        onChange={(e) => setParticipant1Search(e.target.value)}
                        className="h-8 border-0 focus:ring-0 focus-visible:ring-0 focus-visible:ring-offset-0 p-0"
                      />
                      {participant1Search && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0"
                          onClick={() => setParticipant1Search('')}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                    <ScrollArea className="h-[300px]">
                      {filteredRecords1.length === 0 ? (
                        <div className="py-6 text-center text-sm text-muted-foreground">
                          No participants found
                        </div>
                      ) : (
                        <div className="space-y-1">
                          {filteredRecords1.slice(0, 50).map((record) => (
                            <Button
                              key={record.id}
                              variant="ghost"
                              className={`w-full justify-start h-auto py-2 px-2 ${
                                record.id === participant2Id ? 'opacity-50 cursor-not-allowed' : ''
                              }`}
                              disabled={record.id === participant2Id}
                              onClick={() => {
                                if (record.id !== participant2Id) {
                                  setParticipant1Id(record.id)
                                  setParticipant1Details(record)
                                  setOpen1(false)
                                  setParticipant1Search('')
                                }
                              }}
                            >
                              <div className="flex flex-col items-start">
                                <span className="font-medium">{record.display_value}</span>
                                {record.data.personal_email && (
                                  <span className="text-xs text-muted-foreground">
                                    {record.data.personal_email}
                                  </span>
                                )}
                              </div>
                            </Button>
                          ))}
                        </div>
                      )}
                    </ScrollArea>
                  </div>
                </PopoverContent>
              </Popover>
              <p className="text-xs text-muted-foreground">
                Will receive link to configure meeting and select times
              </p>
              {participant1Details && selectedFields.length > 0 && (
                <div className="mt-3 p-3 bg-muted/30 rounded-md border border-muted">
                  <p className="text-xs font-semibold mb-2 text-primary">Participant 1 Information:</p>
                  <div className="space-y-1">
                    {selectedFields.map(field => {
                      // Check both data object and top level for field values
                      const value = participant1Details.data?.[field.slug] ?? participant1Details[field.slug]
                      const hasValue = value !== undefined && value !== null && value !== ''
                      
                      return (
                        <div key={field.id} className="text-xs flex">
                          <span className="font-medium text-muted-foreground min-w-[100px]">
                            {field.display_name || field.name || formatFieldName(field.slug)}:
                          </span>
                          <span className={`ml-2 ${!hasValue ? 'text-muted-foreground/50 italic' : ''}`}>
                            {hasValue ? renderFieldValue(value) : 'Not provided'}
                          </span>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="participant2">Participant 2</Label>
              <Popover open={open2} onOpenChange={setOpen2}>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    role="combobox"
                    aria-expanded={open2}
                    className="w-full justify-between font-normal"
                  >
                    {participant2Details ? (
                      <span className="truncate">{participant2Details.display_value}</span>
                    ) : (
                      <span className="text-muted-foreground">Search and select second participant</span>
                    )}
                    <Search className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-[400px] p-2" align="start">
                  <div className="space-y-2">
                    <div className="flex items-center px-2">
                      <Search className="h-4 w-4 mr-2 text-muted-foreground" />
                      <Input
                        placeholder="Search by name, email, or phone..."
                        value={participant2Search}
                        onChange={(e) => setParticipant2Search(e.target.value)}
                        className="h-8 border-0 focus:ring-0 focus-visible:ring-0 focus-visible:ring-offset-0 p-0"
                      />
                      {participant2Search && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0"
                          onClick={() => setParticipant2Search('')}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                    <ScrollArea className="h-[300px]">
                      {filteredRecords2.length === 0 ? (
                        <div className="py-6 text-center text-sm text-muted-foreground">
                          No participants found
                        </div>
                      ) : (
                        <div className="space-y-1">
                          {filteredRecords2.slice(0, 50).map((record) => (
                            <Button
                              key={record.id}
                              variant="ghost"
                              className={`w-full justify-start h-auto py-2 px-2 ${
                                record.id === participant1Id ? 'opacity-50 cursor-not-allowed' : ''
                              }`}
                              disabled={record.id === participant1Id}
                              onClick={() => {
                                if (record.id !== participant1Id) {
                                  setParticipant2Id(record.id)
                                  setParticipant2Details(record)
                                  setOpen2(false)
                                  setParticipant2Search('')
                                }
                              }}
                            >
                              <div className="flex flex-col items-start">
                                <span className="font-medium">{record.display_value}</span>
                                {record.data.personal_email && (
                                  <span className="text-xs text-muted-foreground">
                                    {record.data.personal_email}
                                  </span>
                                )}
                              </div>
                            </Button>
                          ))}
                        </div>
                      )}
                    </ScrollArea>
                  </div>
                </PopoverContent>
              </Popover>
              <p className="text-xs text-muted-foreground">
                Will receive link to choose from Participant 1's selected times
              </p>
              {participant2Details && selectedFields.length > 0 && (
                <div className="mt-3 p-3 bg-muted/30 rounded-md border border-muted">
                  <p className="text-xs font-semibold mb-2 text-primary">Participant 2 Information:</p>
                  <div className="space-y-1">
                    {selectedFields.map(field => {
                      // Check both data object and top level for field values
                      const value = participant2Details.data?.[field.slug] ?? participant2Details[field.slug]
                      const hasValue = value !== undefined && value !== null && value !== ''
                      
                      return (
                        <div key={field.id} className="text-xs flex">
                          <span className="font-medium text-muted-foreground min-w-[100px]">
                            {field.display_name || field.name || formatFieldName(field.slug)}:
                          </span>
                          <span className={`ml-2 ${!hasValue ? 'text-muted-foreground/50 italic' : ''}`}>
                            {hasValue ? renderFieldValue(value) : 'Not provided'}
                          </span>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
            </div>
            
            <div className="flex gap-2 pt-4">
              {onClose && (
                <Button variant="outline" onClick={onClose}>
                  Cancel
                </Button>
              )}
              <Button 
                onClick={handleSubmit}
                disabled={!participant1Id || !participant2Id || submitting}
                className="flex-1"
              >
                {submitting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Initiating...
                  </>
                ) : (
                  <>
                    <Send className="h-4 w-4 mr-2" />
                    Initiate Meeting
                  </>
                )}
              </Button>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}