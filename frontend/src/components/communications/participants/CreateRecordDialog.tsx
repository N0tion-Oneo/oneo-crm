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
import {
  CheckCircle,
  XCircle,
  AlertCircle,
  ArrowRight,
  Loader2,
  UserPlus
} from 'lucide-react'
import { useToast } from '@/hooks/use-toast'
import { api, communicationsApi } from '@/lib/api'

interface Participant {
  id: string
  name: string
  email: string
  phone: string
  linkedin_member_urn?: string
  instagram_username?: string
  twitter_handle?: string
}

interface Pipeline {
  id: string
  name: string
  slug: string
  description?: string
}

interface FieldMapping {
  field_name: string
  field_slug: string
  field_type: string
  source: string
  participant_value: any
  formatted_value: any
  is_valid: boolean
  validation_errors: string[]
  is_required: boolean
}

interface CreateRecordDialogProps {
  participant: Participant | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
}

export function CreateRecordDialog({
  participant,
  open,
  onOpenChange,
  onSuccess
}: CreateRecordDialogProps) {
  const [pipelines, setPipelines] = useState<Pipeline[]>([])
  const [selectedPipeline, setSelectedPipeline] = useState<string>('')
  const [fieldMappings, setFieldMappings] = useState<FieldMapping[]>([])
  const [fieldOverrides, setFieldOverrides] = useState<Record<string, any>>({})
  const [loading, setLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [validationErrors, setValidationErrors] = useState<Record<string, string[]>>({})
  
  const { toast } = useToast()

  useEffect(() => {
    if (open) {
      loadPipelines()
      setSelectedPipeline('')
      setFieldMappings([])
      setFieldOverrides({})
      setValidationErrors({})
    }
  }, [open])

  useEffect(() => {
    if (selectedPipeline && participant) {
      loadFieldMapping()
    }
  }, [selectedPipeline, participant])

  const loadPipelines = async () => {
    try {
      const response = await api.get('/pipelines/')
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

  const loadFieldMapping = async () => {
    if (!participant) return
    
    setLoading(true)
    try {
      const response = await communicationsApi.getParticipantFieldMapping(
        participant.id,
        { pipeline_id: selectedPipeline }
      )
      setFieldMappings(response.data.mappings || [])
      
      // Check for validation errors
      const errors: Record<string, string[]> = {}
      response.data.mappings.forEach((mapping: FieldMapping) => {
        if (!mapping.is_valid && mapping.validation_errors.length > 0) {
          errors[mapping.field_slug] = mapping.validation_errors
        }
      })
      setValidationErrors(errors)
    } catch (error) {
      console.error('Error loading field mapping:', error)
      toast({
        title: "Failed to load field mapping",
        description: "Please try again",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const handleFieldOverride = (fieldSlug: string, value: any) => {
    setFieldOverrides(prev => ({
      ...prev,
      [fieldSlug]: value
    }))
    
    // Clear validation error for this field
    setValidationErrors(prev => {
      const newErrors = { ...prev }
      delete newErrors[fieldSlug]
      return newErrors
    })
  }

  const handleCreateRecord = async () => {
    if (!participant || !selectedPipeline) return
    
    setCreating(true)
    try {
      const response = await communicationsApi.createRecordFromParticipant(participant.id, {
        pipeline_id: selectedPipeline,
        overrides: fieldOverrides,
        link_conversations: true
      })
      
      toast({
        title: "Record created successfully",
        description: `Created record and linked ${response.data.conversations_linked || 0} conversations`,
      })
      
      onSuccess()
      onOpenChange(false)
    } catch (error: any) {
      console.error('Error creating record:', error)
      
      // Handle validation errors
      if (error.response?.data?.field_errors) {
        setValidationErrors(error.response.data.field_errors)
        toast({
          title: "Validation failed",
          description: "Please fix the highlighted fields",
          variant: "destructive",
        })
      } else {
        toast({
          title: "Failed to create record",
          description: error.response?.data?.detail || "Please try again",
          variant: "destructive",
        })
      }
    } finally {
      setCreating(false)
    }
  }

  const getSourceBadgeVariant = (source: string) => {
    if (source.startsWith('duplicate_rule')) return 'default'
    if (source === 'field_name_match') return 'secondary'
    return 'outline'
  }

  const getSourceLabel = (source: string) => {
    if (source === 'duplicate_rule_email') return 'Email (Duplicate Rule)'
    if (source === 'duplicate_rule_phone') return 'Phone (Duplicate Rule)'
    if (source === 'duplicate_rule_name') return 'Name (Duplicate Rule)'
    if (source === 'duplicate_rule_url') return 'URL (Duplicate Rule)'
    if (source === 'field_name_match') return 'Field Name Match'
    return source
  }

  const hasValidationErrors = Object.keys(validationErrors).length > 0
  const hasRequiredFields = fieldMappings.some(m => m.is_required && !m.formatted_value && !fieldOverrides[m.field_slug])

  if (!participant) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <UserPlus className="w-5 h-5" />
            Create Record from Participant
          </DialogTitle>
          <DialogDescription>
            Create a new CRM record for {participant.name || participant.email}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
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

          {/* Field Mapping Preview */}
          {selectedPipeline && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <Label>Field Mapping</Label>
                {hasValidationErrors && (
                  <Badge variant="destructive">
                    {Object.keys(validationErrors).length} validation errors
                  </Badge>
                )}
              </div>

              {loading ? (
                <div className="space-y-2">
                  {[...Array(4)].map((_, i) => (
                    <Skeleton key={i} className="h-20 w-full" />
                  ))}
                </div>
              ) : fieldMappings.length > 0 ? (
                <div className="space-y-3">
                  {fieldMappings.map((mapping) => {
                    const hasError = validationErrors[mapping.field_slug]
                    const overrideValue = fieldOverrides[mapping.field_slug]
                    const displayValue = overrideValue !== undefined ? overrideValue : mapping.formatted_value
                    
                    return (
                      <div
                        key={mapping.field_slug}
                        className={`border rounded-lg p-3 ${
                          hasError ? 'border-red-300 bg-red-50' : ''
                        }`}
                      >
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-sm">
                                {mapping.field_name}
                                {mapping.is_required && (
                                  <span className="text-red-500 ml-1">*</span>
                                )}
                              </span>
                              <Badge variant={getSourceBadgeVariant(mapping.source)} className="text-xs">
                                {getSourceLabel(mapping.source)}
                              </Badge>
                            </div>
                            {mapping.is_valid && !hasError ? (
                              <CheckCircle className="w-4 h-4 text-green-500" />
                            ) : (
                              <XCircle className="w-4 h-4 text-red-500" />
                            )}
                          </div>

                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <span>{mapping.participant_value || 'No value'}</span>
                            <ArrowRight className="w-3 h-3" />
                            <Input
                              value={displayValue || ''}
                              onChange={(e) => handleFieldOverride(mapping.field_slug, e.target.value)}
                              placeholder={`Enter ${mapping.field_name.toLowerCase()}`}
                              className="h-7 text-xs"
                            />
                          </div>

                          {hasError && (
                            <div className="text-xs text-red-600">
                              {validationErrors[mapping.field_slug].join(', ')}
                            </div>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    No fields could be automatically mapped. You can still create the record and add data later.
                  </AlertDescription>
                </Alert>
              )}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            onClick={() => onOpenChange(false)}
            variant="outline"
            disabled={creating}
          >
            Cancel
          </Button>
          <Button
            onClick={handleCreateRecord}
            disabled={!selectedPipeline || creating || hasValidationErrors || hasRequiredFields}
          >
            {creating ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Creating...
              </>
            ) : (
              <>
                <UserPlus className="w-4 h-4 mr-2" />
                Create Record
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}