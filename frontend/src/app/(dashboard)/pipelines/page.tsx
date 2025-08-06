'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Search, Plus, MoreHorizontal, Database, Users, Calendar, Edit, Eye, Activity, Shield } from 'lucide-react'
import { useAuth } from '@/features/auth/context'
import { api, pipelinesApi } from '@/lib/api'
import { PermissionGuard, PermissionButton } from '@/components/permissions/PermissionGuard'
import { PipelineTemplateLoader, type PipelineTemplate } from '@/components/pipelines/pipeline-template-loader'
import { usePipelinesOverviewSubscription } from '@/hooks/use-websocket-subscription'
import { type RealtimeMessage } from '@/contexts/websocket-context'

interface Pipeline {
  id: number
  name: string
  description: string
  visibility?: string
  record_count: number
  created_at: string
  updated_at: string
  created_by: {
    first_name: string
    last_name: string
  }
}

const PipelinesAccessDenied = () => (
  <div className="flex items-center justify-center h-64">
    <div className="text-center max-w-md">
      <Shield className="w-12 h-12 text-red-500 mx-auto mb-4" />
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
        Access Denied
      </h2>
      <p className="text-gray-600 dark:text-gray-400 mb-4">
        You don't have permission to view pipelines. Please contact your administrator to request access.
      </p>
      <div className="bg-red-50 dark:bg-red-950/30 rounded-lg p-3">
        <p className="text-sm text-red-700 dark:text-red-300">
          Required permission: <code className="bg-red-100 dark:bg-red-900/50 px-1 rounded">pipelines.read</code>
        </p>
      </div>
    </div>
  </div>
)

export default function PipelinesPage() {
  const { user, isLoading: authLoading } = useAuth()
  const router = useRouter()
  const [pipelines, setPipelines] = useState<Pipeline[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  
  // New pipeline creation states
  const [showTemplateLoader, setShowTemplateLoader] = useState(false)

  // Handle real-time record updates
  const handleRealtimeMessage = useCallback((message: RealtimeMessage) => {
    console.log('📡 Pipeline overview received real-time message:', message)
    
    // Only handle record-related updates
    if (message.type === 'record_create' || message.type === 'record_update' || message.type === 'record_delete') {
      if (message.payload?.pipeline_id) {
        // Convert pipeline_id to number for comparison (backend sends strings, frontend uses numbers)
        const messagesPipelineId = parseInt(message.payload.pipeline_id)
        
        console.log('🔄 Updating pipeline record count:', {
          messageType: message.type,
          pipelineId: messagesPipelineId,
          newCount: message.payload.new_count,
          recordId: message.payload.record_id
        })
        
        setPipelines(prev => {
          const updated = prev.map(pipeline => {
            if (pipeline.id === messagesPipelineId) {
              const updatedPipeline = { 
                ...pipeline, 
                record_count: message.payload.new_count !== undefined ? message.payload.new_count : pipeline.record_count 
              }
              console.log(`✅ Updated pipeline ${pipeline.id} count: ${pipeline.record_count} → ${updatedPipeline.record_count}`)
              return updatedPipeline
            }
            return pipeline
          })
          return updated
        })
      } else {
        console.warn('❌ Real-time message missing pipeline_id:', message)
      }
    }
  }, [])

  // Real-time WebSocket connection for record updates using centralized system
  const { isConnected } = usePipelinesOverviewSubscription(
    handleRealtimeMessage,
    true // Always enabled
  )




  // Load pipelines
  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true)
        
        // Just load pipelines - backend will filter based on user permissions
        const pipelinesResponse = await pipelinesApi.list()
        const pipelinesData = pipelinesResponse.data.results || pipelinesResponse.data || []
        
        // Debug logging
        console.log('🔍 Pipelines Data Loaded (Backend Filtered):')
        console.log(`   Total Pipelines: ${pipelinesData.length}`)
        console.log('   Pipeline List:', pipelinesData.map((p: any) => ({ id: p.id, name: p.name })))
        
        setPipelines(pipelinesData)
        
      } catch (error: any) {
        console.error('Failed to load pipelines data:', error)
        console.error('Error details:', {
          message: error?.message,
          response: error?.response?.data,
          status: error?.response?.status,
          config: {
            url: error?.config?.url,
            baseURL: error?.config?.baseURL,
            headers: error?.config?.headers
          }
        })
        
        // Show error notification
        const notification = document.createElement('div')
        notification.className = 'fixed top-4 right-4 bg-red-500 text-white px-4 py-2 rounded-md shadow-lg z-50 max-w-md'
        notification.innerHTML = `
          <div class="font-semibold">Failed to load pipelines</div>
          <div class="text-sm mt-1">${error?.response?.data?.error || error?.message || 'Network error'}</div>
          <div class="text-xs mt-1">Status: ${error?.response?.status || 'Unknown'}</div>
        `
        document.body.appendChild(notification)
        
        setTimeout(() => {
          if (document.body.contains(notification)) {
            document.body.removeChild(notification)
          }
        }, 5000)
      } finally {
        setLoading(false)
      }
    }

    // Only load data when auth is ready
    if (!authLoading) {
      if (user) {
        loadData()
      } else {
        // Auth is complete but no user - redirect to login
        router.push('/login')
      }
    }
  }, [authLoading, user, router])

  // Handle template selection - create pipeline and redirect to fields page
  const handleTemplateSelected = async (template: PipelineTemplate) => {
    try {
      setShowTemplateLoader(false)
      
      // Create the pipeline first
      const pipelineData = {
        name: template.name,
        description: template.description,
        pipeline_type: template.category || 'custom',
        visibility: 'private'
      }
      
      console.log('Creating pipeline from template:', pipelineData)
      const pipelineResponse = await pipelinesApi.create(pipelineData)
      const newPipeline = pipelineResponse.data
      
      // Show success notification
      const successNotification = document.createElement('div')
      successNotification.className = 'fixed top-4 right-4 bg-green-500 text-white px-4 py-2 rounded-md shadow-lg z-50'
      successNotification.textContent = `Pipeline "${template.name}" created! Redirecting to field builder...`
      document.body.appendChild(successNotification)
      
      setTimeout(() => {
        if (document.body.contains(successNotification)) {
          document.body.removeChild(successNotification)
        }
      }, 2000)
      
      // Redirect to the fields page to configure fields
      router.push(`/pipelines/${newPipeline.id}/fields`)
      
    } catch (error: any) {
      console.error('Failed to create pipeline:', error)
      
      const errorNotification = document.createElement('div')
      errorNotification.className = 'fixed top-4 right-4 bg-red-500 text-white px-4 py-2 rounded-md shadow-lg z-50 max-w-md'
      errorNotification.innerHTML = `
        <div class="font-semibold">Failed to create pipeline</div>
        <div class="text-sm mt-1">${error?.response?.data?.error || error?.message || 'Unknown error occurred'}</div>
      `
      document.body.appendChild(errorNotification)
      
      setTimeout(() => {
        if (document.body.contains(errorNotification)) {
          document.body.removeChild(errorNotification)
        }
      }, 5000)
    }
  }


  // Handle pipeline edit - redirect to dedicated fields page
  const handleEditPipeline = (pipeline: Pipeline) => {
    router.push(`/pipelines/${pipeline.id}/fields`)
  }


  // Filter pipelines based on search only - backend handles permission filtering
  const filteredPipelines = pipelines.filter(pipeline => {
    return searchQuery === '' ||
      pipeline.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      pipeline.description.toLowerCase().includes(searchQuery.toLowerCase())
  })
  
  // Pipeline filtering completed

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString()
  }

  const getVisibilityColor = (visibility?: string) => {
    if (!visibility) return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
    
    switch (visibility.toLowerCase()) {
      case 'public':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
      case 'internal':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
      case 'private':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
    }
  }

  if (authLoading || loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-300 dark:bg-gray-600 rounded w-1/4 mb-4"></div>
          <div className="h-4 bg-gray-300 dark:bg-gray-600 rounded w-1/2 mb-8"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-48 bg-gray-300 dark:bg-gray-600 rounded-lg"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <PermissionGuard 
      category="pipelines" 
      action="read"
      fallback={<PipelinesAccessDenied />}
    >
      <div className="p-6">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                Pipelines
              </h1>
              <p className="text-gray-600 dark:text-gray-400 mt-2">
                Manage your data pipelines and workflow configurations.
              </p>
            </div>
          
          {/* Simple real-time indicator */}
          {isConnected && (
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-xs text-green-600">Live Updates</span>
            </div>
          )}
        </div>
      </div>

      {/* Actions Bar */}
      <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        {/* Search */}
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="h-4 w-4 text-gray-400" />
          </div>
          <input
            type="text"
            placeholder="Search pipelines..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="block w-full sm:w-64 pl-10 pr-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md leading-5 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-sm"
          />
        </div>

        {/* Add Pipeline Button */}
        <PermissionButton
          category="pipelines"
          action="create"
          onClick={() => setShowTemplateLoader(true)}
          className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
        >
          <Plus className="w-4 h-4 mr-2" />
          Create Pipeline
        </PermissionButton>
      </div>

      {/* Pipelines Grid */}
      {filteredPipelines.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredPipelines.map((pipeline) => (
            <div key={pipeline.id} className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:shadow-lg transition-shadow">
              {/* Card Header */}
              <div className="p-6 pb-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                      {pipeline.name}
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
                      {pipeline.description || 'No description provided.'}
                    </p>
                  </div>
                  <div className="flex items-center space-x-2">
                    <PermissionGuard category="records" action="read">
                      <Link 
                        href={`/pipelines/${pipeline.id}`}
                        className="text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 p-1"
                        title="View Records"
                      >
                        <Eye className="w-4 h-4" />
                      </Link>
                    </PermissionGuard>
                    <PermissionGuard category="pipelines" action="update">
                      <button 
                        onClick={() => handleEditPipeline(pipeline)}
                        className="text-gray-400 hover:text-green-600 dark:hover:text-green-400 p-1"
                        title="Edit Pipeline"
                      >
                        <Edit className="w-4 h-4" />
                      </button>
                    </PermissionGuard>
                    <PermissionGuard category="pipelines" action="read">
                      <button className="text-gray-400 hover:text-gray-500 dark:hover:text-gray-300 p-1">
                        <MoreHorizontal className="w-4 h-4" />
                      </button>
                    </PermissionGuard>
                  </div>
                </div>
              </div>

              {/* Card Stats */}
              <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center text-gray-500 dark:text-gray-400">
                    <Database className="w-4 h-4 mr-1" />
                    {pipeline.record_count || 0} records
                  </div>
                  <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getVisibilityColor(pipeline.visibility)}`}>
                    {pipeline.visibility || 'private'}
                  </span>
                </div>
              </div>

              {/* Card Footer */}
              <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/50 rounded-b-lg">
                <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                  <div className="flex items-center">
                    <Users className="w-3 h-3 mr-1" />
                    {pipeline.created_by ? `${pipeline.created_by.first_name} ${pipeline.created_by.last_name}` : 'Unknown'}
                  </div>
                  <div className="flex items-center">
                    <Calendar className="w-3 h-3 mr-1" />
                    {formatDate(pipeline.created_at)}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <Database className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            {searchQuery ? 'No accessible pipelines match your search' : 'No accessible pipelines'}
          </h3>
          <p className="text-gray-500 dark:text-gray-400 mb-6">
            {searchQuery 
              ? 'Try adjusting your search terms or check if you have access to more pipelines.'
              : 'You don\'t have access to any pipelines yet. Contact your administrator or create a new pipeline.'}
          </p>
          {!searchQuery && (
            <PermissionButton
              category="pipelines"
              action="create"
              onClick={() => setShowTemplateLoader(true)}
              className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary hover:bg-primary/90"
            >
              <Plus className="w-4 h-4 mr-2" />
              Create Pipeline
            </PermissionButton>
          )}
        </div>
      )}

      {/* Summary Stats */}
      {filteredPipelines.length > 0 && (
        <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
            <div className="flex items-center">
              <Database className="w-5 h-5 text-primary mr-2" />
              <div>
                <div className="text-2xl font-bold text-gray-900 dark:text-white">
                  {pipelines.length}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  Accessible Pipelines
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
            <div className="flex items-center">
              <Activity className="w-5 h-5 text-green-500 mr-2" />
              <div>
                <div className="text-2xl font-bold text-gray-900 dark:text-white">
                  {pipelines.filter(p => p.visibility === 'public').length}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  Public Accessible
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
            <div className="flex items-center">
              <Users className="w-5 h-5 text-blue-500 mr-2" />
              <div>
                <div className="text-2xl font-bold text-gray-900 dark:text-white">
                  {pipelines.reduce((sum, p) => sum + (p.record_count || 0), 0)}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  Total Records
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
            <div className="flex items-center">
              <Calendar className="w-5 h-5 text-purple-500 mr-2" />
              <div>
                <div className="text-2xl font-bold text-gray-900 dark:text-white">
                  {pipelines.filter(p => {
                    const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
                    return new Date(p.created_at) > weekAgo
                  }).length}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  Created This Week
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Template Loader Modal */}
      {showTemplateLoader && (
        <PipelineTemplateLoader
          onSelectTemplate={handleTemplateSelected}
          onCancel={() => setShowTemplateLoader(false)}
        />
      )}

      </div>
    </PermissionGuard>
  )
}