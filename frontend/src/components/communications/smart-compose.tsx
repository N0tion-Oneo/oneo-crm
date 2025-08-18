"use client"

import React, { useState, useEffect, useRef, useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { 
  Send, 
  Paperclip, 
  Smile, 
  AtSign, 
  Hash,
  MessageSquare, 
  Phone, 
  Mail, 
  Linkedin, 
  Instagram,
  MessageCircle,
  CheckCircle2,
  AlertCircle,
  Clock,
  Zap,
  Target,
  TrendingUp,
  Users,
  Star,
  X,
  Plus,
  FileText,
  Image as ImageIcon,
  File,
  Mic,
  Video,
  Calendar,
  ExternalLink
} from 'lucide-react'

// Types
interface Channel {
  type: string
  display_name: string
  status: 'available' | 'limited' | 'historical' | 'unavailable'
  user_connected: boolean
  contact_info_available: boolean
  has_history: boolean
  priority: number
  limitations: string[]
  history?: {
    total_messages: number
    last_contact: string
    response_rate: number
    engagement_score: number
  }
  connection_details: Array<{
    id: string
    name: string
    can_send: boolean
    status: string
  }>
}

interface ChannelRecommendation {
  channel_type: string
  display_name: string
  score: number
  reason: string
}

interface Attachment {
  id: string
  name: string
  size: number
  type: string
  url?: string
}

interface SmartComposeProps {
  recordId: number
  recordTitle: string
  onSent?: (messageId: string, channel: string) => void
  onCancel?: () => void
  defaultChannel?: string
  className?: string
}

interface ComposeData {
  channel_type: string
  subject: string
  content: string
  attachments: Attachment[]
  scheduled_at?: string
  priority: 'low' | 'normal' | 'high'
  request_read_receipt: boolean
}

export default function SmartCompose({ 
  recordId, 
  recordTitle, 
  onSent, 
  onCancel, 
  defaultChannel,
  className = "" 
}: SmartComposeProps) {
  const [channels, setChannels] = useState<Channel[]>([])
  const [recommendations, setRecommendations] = useState<ChannelRecommendation[]>([])
  const [selectedChannel, setSelectedChannel] = useState<string>('')
  const [composeData, setComposeData] = useState<ComposeData>({
    channel_type: '',
    subject: '',
    content: '',
    attachments: [],
    priority: 'normal',
    request_read_receipt: false
  })
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [showTemplates, setShowTemplates] = useState(false)
  const [characterCount, setCharacterCount] = useState(0)
  const [suggestions, setSuggestions] = useState<string[]>([])
  
  const contentRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Character limits by channel
  const channelLimits = {
    whatsapp: 4096,
    linkedin: 3000,
    twitter: 280,
    instagram: 2200,
    sms: 160,
    email: 50000
  }

  // Fetch channel availability and recommendations
  useEffect(() => {
    fetchChannelData()
  }, [recordId])

  // Set default channel
  useEffect(() => {
    if (defaultChannel && channels.length > 0) {
      setSelectedChannel(defaultChannel)
      setComposeData(prev => ({ ...prev, channel_type: defaultChannel }))
    } else if (recommendations.length > 0 && !selectedChannel) {
      const primaryChannel = recommendations[0].channel_type
      setSelectedChannel(primaryChannel)
      setComposeData(prev => ({ ...prev, channel_type: primaryChannel }))
    }
  }, [defaultChannel, channels, recommendations, selectedChannel])

  // Update character count
  useEffect(() => {
    setCharacterCount(composeData.content.length)
  }, [composeData.content])

  const fetchChannelData = async () => {
    try {
      setLoading(true)
      
      // Fetch channel availability
      const channelResponse = await fetch(`/api/v1/communications/records/${recordId}/channels/`)
      if (channelResponse.ok) {
        const channelData = await channelResponse.json()
        setChannels(channelData.available_channels || [])
      }
      
      // Fetch recommendations
      const recResponse = await fetch(`/api/v1/communications/records/${recordId}/channels/recommendations/`)
      if (recResponse.ok) {
        const recData = await recResponse.json()
        if (recData.primary_channel) {
          const primary = recData.primary_channel
          const alternatives = recData.alternative_channels || []
          setRecommendations([primary, ...alternatives])
        }
      }
      
    } catch (error) {
      console.error('Error fetching channel data:', error)
    } finally {
      setLoading(false)
    }
  }

  // Available channels for selection
  const availableChannels = useMemo(() => {
    return channels.filter(channel => 
      channel.status === 'available' && 
      channel.user_connected && 
      channel.contact_info_available
    )
  }, [channels])

  // Get character limit for selected channel
  const characterLimit = useMemo(() => {
    if (!selectedChannel) return null
    return channelLimits[selectedChannel as keyof typeof channelLimits] || null
  }, [selectedChannel])

  // Check if message is too long
  const isContentTooLong = useMemo(() => {
    return characterLimit ? characterCount > characterLimit : false
  }, [characterCount, characterLimit])

  // Handle channel selection
  const handleChannelSelect = (channelType: string) => {
    setSelectedChannel(channelType)
    setComposeData(prev => ({ ...prev, channel_type: channelType }))
  }

  // Handle file attachment
  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    if (!files) return

    Array.from(files).forEach(file => {
      const attachment: Attachment = {
        id: Math.random().toString(36).substr(2, 9),
        name: file.name,
        size: file.size,
        type: file.type
      }
      
      setComposeData(prev => ({
        ...prev,
        attachments: [...prev.attachments, attachment]
      }))
    })
  }

  // Remove attachment
  const removeAttachment = (attachmentId: string) => {
    setComposeData(prev => ({
      ...prev,
      attachments: prev.attachments.filter(att => att.id !== attachmentId)
    }))
  }

  // Send message
  const handleSend = async () => {
    if (!selectedChannel || !composeData.content.trim()) {
      return
    }

    try {
      setSending(true)
      
      const response = await fetch(`/api/v1/communications/records/${recordId}/send-message/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          content: composeData.content,
          subject: composeData.subject,
          channel_type: selectedChannel,
          attachments: composeData.attachments,
          priority: composeData.priority,
          request_read_receipt: composeData.request_read_receipt
        })
      })
      
      if (response.ok) {
        const result = await response.json()
        onSent?.(result.message_id, selectedChannel)
        
        // Reset form
        setComposeData({
          channel_type: selectedChannel,
          subject: '',
          content: '',
          attachments: [],
          priority: 'normal',
          request_read_receipt: false
        })
      }
      
    } catch (error) {
      console.error('Error sending message:', error)
    } finally {
      setSending(false)
    }
  }

  // Handle template selection
  const insertTemplate = (template: string) => {
    setComposeData(prev => ({
      ...prev,
      content: prev.content + template
    }))
    setShowTemplates(false)
  }

  // Get channel icon
  const getChannelIcon = (channelType: string) => {
    switch (channelType) {
      case 'whatsapp': return <MessageCircle className="h-4 w-4" />
      case 'linkedin': return <Linkedin className="h-4 w-4" />
      case 'gmail':
      case 'outlook':
      case 'mail': return <Mail className="h-4 w-4" />
      case 'phone': return <Phone className="h-4 w-4" />
      case 'instagram': return <Instagram className="h-4 w-4" />
      default: return <MessageSquare className="h-4 w-4" />
    }
  }

  // Get channel color
  const getChannelColor = (channelType: string) => {
    switch (channelType) {
      case 'whatsapp': return 'bg-green-500 border-green-600 text-green-700'
      case 'linkedin': return 'bg-blue-600 border-blue-700 text-blue-700'
      case 'gmail': return 'bg-red-500 border-red-600 text-red-700'
      case 'outlook': return 'bg-blue-500 border-blue-600 text-blue-700'
      case 'instagram': return 'bg-purple-500 border-purple-600 text-purple-700'
      default: return 'bg-gray-500 border-gray-600 text-gray-700'
    }
  }

  // Get recommendation score color
  const getScoreColor = (score: number) => {
    if (score >= 8) return 'text-green-600 bg-green-50 border-green-200'
    if (score >= 6) return 'text-yellow-600 bg-yellow-50 border-yellow-200'
    return 'text-red-600 bg-red-50 border-red-200'
  }

  // Format file size
  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  if (loading) {
    return (
      <Card className={className}>
        <CardContent className="p-6">
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={className}>
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Send className="h-5 w-5" />
            Compose Message
            <Badge variant="outline">{recordTitle}</Badge>
          </CardTitle>
          
          {onCancel && (
            <Button variant="ghost" size="sm" onClick={onCancel}>
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Channel Selection */}
        <div className="space-y-3">
          <Label className="text-sm font-medium">Select Channel</Label>
          
          {/* Recommended Channels */}
          {recommendations.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Zap className="h-4 w-4 text-yellow-500" />
                <span className="text-sm font-medium text-gray-700">Recommended</span>
              </div>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {recommendations.slice(0, 2).map((rec) => {
                  const channel = channels.find(ch => ch.type === rec.channel_type)
                  if (!channel || channel.status !== 'available') return null
                  
                  return (
                    <Button
                      key={rec.channel_type}
                      variant={selectedChannel === rec.channel_type ? "default" : "outline"}
                      className={`justify-start h-auto p-3 ${
                        selectedChannel === rec.channel_type ? getChannelColor(rec.channel_type) : ''
                      }`}
                      onClick={() => handleChannelSelect(rec.channel_type)}
                    >
                      <div className="flex items-center gap-3 w-full">
                        <div className={`p-1 rounded-full text-white ${
                          selectedChannel === rec.channel_type ? 'bg-white bg-opacity-20' : getChannelColor(rec.channel_type).split(' ')[0]
                        }`}>
                          {getChannelIcon(rec.channel_type)}
                        </div>
                        
                        <div className="flex-1 text-left">
                          <div className="font-medium">{rec.display_name}</div>
                          <div className="text-xs opacity-75">{rec.reason}</div>
                        </div>
                        
                        <Badge className={getScoreColor(rec.score)}>
                          {rec.score.toFixed(1)}
                        </Badge>
                      </div>
                    </Button>
                  )
                })}
              </div>
            </div>
          )}
          
          {/* All Available Channels */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Users className="h-4 w-4 text-blue-500" />
              <span className="text-sm font-medium text-gray-700">All Channels</span>
            </div>
            
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
              {availableChannels.map((channel) => (
                <TooltipProvider key={channel.type}>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant={selectedChannel === channel.type ? "default" : "outline"}
                        size="sm"
                        className={`justify-start ${
                          selectedChannel === channel.type ? getChannelColor(channel.type) : ''
                        }`}
                        onClick={() => handleChannelSelect(channel.type)}
                      >
                        <div className={`p-1 rounded-full text-white mr-2 ${
                          selectedChannel === channel.type ? 'bg-white bg-opacity-20' : getChannelColor(channel.type).split(' ')[0]
                        }`}>
                          {getChannelIcon(channel.type)}
                        </div>
                        {channel.display_name}
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>
                      <div className="space-y-1">
                        <p className="font-medium">{channel.display_name}</p>
                        {channel.history && (
                          <div className="text-xs text-gray-500">
                            <p>{channel.history.total_messages} messages</p>
                            <p>{channel.history.response_rate.toFixed(1)}% response rate</p>
                          </div>
                        )}
                      </div>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              ))}
            </div>
          </div>
        </div>

        {/* Subject Line (for email channels) */}
        {selectedChannel && ['gmail', 'outlook', 'mail'].includes(selectedChannel) && (
          <div className="space-y-2">
            <Label htmlFor="subject">Subject</Label>
            <Input
              id="subject"
              placeholder="Enter subject line..."
              value={composeData.subject}
              onChange={(e) => setComposeData(prev => ({ ...prev, subject: e.target.value }))}
            />
          </div>
        )}

        {/* Message Content */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label htmlFor="content">Message</Label>
            <div className="flex items-center gap-2">
              {characterLimit && (
                <span className={`text-xs ${
                  isContentTooLong ? 'text-red-500' : 'text-gray-500'
                }`}>
                  {characterCount}/{characterLimit}
                </span>
              )}
              
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowTemplates(!showTemplates)}
              >
                <FileText className="h-4 w-4" />
              </Button>
            </div>
          </div>
          
          <Textarea
            ref={contentRef}
            id="content"
            placeholder="Type your message..."
            value={composeData.content}
            onChange={(e) => setComposeData(prev => ({ ...prev, content: e.target.value }))}
            className={`min-h-[120px] resize-none ${
              isContentTooLong ? 'border-red-300 focus:border-red-500' : ''
            }`}
          />
          
          {isContentTooLong && (
            <p className="text-sm text-red-500">
              Message exceeds {characterLimit} character limit for {selectedChannel}
            </p>
          )}
        </div>

        {/* Quick Templates */}
        {showTemplates && (
          <Card className="border border-gray-200">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Quick Templates</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {[
                "Hi {name}, I wanted to follow up on our previous conversation...",
                "Thank you for your interest in our services. I'd be happy to discuss...",
                "I hope this message finds you well. I'm reaching out regarding...",
                "Thanks for connecting! I look forward to exploring potential collaboration..."
              ].map((template, index) => (
                <Button
                  key={index}
                  variant="ghost"
                  size="sm"
                  className="h-auto p-2 text-left justify-start whitespace-normal"
                  onClick={() => insertTemplate(template)}
                >
                  {template}
                </Button>
              ))}
            </CardContent>
          </Card>
        )}

        {/* Attachments */}
        {composeData.attachments.length > 0 && (
          <div className="space-y-2">
            <Label>Attachments</Label>
            <div className="space-y-2">
              {composeData.attachments.map((attachment) => (
                <div key={attachment.id} className="flex items-center gap-3 p-2 border rounded-md">
                  <div className="p-1 bg-gray-100 rounded">
                    {attachment.type.startsWith('image/') ? (
                      <ImageIcon className="h-4 w-4" />
                    ) : (
                      <File className="h-4 w-4" />
                    )}
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{attachment.name}</p>
                    <p className="text-xs text-gray-500">{formatFileSize(attachment.size)}</p>
                  </div>
                  
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => removeAttachment(attachment.id)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Action Bar */}
        <div className="flex items-center justify-between pt-4 border-t">
          <div className="flex items-center gap-2">
            {/* Attachment Button */}
            <input
              ref={fileInputRef}
              type="file"
              multiple
              className="hidden"
              onChange={handleFileSelect}
            />
            <Button
              variant="ghost"
              size="sm"
              onClick={() => fileInputRef.current?.click()}
            >
              <Paperclip className="h-4 w-4" />
            </Button>
            
            {/* Advanced Options */}
            <Popover>
              <PopoverTrigger asChild>
                <Button variant="ghost" size="sm">
                  <Zap className="h-4 w-4" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-80">
                <div className="space-y-4">
                  <h4 className="font-medium">Message Options</h4>
                  
                  <div className="space-y-2">
                    <Label>Priority</Label>
                    <div className="flex gap-2">
                      {['low', 'normal', 'high'].map((priority) => (
                        <Button
                          key={priority}
                          variant={composeData.priority === priority ? "default" : "outline"}
                          size="sm"
                          onClick={() => setComposeData(prev => ({ 
                            ...prev, 
                            priority: priority as ComposeData['priority'] 
                          }))}
                        >
                          {priority.charAt(0).toUpperCase() + priority.slice(1)}
                        </Button>
                      ))}
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="read-receipt"
                      checked={composeData.request_read_receipt}
                      onChange={(e) => setComposeData(prev => ({ 
                        ...prev, 
                        request_read_receipt: e.target.checked 
                      }))}
                    />
                    <Label htmlFor="read-receipt" className="text-sm">
                      Request read receipt
                    </Label>
                  </div>
                </div>
              </PopoverContent>
            </Popover>
          </div>
          
          {/* Send Button */}
          <Button
            onClick={handleSend}
            disabled={!selectedChannel || !composeData.content.trim() || isContentTooLong || sending}
            className="min-w-[100px]"
          >
            {sending ? (
              <div className="flex items-center gap-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                Sending...
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Send className="h-4 w-4" />
                Send
              </div>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}