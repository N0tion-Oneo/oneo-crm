'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useAuth } from '@/features/auth/context'
import { ArrowLeft, Edit, Settings, Target, Copy, Lock } from 'lucide-react'
import { RecordListView, type Pipeline, type Record } from '@/components/pipelines/record-list-view'
import { RecordDetailDrawer } from '@/components/pipelines/record-detail-drawer'
import { pipelinesApi } from '@/lib/api'

export default function PipelineRecordsPage() {
  const params = useParams()
  const router = useRouter()
  const { isLoading: authLoading, isAuthenticated, hasPermission } = useAuth()
  const pipelineId = params.id as string
  
  // Check permissions - users can have either 'read' or 'read_all'
  const canReadRecords = hasPermission('records', 'read') || hasPermission('records', 'read_all')
  const canCreateRecords = hasPermission('records', 'create')
  const canUpdateRecords = hasPermission('records', 'update')
  const canDeleteRecords = hasPermission('records', 'delete')

  const [pipeline, setPipeline] = useState<Pipeline | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [selectedRecord, setSelectedRecord] = useState<Record | null>(null)
  const [showRecordDrawer, setShowRecordDrawer] = useState(false)
  const [creatingNewRecord, setCreatingNewRecord] = useState(false)
  const [drawerPipeline, setDrawerPipeline] = useState<Pipeline | null>(null)

  // Load pipeline data
  useEffect(() => {
    const loadPipeline = async () => {
      try {
        
        // Load pipeline basic data
        const response = await pipelinesApi.get(pipelineId)
        
        // Load field groups data
        const fieldGroupsResponse = await pipelinesApi.getFieldGroups(pipelineId)
        const fieldGroups = (fieldGroupsResponse.data as any)?.results || (fieldGroupsResponse as any).results || fieldGroupsResponse.data || fieldGroupsResponse || []
        
        // Transform API response to match frontend interface
        const transformedPipeline: Pipeline = {
          id: response.data.id?.toString() || pipelineId,
          name: response.data.name || 'Unknown Pipeline',
          description: response.data.description || '',
          record_count: response.data.record_count || 0,
          fields: (response.data.fields || []).map((field: any) => ({
            id: field.id?.toString() || `field_${Date.now()}`,
            name: field.slug || field.name?.toLowerCase().replace(/\s+/g, '_'),
            display_name: field.name || field.display_name || field.slug || 'Unknown Field',
            field_type: field.field_type || 'text',
            is_visible_in_list: field.is_visible_in_list !== false,
            is_visible_in_detail: field.is_visible_in_detail !== false,
            is_visible_in_public_forms: field.is_visible_in_public_forms || false,
            display_order: field.display_order || 0,
            field_config: field.field_config || {},
            config: field.field_config || {}, // Legacy support
            ai_config: field.ai_config || {}, // AI field configuration
            // Preserve original slug for backend API calls
            original_slug: field.slug,
            business_rules: field.business_rules || {},
            // Field group assignment
            field_group: field.field_group?.toString() || null
          })),
          field_groups: fieldGroups.map((group: any) => ({
            id: group.id?.toString() || `group_${Date.now()}`,
            name: group.name || 'Unknown Group',
            description: group.description || '',
            color: group.color || '#3B82F6',
            icon: group.icon || 'folder',
            display_order: group.display_order || 0,
            field_count: group.field_count || 0
          })),
          stages: response.data.stages || []
        }
        
        setPipeline(transformedPipeline)
      } catch (error: any) {
        console.error('Failed to load pipeline:', error)
        setError('Failed to load pipeline data')
      }
    }

    if (pipelineId) {
      loadPipeline()
    }
  }, [pipelineId])

  const handleEditRecord = (record: Record, relatedPipeline?: Pipeline) => {
    // Only allow edit if user has update permission
    if (!canUpdateRecords) return
    
    setSelectedRecord(record)
    setDrawerPipeline(relatedPipeline || pipeline)
    setCreatingNewRecord(false)
    setShowRecordDrawer(true)
  }

  const handleCreateRecord = () => {
    // Only allow create if user has create permission
    if (!canCreateRecords) return
    
    setSelectedRecord(null)
    setDrawerPipeline(pipeline)
    setCreatingNewRecord(true)
    setShowRecordDrawer(true)
  }

  const handleRecordSave = async (updatedRecord: Record) => {
    // Record will be updated in RecordListView through real-time updates or refresh
    setShowRecordDrawer(false)
    setSelectedRecord(null)
    setCreatingNewRecord(false)
  }

  // Don't show page-level loading - let RecordListView handle its own loading state
  
  // Check if user has no access to records at all
  if (!canReadRecords) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <Lock className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            Access Denied
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            You don't have permission to view records.
          </p>
        </div>
      </div>
    )
  }

  // Create minimal pipeline object to eliminate sequential loading
  const minimalPipeline = pipeline || {
    id: pipelineId,
    name: 'Loading...',
    description: '',
    record_count: 0,
    fields: [],
    field_groups: [],
    stages: []
  }

  return (
    <div className="h-screen flex flex-col">
      {/* Main content area with RecordListView */}
      <div className="flex-1 overflow-hidden">
        <RecordListView
          pipeline={minimalPipeline}
          onEditRecord={canUpdateRecords ? handleEditRecord : undefined}
          onCreateRecord={canCreateRecords ? handleCreateRecord : undefined}
        />
      </div>

      {/* Record Detail Drawer */}
      {showRecordDrawer && drawerPipeline && (
        <RecordDetailDrawer
          record={selectedRecord}
          pipeline={drawerPipeline}
          isOpen={showRecordDrawer}
          onClose={() => {
            setShowRecordDrawer(false)
            setSelectedRecord(null)
            setCreatingNewRecord(false)
          }}
          onSave={handleRecordSave}
          isCreating={creatingNewRecord}
        />
      )}
    </div>
  )
}