'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useAuth } from '@/features/auth/context'
import { ArrowLeft, Copy, ChevronRight, Database, Settings, Plus, Search, Filter, AlertTriangle } from 'lucide-react'
import { PipelineDuplicateSettings } from '@/components/duplicates/pipeline-duplicate-settings'
import { DuplicateMatchesView } from '@/components/duplicates/duplicate-matches-view'
import { DuplicateAnalyticsView } from '@/components/duplicates/duplicate-analytics-view'
import URLExtractionManager from '@/components/duplicates/url-extraction-manager'
import { pipelinesApi } from '@/lib/api'

interface Pipeline {
  id: string
  name: string
  description: string
  access_level?: string
  fields: any[]
  stages: string[]
  record_count?: number
}

export default function DuplicateManagementPage() {
  const params = useParams()
  const router = useRouter()
  const { isLoading: authLoading } = useAuth()
  const pipelineId = params.id as string

  const [pipeline, setPipeline] = useState<Pipeline | null>(null)
  const [activeTab, setActiveTab] = useState<'settings' | 'matches' | 'analytics' | 'url-extraction'>('settings')

  // Load pipeline data for header display
  useEffect(() => {
    const loadPipeline = async () => {
      try {
        const response = await pipelinesApi.get(pipelineId)
        setPipeline({
          id: response.data.id?.toString() || pipelineId,
          name: response.data.name || 'Unknown Pipeline',
          description: response.data.description || '',
          access_level: response.data.access_level || 'internal',
          fields: response.data.fields || [],
          stages: response.data.stages || [],
          record_count: response.data.record_count || 0
        })
      } catch (error) {
        console.error('Failed to load pipeline for header:', error)
      }
    }

    if (pipelineId && !authLoading) {
      loadPipeline()
    }
  }, [pipelineId, authLoading])

  if (authLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading...</div>
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
      {/* Enhanced Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 shadow-sm">
        <div className="px-6 py-4">
          {/* Breadcrumbs */}
          <div className="flex items-center space-x-2 text-sm text-gray-500 dark:text-gray-400 mb-3">
            <button
              onClick={() => router.push('/pipelines')}
              className="hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
            >
              Pipelines
            </button>
            <ChevronRight className="w-4 h-4" />
            <button
              onClick={() => router.push(`/pipelines/${pipelineId}`)}
              className="hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
            >
              {pipeline?.name || 'Pipeline'}
            </button>
            <ChevronRight className="w-4 h-4" />
            <span className="text-gray-900 dark:text-white font-medium">Duplicate Management</span>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => router.push(`/pipelines/${pipelineId}`)}
                className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-all"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
              
              {/* Pipeline Info Card */}
              <div className="bg-gradient-to-r from-orange-50 to-red-50 dark:from-orange-900/20 dark:to-red-900/20 rounded-lg p-4 border border-orange-100 dark:border-orange-800">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-orange-500 rounded-lg">
                    <Copy className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h1 className="text-xl font-bold text-gray-900 dark:text-white flex items-center">
                      {pipeline?.name || 'Loading...'}
                      <Database className="w-5 h-5 ml-2 text-gray-500" />
                    </h1>
                    <p className="text-sm text-gray-600 dark:text-gray-300">
                      Duplicate Management • {pipeline?.record_count || 0} records to analyze
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Tab Navigation */}
            <div className="flex bg-gray-100 dark:bg-gray-700 rounded-lg p-1">
              <button
                onClick={() => setActiveTab('settings')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                  activeTab === 'settings'
                    ? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                <Settings className="w-4 h-4 mr-2 inline" />
                Settings
              </button>
              <button
                onClick={() => setActiveTab('matches')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                  activeTab === 'matches'
                    ? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                <AlertTriangle className="w-4 h-4 mr-2 inline" />
                Matches
              </button>
              <button
                onClick={() => setActiveTab('analytics')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                  activeTab === 'analytics'
                    ? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                <Database className="w-4 h-4 mr-2 inline" />
                Analytics
              </button>
              <button
                onClick={() => setActiveTab('url-extraction')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                  activeTab === 'url-extraction'
                    ? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                <Copy className="w-4 h-4 mr-2 inline" />
                URL Extraction
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-hidden p-6">
        <div className="h-full bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="p-6 h-full overflow-y-auto">
            {activeTab === 'settings' && (
              <PipelineDuplicateSettings 
                pipelineId={pipelineId}
                pipeline={pipeline}
                onSettingsChange={(settings) => {
                  // Optional: Update parent state when settings change
                  console.log('Duplicate settings updated:', settings)
                }}
              />
            )}
            {activeTab === 'matches' && (
              <DuplicateMatchesView 
                pipelineId={pipelineId}
              />
            )}
            {activeTab === 'analytics' && (
              <DuplicateAnalyticsView 
                pipelineId={pipelineId}
              />
            )}
            {activeTab === 'url-extraction' && (
              <URLExtractionManager 
                pipelineId={pipelineId}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}