'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { CalendarIcon, Clock, Plus, Trash2, Edit, Save, X, RefreshCw } from 'lucide-react'
import { useAuth } from '@/features/auth/context'
import { useToast } from '@/hooks/use-toast'
import api from '@/lib/api'

interface WorkingHours {
  [key: string]: {
    enabled: boolean
    start: string
    end: string
    breaks?: Array<{ start: string; end: string }>
  }
}

interface CalendarConnection {
  id: string
  account_name: string
  channel_type: string
  auth_status: string
  unipile_account_id: string
}

interface SchedulingProfile {
  id: string
  user: string
  calendar_connection?: string
  calendar_connection_display?: {
    id: string
    account_name: string
    channel_type: string
    auth_status: string
  }
  timezone: string
  working_hours: { [key: string]: Array<{ start: string; end: string }> }
  buffer_minutes: number
  min_notice_hours: number
  max_advance_days: number
  slot_interval_minutes?: number
  calendar_sync_enabled: boolean
  show_busy_slots: boolean
  blocked_dates: string[]
  override_dates: { [key: string]: any }
  is_active: boolean
  availability_overrides?: AvailabilityOverride[]
  created_at: string
  updated_at: string
}

interface AvailabilityOverride {
  id: string
  profile: string
  date: string
  is_available: boolean
  time_slots?: Array<{ start: string; end: string }>
  reason?: string
}

const DAYS = [
  { key: 'monday', label: 'Monday' },
  { key: 'tuesday', label: 'Tuesday' },
  { key: 'wednesday', label: 'Wednesday' },
  { key: 'thursday', label: 'Thursday' },
  { key: 'friday', label: 'Friday' },
  { key: 'saturday', label: 'Saturday' },
  { key: 'sunday', label: 'Sunday' },
]

const TIMEZONES = [
  { value: 'Pacific/Midway', label: 'GMT-11:00 (Midway Island, Samoa)' },
  { value: 'Pacific/Honolulu', label: 'GMT-10:00 (Hawaii)' },
  { value: 'America/Anchorage', label: 'GMT-09:00 (Alaska)' },
  { value: 'America/Los_Angeles', label: 'GMT-08:00 (Pacific Time US & Canada)' },
  { value: 'America/Denver', label: 'GMT-07:00 (Mountain Time US & Canada)' },
  { value: 'America/Chicago', label: 'GMT-06:00 (Central Time US & Canada)' },
  { value: 'America/New_York', label: 'GMT-05:00 (Eastern Time US & Canada)' },
  { value: 'America/Caracas', label: 'GMT-04:00 (Caracas, La Paz)' },
  { value: 'America/Buenos_Aires', label: 'GMT-03:00 (Buenos Aires, Georgetown)' },
  { value: 'Atlantic/South_Georgia', label: 'GMT-02:00 (Mid-Atlantic)' },
  { value: 'Atlantic/Azores', label: 'GMT-01:00 (Azores, Cape Verde)' },
  { value: 'GMT', label: 'GMT+00:00 (Greenwich Mean Time)' },
  { value: 'Europe/London', label: 'GMT+00:00 (London, Dublin, Lisbon)' },
  { value: 'Europe/Paris', label: 'GMT+01:00 (Paris, Berlin, Rome)' },
  { value: 'Europe/Athens', label: 'GMT+02:00 (Athens, Cairo, Jerusalem)' },
  { value: 'Africa/Johannesburg', label: 'GMT+02:00 (Johannesburg, Cape Town) - SAST' },
  { value: 'Europe/Moscow', label: 'GMT+03:00 (Moscow, St. Petersburg)' },
  { value: 'Asia/Dubai', label: 'GMT+04:00 (Abu Dhabi, Dubai)' },
  { value: 'Asia/Karachi', label: 'GMT+05:00 (Islamabad, Karachi)' },
  { value: 'Asia/Kolkata', label: 'GMT+05:30 (Mumbai, Kolkata, New Delhi)' },
  { value: 'Asia/Dhaka', label: 'GMT+06:00 (Dhaka, Almaty)' },
  { value: 'Asia/Bangkok', label: 'GMT+07:00 (Bangkok, Jakarta)' },
  { value: 'Asia/Shanghai', label: 'GMT+08:00 (Beijing, Hong Kong, Singapore)' },
  { value: 'Asia/Tokyo', label: 'GMT+09:00 (Tokyo, Seoul)' },
  { value: 'Australia/Sydney', label: 'GMT+10:00 (Sydney, Melbourne)' },
  { value: 'Pacific/Noumea', label: 'GMT+11:00 (Noumea, Solomon Islands)' },
  { value: 'Pacific/Auckland', label: 'GMT+12:00 (Auckland, Wellington)' },
]

interface AvailabilitySettingsProps {
  canManageAll?: boolean
}

export default function AvailabilitySettings({ canManageAll = false }: AvailabilitySettingsProps) {
  const { user } = useAuth()
  const { toast } = useToast()
  const [profile, setProfile] = useState<SchedulingProfile | null>(null)
  const [overrides, setOverrides] = useState<AvailabilityOverride[]>([])
  const [calendarConnections, setCalendarConnections] = useState<CalendarConnection[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [editingDay, setEditingDay] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState('availability')
  const [workingHours, setWorkingHours] = useState<WorkingHours>({
    monday: { enabled: true, start: '09:00', end: '17:00' },
    tuesday: { enabled: true, start: '09:00', end: '17:00' },
    wednesday: { enabled: true, start: '09:00', end: '17:00' },
    thursday: { enabled: true, start: '09:00', end: '17:00' },
    friday: { enabled: true, start: '09:00', end: '17:00' },
    saturday: { enabled: false, start: '09:00', end: '17:00' },
    sunday: { enabled: false, start: '09:00', end: '17:00' },
  })

  useEffect(() => {
    fetchCalendarConnections()
    fetchProfile()
    fetchOverrides()
  }, [])

  const fetchCalendarConnections = async () => {
    try {
      const response = await api.get('/api/v1/communications/scheduling/profiles/calendar_connections/')
      setCalendarConnections(response.data.connections || [])
    } catch (error) {
      console.error('Failed to fetch calendar connections:', error)
    }
  }

  const fetchProfile = async () => {
    setIsLoading(true)
    try {
      // Backend API already filters based on permissions (scheduling_all shows all, scheduling shows own)
      const response = await api.get('/api/v1/communications/scheduling/profiles/')
      if (response.data.results && response.data.results.length > 0) {
        const profileData = response.data.results[0]
        setProfile(profileData)
        // Convert working hours to UI format
        const convertedHours: WorkingHours = {}
        DAYS.forEach(day => {
          const dayHours = profileData.working_hours[day.key] || []
          convertedHours[day.key] = {
            enabled: dayHours.length > 0,
            start: dayHours[0]?.start || '09:00',
            end: dayHours[0]?.end || '17:00',
          }
        })
        setWorkingHours(convertedHours)
      } else {
        // Create default profile if none exists
        const defaultProfile = await createDefaultProfile()
        setProfile(defaultProfile)
      }
    } catch (error) {
      console.error('Failed to fetch scheduling profile:', error)
      toast({
        title: 'Error',
        description: 'Failed to load availability settings',
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  const createDefaultProfile = async () => {
    const defaultWorkingHours = {
      monday: [{ start: '09:00', end: '17:00' }],
      tuesday: [{ start: '09:00', end: '17:00' }],
      wednesday: [{ start: '09:00', end: '17:00' }],
      thursday: [{ start: '09:00', end: '17:00' }],
      friday: [{ start: '09:00', end: '17:00' }],
      saturday: [],
      sunday: [],
    }

    try {
      const response = await api.post('/api/v1/communications/scheduling/profiles/', {
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'America/New_York',
        working_hours: defaultWorkingHours,
        buffer_minutes: 0,
        min_notice_hours: 1,
        max_advance_days: 60,
        calendar_sync_enabled: false,
        show_busy_slots: false,
        blocked_dates: [],
        override_dates: {},
        is_active: true,
      })
      return response.data
    } catch (error: any) {
      console.error('Failed to create default profile:', {
        status: error.response?.status,
        data: error.response?.data,
        message: error.message,
        config: error.config?.data
      })
      throw error
    }
  }

  const fetchOverrides = async () => {
    try {
      const response = await api.get('/api/v1/communications/scheduling/overrides/')
      setOverrides(response.data.results || [])
    } catch (error) {
      console.error('Failed to fetch overrides:', error)
    }
  }

  const updateProfile = async (updates: Partial<SchedulingProfile>) => {
    if (!profile) return

    // Convert WorkingHours format to API format if updating working_hours
    let apiUpdates = { ...updates }
    if (updates.working_hours) {
      // Already in correct format from toggleDayEnabled or saveDayHours
      apiUpdates = updates
    }

    setIsSaving(true)
    try {
      const response = await api.patch(
        `/api/v1/communications/scheduling/profiles/${profile.id}/`,
        apiUpdates
      )
      setProfile(response.data)
      toast({
        title: 'Success',
        description: 'Availability settings updated',
      })
    } catch (error) {
      console.error('Failed to update profile:', error)
      toast({
        title: 'Error',
        description: 'Failed to update settings',
        variant: 'destructive',
      })
    } finally {
      setIsSaving(false)
    }
  }

  const toggleDayEnabled = (day: string) => {
    if (!profile) return

    const newWorkingHours = { ...workingHours }
    newWorkingHours[day] = {
      ...newWorkingHours[day],
      enabled: !newWorkingHours[day].enabled,
    }
    setWorkingHours(newWorkingHours)

    // Convert to API format
    const apiWorkingHours: { [key: string]: Array<{ start: string; end: string }> } = {}
    DAYS.forEach(d => {
      if (newWorkingHours[d.key].enabled) {
        apiWorkingHours[d.key] = [{
          start: newWorkingHours[d.key].start,
          end: newWorkingHours[d.key].end,
        }]
      } else {
        apiWorkingHours[d.key] = []
      }
    })

    updateProfile({ working_hours: apiWorkingHours })
  }

  const updateDayHours = (day: string, field: 'start' | 'end', value: string) => {
    const newWorkingHours = { ...workingHours }
    newWorkingHours[day] = {
      ...newWorkingHours[day],
      [field]: value,
    }
    setWorkingHours(newWorkingHours)
  }

  const saveDayHours = (day: string) => {
    if (!profile) return
    
    // Convert to API format
    const apiWorkingHours: { [key: string]: Array<{ start: string; end: string }> } = {}
    DAYS.forEach(d => {
      if (workingHours[d.key].enabled) {
        apiWorkingHours[d.key] = [{
          start: workingHours[d.key].start,
          end: workingHours[d.key].end,
        }]
      } else {
        apiWorkingHours[d.key] = []
      }
    })

    updateProfile({ working_hours: apiWorkingHours })
    setEditingDay(null)
  }

  const syncCalendars = async () => {
    toast({
      title: 'Info',
      description: 'Calendar sync will be available soon',
    })
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="availability">Availability</TabsTrigger>
          <TabsTrigger value="calendars">Calendar Sync</TabsTrigger>
        </TabsList>

        <TabsContent value="availability" className="mt-4">
          <div className="grid gap-4 lg:grid-cols-2">
            {/* Working Hours Card */}
            <Card>
              <CardHeader>
                <CardTitle>Weekly Schedule</CardTitle>
                <CardDescription>
                  Set your regular working hours
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Timezone Selection */}
                <div className="space-y-2">
                  <Label htmlFor="timezone">Timezone</Label>
                  <Select
                    value={profile?.timezone}
                    onValueChange={(value) => updateProfile({ timezone: value })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select timezone" />
                    </SelectTrigger>
                    <SelectContent>
                      {TIMEZONES.map((tz) => (
                        <SelectItem key={tz.value} value={tz.value}>
                          {tz.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Working Hours */}
                <div className="space-y-2">
                  {DAYS.map((day) => {
                    const dayHours = workingHours[day.key]
                    const isEditing = editingDay === day.key

                    return (
                      <div
                        key={day.key}
                        className="flex items-center justify-between py-2 border-b last:border-0"
                      >
                        <div className="flex items-center space-x-2">
                          <Switch
                            checked={dayHours?.enabled || false}
                            onCheckedChange={() => toggleDayEnabled(day.key)}
                          />
                          <Label
                            className={`w-20 text-sm ${!dayHours?.enabled ? 'text-muted-foreground' : ''}`}
                          >
                            {day.label}
                          </Label>
                        </div>

                        {dayHours?.enabled && (
                          <div className="flex items-center space-x-1">
                            {isEditing ? (
                              <>
                                <Input
                                  type="time"
                                  value={dayHours.start}
                                  onChange={(e) => updateDayHours(day.key, 'start', e.target.value)}
                                  className="w-20 h-8"
                                />
                                <span className="text-xs">-</span>
                                <Input
                                  type="time"
                                  value={dayHours.end}
                                  onChange={(e) => updateDayHours(day.key, 'end', e.target.value)}
                                  className="w-20 h-8"
                                />
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => saveDayHours(day.key)}
                                  disabled={isSaving}
                                  className="h-8 w-8 p-0"
                                >
                                  <Save className="h-3 w-3" />
                                </Button>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => setEditingDay(null)}
                                  className="h-8 w-8 p-0"
                                >
                                  <X className="h-3 w-3" />
                                </Button>
                              </>
                            ) : (
                              <>
                                <span className="text-sm text-muted-foreground">
                                  {dayHours.start} - {dayHours.end}
                                </span>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => setEditingDay(day.key)}
                                  className="h-8 w-8 p-0"
                                >
                                  <Edit className="h-3 w-3" />
                                </Button>
                              </>
                            )}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              </CardContent>
            </Card>

            {/* Booking Rules Card */}
            <Card>
              <CardHeader>
                <CardTitle>Booking Rules</CardTitle>
                <CardDescription>
                  Configure scheduling parameters
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="minimum-notice">Minimum Notice</Label>
                    <div className="flex items-center space-x-2">
                      <Input
                        id="minimum-notice"
                        type="number"
                        value={profile?.min_notice_hours || 1}
                        onChange={(e) =>
                          updateProfile({ min_notice_hours: parseInt(e.target.value) })
                        }
                        className="w-24"
                      />
                      <span className="text-sm text-muted-foreground">hours</span>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Minimum time before a meeting can be booked
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="maximum-advance">Maximum Advance Booking</Label>
                    <div className="flex items-center space-x-2">
                      <Input
                        id="maximum-advance"
                        type="number"
                        value={profile?.max_advance_days || 60}
                        onChange={(e) =>
                          updateProfile({ max_advance_days: parseInt(e.target.value) })
                        }
                        className="w-24"
                      />
                      <span className="text-sm text-muted-foreground">days</span>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      How far in advance meetings can be scheduled
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="buffer-minutes">Meeting Buffer</Label>
                    <div className="flex items-center space-x-2">
                      <Input
                        id="buffer-minutes"
                        type="number"
                        value={profile?.buffer_minutes || 0}
                        onChange={(e) =>
                          updateProfile({ buffer_minutes: parseInt(e.target.value) })
                        }
                        className="w-24"
                      />
                      <span className="text-sm text-muted-foreground">minutes</span>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Buffer time between meetings
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="slot-interval">Time Slot Interval</Label>
                    <Select
                      value={String(profile?.slot_interval_minutes || 30)}
                      onValueChange={(value) =>
                        updateProfile({ slot_interval_minutes: parseInt(value) })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="15">15 minutes</SelectItem>
                        <SelectItem value="20">20 minutes</SelectItem>
                        <SelectItem value="30">30 minutes</SelectItem>
                        <SelectItem value="45">45 minutes</SelectItem>
                        <SelectItem value="60">60 minutes</SelectItem>
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-muted-foreground">
                      Incremental slots for availability
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="calendars" className="space-y-4 mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Calendar Integration</CardTitle>
              <CardDescription>
                Select which calendar to use for availability checking
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Calendar Selection */}
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label>Select Calendar Account</Label>
                  <p className="text-sm text-muted-foreground">
                    Choose which connected calendar to use for scheduling
                  </p>
                  {calendarConnections.length > 0 ? (
                    <Select
                      value={profile?.calendar_connection || 'none'}
                      onValueChange={(value) => {
                        const connectionId = value === 'none' ? undefined : value
                        updateProfile({ calendar_connection: connectionId })
                      }}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select a calendar" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">
                          <span className="text-muted-foreground">No calendar selected</span>
                        </SelectItem>
                        {calendarConnections.map((conn) => (
                          <SelectItem key={conn.id} value={conn.id}>
                            <div className="flex items-center gap-2">
                              <CalendarIcon className="h-4 w-4" />
                              <span>{conn.account_name}</span>
                              <span className="text-xs text-muted-foreground">
                                ({conn.channel_type === 'gmail' ? 'Google' : 
                                  conn.channel_type === 'outlook' ? 'Outlook' : 
                                  'Calendar'})
                              </span>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  ) : (
                    <div className="text-center py-6 border-2 border-dashed rounded-lg">
                      <CalendarIcon className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
                      <p className="text-sm text-muted-foreground mb-3">
                        No calendar accounts connected yet
                      </p>
                      <p className="text-xs text-muted-foreground">
                        To use scheduling, first connect your Google or Outlook calendar through the Communications settings
                      </p>
                    </div>
                  )}
                </div>

                {/* Calendar Sync Settings */}
                <div className="flex items-center justify-between py-3 border-t">
                  <div className="space-y-1">
                    <Label>Check for Conflicts</Label>
                    <p className="text-sm text-muted-foreground">
                      Block times when you have existing calendar events
                    </p>
                  </div>
                  <Switch
                    checked={profile?.calendar_sync_enabled || false}
                    onCheckedChange={(checked) =>
                      updateProfile({ calendar_sync_enabled: checked })
                    }
                    disabled={!profile?.calendar_connection}
                  />
                </div>

                <div className="flex items-center justify-between py-3">
                  <div className="space-y-1">
                    <Label>Show Busy Times</Label>
                    <p className="text-sm text-muted-foreground">
                      Display busy slots to visitors (without details)
                    </p>
                  </div>
                  <Switch
                    checked={profile?.show_busy_slots || false}
                    onCheckedChange={(checked) =>
                      updateProfile({ show_busy_slots: checked })
                    }
                    disabled={!profile?.calendar_sync_enabled}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}