'use client'

import React, { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Checkbox } from '@/components/ui/checkbox'
import {
  LinkIcon,
  Search,
  Loader2,
  User,
  AlertCircle,
  Building2,
  Users
} from 'lucide-react'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { useToast } from '@/hooks/use-toast'
import { api, communicationsApi } from '@/lib/api'

interface Participant {
  id: string
  name: string
  email: string
  phone: string
}

interface Pipeline {
  id: string
  name: string
  slug: string
  description?: string
}

interface PipelineRecord {
  id: string
  display_name: string
  pipeline_id: string
  pipeline_name: string
  data: Record<string, any>
  created_at: string
}

interface LinkRecordDialogProps {
  participant: Participant | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
}

export function LinkRecordDialog({
  participant,
  open,
  onOpenChange,
  onSuccess
}: LinkRecordDialogProps) {
  const [pipelines, setPipelines] = useState<Pipeline[]>([])
  const [selectedPipeline, setSelectedPipeline] = useState<string>('')
  const [searchQuery, setSearchQuery] = useState('')
  const [records, setRecords] = useState<PipelineRecord[]>([])
  const [selectedRecord, setSelectedRecord] = useState<string>('')
  const [linkType, setLinkType] = useState<'primary' | 'secondary'>('primary')
  const [linkConversations, setLinkConversations] = useState(true)
  const [loading, setLoading] = useState(false)
  const [linking, setLinking] = useState(false)
  
  const { toast } = useToast()

  useEffect(() => {
    if (open) {
      loadPipelines()
      setSelectedPipeline('')
      setSearchQuery('')
      setRecords([])
      setSelectedRecord('')
      setLinkType('primary')
      setLinkConversations(true)
    }
  }, [open])

  useEffect(() => {
    if (selectedPipeline) {
      searchRecords()
    }
  }, [selectedPipeline, searchQuery])

  const loadPipelines = async () => {
    try {
      const response = await api.get('/api/v1/pipelines/')
      setPipelines(response.data.results || response.data || [])
    } catch (error) {
      console.error('Error loading pipelines:', error)
      toast({
        title: "Failed to load pipelines",
        description: "Please try again",
        variant: "destructive",
      })
    }
  }

  const searchRecords = async () => {
    if (!selectedPipeline) return
    
    setLoading(true)
    try {
      const params: any = {
        page_size: 20
      }
      
      if (searchQuery) {
        params.search = searchQuery
      }
      
      const response = await api.get(`/api/v1/pipelines/${selectedPipeline}/records/`, { params })
      setRecords(response.data.results || response.data || [])
    } catch (error) {
      console.error('Error searching records:', error)
      toast({
        title: "Failed to search records",
        description: "Please try again",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const handleLinkRecord = async () => {
    if (!participant || !selectedRecord) return
    
    setLinking(true)
    try {
      const response = await communicationsApi.linkParticipantToRecord(participant.id, {
        record_id: selectedRecord,
        link_type: linkType,
        link_conversations: linkConversations
      })
      
      toast({
        title: "Record linked successfully",
        description: linkConversations 
          ? `Linked and associated ${response.data.conversations_linked || 0} conversations`
          : "Successfully linked participant to record",
      })
      
      onSuccess()
      onOpenChange(false)
    } catch (error: any) {
      console.error('Error linking record:', error)
      toast({
        title: "Failed to link record",
        description: error.response?.data?.detail || "Please try again",
        variant: "destructive",
      })
    } finally {
      setLinking(false)
    }
  }

  const getRecordDisplayValue = (record: PipelineRecord) => {
    // Try to get a meaningful display value from the record data
    const possibleFields = ['name', 'title', 'email', 'company', 'full_name']
    for (const field of possibleFields) {
      if (record.data[field]) {
        return record.data[field]
      }
    }
    return record.display_name || `Record ${record.id}`
  }

  const getRecordSubtitle = (record: PipelineRecord) => {
    // Try to get secondary information
    const fields = []
    
    if (record.data.email && record.data.email !== getRecordDisplayValue(record)) {
      fields.push(record.data.email)
    }
    if (record.data.phone) {
      fields.push(record.data.phone)
    }
    if (record.data.company && record.data.company !== getRecordDisplayValue(record)) {
      fields.push(record.data.company)
    }
    
    return fields.join(' • ')
  }

  if (!participant) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <LinkIcon className="w-5 h-5" />
            Link to Existing Record
          </DialogTitle>
          <DialogDescription>
            Link {participant.name || participant.email} to an existing CRM record
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Link Type Selection */}
          <div className="space-y-2">
            <Label>Link Type</Label>
            <RadioGroup value={linkType} onValueChange={(value) => setLinkType(value as 'primary' | 'secondary')}>
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="primary" id="primary" />
                  <Label htmlFor="primary" className="flex items-center cursor-pointer">
                    <Users className="w-4 h-4 mr-2" />
                    Primary Contact
                    <span className="text-xs text-muted-foreground ml-2">(Individual)</span>
                  </Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="secondary" id="secondary" />
                  <Label htmlFor="secondary" className="flex items-center cursor-pointer">
                    <Building2 className="w-4 h-4 mr-2" />
                    Secondary Link
                    <span className="text-xs text-muted-foreground ml-2">(Organization/Company)</span>
                  </Label>
                </div>
              </div>
            </RadioGroup>
          </div>

          {/* Pipeline Selection */}
          <div className="space-y-2">
            <Label>Select Pipeline</Label>
            <Select value={selectedPipeline} onValueChange={setSelectedPipeline}>
              <SelectTrigger>
                <SelectValue placeholder="Choose a pipeline..." />
              </SelectTrigger>
              <SelectContent>
                {pipelines.map((pipeline) => (
                  <SelectItem key={pipeline.id} value={pipeline.id}>
                    <div>
                      <div className="font-medium">{pipeline.name}</div>
                      {pipeline.description && (
                        <div className="text-xs text-muted-foreground">
                          {pipeline.description}
                        </div>
                      )}
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Search Records */}
          {selectedPipeline && (
            <>
              <div className="space-y-2">
                <Label>Search Records</Label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <Input
                    placeholder="Search by name, email, or other fields..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10"
                  />
                </div>
              </div>

              {/* Record List */}
              <div className="space-y-2">
                <Label>Select Record</Label>
                {loading ? (
                  <div className="space-y-2">
                    {[...Array(3)].map((_, i) => (
                      <Skeleton key={i} className="h-16 w-full" />
                    ))}
                  </div>
                ) : records.length > 0 ? (
                  <div className="border rounded-lg max-h-64 overflow-y-auto">
                    {records.map((record) => (
                      <div
                        key={record.id}
                        onClick={() => setSelectedRecord(record.id)}
                        className={`p-3 border-b last:border-b-0 cursor-pointer hover:bg-gray-50 transition-colors ${
                          selectedRecord === record.id ? 'bg-blue-50 border-blue-200' : ''
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-3">
                            <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
                              <User className="w-4 h-4 text-gray-500" />
                            </div>
                            <div>
                              <div className="font-medium text-sm">
                                {getRecordDisplayValue(record)}
                              </div>
                              {getRecordSubtitle(record) && (
                                <div className="text-xs text-muted-foreground">
                                  {getRecordSubtitle(record)}
                                </div>
                              )}
                            </div>
                          </div>
                          {selectedRecord === record.id && (
                            <Badge variant="default">Selected</Badge>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <Alert>
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      {searchQuery 
                        ? "No records found matching your search"
                        : "No records found in this pipeline"}
                    </AlertDescription>
                  </Alert>
                )}
              </div>

              {/* Link Conversations Option */}
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="link-conversations"
                  checked={linkConversations}
                  onCheckedChange={(checked) => setLinkConversations(checked as boolean)}
                />
                <Label
                  htmlFor="link-conversations"
                  className="text-sm font-normal cursor-pointer"
                >
                  Also link all conversations from this participant to the record
                </Label>
              </div>
            </>
          )}
        </div>

        <DialogFooter>
          <Button
            onClick={() => onOpenChange(false)}
            variant="outline"
            disabled={linking}
          >
            Cancel
          </Button>
          <Button
            onClick={handleLinkRecord}
            disabled={!selectedRecord || linking}
          >
            {linking ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Linking...
              </>
            ) : (
              <>
                <LinkIcon className="w-4 h-4 mr-2" />
                Link Record
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}