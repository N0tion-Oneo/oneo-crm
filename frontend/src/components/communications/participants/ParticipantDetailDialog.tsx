'use client'

import React, { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Mail,
  Phone,
  Linkedin,
  Instagram,
  Twitter,
  Calendar,
  MessageSquare,
  Activity,
  User,
  Link2,
  Unlink,
  UserPlus,
  RefreshCw,
  Settings
} from 'lucide-react'
import { useToast } from '@/hooks/use-toast'
import { communicationsApi } from '@/lib/api'
import { format } from 'date-fns'

interface Participant {
  id: string
  name: string
  email: string
  phone: string
  linkedin_member_urn?: string
  instagram_username?: string
  twitter_handle?: string
  avatar_url?: string
  contact_record?: string
  contact_record_display?: {
    id: string
    display_name: string
    pipeline_name: string
  }
  secondary_record?: string
  is_linked: boolean
  conversation_count: number
  last_activity?: string
  channel_types: string[]
  resolution_confidence?: number
  resolution_method?: string
  resolved_at?: string
  first_seen: string
  last_seen: string
}

interface ConversationSummary {
  total_count: number
  by_channel: Record<string, number>
  recent_conversations: Array<{
    id: string
    subject?: string
    last_message_at: string
    channel: string
    message_count: number
  }>
}

interface ParticipantDetailDialogProps {
  participant: Participant | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onRefresh: () => void
}

export function ParticipantDetailDialog({
  participant,
  open,
  onOpenChange,
  onRefresh
}: ParticipantDetailDialogProps) {
  const [loading, setLoading] = useState(false)
  const [conversationSummary, setConversationSummary] = useState<ConversationSummary | null>(null)
  const [fieldMapping, setFieldMapping] = useState<any[]>([])
  const [activeTab, setActiveTab] = useState('overview')
  const [selectedPipelineId, setSelectedPipelineId] = useState<string>('')
  const [pipelines, setPipelines] = useState<any[]>([])
  const [mappingLoading, setMappingLoading] = useState(false)
  const [showOverrideDialog, setShowOverrideDialog] = useState(false)
  const [overrideSettings, setOverrideSettings] = useState<any>({})
  
  const { toast } = useToast()

  useEffect(() => {
    if (open && participant) {
      loadParticipantDetails()
      if (!participant.is_linked) {
        loadCompatiblePipelines()
      }
    }
  }, [open, participant])

  useEffect(() => {
    if (selectedPipelineId && participant && !participant.is_linked) {
      loadFieldMappingForPipeline(selectedPipelineId)
    }
  }, [selectedPipelineId, participant])

  const loadParticipantDetails = async () => {
    if (!participant) return
    
    setLoading(true)
    try {
      // Load conversation summary
      const convResponse = await communicationsApi.getParticipantConversations(participant.id)
      setConversationSummary(convResponse.data)
      
      // Load field mapping if not linked
      // Note: Field mapping requires a pipeline_id to be selected
      // We'll load this when user selects a pipeline in the mapping tab
      if (!participant.is_linked) {
        setFieldMapping([])
      }
    } catch (error) {
      console.error('Error loading participant details:', error)
      toast({
        title: "Failed to load details",
        description: "Please try again",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const loadCompatiblePipelines = async () => {
    try {
      const response = await communicationsApi.getCompatiblePipelines()
      setPipelines(response.data || [])
    } catch (error) {
      console.error('Error loading pipelines:', error)
    }
  }

  const loadFieldMappingForPipeline = async (pipelineId: string) => {
    if (!participant) return
    
    setMappingLoading(true)
    try {
      const response = await communicationsApi.getParticipantFieldMapping(
        participant.id, 
        { pipeline_id: pipelineId }
      )
      setFieldMapping(response.data.mappings || [])
    } catch (error) {
      console.error('Error loading field mapping:', error)
      toast({
        title: "Failed to load field mapping",
        description: "Please try again",
        variant: "destructive",
      })
    } finally {
      setMappingLoading(false)
    }
  }

  const handleUnlink = async () => {
    if (!participant) return
    
    try {
      await communicationsApi.unlinkParticipant(participant.id)
      toast({
        title: "Participant unlinked",
        description: "Successfully removed record link",
      })
      onRefresh()
      onOpenChange(false)
    } catch (error) {
      console.error('Error unlinking participant:', error)
      toast({
        title: "Failed to unlink",
        description: "Please try again",
        variant: "destructive",
      })
    }
  }

  const getIdentifierBadges = () => {
    if (!participant) return []
    
    const identifiers = []
    
    if (participant.email) {
      identifiers.push(
        <Badge key="email" variant="outline" className="flex items-center gap-1">
          <Mail className="w-3 h-3" />
          {participant.email}
        </Badge>
      )
    }
    
    if (participant.phone) {
      identifiers.push(
        <Badge key="phone" variant="outline" className="flex items-center gap-1">
          <Phone className="w-3 h-3" />
          {participant.phone}
        </Badge>
      )
    }
    
    if (participant.linkedin_member_urn) {
      identifiers.push(
        <Badge key="linkedin" variant="outline" className="flex items-center gap-1">
          <Linkedin className="w-3 h-3" />
          LinkedIn
        </Badge>
      )
    }
    
    if (participant.instagram_username) {
      identifiers.push(
        <Badge key="instagram" variant="outline" className="flex items-center gap-1">
          <Instagram className="w-3 h-3" />
          @{participant.instagram_username}
        </Badge>
      )
    }
    
    if (participant.twitter_handle) {
      identifiers.push(
        <Badge key="twitter" variant="outline" className="flex items-center gap-1">
          <Twitter className="w-3 h-3" />
          @{participant.twitter_handle}
        </Badge>
      )
    }
    
    return identifiers
  }

  if (!participant) return null

  return (
    <>
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              {participant.avatar_url ? (
                <img
                  src={participant.avatar_url}
                  alt={participant.name}
                  className="w-12 h-12 rounded-full"
                />
              ) : (
                <div className="w-12 h-12 rounded-full bg-gray-200 flex items-center justify-center">
                  <User className="w-6 h-6 text-gray-500" />
                </div>
              )}
              <div>
                <DialogTitle className="text-xl">
                  {participant.name || 'Unknown Participant'}
                </DialogTitle>
                <DialogDescription className="flex items-center gap-2 mt-1">
                  {participant.is_linked ? (
                    <>
                      <Link2 className="w-4 h-4 text-green-500" />
                      <span>Linked to {participant.contact_record_display?.display_name}</span>
                    </>
                  ) : (
                    <>
                      <Unlink className="w-4 h-4 text-gray-400" />
                      <span>Not linked to any record</span>
                    </>
                  )}
                </DialogDescription>
              </div>
            </div>
            
            <Button
              onClick={() => loadParticipantDetails()}
              variant="outline"
              size="sm"
            >
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>
        </DialogHeader>

        <div className="mt-4 space-y-4">
          {/* Identifiers */}
          <div className="flex flex-wrap gap-2">
            {getIdentifierBadges()}
          </div>

          {/* Tabs */}
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="conversations">Conversations</TabsTrigger>
              {!participant.is_linked && (
                <TabsTrigger value="mapping">Field Mapping</TabsTrigger>
              )}
            </TabsList>

            <TabsContent value="overview" className="space-y-4 mt-4">
              {/* Link Status */}
              {participant.is_linked ? (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-medium text-green-900">Linked Record</h4>
                      <p className="text-sm text-green-700 mt-1">
                        {participant.contact_record_display?.display_name}
                      </p>
                      <p className="text-xs text-green-600">
                        Pipeline: {participant.contact_record_display?.pipeline_name}
                      </p>
                      {participant.resolution_confidence && (
                        <p className="text-xs text-green-600 mt-1">
                          Confidence: {(participant.resolution_confidence * 100).toFixed(0)}%
                        </p>
                      )}
                    </div>
                    <Button
                      onClick={handleUnlink}
                      variant="outline"
                      size="sm"
                      className="text-red-600"
                    >
                      <Unlink className="w-4 h-4 mr-2" />
                      Unlink
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-medium text-yellow-900">No Linked Record</h4>
                      <p className="text-sm text-yellow-700 mt-1">
                        This participant is not linked to any CRM record
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <Button 
                        size="sm" 
                        variant="outline"
                        onClick={() => setShowOverrideDialog(true)}
                      >
                        <Settings className="w-4 h-4 mr-2" />
                        Override Settings
                      </Button>
                      <Button size="sm">
                        <UserPlus className="w-4 h-4 mr-2" />
                        Create Record
                      </Button>
                    </div>
                  </div>
                </div>
              )}

              {/* Activity Summary */}
              <div className="grid grid-cols-2 gap-4">
                <div className="border rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Conversations</span>
                    <MessageSquare className="w-4 h-4 text-gray-400" />
                  </div>
                  <p className="text-2xl font-semibold mt-2">
                    {participant.conversation_count}
                  </p>
                </div>
                
                <div className="border rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Last Activity</span>
                    <Activity className="w-4 h-4 text-gray-400" />
                  </div>
                  <p className="text-sm font-medium mt-2">
                    {participant.last_activity
                      ? format(new Date(participant.last_activity), 'MMM d, yyyy')
                      : 'No activity'}
                  </p>
                </div>
              </div>

              {/* Metadata */}
              <div className="text-sm text-muted-foreground space-y-1">
                <div className="flex items-center gap-2">
                  <Calendar className="w-4 h-4" />
                  <span>First seen: {format(new Date(participant.first_seen), 'MMM d, yyyy HH:mm')}</span>
                </div>
                {participant.resolved_at && (
                  <div className="flex items-center gap-2">
                    <Link2 className="w-4 h-4" />
                    <span>Linked: {format(new Date(participant.resolved_at), 'MMM d, yyyy HH:mm')}</span>
                  </div>
                )}
              </div>
            </TabsContent>

            <TabsContent value="conversations" className="mt-4">
              {loading ? (
                <div className="space-y-2">
                  {[...Array(3)].map((_, i) => (
                    <Skeleton key={i} className="h-16 w-full" />
                  ))}
                </div>
              ) : conversationSummary ? (
                <div className="space-y-4">
                  {/* Channel Summary */}
                  <div className="flex gap-2">
                    {Object.entries(conversationSummary.by_channel).map(([channel, count]) => (
                      <Badge key={channel} variant="secondary">
                        {channel}: {count}
                      </Badge>
                    ))}
                  </div>

                  {/* Recent Conversations */}
                  <div className="space-y-2">
                    <h4 className="font-medium text-sm">Recent Conversations</h4>
                    {conversationSummary.recent_conversations.map((conv) => (
                      <div key={conv.id} className="border rounded-lg p-3">
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="font-medium text-sm">
                              {conv.subject || 'No subject'}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {conv.channel} • {conv.message_count} messages
                            </p>
                          </div>
                          <span className="text-xs text-muted-foreground">
                            {format(new Date(conv.last_message_at), 'MMM d, HH:mm')}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="text-center text-muted-foreground py-8">
                  No conversations found
                </p>
              )}
            </TabsContent>

            {!participant.is_linked && (
              <TabsContent value="mapping" className="mt-4">
                <div className="space-y-4">
                  <div>
                    <p className="text-sm text-muted-foreground mb-2">
                      Select a pipeline to preview how this participant's data will map to record fields
                    </p>
                    <Select
                      value={selectedPipelineId}
                      onValueChange={setSelectedPipelineId}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select a pipeline" />
                      </SelectTrigger>
                      <SelectContent>
                        {pipelines.map((pipeline) => (
                          <SelectItem key={pipeline.id} value={pipeline.id}>
                            {pipeline.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  {mappingLoading ? (
                    <div className="space-y-2">
                      {[...Array(3)].map((_, i) => (
                        <Skeleton key={i} className="h-16 w-full" />
                      ))}
                    </div>
                  ) : selectedPipelineId && fieldMapping.length > 0 ? (
                    fieldMapping.map((mapping, idx) => (
                      <div key={idx} className="border rounded-lg p-3">
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="font-medium text-sm">{mapping.field_name}</p>
                            <p className="text-xs text-muted-foreground">
                              {mapping.participant_value} → {mapping.formatted_value}
                            </p>
                          </div>
                          <div className="flex items-center gap-2">
                            <Badge variant={mapping.is_valid ? "default" : "destructive"}>
                              {mapping.is_valid ? "Valid" : "Invalid"}
                            </Badge>
                            <Badge variant="outline" className="text-xs">
                              {mapping.source}
                            </Badge>
                          </div>
                        </div>
                      </div>
                    ))
                  ) : selectedPipelineId ? (
                    <p className="text-center text-muted-foreground py-8">
                      No field mappings available for this pipeline
                    </p>
                  ) : (
                    <p className="text-center text-muted-foreground py-8">
                      Select a pipeline to see field mapping
                    </p>
                  )}
                </div>
              </TabsContent>
            )}
          </Tabs>
        </div>
      </DialogContent>
    </Dialog>

    <Dialog open={showOverrideDialog} onOpenChange={setShowOverrideDialog}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Override Auto-Creation Settings</DialogTitle>
          <DialogDescription>
            Set specific rules for this participant that override global settings
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <Label>Never Auto-Create</Label>
              <p className="text-sm text-gray-500">
                Prevent this participant from ever being auto-created
              </p>
            </div>
            <Switch
              checked={overrideSettings.never_auto_create || false}
              onCheckedChange={(checked) => setOverrideSettings({
                ...overrideSettings,
                never_auto_create: checked,
                always_auto_create: checked ? false : overrideSettings.always_auto_create
              })}
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <Label>Always Auto-Create</Label>
              <p className="text-sm text-gray-500">
                Auto-create immediately regardless of other settings
              </p>
            </div>
            <Switch
              checked={overrideSettings.always_auto_create || false}
              onCheckedChange={(checked) => setOverrideSettings({
                ...overrideSettings,
                always_auto_create: checked,
                never_auto_create: checked ? false : overrideSettings.never_auto_create
              })}
            />
          </div>

          <div className="space-y-2">
            <Label>Override Reason</Label>
            <Textarea
              placeholder="Why are you overriding settings for this participant?"
              value={overrideSettings.override_reason || ''}
              onChange={(e) => setOverrideSettings({
                ...overrideSettings,
                override_reason: e.target.value
              })}
            />
          </div>

          <div className="flex justify-end space-x-2">
            <Button
              variant="outline"
              onClick={() => setShowOverrideDialog(false)}
            >
              Cancel
            </Button>
            <Button
              onClick={async () => {
                try {
                  // Save override settings
                  await communicationsApi.saveParticipantOverride(participant!.id, overrideSettings)
                  toast({
                    title: "Override settings saved",
                    description: "Settings have been applied to this participant",
                  })
                  setShowOverrideDialog(false)
                  onRefresh()
                } catch (error) {
                  toast({
                    title: "Failed to save override",
                    description: "Please try again",
                    variant: "destructive",
                  })
                }
              }}
            >
              Save Override
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
    </>
  )
}