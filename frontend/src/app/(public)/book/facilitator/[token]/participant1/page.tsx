'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Input } from '@/components/ui/input'
import { 
  Calendar, Clock, MapPin, Users, Loader2, Check, AlertCircle, 
  ChevronLeft, ChevronRight, Video, Phone, Building2, ArrowLeft,
  User, Mail, ArrowRight, Globe
} from 'lucide-react'
import { 
  format, parseISO, addDays, startOfDay, startOfMonth, endOfMonth, 
  eachDayOfInterval, isSameMonth, isSameDay, isToday, isBefore, 
  addMonths, subMonths 
} from 'date-fns'
import axios from 'axios'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'

interface BookingDetails {
  booking_id: string
  status: string
  meeting_type: {
    name: string
    description: string
    pipeline_id?: string
  }
  facilitator: {
    name: string
    email: string
  }
  participant_1?: {
    name: string
    email: string
  }
  participant_2: {
    name: string
    email: string
  }
  settings: {
    duration_options: number[]
    default_duration: number
    location_options: string[]
    max_time_options: number
  }
  expires_at: string
  organization?: {
    name?: string
    logo?: string
    website?: string
  }
}

interface TimeSlot {
  start: string
  end: string
}

const LOCATION_CONFIG: Record<string, { label: string; icon: any; description: string }> = {
  google_meet: { 
    label: 'Google Meet', 
    icon: Video,
    description: 'Video conference via Google Meet'
  },
  zoom: { 
    label: 'Zoom', 
    icon: Video,
    description: 'Video conference via Zoom'
  },
  teams: { 
    label: 'Microsoft Teams', 
    icon: Video,
    description: 'Video conference via Teams'
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

export default function FacilitatorParticipant1Page() {
  const params = useParams()
  const token = params.token as string
  
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [bookingDetails, setBookingDetails] = useState<BookingDetails | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [currentStep, setCurrentStep] = useState<'config' | 'slots' | 'review' | 'confirmation'>('config')
  
  // Configuration selections
  const [selectedDuration, setSelectedDuration] = useState<number>(30)
  const [selectedLocation, setSelectedLocation] = useState<string>('google_meet')
  const [locationAddress, setLocationAddress] = useState('')
  const [message, setMessage] = useState('')
  
  // Time slot selections - Updated for multi-date
  const [selectedDates, setSelectedDates] = useState<Date[]>([])
  const [expandedDate, setExpandedDate] = useState<Date | null>(null)
  const [availableSlots, setAvailableSlots] = useState<TimeSlot[]>([])
  const [selectedSlots, setSelectedSlots] = useState<TimeSlot[]>([])
  const [loadingSlots, setLoadingSlots] = useState(false)
  const [currentMonth, setCurrentMonth] = useState(new Date())
  const [timezone] = useState(Intl.DateTimeFormat().resolvedOptions().timeZone)
  
  useEffect(() => {
    fetchBookingDetails()
  }, [token])
  
  // Get tenant from subdomain
  const getTenant = () => {
    if (typeof window !== 'undefined') {
      const hostname = window.location.hostname
      const parts = hostname.split('.')
      if (parts.length > 2 || (parts.length === 2 && parts[1] === 'localhost')) {
        return parts[0]
      }
    }
    return 'oneotalent'
  }
  
  // Generate calendar days for the current month
  const generateCalendarDays = () => {
    const start = startOfMonth(currentMonth)
    const end = endOfMonth(currentMonth)
    const days = eachDayOfInterval({ start, end })
    
    // Add padding days from previous month
    const startDay = start.getDay()
    const paddingDays = []
    for (let i = startDay - 1; i >= 0; i--) {
      paddingDays.push(new Date(start.getFullYear(), start.getMonth(), -i))
    }
    
    return [...paddingDays, ...days]
  }
  
  const handleDateSelect = (date: Date) => {
    // Toggle date selection
    const isSelected = selectedDates.some(d => isSameDay(d, date))
    
    if (isSelected) {
      // Remove date and its slots
      setSelectedDates(selectedDates.filter(d => !isSameDay(d, date)))
      
      // Remove slots from this date
      const dateStr = format(date, 'yyyy-MM-dd')
      setSelectedSlots(selectedSlots.filter(slot => 
        !slot.start.startsWith(dateStr)
      ))
      
      // If this was the expanded date, clear it
      if (expandedDate && isSameDay(expandedDate, date)) {
        setExpandedDate(null)
      }
    } else {
      // Add date and expand it
      setSelectedDates([...selectedDates, date].sort((a, b) => a.getTime() - b.getTime()))
      setExpandedDate(date)
      generateTimeSlots(date)
    }
  }
  
  const fetchBookingDetails = async () => {
    try {
      const tenant = getTenant()
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || `http://${tenant}.localhost:8000`
      const response = await axios.get(
        `${apiUrl}/api/v1/communications/scheduling/public/facilitator/${token}/participant1/`
      )
      
      if (response.data.status !== 'pending_p1') {
        setError('You have already configured this meeting.')
      } else {
        setBookingDetails(response.data)
        setSelectedDuration(response.data.settings.default_duration)
        if (response.data.settings.location_options.length > 0) {
          setSelectedLocation(response.data.settings.location_options[0])
        }
      }
    } catch (error: any) {
      console.error('Failed to fetch booking details:', error)
      if (error.response?.status === 404) {
        setError('Invalid booking link. Please check the URL and try again.')
      } else if (error.response?.status === 410) {
        setError(error.response.data.error || 'This booking link has expired.')
      } else {
        setError('Failed to load booking details. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }
  
  const generateTimeSlots = (date?: Date) => {
    const targetDate = date || expandedDate
    if (!targetDate || !selectedDuration) return
    
    setLoadingSlots(true)
    
    // Generate slots from 8 AM to 8 PM in 30-minute intervals
    const slots: TimeSlot[] = []
    const dateStart = startOfDay(targetDate)
    const startHour = 8
    const endHour = 20
    const interval = 30 // minutes
    
    for (let hour = startHour; hour < endHour; hour++) {
      for (let minute = 0; minute < 60; minute += interval) {
        const startTime = new Date(dateStart)
        startTime.setHours(hour, minute, 0, 0)
        
        const endTime = new Date(startTime)
        endTime.setMinutes(endTime.getMinutes() + selectedDuration)
        
        // Don't add slots that end after 8 PM
        if (endTime.getHours() < endHour || (endTime.getHours() === endHour && endTime.getMinutes() === 0)) {
          slots.push({
            start: startTime.toISOString(),
            end: endTime.toISOString()
          })
        }
      }
    }
    
    setAvailableSlots(slots)
    setLoadingSlots(false)
  }
  
  const handleSlotToggle = (slot: TimeSlot) => {
    if (!bookingDetails) return
    
    const maxSlots = bookingDetails.settings.max_time_options
    const isSelected = selectedSlots.some(s => s.start === slot.start && s.end === slot.end)
    
    if (isSelected) {
      setSelectedSlots(selectedSlots.filter(s => !(s.start === slot.start && s.end === slot.end)))
    } else if (selectedSlots.length < maxSlots) {
      setSelectedSlots([...selectedSlots, slot])
    }
  }
  
  const handleSubmit = async () => {
    setSubmitting(true)
    try {
      const tenant = getTenant()
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || `http://${tenant}.localhost:8000`
      const response = await axios.post(
        `${apiUrl}/api/v1/communications/scheduling/public/facilitator/${token}/participant1/`,
        {
          duration_minutes: selectedDuration,
          location_type: selectedLocation,
          location_details: selectedLocation === 'in_person' ? { address: locationAddress } : {},
          selected_slots: selectedSlots,
          message: message
        }
      )
      
      setSuccess(true)
      setCurrentStep('confirmation')
    } catch (error: any) {
      console.error('Failed to submit configuration:', error)
      setError(error.response?.data?.error || 'Failed to save configuration. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }
  
  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4">
        <Card>
          <CardContent className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </CardContent>
        </Card>
      </div>
    )
  }
  
  // Error state
  if (error || !bookingDetails) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4">
        <Card className="max-w-md">
          <CardContent className="pt-6">
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                {error || 'Failed to load booking details'}
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>
      </div>
    )
  }
  
  // Success/Confirmation state
  if (currentStep === 'confirmation') {
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
                
                <h2 className="text-2xl font-semibold mb-4">Configuration Saved!</h2>
                <p className="text-gray-600 dark:text-gray-400 mb-6">
                  Your meeting preferences have been saved. {bookingDetails.participant_2.name} will receive 
                  an email with your proposed time slots to choose from.
                </p>
                
                <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg text-left max-w-md mx-auto">
                  <h3 className="font-medium mb-3">Your Selections:</h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Duration:</span>
                      <span className="font-medium">{selectedDuration} minutes</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Location:</span>
                      <span className="font-medium">{LOCATION_CONFIG[selectedLocation]?.label}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Time Slots:</span>
                      <span className="font-medium">{selectedSlots.length} options provided</span>
                    </div>
                  </div>
                </div>
                
                <p className="mt-6 text-sm text-gray-500">
                  You'll receive an email confirmation once {bookingDetails.participant_2.name} selects a time.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </motion.div>
    )
  }
  
  // Configuration step - Two column layout like booking page
  if (currentStep === 'config') {
    return (
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="min-h-screen bg-gray-50 dark:bg-gray-900"
      >
        {/* Organization Bar - Top header if exists */}
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
          {/* Left Sidebar - Meeting Info */}
          <div className="lg:w-2/5 bg-white dark:bg-gray-800 border-r dark:border-gray-700 p-8 overflow-y-auto">
            <div className="mb-8">
              <h1 className="text-2xl font-semibold text-gray-900 dark:text-white mb-3">
                {bookingDetails.meeting_type.name}
              </h1>
              
              {bookingDetails.meeting_type.description && (
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                  {bookingDetails.meeting_type.description}
                </p>
              )}
              
              <div className="space-y-4 text-sm">
                <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                  <p className="text-blue-900 dark:text-blue-200 font-medium mb-1">Your Role</p>
                  <p className="text-blue-700 dark:text-blue-300 text-xs">
                    Configure the meeting parameters and propose time slots for the meeting between you and {bookingDetails.participant_2.name}.
                  </p>
                </div>
                
                {/* Stage Tracker - Numbered and Clear */}
                <div className="border-t dark:border-gray-700 pt-4">
                  <h3 className="font-medium mb-3">Booking Progress</h3>
                  <div className="space-y-3">
                    <div className="flex items-center gap-3">
                      <div className={cn(
                        "w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium",
                        currentStep === 'config' 
                          ? "bg-blue-600 text-white" 
                          : "bg-green-600 text-white"
                      )}>
                        {currentStep === 'config' ? '1' : '✓'}
                      </div>
                      <span className={cn(
                        "text-sm",
                        currentStep === 'config' ? "font-medium text-gray-900 dark:text-white" : "text-gray-500 dark:text-gray-400"
                      )}>Configure Meeting</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className={cn(
                        "w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium",
                        currentStep === 'slots' 
                          ? "bg-blue-600 text-white" 
                          : currentStep === 'review' 
                          ? "bg-green-600 text-white" 
                          : "bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400"
                      )}>
                        {currentStep === 'review' ? '✓' : '2'}
                      </div>
                      <span className={cn(
                        "text-sm",
                        currentStep === 'slots' ? "font-medium text-gray-900 dark:text-white" : "text-gray-500 dark:text-gray-400"
                      )}>Select Time Slots</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className={cn(
                        "w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium",
                        currentStep === 'review' 
                          ? "bg-blue-600 text-white" 
                          : "bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400"
                      )}>
                        3
                      </div>
                      <span className={cn(
                        "text-sm",
                        currentStep === 'review' ? "font-medium text-gray-900 dark:text-white" : "text-gray-500 dark:text-gray-400"
                      )}>Review & Confirm</span>
                    </div>
                  </div>
                </div>
                
                {/* Facilitator Section - Separated */}
                <div className="border-t dark:border-gray-700 pt-4">
                  <h3 className="font-medium mb-3">Meeting Facilitator</h3>
                  <div className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                    <div className="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                      <Users className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                    </div>
                    <div>
                      <p className="font-medium">{bookingDetails.facilitator.name}</p>
                      <p className="text-xs text-gray-500">{bookingDetails.facilitator.email}</p>
                    </div>
                  </div>
                </div>
                
                {/* Participants Section - Separated */}
                <div className="border-t dark:border-gray-700 pt-4">
                  <h3 className="font-medium mb-3">Meeting Participants</h3>
                  <div className="space-y-3">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
                        <User className="h-5 w-5 text-green-600 dark:text-green-400" />
                      </div>
                      <div>
                        <p className="font-medium">{bookingDetails.participant_1?.name || 'Participant 1'}</p>
                        <p className="text-xs text-gray-500">Configure meeting</p>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center">
                        <User className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                      </div>
                      <div>
                        <p className="font-medium">{bookingDetails.participant_2.name}</p>
                        <p className="text-xs text-gray-500">Will select final time</p>
                      </div>
                    </div>
                  </div>
                </div>
                
                <div className="border-t dark:border-gray-700 pt-4">
                  <p className="text-xs text-gray-500 flex items-center gap-1">
                    <AlertCircle className="h-3 w-3" />
                    Expires {format(parseISO(bookingDetails.expires_at), 'MMM d, yyyy at h:mm a')}
                  </p>
                </div>
              </div>
            </div>
          </div>
          
          {/* Right Side - Configuration Form */}
          <div className="lg:w-3/5 p-8 bg-white dark:bg-gray-900">
            <div className="max-w-lg mx-auto">
              <h2 className="text-lg font-medium mb-6 text-gray-900 dark:text-white">Configure Meeting</h2>
              
              <div className="space-y-6">
                {/* Duration Selection */}
                <div className="space-y-3">
                  <Label>Meeting Duration</Label>
                  <RadioGroup value={selectedDuration.toString()} onValueChange={(v) => setSelectedDuration(parseInt(v))}>
                    {bookingDetails.settings.duration_options.map(duration => (
                      <div key={duration} className="flex items-center space-x-2">
                        <RadioGroupItem value={duration.toString()} id={`duration-${duration}`} />
                        <Label htmlFor={`duration-${duration}`} className="font-normal cursor-pointer">
                          {duration} minutes
                        </Label>
                      </div>
                    ))}
                  </RadioGroup>
                </div>
                
                {/* Location Selection */}
                <div className="space-y-3">
                  <Label>Meeting Location</Label>
                  <div className="space-y-2">
                    {bookingDetails.settings.location_options.map(location => {
                      const config = LOCATION_CONFIG[location]
                      if (!config) return null
                      const Icon = config.icon
                      
                      return (
                        <button
                          key={location}
                          onClick={() => setSelectedLocation(location)}
                          className={cn(
                            "w-full p-3 rounded-lg border text-left transition-all",
                            selectedLocation === location
                              ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                              : "border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600"
                          )}
                        >
                          <div className="flex items-start gap-3">
                            <Icon className={cn(
                              "h-5 w-5 mt-0.5",
                              selectedLocation === location
                                ? "text-blue-600 dark:text-blue-400"
                                : "text-gray-400"
                            )} />
                            <div>
                              <p className={cn(
                                "font-medium",
                                selectedLocation === location && "text-blue-900 dark:text-blue-200"
                              )}>
                                {config.label}
                              </p>
                              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                                {config.description}
                              </p>
                            </div>
                          </div>
                        </button>
                      )
                    })}
                  </div>
                  
                  {selectedLocation === 'in_person' && (
                    <div className="mt-3">
                      <Label htmlFor="address">Meeting Address</Label>
                      <Input
                        id="address"
                        placeholder="Enter the meeting location address"
                        value={locationAddress}
                        onChange={(e) => setLocationAddress(e.target.value)}
                        className="mt-1"
                      />
                    </div>
                  )}
                </div>
                
                {/* Optional Message */}
                <div className="space-y-3">
                  <Label htmlFor="message">Message for {bookingDetails.participant_2.name} (Optional)</Label>
                  <Textarea
                    id="message"
                    placeholder="Add any notes or context for the meeting..."
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    rows={3}
                  />
                </div>
                
                {/* Continue Button */}
                <div className="pt-4">
                  <Button 
                    onClick={() => setCurrentStep('slots')}
                    className="w-full"
                    disabled={selectedLocation === 'in_person' && !locationAddress}
                  >
                    Continue to Time Selection
                    <ArrowRight className="h-4 w-4 ml-2" />
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    )
  }
  
  // Time slots selection step
  if (currentStep === 'slots') {
    return (
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="min-h-screen bg-gray-50 dark:bg-gray-900"
      >
        {/* Organization Bar - Top header if exists */}
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
          {/* Left Sidebar - Summary */}
          <div className="lg:w-2/5 bg-white dark:bg-gray-800 border-r dark:border-gray-700 p-8 overflow-y-auto">
            <button
              onClick={() => setCurrentStep('config')}
              className="flex items-center gap-2 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white mb-6"
            >
              <ArrowLeft className="h-4 w-4" />
              <span>Back to Configuration</span>
            </button>
            
            <div className="mb-8">
              <h1 className="text-2xl font-semibold text-gray-900 dark:text-white mb-3">
                Select Available Times
              </h1>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Choose up to {bookingDetails.settings.max_time_options} time slots when you're available. 
                {bookingDetails.participant_2.name} will select one that works for them.
              </p>
            </div>
            
            {/* Stage Tracker - Numbered and Clear */}
            <div className="border-t dark:border-gray-700 pt-4 mb-4">
              <h3 className="font-medium mb-3">Booking Progress</h3>
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <div className="w-7 h-7 rounded-full bg-green-600 text-white flex items-center justify-center text-xs font-medium">
                    ✓
                  </div>
                  <span className="text-sm text-gray-500 dark:text-gray-400">Configure Meeting</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-7 h-7 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs font-medium">
                    2
                  </div>
                  <span className="text-sm font-medium text-gray-900 dark:text-white">Select Time Slots</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-7 h-7 rounded-full bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400 flex items-center justify-center text-xs font-medium">
                    3
                  </div>
                  <span className="text-sm text-gray-500 dark:text-gray-400">Review & Confirm</span>
                </div>
              </div>
            </div>
            
            {/* Facilitator Section - Separated */}
            <div className="border-t dark:border-gray-700 pt-4 mb-4">
              <h3 className="font-medium mb-3">Meeting Facilitator</h3>
              <div className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div className="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                  <Users className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <p className="font-medium">{bookingDetails.facilitator.name}</p>
                  <p className="text-xs text-gray-500">{bookingDetails.facilitator.email}</p>
                </div>
              </div>
            </div>
            
            {/* Participants Section - Separated */}
            <div className="border-t dark:border-gray-700 pt-4 mb-4">
              <h3 className="font-medium mb-3">Meeting Participants</h3>
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
                    <User className="h-5 w-5 text-green-600 dark:text-green-400" />
                  </div>
                  <div>
                    <p className="font-medium">{bookingDetails.participant_1?.name || 'Participant 1'}</p>
                    <p className="text-xs text-gray-500">Selecting times</p>
                  </div>
                </div>
                
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center">
                    <User className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                  </div>
                  <div>
                    <p className="font-medium">{bookingDetails.participant_2.name}</p>
                    <p className="text-xs text-gray-500">Will select final time</p>
                  </div>
                </div>
              </div>
            </div>
            
            {/* Configuration Summary */}
            <div className="space-y-4 text-sm">
              <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                <h3 className="font-medium mb-3">Your Configuration</h3>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Clock className="h-4 w-4 text-gray-400" />
                    <span>{selectedDuration} minutes</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <MapPin className="h-4 w-4 text-gray-400" />
                    <span>{LOCATION_CONFIG[selectedLocation]?.label}</span>
                  </div>
                  {message && (
                    <div className="pt-2 border-t dark:border-gray-700">
                      <p className="text-xs text-gray-500">Message:</p>
                      <p className="text-xs mt-1">{message}</p>
                    </div>
                  )}
                </div>
              </div>
              
              {/* Selected Slots Summary - Grouped by Date */}
              {selectedSlots.length > 0 && (
                <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                  <h3 className="font-medium mb-3 text-blue-900 dark:text-blue-200">
                    Selected Time Slots ({selectedSlots.length}/{bookingDetails.settings.max_time_options})
                  </h3>
                  <div className="space-y-2">
                    {/* Group slots by date */}
                    {Object.entries(
                      selectedSlots.reduce((acc, slot) => {
                        const date = format(parseISO(slot.start), 'yyyy-MM-dd')
                        if (!acc[date]) acc[date] = []
                        acc[date].push(slot)
                        return acc
                      }, {} as Record<string, TimeSlot[]>)
                    )
                      .sort(([a], [b]) => a.localeCompare(b))
                      .map(([date, slots]) => (
                        <div key={date}>
                          <p className="text-xs font-medium text-blue-800 dark:text-blue-300 mb-1">
                            {format(parseISO(date), 'EEEE, MMMM d')}
                          </p>
                          <div className="space-y-0.5 ml-2">
                            {slots.map((slot, idx) => (
                              <div key={idx} className="text-xs text-blue-700 dark:text-blue-400">
                                {format(parseISO(slot.start), 'h:mm a')}
                              </div>
                            ))}
                          </div>
                        </div>
                      ))
                    }
                  </div>
                </div>
              )}
            </div>
          </div>
          
          {/* Right Side - Calendar and Time Selection */}
          <div className="lg:w-3/5 p-8 bg-white dark:bg-gray-900">
            <div className="max-w-lg mx-auto">
              <h2 className="text-lg font-medium mb-2 text-gray-900 dark:text-white">Select Date & Times</h2>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                Select multiple dates to offer more options. Click a date to see available times.
              </p>
              
              {/* Legend */}
              <div className="flex gap-4 text-xs mb-4">
                <div className="flex items-center gap-1">
                  <div className="w-4 h-4 border-2 border-blue-600 bg-blue-100 dark:bg-blue-900 rounded"></div>
                  <span className="text-gray-600 dark:text-gray-400">Selected date</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-4 h-4 bg-blue-600 rounded"></div>
                  <span className="text-gray-600 dark:text-gray-400">Viewing times</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-4 h-4 bg-blue-600 rounded-full text-white flex items-center justify-center text-[10px]">2</div>
                  <span className="text-gray-600 dark:text-gray-400">Slots picked</span>
                </div>
              </div>
              
              {/* Month Navigation */}
              <div className="flex items-center justify-between mb-4">
                <button
                  onClick={() => setCurrentMonth(subMonths(currentMonth, 1))}
                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
                  disabled={isBefore(subMonths(currentMonth, 1), startOfMonth(new Date()))}
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <h3 className="text-base font-medium dark:text-white">
                  {format(currentMonth, 'MMMM yyyy')}
                </h3>
                <button
                  onClick={() => setCurrentMonth(addMonths(currentMonth, 1))}
                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
              
              {/* Calendar Grid */}
              <div className="grid grid-cols-7 gap-1 mb-6">
                {/* Weekday headers */}
                {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
                  <div key={day} className="text-center text-xs font-medium text-gray-500 dark:text-gray-400 py-2">
                    {day}
                  </div>
                ))}
                
                {/* Calendar days */}
                {generateCalendarDays().map((date, index) => {
                  const isCurrentMonth = isSameMonth(date, currentMonth)
                  const isSelected = selectedDates.some(d => isSameDay(d, date))
                  const isExpanded = expandedDate && isSameDay(date, expandedDate)
                  const isToday_ = isToday(date)
                  const isPast = isBefore(date, startOfDay(new Date()))
                  const isTooFar = date > addDays(new Date(), 60)
                  const isDisabled = !isCurrentMonth || isPast || isTooFar
                  
                  // Count how many slots are selected for this date
                  const dateStr = format(date, 'yyyy-MM-dd')
                  const slotsForDate = selectedSlots.filter(slot => slot.start.startsWith(dateStr)).length
                  
                  return (
                    <button
                      key={index}
                      onClick={() => !isDisabled && handleDateSelect(date)}
                      disabled={isDisabled}
                      className={cn(
                        "h-10 text-sm rounded-md transition-all relative",
                        isCurrentMonth ? "text-gray-900 dark:text-gray-100" : "text-gray-400 dark:text-gray-600",
                        !isDisabled && "hover:bg-gray-100 dark:hover:bg-gray-800 cursor-pointer",
                        isSelected && !isExpanded && "bg-blue-100 dark:bg-blue-900 border-2 border-blue-600",
                        isExpanded && "bg-blue-600 text-white hover:bg-blue-700 shadow-sm",
                        isToday_ && !isSelected && !isExpanded && "bg-blue-50 dark:bg-gray-800 text-blue-600 dark:text-blue-400 font-semibold",
                        isDisabled && "cursor-not-allowed opacity-40"
                      )}
                    >
                      {format(date, 'd')}
                      {slotsForDate > 0 && (
                        <div className="absolute -top-1 -right-1 w-4 h-4 bg-blue-600 text-white rounded-full text-[10px] flex items-center justify-center">
                          {slotsForDate}
                        </div>
                      )}
                    </button>
                  )
                })}
              </div>
              
              {/* Time Slots - Shows inline when date is expanded */}
              {expandedDate && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="border-t dark:border-gray-700 pt-6"
                >
                  {loadingSlots ? (
                    <div className="text-center py-4">
                      <Loader2 className="h-6 w-6 animate-spin text-blue-600 mx-auto mb-2" />
                      <p className="text-sm text-gray-500 dark:text-gray-400">Loading available times...</p>
                    </div>
                  ) : availableSlots.length > 0 ? (
                    <div>
                      <div className="flex items-center justify-between mb-3">
                        <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                          Available times for {format(expandedDate, 'MMMM d')}
                        </h3>
                        <Badge variant={selectedSlots.length > 0 ? 'default' : 'secondary'}>
                          {selectedSlots.length} / {bookingDetails.settings.max_time_options} selected
                        </Badge>
                      </div>
                      <div className="max-h-64 overflow-y-auto pr-2">
                        <div className="grid grid-cols-3 gap-2">
                          {availableSlots.map((slot) => {
                            const isSelected = selectedSlots.some(s => s.start === slot.start)
                            const isDisabled = !isSelected && selectedSlots.length >= bookingDetails.settings.max_time_options
                            
                            return (
                              <button
                                key={slot.start}
                                onClick={() => !isDisabled && handleSlotToggle(slot)}
                                disabled={isDisabled}
                                className={cn(
                                  "py-2 px-3 text-sm rounded-md border transition-all",
                                  isSelected
                                    ? "bg-blue-600 text-white border-blue-600"
                                    : isDisabled
                                    ? "bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-400 cursor-not-allowed"
                                    : "bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300"
                                )}
                              >
                                {format(parseISO(slot.start), 'h:mm a')}
                              </button>
                            )
                          })}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-4">
                      <p className="text-sm text-gray-500 dark:text-gray-400">No available times for this date</p>
                      <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">Please select another date</p>
                    </div>
                  )}
                </motion.div>
              )}
              
              {/* Timezone */}
              <div className="mt-6 pt-4 border-t dark:border-gray-700">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-500 dark:text-gray-400">Timezone</span>
                  <span className="text-gray-700 dark:text-gray-300 font-medium">{timezone}</span>
                </div>
              </div>
              
              {/* Action Buttons */}
              <div className="mt-8 flex gap-3">
                <Button
                  variant="outline"
                  onClick={() => setCurrentStep('config')}
                  className="flex-1"
                >
                  Back
                </Button>
                <Button
                  onClick={() => setCurrentStep('review')}
                  disabled={selectedSlots.length === 0}
                  className="flex-1"
                >
                  Review Selection
                  <ArrowRight className="h-4 w-4 ml-2" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    )
  }
  
  // Review step
  if (currentStep === 'review') {
    return (
      <motion.div 
        initial={{ opacity: 0, x: 100 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: -100 }}
        transition={{ duration: 0.3, ease: 'easeInOut' }}
        className="min-h-screen bg-white dark:bg-gray-900"
      >
        <div className="max-w-2xl mx-auto px-4 py-8">
          {/* Back button */}
          <button
            onClick={() => setCurrentStep('slots')}
            className="flex items-center gap-2 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white mb-6"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Back</span>
          </button>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.1 }}
          >
            <Card>
            <CardHeader>
              <CardTitle>Review Your Selection</CardTitle>
              <CardDescription>
                Please confirm your meeting configuration before sending to {bookingDetails.participant_2.name}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Meeting Details */}
              <div className="space-y-4">
                <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                  <div className="flex items-center gap-2">
                    <Clock className="h-4 w-4 text-gray-400" />
                    <span className="text-sm">Duration</span>
                  </div>
                  <span className="font-medium">{selectedDuration} minutes</span>
                </div>
                
                <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                  <div className="flex items-center gap-2">
                    <MapPin className="h-4 w-4 text-gray-400" />
                    <span className="text-sm">Location</span>
                  </div>
                  <div className="text-right">
                    <p className="font-medium">{LOCATION_CONFIG[selectedLocation]?.label}</p>
                    {selectedLocation === 'in_person' && locationAddress && (
                      <p className="text-xs text-gray-500 mt-1">{locationAddress}</p>
                    )}
                  </div>
                </div>
              </div>
              
              {/* Selected Time Slots */}
              <div>
                <h3 className="font-medium mb-3">Proposed Time Slots</h3>
                <div className="space-y-2">
                  {selectedSlots.map((slot, idx) => (
                    <div key={idx} className="flex items-center gap-3 p-3 border dark:border-gray-700 rounded-lg">
                      <Calendar className="h-4 w-4 text-gray-400" />
                      <div>
                        <p className="font-medium text-sm">
                          {format(parseISO(slot.start), 'EEEE, MMMM d, yyyy')}
                        </p>
                        <p className="text-xs text-gray-500">
                          {format(parseISO(slot.start), 'h:mm a')} - {format(parseISO(slot.end), 'h:mm a')}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              
              {/* Message */}
              {message && (
                <div>
                  <h3 className="font-medium mb-2">Your Message</h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                    {message}
                  </p>
                </div>
              )}
              
              {/* Action Buttons */}
              <div className="pt-4">
                <Button
                  onClick={handleSubmit}
                  disabled={submitting}
                  className="w-full"
                  size="lg"
                >
                  {submitting ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                      Scheduling...
                    </>
                  ) : (
                    'Schedule Event'
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
          </motion.div>
        </div>
      </motion.div>
    )
  }
  
  return null
}