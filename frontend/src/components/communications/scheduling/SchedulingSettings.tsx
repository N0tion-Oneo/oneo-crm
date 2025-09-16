'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Switch } from '@/components/ui/switch'
import { Calendar, Clock, Plus, Edit, Trash2, Copy, ExternalLink, Loader2, Settings, Link as LinkIcon } from 'lucide-react'
import { useToast } from '@/hooks/use-toast'
import { useAuth } from '@/features/auth/context'
import { api } from '@/lib/api'

interface Pipeline {
  id: string
  name: string
  description: string
  pipeline_type: string
}

interface MeetingType {
  id: string
  name: string
  slug: string
  description: string
  duration_minutes: number
  location_type: string
  calendar_connection: string | null
  calendar_connection_display?: {
    id: string
    account_name: string
    channel_type: string
    auth_status: string
  }
  calendar_id: string
  calendar_name: string
  pipeline: string | null
  pipeline_stage: string
  booking_form_config?: {
    selected_fields?: string[]
    stage_field_id?: string | null
  }
  required_fields?: string[]
  is_active: boolean
  total_bookings: number
  booking_url?: string
  is_template?: boolean
  template_source?: string
  created_for_org?: boolean
}

interface Field {
  id: string
  slug: string
  name: string
  field_type: string
  is_required: boolean
  field_config?: {
    options?: { value: string; label: string }[]
  }
}

interface Calendar {
  id: string
  name: string
  is_default: boolean
  is_read_only: boolean
  is_owned_by_user: boolean
}

interface SchedulingProfile {
  id: string
  user: string
  calendar_connection: string | null
  timezone: string
  buffer_minutes: number
  min_notice_hours: number
  max_advance_days: number
  working_hours: Record<string, any[]>
  is_active: boolean
}

interface SchedulingSettingsProps {
  canManageAll?: boolean
}

export function SchedulingSettings({ canManageAll = false }: SchedulingSettingsProps) {
  const [profiles, setProfiles] = useState<SchedulingProfile[]>([])
  const [meetingTypes, setMeetingTypes] = useState<MeetingType[]>([])
  const [templates, setTemplates] = useState<MeetingType[]>([])
  const [calendars, setCalendars] = useState<Calendar[]>([])
  const [loadingCalendars, setLoadingCalendars] = useState(false)
  const [pipelines, setPipelines] = useState<Pipeline[]>([])
  const [selectedPipeline, setSelectedPipeline] = useState<Pipeline | null>(null)
  const [stageFields, setStageFields] = useState<Field[]>([])  // Select fields that can be stages
  const [selectedStageField, setSelectedStageField] = useState<Field | null>(null)  // Selected stage field
  const [loading, setLoading] = useState(true)
  const [showMeetingDialog, setShowMeetingDialog] = useState(false)
  const [showTemplateDialog, setShowTemplateDialog] = useState(false)
  const [editingMeeting, setEditingMeeting] = useState<MeetingType | null>(null)
  
  const { toast } = useToast()
  const { user } = useAuth()
  
  // Form state for meeting type
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    duration_minutes: 30,
    location_type: 'google_meet',
    calendar_id: '',
    calendar_name: '',
    pipeline: '',
    pipeline_stage: '',
    booking_form_config: {
      selected_fields: [] as string[],
      stage_field_id: null as string | null
    },
    required_fields: [] as string[],
    is_active: true,
    allow_rescheduling: true,
    allow_cancellation: true,
    cancellation_notice_hours: 24,
    send_reminders: true,
    reminder_hours: 24
  })

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      // Load meeting types, templates and pipelines
      // Note: Backend API already filters based on permissions (scheduling_all vs scheduling)
      const [meetingTypesRes, templatesRes, pipelinesRes] = await Promise.all([
        api.get('/api/v1/communications/scheduling/meeting-types/'),
        api.get('/api/v1/communications/scheduling/meeting-types/templates/').catch(() => ({ data: [] })),
        api.get('/api/v1/pipelines/')
      ])
      
      const allTypes = meetingTypesRes.data.results || meetingTypesRes.data || []
      // Filter out templates from regular meeting types
      setMeetingTypes(allTypes.filter((mt: MeetingType) => !mt.is_template))
      setTemplates(templatesRes.data.results || templatesRes.data || [])
      setPipelines(pipelinesRes.data.results || pipelinesRes.data || [])
      
      // Try to load calendars from the user's profile connection
      // This will work if they have a profile with a calendar connection
      try {
        const calendarsRes = await api.get('/api/v1/communications/scheduling/meeting-types/calendars_for_connection/')
        setCalendars(calendarsRes.data.calendars || [])
      } catch (error) {
        // If no profile/connection, calendars will be empty
        console.log('No calendar connection in profile yet')
        setCalendars([])
      }
    } catch (error: any) {
      console.error('Failed to load scheduling data:', error)
      toast({
        title: 'Failed to load scheduling data',
        description: error.response?.data?.error || 'An error occurred',
        variant: 'destructive'
      })
    } finally {
      setLoading(false)
    }
  }

  const loadPipelineFields = async (pipelineId: string, meetingToEdit?: MeetingType | null) => {
    if (!pipelineId) {
      setStageFields([])
      return
    }
    
    try {
      const response = await api.get(`/api/v1/pipelines/${pipelineId}/fields/`)
      const fields = response.data.results || response.data
      
      // Filter for select fields that can be used as stages
      const selectFields = fields.filter((f: Field) => f.field_type === 'select')
      console.log('Select fields found:', selectFields)
      setStageFields(selectFields)
      
      // If editing and has a stored stage field, restore it
      if (meetingToEdit && meetingToEdit.booking_form_config?.stage_field_id) {
        const storedStageField = selectFields.find((f: Field) => 
          f.id === meetingToEdit.booking_form_config?.stage_field_id
        )
        if (storedStageField) {
          console.log('Restored stage field:', storedStageField)
          setSelectedStageField(storedStageField)
          return
        }
      }
      
      // Otherwise, auto-select a field named 'stage' or 'status'
      const defaultStageField = selectFields.find((f: Field) => 
        f.slug === 'stage' || f.slug === 'status' || 
        (f.name && (f.name.toLowerCase().includes('stage') || f.name.toLowerCase().includes('status')))
      )
      if (defaultStageField) {
        console.log('Default stage field:', defaultStageField)
        setSelectedStageField(defaultStageField)
      }
    } catch (error) {
      console.error('Failed to load pipeline fields:', error)
    }
  }

  const handleCreateOrUpdateMeeting = async () => {
    try {
      if (!formData.name || !formData.calendar_id || !formData.pipeline) {
        toast({
          title: 'Missing Required Fields',
          description: 'Please provide a name, select a calendar, and choose a pipeline',
          variant: 'destructive'
        })
        return
      }

      const payload = {
        ...formData,
        user: user?.id
      }

      if (editingMeeting) {
        await api.patch(`/api/v1/communications/scheduling/meeting-types/${editingMeeting.id}/`, payload)
        toast({
          title: 'Meeting Type Updated',
          description: 'Meeting type has been updated successfully'
        })
      } else {
        await api.post('/api/v1/communications/scheduling/meeting-types/', payload)
        toast({
          title: 'Meeting Type Created',
          description: 'New meeting type has been created successfully'
        })
      }

      setShowMeetingDialog(false)
      resetForm()
      loadData()
    } catch (error: any) {
      console.error('Failed to save meeting type:', error)
      toast({
        title: 'Failed to save meeting type',
        description: error.response?.data?.error || 'An error occurred',
        variant: 'destructive'
      })
    }
  }

  const handleDeleteMeeting = async (id: string) => {
    if (!confirm('Are you sure you want to delete this meeting type?')) return

    try {
      await api.delete(`/api/v1/communications/scheduling/meeting-types/${id}/`)
      toast({
        title: 'Meeting Type Deleted',
        description: 'Meeting type has been deleted successfully'
      })
      loadData()
    } catch (error: any) {
      toast({
        title: 'Failed to delete meeting type',
        description: error.response?.data?.error || 'An error occurred',
        variant: 'destructive'
      })
    }
  }

  const handleMakeTemplate = async (id: string) => {
    try {
      await api.post(`/api/v1/communications/scheduling/meeting-types/${id}/make_template/`)
      toast({
        title: 'Template Created',
        description: 'Meeting type has been converted to a template'
      })
      loadData()
    } catch (error: any) {
      toast({
        title: 'Failed to create template',
        description: error.response?.data?.error || 'An error occurred',
        variant: 'destructive'
      })
    }
  }

  const handleCreateFromTemplate = async (templateId: string) => {
    try {
      await api.post(`/api/v1/communications/scheduling/meeting-types/${templateId}/copy_from_template/`)
      toast({
        title: 'Meeting Type Created',
        description: 'Meeting type has been created from template'
      })
      setShowTemplateDialog(false)
      loadData()
    } catch (error: any) {
      toast({
        title: 'Failed to create from template',
        description: error.response?.data?.error || 'An error occurred',
        variant: 'destructive'
      })
    }
  }

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      duration_minutes: 30,
      location_type: 'google_meet',
      calendar_id: '',
      calendar_name: '',
      pipeline: '',
      pipeline_stage: '',
      booking_form_config: {
        selected_fields: [],
        stage_field_id: null
      },
      required_fields: [],
      is_active: true,
      allow_rescheduling: true,
      allow_cancellation: true,
      cancellation_notice_hours: 24,
      send_reminders: true,
      reminder_hours: 24
    })
    setEditingMeeting(null)
    // Don't reset calendars - they come from the profile
    setSelectedPipeline(null)
    setStageFields([])
    setSelectedStageField(null)
  }
  

  const openEditDialog = async (meeting: MeetingType) => {
    setEditingMeeting(meeting)
    setFormData({
      name: meeting.name,
      description: meeting.description,
      duration_minutes: meeting.duration_minutes,
      location_type: meeting.location_type,
      calendar_id: meeting.calendar_id || '',
      calendar_name: meeting.calendar_name || '',
      pipeline: meeting.pipeline || '',
      pipeline_stage: meeting.pipeline_stage || '',
      booking_form_config: {
        selected_fields: meeting.booking_form_config?.selected_fields || [],
        stage_field_id: meeting.booking_form_config?.stage_field_id || null
      },
      required_fields: meeting.required_fields || [],
      is_active: meeting.is_active,
      allow_rescheduling: true,
      allow_cancellation: true,
      cancellation_notice_hours: 24,
      send_reminders: true,
      reminder_hours: 24
    })
    
    // Set selected pipeline
    if (meeting.pipeline) {
      const pipeline = pipelines.find(p => p.id === meeting.pipeline)
      setSelectedPipeline(pipeline || null)
    }
    
    // Fetch pipeline fields if pipeline is selected
    if (meeting.pipeline) {
      await loadPipelineFields(meeting.pipeline, meeting)
    }
    
    setShowMeetingDialog(true)
  }

  const copyBookingLink = (meeting: MeetingType) => {
    // Use the booking_url from API if available, otherwise construct it
    let url = meeting.booking_url
    if (!url && user) {
      // Create user slug from first and last name
      const firstName = user.firstName?.toLowerCase().replace(/\s+/g, '-') || ''
      const lastName = user.lastName?.toLowerCase().replace(/\s+/g, '-') || ''
      const userSlug = firstName && lastName ? `${firstName}-${lastName}` : user.username?.toLowerCase()
      url = `${window.location.origin}/book/${userSlug}/${meeting.slug}`
    }
    if (url) {
      navigator.clipboard.writeText(url)
      toast({
        title: 'Link Copied',
        description: 'Booking link has been copied to clipboard'
      })
    }
  }

  const getLocationTypeDisplay = (type: string) => {
    const types: Record<string, string> = {
      'zoom': 'Zoom Meeting',
      'google_meet': 'Google Meet',
      'teams': 'Microsoft Teams',
      'phone': 'Phone Call',
      'in_person': 'In Person',
      'custom': 'Custom Location'
    }
    return types[type] || type
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  // Show message if no calendars are available
  if (!loading && calendars.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Set Up Your Availability First</CardTitle>
          <CardDescription>
            You need to configure your availability settings and connect a calendar before creating meeting types.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Alert>
            <Calendar className="h-4 w-4" />
            <AlertDescription>
              Please go to the Availability tab to:
              1. Connect your Google Calendar or Outlook account
              2. Set your working hours
              3. Configure your scheduling preferences
              
              Once set up, you'll be able to create meeting types here.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Meeting Types Section */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Meeting Types</CardTitle>
              <CardDescription>
                Configure different types of meetings that external contacts can book
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              {templates.length > 0 && (
                <Button variant="outline" onClick={() => setShowTemplateDialog(true)}>
                  <Copy className="h-4 w-4 mr-2" />
                  Use Template
                </Button>
              )}
              <Dialog open={showMeetingDialog} onOpenChange={setShowMeetingDialog}>
                <DialogTrigger asChild>
                  <Button onClick={() => { resetForm(); setShowMeetingDialog(true) }}>
                    <Plus className="h-4 w-4 mr-2" />
                    Add Meeting Type
                  </Button>
                </DialogTrigger>
              <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                  <DialogTitle>
                    {editingMeeting ? 'Edit Meeting Type' : 'Create Meeting Type'}
                  </DialogTitle>
                </DialogHeader>
                
                <div className="space-y-4 mt-4">
                  <div>
                    <Label htmlFor="name">Meeting Name *</Label>
                    <Input
                      id="name"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      placeholder="e.g., 30 Minute Consultation"
                    />
                  </div>

                  <div>
                    <Label htmlFor="description">Description</Label>
                    <Textarea
                      id="description"
                      value={formData.description}
                      onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                      placeholder="Brief description of what this meeting is for"
                      rows={3}
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="duration">Duration (minutes)</Label>
                      <Input
                        id="duration"
                        type="number"
                        value={formData.duration_minutes}
                        onChange={(e) => setFormData({ ...formData, duration_minutes: parseInt(e.target.value) })}
                        min={5}
                        max={480}
                      />
                    </div>

                    <div>
                      <Label htmlFor="location">Location Type</Label>
                      <Select
                        value={formData.location_type}
                        onValueChange={(value) => setFormData({ ...formData, location_type: value })}
                      >
                        <SelectTrigger id="location">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="zoom">Zoom Meeting</SelectItem>
                          <SelectItem value="google_meet">Google Meet</SelectItem>
                          <SelectItem value="teams">Microsoft Teams</SelectItem>
                          <SelectItem value="phone">Phone Call</SelectItem>
                          <SelectItem value="in_person">In Person</SelectItem>
                          <SelectItem value="custom">Custom Location</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>


                  <div>
                    <Label htmlFor="calendar_select">Calendar *</Label>
                    <Select
                      value={formData.calendar_id}
                      onValueChange={(value) => {
                        const calendar = calendars.find(c => c.id === value)
                        setFormData({ 
                          ...formData, 
                          calendar_id: value,
                          calendar_name: calendar?.name || ''
                        })
                      }}
                      disabled={loadingCalendars}
                    >
                      <SelectTrigger id="calendar_select">
                        <SelectValue placeholder={
                          loadingCalendars ? "Loading calendars..." : 
                          "Select a calendar"
                        } />
                      </SelectTrigger>
                      <SelectContent>
                        {(() => {
                          console.log('Rendering calendars dropdown, calendars:', calendars)
                          console.log('Calendars length:', calendars.length)
                          console.log('Loading calendars:', loadingCalendars)
                          
                          if (calendars.length === 0) {
                            return (
                              <SelectItem value="none" disabled>
                                {loadingCalendars ? "Loading..." : "No calendars available"}
                              </SelectItem>
                            )
                          } else {
                            return calendars.map((calendar) => (
                              <SelectItem key={calendar.id} value={calendar.id}>
                                {calendar.name}
                                {calendar.is_default && " (Primary)"}
                              </SelectItem>
                            ))
                          }
                        })()}
                      </SelectContent>
                    </Select>
                    <p className="text-sm text-muted-foreground mt-1">
                      Select which calendar to check for availability
                    </p>
                  </div>

                  <div>
                    <Label htmlFor="pipeline">Pipeline *</Label>
                    <Select
                      value={formData.pipeline || ''}
                      onValueChange={(value) => {
                        const pipeline = pipelines.find(p => p.id === value)
                        setSelectedPipeline(pipeline || null)
                        setFormData({ 
                          ...formData, 
                          pipeline: value,
                          pipeline_stage: '',
                          booking_form_config: { 
                            selected_fields: [],
                            stage_field_id: null
                          }
                        })
                        loadPipelineFields(value)
                        setSelectedStageField(null)
                      }}
                    >
                      <SelectTrigger id="pipeline">
                        <SelectValue placeholder="Select a pipeline (required)" />
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

                  {formData.pipeline && (
                    <>
                      {stageFields.length > 0 && (
                        <div>
                          <Label htmlFor="stage-field">Stage Field</Label>
                          <Select
                            value={selectedStageField?.id || ''}
                            onValueChange={(value) => {
                              const field = stageFields.find(f => f.id === value)
                              console.log('Selected stage field:', field)
                              setSelectedStageField(field || null)
                              // Reset the stage selection when changing stage field
                              setFormData({ 
                                ...formData, 
                                pipeline_stage: '',
                                booking_form_config: {
                                  ...formData.booking_form_config,
                                  stage_field_id: value
                                }
                              })
                            }}
                          >
                            <SelectTrigger id="stage-field">
                              <SelectValue placeholder="Select which field defines stages" />
                            </SelectTrigger>
                            <SelectContent>
                              {stageFields.map((field) => (
                                <SelectItem key={field.id} value={field.id}>
                                  {field.name}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <p className="text-xs text-muted-foreground mt-1">
                            Choose which field represents the stage/status in your pipeline
                          </p>
                        </div>
                      )}

                      {selectedStageField && (
                        <div>
                          <Label htmlFor="stage">Stage</Label>
                          <Select
                            value={formData.pipeline_stage || 'all'}
                            onValueChange={(value) => setFormData({ ...formData, pipeline_stage: value === 'all' ? '' : value })}
                          >
                            <SelectTrigger id="stage">
                              <SelectValue placeholder="Select a stage" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="all">All Stages</SelectItem>
                              {selectedStageField.field_config?.options?.map((option) => (
                                <SelectItem key={option.value} value={option.value}>
                                  {option.label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <p className="text-xs text-muted-foreground mt-1">
                            The selected stage determines which fields are shown on the booking form
                          </p>
                        </div>
                      )}
                    </>
                  )}

                  <div className="space-y-4 border-t pt-4">
                    <h4 className="font-medium">Meeting Settings</h4>
                    
                    <div className="grid gap-4 md:grid-cols-2">
                      <div className="flex items-center justify-between">
                        <Label htmlFor="allow-rescheduling">Allow Rescheduling</Label>
                        <Switch
                          id="allow-rescheduling"
                          checked={formData.allow_rescheduling}
                          onCheckedChange={(checked) => 
                            setFormData({ ...formData, allow_rescheduling: checked })
                          }
                        />
                      </div>

                      <div className="flex items-center justify-between">
                        <Label htmlFor="allow-cancellation">Allow Cancellation</Label>
                        <Switch
                          id="allow-cancellation"
                          checked={formData.allow_cancellation}
                          onCheckedChange={(checked) => 
                            setFormData({ ...formData, allow_cancellation: checked })
                          }
                        />
                      </div>
                    </div>

                    {formData.allow_cancellation && (
                      <div>
                        <Label htmlFor="cancellation-notice">Cancellation Notice (hours)</Label>
                        <Input
                          id="cancellation-notice"
                          type="number"
                          value={formData.cancellation_notice_hours}
                          onChange={(e) => setFormData({ 
                            ...formData, 
                            cancellation_notice_hours: parseInt(e.target.value) || 24 
                          })}
                          min={0}
                          max={168}
                        />
                        <p className="text-xs text-muted-foreground mt-1">
                          Minimum hours before meeting that cancellation is allowed
                        </p>
                      </div>
                    )}

                    <div className="flex items-center justify-between">
                      <Label htmlFor="send-reminders">Send Reminders</Label>
                      <Switch
                        id="send-reminders"
                        checked={formData.send_reminders}
                        onCheckedChange={(checked) => 
                          setFormData({ ...formData, send_reminders: checked })
                        }
                      />
                    </div>

                    {formData.send_reminders && (
                      <div>
                        <Label htmlFor="reminder-hours">Reminder Time (hours before)</Label>
                        <Input
                          id="reminder-hours"
                          type="number"
                          value={formData.reminder_hours}
                          onChange={(e) => setFormData({ 
                            ...formData, 
                            reminder_hours: parseInt(e.target.value) || 24 
                          })}
                          min={1}
                          max={168}
                        />
                        <p className="text-xs text-muted-foreground mt-1">
                          How many hours before the meeting to send reminder
                        </p>
                      </div>
                    )}
                  </div>

                  <div className="flex items-center justify-end space-x-2 pt-4">
                    <Button variant="outline" onClick={() => setShowMeetingDialog(false)}>
                      Cancel
                    </Button>
                    <Button onClick={handleCreateOrUpdateMeeting}>
                      {editingMeeting ? 'Update' : 'Create'} Meeting Type
                    </Button>
                  </div>
                </div>
              </DialogContent>
            </Dialog>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {meetingTypes.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No meeting types configured yet. Create your first meeting type to start accepting bookings.
            </div>
          ) : (
            <div className="space-y-4">
              {meetingTypes.map((meeting) => (
                <div key={meeting.id} className="border rounded-lg p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold">{meeting.name}</h3>
                        <Badge variant={meeting.is_active ? 'default' : 'secondary'}>
                          {meeting.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                        {meeting.total_bookings > 0 && (
                          <Badge variant="outline">
                            {meeting.total_bookings} bookings
                          </Badge>
                        )}
                        {meeting.template_source && (
                          <Badge variant="outline" className="bg-blue-50">
                            From template
                          </Badge>
                        )}
                      </div>
                      
                      {meeting.description && (
                        <p className="text-sm text-muted-foreground mt-1">{meeting.description}</p>
                      )}
                      
                      <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {meeting.duration_minutes} min
                        </span>
                        <span className="flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          {meeting.calendar_name || 'No calendar selected'}
                        </span>
                        <span>{getLocationTypeDisplay(meeting.location_type)}</span>
                      </div>

                      <div className="flex items-center gap-2 mt-3">
                        <div className="flex items-center gap-1 text-sm">
                          <LinkIcon className="h-3 w-3" />
                          <code className="bg-muted px-2 py-1 rounded text-xs">
                            {meeting.booking_url || `/book/${user?.username}/${meeting.slug}`}
                          </code>
                        </div>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => copyBookingLink(meeting)}
                        >
                          <Copy className="h-3 w-3" />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => {
                            let url = meeting.booking_url
                            if (!url && user) {
                              // Create user slug from first and last name
                              const firstName = user.firstName?.toLowerCase().replace(/\s+/g, '-') || ''
                              const lastName = user.lastName?.toLowerCase().replace(/\s+/g, '-') || ''
                              const userSlug = firstName && lastName ? `${firstName}-${lastName}` : user.username?.toLowerCase()
                              url = `${window.location.origin}/book/${userSlug}/${meeting.slug}`
                            }
                            if (url) {
                              window.open(url, '_blank')
                            }
                          }}
                        >
                          <ExternalLink className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      {canManageAll && !meeting.is_template && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleMakeTemplate(meeting.id)}
                          title="Convert to template"
                        >
                          <Copy className="h-4 w-4" />
                        </Button>
                      )}
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => openEditDialog(meeting)}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleDeleteMeeting(meeting.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Scheduling Profile Section */}
      <Card>
        <CardHeader>
          <CardTitle>Scheduling Profiles</CardTitle>
          <CardDescription>
            Configure your availability and scheduling preferences
          </CardDescription>
        </CardHeader>
        <CardContent>
          {profiles.length === 0 ? (
            <Alert>
              <Settings className="h-4 w-4" />
              <AlertDescription>
                No scheduling profile configured. Create a profile to manage your availability settings.
              </AlertDescription>
            </Alert>
          ) : (
            <div className="space-y-4">
              {profiles.map((profile) => (
                <div key={profile.id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">Timezone: {profile.timezone}</p>
                      <p className="text-sm text-muted-foreground">
                        Buffer: {profile.buffer_minutes} min | 
                        Notice: {profile.min_notice_hours} hours | 
                        Advance: {profile.max_advance_days} days
                      </p>
                    </div>
                    <Badge variant={profile.is_active ? 'default' : 'secondary'}>
                      {profile.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Template Selection Dialog */}
      <Dialog open={showTemplateDialog} onOpenChange={setShowTemplateDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Choose a Template</DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4 mt-4">
            {templates.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                No templates available
              </div>
            ) : (
              <ScrollArea className="h-[400px] pr-4">
                <div className="space-y-3">
                  {templates.map((template) => (
                    <div 
                      key={template.id} 
                      className="border rounded-lg p-4 hover:bg-muted/50 cursor-pointer transition-colors"
                      onClick={() => handleCreateFromTemplate(template.id)}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <h3 className="font-semibold">{template.name}</h3>
                          {template.description && (
                            <p className="text-sm text-muted-foreground mt-1">
                              {template.description}
                            </p>
                          )}
                          <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                            <span className="flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              {template.duration_minutes} min
                            </span>
                            <span className="flex items-center gap-1">
                              <Calendar className="h-3 w-3" />
                              {getLocationTypeDisplay(template.location_type)}
                            </span>
                          </div>
                        </div>
                        {template.created_for_org && (
                          <Badge variant="secondary" className="bg-purple-100">
                            Organization
                          </Badge>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            )}
            
            <div className="flex justify-end pt-4 border-t">
              <Button variant="outline" onClick={() => setShowTemplateDialog(false)}>
                Cancel
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}