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
  Users,
  Mail,
  CheckCircle,
  XCircle,
  AlertCircle,
  ExternalLink,
  MoreVertical,
  CalendarX,
  Copy,
  Send,
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

interface FacilitatorBooking {
  id: string
  meeting_type: {
    id: string
    name: string
  }
  facilitator: {
    id: string
    username: string
    email: string
  }
  participant_1_email: string
  participant_1_name: string
  participant_1_phone?: string
  participant_1_record_id?: string
  participant_1_completed_at?: string
  participant_1_message?: string
  participant_2_email: string
  participant_2_name: string
  participant_2_phone?: string
  participant_2_record_id?: string
  participant_2_completed_at?: string
  selected_duration_minutes?: number
  selected_location_type?: string
  selected_location_details?: any
  selected_slots?: Array<{ start: string; end: string }>
  final_slot?: { start: string; end: string }
  status: 'pending_p1' | 'pending_p2' | 'completed' | 'expired' | 'cancelled'
  participant_1_token: string
  participant_2_token: string
  expires_at: string
  invitation_sent_at?: string
  invitation_opened_at?: string
  reminder_sent_at?: string
  scheduled_meeting?: {
    id: string
    meeting_url?: string
    meeting_location?: string
    calendar_event_id?: string
    status?: string
  }
  created_at: string
  updated_at: string
}

interface ScheduledMeeting {
  id: string
  meeting_type: MeetingType
  meeting_type_name?: string
  start_time: string
  end_time: string
  timezone: string
  status: 'scheduled' | 'confirmed' | 'reminder_sent' | 'completed' | 'cancelled' | 'no_show' | 'pending'
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
  is_facilitator_meeting?: boolean
  facilitator_booking?: FacilitatorBooking
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
  pending: { label: 'Pending', variant: 'secondary' as const, icon: Clock },
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
  zoom: Video,
  google_meet: Video,
  teams: Video,
}

const FACILITATOR_STATUS_CONFIG = {
  pending_p1: { 
    label: 'Awaiting Participant 1', 
    variant: 'secondary' as const, 
    icon: Clock,
    description: 'Waiting for first participant to select meeting options'
  },
  pending_p2: { 
    label: 'Awaiting Participant 2', 
    variant: 'default' as const, 
    icon: Clock,
    description: 'Waiting for second participant to choose a time'
  },
  completed: { 
    label: 'Completed', 
    variant: 'outline' as const, 
    icon: CheckCircle,
    description: 'Meeting successfully scheduled'
  },
  expired: { 
    label: 'Expired', 
    variant: 'destructive' as const, 
    icon: AlertCircle,
    description: 'Booking link has expired'
  },
  cancelled: { 
    label: 'Cancelled', 
    variant: 'destructive' as const, 
    icon: XCircle,
    description: 'Booking was cancelled'
  },
}

const LOCATION_DISPLAY: Record<string, string> = {
  zoom: 'Zoom',
  google_meet: 'Google Meet',
  teams: 'Microsoft Teams',
  phone: 'Phone Call',
  in_person: 'In Person',
  custom: 'Custom Location',
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
  const [isFacilitatorModalOpen, setIsFacilitatorModalOpen] = useState(false)
  const [selectedFacilitatorBooking, setSelectedFacilitatorBooking] = useState<FacilitatorBooking | null>(null)
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
    if (meeting.is_facilitator_meeting && meeting.facilitator_booking) {
      setSelectedFacilitatorBooking(meeting.facilitator_booking)
      setIsFacilitatorModalOpen(true)
    } else {
      setSelectedMeeting(meeting)
      setIsDetailsOpen(true)
    }
  }

  const copyLink = (token: string, participant: 1 | 2) => {
    const baseUrl = window.location.origin
    const url = participant === 1 
      ? `${baseUrl}/book/facilitator/${token}/participant1/`
      : `${baseUrl}/book/facilitator/${token}/`
    
    navigator.clipboard.writeText(url)
    toast({
      title: 'Link copied!',
      description: `Booking link for participant ${participant} copied to clipboard`,
    })
  }

  const resendInvitation = async (booking: FacilitatorBooking) => {
    try {
      await api.post(`/api/v1/communications/scheduling/facilitator-bookings/${booking.id}/resend/`)
      toast({
        title: 'Invitation sent',
        description: 'Booking invitation has been resent',
      })
    } catch (error: any) {
      toast({
        title: 'Failed to resend invitation',
        description: error.response?.data?.error || 'Please try again',
        variant: 'destructive'
      })
    }
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

                            {meeting.is_facilitator_meeting && meeting.facilitator_booking ? (
                              <div className="flex items-center gap-4">
                                <div className="flex items-center gap-2">
                                  <Users className="h-4 w-4 text-muted-foreground" />
                                  <span className="text-sm font-medium">
                                    {meeting.facilitator_booking.participant_1_name} & {meeting.facilitator_booking.participant_2_name}
                                  </span>
                                </div>
                                {meeting.facilitator_booking.status && (
                                  <Badge variant={FACILITATOR_STATUS_CONFIG[meeting.facilitator_booking.status]?.variant || 'default'}>
                                    Facilitator: {FACILITATOR_STATUS_CONFIG[meeting.facilitator_booking.status]?.label || meeting.facilitator_booking.status}
                                  </Badge>
                                )}
                              </div>
                            ) : (
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
                            )}
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

      {/* Facilitator Booking Details Dialog */}
      <Dialog open={isFacilitatorModalOpen} onOpenChange={setIsFacilitatorModalOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Facilitator Booking Details</DialogTitle>
            <DialogDescription>
              {selectedFacilitatorBooking && FACILITATOR_STATUS_CONFIG[selectedFacilitatorBooking.status].description}
            </DialogDescription>
          </DialogHeader>
          
          {selectedFacilitatorBooking && (
            <div className="space-y-6 mt-4">
              {/* Status and Meeting Type */}
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-medium">{selectedFacilitatorBooking.meeting_type.name}</h3>
                  <p className="text-sm text-muted-foreground">
                    Facilitated by {selectedFacilitatorBooking.facilitator.username}
                  </p>
                </div>
                <Badge variant={FACILITATOR_STATUS_CONFIG[selectedFacilitatorBooking.status].variant}>
                  {FACILITATOR_STATUS_CONFIG[selectedFacilitatorBooking.status].label}
                </Badge>
              </div>

              {/* Participants */}
              <div className="space-y-4">
                <h4 className="font-medium">Participants</h4>
                
                <div className="grid gap-4 md:grid-cols-2">
                  <Card>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm">Participant 1</CardTitle>
                      {selectedFacilitatorBooking.participant_1_completed_at && (
                        <Badge variant="outline" className="w-fit">
                          <CheckCircle className="h-3 w-3 mr-1" />
                          Completed
                        </Badge>
                      )}
                    </CardHeader>
                    <CardContent className="space-y-2">
                      <div className="text-sm">
                        <Users className="h-3 w-3 inline mr-1" />
                        {selectedFacilitatorBooking.participant_1_name}
                      </div>
                      <div className="text-sm">
                        <Mail className="h-3 w-3 inline mr-1" />
                        {selectedFacilitatorBooking.participant_1_email}
                      </div>
                      {selectedFacilitatorBooking.participant_1_phone && (
                        <div className="text-sm">
                          <Phone className="h-3 w-3 inline mr-1" />
                          {selectedFacilitatorBooking.participant_1_phone}
                        </div>
                      )}
                      {selectedFacilitatorBooking.status === 'pending_p1' && (
                        <div className="pt-2 space-y-2">
                          <Button
                            size="sm"
                            variant="outline"
                            className="w-full"
                            onClick={() => copyLink(selectedFacilitatorBooking.participant_1_token, 1)}
                          >
                            <Copy className="h-3 w-3 mr-1" />
                            Copy Booking Link
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="w-full"
                            onClick={() => resendInvitation(selectedFacilitatorBooking)}
                          >
                            <Send className="h-3 w-3 mr-1" />
                            Resend Invitation
                          </Button>
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm">Participant 2</CardTitle>
                      {selectedFacilitatorBooking.participant_2_completed_at && (
                        <Badge variant="outline" className="w-fit">
                          <CheckCircle className="h-3 w-3 mr-1" />
                          Completed
                        </Badge>
                      )}
                    </CardHeader>
                    <CardContent className="space-y-2">
                      <div className="text-sm">
                        <Users className="h-3 w-3 inline mr-1" />
                        {selectedFacilitatorBooking.participant_2_name}
                      </div>
                      <div className="text-sm">
                        <Mail className="h-3 w-3 inline mr-1" />
                        {selectedFacilitatorBooking.participant_2_email}
                      </div>
                      {selectedFacilitatorBooking.participant_2_phone && (
                        <div className="text-sm">
                          <Phone className="h-3 w-3 inline mr-1" />
                          {selectedFacilitatorBooking.participant_2_phone}
                        </div>
                      )}
                      {selectedFacilitatorBooking.status === 'pending_p2' && (
                        <div className="pt-2 space-y-2">
                          <Button
                            size="sm"
                            variant="outline"
                            className="w-full"
                            onClick={() => copyLink(selectedFacilitatorBooking.participant_2_token, 2)}
                          >
                            <Copy className="h-3 w-3 mr-1" />
                            Copy Booking Link
                          </Button>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </div>
              </div>

              {/* Meeting Options (if P1 completed) */}
              {selectedFacilitatorBooking.selected_duration_minutes && (
                <div className="space-y-3">
                  <h4 className="font-medium">Selected Meeting Options</h4>
                  <Card>
                    <CardContent className="pt-4 space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Clock className="h-4 w-4 text-muted-foreground" />
                          <span className="text-sm">Duration</span>
                        </div>
                        <span className="text-sm font-medium">
                          {selectedFacilitatorBooking.selected_duration_minutes} minutes
                        </span>
                      </div>
                      {selectedFacilitatorBooking.selected_location_type && (
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <MapPin className="h-4 w-4 text-muted-foreground" />
                            <span className="text-sm">Location</span>
                          </div>
                          <span className="text-sm font-medium">
                            {LOCATION_DISPLAY[selectedFacilitatorBooking.selected_location_type]}
                          </span>
                        </div>
                      )}
                      {selectedFacilitatorBooking.participant_1_message && (
                        <div>
                          <p className="text-sm text-muted-foreground mb-1">Message from Participant 1:</p>
                          <p className="text-sm italic">{selectedFacilitatorBooking.participant_1_message}</p>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </div>
              )}

              {/* Available Time Slots (if P1 completed) */}
              {selectedFacilitatorBooking.selected_slots && selectedFacilitatorBooking.selected_slots.length > 0 && (
                <div className="space-y-3">
                  <h4 className="font-medium">Available Time Slots</h4>
                  <div className="grid gap-2">
                    {selectedFacilitatorBooking.selected_slots.map((slot, index) => (
                      <Card key={index}>
                        <CardContent className="py-2 px-4">
                          <div className="flex items-center gap-2">
                            <Calendar className="h-4 w-4 text-muted-foreground" />
                            <span className="text-sm">
                              {format(parseISO(slot.start), 'MMM d, yyyy h:mm a')} - {format(parseISO(slot.end), 'h:mm a')}
                            </span>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>
              )}

              {/* Final Scheduled Time (if completed) */}
              {selectedFacilitatorBooking.final_slot && (
                <div className="space-y-3">
                  <h4 className="font-medium">Scheduled Meeting</h4>
                  <Card>
                    <CardContent className="pt-4 space-y-2">
                      <div className="flex items-center gap-2">
                        <CheckCircle className="h-5 w-5 text-green-500" />
                        <span className="font-medium">Meeting Confirmed</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Calendar className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm">
                          {format(parseISO(selectedFacilitatorBooking.final_slot.start), 'MMMM d, yyyy')}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Clock className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm">
                          {format(parseISO(selectedFacilitatorBooking.final_slot.start), 'h:mm a')} - 
                          {format(parseISO(selectedFacilitatorBooking.final_slot.end), 'h:mm a')}
                        </span>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              )}

              {/* Meeting Link (if available) */}
              {selectedFacilitatorBooking.scheduled_meeting?.meeting_url && (
                <div className="space-y-3">
                  <h4 className="font-medium">Meeting Link</h4>
                  <Card>
                    <CardContent className="pt-4">
                      <div className="flex items-center gap-2">
                        <Video className="h-4 w-4 text-muted-foreground" />
                        <div className="flex-1">
                          <Input 
                            value={selectedFacilitatorBooking.scheduled_meeting.meeting_url} 
                            readOnly 
                            className="font-mono text-sm"
                          />
                        </div>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            navigator.clipboard.writeText(selectedFacilitatorBooking.scheduled_meeting?.meeting_url || '')
                            toast({
                              title: 'Meeting link copied!',
                              description: 'The meeting link has been copied to your clipboard',
                            })
                          }}
                        >
                          <Copy className="h-4 w-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="default"
                          onClick={() => window.open(selectedFacilitatorBooking.scheduled_meeting?.meeting_url, '_blank')}
                        >
                          <ExternalLink className="h-4 w-4 mr-1" />
                          Join
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              )}

              {/* Expiry Information */}
              {selectedFacilitatorBooking.status !== 'completed' && selectedFacilitatorBooking.status !== 'cancelled' && (
                <div className="flex items-center gap-2 p-3 bg-muted rounded-lg">
                  <AlertCircle className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">
                    This booking expires on {format(parseISO(selectedFacilitatorBooking.expires_at), 'MMMM d, yyyy at h:mm a')}
                  </span>
                </div>
              )}

              <div className="flex justify-end gap-2 pt-4 border-t">
                <Button variant="outline" onClick={() => setIsFacilitatorModalOpen(false)}>
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