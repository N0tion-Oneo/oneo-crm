'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Calendar, Clock, MapPin, Globe, Video, Phone as PhoneIcon, Check, ChevronLeft, ChevronRight, Loader2, Github, Linkedin, Twitter, Mail, Link, Building2, ChevronDown, ChevronUp, ArrowLeft } from 'lucide-react'
import { format, parseISO, startOfMonth, endOfMonth, eachDayOfInterval, isSameMonth, isSameDay, isToday, isBefore, startOfDay, addMonths, subMonths } from 'date-fns'
import axios from 'axios'
import { FieldWrapper, initializeFieldSystem } from '@/lib/field-system'
import { Field } from '@/lib/field-system/types'
import { cn } from '@/lib/utils'
import { motion } from 'framer-motion'

// Initialize the field system
if (typeof window !== 'undefined') {
  initializeFieldSystem()
}

interface MeetingType {
  name: string
  description: string
  duration_minutes: number
  location_type: string
  booking_form_config: any
  custom_questions: any[]
  required_fields: string[]
  allow_rescheduling: boolean
  allow_cancellation: boolean
  cancellation_notice_hours: number
  host: {
    name: string
    title?: string
    email?: string
    avatar?: string
    bio?: string
    company?: string
    department?: string
    expertise?: string[]
    timezone?: string
    professional_links?: Record<string, string>
  }
  organization?: {
    name?: string
    logo?: string
    website?: string
  }
  booking_url: string
}

interface SchedulingLink {
  public_name: string
  public_description: string
  meeting_type: {
    name: string
    description: string
    duration_minutes: number
    location_type: string
  }
  host: {
    name: string
    title?: string
    email?: string
    avatar?: string
    bio?: string
    company?: string
    department?: string
    expertise?: string[]
    timezone?: string
    professional_links?: Record<string, string>
  }
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
    host: string
  }
}

interface FormField {
  field_id?: number
  field_slug: string
  field_name: string
  field_type: string
  is_required: boolean
  is_visible?: boolean
  display_order: number
  help_text?: string
  placeholder?: string
  field_config?: any
  validation_rules?: any
  business_rules?: any
}

interface FormSchema {
  fields: FormField[]
  pipeline_id?: number
  pipeline_name?: string
  stage?: string
  total_fields?: number
  required_fields?: number
}

export default function BookingPage() {
  const params = useParams()
  const paramsArray = params.params as string[]
  
  // Determine if this is a new format (username/slug) or old format (UUID)
  const isNewFormat = paramsArray.length === 2
  const username = isNewFormat ? paramsArray[0] : null
  const slug = isNewFormat ? paramsArray[1] : paramsArray[0]
  
  const [loading, setLoading] = useState(true)
  const [meetingData, setMeetingData] = useState<MeetingType | SchedulingLink | null>(null)
  const [error, setError] = useState<string | null>(null)
  
  // Booking flow states - Calendly-style with clear steps
  const [currentStep, setCurrentStep] = useState<'datetime' | 'details' | 'confirmation'>('datetime')
  const [selectedDate, setSelectedDate] = useState<Date | null>(null)
  const [selectedSlot, setSelectedSlot] = useState<TimeSlot | null>(null)
  const [availableSlots, setAvailableSlots] = useState<TimeSlot[]>([])
  const [loadingSlots, setLoadingSlots] = useState(false)
  const [bookingConfirmation, setBookingConfirmation] = useState<BookingConfirmation | null>(null)
  const [submitting, setSubmitting] = useState(false)
  
  // Calendar navigation
  const [currentMonth, setCurrentMonth] = useState(new Date())
  const [timezone] = useState(Intl.DateTimeFormat().resolvedOptions().timeZone)
  
  // Form data
  const [formData, setFormData] = useState<Record<string, any>>({})
  const [formSchema, setFormSchema] = useState<FormSchema | null>(null)
  const [loadingFormSchema, setLoadingFormSchema] = useState(false)
  
  // UI states
  const [isBioExpanded, setIsBioExpanded] = useState(false)
  
  
  // Get tenant from subdomain
  const getTenant = () => {
    if (typeof window !== 'undefined') {
      const hostname = window.location.hostname
      const parts = hostname.split('.')
      if (parts.length > 2 || (parts.length === 2 && parts[1] === 'localhost')) {
        return parts[0]
      }
    }
    return 'demo' // Default tenant
  }
  
  // Load meeting data
  useEffect(() => {
    const fetchMeetingData = async () => {
      try {
        const tenant = getTenant()
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || `http://${tenant}.localhost:8000`
        
        let response
        if (isNewFormat && username) {
          // New format: /book/[username]/[slug]
          response = await axios.get(
            `${apiUrl}/api/v1/communications/scheduling/public/book/${username}/${slug}/`
          )
        } else {
          // Old format: /book/[uuid]
          response = await axios.get(
            `${apiUrl}/api/v1/communications/scheduling/public/links/${slug}/`
          )
        }
        
        setMeetingData(response.data)
        console.log('Meeting data received:', response.data)
        
        // Fetch form schema
        if (isNewFormat && username) {
          fetchFormSchema()
        } else {
          // For old format, use default fields
          setFormSchema({
            fields: [
              {
                field_slug: 'name',
                field_name: 'Full Name',
                field_type: 'text',
                is_required: true,
                display_order: 1
              },
              {
                field_slug: 'email',
                field_name: 'Email',
                field_type: 'email',
                is_required: true,
                display_order: 2
              },
              {
                field_slug: 'phone',
                field_name: 'Phone',
                field_type: 'phone',
                is_required: false,
                display_order: 3
              },
              {
                field_slug: 'notes',
                field_name: 'Additional Notes',
                field_type: 'textarea',
                is_required: false,
                display_order: 4
              }
            ]
          })
          setFormData({ name: '', email: '', phone: '', notes: '' })
        }
        
        setLoading(false)
      } catch (err: any) {
        console.error('Failed to load meeting information:', err)
        setError(err.response?.data?.error || 'Failed to load meeting information')
        setLoading(false)
      }
    }
    
    fetchMeetingData()
  }, [isNewFormat, username, slug])
  
  const fetchFormSchema = async () => {
    setLoadingFormSchema(true)
    try {
      const tenant = getTenant()
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || `http://${tenant}.localhost:8000`
      
      const response = await axios.get(
        `${apiUrl}/api/v1/communications/scheduling/public/book/${username}/${slug}/form/`
      )
      
      setFormSchema(response.data)
      
      // Initialize form data with empty values for all fields
      const initialData: Record<string, any> = {}
      response.data.fields.forEach((field: FormField) => {
        initialData[field.field_slug] = ''
      })
      setFormData(initialData)
      
      setLoadingFormSchema(false)
    } catch (err: any) {
      console.error('Failed to load form schema:', err)
      // Fall back to default fields if schema fetch fails
      setFormSchema({
        fields: [
          {
            field_slug: 'name',
            field_name: 'Full Name',
            field_type: 'text',
            is_required: true,
            display_order: 1
          },
          {
            field_slug: 'email',
            field_name: 'Email',
            field_type: 'email',
            is_required: true,
            display_order: 2
          },
          {
            field_slug: 'phone',
            field_name: 'Phone',
            field_type: 'phone',
            is_required: false,
            display_order: 3
          },
          {
            field_slug: 'notes',
            field_name: 'Additional Notes',
            field_type: 'textarea',
            is_required: false,
            display_order: 4
          }
        ]
      })
      setFormData({ name: '', email: '', phone: '', notes: '' })
      setLoadingFormSchema(false)
    }
  }
  
  // Load available slots when date is selected
  useEffect(() => {
    if (selectedDate) {
      loadAvailableSlots(selectedDate)
    }
  }, [selectedDate])
  
  const loadAvailableSlots = async (date: Date) => {
    setLoadingSlots(true)
    try {
      const tenant = getTenant()
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || `http://${tenant}.localhost:8000`
      
      let endpoint
      if (isNewFormat && username) {
        endpoint = `${apiUrl}/api/v1/communications/scheduling/public/book/${username}/${slug}/availability/`
      } else {
        endpoint = `${apiUrl}/api/v1/communications/scheduling/public/links/${slug}/availability/`
      }
      
      // Create date strings that preserve the selected date
      // Format as YYYY-MM-DDTHH:MM:SS to avoid timezone shifts
      const year = date.getFullYear()
      const month = String(date.getMonth() + 1).padStart(2, '0')
      const day = String(date.getDate()).padStart(2, '0')
      
      // Send as date + time strings without timezone conversion
      // Include timezone to help backend understand the context
      const response = await axios.post(endpoint, {
        start_date: `${year}-${month}-${day}T00:00:00`,
        end_date: `${year}-${month}-${day}T23:59:59`,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
      })
      
      console.log('Availability response:', {
        endpoint,
        slotsCount: response.data.slots?.length,
        slots: response.data.slots
      })
      
      setAvailableSlots(response.data.slots || [])
    } catch (err) {
      console.error('Failed to load availability:', err)
      setAvailableSlots([])
    } finally {
      setLoadingSlots(false)
    }
  }
  
  const handleDateSelect = (date: Date) => {
    setSelectedDate(date)
    setSelectedSlot(null) // Clear selected slot when date changes
  }
  
  const handleSlotSelect = (slot: TimeSlot) => {
    setSelectedSlot(slot)
    // Automatically move to details step when slot is selected
    setCurrentStep('details')
  }
  
  const handleBackToDateTime = () => {
    setCurrentStep('datetime')
    setSelectedSlot(null)
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
  
  const renderFormField = (field: FormField) => {
    // Convert the API field data to the Field type expected by the field system
    const fieldSystemField: Field = {
      id: field.field_id?.toString() || field.field_slug,
      name: field.field_slug,
      display_name: field.field_name,
      field_type: field.field_type,
      field_config: field.field_config || {},
      is_readonly: false,
      help_text: field.help_text,
      placeholder: field.placeholder,
      business_rules: {
        ...field.business_rules,
        // Store required status in business_rules for conditional evaluation
        required: field.is_required
      }
    }
    
    // For boolean/checkbox fields, we need to handle the special case
    if (field.field_type === 'checkbox' || field.field_type === 'boolean') {
      fieldSystemField.field_type = 'boolean'
    }
    
    return (
      <FieldWrapper
        field={fieldSystemField}
        value={formData[field.field_slug] || ''}
        onChange={(value) => setFormData({ ...formData, [field.field_slug]: value })}
        onBlur={() => {}}
        disabled={false}
        context="form"
        showLabel={false} // We handle labels in the parent
        showHelp={false}  // We handle help text in the parent
      />
    )
  }
  
  const handleBooking = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    
    if (!selectedSlot || !meetingData) {
      setError('Please select a date and time slot')
      return
    }
    
    // Basic validation
    const requiredFields = formSchema?.fields.filter(f => f.is_required) || []
    for (const field of requiredFields) {
      if (!formData[field.field_slug] || formData[field.field_slug] === '') {
        setError(`Please fill in ${field.field_name}`)
        return
      }
    }
    
    setSubmitting(true)
    setError(null)
    
    try {
      const tenant = getTenant()
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || `http://${tenant}.localhost:8000`
      
      let endpoint
      if (isNewFormat && username) {
        endpoint = `${apiUrl}/api/v1/communications/scheduling/public/book/${username}/${slug}/book/`
      } else {
        endpoint = `${apiUrl}/api/v1/communications/scheduling/public/links/${slug}/book/`
      }
      
      const response = await axios.post(endpoint, {
        ...formData,
        selected_slot: selectedSlot,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
      })
      
      setBookingConfirmation(response.data)
      setCurrentStep('confirmation')
    } catch (err: any) {
      console.error('Booking failed:', err)
      setError(err.response?.data?.error || 'Failed to complete booking')
    } finally {
      setSubmitting(false)
    }
  }
  
  const getMeetingInfo = () => {
    if (!meetingData) return null
    
    // Check if it's a MeetingType (new format) or SchedulingLink (old format)
    if ('name' in meetingData) {
      // Direct meeting type
      const meeting = meetingData as MeetingType
      
      return {
        name: meeting.name,
        description: meeting.description,
        duration_minutes: meeting.duration_minutes,
        location_type: meeting.location_type,
        host: meeting.host,
        organization: meeting.organization,
        allow_rescheduling: meeting.allow_rescheduling,
        allow_cancellation: meeting.allow_cancellation
      }
    }
    
    // Legacy SchedulingLink format
    const link = meetingData as SchedulingLink
    
    return {
      name: link.public_name || link.meeting_type?.name,
      description: link.public_description || link.meeting_type?.description,
      duration_minutes: link.meeting_type?.duration_minutes,
      location_type: link.meeting_type?.location_type,
      host: link.host,
      organization: link.organization,
      allow_rescheduling: false,
      allow_cancellation: false
    }
  }
  
  const getLocationDisplay = () => {
    const info = getMeetingInfo()
    if (!info) return ''
    
    const locationMap: Record<string, string> = {
      'zoom': 'Zoom Meeting',
      'google_meet': 'Google Meet',
      'teams': 'Microsoft Teams',
      'phone': 'Phone Call',
      'in_person': 'In Person',
      'custom': 'Custom Location'
    }
    
    return locationMap[info.location_type] || info.location_type
  }
  
  // Get location icon based on type
  const getLocationIcon = (type: string) => {
    switch(type) {
      case 'zoom':
      case 'google_meet':
      case 'teams':
        return <Video className="h-4 w-4" />
      case 'phone':
        return <PhoneIcon className="h-4 w-4" />
      case 'in_person':
        return <MapPin className="h-4 w-4" />
      default:
        return <Globe className="h-4 w-4" />
    }
  }
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-white dark:from-gray-900 dark:to-gray-800">
        <motion.div 
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3 }}
          className="text-center"
        >
          <motion.div 
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
            className="rounded-full h-12 w-12 border-t-4 border-b-4 border-blue-600 dark:border-blue-400 mx-auto"
          ></motion.div>
          <motion.p 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="mt-4 text-gray-600 dark:text-gray-300 font-medium"
          >
            Loading meeting information...
          </motion.p>
        </motion.div>
      </div>
    )
  }
  
  if (error || !meetingData) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <Card className="max-w-md">
          <CardHeader>
            <CardTitle>Meeting Not Found</CardTitle>
            <p className="text-sm text-muted-foreground mt-2">
              {error || 'This meeting type is not available.'}
            </p>
          </CardHeader>
        </Card>
      </div>
    )
  }
  
  const meetingInfo = getMeetingInfo()
  
  // Confirmation page
  if (currentStep === 'confirmation' && bookingConfirmation) {
    return (
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
        className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8"
      >
        <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8">
          <Card>
            <CardContent className="pt-8">
              <div className="text-center">
                <motion.div 
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ duration: 0.5, type: 'spring', stiffness: 200 }}
                  className="inline-flex items-center justify-center w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full mb-4"
                >
                  <Check className="h-8 w-8 text-green-600 dark:text-green-400" />
                </motion.div>
                
                <h2 className="text-2xl font-semibold mb-4 dark:text-white">Meeting Confirmed!</h2>
                
                <div className="bg-gray-50 dark:bg-gray-800 p-6 rounded-lg text-left max-w-md mx-auto">
                  <div className="space-y-3">
                    <div>
                      <p className="text-sm text-gray-600 dark:text-gray-400">Meeting Type</p>
                      <p className="font-semibold dark:text-white">{bookingConfirmation.confirmation.meeting_type}</p>
                    </div>
                    
                    <div>
                      <p className="text-sm text-gray-600 dark:text-gray-400">Date & Time</p>
                      <p className="font-semibold dark:text-white">
                        {format(parseISO(bookingConfirmation.confirmation.start_time), 'EEEE, MMMM d, yyyy')}
                        <br />
                        {format(parseISO(bookingConfirmation.confirmation.start_time), 'h:mm a')} - 
                        {format(parseISO(bookingConfirmation.confirmation.end_time), 'h:mm a')}
                      </p>
                    </div>
                    
                    <div>
                      <p className="text-sm text-gray-600 dark:text-gray-400">Host</p>
                      <p className="font-semibold dark:text-white">{bookingConfirmation.confirmation.host}</p>
                    </div>
                    
                    <div>
                      <p className="text-sm text-gray-600 dark:text-gray-400">Location</p>
                      <p className="font-semibold dark:text-white">{getLocationDisplay()}</p>
                      {bookingConfirmation.confirmation.meeting_url && (
                        <a 
                          href={bookingConfirmation.confirmation.meeting_url}
                          className="text-primary hover:underline text-sm"
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          Join Meeting
                        </a>
                      )}
                    </div>
                  </div>
                </div>
                
                <p className="mt-6 text-gray-600 dark:text-gray-300">
                  A confirmation email has been sent to <strong>{formData.email}</strong>
                </p>
                
                {meetingInfo?.allow_rescheduling && (
                  <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                    Need to reschedule? Check your confirmation email for instructions.
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </motion.div>
    )
  }

  // Main booking view - Redesigned with left sidebar
  if (currentStep === 'datetime') {
    return (
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="min-h-screen bg-gray-50 dark:bg-gray-900"
      >
        {/* Organization Bar - Top header if exists */}
        {(meetingInfo?.organization?.logo || meetingInfo?.organization?.name) && (
          <div className="bg-white dark:bg-gray-800 border-b dark:border-gray-700">
            <div className="max-w-7xl mx-auto px-6 py-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  {meetingInfo.organization.logo ? (
                    <img 
                      src={meetingInfo.organization.logo} 
                      alt={meetingInfo.organization.name || 'Organization'}
                      className="h-8 object-contain"
                    />
                  ) : (
                    <div className="flex items-center gap-2">
                      <Building2 className="h-5 w-5 text-gray-400" />
                      <span className="text-sm font-medium text-gray-900 dark:text-white">
                        {meetingInfo.organization.name}
                      </span>
                    </div>
                  )}
                </div>
                {meetingInfo.organization.website && (
                  <a 
                    href={meetingInfo.organization.website}
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
          {/* Left Sidebar - Host Info & Meeting Details */}
          <div className="lg:w-2/5 bg-white dark:bg-gray-800 border-r dark:border-gray-700 p-8 overflow-y-auto">
            {/* Meeting Information */}
            <div className="mb-8">
              <h1 className="text-2xl font-semibold text-gray-900 dark:text-white mb-3">
                {meetingInfo?.name}
              </h1>
              
              {meetingInfo?.description && (
                <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed mb-4">
                  {meetingInfo.description}
                </p>
              )}
              
              {/* Meeting Details */}
              <div className="flex flex-wrap items-center gap-4 text-sm">
                <div className="flex items-center gap-1.5 text-gray-600 dark:text-gray-400">
                  <Clock className="h-4 w-4" />
                  <span>{meetingInfo?.duration_minutes} min</span>
                </div>
                
                <div className="flex items-center gap-1.5 text-gray-600 dark:text-gray-400">
                  {getLocationIcon(meetingInfo?.location_type || '')}
                  <span>{getLocationDisplay()}</span>
                </div>
              </div>
            </div>
            
            {/* Host Profile Section */}
            <div className="border-t dark:border-gray-700 pt-6">
              <div className="flex items-start gap-4">
                {/* Staff Avatar */}
                {meetingInfo?.host?.avatar ? (
                  <img 
                    src={meetingInfo.host.avatar} 
                    alt={meetingInfo.host.name}
                    className="w-16 h-16 rounded-full object-cover ring-2 ring-gray-100 dark:ring-gray-700"
                  />
                ) : (
                  <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center text-white text-lg font-medium">
                    {meetingInfo?.host?.name?.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)}
                  </div>
                )}
                
                {/* Host Info */}
                <div className="flex-1">
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                    {meetingInfo?.host?.name}
                  </h3>
                  {(meetingInfo?.host?.title || meetingInfo?.host?.company || meetingInfo?.host?.department) && (
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      {meetingInfo.host.title}
                      {meetingInfo.host.title && (meetingInfo.host.company || meetingInfo.host.department) && ' at '}
                      {meetingInfo.host.company}
                      {meetingInfo.host.company && meetingInfo.host.department && ' / '}
                      {meetingInfo.host.department}
                    </p>
                  )}
                </div>
              </div>
              
              {/* Professional Links */}
              {meetingInfo?.host?.professional_links && Object.keys(meetingInfo.host.professional_links).length > 0 && (
                <div className="mt-4 flex flex-wrap items-center gap-2">
                  {Object.entries(meetingInfo.host.professional_links).map(([platform, url]) => {
                    const platformLower = platform.toLowerCase()
                    let icon = null
                    let label = platform
                    
                    if (platformLower === 'linkedin') {
                      icon = <Linkedin className="w-3.5 h-3.5" />
                      label = 'LinkedIn'
                    } else if (platformLower === 'github') {
                      icon = <Github className="w-3.5 h-3.5" />
                      label = 'GitHub'
                    } else if (platformLower === 'twitter' || platformLower === 'x') {
                      icon = <Twitter className="w-3.5 h-3.5" />
                      label = platformLower === 'x' ? 'X' : 'Twitter'
                    } else if (platformLower === 'email' || platformLower === 'mail') {
                      icon = <Mail className="w-3.5 h-3.5" />
                      label = 'Email'
                    } else if (platformLower === 'website' || platformLower === 'portfolio') {
                      icon = <Globe className="w-3.5 h-3.5" />
                      label = platform.charAt(0).toUpperCase() + platform.slice(1)
                    } else {
                      icon = <Link className="w-3.5 h-3.5" />
                      label = platform.charAt(0).toUpperCase() + platform.slice(1)
                    }
                    
                    return (
                      <a 
                        key={platform}
                        href={platformLower === 'email' || platformLower === 'mail' ? `mailto:${url}` : url as string}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 px-2.5 py-1 text-xs bg-gray-50 hover:bg-gray-100 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-full transition-colors"
                      >
                        {icon}
                        <span>{label}</span>
                      </a>
                    )
                  })}
                </div>
              )}
              
              {/* Collapsible Host Bio */}
              {meetingInfo?.host?.bio && (
                <div className="mt-4">
                  <div className={`text-sm text-gray-600 dark:text-gray-400 leading-relaxed ${!isBioExpanded ? 'line-clamp-3' : ''}`}>
                    <p className="whitespace-pre-wrap">
                      {meetingInfo.host.bio}
                    </p>
                  </div>
                  {meetingInfo.host.bio.length > 200 && (
                    <button
                      onClick={() => setIsBioExpanded(!isBioExpanded)}
                      className="mt-2 inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 transition-colors"
                    >
                      <span>{isBioExpanded ? 'Show less' : 'Read more'}</span>
                      {isBioExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                    </button>
                  )}
                </div>
              )}
              
              {/* Expertise Tags */}
              {meetingInfo?.host?.expertise && meetingInfo.host.expertise.length > 0 && (
                <div className="mt-4 flex flex-wrap gap-2">
                  {meetingInfo.host.expertise.map((skill, index) => (
                    <span 
                      key={index}
                      className="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Right Side - Calendar and Time Selection */}
          <div className="lg:w-3/5 p-8 bg-white dark:bg-gray-900">
            <div className="max-w-lg mx-auto">
              <h2 className="text-lg font-medium mb-6 text-gray-900 dark:text-white">Select Date & Time</h2>
              
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
                  const isSelected = selectedDate && isSameDay(date, selectedDate)
                  const isToday_ = isToday(date)
                  const isPast = isBefore(date, startOfDay(new Date()))
                  const isDisabled = !isCurrentMonth || isPast
                  
                  return (
                    <button
                      key={index}
                      onClick={() => !isDisabled && handleDateSelect(date)}
                      disabled={isDisabled}
                      className={cn(
                        "h-10 text-sm rounded-md transition-all",
                        isCurrentMonth ? "text-gray-900 dark:text-gray-100" : "text-gray-400 dark:text-gray-600",
                        !isDisabled && "hover:bg-gray-100 dark:hover:bg-gray-800 cursor-pointer",
                        isSelected && "bg-blue-600 text-white hover:bg-blue-700 shadow-sm",
                        isToday_ && !isSelected && "bg-blue-50 dark:bg-gray-800 text-blue-600 dark:text-blue-400 font-semibold",
                        isDisabled && "cursor-not-allowed opacity-40"
                      )}
                    >
                      {format(date, 'd')}
                    </button>
                  )
                })}
              </div>

              {/* Time Slots - Shows inline when date is selected */}
              {selectedDate && (
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
                      <h3 className="text-sm font-medium mb-3 text-gray-700 dark:text-gray-300">
                        Available times for {format(selectedDate, 'MMMM d')}
                      </h3>
                      <div className="max-h-64 overflow-y-auto pr-2">
                        <div className="grid grid-cols-3 gap-2">
                          {availableSlots.map((slot) => (
                            <button
                              key={slot.start}
                              onClick={() => handleSlotSelect(slot)}
                              className={cn(
                                "py-2 px-3 text-sm rounded-md border transition-all",
                                selectedSlot?.start === slot.start
                                  ? "bg-blue-600 text-white border-blue-600"
                                  : "bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300"
                              )}
                            >
                              {format(parseISO(slot.start), 'h:mm a')}
                            </button>
                          ))}
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
            </div>
          </div>
        </div>
      </motion.div>
    )
  }

  // Details form step
  if (currentStep === 'details') {
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
            onClick={handleBackToDateTime}
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
                <CardTitle>{meetingInfo?.name}</CardTitle>
                <div className="flex flex-col gap-2 mt-2 text-sm text-muted-foreground">
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4" />
                    <span>{selectedSlot && format(parseISO(selectedSlot.start), 'EEEE, MMMM d, yyyy')}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Clock className="h-4 w-4" />
                    <span>{selectedSlot && format(parseISO(selectedSlot.start), 'h:mm a')} ({meetingInfo?.duration_minutes} min)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {getLocationIcon(meetingInfo?.location_type || '')}
                    <span>{getLocationDisplay()}</span>
                  </div>
                </div>
              </CardHeader>
            <CardContent>
              <form className="space-y-4" onSubmit={handleBooking}>
                <h3 className="font-medium text-lg mb-4 dark:text-white">Enter Details</h3>
                {error && (
                  <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-400 text-sm">
                    {error}
                  </div>
                )}
                
                {loadingFormSchema ? (
                  <div className="text-center py-8">
                    <Loader2 className="h-8 w-8 animate-spin text-blue-600 mx-auto mb-3" />
                    <p className="text-gray-600 dark:text-gray-300">Loading form...</p>
                  </div>
                ) : (
                  <>
                    {formSchema?.fields
                      .sort((a, b) => a.display_order - b.display_order)
                      .map((field) => (
                        <div key={field.field_slug}>
                          <Label htmlFor={field.field_slug}>
                            {field.field_name} {field.is_required && <span className="text-red-500">*</span>}
                          </Label>
                          {field.help_text && (
                            <p className="text-xs text-gray-500 mb-1">{field.help_text}</p>
                          )}
                          {renderFormField(field)}
                        </div>
                      ))}
                  </>
                )}
                
                <Button 
                  type="submit" 
                  className="w-full" 
                  disabled={submitting}
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
              </form>
            </CardContent>
            </Card>
          </motion.div>
        </div>
      </motion.div>
    )
  }
}