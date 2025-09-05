'use client'

import React, { useState, useEffect } from 'react'
import { 
  Users, 
  Link2, 
  LinkIcon,
  Unlink, 
  UserPlus, 
  Search, 
  Filter,
  MoreHorizontal,
  Mail,
  Phone,
  CheckCircle,
  XCircle,
  AlertCircle,
  Shield
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useAuth } from '@/features/auth/context'
import { PermissionGuard } from '@/components/permissions/PermissionGuard'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Checkbox } from '@/components/ui/checkbox'
import { Skeleton } from '@/components/ui/skeleton'
import { useToast } from '@/hooks/use-toast'
import { communicationsApi } from '@/lib/api'
import { ParticipantDetailDialog } from './ParticipantDetailDialog'
import { CreateRecordDialog } from './CreateRecordDialog'
import { LinkRecordDialog } from './LinkRecordDialog'
import { BulkActionsBar } from './BulkActionsBar'

interface Participant {
  id: string
  name: string
  email: string
  phone: string
  linkedin_member_urn?: string
  avatar_url?: string
  contact_record?: string
  contact_record_display?: {
    id: string
    display_name: string
    pipeline_name: string
  }
  secondary_record?: string
  secondary_record_display?: {
    id: string
    display_name: string
    pipeline_name: string
  }
  is_linked: boolean
  conversation_count: number
  last_activity?: string
  channel_types: string[]
  resolution_confidence?: number
  resolution_method?: string
  first_seen?: string
  last_seen?: string
}

interface ParticipantListProps {
  className?: string
}

export function ParticipantList({ className }: ParticipantListProps) {
  const [participants, setParticipants] = useState<Participant[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterStatus, setFilterStatus] = useState<'all' | 'linked' | 'unlinked'>('all')
  const [selectedParticipants, setSelectedParticipants] = useState<string[]>([])
  
  // Dialog states
  const [selectedParticipant, setSelectedParticipant] = useState<Participant | null>(null)
  const [detailDialogOpen, setDetailDialogOpen] = useState(false)
  const [createRecordDialogOpen, setCreateRecordDialogOpen] = useState(false)
  const [linkRecordDialogOpen, setLinkRecordDialogOpen] = useState(false)
  
  const { toast } = useToast()
  const { hasPermission } = useAuth()
  
  // Permission checks
  const canViewParticipants = hasPermission('participants', 'read')
  const canCreateParticipants = hasPermission('participants', 'create')
  const canUpdateParticipants = hasPermission('participants', 'update')
  const canDeleteParticipants = hasPermission('participants', 'delete')
  const canLinkParticipants = hasPermission('participants', 'link')
  const canBatchProcess = hasPermission('participants', 'batch')

  // Load participants
  useEffect(() => {
    loadParticipants()
  }, [filterStatus])

  const loadParticipants = async () => {
    try {
      setLoading(true)
      
      // Build query params
      const params: any = {}
      if (filterStatus === 'linked') {
        params.contact_record__isnull = false
      } else if (filterStatus === 'unlinked') {
        params.contact_record__isnull = true
      }
      
      const response = await communicationsApi.getParticipants(params)
      setParticipants(response.data.results || response.data || [])
    } catch (error) {
      console.error('Error loading participants:', error)
      toast({
        title: "Failed to load participants",
        description: "Please try again later",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const handleUnlinkParticipant = async (participant: Participant) => {
    try {
      await communicationsApi.unlinkParticipant(participant.id)
      
      toast({
        title: "Participant unlinked",
        description: `${participant.name || participant.email} has been unlinked from their record`,
      })
      
      // Reload participants
      loadParticipants()
    } catch (error) {
      console.error('Error unlinking participant:', error)
      toast({
        title: "Failed to unlink participant",
        description: "Please try again",
        variant: "destructive",
      })
    }
  }

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedParticipants(participants.map(p => p.id))
    } else {
      setSelectedParticipants([])
    }
  }

  const handleSelectParticipant = (participantId: string, checked: boolean) => {
    if (checked) {
      setSelectedParticipants([...selectedParticipants, participantId])
    } else {
      setSelectedParticipants(selectedParticipants.filter(id => id !== participantId))
    }
  }

  const handleBulkAction = async (action: string, data?: any) => {
    // Handle bulk actions
    try {
      if (action === 'unlink') {
        // Unlink selected participants
        for (const id of selectedParticipants) {
          await communicationsApi.unlinkParticipant(id)
        }
        toast({
          title: "Participants unlinked",
          description: `${selectedParticipants.length} participants have been unlinked`,
        })
      } else if (action === 'link' && data?.recordId) {
        // Link selected participants to a record
        await communicationsApi.bulkLinkParticipants({
          participant_ids: selectedParticipants,
          record_id: data.recordId
        })
        toast({
          title: "Participants linked",
          description: `${selectedParticipants.length} participants have been linked to the record`,
        })
      } else if (action === 'create' && data?.pipelineId) {
        // Create records for selected participants
        const response = await communicationsApi.bulkCreateRecords({
          participant_ids: selectedParticipants,
          pipeline_id: data.pipelineId
        })
        toast({
          title: "Records created",
          description: `Created ${response.data.success_count} records`,
        })
      }
      
      // Clear selection and reload
      setSelectedParticipants([])
      loadParticipants()
    } catch (error) {
      console.error('Error performing bulk action:', error)
      toast({
        title: "Bulk action failed",
        description: "Please try again",
        variant: "destructive",
      })
    }
  }

  const filteredParticipants = participants.filter(participant => {
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      return (
        participant.name?.toLowerCase().includes(query) ||
        participant.email?.toLowerCase().includes(query) ||
        participant.phone?.includes(query)
      )
    }
    return true
  })

  const getChannelBadges = (channelTypes: string[]) => {
    const channelIcons: Record<string, string> = {
      gmail: '📧',
      outlook: '📧',
      mail: '📬',
      whatsapp: '💬',
      linkedin: '💼',
      instagram: '📷',
      messenger: '💬',
      telegram: '✈️',
      twitter: '🐦',
    }
    
    return channelTypes.map(channel => (
      <Badge key={channel} variant="outline" className="text-xs">
        {channelIcons[channel] || '📢'} {channel}
      </Badge>
    ))
  }

  // Check permissions first
  if (!canViewParticipants) {
    return (
      <div className={className}>
        <Alert>
          <Shield className="h-4 w-4" />
          <AlertDescription>
            You don't have permission to view participants. Please contact your administrator.
          </AlertDescription>
        </Alert>
      </div>
    )
  }

  if (loading) {
    return (
      <div className={className}>
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className={className}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold">Participants</h2>
          <p className="text-sm text-muted-foreground">
            Manage communication participants and their CRM record links
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Badge variant="outline">
            {participants.length} total
          </Badge>
          <Badge variant="outline" className="bg-green-50">
            {participants.filter(p => p.is_linked).length} linked
          </Badge>
          <Badge variant="outline" className="bg-yellow-50">
            {participants.filter(p => !p.is_linked).length} unlinked
          </Badge>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center space-x-4 mb-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
          <Input
            placeholder="Search by name, email, or phone..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        <Select value={filterStatus} onValueChange={(value: any) => setFilterStatus(value)}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Filter by status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Participants</SelectItem>
            <SelectItem value="linked">Linked Only</SelectItem>
            <SelectItem value="unlinked">Unlinked Only</SelectItem>
          </SelectContent>
        </Select>
        <Button variant="outline" onClick={loadParticipants}>
          <Filter className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Bulk Actions Bar - only show if user has batch permissions */}
      {selectedParticipants.length > 0 && canBatchProcess && (
        <BulkActionsBar
          selectedCount={selectedParticipants.length}
          onAction={handleBulkAction}
          onClear={() => setSelectedParticipants([])}
        />
      )}

      {/* Table */}
      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-12">
                {canBatchProcess && (
                  <Checkbox
                    checked={selectedParticipants.length === participants.length && participants.length > 0}
                    onCheckedChange={handleSelectAll}
                  />
                )}
              </TableHead>
              <TableHead>Participant</TableHead>
              <TableHead>Channels</TableHead>
              <TableHead>Conversations</TableHead>
              <TableHead>Primary Contact</TableHead>
              <TableHead>Secondary Link</TableHead>
              <TableHead>Last Activity</TableHead>
              <TableHead className="w-12"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredParticipants.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                  No participants found
                </TableCell>
              </TableRow>
            ) : (
              filteredParticipants.map((participant) => (
                <TableRow key={participant.id}>
                  <TableCell>
                    {canBatchProcess && (
                      <Checkbox
                        checked={selectedParticipants.includes(participant.id)}
                        onCheckedChange={(checked) => handleSelectParticipant(participant.id, checked as boolean)}
                      />
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center space-x-3">
                      {participant.avatar_url ? (
                        <img
                          src={participant.avatar_url}
                          alt={participant.name}
                          className="w-8 h-8 rounded-full"
                        />
                      ) : (
                        <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
                          <Users className="w-4 h-4 text-gray-500" />
                        </div>
                      )}
                      <div>
                        <div className="font-medium">{participant.name || 'Unknown'}</div>
                        <div className="text-sm text-muted-foreground space-x-2">
                          {participant.email && (
                            <span className="inline-flex items-center">
                              <Mail className="w-3 h-3 mr-1" />
                              {participant.email}
                            </span>
                          )}
                          {participant.phone && (
                            <span className="inline-flex items-center">
                              <Phone className="w-3 h-3 mr-1" />
                              {participant.phone}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {getChannelBadges(participant.channel_types)}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary">
                      {participant.conversation_count}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {participant.contact_record ? (
                      <div className="flex items-center space-x-2">
                        <CheckCircle className="w-4 h-4 text-green-500" />
                        <div>
                          <div className="text-sm font-medium">
                            {participant.contact_record_display?.display_name}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {participant.contact_record_display?.pipeline_name}
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center space-x-2">
                        <XCircle className="w-4 h-4 text-gray-400" />
                        <span className="text-sm text-muted-foreground">Not linked</span>
                      </div>
                    )}
                  </TableCell>
                  <TableCell>
                    {participant.secondary_record ? (
                      <div className="flex items-center space-x-2">
                        <Link2 className="w-4 h-4 text-blue-500" />
                        <div>
                          <div className="text-sm font-medium">
                            {participant.secondary_record_display?.display_name || 'Secondary Link'}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {participant.secondary_record_display?.pipeline_name || 'Organization'}
                          </div>
                        </div>
                      </div>
                    ) : (
                      <span className="text-sm text-muted-foreground">-</span>
                    )}
                  </TableCell>
                  <TableCell>
                    {participant.last_activity ? (
                      <span className="text-sm text-muted-foreground">
                        {new Date(participant.last_activity).toLocaleDateString()}
                      </span>
                    ) : (
                      <span className="text-sm text-muted-foreground">-</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm">
                          <MoreHorizontal className="w-4 h-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuLabel>Actions</DropdownMenuLabel>
                        <DropdownMenuItem
                          onClick={() => {
                            setSelectedParticipant(participant)
                            setDetailDialogOpen(true)
                          }}
                        >
                          View Details
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        {participant.contact_record ? (
                          canLinkParticipants && (
                            <DropdownMenuItem
                              onClick={() => handleUnlinkParticipant(participant)}
                              className="text-destructive"
                            >
                              <Unlink className="w-4 h-4 mr-2" />
                              Unlink Primary Contact
                            </DropdownMenuItem>
                          )
                        ) : (
                          <>
                            {canLinkParticipants && (
                              <DropdownMenuItem
                                onClick={() => {
                                  setSelectedParticipant(participant)
                                  setCreateRecordDialogOpen(true)
                                }}
                              >
                                <UserPlus className="w-4 h-4 mr-2" />
                                Create Record
                              </DropdownMenuItem>
                            )}
                            {canLinkParticipants && (
                              <DropdownMenuItem
                                onClick={() => {
                                  setSelectedParticipant(participant)
                                  setLinkRecordDialogOpen(true)
                                }}
                              >
                                <LinkIcon className="w-4 h-4 mr-2" />
                                Link to Record
                              </DropdownMenuItem>
                            )}
                          </>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Dialogs */}
      {selectedParticipant && (
        <>
          <ParticipantDetailDialog
            participant={selectedParticipant}
            open={detailDialogOpen}
            onOpenChange={setDetailDialogOpen}
            onRefresh={loadParticipants}
          />
          <CreateRecordDialog
            participant={selectedParticipant}
            open={createRecordDialogOpen}
            onOpenChange={setCreateRecordDialogOpen}
            onSuccess={loadParticipants}
          />
          <LinkRecordDialog
            participant={selectedParticipant}
            open={linkRecordDialogOpen}
            onOpenChange={setLinkRecordDialogOpen}
            onSuccess={loadParticipants}
          />
        </>
      )}
    </div>
  )
}