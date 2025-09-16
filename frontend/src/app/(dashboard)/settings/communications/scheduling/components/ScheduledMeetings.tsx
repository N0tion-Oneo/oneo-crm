'use client'

import { useState, useEffect, useMemo } from 'react'
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
  Eye,
  Search,
  Filter,
  X,
} from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
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
  participant_1_link?: string
  participant_2_email: string
  participant_2_name: string
  participant_2_phone?: string
  participant_2_record_id?: string
  participant_2_completed_at?: string
  participant_2_link?: string
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
  duration_minutes?: number
  buffer_time?: number
}

interface Participant {
  id: string
  name: string
  email: string
  phone?: string
  notes?: string
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
  const [incompleteBookings, setIncompleteBookings] = useState<FacilitatorBooking[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('upcoming') // Will be updated after fetching data
  const [selectedMeeting, setSelectedMeeting] = useState<ScheduledMeeting | null>(null)
  const [isDetailsOpen, setIsDetailsOpen] = useState(false)
  const [isFacilitatorModalOpen, setIsFacilitatorModalOpen] = useState(false)
  const [selectedFacilitatorBooking, setSelectedFacilitatorBooking] = useState<FacilitatorBooking | null>(null)
  const [selectedFacilitatorMeeting, setSelectedFacilitatorMeeting] = useState<ScheduledMeeting | null>(null)
  const [filters, setFilters] = useState({
    status: 'all',
    dateRange: 'all',
    meetingType: 'all',
    searchQuery: '',
  })

  useEffect(() => {
    fetchMeetings()
    fetchIncompleteBookings()
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

  const fetchIncompleteBookings = async () => {
    try {
      const response = await api.get('/api/v1/communications/scheduling/facilitator-bookings/incomplete/')
      const bookingsData = response.data.results || []
      console.log('Fetched incomplete facilitator bookings:', bookingsData)
      setIncompleteBookings(Array.isArray(bookingsData) ? bookingsData : [])

      // If there are incomplete bookings, default to showing that tab
      if (bookingsData && bookingsData.length > 0) {
        setActiveTab('incomplete')
      }
    } catch (error) {
      console.error('Failed to fetch incomplete bookings:', error)
      // Don't show error toast as this is a supplementary fetch
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

  const openMeetingDetails = (meeting: ScheduledMeeting) => {
    if (meeting.is_facilitator_meeting && meeting.facilitator_booking) {
      setSelectedFacilitatorBooking(meeting.facilitator_booking)
      setSelectedFacilitatorMeeting(meeting)
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
    // If we're on the incomplete tab, don't filter regular meetings
    if (activeTab === 'incomplete') {
      return []
    }

    let filtered = [...meetings]

    // Filter by search query
    if (filters.searchQuery.trim()) {
      const query = filters.searchQuery.toLowerCase()
      filtered = filtered.filter((m) => {
        const participantName = m.participant_detail?.name || m.participant?.name || ''
        const participantEmail = m.participant_detail?.email || m.participant?.email || ''
        const meetingTypeName = m.meeting_type?.name || m.meeting_type_name || ''
        const hostName = m.host_name || ''
        
        // For facilitator meetings, also search facilitator participants
        let facilitatorSearch = ''
        if (m.facilitator_booking) {
          facilitatorSearch = [
            m.facilitator_booking.participant_1_name,
            m.facilitator_booking.participant_1_email,
            m.facilitator_booking.participant_2_name,
            m.facilitator_booking.participant_2_email,
            m.facilitator_booking.facilitator?.username,
          ].filter(Boolean).join(' ').toLowerCase()
        }
        
        return (
          participantName.toLowerCase().includes(query) ||
          participantEmail.toLowerCase().includes(query) ||
          meetingTypeName.toLowerCase().includes(query) ||
          hostName.toLowerCase().includes(query) ||
          facilitatorSearch.includes(query)
        )
      })
    }

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

    // Filter by meeting type
    if (filters.meetingType !== 'all') {
      if (filters.meetingType === 'facilitator') {
        filtered = filtered.filter((m) => m.is_facilitator_meeting)
      } else if (filters.meetingType === 'standard') {
        filtered = filtered.filter((m) => !m.is_facilitator_meeting)
      }
    }

    // Filter by date range
    if (filters.dateRange !== 'all' && filters.dateRange !== '') {
      const now = new Date()
      const startOfToday = startOfDay(now)
      const endOfToday = endOfDay(now)
      
      filtered = filtered.filter((m) => {
        if (!m.start_time) return false
        try {
          const meetingDate = parseISO(m.start_time)
          
          switch (filters.dateRange) {
            case 'today':
              return isAfter(meetingDate, startOfToday) && isBefore(meetingDate, endOfToday)
            case 'week':
              const weekFromNow = new Date(now)
              weekFromNow.setDate(weekFromNow.getDate() + 7)
              return isAfter(meetingDate, now) && isBefore(meetingDate, weekFromNow)
            case 'month':
              const monthFromNow = new Date(now)
              monthFromNow.setMonth(monthFromNow.getMonth() + 1)
              return isAfter(meetingDate, now) && isBefore(meetingDate, monthFromNow)
            default:
              return true
          }
        } catch {
          return false
        }
      })
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

  // Memoize filtered meetings to avoid recalculating on every render
  const filteredMeetings = useMemo(() => filterMeetings(meetings), [meetings, activeTab, filters])
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 10
  
  // Calculate paginated meetings
  const paginatedMeetings = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage
    const endIndex = startIndex + itemsPerPage
    return filteredMeetings.slice(startIndex, endIndex)
  }, [filteredMeetings, currentPage])
  
  const totalPages = Math.ceil(filteredMeetings.length / itemsPerPage)
  
  // Reset to page 1 when filters change
  useEffect(() => {
    setCurrentPage(1)
  }, [activeTab, filters.status])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="space-y-3">
        <div>
          <p className="text-sm text-muted-foreground">
            View and manage your scheduled meetings
          </p>
        </div>
        
        {/* Inline Search Bar and Filters */}
        <div className="flex flex-wrap gap-2 items-center">
          {/* Search Bar */}
          <div className="relative flex-1 min-w-[200px] max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Search meetings..."
              value={filters.searchQuery}
              onChange={(e) => setFilters({ ...filters, searchQuery: e.target.value })}
              className="pl-9 pr-9 h-9"
            />
            {filters.searchQuery && (
              <Button
                variant="ghost"
                size="sm"
                className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7 p-0"
                onClick={() => setFilters({ ...filters, searchQuery: '' })}
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            )}
          </div>

          {/* Filters */}
          <Select
            value={filters.status}
            onValueChange={(value) => setFilters({ ...filters, status: value })}
          >
            <SelectTrigger className="w-[130px] h-9">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Statuses</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="scheduled">Scheduled</SelectItem>
              <SelectItem value="confirmed">Confirmed</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="cancelled">Cancelled</SelectItem>
              <SelectItem value="no_show">No Show</SelectItem>
            </SelectContent>
          </Select>

          <Select
            value={filters.meetingType}
            onValueChange={(value) => setFilters({ ...filters, meetingType: value })}
          >
            <SelectTrigger className="w-[120px] h-9">
              <SelectValue placeholder="Type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              <SelectItem value="standard">Standard</SelectItem>
              <SelectItem value="facilitator">Facilitator</SelectItem>
            </SelectContent>
          </Select>

          <Select
            value={filters.dateRange}
            onValueChange={(value) => setFilters({ ...filters, dateRange: value })}
          >
            <SelectTrigger className="w-[130px] h-9">
              <SelectValue placeholder="Date" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Dates</SelectItem>
              <SelectItem value="today">Today</SelectItem>
              <SelectItem value="week">Next 7 Days</SelectItem>
              <SelectItem value="month">Next 30 Days</SelectItem>
            </SelectContent>
          </Select>

          {/* Clear filters button */}
          {(filters.status !== 'all' || filters.meetingType !== 'all' || filters.dateRange !== 'all' || filters.searchQuery) && (
            <Button
              variant="outline"
              size="sm"
              className="h-9 gap-1"
              onClick={() => setFilters({
                status: 'all',
                dateRange: 'all',
                meetingType: 'all',
                searchQuery: '',
              })}
            >
              <X className="h-3.5 w-3.5" />
              Clear
            </Button>
          )}
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <div className="flex justify-between items-center mb-4">
          <TabsList className="grid w-full grid-cols-4 max-w-[500px]">
            <TabsTrigger value="incomplete">
              Incomplete
              {incompleteBookings.length > 0 && (
                <span className="ml-1.5 px-1.5 py-0.5 text-xs bg-orange-500 text-white rounded-full">
                  {incompleteBookings.length}
                </span>
              )}
            </TabsTrigger>
            <TabsTrigger value="upcoming">Upcoming</TabsTrigger>
            <TabsTrigger value="past">Past</TabsTrigger>
            <TabsTrigger value="cancelled">Cancelled</TabsTrigger>
          </TabsList>

          {/* Results count */}
          <div className="text-sm text-muted-foreground">
            {activeTab === 'incomplete' ? (
              <>
                <span className="font-medium">{incompleteBookings.length}</span> incomplete booking{incompleteBookings.length !== 1 ? 's' : ''}
              </>
            ) : (
              <>
                {filteredMeetings.length > 0 && (
                  <span>
                    Showing {Math.min((currentPage - 1) * itemsPerPage + 1, filteredMeetings.length)}-
                    {Math.min(currentPage * itemsPerPage, filteredMeetings.length)} of{' '}
                  </span>
                )}
                <span className="font-medium">{filteredMeetings.length}</span> meeting{filteredMeetings.length !== 1 ? 's' : ''}
              </>
            )}
          </div>
        </div>

        <TabsContent value={activeTab} className="space-y-4 mt-4">
          {activeTab === 'incomplete' ? (
            // Incomplete facilitator bookings tab content
            incompleteBookings.length === 0 ? (
              <Card>
                <CardContent className="flex flex-col items-center justify-center py-12">
                  <Clock className="h-12 w-12 text-muted-foreground mb-4" />
                  <h3 className="text-lg font-medium mb-2">No incomplete bookings</h3>
                  <p className="text-sm text-muted-foreground text-center">
                    All facilitator meetings have been scheduled successfully
                  </p>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-3">
                {incompleteBookings.map((booking) => {
                  const statusConfig = FACILITATOR_STATUS_CONFIG[booking.status]
                  const StatusIcon = statusConfig.icon

                  return (
                    <Card key={booking.id} className="border-l-4 border-l-orange-500">
                      <CardContent className="p-4">
                        <div className="space-y-3">
                          {/* Header */}
                          <div className="flex items-start justify-between">
                            <div className="flex items-center gap-2">
                              <Users className="h-4 w-4 text-purple-600 dark:text-purple-400" />
                              <span className="font-medium">{booking.meeting_type.name}</span>
                              <Badge variant={statusConfig.variant}>
                                <StatusIcon className="h-3 w-3 mr-1" />
                                {statusConfig.label}
                              </Badge>
                            </div>
                            <div className="text-xs text-muted-foreground">
                              Created {format(parseISO(booking.created_at), 'MMM d, yyyy')}
                            </div>
                          </div>

                          {/* Participants */}
                          <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                              <div className="text-xs font-medium text-muted-foreground">Participant 1</div>
                              <div>
                                <p className="text-sm font-medium">{booking.participant_1_name}</p>
                                <p className="text-xs text-muted-foreground">{booking.participant_1_email}</p>
                              </div>
                              {booking.status === 'pending_p1' && (
                                <div className="flex items-center gap-2">
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    className="h-7 text-xs"
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      const link = booking.participant_1_link ||
                                        `${window.location.origin}/book/facilitator/${booking.participant_1_token}/participant1`
                                      navigator.clipboard.writeText(link)
                                      toast({
                                        title: 'Link copied!',
                                        description: 'Participant 1 booking link copied to clipboard',
                                      })
                                    }}
                                  >
                                    <Copy className="h-3 w-3 mr-1" />
                                    Copy Link
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    className="h-7 text-xs"
                                    onClick={async (e) => {
                                      e.stopPropagation()
                                      await resendInvitation(booking)
                                    }}
                                  >
                                    <Send className="h-3 w-3 mr-1" />
                                    Resend
                                  </Button>
                                </div>
                              )}
                              {booking.participant_1_completed_at && (
                                <Badge variant="outline" className="text-xs">
                                  <CheckCircle className="h-3 w-3 mr-1 text-green-600" />
                                  Completed
                                </Badge>
                              )}
                            </div>

                            <div className="space-y-2">
                              <div className="text-xs font-medium text-muted-foreground">Participant 2</div>
                              <div>
                                <p className="text-sm font-medium">{booking.participant_2_name}</p>
                                <p className="text-xs text-muted-foreground">{booking.participant_2_email}</p>
                              </div>
                              {booking.status === 'pending_p2' && (
                                <div className="flex items-center gap-2">
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    className="h-7 text-xs"
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      const link = booking.participant_2_link ||
                                        `${window.location.origin}/book/facilitator/${booking.participant_2_token}`
                                      navigator.clipboard.writeText(link)
                                      toast({
                                        title: 'Link copied!',
                                        description: 'Participant 2 booking link copied to clipboard',
                                      })
                                    }}
                                  >
                                    <Copy className="h-3 w-3 mr-1" />
                                    Copy Link
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    className="h-7 text-xs"
                                    onClick={async (e) => {
                                      e.stopPropagation()
                                      await resendInvitation(booking)
                                    }}
                                  >
                                    <Send className="h-3 w-3 mr-1" />
                                    Resend
                                  </Button>
                                </div>
                              )}
                              {booking.participant_2_completed_at && (
                                <Badge variant="outline" className="text-xs">
                                  <CheckCircle className="h-3 w-3 mr-1 text-green-600" />
                                  Confirmed
                                </Badge>
                              )}
                            </div>
                          </div>

                          {/* Progress Bar */}
                          <div className="flex items-center gap-3">
                            <div className="flex-1">
                              <div className="flex items-center justify-between text-xs mb-1">
                                <span>Progress</span>
                                <span className="text-muted-foreground">
                                  {booking.status === 'pending_p1' ? 'Step 1 of 2' : 'Step 2 of 2'}
                                </span>
                              </div>
                              <div className="h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                                <div
                                  className="h-full bg-orange-500 rounded-full transition-all"
                                  style={{ width: booking.status === 'pending_p1' ? '33%' : '66%' }}
                                />
                              </div>
                            </div>
                          </div>

                          {/* Expiry Warning */}
                          {booking.expires_at && (
                            <div className="text-xs text-muted-foreground flex items-center gap-1">
                              <AlertCircle className="h-3 w-3" />
                              Expires {format(parseISO(booking.expires_at), 'MMM d, yyyy')}
                            </div>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  )
                })}
              </div>
            )
          ) : filteredMeetings.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Calendar className="h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="text-lg font-medium mb-2">
                  {filters.searchQuery || filters.status !== 'all' || filters.meetingType !== 'all' || filters.dateRange !== 'all' 
                    ? 'No meetings found' 
                    : `No ${activeTab} meetings`}
                </h3>
                <p className="text-sm text-muted-foreground text-center">
                  {filters.searchQuery || filters.status !== 'all' || filters.meetingType !== 'all' || filters.dateRange !== 'all' ? (
                    <>Try adjusting your filters or search query</>
                  ) : (
                    <>
                      {activeTab === 'upcoming'
                        ? 'No upcoming meetings scheduled'
                        : activeTab === 'past'
                        ? 'No past meetings to show'
                        : 'No cancelled meetings'}
                    </>
                  )}
                </p>
              </CardContent>
            </Card>
          ) : (
            <>
              <div className="space-y-3">
                {paginatedMeetings.map((meeting) => {
                const statusBadge = STATUS_BADGES[meeting.status] || STATUS_BADGES.scheduled
                const StatusIcon = statusBadge.icon
                const LocationIcon = LOCATION_ICONS[meeting.meeting_type?.location_type] || Calendar

                // Calculate time until meeting for upcoming meetings
                const timeUntilMeeting = meeting.start_time ? 
                  Math.floor((new Date(meeting.start_time).getTime() - Date.now()) / (1000 * 60)) : null
                const isStartingSoon = timeUntilMeeting !== null && timeUntilMeeting > 0 && timeUntilMeeting <= 15

                return (
                  <Card 
                    key={meeting.id} 
                    className={`cursor-pointer hover:shadow-md transition-all ${
                      meeting.is_facilitator_meeting ? 'border-l-4 border-l-purple-500' : ''
                    } ${isStartingSoon ? 'ring-2 ring-primary ring-opacity-50' : ''}`}
                    onClick={() => openMeetingDetails(meeting)}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 space-y-3">
                          {/* Header Row */}
                          <div className="flex items-start justify-between">
                            <div className="flex items-center gap-3">
                              {meeting.is_facilitator_meeting && (
                                <div className="p-1.5 bg-purple-100 dark:bg-purple-900/30 rounded-md">
                                  <Users className="h-4 w-4 text-purple-600 dark:text-purple-400" />
                                </div>
                              )}
                              <div>
                                <h3 className="font-medium flex items-center gap-2">
                                  {meeting.meeting_type?.name || meeting.meeting_type_name || 'Unknown Meeting'}
                                  {meeting.is_facilitator_meeting && (
                                    <span className="text-xs text-purple-600 dark:text-purple-400 font-normal">
                                      (Facilitator)
                                    </span>
                                  )}
                                </h3>
                                {meeting.meeting_type?.duration_minutes && (
                                  <p className="text-xs text-muted-foreground mt-0.5">
                                    {meeting.meeting_type.duration_minutes} minutes
                                    {meeting.meeting_type?.buffer_time && ` • ${meeting.meeting_type.buffer_time}min buffer`}
                                  </p>
                                )}
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              {isStartingSoon && (
                                <Badge variant="default" className="animate-pulse">
                                  Starting in {timeUntilMeeting}m
                                </Badge>
                              )}
                              <Badge variant={statusBadge.variant}>
                                <StatusIcon className="h-3 w-3 mr-1" />
                                {statusBadge.label}
                              </Badge>
                            </div>
                          </div>

                          {/* Date, Time & Location Row */}
                          <div className="flex flex-wrap items-center gap-4 text-sm">
                            <div className="flex items-center gap-1.5 text-muted-foreground">
                              <Calendar className="h-3.5 w-3.5" />
                              <span className="font-medium">
                                {meeting.start_time ? format(parseISO(meeting.start_time), 'MMM d, yyyy') : 'No date'}
                              </span>
                            </div>
                            <div className="flex items-center gap-1.5 text-muted-foreground">
                              <Clock className="h-3.5 w-3.5" />
                              <span>
                                {meeting.start_time ? format(parseISO(meeting.start_time), 'h:mm a') : 'No time'}
                                {meeting.end_time && ` - ${format(parseISO(meeting.end_time), 'h:mm a')}`}
                              </span>
                            </div>
                            <div className="flex items-center gap-1.5">
                              <LocationIcon className="h-3.5 w-3.5 text-muted-foreground" />
                              <span className="text-muted-foreground">
                                {(() => {
                                  const locationType = meeting.meeting_type?.location_type
                                  if (locationType === 'google_meet') return 'Google Meet'
                                  if (locationType === 'zoom') return 'Zoom'
                                  if (locationType === 'teams') return 'MS Teams'
                                  if (locationType === 'phone') return meeting.meeting_location || 'Phone Call'
                                  if (locationType === 'in_person') return meeting.meeting_location || 'In Person'
                                  return meeting.meeting_location || 'TBD'
                                })()}
                              </span>
                              {meeting.meeting_url && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-6 px-2"
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    navigator.clipboard.writeText(meeting.meeting_url || '')
                                    toast({ title: 'Meeting link copied!' })
                                  }}
                                >
                                  <Copy className="h-3 w-3" />
                                </Button>
                              )}
                            </div>
                          </div>

                          {/* Meeting URL - More Visible */}
                          {meeting.meeting_url && (
                            <div className="flex items-center gap-2 mt-2">
                              <div className="flex items-center gap-2 px-2 py-1 bg-blue-50 dark:bg-blue-950/30 rounded-md">
                                <Video className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
                                <span className="text-sm font-medium text-blue-600 dark:text-blue-400">
                                  Meeting Link Available
                                </span>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-5 px-1.5 hover:bg-blue-100 dark:hover:bg-blue-900/50"
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    navigator.clipboard.writeText(meeting.meeting_url || '')
                                    toast({ title: 'Meeting link copied!' })
                                  }}
                                >
                                  <Copy className="h-3 w-3" />
                                </Button>
                              </div>
                            </div>
                          )}

                          {/* Participants Row */}
                          {meeting.is_facilitator_meeting && meeting.facilitator_booking ? (
                            <div className="space-y-2">
                              {/* Progress indicator for facilitator bookings */}
                              {meeting.facilitator_booking?.status === 'pending_p1' && (
                                <div className="flex items-center gap-3">
                                  <div className="flex-1">
                                    <div className="flex items-center justify-between text-xs mb-1">
                                      <span>Booking Progress</span>
                                      <span className="text-muted-foreground">Step 1 of 2</span>
                                    </div>
                                    <div className="h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                                      <div className="h-full w-1/3 bg-purple-500 rounded-full" />
                                    </div>
                                  </div>
                                </div>
                              )}
                              {meeting.facilitator_booking?.status === 'pending_p2' && (
                                <div className="flex items-center gap-3">
                                  <div className="flex-1">
                                    <div className="flex items-center justify-between text-xs mb-1">
                                      <span>Booking Progress</span>
                                      <span className="text-muted-foreground">Step 2 of 2</span>
                                    </div>
                                    <div className="h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                                      <div className="h-full w-2/3 bg-purple-500 rounded-full" />
                                    </div>
                                  </div>
                                </div>
                              )}
                              
                              <div className="grid grid-cols-2 gap-3">
                                <div className="flex items-start gap-2">
                                  <User className="h-3.5 w-3.5 text-muted-foreground mt-0.5" />
                                  <div className="min-w-0">
                                    <p className="text-sm font-medium truncate">
                                      {meeting.facilitator_booking?.participant_1_name || 'Participant 1'}
                                    </p>
                                    <p className="text-xs text-muted-foreground truncate">
                                      {meeting.facilitator_booking?.participant_1_email}
                                    </p>
                                    {meeting.facilitator_booking?.participant_1_completed_at && (
                                      <p className="text-xs text-green-600 dark:text-green-400 mt-0.5">
                                        ✓ Selected times
                                      </p>
                                    )}
                                  </div>
                                </div>
                                <div className="flex items-start gap-2">
                                  <User className="h-3.5 w-3.5 text-muted-foreground mt-0.5" />
                                  <div className="min-w-0">
                                    <p className="text-sm font-medium truncate">
                                      {meeting.facilitator_booking?.participant_2_name || 'Participant 2'}
                                    </p>
                                    <p className="text-xs text-muted-foreground truncate">
                                      {meeting.facilitator_booking?.participant_2_email}
                                    </p>
                                    {meeting.facilitator_booking?.participant_2_completed_at && (
                                      <p className="text-xs text-green-600 dark:text-green-400 mt-0.5">
                                        ✓ Confirmed
                                      </p>
                                    )}
                                  </div>
                                </div>
                              </div>
                            </div>
                          ) : (
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-3">
                                <div className="flex items-center gap-2">
                                  <User className="h-3.5 w-3.5 text-muted-foreground" />
                                  <span className="text-sm font-medium">
                                    {meeting.participant_detail?.name || meeting.participant?.name || 'Unknown'}
                                  </span>
                                </div>
                                <div className="flex items-center gap-2">
                                  <Mail className="h-3.5 w-3.5 text-muted-foreground" />
                                  <span className="text-sm text-muted-foreground">
                                    {meeting.participant_detail?.email || meeting.participant?.email || 'No email'}
                                  </span>
                                </div>
                              </div>
                              {meeting.participant_detail?.phone && (
                                <div className="flex items-center gap-2">
                                  <Phone className="h-3.5 w-3.5 text-muted-foreground" />
                                  <span className="text-sm text-muted-foreground">
                                    {meeting.participant_detail?.phone}
                                  </span>
                                </div>
                              )}
                            </div>
                          )}

                          {/* Notes preview if available */}
                          {meeting.participant_detail?.notes && (
                            <div className="p-2 bg-gray-50 dark:bg-gray-800/50 rounded-md">
                              <p className="text-xs text-muted-foreground line-clamp-2">
                                {meeting.participant_detail?.notes}
                              </p>
                            </div>
                          )}
                        </div>

                        <DropdownMenu>
                          <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                            <Button variant="ghost" size="sm">
                              <MoreVertical className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem
                              onClick={(e) => {
                                e.stopPropagation()
                                openMeetingDetails(meeting)
                              }}
                            >
                              <Eye className="h-4 w-4 mr-2" />
                              View Details
                            </DropdownMenuItem>
                            {meeting.meeting_url && (
                              <>
                                <DropdownMenuItem
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    window.open(meeting.meeting_url, '_blank')
                                  }}
                                >
                                  <ExternalLink className="h-4 w-4 mr-2" />
                                  Join Meeting
                                </DropdownMenuItem>
                                <DropdownMenuItem
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    navigator.clipboard.writeText(meeting.meeting_url || '')
                                    toast({ title: 'Meeting link copied!' })
                                  }}
                                >
                                  <Copy className="h-4 w-4 mr-2" />
                                  Copy Link
                                </DropdownMenuItem>
                              </>
                            )}
                            {(meeting.status === 'scheduled' || meeting.status === 'pending' || meeting.status === 'reminder_sent') && (
                              <>
                                <DropdownMenuSeparator />
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
                              </>
                            )}
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                    </CardContent>
                  </Card>
                )
              })}
              </div>
              
              {/* Pagination Controls */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between pt-4">
                  <div className="text-sm text-muted-foreground">
                    Showing {((currentPage - 1) * itemsPerPage) + 1}-{Math.min(currentPage * itemsPerPage, filteredMeetings.length)} of {filteredMeetings.length} meetings
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                      disabled={currentPage === 1}
                    >
                      Previous
                    </Button>
                    <div className="flex items-center gap-1">
                      {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                        let pageNum
                        if (totalPages <= 5) {
                          pageNum = i + 1
                        } else if (currentPage <= 3) {
                          pageNum = i + 1
                        } else if (currentPage >= totalPages - 2) {
                          pageNum = totalPages - 4 + i
                        } else {
                          pageNum = currentPage - 2 + i
                        }
                        return (
                          <Button
                            key={pageNum}
                            variant={pageNum === currentPage ? "default" : "outline"}
                            size="sm"
                            className="w-8 h-8 p-0"
                            onClick={() => setCurrentPage(pageNum)}
                          >
                            {pageNum}
                          </Button>
                        )
                      })}
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                      disabled={currentPage === totalPages}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </TabsContent>
      </Tabs>

      <Dialog open={isDetailsOpen} onOpenChange={setIsDetailsOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center justify-between">
              <span>{selectedMeeting?.meeting_type?.name}</span>
              {selectedMeeting && (
                <Badge variant={STATUS_BADGES[selectedMeeting.status].variant}>
                  {STATUS_BADGES[selectedMeeting.status].label}
                </Badge>
              )}
            </DialogTitle>
            <DialogDescription>
              {selectedMeeting?.host_name && `Hosted by ${selectedMeeting.host_name}`}
            </DialogDescription>
          </DialogHeader>
          {selectedMeeting && (
            <div className="space-y-4 mt-4">
              {/* Meeting Details - Compact Grid */}
              <div className="grid gap-3 md:grid-cols-2">
                {/* Date & Time Info */}
                <div className="border rounded-lg p-3 space-y-2">
                  <div className="flex items-center gap-2 text-sm font-medium">
                    <Calendar className="h-3 w-3" />
                    Meeting Schedule
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm">
                      {selectedMeeting?.start_time ? format(parseISO(selectedMeeting.start_time), 'MMM d, yyyy') : 'No date'}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {selectedMeeting?.start_time ? format(parseISO(selectedMeeting.start_time), 'h:mm a') : 'No time'}
                      {selectedMeeting?.end_time && ` - ${format(parseISO(selectedMeeting.end_time), 'h:mm a')}`}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {selectedMeeting?.start_time && selectedMeeting?.end_time ? 
                        `${Math.round((new Date(selectedMeeting.end_time).getTime() - new Date(selectedMeeting.start_time).getTime()) / 60000)} minutes` : 
                        'Duration not available'}
                    </p>
                  </div>
                </div>

                {/* Participant Info */}
                <div className="border rounded-lg p-3 space-y-2">
                  <div className="flex items-center gap-2 text-sm font-medium">
                    <User className="h-3 w-3" />
                    Participant
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm font-medium">
                      {selectedMeeting?.participant_detail?.name || selectedMeeting?.participant?.name || 'Unknown'}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {selectedMeeting?.participant_detail?.email || selectedMeeting?.participant?.email || 'No email'}
                    </p>
                    {(selectedMeeting?.participant_detail?.phone || selectedMeeting?.participant?.phone) && (
                      <p className="text-xs text-muted-foreground">
                        {selectedMeeting?.participant_detail?.phone || selectedMeeting?.participant?.phone}
                      </p>
                    )}
                  </div>
                </div>
              </div>

              {/* Location Info - Compact Display */}
              <div className="border rounded-lg p-3 bg-muted/30">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground flex items-center gap-1">
                    <MapPin className="h-3 w-3" />
                    Location
                  </span>
                  <span className="font-medium">
                    {LOCATION_DISPLAY[selectedMeeting?.meeting_type?.location_type] || 
                     selectedMeeting?.meeting_type?.location_type?.replace('_', ' ') || 
                     'No location'}
                  </span>
                </div>
              </div>

              {/* Meeting Link - Enhanced */}
              {selectedMeeting?.meeting_url && (
                <div className="border-2 border-blue-200 dark:border-blue-800 rounded-lg p-3 bg-blue-50 dark:bg-blue-950/20">
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <Video className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                      <span className="text-sm font-semibold text-blue-600 dark:text-blue-400">
                        Meeting Link
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Input 
                        value={selectedMeeting?.meeting_url || ''} 
                        readOnly 
                        className="h-8 text-xs font-mono flex-1 bg-white dark:bg-gray-900"
                      />
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-8 px-2"
                        onClick={() => {
                          navigator.clipboard.writeText(selectedMeeting?.meeting_url || '')
                          toast({
                            title: 'Link copied!',
                            description: 'Meeting link copied to clipboard',
                          })
                        }}
                      >
                        <Copy className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        size="sm"
                        variant="default"
                        className="h-8 px-3 bg-blue-600 hover:bg-blue-700"
                        onClick={() => window.open(selectedMeeting?.meeting_url, '_blank')}
                      >
                        <ExternalLink className="h-3.5 w-3.5 mr-1.5" />
                        Join Meeting
                      </Button>
                    </div>
                  </div>
                </div>
              )}

              {/* Notes - Compact */}
              {(selectedMeeting?.pre_meeting_notes || selectedMeeting?.post_meeting_notes) && (
                <div className="border rounded-lg p-3 space-y-2">
                  <div className="flex items-center gap-2 text-sm font-medium">
                    <AlertCircle className="h-3 w-3" />
                    Notes
                  </div>
                  {selectedMeeting?.pre_meeting_notes && (
                    <div>
                      <p className="text-xs text-muted-foreground">Pre-meeting:</p>
                      <p className="text-xs">{selectedMeeting?.pre_meeting_notes}</p>
                    </div>
                  )}
                  {selectedMeeting?.post_meeting_notes && (
                    <div>
                      <p className="text-xs text-muted-foreground">Post-meeting:</p>
                      <p className="text-xs">{selectedMeeting?.post_meeting_notes}</p>
                    </div>
                  )}
                </div>
              )}

              {/* Action Buttons - Compact Footer */}
              <div className="flex justify-between items-center pt-3">
                <div className="flex gap-2">
                  {(selectedMeeting?.status === 'scheduled' || selectedMeeting?.status === 'pending' || selectedMeeting?.status === 'reminder_sent') && (
                    <Button
                      size="sm"
                      variant="destructive"
                      className="h-8 text-xs"
                      onClick={() => {
                        cancelMeeting(selectedMeeting)
                        setIsDetailsOpen(false)
                      }}
                    >
                      <XCircle className="h-3 w-3 mr-1" />
                      Cancel Meeting
                    </Button>
                  )}
                </div>
                <Button size="sm" variant="outline" onClick={() => setIsDetailsOpen(false)}>
                  Close
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Facilitator Booking Details Dialog */}
      <Dialog open={isFacilitatorModalOpen} onOpenChange={setIsFacilitatorModalOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center justify-between">
              <span>{selectedFacilitatorBooking?.meeting_type?.name}</span>
              {selectedFacilitatorBooking && (
                <Badge variant={FACILITATOR_STATUS_CONFIG[selectedFacilitatorBooking.status].variant}>
                  {FACILITATOR_STATUS_CONFIG[selectedFacilitatorBooking.status].label}
                </Badge>
              )}
            </DialogTitle>
            <DialogDescription>
              Facilitated by {selectedFacilitatorBooking?.facilitator?.username || 'Unknown'}
            </DialogDescription>
          </DialogHeader>
          
          {selectedFacilitatorBooking && (
            <div className="space-y-4 mt-4">
              {/* Participants - Compact Grid */}
              <div className="grid gap-3 md:grid-cols-2">
                {/* Participant 1 */}
                <div className="border rounded-lg p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium flex items-center gap-1">
                      <Users className="h-3 w-3" />
                      Participant 1
                    </span>
                    {selectedFacilitatorBooking?.participant_1_completed_at && (
                      <Badge variant="outline" className="h-5 text-xs">
                        <CheckCircle className="h-3 w-3 mr-1" />
                        Done
                      </Badge>
                    )}
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm font-medium">{selectedFacilitatorBooking?.participant_1_name}</p>
                    <p className="text-xs text-muted-foreground">{selectedFacilitatorBooking?.participant_1_email}</p>
                    {selectedFacilitatorBooking?.participant_1_phone && (
                      <p className="text-xs text-muted-foreground">{selectedFacilitatorBooking?.participant_1_phone}</p>
                    )}
                  </div>
                  {selectedFacilitatorBooking?.status === 'pending_p1' && (
                    <div className="flex gap-2 pt-1">
                      <Button
                        size="sm"
                        variant="outline"
                        className="flex-1 h-7 text-xs"
                        onClick={() => copyLink(selectedFacilitatorBooking?.participant_1_token, 1)}
                      >
                        <Copy className="h-3 w-3 mr-1" />
                        Copy Link
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        className="flex-1 h-7 text-xs"
                        onClick={() => resendInvitation(selectedFacilitatorBooking)}
                      >
                        <Send className="h-3 w-3 mr-1" />
                        Resend
                      </Button>
                    </div>
                  )}
                </div>

                {/* Participant 2 */}
                <div className="border rounded-lg p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium flex items-center gap-1">
                      <Users className="h-3 w-3" />
                      Participant 2
                    </span>
                    {selectedFacilitatorBooking?.participant_2_completed_at && (
                      <Badge variant="outline" className="h-5 text-xs">
                        <CheckCircle className="h-3 w-3 mr-1" />
                        Done
                      </Badge>
                    )}
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm font-medium">{selectedFacilitatorBooking?.participant_2_name}</p>
                    <p className="text-xs text-muted-foreground">{selectedFacilitatorBooking?.participant_2_email}</p>
                    {selectedFacilitatorBooking?.participant_2_phone && (
                      <p className="text-xs text-muted-foreground">{selectedFacilitatorBooking?.participant_2_phone}</p>
                    )}
                  </div>
                  {selectedFacilitatorBooking?.status === 'pending_p2' && (
                    <div className="flex gap-2 pt-1">
                      <Button
                        size="sm"
                        variant="outline"
                        className="flex-1 h-7 text-xs"
                        onClick={() => copyLink(selectedFacilitatorBooking?.participant_2_token, 2)}
                      >
                        <Copy className="h-3 w-3 mr-1" />
                        Copy Link
                      </Button>
                    </div>
                  )}
                </div>
              </div>

              {/* Meeting Configuration - Compact Display */}
              {selectedFacilitatorBooking?.selected_duration_minutes && (
                <div className="border rounded-lg p-3 bg-muted/30">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Meeting Configuration</span>
                    <div className="flex items-center gap-3">
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {selectedFacilitatorBooking?.selected_duration_minutes} min
                      </span>
                      {selectedFacilitatorBooking?.selected_location_type && (
                        <span className="flex items-center gap-1">
                          <MapPin className="h-3 w-3" />
                          {LOCATION_DISPLAY[selectedFacilitatorBooking?.selected_location_type]}
                        </span>
                      )}
                    </div>
                  </div>
                  {selectedFacilitatorBooking?.participant_1_message && (
                    <p className="text-xs text-muted-foreground mt-2 italic">
                      Note: {selectedFacilitatorBooking?.participant_1_message}
                    </p>
                  )}
                </div>
              )}

              {/* Available Time Slots - Compact List */}
              {selectedFacilitatorBooking?.selected_slots && selectedFacilitatorBooking?.selected_slots.length > 0 && (
                <div className="border rounded-lg p-3">
                  <p className="text-sm font-medium mb-2">Available Time Slots</p>
                  <div className="space-y-1 max-h-32 overflow-y-auto">
                    {selectedFacilitatorBooking?.selected_slots.map((slot, index) => (
                      <div key={index} className="flex items-center gap-2 text-xs text-muted-foreground py-1">
                        <Calendar className="h-3 w-3" />
                        <span>
                          {format(parseISO(slot.start), 'MMM d, h:mm a')} - {format(parseISO(slot.end), 'h:mm a')}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Confirmed Meeting Details - Combined Section */}
              {(selectedFacilitatorBooking?.final_slot || selectedFacilitatorMeeting?.meeting_url) && (
                <div className="border rounded-lg p-3 bg-green-50 dark:bg-green-950/20">
                  <div className="flex items-center gap-2 mb-2">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    <span className="text-sm font-medium">Meeting Confirmed</span>
                  </div>
                  
                  {selectedFacilitatorBooking?.final_slot && (
                    <div className="flex items-center gap-4 text-sm text-muted-foreground mb-2">
                      <span className="flex items-center gap-1">
                        <Calendar className="h-3 w-3" />
                        {selectedFacilitatorBooking?.final_slot?.start ? format(parseISO(selectedFacilitatorBooking.final_slot.start), 'MMM d, yyyy') : 'No date'}
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {selectedFacilitatorBooking?.final_slot?.start ? format(parseISO(selectedFacilitatorBooking.final_slot.start), 'h:mm a') : 'No time'} - 
                        {selectedFacilitatorBooking?.final_slot?.end ? format(parseISO(selectedFacilitatorBooking.final_slot.end), 'h:mm a') : 'No time'}
                      </span>
                    </div>
                  )}
                  
                  {selectedFacilitatorMeeting?.meeting_url && (
                    <div className="mt-3 pt-3 border-t space-y-2">
                      <div className="flex items-center gap-2">
                        <Video className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                        <span className="text-sm font-semibold text-blue-600 dark:text-blue-400">
                          Meeting Link
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Input 
                          value={selectedFacilitatorMeeting?.meeting_url || ''} 
                          readOnly 
                          className="h-8 text-xs font-mono flex-1 bg-white dark:bg-gray-900"
                        />
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-8 px-2"
                          onClick={() => {
                            navigator.clipboard.writeText(selectedFacilitatorMeeting?.meeting_url || '')
                            toast({
                              title: 'Link copied!',
                              description: 'Meeting link copied to clipboard',
                            })
                          }}
                        >
                          <Copy className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          size="sm"
                          variant="default"
                          className="h-8 px-3 bg-blue-600 hover:bg-blue-700"
                          onClick={() => window.open(selectedFacilitatorMeeting?.meeting_url, '_blank')}
                        >
                          <ExternalLink className="h-3.5 w-3.5 mr-1.5" />
                          Join Meeting
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Expiry Warning - Compact */}
              {selectedFacilitatorBooking?.status !== 'completed' && selectedFacilitatorBooking?.status !== 'cancelled' && (
                <div className="flex items-center gap-2 p-2 bg-amber-50 dark:bg-amber-950/20 rounded text-xs text-amber-700 dark:text-amber-400">
                  <AlertCircle className="h-3 w-3" />
                  <span>Expires {selectedFacilitatorBooking?.expires_at ? format(parseISO(selectedFacilitatorBooking.expires_at), 'MMM d, h:mm a') : 'Unknown'}</span>
                </div>
              )}

              <div className="flex justify-end pt-3">
                <Button size="sm" variant="outline" onClick={() => setIsFacilitatorModalOpen(false)}>
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