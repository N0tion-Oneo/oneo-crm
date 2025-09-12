import React, { useState } from 'react'
import { Calendar, Clock, Video, MapPin, Globe, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { api } from '@/lib/api'
import { toast } from '@/hooks/use-toast'

interface EventSchedulerProps {
  recordId: string
  onEventScheduled?: () => void
  onCancel?: () => void
  defaultParticipant?: {
    email?: string
    name?: string
    phone?: string
  }
}

export function EventScheduler({
  recordId,
  onEventScheduled,
  onCancel,
  defaultParticipant
}: EventSchedulerProps) {
  const [title, setTitle] = useState('')
  const [participantEmails, setParticipantEmails] = useState(defaultParticipant?.email || '')
  const [location, setLocation] = useState('')
  const [locationType, setLocationType] = useState<'google_meet' | 'teams' | 'zoom' | 'in_person' | 'other'>('google_meet')
  const [selectedDate, setSelectedDate] = useState('')
  const [startTime, setStartTime] = useState('')
  const [endTime, setEndTime] = useState('')
  const [description, setDescription] = useState('')
  const [isCreating, setIsCreating] = useState(false)

  const handleCreate = async () => {
    // Validate required fields
    if (!title || !selectedDate || !startTime) {
      toast({
        title: 'Missing Information',
        description: 'Please fill in the required fields (title, date, start time)',
        variant: 'destructive'
      })
      return
    }

    // Set default end time if not provided (1 hour after start)
    let finalEndTime = endTime
    if (!finalEndTime) {
      const [hours, minutes] = startTime.split(':').map(Number)
      const endHour = hours + 1
      finalEndTime = `${endHour.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`
    }

    setIsCreating(true)
    try {
      // Prepare the event data
      const startDateTime = `${selectedDate}T${startTime}:00`
      const endDateTime = `${selectedDate}T${finalEndTime}:00`
      
      // Parse participant emails (comma-separated)
      const attendees = participantEmails
        .split(',')
        .map(email => email.trim())
        .filter(email => email.length > 0)

      // Determine the final location based on type
      let finalLocation = location
      if (locationType === 'google_meet' && !location) {
        finalLocation = 'Google Meet (link will be added)'
      } else if (locationType === 'teams' && !location) {
        finalLocation = 'Microsoft Teams (link will be added)'
      } else if (locationType === 'zoom' && !location) {
        finalLocation = 'Zoom (link will be added)'
      }

      // Create calendar event via API
      const eventData = {
        title,
        event_type: 'meeting', // Always meeting for calendar events
        start_time: startDateTime,
        end_time: endDateTime,
        location: finalLocation,
        location_type: locationType,
        description,
        attendees,
        record_id: recordId,
        add_to_calendar: true, // Always add to calendar
        metadata: {
          created_from: 'record_communications',
          is_custom_event: true
        }
      }

      // Call the API to create the calendar event
      const response = await api.post('/api/v1/communications/calendar/events/create_event/', eventData)

      toast({
        title: 'Meeting Scheduled',
        description: `"${title}" has been added to your calendar`,
      })

      // Clear form and notify parent
      setTitle('')
      setParticipantEmails('')
      setLocation('')
      setSelectedDate('')
      setStartTime('')
      setEndTime('')
      setDescription('')
      
      if (onEventScheduled) {
        onEventScheduled()
      }
    } catch (error: any) {
      console.error('Failed to create event:', error)
      toast({
        title: 'Failed to Schedule Meeting',
        description: error.response?.data?.detail || 'Could not create the calendar event',
        variant: 'destructive'
      })
    } finally {
      setIsCreating(false)
    }
  }

  const getLocationIcon = () => {
    switch (locationType) {
      case 'google_meet': 
      case 'teams':
      case 'zoom':
        return <Video className="w-4 h-4" />
      case 'in_person': return <MapPin className="w-4 h-4" />
      case 'other': return <Globe className="w-4 h-4" />
      default: return <MapPin className="w-4 h-4" />
    }
  }

  return (
    <div className="p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Calendar className="w-5 h-5" />
            Schedule Meeting
          </h3>
          {onCancel && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onCancel}
            >
              <X className="w-4 h-4" />
            </Button>
          )}
        </div>

        {/* Title */}
        <div>
          <Label htmlFor="title">Meeting Title *</Label>
          <Input
            id="title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Team Sync Meeting"
            required
          />
        </div>

        {/* Date and Time */}
        <div className="grid grid-cols-3 gap-4">
          <div>
            <Label htmlFor="date">Date *</Label>
            <Input
              id="date"
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              min={new Date().toISOString().split('T')[0]}
              required
            />
          </div>
          <div>
            <Label htmlFor="start-time">Start Time *</Label>
            <Input
              id="start-time"
              type="time"
              value={startTime}
              onChange={(e) => setStartTime(e.target.value)}
              required
            />
          </div>
          <div>
            <Label htmlFor="end-time">End Time</Label>
            <Input
              id="end-time"
              type="time"
              value={endTime}
              onChange={(e) => setEndTime(e.target.value)}
              placeholder="Optional"
            />
          </div>
        </div>

        {/* Location */}
        <div className="grid grid-cols-3 gap-4">
          <div>
            <Label htmlFor="location-type">Meeting Type</Label>
            <Select value={locationType} onValueChange={(value: any) => setLocationType(value)}>
              <SelectTrigger id="location-type">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="google_meet">Google Meet</SelectItem>
                <SelectItem value="teams">Microsoft Teams</SelectItem>
                <SelectItem value="zoom">Zoom</SelectItem>
                <SelectItem value="in_person">In Person</SelectItem>
                <SelectItem value="other">Other</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="col-span-2">
            <Label htmlFor="location">Location / Meeting Link</Label>
            <div className="relative">
              <Input
                id="location"
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder={
                  locationType === 'google_meet' ? 'Google Meet link (optional - will be created)' :
                  locationType === 'teams' ? 'Teams link (optional - will be created)' :
                  locationType === 'zoom' ? 'Zoom link' :
                  locationType === 'in_person' ? 'Address or room' :
                  'Location details'
                }
                className="pl-8"
              />
              <div className="absolute left-2 top-1/2 -translate-y-1/2">
                {getLocationIcon()}
              </div>
            </div>
          </div>
        </div>

        {/* Participants */}
        <div>
          <Label htmlFor="participants">Participant Emails (comma-separated)</Label>
          <Input
            id="participants"
            type="text"
            value={participantEmails}
            onChange={(e) => setParticipantEmails(e.target.value)}
            placeholder="john@example.com, jane@example.com"
          />
        </div>

        {/* Description */}
        <div>
          <Label htmlFor="description">Meeting Agenda / Notes</Label>
          <Textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Meeting agenda and discussion points..."
            rows={3}
          />
        </div>

        {/* Action Buttons */}
        <div className="flex justify-end gap-2">
          {onCancel && (
            <Button
              variant="outline"
              onClick={onCancel}
            >
              Cancel
            </Button>
          )}
          <Button
            onClick={handleCreate}
            disabled={isCreating || !title || !selectedDate || !startTime}
          >
            {isCreating ? 'Scheduling...' : 'Schedule Meeting'}
          </Button>
        </div>

        {/* Meeting Summary */}
        {title && selectedDate && startTime && (
          <div className="text-sm text-gray-500 dark:text-gray-400 border-t pt-3">
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4" />
              <span className="font-medium">{title}</span>
            </div>
            <div className="flex items-center gap-4 mt-1">
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {new Date(selectedDate).toLocaleDateString()} at {startTime}
                {endTime && ` - ${endTime}`}
              </span>
              {location && (
                <span className="flex items-center gap-1">
                  {getLocationIcon()}
                  {location.substring(0, 30)}{location.length > 30 && '...'}
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}