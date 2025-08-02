'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useAuth } from '@/features/auth/context'
import { ArrowLeft, Target, ChevronRight, Database, Settings } from 'lucide-react'
import { BusinessRulesBuilder } from '@/components/pipelines/business-rules-builder'
import { pipelinesApi } from '@/lib/api'

interface Pipeline {
  id: string
  name: string
  description: string
  access_level?: string
  fields: any[]
  stages: string[]
}

export default function BusinessRulesPage() {
  const params = useParams()
  const router = useRouter()
  const { isLoading: authLoading } = useAuth()
  const pipelineId = params.id as string

  const [pipeline, setPipeline] = useState<Pipeline | null>(null)

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
          stages: response.data.stages || []
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
            <span className="text-gray-900 dark:text-white font-medium">Business Rules</span>
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
              <div className="bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 rounded-lg p-4 border border-purple-100 dark:border-purple-800">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-purple-500 rounded-lg">
                    <Target className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h1 className="text-xl font-bold text-gray-900 dark:text-white flex items-center">
                      {pipeline?.name || 'Loading...'}
                      <Settings className="w-5 h-5 ml-2 text-gray-500" />
                    </h1>
                    <p className="text-sm text-gray-600 dark:text-gray-300">
                      Business Rules • Configure field requirements and visibility
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-hidden p-6">
        <div className="h-full bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="p-6 h-full overflow-y-auto">
            <BusinessRulesBuilder 
              pipelineId={pipelineId}
              onPipelineChange={setPipeline}
            />
          </div>
        </div>
      </div>
    </div>
  )
}