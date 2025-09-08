'use client'

import { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Database, Plus, Settings, Lock } from 'lucide-react'
import { PipelineTemplateLoader, type PipelineTemplate } from '@/components/pipelines/pipeline-template-loader'
import { PipelineCreationWizard, type PipelineCreationData } from '@/components/pipelines/pipeline-creation-wizard'
import { pipelinesApi } from '@/lib/api'
import { useAuth } from '@/features/auth/context'
import { PermissionButton, PermissionGuard } from '@/components/permissions/PermissionGuard'

export default function PipelinesPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { hasPermission } = useAuth()
  const [showTemplateLoader, setShowTemplateLoader] = useState(false)
  const [showCreationWizard, setShowCreationWizard] = useState(false)
  const [creationLoading, setCreationLoading] = useState(false)
  
  // Check permissions
  const canCreatePipeline = hasPermission('pipelines', 'create')
  const canReadPipelines = hasPermission('pipelines', 'read') || hasPermission('pipelines', 'read_all')
  
  // Check if we should show the new pipeline modal
  useEffect(() => {
    if (searchParams.get('action') === 'new' && canCreatePipeline) {
      setShowTemplateLoader(true)
    }
  }, [searchParams, canCreatePipeline])

  // Handle template selection - create pipeline and redirect to fields page
  const handleTemplateSelected = async (template: PipelineTemplate) => {
    // If it's a blank template, show the creation wizard instead
    if (template.id === 'blank') {
      setShowTemplateLoader(false)
      setShowCreationWizard(true)
      return
    }

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

  // Handle custom pipeline creation from wizard
  const handlePipelineCreation = async (data: PipelineCreationData) => {
    try {
      setCreationLoading(true)
      
      console.log('Creating custom pipeline:', data)
      const pipelineResponse = await pipelinesApi.create(data)
      const newPipeline = pipelineResponse.data
      
      // Show success notification
      const successNotification = document.createElement('div')
      successNotification.className = 'fixed top-4 right-4 bg-green-500 text-white px-4 py-2 rounded-md shadow-lg z-50'
      successNotification.textContent = `Pipeline "${data.name}" created! Redirecting to field builder...`
      document.body.appendChild(successNotification)
      
      setTimeout(() => {
        if (document.body.contains(successNotification)) {
          document.body.removeChild(successNotification)
        }
      }, 2000)
      
      // Close wizard and redirect to the fields page
      setShowCreationWizard(false)
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
    } finally {
      setCreationLoading(false)
    }
  }

  // Show access denied if user can't read pipelines
  if (!canReadPipelines) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50 dark:bg-gray-900">
        <div className="text-center max-w-md">
          <div className="mb-6">
            <div className="w-20 h-20 bg-red-100 dark:bg-red-900/20 rounded-full flex items-center justify-center mx-auto">
              <Lock className="w-10 h-10 text-red-600 dark:text-red-400" />
            </div>
          </div>
          
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-3">
            Access Denied
          </h1>
          
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            You don't have permission to view pipelines.
          </p>
          
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Please contact your administrator if you need access to pipeline management.
          </p>
        </div>
      </div>
    )
  }

  return (
    <>
      <div className="flex items-center justify-center h-full bg-gray-50 dark:bg-gray-900">
        <div className="text-center max-w-md">
          <div className="mb-6">
            <div className="w-20 h-20 bg-blue-100 dark:bg-blue-900/20 rounded-full flex items-center justify-center mx-auto">
              <Database className="w-10 h-10 text-blue-600 dark:text-blue-400" />
            </div>
          </div>
          
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-3">
            Pipeline Configuration Center
          </h1>
          
          <p className="text-gray-600 dark:text-gray-400 mb-8">
            Select a pipeline from the sidebar to manage its configuration{canCreatePipeline ? ', or create a new pipeline to get started' : ''}.
          </p>
          
          <div className="space-y-4">
            <PermissionGuard 
              category="pipelines" 
              action="create"
              fallback={
                <button
                  disabled
                  className="w-full px-6 py-3 bg-gray-400 text-gray-200 rounded-lg font-medium flex items-center justify-center cursor-not-allowed"
                  title="You don't have permission to create pipelines"
                >
                  <Lock className="w-5 h-5 mr-2" />
                  Create New Pipeline (No Permission)
                </button>
              }
            >
              <button
                onClick={() => setShowTemplateLoader(true)}
                className="w-full px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium flex items-center justify-center transition-colors"
              >
                <Plus className="w-5 h-5 mr-2" />
                Create New Pipeline
              </button>
            </PermissionGuard>
            
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                <Settings className="w-5 h-5 text-gray-400 mx-auto mb-1" />
                <div className="text-gray-700 dark:text-gray-300">Configure Fields</div>
              </div>
              <div className="p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                <Database className="w-5 h-5 text-gray-400 mx-auto mb-1" />
                <div className="text-gray-700 dark:text-gray-300">Manage Rules</div>
              </div>
            </div>
          </div>
          
          <div className="mt-8 text-xs text-gray-500 dark:text-gray-400">
            Use the sidebar to navigate between pipelines and access configuration options.
          </div>
        </div>
      </div>

      {/* Template Loader Modal */}
      {showTemplateLoader && (
        <PipelineTemplateLoader
          onSelectTemplate={handleTemplateSelected}
          onCancel={() => setShowTemplateLoader(false)}
        />
      )}

      {/* Pipeline Creation Wizard */}
      {showCreationWizard && (
        <PipelineCreationWizard
          onSubmit={handlePipelineCreation}
          onCancel={() => setShowCreationWizard(false)}
          loading={creationLoading}
        />
      )}
    </>
  )
}