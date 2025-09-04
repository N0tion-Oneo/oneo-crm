'use client'

import React, { useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import {
  Users,
  Link2,
  Unlink,
  UserPlus,
  ChevronDown,
  X,
  Loader2,
  AlertCircle
} from 'lucide-react'
import { api } from '@/lib/api'

interface Pipeline {
  id: string
  name: string
  description?: string
}

interface BulkActionsBarProps {
  selectedCount: number
  onAction: (action: string, data?: any) => Promise<void>
  onClear: () => void
}

export function BulkActionsBar({ selectedCount, onAction, onClear }: BulkActionsBarProps) {
  const [isProcessing, setIsProcessing] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [dialogType, setDialogType] = useState<'link' | 'create' | null>(null)
  const [pipelines, setPipelines] = useState<Pipeline[]>([])
  const [selectedPipeline, setSelectedPipeline] = useState('')
  const [selectedRecord, setSelectedRecord] = useState('')

  const openDialog = async (type: 'link' | 'create') => {
    setDialogType(type)
    setDialogOpen(true)
    setSelectedPipeline('')
    setSelectedRecord('')
    
    // Load pipelines
    try {
      const response = await api.get('/pipelines/')
      setPipelines(response.data.results || response.data || [])
    } catch (error) {
      console.error('Error loading pipelines:', error)
    }
  }

  const handleDialogAction = async () => {
    if (!selectedPipeline) return
    
    setIsProcessing(true)
    try {
      if (dialogType === 'create') {
        await onAction('create', { pipelineId: selectedPipeline })
      } else if (dialogType === 'link' && selectedRecord) {
        await onAction('link', { recordId: selectedRecord })
      }
      setDialogOpen(false)
    } finally {
      setIsProcessing(false)
    }
  }

  const handleUnlink = async () => {
    setIsProcessing(true)
    try {
      await onAction('unlink')
    } finally {
      setIsProcessing(false)
    }
  }

  return (
    <>
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Badge variant="default" className="bg-blue-600">
              <Users className="w-3 h-3 mr-1" />
              {selectedCount} selected
            </Badge>
            
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => openDialog('create')}
                disabled={isProcessing}
              >
                <UserPlus className="w-4 h-4 mr-2" />
                Create Records
              </Button>
              
              <Button
                size="sm"
                variant="outline"
                onClick={() => openDialog('link')}
                disabled={isProcessing}
              >
                <Link2 className="w-4 h-4 mr-2" />
                Link to Record
              </Button>
              
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button size="sm" variant="outline" disabled={isProcessing}>
                    More Actions
                    <ChevronDown className="w-4 h-4 ml-2" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuLabel>Bulk Actions</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    onClick={handleUnlink}
                    className="text-destructive"
                  >
                    <Unlink className="w-4 h-4 mr-2" />
                    Unlink from Records
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
          
          <Button
            size="sm"
            variant="ghost"
            onClick={onClear}
            disabled={isProcessing}
          >
            <X className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Bulk Action Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {dialogType === 'create' ? 'Create Records' : 'Link to Record'}
            </DialogTitle>
            <DialogDescription>
              {dialogType === 'create'
                ? `Create new records for ${selectedCount} selected participants`
                : `Link ${selectedCount} participants to an existing record`}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {/* Pipeline Selection */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Select Pipeline</label>
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

            {/* Record Selection for Link Action */}
            {dialogType === 'link' && selectedPipeline && (
              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  Record selection for bulk linking will open in a separate dialog.
                  For now, you can link participants individually.
                </AlertDescription>
              </Alert>
            )}

            {/* Warning for Create Action */}
            {dialogType === 'create' && (
              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  This will create {selectedCount} new records in the selected pipeline.
                  Each participant's data will be mapped to the appropriate fields.
                </AlertDescription>
              </Alert>
            )}
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDialogOpen(false)}
              disabled={isProcessing}
            >
              Cancel
            </Button>
            <Button
              onClick={handleDialogAction}
              disabled={!selectedPipeline || isProcessing}
            >
              {isProcessing ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Processing...
                </>
              ) : dialogType === 'create' ? (
                <>
                  <UserPlus className="w-4 h-4 mr-2" />
                  Create Records
                </>
              ) : (
                <>
                  <Link2 className="w-4 h-4 mr-2" />
                  Link to Record
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}