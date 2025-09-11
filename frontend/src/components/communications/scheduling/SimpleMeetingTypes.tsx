'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Checkbox } from '@/components/ui/checkbox'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Clock, Calendar, Copy, Trash2, Plus } from 'lucide-react'
import { useToast } from '@/hooks/use-toast'
import axios from 'axios'

interface CalendarConnection {
  id: string
  account_name: string
  channel_type: string
}

interface MeetingType {
  id: string
  name: string
  slug: string
  description: string
  duration_minutes: number
  location_type: string
  calendar_connection: string
  calendar_name?: string
  booking_url: string
  is_active: boolean
  pipeline?: string
  pipeline_stage?: string
  booking_form_config?: {
    selected_fields?: string[]
  }
  required_fields?: string[]
  is_template?: boolean
  template_source?: string
  created_for_org?: boolean
}

interface Pipeline {
  id: string
  name: string
  stages?: any[]
}

interface Field {
  id: string
  field_slug: string
  field_name: string
  field_type: string
  is_required: boolean
}

export default function SimpleMeetingTypes() {
  const [meetingTypes, setMeetingTypes] = useState<MeetingType[]>([])
  const [templates, setTemplates] = useState<MeetingType[]>([])
  const [calendars, setCalendars] = useState<CalendarConnection[]>([])
  const [pipelines, setPipelines] = useState<Pipeline[]>([])
  const [pipelineFields, setPipelineFields] = useState<Field[]>([])
  const [selectedFields, setSelectedFields] = useState<string[]>([])
  const [showDialog, setShowDialog] = useState(false)
  const [showTemplateDialog, setShowTemplateDialog] = useState(false)
  const [selectedTemplate, setSelectedTemplate] = useState<MeetingType | null>(null)
  const [loading, setLoading] = useState(false)
  const [hasManageAllPermission, setHasManageAllPermission] = useState(false)
  const { toast } = useToast()
  
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    duration_minutes: 30,
    location_type: 'google_meet',
    calendar_connection: '',
    pipeline: '',
    pipeline_stage: '',
    booking_form_config: {
      selected_fields: [] as string[]
    },
    required_fields: [] as string[]
  })

  useEffect(() => {
    loadMeetingTypes()
    loadTemplates()
    loadCalendars()
    loadPipelines()
    checkPermissions()
  }, [])

  const checkPermissions = async () => {
    try {
      const response = await axios.get('/api/v1/auth/me/')
      const permissions = response.data.permissions || {}
      setHasManageAllPermission(permissions.communication_settings?.scheduling_all === true)
    } catch (error) {
      console.error('Failed to check permissions:', error)
    }
  }

  const loadMeetingTypes = async () => {
    try {
      const response = await axios.get('/api/v1/communications/scheduling/meeting-types/')
      const allTypes = response.data.results || response.data
      // Filter out templates from regular meeting types
      setMeetingTypes(allTypes.filter((mt: MeetingType) => !mt.is_template))
    } catch (error) {
      console.error('Failed to load meeting types:', error)
    }
  }

  const loadTemplates = async () => {
    try {
      const response = await axios.get('/api/v1/communications/scheduling/meeting-types/templates/')
      setTemplates(response.data.results || response.data)
    } catch (error) {
      console.error('Failed to load templates:', error)
    }
  }

  const loadCalendars = async () => {
    try {
      const response = await axios.get('/api/v1/communications/scheduling/meeting-types/calendar_connections/')
      setCalendars(response.data)
    } catch (error) {
      console.error('Failed to load calendars:', error)
    }
  }

  const loadPipelines = async () => {
    try {
      const response = await axios.get('/api/v1/pipelines/')
      setPipelines(response.data.results || response.data)
    } catch (error) {
      console.error('Failed to load pipelines:', error)
    }
  }

  const loadPipelineFields = async (pipelineId: string) => {
    if (!pipelineId) {
      setPipelineFields([])
      return
    }
    
    try {
      const response = await axios.get(`/api/v1/pipelines/${pipelineId}/fields/`)
      const fields = response.data.results || response.data
      setPipelineFields(fields)
    } catch (error) {
      console.error('Failed to load pipeline fields:', error)
    }
  }

  const handleSubmit = async () => {
    if (!formData.name || !formData.calendar_connection || !formData.pipeline) {
      toast({
        title: 'Missing Fields',
        description: 'Name, calendar, and pipeline are required',
        variant: 'destructive'
      })
      return
    }

    setLoading(true)
    try {
      if (selectedTemplate) {
        // Creating from template
        const calendar = calendars.find(c => c.id === formData.calendar_connection)
        await axios.post(`/api/v1/communications/scheduling/meeting-types/${selectedTemplate.id}/copy_from_template/`, {
          name: formData.name,
          calendar_id: formData.calendar_connection,
          calendar_name: calendar?.name || ''
        })
        toast({
          title: 'Success',
          description: 'Meeting type created from template'
        })
      } else {
        // Creating new meeting type
        await axios.post('/api/v1/communications/scheduling/meeting-types/', formData)
        toast({
          title: 'Success',
          description: 'Meeting type created'
        })
      }
      setShowDialog(false)
      resetForm()
      setSelectedTemplate(null)
      loadMeetingTypes()
    } catch (error) {
      toast({
        title: 'Error',
        description: selectedTemplate ? 'Failed to create from template' : 'Failed to create meeting type',
        variant: 'destructive'
      })
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this meeting type?')) return
    
    try {
      await axios.delete(`/api/v1/communications/scheduling/meeting-types/${id}/`)
      toast({ title: 'Deleted' })
      loadMeetingTypes()
      loadTemplates()
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to delete',
        variant: 'destructive'
      })
    }
  }

  const handleMakeTemplate = async (id: string) => {
    try {
      await axios.post(`/api/v1/communications/scheduling/meeting-types/${id}/make_template/`)
      toast({
        title: 'Success',
        description: 'Meeting type converted to template'
      })
      loadMeetingTypes()
      loadTemplates()
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to create template',
        variant: 'destructive'
      })
    }
  }

  const handleCreateFromTemplate = async (templateId: string) => {
    // First, check if user has calendars configured
    if (calendars.length === 0) {
      toast({
        title: 'No Calendar',
        description: 'Please configure your calendar first',
        variant: 'destructive'
      })
      return
    }

    // Set the selected template and open the main dialog to get calendar info
    const template = templates.find(t => t.id === templateId)
    if (!template) return
    
    // Pre-fill form with template data
    setFormData({
      name: template.name,
      description: template.description,
      duration_minutes: template.duration_minutes,
      location_type: template.location_type,
      calendar_connection: calendars[0]?.id || '',
      pipeline: template.pipeline || '',
      pipeline_stage: template.pipeline_stage || '',
      booking_form_config: template.booking_form_config || { selected_fields: [] },
      required_fields: template.required_fields || []
    })
    
    setSelectedTemplate(template)
    setShowTemplateDialog(false)
    setShowDialog(true)
  }

  const copyLink = (url: string) => {
    navigator.clipboard.writeText(url)
    toast({ title: 'Link copied!' })
  }

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      duration_minutes: 30,
      location_type: 'google_meet',
      calendar_connection: '',
      pipeline: '',
      pipeline_stage: '',
      booking_form_config: {
        selected_fields: []
      },
      required_fields: []
    })
    setSelectedFields([])
    setPipelineFields([])
    setSelectedTemplate(null)
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Meeting Types</CardTitle>
            <CardDescription>
              Create different types of meetings people can book with you
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            {templates.length > 0 && (
              <Button variant="outline" onClick={() => setShowTemplateDialog(true)}>
                <Copy className="h-4 w-4 mr-2" />
                Use Template
              </Button>
            )}
            <Button onClick={() => { resetForm(); setShowDialog(true) }}>
              <Plus className="h-4 w-4 mr-2" />
              Add Meeting Type
            </Button>
          </div>
        </div>
      </CardHeader>
      
      <CardContent>
        {meetingTypes.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            No meeting types yet. Create your first one!
          </div>
        ) : (
          <div className="space-y-3">
            {meetingTypes.map((meeting) => (
              <div key={meeting.id} className="border rounded-lg p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold">{meeting.name}</h3>
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
                        {meeting.calendar_name || 'Calendar'}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 mt-3">
                      <code className="text-xs bg-muted px-2 py-1 rounded">
                        {meeting.booking_url}
                      </code>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => copyLink(meeting.booking_url)}
                      >
                        <Copy className="h-3 w-3" />
                      </Button>
                    </div>
                    {meeting.template_source && (
                      <div className="mt-2">
                        <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-blue-100 text-blue-800">
                          Created from template
                        </span>
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {hasManageAllPermission && !meeting.is_template && (
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
                      onClick={() => handleDelete(meeting.id)}
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

      <Dialog open={showDialog} onOpenChange={setShowDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {selectedTemplate ? `Create from Template: ${selectedTemplate.name}` : 'Create Meeting Type'}
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4 mt-4">
            <div>
              <Label>Name</Label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="e.g., 30 Minute Call"
              />
            </div>

            <div>
              <Label>Description (optional)</Label>
              <Input
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Brief description"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Duration</Label>
                <Select
                  value={String(formData.duration_minutes)}
                  onValueChange={(value) => setFormData({ ...formData, duration_minutes: parseInt(value) })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="15">15 minutes</SelectItem>
                    <SelectItem value="30">30 minutes</SelectItem>
                    <SelectItem value="45">45 minutes</SelectItem>
                    <SelectItem value="60">1 hour</SelectItem>
                    <SelectItem value="90">1.5 hours</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label>Location</Label>
                <Select
                  value={formData.location_type}
                  onValueChange={(value) => setFormData({ ...formData, location_type: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="google_meet">Google Meet</SelectItem>
                    <SelectItem value="zoom">Zoom</SelectItem>
                    <SelectItem value="teams">Teams</SelectItem>
                    <SelectItem value="phone">Phone</SelectItem>
                    <SelectItem value="in_person">In Person</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div>
              <Label>Calendar</Label>
              <Select
                value={formData.calendar_connection}
                onValueChange={(value) => setFormData({ ...formData, calendar_connection: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a calendar" />
                </SelectTrigger>
                <SelectContent>
                  {calendars.map((cal) => (
                    <SelectItem key={cal.id} value={cal.id}>
                      {cal.account_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label>Pipeline *</Label>
              <Select
                value={formData.pipeline}
                onValueChange={(value) => {
                  setFormData({ ...formData, pipeline: value, pipeline_stage: '', booking_form_config: { selected_fields: [] } })
                  loadPipelineFields(value)
                  setSelectedFields([])
                }}
              >
                <SelectTrigger>
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

            {formData.pipeline && (
              <>
                <div>
                  <Label>Stage (Optional)</Label>
                  <Input
                    value={formData.pipeline_stage}
                    onChange={(e) => setFormData({ ...formData, pipeline_stage: e.target.value })}
                    placeholder="e.g., New Lead, Qualified"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Leave empty to show all public fields
                  </p>
                </div>

                {pipelineFields.length > 0 && (
                  <div>
                    <Label>Select Fields to Show on Booking Form</Label>
                    <ScrollArea className="h-[200px] border rounded-md p-3 mt-2">
                      <div className="space-y-2">
                        {pipelineFields.map((field) => (
                          <div key={field.id} className="flex items-center space-x-2">
                            <Checkbox
                              id={field.id}
                              checked={selectedFields.includes(field.id)}
                              onCheckedChange={(checked) => {
                                if (checked) {
                                  const newSelected = [...selectedFields, field.id]
                                  setSelectedFields(newSelected)
                                  setFormData({
                                    ...formData,
                                    booking_form_config: {
                                      selected_fields: newSelected
                                    }
                                  })
                                } else {
                                  const newSelected = selectedFields.filter(id => id !== field.id)
                                  setSelectedFields(newSelected)
                                  setFormData({
                                    ...formData,
                                    booking_form_config: {
                                      selected_fields: newSelected
                                    }
                                  })
                                }
                              }}
                            />
                            <label
                              htmlFor={field.id}
                              className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                            >
                              {field.field_name} ({field.field_type})
                              {field.is_required && <span className="text-red-500 ml-1">*</span>}
                            </label>
                          </div>
                        ))}
                      </div>
                    </ScrollArea>
                    <p className="text-xs text-muted-foreground mt-1">
                      Select which fields to show. Leave empty to show all public fields.
                    </p>
                  </div>
                )}
              </>
            )}

            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowDialog(false)}>
                Cancel
              </Button>
              <Button onClick={handleSubmit} disabled={loading}>
                Create
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={showTemplateDialog} onOpenChange={setShowTemplateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Choose a Template</DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4 mt-4">
            {templates.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                No templates available yet
              </div>
            ) : (
              <div className="space-y-3">
                {templates.map((template) => (
                  <div key={template.id} className="border rounded-lg p-4 hover:bg-muted/50 cursor-pointer"
                       onClick={() => handleCreateFromTemplate(template.id)}>
                    <div>
                      <h3 className="font-semibold">{template.name}</h3>
                      {template.description && (
                        <p className="text-sm text-muted-foreground mt-1">{template.description}</p>
                      )}
                      <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {template.duration_minutes} min
                        </span>
                        <span>{template.location_type}</span>
                      </div>
                      {template.created_for_org && (
                        <div className="mt-2">
                          <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-purple-100 text-purple-800">
                            Organization Template
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
            
            <div className="flex justify-end">
              <Button variant="outline" onClick={() => setShowTemplateDialog(false)}>
                Cancel
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </Card>
  )
}