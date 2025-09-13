'use client'

import React, { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Calendar, Clock, MapPin, Users, Loader2, Check, AlertCircle, User, ArrowRight, Video, Phone, Building2, Globe } from 'lucide-react'
import { cn } from '@/lib/utils'
import { format, parseISO } from 'date-fns'
import axios from 'axios'
import { motion } from 'framer-motion'
// No form fields needed - participant data provided by facilitator

interface BookingDetails {
  status: string
  meeting_details: {
    name: string
    description: string
    duration_minutes: number
    location_type: string
    location_details: any
  }
  facilitator: {
    name: string
    email: string
  }
  participant_1: {
    name: string
    message?: string
  }
  participant_2: {
    email: string
    name?: string
  }
  selected_slots: Array<{
    start: string
    end: string
  }>
  expires_at: string
  labels: {
    participant_1: string
    participant_2: string
  }
  pipeline_id?: string
  meeting_type?: {
    pipeline_id?: string
    name?: string
    description?: string
  }
  organization?: {
    name: string
    logo: string
    website: string
  }
}

interface BookingConfirmation {
  success: boolean
  meeting_id: string
  confirmation: {
    meeting_type: string
    start_time: string
    end_time: string
    timezone: string
    location_type: string
    meeting_url?: string
    location?: string
    participants: string[]
    facilitator: string
  }
}

const LOCATION_CONFIG: Record<string, { label: string; icon: any; description: string }> = {
  google_meet: { 
    label: 'Google Meet', 
    icon: Video,
    description: 'Video conference via Google Meet'
  },
  teams: { 
    label: 'Microsoft Teams', 
    icon: Video,
    description: 'Video conference via Teams'
  },
  zoom: { 
    label: 'Zoom', 
    icon: Video,
    description: 'Video conference via Zoom'
  },
  phone: { 
    label: 'Phone Call', 
    icon: Phone,
    description: 'We\'ll call you at your phone number'
  },
  in_person: { 
    label: 'In Person', 
    icon: MapPin,
    description: 'Meet at a physical location'
  },
  custom: { 
    label: 'Custom Location', 
    icon: MapPin,
    description: 'Location to be determined'
  }
}

export default function Participant2SelectionPage() {
  const params = useParams()
  const token = params.token as string
  
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [bookingDetails, setBookingDetails] = useState<BookingDetails | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [confirmation, setConfirmation] = useState<BookingConfirmation | null>(null)
  
  const [selectedSlot, setSelectedSlot] = useState<string>('')
  const [participantInfo, setParticipantInfo] = useState({
    name: '',
    phone: '',
    notes: ''
  })
  
  // Dynamic form state
  // No form needed - participant data already provided by facilitator

  useEffect(() => {
    fetchBookingDetails()
  }, [token])
  
  // No form schema needed - using participant data from facilitator

  const getApiUrl = () => {
    // Derive API URL from current domain if not in environment
    if (typeof window !== 'undefined') {
      const parts = window.location.hostname.split('.')
      const tenant = (parts.length > 2 || (parts.length === 2 && parts[1] === 'localhost')) 
        ? parts[0] : 'demo'
      return process.env.NEXT_PUBLIC_API_URL || `http://${tenant}.localhost:8000`
    }
    return process.env.NEXT_PUBLIC_API_URL || 'http://demo.localhost:8000'
  }
  

  const fetchBookingDetails = async () => {
    try {
      const apiUrl = getApiUrl()
      const response = await axios.get(
        `${apiUrl}/api/v1/communications/scheduling/public/facilitator/${token}/`
      )
      
      if (response.data.status === 'expired') {
        setError('This booking link has expired. Please contact the meeting organizer for a new link.')
      } else if (response.data.status === 'completed') {
        setError('This meeting has already been scheduled.')
      } else {
        setBookingDetails(response.data)
        // Pre-fill name if provided (safely check for participant_2)
        if (response.data.participant_2?.name) {
          setParticipantInfo(prev => ({ ...prev, name: response.data.participant_2.name }))
        }
      }
    } catch (error: any) {
      console.error('Failed to fetch booking details:', error)
      if (error.response?.status === 404) {
        setError('Invalid booking link. Please check the URL and try again.')
      } else if (error.response?.status === 410) {
        setError(error.response.data?.error || 'This booking is no longer available.')
      } else {
        setError('Failed to load booking details. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }


  const handleSubmit = async () => {
    if (!selectedSlot || !bookingDetails) return
    
    setSubmitting(true)
    try {
      // Find the selected slot data
      const selectedSlotData = bookingDetails.selected_slots.find(
        s => `${s.start}-${s.end}` === selectedSlot
      )
      
      if (!selectedSlotData) {
        setError('Please select a valid time slot')
        setSubmitting(false)
        return
      }
      
      const apiUrl = getApiUrl()
      const response = await axios.post(
        `${apiUrl}/api/v1/communications/scheduling/public/facilitator/${token}/confirm/`,
        {
          selected_slot: selectedSlotData,
          participant_info: participantInfo,
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
        }
      )
      
      setConfirmation(response.data)
      setSuccess(true)
    } catch (error: any) {
      console.error('Failed to confirm booking:', error)
      if (error.response?.data?.error) {
        setError(error.response.data.error)
      } else {
        setError('Failed to confirm booking. Please try again.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
        <Card className="w-full max-w-2xl">
          <CardContent className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </CardContent>
        </Card>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
        <Card className="w-full max-w-2xl">
          <CardContent className="py-12">
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (success && confirmation) {
    return (
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8"
      >
        <div className="max-w-2xl mx-auto px-4">
          <Card>
            <CardContent className="pt-8">
              <div className="text-center">
                <motion.div 
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: 'spring', stiffness: 200 }}
                  className="inline-flex items-center justify-center w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full mb-4"
                >
                  <Check className="h-8 w-8 text-green-600 dark:text-green-400" />
                </motion.div>
                
                <h2 className="text-2xl font-semibold mb-4">Meeting Confirmed!</h2>
                <p className="text-gray-600 dark:text-gray-400 mb-6">
                  Your meeting has been successfully scheduled. Calendar invitations have been sent to all participants.
                </p>
                
                <div className="bg-gray-50 dark:bg-gray-800 p-6 rounded-lg text-left max-w-md mx-auto">
                  <h3 className="font-medium mb-4">Meeting Details:</h3>
                  <div className="space-y-3">
                    <div className="flex items-center gap-3">
                      <Calendar className="h-4 w-4 text-gray-400" />
                      <span className="text-sm">
                        {format(parseISO(confirmation.confirmation.start_time), 'EEEE, MMMM d, yyyy')}
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      <Clock className="h-4 w-4 text-gray-400" />
                      <span className="text-sm">
                        {format(parseISO(confirmation.confirmation.start_time), 'h:mm a')} - 
                        {format(parseISO(confirmation.confirmation.end_time), ' h:mm a')}
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      {React.createElement(LOCATION_CONFIG[confirmation.confirmation.location_type]?.icon || MapPin, {
                        className: "h-4 w-4 text-gray-400"
                      })}
                      <span className="text-sm">
                        {LOCATION_CONFIG[confirmation.confirmation.location_type]?.label || confirmation.confirmation.location_type}
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      <Users className="h-4 w-4 text-gray-400" />
                      <span className="text-sm">
                        {confirmation.confirmation.participants.join(', ')}
                      </span>
                    </div>
                  </div>
                  
                  <div className="mt-4 pt-4 border-t dark:border-gray-700">
                    <p className="text-xs text-gray-500">
                      Facilitated by {confirmation.confirmation.facilitator}
                    </p>
                  </div>
                </div>
                
                <Alert className="mt-6 max-w-md mx-auto">
                  <Check className="h-4 w-4" />
                  <AlertDescription>
                    Calendar invitations have been sent to all participants. Please check your email for the meeting link and additional details.
                  </AlertDescription>
                </Alert>
              </div>
            </CardContent>
          </Card>
        </div>
      </motion.div>
    )
  }

  if (!bookingDetails) return null

  // Group slots by date for better display
  const slotsByDate = bookingDetails.selected_slots.reduce((acc, slot) => {
    const date = format(parseISO(slot.start), 'yyyy-MM-dd')
    if (!acc[date]) acc[date] = []
    acc[date].push(slot)
    return acc
  }, {} as Record<string, typeof bookingDetails.selected_slots>)

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Organization Header - Matching P1 design */}
      {(bookingDetails.organization?.logo || bookingDetails.organization?.name) && (
        <div className="bg-white dark:bg-gray-800 border-b dark:border-gray-700">
          <div className="max-w-7xl mx-auto px-6 py-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                {bookingDetails.organization.logo ? (
                  <img 
                    src={bookingDetails.organization.logo} 
                    alt={bookingDetails.organization.name || 'Organization'}
                    className="h-8 object-contain"
                  />
                ) : (
                  <div className="flex items-center gap-2">
                    <Building2 className="h-5 w-5 text-gray-400" />
                    <span className="text-sm font-medium text-gray-900 dark:text-white">
                      {bookingDetails.organization.name}
                    </span>
                  </div>
                )}
              </div>
              {bookingDetails.organization.website && (
                <a 
                  href={bookingDetails.organization.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
                >
                  <Globe className="h-3 w-3" />
                  <span>Website</span>
                </a>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="max-w-7xl mx-auto flex flex-col lg:flex-row min-h-[calc(100vh-60px)]">
        {/* Left Side - Meeting Info & Participants */}
        <div className="lg:w-2/5 bg-white dark:bg-gray-800 border-r dark:border-gray-700 p-8 overflow-y-auto">
          {/* Meeting Title */}
          <div className="mb-8">
            <h1 className="text-2xl font-semibold text-gray-900 dark:text-white mb-3">
              Select Meeting Time
            </h1>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {bookingDetails.participant_1.name} has proposed times for your meeting. 
              Select the one that works best for you.
            </p>
          </div>

          {/* Stage Tracker */}
          <div className="border-t dark:border-gray-700 pt-4 mb-4">
            <h3 className="font-medium mb-3">Booking Progress</h3>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="w-7 h-7 rounded-full bg-green-600 text-white flex items-center justify-center text-xs font-medium">
                  ✓
                </div>
                <span className="text-sm text-gray-500 dark:text-gray-400">Meeting Configured</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-7 h-7 rounded-full bg-green-600 text-white flex items-center justify-center text-xs font-medium">
                  ✓
                </div>
                <span className="text-sm text-gray-500 dark:text-gray-400">Times Proposed</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-7 h-7 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs font-medium">
                  3
                </div>
                <span className="text-sm font-medium text-gray-900 dark:text-white">Select Final Time</span>
              </div>
            </div>
          </div>

          {/* Facilitator Section */}
          <div className="border-t dark:border-gray-700 pt-4 mb-4">
            <h3 className="font-medium mb-3">Meeting Facilitator</h3>
            <div className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-900 rounded-lg">
              <div className="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                <Users className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <p className="font-medium">{bookingDetails.facilitator.name}</p>
                <p className="text-xs text-gray-500">{bookingDetails.facilitator.email}</p>
              </div>
            </div>
          </div>

          {/* Participants Section */}
          <div className="border-t dark:border-gray-700 pt-4 mb-4">
            <h3 className="font-medium mb-3">Meeting Participants</h3>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
                  <User className="h-5 w-5 text-green-600 dark:text-green-400" />
                </div>
                <div>
                  <p className="font-medium">{bookingDetails.participant_1.name}</p>
                  <p className="text-xs text-gray-500">Proposed times</p>
                </div>
              </div>
              
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center">
                  <User className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                </div>
                <div>
                  <p className="font-medium">{bookingDetails.participant_2?.name || 'Participant 2'}</p>
                  <p className="text-xs text-gray-500">Selecting final time</p>
                </div>
              </div>
            </div>
          </div>

          {/* Meeting Details */}
          <div className="border-t dark:border-gray-700 pt-4">
            <h3 className="font-medium mb-3">Meeting Details</h3>
            <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg space-y-3">
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-gray-400" />
                <span className="text-sm">{bookingDetails.meeting_details.duration_minutes} minutes</span>
              </div>
              <div className="flex items-center gap-2">
                {React.createElement(LOCATION_CONFIG[bookingDetails.meeting_details.location_type]?.icon || MapPin, {
                  className: "h-4 w-4 text-gray-400"
                })}
                <span className="text-sm">{LOCATION_CONFIG[bookingDetails.meeting_details.location_type]?.label}</span>
              </div>
              {bookingDetails.meeting_details.location_type === 'in_person' && 
                bookingDetails.meeting_details.location_details?.address && (
                <div className="flex items-start gap-2">
                  <MapPin className="h-4 w-4 text-gray-400 mt-0.5" />
                  <span className="text-sm">{bookingDetails.meeting_details.location_details.address}</span>
                </div>
              )}
              {bookingDetails.participant_1.message && (
                <div className="pt-3 border-t dark:border-gray-700">
                  <p className="text-xs text-gray-500 mb-1">Message from {bookingDetails.participant_1.name}:</p>
                  <p className="text-sm italic text-gray-600 dark:text-gray-400">
                    "{bookingDetails.participant_1.message}"
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Side - Time Selection & Form */}
        <div className="lg:w-3/5 p-8 bg-white dark:bg-gray-900">
          <div className="max-w-2xl mx-auto space-y-6">
            {/* Time Selection Header */}
            <div>
              <h2 className="text-lg font-medium mb-2 text-gray-900 dark:text-white">
                Choose Your Preferred Time
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Select one of the proposed time slots below. You'll receive a calendar invitation once confirmed.
              </p>
            </div>

            {/* Time Slots Grouped by Date */}
            <div className="space-y-4">
              <RadioGroup value={selectedSlot} onValueChange={setSelectedSlot} className="space-y-4">
                {Object.entries(slotsByDate)
                  .sort(([a], [b]) => a.localeCompare(b))
                  .map(([date, slots]) => (
                    <div key={date} className="space-y-2">
                      <h3 className="font-medium text-sm text-gray-700 dark:text-gray-300 mb-2">
                        {format(parseISO(date), 'EEEE, MMMM d, yyyy')}
                      </h3>
                      <div className="space-y-2">
                        {slots.map((slot, idx) => {
                          const slotKey = `${slot.start}-${slot.end}`
                          const startTime = parseISO(slot.start)
                          const endTime = parseISO(slot.end)
                          const isSelected = selectedSlot === slotKey
                          
                          return (
                            <div key={`${date}-${idx}`} className="relative">
                              <RadioGroupItem 
                                value={slotKey} 
                                id={`slot-${date}-${idx}`}
                                className="absolute left-4 top-1/2 -translate-y-1/2"
                              />
                              <Label 
                                htmlFor={`slot-${date}-${idx}`} 
                                className={cn(
                                  "block pl-12 pr-4 py-3 rounded-lg border cursor-pointer transition-all",
                                  isSelected 
                                    ? "bg-blue-50 dark:bg-blue-900/20 border-blue-500 dark:border-blue-400" 
                                    : "bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700"
                                )}
                              >
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center gap-3">
                                    <Clock className="h-4 w-4 text-gray-400" />
                                    <span className={cn(
                                      "font-medium",
                                      isSelected ? "text-blue-900 dark:text-blue-200" : "text-gray-900 dark:text-white"
                                    )}>
                                      {format(startTime, 'h:mm a')} - {format(endTime, 'h:mm a')}
                                    </span>
                                  </div>
                                  <span className="text-xs text-gray-500 dark:text-gray-400">
                                    {bookingDetails.meeting_details.duration_minutes} min
                                  </span>
                                </div>
                              </Label>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  ))
                }
              </RadioGroup>
            </div>

            {/* Expiry Warning */}
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                This link expires on {format(parseISO(bookingDetails.expires_at), 'MMMM d, yyyy at h:mm a')}
              </AlertDescription>
            </Alert>

            {/* Submit Button */}
            <Button 
              onClick={handleSubmit}
              disabled={!selectedSlot || submitting}
              className="w-full"
            >
              {submitting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Confirming Meeting...
                </>
              ) : (
                'Confirm Meeting Time'
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}