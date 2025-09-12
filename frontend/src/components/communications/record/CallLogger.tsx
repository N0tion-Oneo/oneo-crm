import React, { useState } from 'react'
import { Phone, Clock, X, PhoneCall, PhoneIncoming, PhoneOutgoing, PhoneMissed } from 'lucide-react'
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

interface CallLoggerProps {
  recordId: string
  onCallLogged?: () => void
  onCancel?: () => void
  defaultParticipant?: {
    email?: string
    name?: string
    phone?: string
  }
}

export function CallLogger({
  recordId,
  onCallLogged,
  onCancel,
  defaultParticipant
}: CallLoggerProps) {
  const [callType, setCallType] = useState<'outgoing' | 'incoming' | 'missed'>('outgoing')
  const [phoneNumber, setPhoneNumber] = useState(defaultParticipant?.phone || '')
  const [contactName, setContactName] = useState(defaultParticipant?.name || '')
  const [callDate, setCallDate] = useState(new Date().toISOString().split('T')[0])
  const [callTime, setCallTime] = useState(new Date().toTimeString().slice(0, 5))
  const [duration, setDuration] = useState('')
  const [notes, setNotes] = useState('')
  const [outcome, setOutcome] = useState<'connected' | 'voicemail' | 'no_answer' | 'busy'>('connected')
  const [isLogging, setIsLogging] = useState(false)

  const handleLog = async () => {
    // Validate required fields
    if (!phoneNumber || !callDate || !callTime) {
      toast({
        title: 'Missing Information',
        description: 'Please fill in the required fields (phone number, date, time)',
        variant: 'destructive'
      })
      return
    }

    setIsLogging(true)
    try {
      const callDateTime = `${callDate}T${callTime}:00`
      
      // Create call log data
      const callData = {
        call_type: callType,
        phone_number: phoneNumber,
        contact_name: contactName,
        call_time: callDateTime,
        duration_minutes: duration ? parseInt(duration) : null,
        outcome,
        notes,
        record_id: recordId,
        metadata: {
          created_from: 'record_communications',
          is_manual_log: true
        }
      }

      // Call the API to log the call
      const response = await api.post('/api/v1/communications/calls/log/', callData)

      toast({
        title: 'Call Logged',
        description: `Call with ${contactName || phoneNumber} has been logged`,
      })

      // Clear form and notify parent
      setPhoneNumber('')
      setContactName('')
      setCallDate(new Date().toISOString().split('T')[0])
      setCallTime(new Date().toTimeString().slice(0, 5))
      setDuration('')
      setNotes('')
      setOutcome('connected')
      
      if (onCallLogged) {
        onCallLogged()
      }
    } catch (error: any) {
      console.error('Failed to log call:', error)
      toast({
        title: 'Failed to Log Call',
        description: error.response?.data?.detail || 'Could not log the call',
        variant: 'destructive'
      })
    } finally {
      setIsLogging(false)
    }
  }

  const getCallIcon = () => {
    switch (callType) {
      case 'incoming': return <PhoneIncoming className="w-4 h-4" />
      case 'outgoing': return <PhoneOutgoing className="w-4 h-4" />
      case 'missed': return <PhoneMissed className="w-4 h-4" />
      default: return <Phone className="w-4 h-4" />
    }
  }

  return (
    <div className="p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Phone className="w-5 h-5" />
            Log Call
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

        {/* Call Type and Phone */}
        <div className="grid grid-cols-3 gap-4">
          <div>
            <Label htmlFor="call-type">Call Type</Label>
            <Select value={callType} onValueChange={(value: any) => setCallType(value)}>
              <SelectTrigger id="call-type">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="outgoing">
                  <div className="flex items-center gap-2">
                    <PhoneOutgoing className="w-4 h-4" />
                    <span>Outgoing</span>
                  </div>
                </SelectItem>
                <SelectItem value="incoming">
                  <div className="flex items-center gap-2">
                    <PhoneIncoming className="w-4 h-4" />
                    <span>Incoming</span>
                  </div>
                </SelectItem>
                <SelectItem value="missed">
                  <div className="flex items-center gap-2">
                    <PhoneMissed className="w-4 h-4" />
                    <span>Missed</span>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="col-span-2">
            <Label htmlFor="phone">Phone Number *</Label>
            <Input
              id="phone"
              type="tel"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              placeholder="+1 234 567 8900"
              required
            />
          </div>
        </div>

        {/* Contact Name */}
        <div>
          <Label htmlFor="contact-name">Contact Name</Label>
          <Input
            id="contact-name"
            type="text"
            value={contactName}
            onChange={(e) => setContactName(e.target.value)}
            placeholder="John Doe"
          />
        </div>

        {/* Date, Time, and Duration */}
        <div className="grid grid-cols-3 gap-4">
          <div>
            <Label htmlFor="date">Date *</Label>
            <Input
              id="date"
              type="date"
              value={callDate}
              onChange={(e) => setCallDate(e.target.value)}
              max={new Date().toISOString().split('T')[0]}
              required
            />
          </div>
          <div>
            <Label htmlFor="time">Time *</Label>
            <Input
              id="time"
              type="time"
              value={callTime}
              onChange={(e) => setCallTime(e.target.value)}
              required
            />
          </div>
          <div>
            <Label htmlFor="duration">Duration (minutes)</Label>
            <Input
              id="duration"
              type="number"
              value={duration}
              onChange={(e) => setDuration(e.target.value)}
              placeholder="15"
              min="0"
              disabled={callType === 'missed'}
            />
          </div>
        </div>

        {/* Outcome */}
        {callType !== 'missed' && (
          <div>
            <Label htmlFor="outcome">Call Outcome</Label>
            <Select value={outcome} onValueChange={(value: any) => setOutcome(value)}>
              <SelectTrigger id="outcome">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="connected">Connected</SelectItem>
                <SelectItem value="voicemail">Left Voicemail</SelectItem>
                <SelectItem value="no_answer">No Answer</SelectItem>
                <SelectItem value="busy">Busy</SelectItem>
              </SelectContent>
            </Select>
          </div>
        )}

        {/* Notes */}
        <div>
          <Label htmlFor="notes">Call Notes</Label>
          <Textarea
            id="notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Discussion points, follow-up actions, etc..."
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
            onClick={handleLog}
            disabled={isLogging || !phoneNumber || !callDate || !callTime}
          >
            {isLogging ? 'Logging...' : 'Log Call'}
          </Button>
        </div>

        {/* Call Summary */}
        {phoneNumber && callDate && callTime && (
          <div className="text-sm text-gray-500 dark:text-gray-400 border-t pt-3">
            <div className="flex items-center gap-2">
              {getCallIcon()}
              <span className="font-medium">
                {callType === 'outgoing' ? 'Outgoing call to' : 
                 callType === 'incoming' ? 'Incoming call from' : 
                 'Missed call from'} {contactName || phoneNumber}
              </span>
            </div>
            <div className="flex items-center gap-4 mt-1">
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {new Date(callDate).toLocaleDateString()} at {callTime}
              </span>
              {duration && callType !== 'missed' && (
                <span>{duration} minutes</span>
              )}
              {outcome && callType !== 'missed' && (
                <span className="capitalize">{outcome.replace('_', ' ')}</span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}