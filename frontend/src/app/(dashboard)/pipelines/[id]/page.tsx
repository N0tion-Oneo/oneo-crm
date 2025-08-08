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
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedRecord, setSelectedRecord] = useState<Record | null>(null)
  const [showRecordDrawer, setShowRecordDrawer] = useState(false)
  const [creatingNewRecord, setCreatingNewRecord] = useState(false)

  // Load pipeline data
  useEffect(() => {
    const loadPipeline = async () => {
      try {
        setLoading(true)
        const response = await pipelinesApi.get(pipelineId)
        
        // Debug: Log the original field data from backend
        console.log('Original backend field data:', response.data.fields)
        
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
            // Preserve original slug for backend API calls
            original_slug: field.slug,
            business_rules: field.business_rules || {}
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
      } finally {
        setLoading(false)
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


  // Handle record selection
  const handleEditRecord = (record: Record) => {
    setSelectedRecord(record)
    setCreatingNewRecord(false)
    setShowRecordDrawer(true)
  }

  // Handle new record creation
  const handleCreateRecord = () => {
    setSelectedRecord(null)
    setCreatingNewRecord(true)
    setShowRecordDrawer(true)
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
            config: field.field_config || {}
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
          config: field.field_config || {}
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


  if (authLoading || loading) {
    return (
      <div className="h-screen flex items-center justify-content">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400">Loading pipeline...</p>
        </div>
      </div>
    )
  }

  if (!pipeline) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            Pipeline Not Found
          </h2>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            The pipeline you're looking for doesn't exist or you don't have access to it.
          </p>
          <button
            onClick={() => router.push('/pipelines')}
            className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90"
          >
            <ArrowLeft className="w-4 h-4 mr-2 inline" />
            Back to Pipelines
          </button>
        </div>
      </div>
    )
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
              {pipeline.name}
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {pipeline.record_count} records
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
          pipeline={pipeline}
          onEditRecord={handleEditRecord}
          onCreateRecord={handleCreateRecord}
        />
      </div>

      {/* Record Detail Drawer */}
      <RecordDetailDrawer
        record={selectedRecord}
        pipeline={pipeline}
        isOpen={showRecordDrawer}
        onClose={() => {
          setShowRecordDrawer(false)
          setSelectedRecord(null)
          setCreatingNewRecord(false)
        }}
        onSave={handleRecordSave}
        onDelete={handleRecordDelete}
      />

    </div>
  )
}