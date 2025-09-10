'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Calendar,
  Clock,
  Video,
  Phone,
  MapPin,
  User,
  Mail,
  CheckCircle,
  XCircle,
  AlertCircle,
  ExternalLink,
  MoreVertical,
  CalendarX,
} from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useAuth } from '@/features/auth/context'
import { useToast } from '@/hooks/use-toast'
import api from '@/lib/api'
import { format, parseISO, isAfter, isBefore, startOfDay, endOfDay } from 'date-fns'

interface ScheduledMeeting {
  id: string
  meeting_type: MeetingType
  scheduled_time: string
  duration: number
  status: 'pending' | 'confirmed' | 'cancelled' | 'completed'
  meeting_url?: string
  meeting_details?: string
  participant: Participant
  notes?: string
  record?: any
  created_at: string
  updated_at: string
}

interface MeetingType {
  id: string
  name: string
  location_type: string
  color: string
}

interface Participant {
  id: string
  name: string
  email: string
  phone?: string
}

const STATUS_BADGES = {
  pending: { label: 'Pending', variant: 'secondary' as const, icon: AlertCircle },
  confirmed: { label: 'Confirmed', variant: 'default' as const, icon: CheckCircle },
  cancelled: { label: 'Cancelled', variant: 'destructive' as const, icon: XCircle },
  completed: { label: 'Completed', variant: 'outline' as const, icon: CheckCircle },
}

const LOCATION_ICONS: Record<string, any> = {
  video: Video,
  phone: Phone,
  in_person: MapPin,
  custom: Calendar,
}

interface ScheduledMeetingsProps {
  canManageAll?: boolean
}

export default function ScheduledMeetings({ canManageAll = false }: ScheduledMeetingsProps) {
  const { user } = useAuth()
  const { toast } = useToast()
  const [meetings, setMeetings] = useState<ScheduledMeeting[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('upcoming')
  const [selectedMeeting, setSelectedMeeting] = useState<ScheduledMeeting | null>(null)
  const [isDetailsOpen, setIsDetailsOpen] = useState(false)
  const [filters, setFilters] = useState({
    status: 'all',
    dateRange: 'all',
  })

  useEffect(() => {
    fetchMeetings()
  }, [])

  const fetchMeetings = async () => {
    setIsLoading(true)
    try {
      // Backend API already filters based on permissions (scheduling_all shows all, scheduling shows own)
      const response = await api.get('/api/v1/communications/scheduling/meetings/')
      setMeetings(response.data.results || [])
    } catch (error) {
      console.error('Failed to fetch scheduled meetings:', error)
      toast({
        title: 'Error',
        description: 'Failed to load meetings',
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  const updateMeetingStatus = async (meeting: ScheduledMeeting, status: string) => {
    try {
      const response = await api.patch(
        `/api/v1/communications/scheduling/meetings/${meeting.id}/`,
        { status }
      )
      setMeetings(
        meetings.map((m) => (m.id === meeting.id ? response.data : m))
      )
      toast({
        title: 'Success',
        description: `Meeting ${status}`,
      })
    } catch (error) {
      console.error('Failed to update meeting status:', error)
      toast({
        title: 'Error',
        description: 'Failed to update meeting',
        variant: 'destructive',
      })
    }
  }

  const cancelMeeting = async (meeting: ScheduledMeeting) => {
    if (!confirm('Are you sure you want to cancel this meeting?')) return
    await updateMeetingStatus(meeting, 'cancelled')
  }

  const confirmMeeting = async (meeting: ScheduledMeeting) => {
    await updateMeetingStatus(meeting, 'confirmed')
  }

  const openMeetingDetails = (meeting: ScheduledMeeting) => {
    setSelectedMeeting(meeting)
    setIsDetailsOpen(true)
  }

  const filterMeetings = (meetings: ScheduledMeeting[]) => {
    let filtered = [...meetings]

    // Filter by tab
    const now = new Date()
    if (activeTab === 'upcoming') {
      filtered = filtered.filter(
        (m) =>
          isAfter(parseISO(m.scheduled_time), now) &&
          m.status !== 'cancelled' &&
          m.status !== 'completed'
      )
    } else if (activeTab === 'past') {
      filtered = filtered.filter(
        (m) =>
          (isBefore(parseISO(m.scheduled_time), now) || m.status === 'completed') &&
          m.status !== 'cancelled'
      )
    } else if (activeTab === 'cancelled') {
      filtered = filtered.filter((m) => m.status === 'cancelled')
    }

    // Filter by status
    if (filters.status !== 'all') {
      filtered = filtered.filter((m) => m.status === filters.status)
    }

    // Sort by scheduled time
    filtered.sort((a, b) => {
      const timeA = new Date(a.scheduled_time).getTime()
      const timeB = new Date(b.scheduled_time).getTime()
      return activeTab === 'past' ? timeB - timeA : timeA - timeB
    })

    return filtered
  }

  const filteredMeetings = filterMeetings(meetings)

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
            View and manage your scheduled meetings
          </p>
        </div>
        <div className="flex gap-2">
          <Select
            value={filters.status}
            onValueChange={(value) => setFilters({ ...filters, status: value })}
          >
            <SelectTrigger className="w-[150px]">
              <SelectValue placeholder="All statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Statuses</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="confirmed">Confirmed</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="cancelled">Cancelled</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="upcoming">Upcoming</TabsTrigger>
          <TabsTrigger value="past">Past</TabsTrigger>
          <TabsTrigger value="cancelled">Cancelled</TabsTrigger>
        </TabsList>

        <TabsContent value={activeTab} className="space-y-4 mt-4">
          {filteredMeetings.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Calendar className="h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="text-lg font-medium mb-2">
                  No {activeTab} meetings
                </h3>
                <p className="text-sm text-muted-foreground">
                  {activeTab === 'upcoming'
                    ? 'No upcoming meetings scheduled'
                    : activeTab === 'past'
                    ? 'No past meetings to show'
                    : 'No cancelled meetings'}
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {filteredMeetings.map((meeting) => {
                const StatusIcon = STATUS_BADGES[meeting.status].icon
                const LocationIcon = LOCATION_ICONS[meeting.meeting_type.location_type] || Calendar

                return (
                  <Card key={meeting.id} className="cursor-pointer hover:shadow-md transition-shadow"
                    onClick={() => openMeetingDetails(meeting)}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex gap-4 flex-1">
                          <div
                            className="w-1 rounded-full"
                            style={{ backgroundColor: meeting.meeting_type.color }}
                          />
                          <div className="space-y-2 flex-1">
                            <div className="flex items-center gap-3">
                              <h3 className="font-medium">
                                {meeting.meeting_type.name}
                              </h3>
                              <Badge variant={STATUS_BADGES[meeting.status].variant}>
                                <StatusIcon className="h-3 w-3 mr-1" />
                                {STATUS_BADGES[meeting.status].label}
                              </Badge>
                            </div>

                            <div className="flex items-center gap-4 text-sm text-muted-foreground">
                              <div className="flex items-center gap-1">
                                <Calendar className="h-3 w-3" />
                                {format(parseISO(meeting.scheduled_time), 'MMM d, yyyy')}
                              </div>
                              <div className="flex items-center gap-1">
                                <Clock className="h-3 w-3" />
                                {format(parseISO(meeting.scheduled_time), 'h:mm a')}
                              </div>
                              <div className="flex items-center gap-1">
                                <LocationIcon className="h-3 w-3" />
                                {meeting.meeting_type.location_type.replace('_', ' ')}
                              </div>
                            </div>

                            <div className="flex items-center gap-4">
                              <div className="flex items-center gap-2">
                                <User className="h-4 w-4 text-muted-foreground" />
                                <span className="text-sm font-medium">
                                  {meeting.participant.name}
                                </span>
                              </div>
                              <div className="flex items-center gap-2">
                                <Mail className="h-4 w-4 text-muted-foreground" />
                                <span className="text-sm text-muted-foreground">
                                  {meeting.participant.email}
                                </span>
                              </div>
                            </div>
                          </div>
                        </div>

                        <DropdownMenu>
                          <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                            <Button variant="ghost" size="sm">
                              <MoreVertical className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            {meeting.status === 'pending' && (
                              <>
                                <DropdownMenuItem
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    confirmMeeting(meeting)
                                  }}
                                >
                                  <CheckCircle className="h-4 w-4 mr-2" />
                                  Confirm Meeting
                                </DropdownMenuItem>
                                <DropdownMenuItem
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    cancelMeeting(meeting)
                                  }}
                                  className="text-destructive"
                                >
                                  <XCircle className="h-4 w-4 mr-2" />
                                  Cancel Meeting
                                </DropdownMenuItem>
                              </>
                            )}
                            {meeting.status === 'confirmed' && (
                              <DropdownMenuItem
                                onClick={(e) => {
                                  e.stopPropagation()
                                  cancelMeeting(meeting)
                                }}
                                className="text-destructive"
                              >
                                <CalendarX className="h-4 w-4 mr-2" />
                                Cancel Meeting
                              </DropdownMenuItem>
                            )}
                            {meeting.meeting_url && (
                              <DropdownMenuItem
                                onClick={(e) => {
                                  e.stopPropagation()
                                  window.open(meeting.meeting_url, '_blank')
                                }}
                              >
                                <ExternalLink className="h-4 w-4 mr-2" />
                                Join Meeting
                              </DropdownMenuItem>
                            )}
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          )}
        </TabsContent>
      </Tabs>

      <Dialog open={isDetailsOpen} onOpenChange={setIsDetailsOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Meeting Details</DialogTitle>
            <DialogDescription>
              View and manage meeting information
            </DialogDescription>
          </DialogHeader>
          {selectedMeeting && (
            <div className="space-y-4 mt-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium">
                  {selectedMeeting.meeting_type.name}
                </h3>
                <Badge variant={STATUS_BADGES[selectedMeeting.status].variant}>
                  {STATUS_BADGES[selectedMeeting.status].label}
                </Badge>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-3">
                  <div>
                    <Label>Date & Time</Label>
                    <p className="text-sm">
                      {format(parseISO(selectedMeeting.scheduled_time), 'MMMM d, yyyy')} at{' '}
                      {format(parseISO(selectedMeeting.scheduled_time), 'h:mm a')}
                    </p>
                  </div>
                  <div>
                    <Label>Duration</Label>
                    <p className="text-sm">{selectedMeeting.duration} minutes</p>
                  </div>
                  <div>
                    <Label>Location</Label>
                    <p className="text-sm">
                      {selectedMeeting.meeting_type.location_type.replace('_', ' ')}
                    </p>
                  </div>
                </div>

                <div className="space-y-3">
                  <div>
                    <Label>Participant</Label>
                    <p className="text-sm">{selectedMeeting.participant.name}</p>
                  </div>
                  <div>
                    <Label>Email</Label>
                    <p className="text-sm">{selectedMeeting.participant.email}</p>
                  </div>
                  {selectedMeeting.participant.phone && (
                    <div>
                      <Label>Phone</Label>
                      <p className="text-sm">{selectedMeeting.participant.phone}</p>
                    </div>
                  )}
                </div>
              </div>

              {selectedMeeting.meeting_url && (
                <div>
                  <Label>Meeting Link</Label>
                  <div className="flex items-center gap-2 mt-1">
                    <Input value={selectedMeeting.meeting_url} readOnly />
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => window.open(selectedMeeting.meeting_url, '_blank')}
                    >
                      <ExternalLink className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}

              {selectedMeeting.notes && (
                <div>
                  <Label>Notes</Label>
                  <p className="text-sm mt-1">{selectedMeeting.notes}</p>
                </div>
              )}

              <div className="flex justify-end gap-2 pt-4 border-t">
                {selectedMeeting.status === 'pending' && (
                  <>
                    <Button
                      variant="outline"
                      onClick={() => {
                        confirmMeeting(selectedMeeting)
                        setIsDetailsOpen(false)
                      }}
                    >
                      Confirm Meeting
                    </Button>
                    <Button
                      variant="destructive"
                      onClick={() => {
                        cancelMeeting(selectedMeeting)
                        setIsDetailsOpen(false)
                      }}
                    >
                      Cancel Meeting
                    </Button>
                  </>
                )}
                {selectedMeeting.status === 'confirmed' && (
                  <Button
                    variant="destructive"
                    onClick={() => {
                      cancelMeeting(selectedMeeting)
                      setIsDetailsOpen(false)
                    }}
                  >
                    Cancel Meeting
                  </Button>
                )}
                <Button variant="outline" onClick={() => setIsDetailsOpen(false)}>
                  Close
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}