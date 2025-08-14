'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import { Eye, Lock, Clock, Users, Shield, AlertCircle } from 'lucide-react'
import { savedFiltersApi } from '@/lib/api'
import { PublicRecordListView } from '@/components/pipelines/record-list/PublicRecordListView'
import { RecordDetailDrawer } from '@/components/pipelines/record-detail-drawer'
import { Button } from '@/components/ui/button'
import { toast } from '@/hooks/use-toast'
import { Record } from '@/types/records'

interface SharedFilterData {
  id: string
  name: string
  description: string
  pipeline: {
    id: string
    name: string
    slug: string
  }
  filter_config: any
  view_mode: 'table' | 'kanban' | 'calendar'
  visible_fields: string[]
  sort_config: any
  access_mode: 'readonly' | 'filtered_edit'
  expires_at: string
  time_remaining_seconds: number
}

export default function SharedFilterPage() {
  const params = useParams()
  const token = params.token as string

  const [filterData, setFilterData] = useState<SharedFilterData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [accessGranted, setAccessGranted] = useState(false)
  const [accessorInfo, setAccessorInfo] = useState({
    name: '',
    email: ''
  })
  
  // Record drawer state
  const [selectedRecord, setSelectedRecord] = useState<Record | null>(null)
  const [isRecordDrawerOpen, setIsRecordDrawerOpen] = useState(false)
  const [pipelineData, setPipelineData] = useState<any>(null)
  const [drawerPipeline, setDrawerPipeline] = useState<any>(null)

  useEffect(() => {
    if (token) {
      loadSharedFilter()
    }
  }, [token])

  // Load pipeline data when access is granted
  useEffect(() => {
    if (accessGranted && token && !pipelineData) {
      loadPipelineData()
    }
  }, [accessGranted, token, pipelineData])

  // Set initial drawer pipeline when pipeline data is loaded
  useEffect(() => {
    if (pipelineData && !drawerPipeline) {
      setDrawerPipeline(pipelineData)
    }
  }, [pipelineData, drawerPipeline])

  const loadSharedFilter = async () => {
    try {
      setLoading(true)
      setError(null)
      
      console.log('🔗 Loading shared filter:', token)
      
      const response = await savedFiltersApi.public.access(token)
      console.log('📄 Shared filter data:', response.data)
      
      setFilterData(response.data)
    } catch (err: any) {
      console.error('❌ Error loading shared filter:', err)
      
      let errorMessage = 'Failed to load shared filter.'
      if (err.response?.status === 404) {
        errorMessage = 'This shared filter link is invalid or has expired.'
      } else if (err.response?.status === 410) {
        errorMessage = 'This shared filter link has been revoked or expired.'
      } else if (err.response?.data?.error) {
        errorMessage = err.response.data.error
      }
      
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const loadPipelineData = async () => {
    try {
      console.log('🔗 Loading pipeline data for drawer:', token)
      const response = await savedFiltersApi.public.getPipeline(token)
      console.log('📄 Pipeline data for drawer:', response.data)
      setPipelineData(response.data)
    } catch (err: any) {
      console.error('❌ Error loading pipeline data:', err)
    }
  }

  const grantAccess = async () => {
    if (!filterData || !accessorInfo.name || !accessorInfo.email) return

    try {
      setLoading(true)

      await savedFiltersApi.public.recordAccess(token, {
        accessor_name: accessorInfo.name,
        accessor_email: accessorInfo.email
      })

      setAccessGranted(true)
      
      toast({
        title: '✅ Access granted',
        description: 'You can now view the shared filter.',
      })

    } catch (err: any) {
      console.error('❌ Error granting access:', err)
      
      let errorMessage = 'Failed to grant access.'
      if (err.response?.data?.error) {
        errorMessage = err.response.data.error
      }
      
      toast({
        title: 'Access denied',
        description: errorMessage,
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  const formatTimeRemaining = (seconds: number) => {
    const days = Math.floor(seconds / (24 * 60 * 60))
    const hours = Math.floor((seconds % (24 * 60 * 60)) / (60 * 60))
    const minutes = Math.floor((seconds % (60 * 60)) / 60)

    if (days > 0) return `${days} day${days > 1 ? 's' : ''}`
    if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''}`
    if (minutes > 0) return `${minutes} minute${minutes > 1 ? 's' : ''}`
    return 'Less than 1 minute'
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            Loading shared filter...
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            Verifying access and loading filter configuration.
          </p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="max-w-md text-center">
          <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
            Unable to Access Filter
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mb-6">
            {error}
          </p>
          <div className="space-y-2">
            <p className="text-sm text-gray-500">
              Possible reasons:
            </p>
            <ul className="text-sm text-gray-500 space-y-1">
              <li>• The link has expired</li>
              <li>• The link has been revoked</li>
              <li>• The link is malformed</li>
              <li>• You don't have permission to access this filter</li>
            </ul>
          </div>
        </div>
      </div>
    )
  }

  if (!filterData) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
            Filter Not Found
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            The shared filter could not be loaded.
          </p>
        </div>
      </div>
    )
  }

  if (!accessGranted) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6">
          {/* Header */}
          <div className="text-center mb-6">
            <Shield className="w-12 h-12 text-blue-600 mx-auto mb-4" />
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
              Shared Filter Access
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              You've been given access to view a filtered dataset
            </p>
          </div>

          {/* Filter Info */}
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-6">
            <h3 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">
              {filterData.name}
            </h3>
            {filterData.description && (
              <p className="text-sm text-blue-700 dark:text-blue-300 mb-3">
                {filterData.description}
              </p>
            )}
            <div className="space-y-2 text-sm">
              <div className="flex items-center text-blue-700 dark:text-blue-300">
                <Users className="w-4 h-4 mr-2" />
                Pipeline: {filterData.pipeline.name}
              </div>
              <div className="flex items-center text-blue-700 dark:text-blue-300">
                <Eye className="w-4 h-4 mr-2" />
                Access: {filterData.access_mode === 'readonly' ? 'Read-only' : 'View & Edit'}
              </div>
              <div className="flex items-center text-blue-700 dark:text-blue-300">
                <Clock className="w-4 h-4 mr-2" />
                Expires in: {formatTimeRemaining(filterData.time_remaining_seconds)}
              </div>
            </div>
          </div>

          {/* Access Form */}
          <div className="space-y-4 mb-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Your Name *
              </label>
              <input
                type="text"
                required
                value={accessorInfo.name}
                onChange={(e) => setAccessorInfo(prev => ({ ...prev, name: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                placeholder="Enter your full name"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Your Email *
              </label>
              <input
                type="email"
                required
                value={accessorInfo.email}
                onChange={(e) => setAccessorInfo(prev => ({ ...prev, email: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                placeholder="Enter your email address"
              />
            </div>
          </div>

          {/* Security Notice */}
          <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-3 mb-6">
            <div className="flex items-start space-x-2">
              <Lock className="w-4 h-4 text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
              <div className="text-sm text-green-700 dark:text-green-300">
                <p className="font-medium mb-1">Secure Access</p>
                <p>This shared filter uses end-to-end encryption and access tracking for security.</p>
              </div>
            </div>
          </div>

          {/* Access Button */}
          <Button 
            onClick={grantAccess}
            disabled={loading || !accessorInfo.name || !accessorInfo.email}
            className="w-full"
          >
            {loading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Verifying access...
              </>
            ) : (
              <>
                <Shield className="w-4 h-4 mr-2" />
                Access Shared Filter
              </>
            )}
          </Button>
        </div>
      </div>
    )
  }


  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header Banner */}
      <div className="bg-blue-600 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Shield className="w-5 h-5" />
              <span className="text-sm font-medium">
                Shared Filter: {filterData.name}
              </span>
            </div>
            <div className="flex items-center space-x-4 text-sm">
              <div className="flex items-center space-x-1">
                <Lock className="w-4 h-4" />
                <span>{filterData.access_mode === 'readonly' ? 'Read-only' : 'Read & Edit'}</span>
              </div>
              <div className="flex items-center space-x-1">
                <Clock className="w-4 h-4" />
                <span>Expires in {formatTimeRemaining(filterData.time_remaining_seconds)}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* PublicRecordListView with token-based authentication */}
      <PublicRecordListView
        filterData={filterData}
        token={token}
        onEditRecord={(record, relatedPipeline) => {
          // Open record drawer for viewing (read-only or edit mode)
          setSelectedRecord(record)
          setIsRecordDrawerOpen(true)
          
          // Use related pipeline if provided, otherwise use main pipeline
          if (relatedPipeline) {
            console.log('🔗 Shared page: Using related pipeline for drawer:', relatedPipeline.name)
            setDrawerPipeline(relatedPipeline)
          } else {
            console.log('🔗 Shared page: Using main pipeline for drawer')
            setDrawerPipeline(pipelineData)
          }
        }}
        onCreateRecord={() => {
          if (filterData.access_mode === 'readonly') {
            toast({
              title: 'Read-only access',
              description: 'You can only view this data. Creating new records is not allowed.',
              variant: 'destructive',
            })
          } else {
            // Handle create for filtered_edit mode
            console.log('Create new record')
            toast({
              title: 'Create functionality',
              description: 'Record creation for shared filters will be implemented soon.',
            })
          }
        }}
      />

      {/* Record Detail Drawer */}
      {drawerPipeline && selectedRecord && (
        <RecordDetailDrawer
          record={selectedRecord}
          pipeline={drawerPipeline}
          isOpen={isRecordDrawerOpen}
          isReadOnly={filterData?.access_mode === 'readonly'}
          isShared={true}
          onClose={() => {
            setIsRecordDrawerOpen(false)
            setSelectedRecord(null)
            setDrawerPipeline(null)
          }}
          onSave={async (recordId: string, data: { [key: string]: any }) => {
            if (filterData?.access_mode === 'readonly') {
              toast({
                title: 'Read-only access',
                description: 'You can only view this data. Editing is not allowed.',
                variant: 'destructive',
              })
              return
            }
            
            // For filtered_edit mode, implement record update logic
            toast({
              title: 'Edit functionality',
              description: 'Record editing for shared filters will be implemented soon.',
            })
          }}
        />
      )}
    </div>
  )
}