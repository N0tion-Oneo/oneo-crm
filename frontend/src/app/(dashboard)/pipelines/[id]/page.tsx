'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useAuth } from '@/features/auth/context'
import { ArrowLeft, Edit, Settings } from 'lucide-react'
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
  const [selectedRecord, setSelectedRecord] = useState<Record | null>(null)
  const [showRecordDrawer, setShowRecordDrawer] = useState(false)
  const [creatingNewRecord, setCreatingNewRecord] = useState(false)

  // Load pipeline data
  useEffect(() => {
    const loadPipeline = async () => {
      try {
        setLoading(true)
        const response = await pipelinesApi.get(pipelineId)
        
        // Transform API response to match frontend interface
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
            required: field.is_required || false,
            visible: field.is_visible_in_list !== false,
            order: field.display_order || 0,
            config: field.field_config || {}
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
        
        // Fallback to mock data for development
        const mockPipeline: Pipeline = {
          id: pipelineId,
          name: 'Sales CRM Pipeline',
          description: 'Track sales opportunities and customer relationships',
          record_count: 45,
          fields: [
            {
              id: '1',
              name: 'company_name',
              label: 'Company Name',
              field_type: 'text',
              required: true,
              visible: true,
              order: 0,
              config: {}
            },
            {
              id: '2',
              name: 'contact_email',
              label: 'Contact Email',
              field_type: 'email',
              required: true,
              visible: true,
              order: 1,
              config: {}
            },
            {
              id: '3',
              name: 'contact_phone',
              label: 'Contact Phone',
              field_type: 'phone',
              required: false,
              visible: true,
              order: 2,
              config: {}
            },
            {
              id: '4',
              name: 'deal_size',
              label: 'Deal Size',
              field_type: 'decimal',
              required: false,
              visible: true,
              order: 3,
              config: {}
            },
            {
              id: '5',
              name: 'stage',
              label: 'Sales Stage',
              field_type: 'select',
              required: true,
              visible: true,
              order: 4,
              config: {
                options: [
                  { value: 'lead', label: 'Lead' },
                  { value: 'qualified', label: 'Qualified' },
                  { value: 'proposal', label: 'Proposal' },
                  { value: 'negotiation', label: 'Negotiation' },
                  { value: 'closed', label: 'Closed Won' },
                  { value: 'lost', label: 'Closed Lost' }
                ]
              }
            },
            {
              id: '6',
              name: 'notes',
              label: 'Notes',
              field_type: 'textarea',
              required: false,
              visible: true,
              order: 5,
              config: {}
            },
            {
              id: '7',
              name: 'next_follow_up',
              label: 'Next Follow-up',
              field_type: 'datetime',
              required: false,
              visible: true,
              order: 6,
              config: {}
            },
            {
              id: '8',
              name: 'priority',
              label: 'Priority',
              field_type: 'boolean',
              required: false,
              visible: true,
              order: 7,
              config: {}
            }
          ],
          stages: ['lead', 'qualified', 'proposal', 'negotiation', 'closed', 'lost']
        }
        
        setPipeline(mockPipeline)
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
    try {
      if (creatingNewRecord) {
        // Create new record
        const response = await pipelinesApi.createRecord(pipelineId, { data })
        console.log('Created record:', response.data)
      } else {
        // Update existing record
        const response = await pipelinesApi.updateRecord(pipelineId, recordId, { data })
        console.log('Updated record:', response.data)
      }
      
      // Update local state if needed
      if (selectedRecord) {
        setSelectedRecord({
          ...selectedRecord,
          data: data,
          updated_at: new Date().toISOString()
        })
      }
    } catch (error) {
      console.error('Failed to save record:', error)
      throw error
    }
  }

  // Handle record delete
  const handleRecordDelete = async (recordId: string) => {
    try {
      // TODO: Implement actual API call
      console.log('Deleting record:', recordId)
      setShowRecordDrawer(false)
      setSelectedRecord(null)
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
            onClick={() => router.push(`/pipelines/${pipelineId}/fields`)}
            className="px-3 py-1.5 text-sm bg-blue-500 text-white rounded-md hover:bg-blue-600 flex items-center"
          >
            <Edit className="w-4 h-4 mr-1" />
            🆕 NEW FIELD BUILDER
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
          onEditPipeline={handleEditPipeline}
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