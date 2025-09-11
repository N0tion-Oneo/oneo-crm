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
  meeting_type_name?: string
  start_time: string
  end_time: string
  timezone: string
  status: 'scheduled' | 'confirmed' | 'reminder_sent' | 'completed' | 'cancelled' | 'no_show'
  meeting_url?: string
  meeting_location?: string
  participant: Participant
  participant_detail?: Participant
  host?: any
  host_name?: string
  pre_meeting_notes?: string
  post_meeting_notes?: string
  record?: any
  record_display?: string
  created_at: string
  updated_at: string
  can_cancel?: boolean
  can_reschedule?: boolean
  is_past?: boolean
  is_upcoming?: boolean
  is_in_progress?: boolean
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
  scheduled: { label: 'Scheduled', variant: 'secondary' as const, icon: Calendar },
  confirmed: { label: 'Confirmed', variant: 'default' as const, icon: CheckCircle },
  reminder_sent: { label: 'Reminder Sent', variant: 'default' as const, icon: AlertCircle },
  completed: { label: 'Completed', variant: 'outline' as const, icon: CheckCircle },
  cancelled: { label: 'Cancelled', variant: 'destructive' as const, icon: XCircle },
  no_show: { label: 'No Show', variant: 'destructive' as const, icon: CalendarX },
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
      // Handle both paginated and non-paginated responses
      const meetingsData = response.data.results || response.data || []
      console.log('Fetched meetings data:', meetingsData) // Debug log to see structure
      setMeetings(Array.isArray(meetingsData) ? meetingsData : [])
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
        (m) => {
          if (!m.start_time) return false
          try {
            return isAfter(parseISO(m.start_time), now) &&
              m.status !== 'cancelled' &&
              m.status !== 'completed'
          } catch {
            return false
          }
        }
      )
    } else if (activeTab === 'past') {
      filtered = filtered.filter(
        (m) => {
          if (!m.start_time) return m.status === 'completed'
          try {
            return (isBefore(parseISO(m.start_time), now) || m.status === 'completed') &&
              m.status !== 'cancelled'
          } catch {
            return m.status === 'completed'
          }
        }
      )
    } else if (activeTab === 'cancelled') {
      filtered = filtered.filter((m) => m.status === 'cancelled')
    }

    // Filter by status
    if (filters.status !== 'all') {
      filtered = filtered.filter((m) => m.status === filters.status)
    }

    // Sort by start time
    filtered.sort((a, b) => {
      if (!a.start_time || !b.start_time) {
        if (!a.start_time && !b.start_time) return 0
        if (!a.start_time) return 1
        return -1
      }
      try {
        const timeA = new Date(a.start_time).getTime()
        const timeB = new Date(b.start_time).getTime()
        return activeTab === 'past' ? timeB - timeA : timeA - timeB
      } catch {
        return 0
      }
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
                const statusBadge = STATUS_BADGES[meeting.status] || STATUS_BADGES.scheduled
                const StatusIcon = statusBadge.icon
                const LocationIcon = LOCATION_ICONS[meeting.meeting_type?.location_type] || Calendar

                return (
                  <Card key={meeting.id} className="cursor-pointer hover:shadow-md transition-shadow"
                    onClick={() => openMeetingDetails(meeting)}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex gap-4 flex-1">
                          <div
                            className="w-1 rounded-full"
                            style={{ backgroundColor: meeting.meeting_type?.color || '#6366f1' }}
                          />
                          <div className="space-y-2 flex-1">
                            <div className="flex items-center gap-3">
                              <h3 className="font-medium">
                                {meeting.meeting_type?.name || meeting.meeting_type_name || 'Unknown Meeting'}
                              </h3>
                              <Badge variant={statusBadge.variant}>
                                <StatusIcon className="h-3 w-3 mr-1" />
                                {statusBadge.label}
                              </Badge>
                            </div>

                            <div className="flex items-center gap-4 text-sm text-muted-foreground">
                              <div className="flex items-center gap-1">
                                <Calendar className="h-3 w-3" />
                                {meeting.start_time ? format(parseISO(meeting.start_time), 'MMM d, yyyy') : 'No date'}
                              </div>
                              <div className="flex items-center gap-1">
                                <Clock className="h-3 w-3" />
                                {meeting.start_time ? format(parseISO(meeting.start_time), 'h:mm a') : 'No time'}
                              </div>
                              <div className="flex items-center gap-1">
                                <LocationIcon className="h-3 w-3" />
                                {(() => {
                                  const locationType = meeting.meeting_type?.location_type
                                  // For virtual meetings, show the URL if available
                                  if (locationType && ['google_meet', 'zoom', 'teams'].includes(locationType)) {
                                    return meeting.meeting_url || meeting.meeting_location || locationType.replace('_', ' ')
                                  }
                                  // For in-person or phone, show the location/phone
                                  if (locationType === 'in_person') {
                                    return meeting.meeting_location || 'In Person'
                                  }
                                  if (locationType === 'phone') {
                                    return meeting.meeting_location || 'Phone Call'
                                  }
                                  // Default fallback
                                  return meeting.meeting_location || (locationType ? locationType.replace('_', ' ') : 'No location')
                                })()}
                              </div>
                            </div>

                            <div className="flex items-center gap-4">
                              <div className="flex items-center gap-2">
                                <User className="h-4 w-4 text-muted-foreground" />
                                <span className="text-sm font-medium">
                                  {meeting.participant_detail?.name || meeting.participant?.name || 'Unknown'}
                                </span>
                              </div>
                              <div className="flex items-center gap-2">
                                <Mail className="h-4 w-4 text-muted-foreground" />
                                <span className="text-sm text-muted-foreground">
                                  {meeting.participant_detail?.email || meeting.participant?.email || 'No email'}
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
                            {(meeting.status === 'scheduled' || meeting.status === 'pending') && (
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
                            {(meeting.status === 'confirmed' || meeting.status === 'reminder_sent') && (
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
                      {selectedMeeting.start_time ? format(parseISO(selectedMeeting.start_time), 'MMMM d, yyyy') : 'No date'} at{' '}
                      {selectedMeeting.start_time ? format(parseISO(selectedMeeting.start_time), 'h:mm a') : 'No time'}
                    </p>
                  </div>
                  <div>
                    <Label>Duration</Label>
                    <p className="text-sm">
                      {selectedMeeting.start_time && selectedMeeting.end_time ? 
                        `${Math.round((new Date(selectedMeeting.end_time).getTime() - new Date(selectedMeeting.start_time).getTime()) / 60000)} minutes` : 
                        'Duration not available'}
                    </p>
                  </div>
                  <div>
                    <Label>Location</Label>
                    <p className="text-sm">
                      {selectedMeeting.meeting_type?.location_type ? 
                        selectedMeeting.meeting_type.location_type.replace('_', ' ') : 
                        'No location'}
                    </p>
                  </div>
                </div>

                <div className="space-y-3">
                  <div>
                    <Label>Participant</Label>
                    <p className="text-sm">
                      {selectedMeeting.participant_detail?.name || 
                       selectedMeeting.participant?.name || 
                       'Unknown'}
                    </p>
                  </div>
                  <div>
                    <Label>Email</Label>
                    <p className="text-sm">
                      {selectedMeeting.participant_detail?.email || 
                       selectedMeeting.participant?.email || 
                       'No email'}
                    </p>
                  </div>
                  {(selectedMeeting.participant_detail?.phone || selectedMeeting.participant?.phone) && (
                    <div>
                      <Label>Phone</Label>
                      <p className="text-sm">
                        {selectedMeeting.participant_detail?.phone || selectedMeeting.participant?.phone}
                      </p>
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

              {(selectedMeeting.pre_meeting_notes || selectedMeeting.post_meeting_notes) && (
                <div>
                  <Label>Notes</Label>
                  {selectedMeeting.pre_meeting_notes && (
                    <div className="mt-1">
                      <p className="text-xs text-muted-foreground">Pre-meeting notes:</p>
                      <p className="text-sm">{selectedMeeting.pre_meeting_notes}</p>
                    </div>
                  )}
                  {selectedMeeting.post_meeting_notes && (
                    <div className="mt-1">
                      <p className="text-xs text-muted-foreground">Post-meeting notes:</p>
                      <p className="text-sm">{selectedMeeting.post_meeting_notes}</p>
                    </div>
                  )}
                </div>
              )}

              <div className="flex justify-end gap-2 pt-4 border-t">
                {(selectedMeeting.status === 'scheduled' || selectedMeeting.status === 'pending') && (
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
                {(selectedMeeting.status === 'confirmed' || selectedMeeting.status === 'reminder_sent') && (
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
                {selectedMeeting.meeting_url && (
                  <Button
                    variant="default"
                    onClick={() => window.open(selectedMeeting.meeting_url, '_blank')}
                  >
                    <Video className="h-4 w-4 mr-2" />
                    Join Meeting
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