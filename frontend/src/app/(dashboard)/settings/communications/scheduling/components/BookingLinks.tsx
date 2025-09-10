'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
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
import { Link2, Plus, Copy, ExternalLink, Edit2, Trash2, QrCode, Share2 } from 'lucide-react'
import { useAuth } from '@/features/auth/context'
import { useToast } from '@/hooks/use-toast'
import api from '@/lib/api'

interface SchedulingLink {
  id: string
  meeting_type: string
  meeting_type_name?: string
  slug: string
  name: string
  public_name?: string
  public_description?: string
  is_active: boolean
  expires_at?: string
  max_bookings?: number
  booking_count: number
  booking_url?: string
  status?: string
  created_at: string
  updated_at: string
}

interface MeetingType {
  id: string
  name: string
  duration: number
  color: string
}

export default function BookingLinks() {
  const { user } = useAuth()
  const { toast } = useToast()
  const [links, setLinks] = useState<SchedulingLink[]>([])
  const [meetingTypes, setMeetingTypes] = useState<MeetingType[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [editingLink, setEditingLink] = useState<SchedulingLink | null>(null)
  const [formData, setFormData] = useState<Partial<SchedulingLink>>({
    meeting_type: '',
    name: '',
    public_name: '',
    public_description: '',
    is_active: true,
  })

  useEffect(() => {
    fetchLinks()
    fetchMeetingTypes()
  }, [])

  const fetchLinks = async () => {
    setIsLoading(true)
    try {
      const response = await api.get('/api/v1/communications/scheduling/links/')
      setLinks(response.data.results || [])
    } catch (error) {
      console.error('Failed to fetch scheduling links:', error)
      toast({
        title: 'Error',
        description: 'Failed to load booking links',
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  const fetchMeetingTypes = async () => {
    try {
      const response = await api.get('/api/v1/communications/scheduling/meeting-types/')
      setMeetingTypes(response.data.results || [])
    } catch (error) {
      console.error('Failed to fetch meeting types:', error)
    }
  }

  const handleSubmit = async () => {
    if (!formData.meeting_type || !formData.name) {
      toast({
        title: 'Error',
        description: 'Please fill in required fields',
        variant: 'destructive',
      })
      return
    }

    try {
      if (editingLink) {
        const response = await api.patch(
          `/api/v1/communications/scheduling/links/${editingLink.id}/`,
          formData
        )
        setLinks(links.map((link) => (link.id === editingLink.id ? response.data : link)))
        toast({
          title: 'Success',
          description: 'Booking link updated',
        })
      } else {
        const response = await api.post('/api/v1/communications/scheduling/links/', formData)
        setLinks([...links, response.data])
        toast({
          title: 'Success',
          description: 'Booking link created',
        })
      }
      handleCloseDialog()
    } catch (error: any) {
      console.error('Failed to save booking link:', {
        status: error.response?.status,
        data: error.response?.data,
        message: error.message,
        payload: formData
      })
      const errorMessage = error.response?.data?.detail || 
                          error.response?.data?.error || 
                          Object.values(error.response?.data || {}).flat().join(', ') ||
                          'Failed to save booking link'
      toast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive',
      })
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this booking link?')) return

    try {
      await api.delete(`/api/v1/communications/scheduling/links/${id}/`)
      setLinks(links.filter((link) => link.id !== id))
      toast({
        title: 'Success',
        description: 'Booking link deleted',
      })
    } catch (error) {
      console.error('Failed to delete booking link:', error)
      toast({
        title: 'Error',
        description: 'Failed to delete booking link',
        variant: 'destructive',
      })
    }
  }

  const handleToggleActive = async (link: SchedulingLink) => {
    try {
      const response = await api.patch(
        `/api/v1/communications/scheduling/links/${link.id}/`,
        { is_active: !link.is_active }
      )
      setLinks(links.map((l) => (l.id === link.id ? response.data : l)))
      toast({
        title: 'Success',
        description: `Booking link ${response.data.is_active ? 'activated' : 'deactivated'}`,
      })
    } catch (error) {
      console.error('Failed to toggle booking link:', error)
      toast({
        title: 'Error',
        description: 'Failed to update booking link',
        variant: 'destructive',
      })
    }
  }

  const handleEdit = (link: SchedulingLink) => {
    setEditingLink(link)
    setFormData(link)
    setIsDialogOpen(true)
  }

  const handleCloseDialog = () => {
    setIsDialogOpen(false)
    setEditingLink(null)
    setFormData({
      meeting_type: '',
      name: '',
      public_name: '',
      public_description: '',
      is_active: true,
    })
  }

  const copyToClipboard = (link: SchedulingLink) => {
    const url = `${window.location.origin}/book/${link.slug}`
    navigator.clipboard.writeText(url)
    toast({
      title: 'Success',
      description: 'Link copied to clipboard',
    })
  }

  const openInNewTab = (link: SchedulingLink) => {
    const url = `${window.location.origin}/book/${link.slug}`
    window.open(url, '_blank')
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
            Create and manage shareable booking links
          </p>
        </div>
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button disabled={meetingTypes.length === 0}>
              <Plus className="h-4 w-4 mr-2" />
              New Booking Link
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>
                {editingLink ? 'Edit Booking Link' : 'Create Booking Link'}
              </DialogTitle>
              <DialogDescription>
                Create a shareable link for people to book meetings with you
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 mt-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="meeting_type">Meeting Type *</Label>
                  <Select
                    value={formData.meeting_type}
                    onValueChange={(value) => setFormData({ ...formData, meeting_type: value })}
                    disabled={!!editingLink}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select meeting type" />
                    </SelectTrigger>
                    <SelectContent>
                      {meetingTypes.map((type) => (
                        <SelectItem key={type.id} value={type.id}>
                          <div className="flex items-center gap-2">
                            <div
                              className="w-3 h-3 rounded-full"
                              style={{ backgroundColor: type.color }}
                            />
                            {type.name} ({type.duration} min)
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="name">Internal Name *</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g., Discovery Call Link"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="public_name">Public Name (Optional)</Label>
                <Input
                  id="public_name"
                  value={formData.public_name}
                  onChange={(e) => setFormData({ ...formData, public_name: e.target.value })}
                  placeholder="e.g., Book a Discovery Call with Our Team"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="public_description">Public Description (Optional)</Label>
                <Input
                  id="public_description"
                  value={formData.public_description}
                  onChange={(e) => setFormData({ ...formData, public_description: e.target.value })}
                  placeholder="Brief description shown on booking page"
                />
              </div>

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Active</Label>
                  <p className="text-sm text-muted-foreground">
                    Allow bookings through this link
                  </p>
                </div>
                <Switch
                  checked={formData.is_active}
                  onCheckedChange={(checked) => setFormData({ ...formData, is_active: checked })}
                />
              </div>

              <div className="flex justify-end space-x-2">
                <Button variant="outline" onClick={handleCloseDialog}>
                  Cancel
                </Button>
                <Button onClick={handleSubmit}>
                  {editingLink ? 'Update' : 'Create'} Booking Link
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {meetingTypes.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Link2 className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">No meeting types available</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Create a meeting type first before creating booking links
            </p>
          </CardContent>
        </Card>
      ) : links.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Link2 className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">No booking links yet</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Create your first booking link to start accepting meetings
            </p>
            <Button onClick={() => setIsDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Create Booking Link
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {links.map((link) => {
            const meetingType = meetingTypes.find((t) => t.id === link.meeting_type)
            const bookingUrl = `${window.location.origin}/book/${link.slug}`

            return (
              <Card key={link.id}>
                <CardContent className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="space-y-3 flex-1">
                      <div className="flex items-center gap-3">
                        <h3 className="text-lg font-medium">{link.name}</h3>
                        <Badge variant={link.is_active ? 'default' : 'secondary'}>
                          {link.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                        {link.booking_count > 0 && (
                          <Badge variant="outline">{link.booking_count} bookings</Badge>
                        )}
                      </div>

                      {link.public_description && (
                        <p className="text-sm text-muted-foreground">{link.public_description}</p>
                      )}

                      <div className="flex items-center gap-4 text-sm">
                        {meetingType && (
                          <div className="flex items-center gap-2">
                            <div
                              className="w-3 h-3 rounded-full"
                              style={{ backgroundColor: meetingType.color }}
                            />
                            <span>{meetingType.name}</span>
                            <span className="text-muted-foreground">({meetingType.duration} min)</span>
                          </div>
                        )}
                      </div>

                      <div className="flex items-center gap-2">
                        <Input
                          value={bookingUrl}
                          readOnly
                          className="flex-1 text-sm"
                        />
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => copyToClipboard(link)}
                        >
                          <Copy className="h-4 w-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => openInNewTab(link)}
                        >
                          <ExternalLink className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>

                    <div className="flex gap-2 ml-4">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleEdit(link)}
                      >
                        <Edit2 className="h-4 w-4" />
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleToggleActive(link)}
                      >
                        {link.is_active ? 'Deactivate' : 'Activate'}
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleDelete(link.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
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