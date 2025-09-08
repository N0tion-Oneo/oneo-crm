'use client'

import { useState, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import { 
  Search, 
  Plus, 
  ChevronRight, 
  ChevronLeft,
  Database,
  Archive,
  Star,
  Filter,
  Folder,
  Lock
} from 'lucide-react'
import { useAuth } from '@/features/auth/context'
import { PermissionGuard } from '@/components/permissions/PermissionGuard'

interface Pipeline {
  id: number
  name: string
  description: string
  pipeline_type: string
  record_count: number
  is_archived?: boolean
  is_favorite?: boolean
  created_at: string
  updated_at: string
}

interface PipelineListSidebarProps {
  pipelines: Pipeline[]
  selectedPipeline: Pipeline | null
  onSelectPipeline: (pipeline: Pipeline) => void
  loading: boolean
  collapsed: boolean
  onToggleCollapse: () => void
}

const PIPELINE_TYPE_ICONS: Record<string, string> = {
  crm: '🎯',
  ats: '👥',
  cms: '📝',
  custom: '⚙️',
  contacts: '👤',
  companies: '🏢',
  deals: '💰',
  support: '🎧',
  inventory: '📦'
}

export function PipelineListSidebar({
  pipelines,
  selectedPipeline,
  onSelectPipeline,
  loading,
  collapsed,
  onToggleCollapse
}: PipelineListSidebarProps) {
  const router = useRouter()
  const { hasPermission } = useAuth()
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState<string | null>(null)
  const [showArchived, setShowArchived] = useState(false)
  
  // Check permissions
  const canCreatePipeline = hasPermission('pipelines', 'create')
  const canReadPipelines = hasPermission('pipelines', 'read')
  const canUpdatePipelines = hasPermission('pipelines', 'update')

  // Filter and group pipelines
  const { activePipelines, archivedPipelines, pipelinesByType } = useMemo(() => {
    let filtered = pipelines

    // Apply search filter
    if (searchQuery) {
      filtered = filtered.filter(p => 
        p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.description?.toLowerCase().includes(searchQuery.toLowerCase())
      )
    }

    // Apply type filter
    if (filterType) {
      filtered = filtered.filter(p => p.pipeline_type === filterType)
    }

    // Separate active and archived
    const active = filtered.filter(p => !p.is_archived)
    const archived = filtered.filter(p => p.is_archived)

    // Group by type
    const byType = active.reduce((acc, pipeline) => {
      const type = pipeline.pipeline_type || 'custom'
      if (!acc[type]) acc[type] = []
      acc[type].push(pipeline)
      return acc
    }, {} as Record<string, Pipeline[]>)

    return {
      activePipelines: active,
      archivedPipelines: archived,
      pipelinesByType: byType
    }
  }, [pipelines, searchQuery, filterType])

  const handlePipelineClick = (pipeline: Pipeline) => {
    onSelectPipeline(pipeline)
    router.push(`/pipelines/${pipeline.id}`)
  }

  const handleNewPipeline = () => {
    // This will open the template loader or creation wizard
    router.push('/pipelines?action=new')
  }

  // If user can't read pipelines, show access denied
  if (!canReadPipelines) {
    return (
      <div className="w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col">
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="text-center">
            <Lock className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-sm text-gray-500 dark:text-gray-400">
              No permission to view pipelines
            </p>
          </div>
        </div>
      </div>
    )
  }
  
  // If user has read but not update permissions, don't show this sidebar at all
  // They should only see pipelines in the main navigation
  if (!canUpdatePipelines) {
    return null
  }

  if (collapsed) {
    return (
      <div className="w-16 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col">
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <button
            onClick={onToggleCollapse}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
            title="Expand sidebar"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto p-2">
          {activePipelines.slice(0, 5).map(pipeline => (
            <button
              key={pipeline.id}
              onClick={() => handlePipelineClick(pipeline)}
              className={`w-full p-2 mb-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 ${
                selectedPipeline?.id === pipeline.id 
                  ? 'bg-blue-50 dark:bg-blue-900/20' 
                  : ''
              }`}
              title={pipeline.name}
            >
              <span className="text-lg">
                {PIPELINE_TYPE_ICONS[pipeline.pipeline_type] || '📊'}
              </span>
            </button>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-lg text-gray-900 dark:text-white">Pipelines</h2>
          <button
            onClick={onToggleCollapse}
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
            title="Collapse sidebar"
          >
            <ChevronLeft className="w-4 h-4 text-gray-500" />
          </button>
        </div>
        
        <PermissionGuard 
          category="pipelines" 
          action="create"
          fallback={
            <button
              disabled
              className="w-full px-3 py-2 bg-gray-400 text-gray-200 rounded-md text-sm font-medium flex items-center justify-center cursor-not-allowed"
              title="You don't have permission to create pipelines"
            >
              <Lock className="w-4 h-4 mr-1" />
              New Pipeline (No Permission)
            </button>
          }
        >
          <button
            onClick={handleNewPipeline}
            className="w-full px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-medium flex items-center justify-center"
          >
            <Plus className="w-4 h-4 mr-1" />
            New Pipeline
          </button>
        </PermissionGuard>
      </div>

      {/* Search */}
      <div className="p-3 border-b border-gray-200 dark:border-gray-700">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="search"
            placeholder="Search pipelines..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* Pipeline List */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="p-4">
            <div className="animate-pulse space-y-2">
              {[1, 2, 3].map(i => (
                <div key={i} className="h-10 bg-gray-200 dark:bg-gray-700 rounded"></div>
              ))}
            </div>
          </div>
        ) : (
          <>
            {/* Active Pipelines */}
            {activePipelines.length > 0 && (
              <div className="p-3">
                <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
                  Active Pipelines ({activePipelines.length})
                </div>
                {activePipelines.map(pipeline => (
                  <PipelineItem
                    key={pipeline.id}
                    pipeline={pipeline}
                    isSelected={selectedPipeline?.id === pipeline.id}
                    onClick={() => handlePipelineClick(pipeline)}
                  />
                ))}
              </div>
            )}

            {/* By Type */}
            {Object.keys(pipelinesByType).length > 1 && (
              <div className="p-3 border-t border-gray-200 dark:border-gray-700">
                <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
                  By Type
                </div>
                {Object.entries(pipelinesByType).map(([type, typePipelines]) => (
                  <div key={type} className="mb-2">
                    <button
                      onClick={() => setFilterType(filterType === type ? null : type)}
                      className={`w-full text-left px-2 py-1 rounded text-sm hover:bg-gray-50 dark:hover:bg-gray-700 ${
                        filterType === type ? 'bg-gray-100 dark:bg-gray-700' : ''
                      }`}
                    >
                      <span className="mr-2">{PIPELINE_TYPE_ICONS[type] || '📊'}</span>
                      <span className="capitalize">{type}</span>
                      <span className="text-gray-500 ml-1">({typePipelines.length})</span>
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Archived */}
            {archivedPipelines.length > 0 && (
              <div className="p-3 border-t border-gray-200 dark:border-gray-700">
                <button
                  onClick={() => setShowArchived(!showArchived)}
                  className="w-full text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2 flex items-center"
                >
                  <Archive className="w-3 h-3 mr-1" />
                  Archived ({archivedPipelines.length})
                  <ChevronRight className={`w-3 h-3 ml-auto transition-transform ${
                    showArchived ? 'rotate-90' : ''
                  }`} />
                </button>
                {showArchived && archivedPipelines.map(pipeline => (
                  <PipelineItem
                    key={pipeline.id}
                    pipeline={pipeline}
                    isSelected={selectedPipeline?.id === pipeline.id}
                    onClick={() => handlePipelineClick(pipeline)}
                    isArchived
                  />
                ))}
              </div>
            )}

            {/* Empty State */}
            {activePipelines.length === 0 && archivedPipelines.length === 0 && (
              <div className="p-4 text-center">
                <Database className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {searchQuery ? 'No pipelines found' : 'No pipelines yet'}
                </p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

interface PipelineItemProps {
  pipeline: Pipeline
  isSelected: boolean
  onClick: () => void
  isArchived?: boolean
}

function PipelineItem({ pipeline, isSelected, onClick, isArchived }: PipelineItemProps) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-3 py-2 rounded-md mb-1 transition-colors ${
        isSelected 
          ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400' 
          : 'hover:bg-gray-50 dark:hover:bg-gray-700'
      } ${isArchived ? 'opacity-60' : ''}`}
    >
      <div className="flex items-start">
        <span className="text-lg mr-2 flex-shrink-0">
          {PIPELINE_TYPE_ICONS[pipeline.pipeline_type] || '📊'}
        </span>
        <div className="flex-1 min-w-0">
          <div className="font-medium text-sm text-gray-900 dark:text-white truncate">
            {pipeline.name}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">
            {pipeline.record_count || 0} records
          </div>
        </div>
      </div>
    </button>
  )
}