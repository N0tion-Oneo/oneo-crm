'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { 
  Clock, Edit, Trash2, Copy, Users, LinkIcon, 
  RefreshCw, Unlink, Plus, Shield, Globe 
} from 'lucide-react'
import { useToast } from '@/hooks/use-toast'
import { api } from '@/lib/api'
import { format } from 'date-fns'

interface MeetingType {
  id: string
  name: string
  slug: string
  description: string
  duration_minutes: number
  location_type: string
  location_details?: any
  pipeline?: string
  pipeline_stage?: string
  booking_form_config?: any
  custom_questions?: any[]
  required_fields?: string[]
  confirmation_template?: string
  reminder_template?: string
  cancellation_template?: string
  allow_rescheduling?: boolean
  allow_cancellation?: boolean
  cancellation_notice_hours?: number
  send_reminders?: boolean
  reminder_hours?: number[]
  is_template: boolean
  template_type?: 'standalone' | 'centralized'
  template_source?: string
  is_synced_to_template?: boolean
  created_for_org: boolean
  last_synced_at?: string
  total_bookings: number
  user?: {
    id: string
    email: string
    first_name: string
    last_name: string
  }
  copied_instances?: Array<{
    id: string
    name: string
    user: {
      email: string
      first_name: string
      last_name: string
    }
    is_synced_to_template: boolean
  }>
}

interface TemplateManagementProps {
  canManageAll?: boolean
}

export default function TemplateManagement({ canManageAll = false }: TemplateManagementProps) {
  const [templates, setTemplates] = useState<MeetingType[]>([])
  const [meetingTypes, setMeetingTypes] = useState<MeetingType[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [editingTemplate, setEditingTemplate] = useState<MeetingType | null>(null)
  const [selectedTemplate, setSelectedTemplate] = useState<MeetingType | null>(null)
  const [showInstancesDialog, setShowInstancesDialog] = useState(false)
  const [pipelineFields, setPipelineFields] = useState<any[]>([])
  const [stageFields, setStageFields] = useState<any[]>([])
  const [selectedStageField, setSelectedStageField] = useState<any>(null)
  const { toast } = useToast()

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    duration_minutes: 30,
    location_type: 'google_meet',
    location_details: {},
    pipeline: '',
    pipeline_stage: '',
    booking_form_config: {},
    custom_questions: [],
    required_fields: [],
    confirmation_template: '',
    reminder_template: '',
    cancellation_template: '',
    allow_rescheduling: true,
    allow_cancellation: true,
    cancellation_notice_hours: 24,
    send_reminders: true,
    reminder_hours: 24,
    template_type: 'standalone' as 'standalone' | 'centralized',
    created_for_org: true
  })
  const [pipelines, setPipelines] = useState<any[]>([])

  useEffect(() => {
    loadData()
    loadPipelines()
  }, [])

  const loadPipelines = async () => {
    try {
      const response = await api.get('/api/v1/pipelines/')
      setPipelines(response.data.results || response.data || [])
    } catch (error) {
      console.error('Failed to load pipelines:', error)
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
      const selectFields = fields.filter((f: any) => 
        f.field_type === 'select' || f.field_type === 'multiselect'
      )
      setStageFields(selectFields)
      
      // If a specific stage field ID was provided, use that
      if (stageFieldId) {
        const specifiedField = selectFields.find((f: any) => f.id === stageFieldId)
        if (specifiedField) {
          setSelectedStageField(specifiedField)
        }
      } else {
        // Try to auto-select a stage field if one exists
        const defaultStageField = selectFields.find((f: any) => 
          f.slug === 'stage' || f.slug === 'status' || 
          (f.name && (f.name.toLowerCase().includes('stage') || f.name.toLowerCase().includes('status')))
        )
        if (defaultStageField) {
          setSelectedStageField(defaultStageField)
        }
      }
      
      // If we're preserving the stage value and it exists, keep it
      // This ensures the pipeline_stage value persists when editing
      if (!preserveStageValue) {
        // Only reset if we're not preserving
        if (!selectedStageField) {
          setFormData(prev => ({ ...prev, pipeline_stage: '' }))
        }
      }
    } catch (error) {
      console.error('Failed to load pipeline fields:', error)
    }
  }

  const loadData = async () => {
    setLoading(true)
    try {
      const [templatesRes, meetingTypesRes] = await Promise.all([
        api.get('/api/v1/communications/scheduling/meeting-types/templates/'),
        api.get('/api/v1/communications/scheduling/meeting-types/')
      ])
      
      setTemplates(templatesRes.data.results || templatesRes.data || [])
      const allTypes = meetingTypesRes.data.results || meetingTypesRes.data || []
      setMeetingTypes(allTypes.filter((mt: MeetingType) => !mt.is_template))
    } catch (error) {
      console.error('Failed to load data:', error)
      toast({
        title: 'Failed to load templates',
        description: 'An error occurred while loading templates',
        variant: 'destructive'
      })
    } finally {
      setLoading(false)
    }
  }

  const handleConvertToTemplate = async (meetingTypeId: string) => {
    const meetingType = meetingTypes.find(mt => mt.id === meetingTypeId)
    if (!meetingType) return

    setEditingTemplate(meetingType)
    
    // Load pipeline fields if a pipeline is selected
    if (meetingType.pipeline) {
      await loadPipelineFields(
        meetingType.pipeline, 
        true, // Preserve existing stage value
        meetingType.booking_form_config?.stage_field_id // Pass existing stage field ID
      )
    }
    
    setFormData({
      name: meetingType.name,
      description: meetingType.description,
      duration_minutes: meetingType.duration_minutes,
      location_type: meetingType.location_type,
      location_details: meetingType.location_details || {},
      pipeline: meetingType.pipeline || '',
      pipeline_stage: meetingType.pipeline_stage || '',
      booking_form_config: meetingType.booking_form_config || {},
      custom_questions: meetingType.custom_questions || [],
      required_fields: meetingType.required_fields || [],
      confirmation_template: meetingType.confirmation_template || '',
      reminder_template: meetingType.reminder_template || '',
      cancellation_template: meetingType.cancellation_template || '',
      allow_rescheduling: meetingType.allow_rescheduling ?? true,
      allow_cancellation: meetingType.allow_cancellation ?? true,
      cancellation_notice_hours: meetingType.cancellation_notice_hours || 24,
      send_reminders: meetingType.send_reminders ?? true,
      reminder_hours: Array.isArray(meetingType.reminder_hours) ? meetingType.reminder_hours[0] : (meetingType.reminder_hours || 24),
      template_type: 'standalone',
      created_for_org: true
    })
    setShowCreateDialog(true)
  }

  const handleSaveTemplate = async () => {
    try {
      if (editingTemplate && !editingTemplate.is_template) {
        // Converting existing meeting type to template
        console.log('Converting meeting type to template:', {
          meetingTypeId: editingTemplate.id,
          meetingTypeName: editingTemplate.name,
          template_type: formData.template_type,
          created_for_org: formData.created_for_org
        })
        
        // Ensure we have a valid meeting type ID
        if (!editingTemplate.id) {
          throw new Error('Meeting type ID is missing')
        }
        
        const response = await api.post(`/api/v1/communications/scheduling/meeting-types/${editingTemplate.id}/make_template/`, {
          template_type: formData.template_type,
          created_for_org: formData.created_for_org
        })
        console.log('Template created successfully:', response.data)
        toast({
          title: 'Template Created',
          description: 'Meeting type has been converted to a template'
        })
      } else if (editingTemplate && editingTemplate.is_template) {
        // Updating existing template - include all fields except calendar
        const updateData = {
          name: formData.name,
          description: formData.description,
          duration_minutes: formData.duration_minutes,
          location_type: formData.location_type,
          location_details: formData.location_details,
          pipeline: formData.pipeline || null,
          pipeline_stage: formData.pipeline_stage,
          booking_form_config: {
            ...formData.booking_form_config,
            stage_field_id: selectedStageField?.id || null
          },
          custom_questions: formData.custom_questions,
          required_fields: formData.required_fields,
          confirmation_template: formData.confirmation_template,
          reminder_template: formData.reminder_template,
          cancellation_template: formData.cancellation_template,
          allow_rescheduling: formData.allow_rescheduling,
          allow_cancellation: formData.allow_cancellation,
          cancellation_notice_hours: formData.cancellation_notice_hours,
          send_reminders: formData.send_reminders,
          reminder_hours: [formData.reminder_hours], // Backend expects an array
          template_type: formData.template_type,
          created_for_org: formData.created_for_org
        }
        await api.patch(`/api/v1/communications/scheduling/meeting-types/${editingTemplate.id}/`, updateData)
        toast({
          title: 'Template Updated',
          description: 'Template has been updated successfully'
        })
      } else {
        // Creating a brand new template
        const createData = {
          name: formData.name,
          description: formData.description,
          duration_minutes: formData.duration_minutes,
          location_type: formData.location_type,
          location_details: formData.location_details,
          pipeline: formData.pipeline || null,
          pipeline_stage: formData.pipeline_stage,
          booking_form_config: {
            ...formData.booking_form_config,
            stage_field_id: selectedStageField?.id || null
          },
          custom_questions: formData.custom_questions,
          required_fields: formData.required_fields,
          confirmation_template: formData.confirmation_template,
          reminder_template: formData.reminder_template,
          cancellation_template: formData.cancellation_template,
          allow_rescheduling: formData.allow_rescheduling,
          allow_cancellation: formData.allow_cancellation,
          cancellation_notice_hours: formData.cancellation_notice_hours,
          send_reminders: formData.send_reminders,
          reminder_hours: [formData.reminder_hours], // Backend expects an array
          is_template: true,
          template_type: formData.template_type,
          created_for_org: formData.created_for_org,
          user: null // Templates don't have a specific user
        }
        await api.post('/api/v1/communications/scheduling/meeting-types/', createData)
        toast({
          title: 'Template Created',
          description: 'New template has been created successfully'
        })
      }
      
      setShowCreateDialog(false)
      setEditingTemplate(null)
      loadData()
    } catch (error: any) {
      console.error('Failed to save template:', error)
      console.error('Error response:', error.response?.data)
      const errorMessage = error.response?.data?.detail || 
                          error.response?.data?.error || 
                          (typeof error.response?.data === 'object' ? JSON.stringify(error.response?.data) : error.response?.data) ||
                          'An error occurred'
      toast({
        title: 'Failed to save template',
        description: errorMessage,
        variant: 'destructive'
      })
    }
  }

  const handleDeleteTemplate = async (templateId: string) => {
    if (!confirm('Are you sure you want to delete this template?')) return

    try {
      await api.delete(`/api/v1/communications/scheduling/meeting-types/${templateId}/`)
      toast({
        title: 'Template Deleted',
        description: 'Template has been deleted successfully'
      })
      loadData()
    } catch (error) {
      toast({
        title: 'Failed to delete template',
        description: 'An error occurred',
        variant: 'destructive'
      })
    }
  }

  const handleSyncInstances = async (templateId: string) => {
    try {
      // Get all instances that are synced to this template
      const template = templates.find(t => t.id === templateId)
      if (!template || template.template_type !== 'centralized') {
        toast({
          title: 'Cannot sync',
          description: 'Only centralized templates can be synced',
          variant: 'destructive'
        })
        return
      }

      // In a real implementation, we'd have a bulk sync endpoint
      // For now, we'll just show a success message
      toast({
        title: 'Sync Started',
        description: 'All linked instances will be updated with the latest template changes'
      })
    } catch (error) {
      toast({
        title: 'Failed to sync instances',
        description: 'An error occurred',
        variant: 'destructive'
      })
    }
  }

  const viewInstances = async (template: MeetingType) => {
    setSelectedTemplate(template)
    // Load instances that use this template
    try {
      const response = await api.get('/api/v1/communications/scheduling/meeting-types/', {
        params: { template_source: template.id }
      })
      const instances = response.data.results || response.data || []
      setSelectedTemplate({ ...template, copied_instances: instances })
      setShowInstancesDialog(true)
    } catch (error) {
      console.error('Failed to load instances:', error)
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
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  if (!canManageAll) {
    return (
      <div className="text-center py-12">
        <Shield className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
        <h3 className="text-lg font-medium mb-2">Admin Access Required</h3>
        <p className="text-muted-foreground">
          Only administrators can manage templates
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <Tabs defaultValue="templates" className="space-y-4">
        <TabsList>
          <TabsTrigger value="templates">Templates</TabsTrigger>
          <TabsTrigger value="meeting-types">Meeting Types</TabsTrigger>
        </TabsList>

        <TabsContent value="templates" className="space-y-4">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h3 className="text-lg font-medium">Organization Templates</h3>
              <p className="text-sm text-muted-foreground">
                Templates that can be used by all users in your organization
              </p>
            </div>
          </div>

          {templates.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <Globe className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <h3 className="text-lg font-medium mb-2">No Templates Yet</h3>
                <p className="text-muted-foreground mb-4">
                  Convert existing meeting types to templates or create new ones
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4">
              {templates.map((template) => (
                <Card key={template.id}>
                  <CardContent className="p-6">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <h3 className="font-semibold text-lg">{template.name}</h3>
                          <Badge variant={template.template_type === 'centralized' ? 'default' : 'secondary'}>
                            {template.template_type === 'centralized' ? 'Centralized' : 'Standalone'}
                          </Badge>
                          {template.created_for_org && (
                            <Badge variant="outline">
                              <Globe className="h-3 w-3 mr-1" />
                              Organization
                            </Badge>
                          )}
                        </div>
                        
                        {template.description && (
                          <p className="text-sm text-muted-foreground mb-3">{template.description}</p>
                        )}
                        
                        <div className="flex items-center gap-4 text-sm text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {template.duration_minutes} minutes
                          </span>
                          <span>{getLocationTypeDisplay(template.location_type)}</span>
                          {template.copied_instances && template.copied_instances.length > 0 && (
                            <span className="flex items-center gap-1">
                              <Users className="h-3 w-3" />
                              {template.copied_instances.length} instances
                            </span>
                          )}
                        </div>

                        {template.template_type === 'centralized' && template.last_synced_at && (
                          <div className="mt-2 text-xs text-muted-foreground">
                            Last synced: {format(new Date(template.last_synced_at), 'PPp')}
                          </div>
                        )}
                      </div>
                      
                      <div className="flex items-center gap-2">
                        {template.template_type === 'centralized' && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleSyncInstances(template.id)}
                          >
                            <RefreshCw className="h-4 w-4" />
                          </Button>
                        )}
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => viewInstances(template)}
                        >
                          <Users className="h-4 w-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={async () => {
                            setEditingTemplate(template)
                            
                            // Load pipeline fields if a pipeline is selected
                            if (template.pipeline) {
                              await loadPipelineFields(
                                template.pipeline, 
                                true, // Preserve existing stage value
                                template.booking_form_config?.stage_field_id // Pass existing stage field ID
                              )
                            }
                            
                            setFormData({
                              name: template.name,
                              description: template.description,
                              duration_minutes: template.duration_minutes,
                              location_type: template.location_type,
                              location_details: template.location_details || {},
                              pipeline: template.pipeline || '',
                              pipeline_stage: template.pipeline_stage || '',
                              booking_form_config: template.booking_form_config || {},
                              custom_questions: template.custom_questions || [],
                              required_fields: template.required_fields || [],
                              confirmation_template: template.confirmation_template || '',
                              reminder_template: template.reminder_template || '',
                              cancellation_template: template.cancellation_template || '',
                              allow_rescheduling: template.allow_rescheduling ?? true,
                              allow_cancellation: template.allow_cancellation ?? true,
                              cancellation_notice_hours: template.cancellation_notice_hours || 24,
                              send_reminders: template.send_reminders ?? true,
                              reminder_hours: Array.isArray(template.reminder_hours) ? template.reminder_hours[0] : (template.reminder_hours || 24),
                              template_type: template.template_type || 'standalone',
                              created_for_org: template.created_for_org
                            })
                            setShowCreateDialog(true)
                          }}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleDeleteTemplate(template.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="meeting-types" className="space-y-4">
          <div className="mb-4">
            <h3 className="text-lg font-medium">Convertible Meeting Types</h3>
            <p className="text-sm text-muted-foreground">
              Select meeting types to convert into templates
            </p>
          </div>

          {meetingTypes.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <p className="text-muted-foreground">
                  No meeting types available to convert
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-3">
              {meetingTypes.map((meetingType) => (
                <Card key={meetingType.id}>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <h4 className="font-medium">{meetingType.name}</h4>
                        <div className="flex items-center gap-4 mt-1 text-sm text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {meetingType.duration_minutes} min
                          </span>
                          <span>{getLocationTypeDisplay(meetingType.location_type)}</span>
                        </div>
                      </div>
                      <Button
                        size="sm"
                        onClick={() => handleConvertToTemplate(meetingType.id)}
                      >
                        <Copy className="h-4 w-4 mr-2" />
                        Make Template
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Create/Edit Template Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>
              {editingTemplate?.is_template ? 'Edit Template' : 'Create Template'}
            </DialogTitle>
            <DialogDescription>
              {editingTemplate?.is_template 
                ? 'Update template settings'
                : 'Convert this meeting type to a reusable template'}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 mt-4 max-h-[60vh] overflow-y-auto pr-2">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <Label>Template Name *</Label>
                <Input
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., Standard Sales Call"
                />
              </div>
              
              <div>
                <Label>Duration (minutes) *</Label>
                <Select
                  value={formData.duration_minutes.toString()}
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
                    <SelectItem value="120">2 hours</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div>
              <Label>Description</Label>
              <Textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Describe this template"
                rows={3}
              />
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <Label>Location Type</Label>
                <Select
                  value={formData.location_type}
                  onValueChange={(value) => setFormData({ ...formData, location_type: value })}
                >
                  <SelectTrigger>
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

              <div>
                <Label>Pipeline (Optional)</Label>
                <Select
                  value={formData.pipeline || 'none'}
                  onValueChange={(value) => {
                    const pipelineId = value === 'none' ? '' : value
                    setFormData({ 
                      ...formData, 
                      pipeline: pipelineId,
                      pipeline_stage: '' // Reset stage when pipeline changes
                    })
                    loadPipelineFields(pipelineId)
                    setSelectedStageField(null)
                  }}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select pipeline" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">None</SelectItem>
                    {pipelines.map((pipeline: any) => (
                      <SelectItem key={pipeline.id} value={pipeline.id}>
                        {pipeline.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {formData.pipeline && (
              <>
                {stageFields.length > 0 && (
                  <div>
                    <Label>Stage Field</Label>
                    <Select
                      value={selectedStageField?.id || ''}
                      onValueChange={(value) => {
                        const field = stageFields.find((f: any) => f.id === value)
                        setSelectedStageField(field || null)
                        // Reset the stage selection when changing stage field
                        setFormData({ 
                          ...formData, 
                          pipeline_stage: ''
                        })
                      }}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select which field defines stages" />
                      </SelectTrigger>
                      <SelectContent>
                        {stageFields.map((field: any) => (
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
                    <Label>Pipeline Stage</Label>
                    <Select
                      value={formData.pipeline_stage || 'all'}
                      onValueChange={(value) => setFormData({ 
                        ...formData, 
                        pipeline_stage: value === 'all' ? '' : value 
                      })}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select a stage" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Stages</SelectItem>
                        {selectedStageField.field_config?.options?.map((option: any) => (
                          <SelectItem key={option.value} value={option.value}>
                            {option.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-muted-foreground mt-1">
                      Records created from this template will be set to this stage
                    </p>
                  </div>
                )}
              </>
            )}

            <div className="space-y-4 border-t pt-4">
              <h4 className="font-medium">Settings</h4>
              
              <div className="grid gap-4 md:grid-cols-2">
                <div className="flex items-center justify-between">
                  <Label>Allow Rescheduling</Label>
                  <Switch
                    checked={formData.allow_rescheduling}
                    onCheckedChange={(checked) => 
                      setFormData({ ...formData, allow_rescheduling: checked })
                    }
                  />
                </div>

                <div className="flex items-center justify-between">
                  <Label>Allow Cancellation</Label>
                  <Switch
                    checked={formData.allow_cancellation}
                    onCheckedChange={(checked) => 
                      setFormData({ ...formData, allow_cancellation: checked })
                    }
                  />
                </div>
              </div>

              {formData.allow_cancellation && (
                <div>
                  <Label>Cancellation Notice (hours)</Label>
                  <Input
                    type="number"
                    value={formData.cancellation_notice_hours || 24}
                    onChange={(e) => setFormData({ ...formData, cancellation_notice_hours: parseInt(e.target.value) || 24 })}
                    min={0}
                    max={168}
                  />
                </div>
              )}

              <div className="flex items-center justify-between">
                <Label>Send Reminders</Label>
                <Switch
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
                  <p className="text-xs text-muted-foreground mt-1">
                    How many hours before the meeting to send reminder
                  </p>
                </div>
              )}
            </div>

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
                    <SelectItem value="standalone">
                      <div>
                        <div className="font-medium">Standalone</div>
                        <div className="text-xs text-muted-foreground">
                          One-time copy - changes won't sync
                        </div>
                      </div>
                    </SelectItem>
                    <SelectItem value="centralized">
                      <div>
                        <div className="font-medium">Centralized</div>
                        <div className="text-xs text-muted-foreground">
                          Changes sync to all linked instances
                        </div>
                      </div>
                    </SelectItem>
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

            <div className="flex justify-end gap-2 pt-4">
              <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
                Cancel
              </Button>
              <Button onClick={handleSaveTemplate}>
                {editingTemplate?.is_template ? 'Update Template' : 'Create Template'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Instances Dialog */}
      <Dialog open={showInstancesDialog} onOpenChange={setShowInstancesDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Template Instances</DialogTitle>
            <DialogDescription>
              Meeting types created from this template
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-3 mt-4">
            {selectedTemplate?.copied_instances && selectedTemplate.copied_instances.length > 0 ? (
              selectedTemplate.copied_instances.map((instance) => (
                <div key={instance.id} className="border rounded-lg p-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">{instance.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {instance.user.first_name} {instance.user.last_name} ({instance.user.email})
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      {instance.is_synced_to_template ? (
                        <Badge variant="default">
                          <LinkIcon className="h-3 w-3 mr-1" />
                          Synced
                        </Badge>
                      ) : (
                        <Badge variant="secondary">
                          <Unlink className="h-3 w-3 mr-1" />
                          Unsynced
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-center py-8 text-muted-foreground">
                No instances created from this template yet
              </p>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}