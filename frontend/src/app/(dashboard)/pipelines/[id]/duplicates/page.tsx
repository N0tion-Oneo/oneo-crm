'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import { useAuth } from '@/features/auth/context'
import { Copy, Settings, AlertTriangle, Database } from 'lucide-react'
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
  const { isLoading: authLoading } = useAuth()
  const pipelineId = params.id as string
  const [pipeline, setPipeline] = useState<Pipeline | null>(null)
  const [activeTab, setActiveTab] = useState<'settings' | 'matches' | 'analytics' | 'url-extraction'>('settings')

  // Load pipeline data
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
        console.error('Failed to load pipeline:', error)
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
    <div className="p-8">
      <div className="max-w-6xl">
        {/* Tab Navigation */}
        <div className="flex gap-1 mb-6 bg-gray-100 dark:bg-gray-800 p-1 rounded-lg">
          <button
            onClick={() => setActiveTab('settings')}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all ${
              activeTab === 'settings'
                ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
            }`}
          >
            <Settings className="w-4 h-4" />
            Settings
          </button>
          <button
            onClick={() => setActiveTab('matches')}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all ${
              activeTab === 'matches'
                ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
            }`}
          >
            <AlertTriangle className="w-4 h-4" />
            Matches
          </button>
          <button
            onClick={() => setActiveTab('analytics')}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all ${
              activeTab === 'analytics'
                ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
            }`}
          >
            <Database className="w-4 h-4" />
            Analytics
          </button>
          <button
            onClick={() => setActiveTab('url-extraction')}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all ${
              activeTab === 'url-extraction'
                ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
            }`}
          >
            <Copy className="w-4 h-4" />
            URL Extraction
          </button>
        </div>

        {/* Content Area */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 min-h-[600px]">
          <div className="p-6">
            {activeTab === 'settings' && (
              <PipelineDuplicateSettings 
                pipelineId={pipelineId}
                pipeline={pipeline}
                onSettingsChange={(settings) => {
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