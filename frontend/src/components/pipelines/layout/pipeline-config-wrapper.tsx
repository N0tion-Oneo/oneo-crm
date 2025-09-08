/**
 * ⚠️ WARNING: This component is NOT CURRENTLY USED
 * 
 * This component is orphaned code - it's not imported anywhere in the codebase.
 * The actual pipeline layout is implemented in /app/(dashboard)/pipelines/layout.tsx
 * and the configuration sidebar is in /app/(dashboard)/pipelines/[id]/layout.tsx
 * 
 * See README.md in this directory for more details.
 * 
 * TODO: Consider removing this file to avoid confusion
 */

'use client'

import { useState, useEffect } from 'react'
import { usePathname, useParams } from 'next/navigation'
import { PipelineListSidebar } from './pipeline-list-sidebar'
import { ConfigSectionsSidebar } from './config-sections-sidebar'
import { pipelinesApi } from '@/lib/api'
import { useAuth } from '@/features/auth/context'

interface PipelineConfigWrapperProps {
  children: React.ReactNode
}

export function PipelineConfigWrapper({ children }: PipelineConfigWrapperProps) {
  const pathname = usePathname()
  const params = useParams()
  const { hasPermission } = useAuth()
  const [pipelines, setPipelines] = useState<any[]>([])
  const [selectedPipeline, setSelectedPipeline] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  
  // Check permissions
  const canUpdatePipelines = hasPermission('pipelines', 'update')

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

  // For users with only read permissions, don't show the configuration wrapper at all
  if (!canUpdatePipelines) {
    return children
  }

  return (
    <div className="flex h-[calc(100vh-4rem)] bg-gray-50 dark:bg-gray-900">
      {/* Primary Sidebar - Pipeline List (only shown if user has update permission) */}
      <PipelineListSidebar
        pipelines={pipelines}
        selectedPipeline={selectedPipeline}
        onSelectPipeline={setSelectedPipeline}
        loading={loading}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
      />

      {/* Secondary Sidebar - Configuration Sections (only shown if user has update permission) */}
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