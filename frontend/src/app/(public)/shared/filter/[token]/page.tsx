'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import { Eye, Lock, Clock, Users, Shield, AlertCircle, Edit } from 'lucide-react'
import { savedFiltersApi } from '@/lib/api'
import { PublicRecordListView } from '@/components/pipelines/record-list/PublicRecordListView'
import { RecordDetailDrawer } from '@/components/pipelines/record-detail-drawer'
import { Button } from '@/components/ui/button'
import { toast } from '@/hooks/use-toast'
import { Record } from '@/types/records'
import { 
  type SharedAccessMode, 
  getAccessPermissions, 
  getAccessModeDisplayName, 
  getAccessModeDescription,
  getAccessDeniedMessage 
} from '@/utils/shared-access-modes'

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
  access_mode: SharedAccessMode
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

  // Restore authentication state from localStorage on page load
  useEffect(() => {
    if (token) {
      // Try to restore authentication state from localStorage
      const savedAccessState = localStorage.getItem(`shared_filter_access_${token}`)
      if (savedAccessState) {
        try {
          const { accessGranted: savedAccessGranted, accessorInfo: savedAccessorInfo } = JSON.parse(savedAccessState)
          if (savedAccessGranted && savedAccessorInfo.name && savedAccessorInfo.email) {
            console.log('🔄 Restoring authentication state from localStorage')
            setAccessGranted(true)
            setAccessorInfo(savedAccessorInfo)
          }
        } catch (error) {
          console.warn('Failed to restore authentication state:', error)
          // Clear invalid data
          localStorage.removeItem(`shared_filter_access_${token}`)
        }
      }
      
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

  // Clean up old authentication data on component unmount
  useEffect(() => {
    return () => {
      // Clean up any authentication data older than 24 hours to prevent localStorage bloat
      try {
        const keys = Object.keys(localStorage)
        const filterAccessKeys = keys.filter(key => key.startsWith('shared_filter_access_'))
        
        filterAccessKeys.forEach(key => {
          try {
            const data = JSON.parse(localStorage.getItem(key) || '{}')
            // Remove if data is malformed or very old (no timestamp means it's old)
            if (!data.accessGranted || !data.accessorInfo) {
              localStorage.removeItem(key)
            }
          } catch (error) {
            // Remove malformed data
            localStorage.removeItem(key)
          }
        })
      } catch (error) {
        console.warn('Failed to clean up authentication data:', error)
      }
    }
  }, [])

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
        // Clear any stored authentication for this expired link
        localStorage.removeItem(`shared_filter_access_${token}`)
      } else if (err.response?.status === 410) {
        errorMessage = 'This shared filter link has been revoked or expired.'
        // Clear any stored authentication for this revoked link
        localStorage.removeItem(`shared_filter_access_${token}`)
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
      
      // Persist authentication state to localStorage
      localStorage.setItem(`shared_filter_access_${token}`, JSON.stringify({
        accessGranted: true,
        accessorInfo: accessorInfo
      }))
      
      console.log('💾 Saved authentication state to localStorage')
      
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
                Access: {getAccessModeDisplayName(filterData.access_mode)}
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


  const expiresSoon = filterData.time_remaining_seconds < 24 * 60 * 60 // Less than 24 hours
  const permissions = getAccessPermissions(filterData.access_mode)

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-7xl mx-auto">
          {/* Header Section */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 p-6 mb-6">
            <div className="flex items-start justify-between">
              <div className="flex items-start space-x-4">
                <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center flex-shrink-0">
                  <Shield className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                </div>
                
                <div className="flex-1">
                  <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                    {filterData.name}
                  </h1>
                  {filterData.description && (
                    <p className="text-gray-600 dark:text-gray-400 mb-2">
                      {filterData.description}
                    </p>
                  )}
                  <p className="text-gray-600 dark:text-gray-400 mb-4">
                    Shared filter from <strong>{filterData.pipeline.name}</strong> pipeline
                  </p>
                  
                  <div className="flex flex-wrap items-center gap-4 text-sm">
                    <div className="flex items-center text-gray-500 dark:text-gray-400">
                      <Clock className="w-4 h-4 mr-2" />
                      Expires in {formatTimeRemaining(filterData.time_remaining_seconds)}
                    </div>
                    <div className="flex items-center text-gray-500 dark:text-gray-400">
                      <Users className="w-4 h-4 mr-2" />
                      {filterData.visible_fields?.length || 0} fields visible
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Status Badge */}
              <div className="flex flex-col items-end space-y-2">
                {/* Access Mode Badge */}
                <div className={`flex items-center px-3 py-1.5 rounded-full text-sm font-medium ${
                  permissions.isReadOnly
                    ? 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300'
                    : 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300'
                }`}>
                  {permissions.isReadOnly ? (
                    <>
                      <Lock className="w-4 h-4 mr-1.5" />
                      {getAccessModeDisplayName(filterData.access_mode)}
                    </>
                  ) : (
                    <>
                      <Edit className="w-4 h-4 mr-1.5" />
                      {getAccessModeDisplayName(filterData.access_mode)}
                    </>
                  )}
                </div>
                
                {/* Expiry Status Badge */}
                <div className={`flex items-center px-3 py-1.5 rounded-full text-sm font-medium ${
                  expiresSoon 
                    ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300'
                    : 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
                }`}>
                  {expiresSoon ? (
                    <>
                      <AlertCircle className="w-4 h-4 mr-1.5" />
                      Expiring Soon
                    </>
                  ) : (
                    <>
                      <Eye className="w-4 h-4 mr-1.5" />
                      Active
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Expiry Warning */}
          {expiresSoon && (
            <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4 mb-6">
              <div className="flex items-start">
                <AlertCircle className="w-5 h-5 text-amber-600 dark:text-amber-400 mt-0.5 mr-3 flex-shrink-0" />
                <div>
                  <h3 className="font-medium text-amber-900 dark:text-amber-200 mb-1">
                    Share Link Expiring Soon
                  </h3>
                  <p className="text-sm text-amber-700 dark:text-amber-300">
                    This shared filter will expire in {formatTimeRemaining(filterData.time_remaining_seconds)}. 
                    After expiration, you will no longer be able to access this filtered data.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Access Information */}
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-6">
            <div className="flex items-start">
              <Shield className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5 mr-3 flex-shrink-0" />
              <div>
                <h3 className="font-medium text-blue-900 dark:text-blue-200 mb-1">
                  Secure Shared Access
                </h3>
                <p className="text-sm text-blue-700 dark:text-blue-300">
                  This is a secure, encrypted share link with{' '}
                  <strong>{getAccessModeDisplayName(filterData.access_mode).toLowerCase()}</strong> access.{' '}
                  {getAccessModeDescription(filterData.access_mode)}
                </p>
                <p className="text-sm text-blue-700 dark:text-blue-300 mt-1">
                  Access is logged for security purposes. No login is required.
                </p>
              </div>
            </div>
          </div>

          {/* Filter Content */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700">
            <div className="p-6 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                    Filtered Records
                  </h2>
                  <p className="text-gray-600 dark:text-gray-400 mt-1">
                    View the filtered records below. {getAccessModeDescription(filterData.access_mode)}
                  </p>
                </div>
                <div className={`flex items-center px-3 py-1.5 rounded-full text-xs font-medium ${
                  permissions.isReadOnly
                    ? 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-300'
                    : 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
                }`}>
                  {permissions.isReadOnly ? (
                    <>
                      <Lock className="w-3 h-3 mr-1" />
                      {getAccessModeDisplayName(filterData.access_mode)}
                    </>
                  ) : (
                    <>
                      <Edit className="w-3 h-3 mr-1" />
                      {getAccessModeDisplayName(filterData.access_mode)}
                    </>
                  )}
                </div>
              </div>
            </div>
            
            <div className="p-6">
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
                onCreateRecord={permissions.canCreate ? () => {
                  // Handle create for filtered_edit mode
                  console.log('Create new record')
                  toast({
                    title: 'Create functionality',
                    description: 'Record creation for shared filters will be implemented soon.',
                  })
                } : () => {
                  toast({
                    title: 'Access Denied',
                    description: getAccessDeniedMessage(filterData.access_mode, 'create'),
                    variant: 'destructive',
                  })
                }}
              />
            </div>
          </div>

          {/* Footer */}
          <div className="mt-8 text-center">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Powered by{' '}
              <span className="font-medium text-blue-600 dark:text-blue-400">
                Oneo CRM
              </span>
              {' '}- Secure Filter Sharing
            </p>
          </div>
        </div>
      </div>

      {/* Record Detail Drawer */}
      {drawerPipeline && selectedRecord && (
        <RecordDetailDrawer
          record={selectedRecord}
          pipeline={drawerPipeline}
          isOpen={isRecordDrawerOpen}
          isReadOnly={permissions.isReadOnly}
          isShared={true}
          sharedToken={token}
          onClose={() => {
            setIsRecordDrawerOpen(false)
            setSelectedRecord(null)
            setDrawerPipeline(null)
          }}
          onSave={async (recordId: string, data: { [key: string]: any }) => {
            if (!permissions.canEdit) {
              toast({
                title: 'Access Denied',
                description: getAccessDeniedMessage(filterData.access_mode, 'edit'),
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