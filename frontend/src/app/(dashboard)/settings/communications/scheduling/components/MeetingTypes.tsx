'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Clock, Plus, Edit2, Trash2, Video, Phone, MapPin, Users, Copy, ExternalLink } from 'lucide-react'
import { useAuth } from '@/features/auth/context'
import { useToast } from '@/hooks/use-toast'
import api from '@/lib/api'

interface MeetingType {
  id: string
  name: string
  slug: string
  description: string
  duration_minutes: number
  location_type: 'zoom' | 'google_meet' | 'teams' | 'phone' | 'in_person' | 'custom'
  location_details: any
  color?: string
  is_active: boolean
  confirmation_required?: boolean
  max_bookings_per_day?: number
  pipeline?: string
  pipeline_stage?: string
  booking_fields?: any[]
  questions?: Array<{
    question: string
    required: boolean
    type: string
  }>
  created_at: string
  updated_at: string
}

interface Pipeline {
  id: string
  name: string
  description: string
}

const LOCATION_TYPES = [
  { value: 'zoom', label: 'Zoom Meeting', icon: Video },
  { value: 'google_meet', label: 'Google Meet', icon: Video },
  { value: 'teams', label: 'Microsoft Teams', icon: Video },
  { value: 'phone', label: 'Phone Call', icon: Phone },
  { value: 'in_person', label: 'In Person', icon: MapPin },
  { value: 'custom', label: 'Custom Location', icon: Users },
]

const COLORS = [
  '#3B82F6', // Blue
  '#10B981', // Green
  '#F59E0B', // Amber
  '#EF4444', // Red
  '#8B5CF6', // Purple
  '#EC4899', // Pink
  '#14B8A6', // Teal
  '#F97316', // Orange
]

const DURATIONS = [
  { value: 15, label: '15 minutes' },
  { value: 30, label: '30 minutes' },
  { value: 45, label: '45 minutes' },
  { value: 60, label: '1 hour' },
  { value: 90, label: '1.5 hours' },
  { value: 120, label: '2 hours' },
]

export default function MeetingTypes() {
  const { user } = useAuth()
  const { toast } = useToast()
  const [meetingTypes, setMeetingTypes] = useState<MeetingType[]>([])
  const [pipelines, setPipelines] = useState<Pipeline[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [editingType, setEditingType] = useState<MeetingType | null>(null)
  const [formData, setFormData] = useState<Partial<MeetingType>>({
    name: '',
    slug: '',
    description: '',
    duration_minutes: 30,
    location_type: 'google_meet',
    location_details: {},
    color: '#3B82F6',
    is_active: true,
    confirmation_required: false,
    booking_fields: [],
  })

  useEffect(() => {
    fetchMeetingTypes()
    fetchPipelines()
  }, [])

  const fetchMeetingTypes = async () => {
    setIsLoading(true)
    try {
      const response = await api.get('/api/v1/communications/scheduling/meeting-types/')
      setMeetingTypes(response.data.results || [])
    } catch (error) {
      console.error('Failed to fetch meeting types:', error)
      toast({
        title: 'Error',
        description: 'Failed to load meeting types',
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  const fetchPipelines = async () => {
    try {
      const response = await api.get('/api/v1/pipelines/')
      setPipelines(response.data.results || [])
    } catch (error) {
      console.error('Failed to fetch pipelines:', error)
    }
  }

  const handleSubmit = async () => {
    if (!formData.name || !formData.duration_minutes) {
      toast({
        title: 'Error',
        description: 'Please fill in required fields',
        variant: 'destructive',
      })
      return
    }

    // Generate slug from name if creating new
    const dataToSend = { ...formData }
    if (!editingType && !dataToSend.slug) {
      dataToSend.slug = formData.name
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '')
    }

    // Ensure location_details is an object
    if (typeof dataToSend.location_details === 'string') {
      dataToSend.location_details = { details: dataToSend.location_details }
    }

    try {
      if (editingType) {
        const response = await api.patch(
          `/api/v1/communications/scheduling/meeting-types/${editingType.id}/`,
          dataToSend
        )
        setMeetingTypes(
          meetingTypes.map((type) => (type.id === editingType.id ? response.data : type))
        )
        toast({
          title: 'Success',
          description: 'Meeting type updated',
        })
      } else {
        const response = await api.post('/api/v1/communications/scheduling/meeting-types/', dataToSend)
        setMeetingTypes([...meetingTypes, response.data])
        toast({
          title: 'Success',
          description: 'Meeting type created',
        })
      }
      handleCloseDialog()
    } catch (error: any) {
      console.error('Failed to save meeting type:', {
        status: error.response?.status,
        data: error.response?.data,
        message: error.message,
        payload: formData
      })
      const errorMessage = error.response?.data?.detail || 
                          error.response?.data?.error || 
                          Object.values(error.response?.data || {}).flat().join(', ') ||
                          'Failed to save meeting type'
      toast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive',
      })
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this meeting type?')) return

    try {
      await api.delete(`/api/v1/communications/scheduling/meeting-types/${id}/`)
      setMeetingTypes(meetingTypes.filter((type) => type.id !== id))
      toast({
        title: 'Success',
        description: 'Meeting type deleted',
      })
    } catch (error) {
      console.error('Failed to delete meeting type:', error)
      toast({
        title: 'Error',
        description: 'Failed to delete meeting type',
        variant: 'destructive',
      })
    }
  }

  const handleToggleActive = async (type: MeetingType) => {
    try {
      const response = await api.patch(
        `/api/v1/communications/scheduling/meeting-types/${type.id}/`,
        { is_active: !type.is_active }
      )
      setMeetingTypes(
        meetingTypes.map((t) => (t.id === type.id ? response.data : t))
      )
      toast({
        title: 'Success',
        description: `Meeting type ${response.data.is_active ? 'activated' : 'deactivated'}`,
      })
    } catch (error) {
      console.error('Failed to toggle meeting type:', error)
      toast({
        title: 'Error',
        description: 'Failed to update meeting type',
        variant: 'destructive',
      })
    }
  }

  const handleEdit = (type: MeetingType) => {
    setEditingType(type)
    setFormData(type)
    setIsDialogOpen(true)
  }

  const handleCloseDialog = () => {
    setIsDialogOpen(false)
    setEditingType(null)
    setFormData({
      name: '',
      slug: '',
      description: '',
      duration_minutes: 30,
      location_type: 'google_meet',
      location_details: {},
      color: '#3B82F6',
      is_active: true,
      confirmation_required: false,
      booking_fields: [],
    })
  }

  const getLocationIcon = (type: string) => {
    const location = LOCATION_TYPES.find((l) => l.value === type)
    return location ? location.icon : Users
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <div>
          <p className="text-sm text-muted-foreground">
            Create different meeting types for various purposes
          </p>
        </div>
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              New Meeting Type
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>
                {editingType ? 'Edit Meeting Type' : 'Create Meeting Type'}
              </DialogTitle>
              <DialogDescription>
                Configure the details for this meeting type
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 mt-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="name">Name *</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g., Discovery Call"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="duration">Duration *</Label>
                  <Select
                    value={formData.duration_minutes?.toString()}
                    onValueChange={(value) => setFormData({ ...formData, duration_minutes: parseInt(value) })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select duration" />
                    </SelectTrigger>
                    <SelectContent>
                      {DURATIONS.map((d) => (
                        <SelectItem key={d.value} value={d.value.toString()}>
                          {d.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Brief description of this meeting type"
                  rows={3}
                />
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="location_type">Location Type</Label>
                  <Select
                    value={formData.location_type}
                    onValueChange={(value: any) => setFormData({ ...formData, location_type: value })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select location" />
                    </SelectTrigger>
                    <SelectContent>
                      {LOCATION_TYPES.map((loc) => {
                        const Icon = loc.icon
                        return (
                          <SelectItem key={loc.value} value={loc.value}>
                            <div className="flex items-center">
                              <Icon className="h-4 w-4 mr-2" />
                              {loc.label}
                            </div>
                          </SelectItem>
                        )
                      })}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="location_details">Location Details</Label>
                  <Input
                    id="location_details"
                    value={formData.location_details?.details || ''}
                    onChange={(e) => setFormData({ 
                      ...formData, 
                      location_details: { details: e.target.value } 
                    })}
                    placeholder={
                      ['zoom', 'google_meet', 'teams'].includes(formData.location_type || '') 
                        ? 'Meeting link will be generated' 
                        : 'Enter location details'
                    }
                  />
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="pipeline">Pipeline (Optional)</Label>
                  <Select
                    value={formData.pipeline || 'none'}
                    onValueChange={(value) => setFormData({ ...formData, pipeline: value === 'none' ? undefined : value })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select pipeline" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">None</SelectItem>
                      {pipelines.map((pipeline) => (
                        <SelectItem key={pipeline.id} value={pipeline.id}>
                          {pipeline.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="color">Color</Label>
                  <div className="flex gap-2">
                    {COLORS.map((color) => (
                      <button
                        key={color}
                        type="button"
                        className={`w-8 h-8 rounded-md border-2 ${
                          formData.color === color ? 'border-gray-900' : 'border-transparent'
                        }`}
                        style={{ backgroundColor: color }}
                        onClick={() => setFormData({ ...formData, color })}
                      />
                    ))}
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Confirmation Required</Label>
                    <p className="text-sm text-muted-foreground">
                      Require manual confirmation for bookings
                    </p>
                  </div>
                  <Switch
                    checked={formData.confirmation_required}
                    onCheckedChange={(checked) =>
                      setFormData({ ...formData, confirmation_required: checked })
                    }
                  />
                </div>
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Active</Label>
                    <p className="text-sm text-muted-foreground">
                      Allow new bookings for this meeting type
                    </p>
                  </div>
                  <Switch
                    checked={formData.is_active}
                    onCheckedChange={(checked) => setFormData({ ...formData, is_active: checked })}
                  />
                </div>
              </div>

              <div className="flex justify-end space-x-2">
                <Button variant="outline" onClick={handleCloseDialog}>
                  Cancel
                </Button>
                <Button onClick={handleSubmit}>
                  {editingType ? 'Update' : 'Create'} Meeting Type
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {meetingTypes.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Clock className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">No meeting types yet</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Create your first meeting type to start accepting bookings
            </p>
            <Button
              onClick={() => setIsDialogOpen(true)}
            >
              <Plus className="h-4 w-4 mr-2" />
              Create Meeting Type
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {meetingTypes.map((type) => {
            const LocationIcon = getLocationIcon(type.location_type)
            return (
              <Card key={type.id} className="relative">
                <div
                  className="absolute top-0 left-0 w-full h-1 rounded-t-lg"
                  style={{ backgroundColor: type.color }}
                />
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <CardTitle className="text-lg">{type.name}</CardTitle>
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Clock className="h-3 w-3" />
                        {type.duration_minutes} minutes
                      </div>
                    </div>
                    <Badge variant={type.is_active ? 'default' : 'secondary'}>
                      {type.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  {type.description && (
                    <p className="text-sm text-muted-foreground line-clamp-2">
                      {type.description}
                    </p>
                  )}
                  <div className="flex items-center gap-2 text-sm">
                    <LocationIcon className="h-4 w-4 text-muted-foreground" />
                    <span>
                      {LOCATION_TYPES.find((l) => l.value === type.location_type)?.label}
                    </span>
                  </div>
                  {type.pipeline && (
                    <div className="text-sm">
                      <span className="text-muted-foreground">Pipeline: </span>
                      <span className="font-medium">
                        {pipelines.find((p) => p.id === type.pipeline)?.name || 'Unknown'}
                      </span>
                    </div>
                  )}
                  <div className="flex gap-2 pt-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleEdit(type)}
                    >
                      <Edit2 className="h-3 w-3" />
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleToggleActive(type)}
                    >
                      {type.is_active ? 'Deactivate' : 'Activate'}
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleDelete(type.id)}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}