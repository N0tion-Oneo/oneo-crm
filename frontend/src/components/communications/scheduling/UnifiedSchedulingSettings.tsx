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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { 
  Calendar, Clock, Plus, Edit, Trash2, Copy, ExternalLink, Loader2, 
  Settings, Link as LinkIcon, Building, User, Globe, Shield, 
  RefreshCw, Unlink, Users, Filter, Send
} from 'lucide-react'
import { useToast } from '@/hooks/use-toast'
import { useAuth } from '@/features/auth/context'
import { api } from '@/lib/api'
import { format } from 'date-fns'
import FacilitatorMeetingInitiator from './FacilitatorMeetingInitiator'

interface Pipeline {
  id: string
  name: string
  description: string
  pipeline_type: string
}

interface Field {
  id: string
  name: string
  slug: string
  field_type: string
  field_config?: {
    options?: Array<{ label: string; value: string }>
  }
}

interface Calendar {
  id: string
  provider: string
  email: string
  name: string
  is_default: boolean
}

interface MeetingType {
  id: string
  user?: {
    id: string
    email: string
    first_name: string
    last_name: string
    full_name?: string
  }
  name: string
  slug: string
  description?: string
  meeting_mode?: 'direct' | 'facilitator'
  facilitator_settings?: {
    max_time_options?: number
    participant_1_label?: string
    participant_2_label?: string
    include_facilitator?: boolean
    allow_duration_selection?: boolean
    duration_options?: number[]
    allow_location_selection?: boolean
    location_options?: string[]
    link_expiry_hours?: number
  }
  duration_minutes: number
  location_type: string
  location_details?: any
  calendar_id?: string
  calendar_name?: string
  pipeline?: string
  pipeline_name?: string
  pipeline_stage?: string
  booking_form_config?: {
    selected_fields?: string[]
    stage_field_id?: string | null
  }
  custom_questions?: any[]
  required_fields?: string[]
  confirmation_template?: string
  reminder_template?: string
  cancellation_template?: string
  allow_rescheduling?: boolean
  allow_cancellation?: boolean
  cancellation_notice_hours?: number
  send_reminders?: boolean
  reminder_hours?: number | number[]
  is_active: boolean
  is_template: boolean
  template_type?: 'standalone' | 'centralized'
  template_source?: string
  template_source_name?: string
  is_synced_to_template?: boolean
  created_for_org?: boolean
  last_synced_at?: string
  total_bookings?: number
  booking_url?: string
  has_scheduling_profile?: boolean
  created_at?: string
  updated_at?: string
}

interface UnifiedSchedulingSettingsProps {
  canManageAll?: boolean
}

export function UnifiedSchedulingSettings({ canManageAll = false }: UnifiedSchedulingSettingsProps) {
  // State management
  const [meetingTypes, setMeetingTypes] = useState<MeetingType[]>([])
  const [templates, setTemplates] = useState<MeetingType[]>([])
  const [calendars, setCalendars] = useState<Calendar[]>([])
  const [loadingCalendars, setLoadingCalendars] = useState(false)
  const [pipelines, setPipelines] = useState<Pipeline[]>([])
  const [selectedPipeline, setSelectedPipeline] = useState<Pipeline | null>(null)
  const [pipelineFields, setPipelineFields] = useState<Field[]>([])
  const [stageFields, setStageFields] = useState<Field[]>([])
  const [selectedStageField, setSelectedStageField] = useState<Field | null>(null)
  const [loading, setLoading] = useState(true)
  const [showFacilitatorDialog, setShowFacilitatorDialog] = useState(false)
  const [facilitatorMeetingType, setFacilitatorMeetingType] = useState<MeetingType | null>(null)
  const [viewMode, setViewMode] = useState<'all' | 'meeting-types' | 'templates'>('all')
  
  // Dialog states
  const [showMeetingDialog, setShowMeetingDialog] = useState(false)
  const [showTemplateDialog, setShowTemplateDialog] = useState(false)
  const [editingMeeting, setEditingMeeting] = useState<MeetingType | null>(null)
  const [creatingTemplate, setCreatingTemplate] = useState(false)
  
  const { toast } = useToast()
  const { user } = useAuth()
  
  // Form state for meeting type/template
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    meeting_mode: 'direct' as 'direct' | 'facilitator',
    facilitator_settings: {
      max_time_options: 3,
      participant_1_label: 'First Participant',
      participant_2_label: 'Second Participant',
      include_facilitator: true,
      allow_duration_selection: true,
      duration_options: [30, 60, 90],
      allow_location_selection: true,
      location_options: ['google_meet', 'teams', 'in_person'],
      link_expiry_hours: 72
    },
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
    reminder_hours: 24,
    is_template: false,
    template_type: 'standalone' as 'standalone' | 'centralized',
    created_for_org: true
  })

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [meetingTypesRes, templatesRes, pipelinesRes] = await Promise.all([
        api.get('/api/v1/communications/scheduling/meeting-types/'),
        api.get('/api/v1/communications/scheduling/meeting-types/templates/'),
        api.get('/api/v1/pipelines/')
      ])
      
      const allMeetingTypes = meetingTypesRes.data.results || meetingTypesRes.data || []
      const allTemplates = templatesRes.data.results || templatesRes.data || []
      
      setMeetingTypes(allMeetingTypes.filter((mt: MeetingType) => !mt.is_template))
      setTemplates(allTemplates)
      setPipelines(pipelinesRes.data.results || pipelinesRes.data || [])
      
      // Load calendars
      await loadCalendars()
    } catch (error) {
      console.error('Failed to load data:', error)
      toast({
        title: 'Failed to load meeting types',
        description: 'An error occurred while loading data',
        variant: 'destructive'
      })
    } finally {
      setLoading(false)
    }
  }

  const loadCalendars = async () => {
    setLoadingCalendars(true)
    try {
      const response = await api.get('/api/v1/communications/scheduling/meeting-types/calendars_for_connection/')
      // The API returns {calendars: [...]}
      const calendarsData = response.data.calendars || response.data.results || response.data || []
      setCalendars(Array.isArray(calendarsData) ? calendarsData : [])
    } catch (error: any) {
      // Don't show error if user hasn't set up scheduling profile yet (400 error)
      if (error.response?.status !== 400) {
        console.error('Failed to load calendars:', error)
      }
      // Set empty calendars array so the UI can still function
      setCalendars([])
    } finally {
      setLoadingCalendars(false)
    }
  }

  const loadPipelineFields = async (pipelineId: string, preserveStageValue?: boolean, stageFieldId?: string) => {
    if (!pipelineId) {
      setPipelineFields([])
      setStageFields([])
      setSelectedStageField(null)
      return
    }

    try {
      const response = await api.get(`/api/v1/pipelines/${pipelineId}/fields/`)
      const fields = response.data.results || response.data || []
      setPipelineFields(fields)
      
      // Filter for select/multiselect fields that could be stages
      const selectFields = fields.filter((f: Field) => 
        f.field_type === 'select' || f.field_type === 'multiselect'
      )
      setStageFields(selectFields)
      
      // If a specific stage field ID was provided, use that
      if (stageFieldId) {
        const specifiedField = selectFields.find((f: Field) => f.id === stageFieldId)
        if (specifiedField) {
          setSelectedStageField(specifiedField)
        }
      } else {
        // Try to auto-select a stage field if one exists
        const defaultStageField = selectFields.find((f: Field) => 
          f.slug === 'stage' || f.slug === 'status' || 
          (f.name && (f.name.toLowerCase().includes('stage') || f.name.toLowerCase().includes('status')))
        )
        if (defaultStageField) {
          setSelectedStageField(defaultStageField)
        }
      }
      
      // If we're not preserving, reset the stage value
      if (!preserveStageValue && !selectedStageField) {
        setFormData(prev => ({ ...prev, pipeline_stage: '' }))
      }
    } catch (error) {
      console.error('Failed to load pipeline fields:', error)
    }
  }

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      toast({
        title: 'Copied!',
        description: 'Link copied to clipboard',
      })
    } catch (err) {
      toast({
        title: 'Failed to copy',
        description: 'Please try again',
        variant: 'destructive',
      })
    }
  }

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      meeting_mode: 'direct' as 'direct' | 'facilitator',
      facilitator_settings: {
        max_time_options: 3,
        participant_1_label: 'First Participant',
        participant_2_label: 'Second Participant',
        include_facilitator: true,
        allow_duration_selection: true,
        duration_options: [30, 60, 90],
        allow_location_selection: true,
        location_options: ['google_meet', 'teams', 'in_person'],
        link_expiry_hours: 72
      },
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
      reminder_hours: 24,
      is_template: false,
      template_type: 'standalone',
      created_for_org: true
    })
    setEditingMeeting(null)
    setCreatingTemplate(false)
    setSelectedPipeline(null)
    setStageFields([])
    setSelectedStageField(null)
  }

  const openEditDialog = async (meeting: MeetingType) => {
    setEditingMeeting(meeting)
    setCreatingTemplate(meeting.is_template)
    setFormData({
      name: meeting.name,
      description: meeting.description || '',
      meeting_mode: meeting.meeting_mode || 'direct',
      facilitator_settings: meeting.facilitator_settings || {
        max_time_options: 3,
        participant_1_label: 'First Participant',
        participant_2_label: 'Second Participant',
        include_facilitator: true,
        allow_duration_selection: true,
        duration_options: [30, 60, 90],
        allow_location_selection: true,
        location_options: ['google_meet', 'teams', 'in_person'],
        link_expiry_hours: 72
      },
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
      allow_rescheduling: meeting.allow_rescheduling ?? true,
      allow_cancellation: meeting.allow_cancellation ?? true,
      cancellation_notice_hours: meeting.cancellation_notice_hours ?? 24,
      send_reminders: meeting.send_reminders ?? true,
      reminder_hours: Array.isArray(meeting.reminder_hours) ? meeting.reminder_hours[0] : (meeting.reminder_hours ?? 24),
      is_template: meeting.is_template,
      template_type: meeting.template_type || 'standalone',
      created_for_org: meeting.created_for_org ?? true
    })
    
    // Set selected pipeline
    if (meeting.pipeline) {
      const pipeline = pipelines.find(p => p.id === meeting.pipeline)
      setSelectedPipeline(pipeline || null)
      await loadPipelineFields(
        meeting.pipeline, 
        true, 
        meeting.booking_form_config?.stage_field_id || undefined
      )
    }
    
    setShowMeetingDialog(true)
  }

  const handleCreateOrUpdateMeeting = async () => {
    try {
      // Validation
      if (!formData.name) {
        toast({
          title: 'Missing Required Fields',
          description: 'Please provide a name',
          variant: 'destructive'
        })
        return
      }

      // For regular meeting types, calendar is required
      if (!formData.is_template && !formData.calendar_id) {
        toast({
          title: 'Missing Required Fields',
          description: 'Please select a calendar',
          variant: 'destructive'
        })
        return
      }

      const payload = {
        ...formData,
        user: formData.is_template ? null : user?.id,
        slug: formData.name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, ''),
        location_details: {},
        booking_form_config: {
          ...formData.booking_form_config,
          stage_field_id: selectedStageField?.id || null
        },
        custom_questions: [],
        reminder_hours: formData.is_template || formData.send_reminders ? [formData.reminder_hours] : []
      }

      if (editingMeeting) {
        await api.patch(`/api/v1/communications/scheduling/meeting-types/${editingMeeting.id}/`, payload)
        toast({
          title: formData.is_template ? 'Template Updated' : 'Meeting Type Updated',
          description: `${formData.is_template ? 'Template' : 'Meeting type'} has been updated successfully`
        })
      } else {
        await api.post('/api/v1/communications/scheduling/meeting-types/', payload)
        toast({
          title: formData.is_template ? 'Template Created' : 'Meeting Type Created',
          description: `New ${formData.is_template ? 'template' : 'meeting type'} has been created successfully`
        })
      }

      setShowMeetingDialog(false)
      resetForm()
      loadData()
    } catch (error: any) {
      console.error('Failed to save:', error)
      const errorMessage = error.response?.data?.detail || 
                          error.response?.data?.error || 
                          (typeof error.response?.data === 'object' ? JSON.stringify(error.response?.data) : error.response?.data) ||
                          'An error occurred'
      toast({
        title: `Failed to save ${formData.is_template ? 'template' : 'meeting type'}`,
        description: errorMessage,
        variant: 'destructive'
      })
    }
  }

  const handleInitiateFacilitatorMeeting = (meetingType: MeetingType) => {
    setFacilitatorMeetingType(meetingType)
    setShowFacilitatorDialog(true)
  }

  const handleDeleteMeeting = async (id: string, isTemplate: boolean) => {
    if (!confirm(`Are you sure you want to delete this ${isTemplate ? 'template' : 'meeting type'}?`)) return

    try {
      await api.delete(`/api/v1/communications/scheduling/meeting-types/${id}/`)
      toast({
        title: `${isTemplate ? 'Template' : 'Meeting Type'} Deleted`,
        description: `${isTemplate ? 'Template' : 'Meeting type'} has been deleted successfully`
      })
      loadData()
    } catch (error: any) {
      toast({
        title: `Failed to delete ${isTemplate ? 'template' : 'meeting type'}`,
        description: error.response?.data?.error || 'An error occurred',
        variant: 'destructive'
      })
    }
  }

  const handleMakeTemplate = async (id: string) => {
    try {
      await api.post(`/api/v1/communications/scheduling/meeting-types/${id}/make_template/`, {
        template_type: 'standalone',
        created_for_org: true
      })
      toast({
        title: 'Template Created',
        description: 'Meeting type has been converted to a template'
      })
      loadData()
    } catch (error: any) {
      toast({
        title: 'Failed to create template',
        description: error.response?.data?.error || 'Only administrators can create templates',
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

  // Display items based on view mode - templates and meeting types are separate
  const getFilteredItems = () => {
    return viewMode === 'templates' ? templates : meetingTypes
  }

  const filteredItems = getFilteredItems()

  return (
    <>
      <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Meeting Types & Templates</CardTitle>
            <CardDescription>
              Manage your meeting types and organization templates
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            {/* Create Button - Only show template creation for admins */}
            {(viewMode === 'meeting-types' || canManageAll) && (
              <Dialog open={showMeetingDialog} onOpenChange={setShowMeetingDialog}>
                <DialogTrigger asChild>
                  <Button onClick={() => { 
                  resetForm()
                  setCreatingTemplate(viewMode === 'templates')
                  setShowMeetingDialog(true) 
                }}>
                  <Plus className="h-4 w-4 mr-2" />
                  {viewMode === 'templates' ? 'Create Template' : 'Create Meeting Type'}
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                  <DialogTitle>
                    {editingMeeting 
                      ? `Edit ${editingMeeting.is_template ? 'Template' : 'Meeting Type'}` 
                      : `Create ${creatingTemplate ? 'Template' : 'Meeting Type'}`}
                  </DialogTitle>
                </DialogHeader>
                
                <div className="space-y-4 mt-4">
                  {/* Creation Type Toggle for new items */}
                  {!editingMeeting && canManageAll && (
                    <div className="flex items-center justify-between p-4 border rounded-lg">
                      <div>
                        <Label>Create as Template</Label>
                        <p className="text-sm text-muted-foreground">
                          Templates can be used by all users in your organization
                        </p>
                      </div>
                      <Switch
                        checked={creatingTemplate}
                        onCheckedChange={(checked) => {
                          setCreatingTemplate(checked)
                          setFormData({ ...formData, is_template: checked })
                        }}
                      />
                    </div>
                  )}

                  {/* Basic Information */}
                  <div>
                    <Label htmlFor="name">Name *</Label>
                    <Input
                      id="name"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      placeholder="e.g., 30-minute consultation"
                    />
                  </div>

                  <div>
                    <Label htmlFor="description">Description</Label>
                    <Textarea
                      id="description"
                      value={formData.description}
                      onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                      placeholder="Brief description of this meeting type"
                      rows={3}
                    />
                  </div>

                  <div>
                    <Label htmlFor="meeting_mode">Meeting Mode</Label>
                    <Select
                      value={formData.meeting_mode}
                      onValueChange={(value: 'direct' | 'facilitator') => 
                        setFormData({ ...formData, meeting_mode: value })
                      }
                    >
                      <SelectTrigger id="meeting_mode">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="direct">
                          <div className="flex flex-col">
                            <span>Direct Meeting</span>
                            <span className="text-xs text-muted-foreground">Regular 1-on-1 booking</span>
                          </div>
                        </SelectItem>
                        <SelectItem value="facilitator">
                          <div className="flex flex-col">
                            <span>Facilitator Meeting</span>
                            <span className="text-xs text-muted-foreground">Coordinate between two participants</span>
                          </div>
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {formData.meeting_mode === 'facilitator' && (
                    <div className="space-y-4 p-4 border rounded-lg bg-muted/30">
                      <h4 className="font-medium">Facilitator Settings</h4>
                      
                      <div className="grid gap-4 md:grid-cols-2">
                        <div>
                          <Label htmlFor="participant_1_label">Participant 1 Label</Label>
                          <Input
                            id="participant_1_label"
                            value={formData.facilitator_settings.participant_1_label}
                            onChange={(e) => setFormData({
                              ...formData,
                              facilitator_settings: {
                                ...formData.facilitator_settings,
                                participant_1_label: e.target.value
                              }
                            })}
                            placeholder="e.g., Candidate, Client"
                          />
                        </div>
                        <div>
                          <Label htmlFor="participant_2_label">Participant 2 Label</Label>
                          <Input
                            id="participant_2_label"
                            value={formData.facilitator_settings.participant_2_label}
                            onChange={(e) => setFormData({
                              ...formData,
                              facilitator_settings: {
                                ...formData.facilitator_settings,
                                participant_2_label: e.target.value
                              }
                            })}
                            placeholder="e.g., Interviewer, Partner"
                          />
                        </div>
                      </div>

                      <div>
                        <Label htmlFor="max_time_options">Maximum Time Options for Participant 1</Label>
                        <Select
                          value={String(formData.facilitator_settings.max_time_options)}
                          onValueChange={(value) => setFormData({
                            ...formData,
                            facilitator_settings: {
                              ...formData.facilitator_settings,
                              max_time_options: parseInt(value)
                            }
                          })}
                        >
                          <SelectTrigger id="max_time_options">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {[1, 2, 3, 4, 5].map(num => (
                              <SelectItem key={num} value={String(num)}>
                                {num} time slot{num > 1 ? 's' : ''}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="space-y-4">
                        <div className="flex items-center justify-between">
                          <div className="space-y-0.5">
                            <Label>Include Facilitator in Meeting</Label>
                            <p className="text-sm text-muted-foreground">
                              Add yourself as a meeting participant. When disabled, you can coordinate multiple meetings simultaneously.
                            </p>
                          </div>
                          <Switch
                            checked={formData.facilitator_settings.include_facilitator}
                            onCheckedChange={(checked) => setFormData({
                              ...formData,
                              facilitator_settings: {
                                ...formData.facilitator_settings,
                                include_facilitator: checked
                              }
                            })}
                          />
                        </div>

                        <div className="flex items-center justify-between">
                          <div className="space-y-0.5">
                            <Label>Allow Duration Selection</Label>
                            <p className="text-sm text-muted-foreground">
                              Let Participant 1 choose meeting duration
                            </p>
                          </div>
                          <Switch
                            checked={formData.facilitator_settings.allow_duration_selection}
                            onCheckedChange={(checked) => setFormData({
                              ...formData,
                              facilitator_settings: {
                                ...formData.facilitator_settings,
                                allow_duration_selection: checked
                              }
                            })}
                          />
                        </div>

                        <div className="flex items-center justify-between">
                          <div className="space-y-0.5">
                            <Label>Allow Location Selection</Label>
                            <p className="text-sm text-muted-foreground">
                              Let Participant 1 choose meeting location
                            </p>
                          </div>
                          <Switch
                            checked={formData.facilitator_settings.allow_location_selection}
                            onCheckedChange={(checked) => setFormData({
                              ...formData,
                              facilitator_settings: {
                                ...formData.facilitator_settings,
                                allow_location_selection: checked
                              }
                            })}
                          />
                        </div>
                      </div>
                    </div>
                  )}

                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <Label htmlFor="duration">Duration</Label>
                      <Select
                        value={formData.duration_minutes.toString()}
                        onValueChange={(value) => setFormData({ ...formData, duration_minutes: parseInt(value) })}
                      >
                        <SelectTrigger id="duration">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="15">15 minutes</SelectItem>
                          <SelectItem value="30">30 minutes</SelectItem>
                          <SelectItem value="45">45 minutes</SelectItem>
                          <SelectItem value="60">1 hour</SelectItem>
                          <SelectItem value="90">1.5 hours</SelectItem>
                          <SelectItem value="120">2 hours</SelectItem>
                        </SelectContent>
                      </Select>
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

                  {/* Calendar Selection - Only for non-templates */}
                  {!formData.is_template && (
                    <div>
                      <Label htmlFor="calendar">Calendar *</Label>
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
                      >
                        <SelectTrigger id="calendar">
                          <SelectValue placeholder="Select a calendar (required)" />
                        </SelectTrigger>
                        <SelectContent>
                          {calendars.length === 0 ? (
                            <SelectItem value="none" disabled>
                              {loadingCalendars ? "Loading..." : "No calendars available"}
                            </SelectItem>
                          ) : (
                            calendars.map((calendar) => (
                              <SelectItem key={calendar.id} value={calendar.id}>
                                {calendar.name}
                                {calendar.is_default && " (Primary)"}
                              </SelectItem>
                            ))
                          )}
                        </SelectContent>
                      </Select>
                    </div>
                  )}

                  {/* Pipeline Selection */}
                  <div>
                    <Label htmlFor="pipeline">Pipeline</Label>
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
                        <SelectValue placeholder="Select a pipeline" />
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

                  {/* Stage Field Selection */}
                  {formData.pipeline && stageFields.length > 0 && (
                    <>
                      <div>
                        <Label htmlFor="stage-field">Stage Field</Label>
                        <Select
                          value={selectedStageField?.id || ''}
                          onValueChange={(value) => {
                            const field = stageFields.find(f => f.id === value)
                            setSelectedStageField(field || null)
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
                      </div>

                      {selectedStageField && (
                        <div>
                          <Label htmlFor="stage">Pipeline Stage</Label>
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
                        </div>
                      )}
                    </>
                  )}

                  {/* Meeting Settings */}
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
                          value={formData.cancellation_notice_hours || 24}
                          onChange={(e) => setFormData({ 
                            ...formData, 
                            cancellation_notice_hours: parseInt(e.target.value) || 24 
                          })}
                          min={0}
                          max={168}
                        />
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
                          value={formData.reminder_hours || 24}
                          onChange={(e) => setFormData({ 
                            ...formData, 
                            reminder_hours: parseInt(e.target.value) || 24 
                          })}
                          min={1}
                          max={168}
                        />
                      </div>
                    )}
                  </div>

                  {/* Template Configuration - Only for templates */}
                  {formData.is_template && (
                    <div className="space-y-4 border-t pt-4">
                      <h4 className="font-medium">Template Configuration</h4>
                      
                      <div>
                        <Label>Template Type</Label>
                        <Select
                          value={formData.template_type}
                          onValueChange={(value: 'standalone' | 'centralized') => 
                            setFormData({ ...formData, template_type: value })
                          }
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="standalone">Standalone - One-time copy</SelectItem>
                            <SelectItem value="centralized">Centralized - Stays synced</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                          <Label>Organization-wide</Label>
                          <p className="text-sm text-muted-foreground">
                            Make this template available to all users
                          </p>
                        </div>
                        <Switch
                          checked={formData.created_for_org}
                          onCheckedChange={(checked) => 
                            setFormData({ ...formData, created_for_org: checked })
                          }
                        />
                      </div>
                    </div>
                  )}

                  <div className="flex items-center justify-end space-x-2 pt-4">
                    <Button variant="outline" onClick={() => setShowMeetingDialog(false)}>
                      Cancel
                    </Button>
                    <Button onClick={handleCreateOrUpdateMeeting}>
                      {editingMeeting ? 'Update' : 'Create'} {formData.is_template ? 'Template' : 'Meeting Type'}
                    </Button>
                  </div>
                </div>
              </DialogContent>
            </Dialog>
            )}
            
            {/* View Mode Toggle */}
            <ToggleGroup type="single" value={viewMode} onValueChange={(value) => value && setViewMode(value as any)}>
              <ToggleGroupItem value="meeting-types" aria-label="Show meeting types">
                <Calendar className="h-4 w-4 mr-2" />
                Meeting Types
              </ToggleGroupItem>
              <ToggleGroupItem value="templates" aria-label="Show templates">
                <Globe className="h-4 w-4 mr-2" />
                Templates
              </ToggleGroupItem>
            </ToggleGroup>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin" />
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground">
            {viewMode === 'templates' 
              ? "No templates available. Create your first template to share with your organization."
              : viewMode === 'meeting-types'
              ? "No meeting types configured yet. Create your first meeting type to start accepting bookings."
              : "No meeting types or templates configured yet."}
          </div>
        ) : (
          <div className="space-y-4">
            {filteredItems.map((item) => (
              <div key={item.id} className="border rounded-lg p-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold">{item.name}</h3>
                      {item.is_template ? (
                        <>
                          <Badge variant="outline">
                            <Globe className="h-3 w-3 mr-1" />
                            Template
                          </Badge>
                          <Badge variant={item.template_type === 'centralized' ? 'default' : 'secondary'}>
                            {item.template_type === 'centralized' ? 'Centralized' : 'Standalone'}
                          </Badge>
                        </>
                      ) : (
                        <>
                          <Badge variant={item.is_active ? 'default' : 'secondary'}>
                            {item.is_active ? 'Active' : 'Inactive'}
                          </Badge>
                          {item.meeting_mode === 'facilitator' && (
                            <Badge variant="outline" className="bg-purple-50 text-purple-700 border-purple-300">
                              <Users className="h-3 w-3 mr-1" />
                              Facilitator
                            </Badge>
                          )}
                          {item.is_synced_to_template && (
                            <Badge variant="outline">
                              <LinkIcon className="h-3 w-3 mr-1" />
                              Synced
                            </Badge>
                          )}
                        </>
                      )}
                    </div>
                    {item.description && (
                      <p className="text-sm text-muted-foreground mt-1">{item.description}</p>
                    )}
                    <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {item.duration_minutes} minutes
                      </span>
                      <span>{getLocationTypeDisplay(item.location_type)}</span>
                      {item.pipeline_name && <span>Pipeline: {item.pipeline_name}</span>}
                      {!item.is_template && item.total_bookings !== undefined && (
                        <span>{item.total_bookings} bookings</span>
                      )}
                    </div>
                    
                    {/* Additional info rows */}
                    <div className="space-y-1 mt-2">
                      {/* First row: User and template source */}
                      <div className="flex items-center gap-4 text-sm">
                        {/* Show user for meeting types */}
                        {!item.is_template && item.user && (
                          <span className="text-muted-foreground">
                            <span className="font-medium">User:</span> {item.user.full_name || item.user.email}
                          </span>
                        )}
                        
                        {/* Show template source for synced meeting types */}
                        {item.is_synced_to_template && item.template_source_name && (
                          <span className="text-muted-foreground">
                            <span className="font-medium">From template:</span> {item.template_source_name}
                          </span>
                        )}
                      </div>
                      
                      {/* Second row: Booking URL */}
                      {!item.is_template && item.booking_url && (
                        <div className="flex items-center gap-1 text-sm">
                          <span className="font-medium text-muted-foreground">Link:</span>
                          <button
                            onClick={() => copyToClipboard(item.booking_url)}
                            className="text-blue-600 dark:text-blue-400 hover:underline truncate max-w-md"
                            title="Click to copy"
                          >
                            {item.booking_url}
                          </button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => copyToClipboard(item.booking_url)}
                            className="h-6 w-6 p-0"
                          >
                            <Copy className="h-3 w-3" />
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    {/* Use Template Button */}
                    {item.is_template && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleCreateFromTemplate(item.id)}
                      >
                        <Copy className="h-4 w-4" />
                      </Button>
                    )}
                    
                    {/* Make Template Button (admin only, for non-templates) */}
                    {canManageAll && !item.is_template && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleMakeTemplate(item.id)}
                      >
                        <Globe className="h-4 w-4" />
                      </Button>
                    )}
                    
                    {/* Edit Button - Only show for templates if user has permission */}
                    {(!item.is_template || canManageAll) && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => openEditDialog(item)}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                    )}
                    
                    {/* Delete Button - Only show for templates if user has permission */}
                    {(!item.is_template || canManageAll) && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleDeleteMeeting(item.id, item.is_template)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                    
                    {/* View Link Button (for non-templates) */}
                    {!item.is_template && item.booking_url && (
                      item.meeting_mode === 'facilitator' ? (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleInitiateFacilitatorMeeting(item)}
                          title="Initiate Facilitator Meeting"
                        >
                          <Send className="h-4 w-4" />
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => window.open(item.booking_url, '_blank')}
                        >
                          <ExternalLink className="h-4 w-4" />
                        </Button>
                      )
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
    
    {/* Facilitator Meeting Initiator Dialog */}
    <Dialog open={showFacilitatorDialog} onOpenChange={setShowFacilitatorDialog}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Initiate Facilitator Meeting</DialogTitle>
        </DialogHeader>
        {facilitatorMeetingType && (
          <FacilitatorMeetingInitiator
            meetingTypeId={facilitatorMeetingType.id}
            pipelineId={facilitatorMeetingType.pipeline}
            meetingType={facilitatorMeetingType}
            onClose={() => {
              setShowFacilitatorDialog(false)
              setFacilitatorMeetingType(null)
            }}
          />
        )}
      </DialogContent>
    </Dialog>
    </>
  )
}