'use client'

import { useState, useEffect } from 'react'
import { usePathname, useParams } from 'next/navigation'
import { PipelineListSidebar } from './pipeline-list-sidebar'
import { ConfigSectionsSidebar } from './config-sections-sidebar'
import { pipelinesApi } from '@/lib/api'

interface PipelineConfigWrapperProps {
  children: React.ReactNode
}

export function PipelineConfigWrapper({ children }: PipelineConfigWrapperProps) {
  const pathname = usePathname()
  const params = useParams()
  const [pipelines, setPipelines] = useState<any[]>([])
  const [selectedPipeline, setSelectedPipeline] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  // Extract pipeline ID from URL
  const pipelineId = params?.id as string

  // Load pipelines list
  useEffect(() => {
    const loadPipelines = async () => {
      try {
        setLoading(true)
        const response = await pipelinesApi.list()
        const pipelinesData = response.data.results || response.data || []
        setPipelines(pipelinesData)
        
        // If there's a pipeline ID in the URL, select it
        if (pipelineId) {
          const pipeline = pipelinesData.find((p: any) => p.id.toString() === pipelineId)
          if (pipeline) {
            setSelectedPipeline(pipeline)
          }
        }
      } catch (error) {
        console.error('Failed to load pipelines:', error)
      } finally {
        setLoading(false)
      }
    }

    loadPipelines()
  }, [pipelineId])

  // Determine active section from pathname
  const getActiveSection = () => {
    const pathParts = pathname.split('/')
    if (pathParts.length > 3) {
      return pathParts[3] // e.g., 'settings', 'fields', 'analytics'
    }
    return 'overview'
  }

  // Check if we're on the main pipelines page (no specific pipeline selected)
  const isMainPage = pathname === '/pipelines'

  return (
    <div className="flex h-[calc(100vh-4rem)] bg-gray-50 dark:bg-gray-900">
      {/* Primary Sidebar - Pipeline List */}
      <PipelineListSidebar
        pipelines={pipelines}
        selectedPipeline={selectedPipeline}
        onSelectPipeline={setSelectedPipeline}
        loading={loading}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
      />

      {/* Secondary Sidebar - Configuration Sections */}
      {selectedPipeline && !isMainPage && (
        <ConfigSectionsSidebar
          pipeline={selectedPipeline}
          activeSection={getActiveSection()}
        />
      )}

      {/* Main Content Area */}
      <main className="flex-1 overflow-auto bg-white dark:bg-gray-800">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <div className="animate-pulse">
              <div className="h-8 bg-gray-300 dark:bg-gray-600 rounded w-48 mb-4"></div>
              <div className="h-4 bg-gray-300 dark:bg-gray-600 rounded w-32"></div>
            </div>
          </div>
        ) : (
          children
        )}
      </main>
    </div>
  )
}