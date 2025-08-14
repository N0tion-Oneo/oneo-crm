'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useAuth } from '@/features/auth/context'
import { ArrowLeft, Edit, Settings, Target, Copy } from 'lucide-react'
import { RecordListView, type Pipeline, type Record } from '@/components/pipelines/record-list-view'
import { RecordDetailDrawer } from '@/components/pipelines/record-detail-drawer'
import { pipelinesApi } from '@/lib/api'

export default function PipelineRecordsPage() {
  const params = useParams()
  const router = useRouter()
  const { isLoading: authLoading, isAuthenticated } = useAuth()
  const pipelineId = params.id as string

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
        
        // Debug: Log the original field data from backend
        console.log('Original backend field data:', response.data.fields)
        console.log('Field groups data:', fieldGroups)
        
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
            // is_required removed - use stage-specific business rules only
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
        console.error('Error details:', {
          message: error?.message,
          response: error?.response?.data,
          status: error?.response?.status,
          url: error?.config?.url
        })
        
        // Show error notification
        const errorNotification = document.createElement('div')
        errorNotification.className = 'fixed top-4 right-4 bg-red-500 text-white px-4 py-2 rounded-md shadow-lg z-50 max-w-md'
        errorNotification.innerHTML = `
          <div class="font-semibold">Failed to load pipeline</div>
          <div class="text-sm mt-1">${error?.response?.data?.detail || error?.message || 'Network error'}</div>
          <div class="text-xs mt-1">Using mock data. Status: ${error?.response?.status || 'Unknown'}</div>
        `
        document.body.appendChild(errorNotification)
        
        setTimeout(() => {
          if (document.body.contains(errorNotification)) {
            document.body.removeChild(errorNotification)
          }
        }, 8000)
        
        // No fallback - let the error state be handled properly
        console.error('Failed to load pipeline after timeout')
        setError('Failed to load pipeline data')
      }
    }

    // Only load data when we have auth and pipelineId
    if (pipelineId && !authLoading && isAuthenticated) {
      loadPipeline()
    } else if (!authLoading && !isAuthenticated) {
      // Auth complete but not authenticated - redirect to login
      router.push('/login')
    }
  }, [pipelineId, authLoading, isAuthenticated, router])


  // Handle record selection with optional related pipeline
  const handleEditRecord = (record: Record, relatedPipeline?: Pipeline) => {
    setSelectedRecord(record)
    setCreatingNewRecord(false)
    setShowRecordDrawer(true)
    
    // Set the pipeline to use in the drawer (related pipeline or main pipeline)
    if (relatedPipeline) {
      console.log('🔗 Parent: Using related pipeline for drawer:', relatedPipeline.name)
      setDrawerPipeline(relatedPipeline)
    } else {
      console.log('🔗 Parent: Using original pipeline for drawer')
      setDrawerPipeline(pipeline)
    }
  }

  // Handle new record creation
  const handleCreateRecord = () => {
    setSelectedRecord(null)
    setCreatingNewRecord(true)
    setShowRecordDrawer(true)
    setDrawerPipeline(pipeline) // Always use main pipeline for new records
  }

  // Handle record save
  const handleRecordSave = async (recordId: string, data: { [key: string]: any }) => {
    console.log(`🚨 PARENT PAGE BULK SAVE TRIGGERED:`, {
      recordId,
      dataKeys: Object.keys(data),
      dataSize: Object.keys(data).length,
      isExistingRecord: !creatingNewRecord,
      stackTrace: new Error().stack
    })
    
    try {
      let savedRecord
      if (creatingNewRecord && recordId === 'new') {
        // Create new record (only if not already created)
        const response = await pipelinesApi.createRecord(pipelineId, { data })
        savedRecord = response.data
        console.log('Created record:', savedRecord)
      } else if (creatingNewRecord && recordId !== 'new') {
        // Record was already created by the drawer, just update UI state
        console.log('Record already created with ID:', recordId, 'updating UI state only')
        savedRecord = { id: recordId, data }
      } else {
        // Update existing record
        const response = await pipelinesApi.updateRecord(pipelineId, recordId, { data })
        savedRecord = response.data
        console.log('Updated record:', savedRecord)
      }
      
      // Update local state
      if (selectedRecord) {
        setSelectedRecord({
          ...selectedRecord,
          data: data,
          updated_at: new Date().toISOString()
        })
      }
      
      // Refresh the pipeline data to update record count (for new records)
      if (creatingNewRecord) {
        const pipelineResponse = await pipelinesApi.get(pipelineId)
        const transformedPipeline: Pipeline = {
          id: pipelineResponse.data.id?.toString() || pipelineId,
          name: pipelineResponse.data.name || 'Unknown Pipeline',
          description: pipelineResponse.data.description || '',
          record_count: pipelineResponse.data.record_count || 0,
          fields: (pipelineResponse.data.fields || []).map((field: any) => ({
            id: field.id?.toString() || `field_${Date.now()}`,
            name: field.slug || field.name?.toLowerCase().replace(/\s+/g, '_'),
            label: field.name || field.slug || 'Unknown Field',
            field_type: field.field_type || 'text',
            // required removed - use stage-specific business rules only
            visible: field.is_visible_in_list !== false,
            order: field.display_order || 0,
            config: field.field_config || {},
            ai_config: field.ai_config || {} // AI field configuration
          })),
          stages: pipelineResponse.data.stages || []
        }
        setPipeline(transformedPipeline)
      }
    } catch (error) {
      console.error('Failed to save record:', error)
      throw error
    }
  }

  // Handle record delete
  const handleRecordDelete = async (recordId: string) => {
    try {
      await pipelinesApi.deleteRecord(pipelineId, recordId)
      setShowRecordDrawer(false)
      setSelectedRecord(null)
      
      // Refresh the pipeline data to update record count and list
      const response = await pipelinesApi.get(pipelineId)
      const transformedPipeline: Pipeline = {
        id: response.data.id?.toString() || pipelineId,
        name: response.data.name || 'Unknown Pipeline',
        description: response.data.description || '',
        record_count: response.data.record_count || 0,
        fields: (response.data.fields || []).map((field: any) => ({
          id: field.id?.toString() || `field_${Date.now()}`,
          name: field.slug || field.name?.toLowerCase().replace(/\s+/g, '_'),
          label: field.name || field.slug || 'Unknown Field',
          field_type: field.field_type || 'text',
          required: false, // Requirements handled by conditional rules
          visible: field.is_visible_in_list !== false,
          order: field.display_order || 0,
          config: field.field_config || {},
          ai_config: field.ai_config || {} // AI field configuration
        })),
        stages: response.data.stages || []
      }
      setPipeline(transformedPipeline)
    } catch (error) {
      console.error('Failed to delete record:', error)
      throw error
    }
  }

  // Handle pipeline edit - redirect to dedicated fields page
  const handleEditPipeline = () => {
    router.push(`/pipelines/${pipelineId}/fields`)
  }


  // Don't show page-level loading - let RecordListView handle its own loading state

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
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
        <div className="flex items-center space-x-4">
          <button
            onClick={() => router.push('/pipelines')}
            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          
          <div>
            <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
              {minimalPipeline.name}
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {minimalPipeline.record_count} records
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          
          <button
            onClick={() => router.push(`/pipelines/${pipelineId}/business-rules`)}
            className="px-3 py-1.5 text-sm bg-purple-500 text-white rounded-md hover:bg-purple-600 flex items-center"
          >
            <Target className="w-4 h-4 mr-1" />
            Business Rules
          </button>
          
          <button
            onClick={() => router.push(`/pipelines/${pipelineId}/duplicates`)}
            className="px-3 py-1.5 text-sm bg-orange-500 text-white rounded-md hover:bg-orange-600 flex items-center"
          >
            <Copy className="w-4 h-4 mr-1" />
            Duplicate Management
          </button>
          
          <button
            onClick={handleEditPipeline}
            className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center"
          >
            <Settings className="w-4 h-4 mr-1" />
            Configure Fields
          </button>
        </div>
      </div>

      {/* Record List */}
      <div className="flex-1">
        <RecordListView
          pipeline={minimalPipeline}
          onEditRecord={handleEditRecord}
          onCreateRecord={handleCreateRecord}
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
            setDrawerPipeline(null) // Clear drawer pipeline when closing
          }}
          onSave={handleRecordSave}
          onDelete={handleRecordDelete}
        />
      )}

    </div>
  )
}