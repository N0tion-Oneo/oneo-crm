'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Calendar, Clock, MapPin, User, Mail, Phone, ArrowLeft, ArrowRight, Check } from 'lucide-react'
import { format, parseISO, addDays, startOfDay, endOfDay } from 'date-fns'
import axios from 'axios'

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
  }
}

interface TimeSlot {
  start: string
  end: string
}

export default function BookingPage() {
  const params = useParams()
  const slug = params.slug as string
  
  const [loading, setLoading] = useState(true)
  const [linkData, setLinkData] = useState<SchedulingLink | null>(null)
  const [error, setError] = useState<string | null>(null)
  
  // Booking flow states
  const [step, setStep] = useState<'select-date' | 'select-time' | 'enter-details' | 'confirmation'>('select-date')
  const [selectedDate, setSelectedDate] = useState<Date | null>(null)
  const [selectedSlot, setSelectedSlot] = useState<TimeSlot | null>(null)
  const [availableSlots, setAvailableSlots] = useState<TimeSlot[]>([])
  const [loadingSlots, setLoadingSlots] = useState(false)
  
  // Form data
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    notes: ''
  })
  
  const [submitting, setSubmitting] = useState(false)
  const [bookingConfirmation, setBookingConfirmation] = useState<any>(null)

  useEffect(() => {
    fetchLinkDetails()
  }, [slug])

  useEffect(() => {
    if (selectedDate) {
      fetchAvailableSlots(selectedDate)
    }
  }, [selectedDate])

  const fetchLinkDetails = async () => {
    try {
      // Get tenant from hostname
      const hostname = window.location.hostname
      const tenant = hostname.split('.')[0]
      
      // Use the tenant subdomain in the API URL
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || `http://${tenant}.localhost:8000`
      
      const response = await axios.get(
        `${apiUrl}/api/v1/communications/scheduling/public/links/${slug}/`
      )
      setLinkData(response.data)
    } catch (err: any) {
      console.error('Failed to fetch link details:', err)
      setError(err.response?.status === 404 ? 'Booking link not found' : 'Failed to load booking page')
    } finally {
      setLoading(false)
    }
  }

  const fetchAvailableSlots = async (date: Date) => {
    if (!linkData) return
    
    setLoadingSlots(true)
    try {
      const tenant = window.location.hostname.split('.')[0]
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || `http://${tenant}.localhost:8000`
      const startDate = startOfDay(date).toISOString()
      const endDate = endOfDay(date).toISOString()
      
      const response = await axios.post(
        `${apiUrl}/api/v1/communications/scheduling/public/links/${slug}/availability/`,
        {
          start_date: startDate,
          end_date: endDate,
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
        }
      )
      setAvailableSlots(response.data.slots || [])
    } catch (err) {
      console.error('Failed to fetch available slots:', err)
      setAvailableSlots([])
    } finally {
      setLoadingSlots(false)
    }
  }

  const handleBooking = async () => {
    if (!selectedSlot || !linkData) return
    
    setSubmitting(true)
    try {
      const tenant = window.location.hostname.split('.')[0]
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || `http://${tenant}.localhost:8000`
      
      const response = await axios.post(
        `${apiUrl}/api/v1/communications/scheduling/public/links/${slug}/book/`,
        {
          ...formData,
          selected_slot: selectedSlot,
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
        }
      )
      
      setBookingConfirmation(response.data)
      setStep('confirmation')
    } catch (err: any) {
      console.error('Failed to book meeting:', err)
      alert(err.response?.data?.error || 'Failed to book meeting. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="max-w-md">
          <CardContent className="pt-6">
            <p className="text-center text-muted-foreground">{error}</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (!linkData) {
    return null
  }

  return (
    <div className="min-h-screen bg-background py-12 px-4">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold mb-2">
            {linkData.public_name || linkData.meeting_type.name}
          </h1>
          {linkData.public_description && (
            <p className="text-muted-foreground">{linkData.public_description}</p>
          )}
          
          <div className="flex items-center justify-center gap-6 mt-6 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <User className="h-4 w-4" />
              <span>{linkData.host.name}</span>
            </div>
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4" />
              <span>{linkData.meeting_type.duration_minutes} minutes</span>
            </div>
            {linkData.meeting_type.location_type && (
              <div className="flex items-center gap-2">
                <MapPin className="h-4 w-4" />
                <span>
                  {linkData.meeting_type.location_type === 'google_meet' ? 'Google Meet' :
                   linkData.meeting_type.location_type === 'zoom' ? 'Zoom' :
                   linkData.meeting_type.location_type === 'teams' ? 'Microsoft Teams' :
                   linkData.meeting_type.location_type === 'phone' ? 'Phone Call' :
                   linkData.meeting_type.location_type === 'in_person' ? 'In Person' :
                   'Online Meeting'}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Booking Steps */}
        {step === 'select-date' && (
          <Card>
            <CardHeader>
              <CardTitle>Select a Date</CardTitle>
              <CardDescription>Choose an available date for your meeting</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 sm:grid-cols-4 gap-3">
                {Array.from({ length: 30 }, (_, i) => {
                  const date = addDays(new Date(), i)
                  const isWeekend = date.getDay() === 0 || date.getDay() === 6
                  
                  return (
                    <Button
                      key={i}
                      variant={selectedDate?.toDateString() === date.toDateString() ? 'default' : 'outline'}
                      className="flex flex-col h-auto py-3"
                      onClick={() => {
                        setSelectedDate(date)
                        setStep('select-time')
                      }}
                      disabled={isWeekend}
                    >
                      <span className="text-xs">{format(date, 'EEE')}</span>
                      <span className="text-lg font-semibold">{format(date, 'd')}</span>
                      <span className="text-xs">{format(date, 'MMM')}</span>
                    </Button>
                  )
                })}
              </div>
            </CardContent>
          </Card>
        )}

        {step === 'select-time' && selectedDate && (
          <Card>
            <CardHeader>
              <CardTitle>Select a Time</CardTitle>
              <CardDescription>
                Available times for {format(selectedDate, 'EEEE, MMMM d, yyyy')}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loadingSlots ? (
                <div className="flex justify-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
                </div>
              ) : availableSlots.length > 0 ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                    {availableSlots.map((slot, index) => {
                      const startTime = parseISO(slot.start)
                      return (
                        <Button
                          key={index}
                          variant={selectedSlot === slot ? 'default' : 'outline'}
                          onClick={() => setSelectedSlot(slot)}
                        >
                          {format(startTime, 'h:mm a')}
                        </Button>
                      )
                    })}
                  </div>
                  
                  <div className="flex gap-3 pt-4">
                    <Button
                      variant="outline"
                      onClick={() => {
                        setStep('select-date')
                        setSelectedSlot(null)
                      }}
                    >
                      <ArrowLeft className="h-4 w-4 mr-2" />
                      Back
                    </Button>
                    <Button
                      className="flex-1"
                      onClick={() => setStep('enter-details')}
                      disabled={!selectedSlot}
                    >
                      Continue
                      <ArrowRight className="h-4 w-4 ml-2" />
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8">
                  <p className="text-muted-foreground mb-4">No available times for this date</p>
                  <Button
                    variant="outline"
                    onClick={() => {
                      setStep('select-date')
                      setSelectedDate(null)
                    }}
                  >
                    <ArrowLeft className="h-4 w-4 mr-2" />
                    Select Another Date
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {step === 'enter-details' && selectedSlot && (
          <Card>
            <CardHeader>
              <CardTitle>Enter Your Details</CardTitle>
              <CardDescription>
                {selectedDate && format(parseISO(selectedSlot.start), 'EEEE, MMMM d, yyyy at h:mm a')}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Name *</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="John Doe"
                    required
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="email">Email *</Label>
                  <Input
                    id="email"
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    placeholder="john@example.com"
                    required
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="phone">Phone (Optional)</Label>
                  <Input
                    id="phone"
                    type="tel"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    placeholder="+1 (555) 123-4567"
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="notes">Additional Notes (Optional)</Label>
                  <textarea
                    id="notes"
                    className="min-h-[100px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={formData.notes}
                    onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                    placeholder="Please share anything that will help prepare for our meeting"
                  />
                </div>
                
                <div className="flex gap-3 pt-4">
                  <Button
                    variant="outline"
                    onClick={() => setStep('select-time')}
                  >
                    <ArrowLeft className="h-4 w-4 mr-2" />
                    Back
                  </Button>
                  <Button
                    className="flex-1"
                    onClick={handleBooking}
                    disabled={!formData.name || !formData.email || submitting}
                  >
                    {submitting ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                        Booking...
                      </>
                    ) : (
                      <>
                        Book Meeting
                        <Check className="h-4 w-4 ml-2" />
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {step === 'confirmation' && bookingConfirmation && (
          <Card>
            <CardHeader>
              <CardTitle>Meeting Confirmed!</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="bg-green-50 dark:bg-green-900/20 p-4 rounded-lg">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="h-10 w-10 rounded-full bg-green-500 flex items-center justify-center">
                      <Check className="h-6 w-6 text-white" />
                    </div>
                    <div>
                      <p className="font-semibold">Your meeting has been scheduled</p>
                      <p className="text-sm text-muted-foreground">A confirmation email has been sent to {formData.email}</p>
                    </div>
                  </div>
                </div>
                
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <Calendar className="h-5 w-5 text-muted-foreground" />
                    <span>{selectedDate && format(parseISO(selectedSlot!.start), 'EEEE, MMMM d, yyyy')}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <Clock className="h-5 w-5 text-muted-foreground" />
                    <span>{format(parseISO(selectedSlot!.start), 'h:mm a')} - {format(parseISO(selectedSlot!.end), 'h:mm a')}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <User className="h-5 w-5 text-muted-foreground" />
                    <span>With {linkData.host.name}</span>
                  </div>
                  {bookingConfirmation.meeting_url && (
                    <div className="flex items-center gap-3">
                      <MapPin className="h-5 w-5 text-muted-foreground" />
                      <a href={bookingConfirmation.meeting_url} className="text-blue-600 hover:underline">
                        Join Meeting
                      </a>
                    </div>
                  )}
                </div>
                
                <div className="pt-4">
                  <p className="text-sm text-muted-foreground">
                    Need to make changes? Check your email for rescheduling or cancellation options.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}