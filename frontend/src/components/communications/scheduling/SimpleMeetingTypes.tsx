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
  const [calendars, setCalendars] = useState<CalendarConnection[]>([])
  const [pipelines, setPipelines] = useState<Pipeline[]>([])
  const [pipelineFields, setPipelineFields] = useState<Field[]>([])
  const [selectedFields, setSelectedFields] = useState<string[]>([])
  const [showDialog, setShowDialog] = useState(false)
  const [loading, setLoading] = useState(false)
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
    loadCalendars()
    loadPipelines()
  }, [])

  const loadMeetingTypes = async () => {
    try {
      const response = await axios.get('/api/v1/communications/scheduling/meeting-types/')
      setMeetingTypes(response.data.results || response.data)
    } catch (error) {
      console.error('Failed to load meeting types:', error)
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
      await axios.post('/api/v1/communications/scheduling/meeting-types/', formData)
      toast({
        title: 'Success',
        description: 'Meeting type created'
      })
      setShowDialog(false)
      resetForm()
      loadMeetingTypes()
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to create meeting type',
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
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to delete',
        variant: 'destructive'
      })
    }
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
          <Button onClick={() => { resetForm(); setShowDialog(true) }}>
            <Plus className="h-4 w-4 mr-2" />
            Add Meeting Type
          </Button>
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
                  </div>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleDelete(meeting.id)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>

      <Dialog open={showDialog} onOpenChange={setShowDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Meeting Type</DialogTitle>
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
    </Card>
  )
}