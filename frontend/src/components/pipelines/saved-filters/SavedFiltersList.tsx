'use client'

import React, { useState, useEffect } from 'react'
import { 
  Filter, 
  Share2, 
  Star, 
  Eye, 
  Trash2, 
  MoreVertical, 
  Calendar,
  Clock,
  Users,
  Lock,
  Building,
  Globe,
  Settings
} from 'lucide-react'
import { savedFiltersApi } from '@/lib/api'
import { BooleanQuery } from '@/types/records'
import { ShareFilterButton } from './ShareFilterButton'
import { SharedFilterHistory } from './SharedFilterHistory'
import { PermissionGuard, PermissionButton } from '@/components/permissions/PermissionGuard'
import { useAuth } from '@/features/auth/context'

// Access level configuration
const accessLevelConfig = {
  private: {
    label: 'Private',
    icon: Lock,
    color: 'text-gray-600 bg-gray-50 border-gray-200',
    description: 'Only you can use this filter'
  },
  pipeline_users: {
    label: 'Pipeline Users',
    icon: Building,
    color: 'text-blue-600 bg-blue-50 border-blue-200',
    description: 'All users with pipeline access can use this filter'
  }
}

export interface SavedFilter {
  id: string
  name: string
  description: string
  pipeline: string
  pipeline_name: string
  created_by: {
    id: string
    email: string
    first_name: string
    last_name: string
  }
  filter_config: BooleanQuery
  view_mode: 'table' | 'kanban' | 'calendar'
  visible_fields: string[]
  sort_config: any
  access_level: 'private' | 'pipeline_users'
  is_shareable: boolean
  share_access_level: 'view_only' | 'filtered_edit' | 'comment' | 'export'
  is_default: boolean
  usage_count: number
  last_used_at: string | null
  can_share: {
    allowed: boolean
    reason: string
  }
  shareable_fields: string[]
  share_count: number
  created_at: string
  updated_at: string
}

export interface SavedFiltersListProps {
  pipeline: { id: string; name: string }
  onFilterSelect: (filter: SavedFilter) => void
  className?: string
}

export function SavedFiltersList({
  pipeline,
  onFilterSelect,
  className = ""
}: SavedFiltersListProps) {
  const [filters, setFilters] = useState<SavedFilter[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionMenuOpen, setActionMenuOpen] = useState<string | null>(null)
  const { hasPermission } = useAuth()
  
  // Helper function to get access level badge
  const getAccessLevelBadge = (accessLevel: string) => {
    const config = accessLevelConfig[accessLevel as keyof typeof accessLevelConfig]
    if (!config) return null

    const IconComponent = config.icon
    
    return (
      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border ${config.color}`}>
        <IconComponent className="w-3 h-3 mr-1" />
        {config.label}
      </span>
    )
  }

  useEffect(() => {
    loadFilters()
  }, [pipeline.id])

  const loadFilters = async () => {
    try {
      setLoading(true)
      setError(null)
      
      console.log('🔄 Loading saved filters for pipeline:', pipeline.id)
      
      const response = await savedFiltersApi.list({ 
        pipeline: pipeline.id,
        ordering: '-last_used_at,-created_at'
      })
      
      console.log('✅ Loaded saved filters:', response.data)
      
      // Debug first filter to check structure
      if (response.data.results && response.data.results.length > 0) {
        console.log('🔍 First filter structure:', JSON.stringify(response.data.results[0], null, 2))
      }
      
      setFilters(response.data.results || response.data)
    } catch (err: any) {
      console.error('❌ Error loading saved filters:', err)
      console.error('❌ Error details:', err.response?.data)
      setError(err.response?.data?.detail || err.message || 'Failed to load filters')
    } finally {
      setLoading(false)
    }
  }

  const handleFilterClick = async (filter: SavedFilter) => {
    try {
      console.log('🎯 Applying saved filter:', filter.name, filter)
      
      // Track usage
      await savedFiltersApi.useFilter(filter.id)
      
      // Apply the filter
      onFilterSelect(filter)
      
      // Refresh the list to update usage stats
      loadFilters()
    } catch (err: any) {
      console.error('❌ Error applying filter:', err)
      // Still apply the filter even if tracking fails
      onFilterSelect(filter)
    }
  }

  const handleSetDefault = async (filter: SavedFilter) => {
    try {
      await savedFiltersApi.setDefault(filter.id)
      loadFilters() // Refresh to update default status
      setActionMenuOpen(null)
    } catch (err: any) {
      console.error('❌ Error setting default filter:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to set default')
    }
  }

  const handleDeleteFilter = async (filter: SavedFilter) => {
    if (!confirm(`Are you sure you want to delete the filter "${filter.name}"?`)) {
      return
    }

    try {
      await savedFiltersApi.delete(filter.id)
      loadFilters() // Refresh the list
      setActionMenuOpen(null)
    } catch (err: any) {
      console.error('❌ Error deleting filter:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to delete filter')
    }
  }

  // Removed handleShareFilter - now handled by ShareFilterButton component

  const formatLastUsed = (lastUsedAt: string | null) => {
    if (!lastUsedAt) return 'Never used'
    
    const date = new Date(lastUsedAt)
    const now = new Date()
    const diffInHours = (now.getTime() - date.getTime()) / (1000 * 60 * 60)
    
    if (diffInHours < 1) return 'Just now'
    if (diffInHours < 24) return `${Math.floor(diffInHours)}h ago`
    if (diffInHours < 48) return 'Yesterday'
    return date.toLocaleDateString()
  }

  const getViewModeIcon = (viewMode: string) => {
    switch (viewMode) {
      case 'kanban':
        return '📋'
      case 'calendar':
        return '📅'
      default:
        return '📊'
    }
  }

  if (loading) {
    return (
      <div className={`p-4 ${className}`}>
        <div className="animate-pulse space-y-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-16 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={`p-4 ${className}`}>
        <div className="text-center text-red-600 dark:text-red-400">
          <p>{error}</p>
          <button 
            onClick={loadFilters}
            className="mt-2 text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400"
          >
            Try again
          </button>
        </div>
      </div>
    )
  }

  if (filters.length === 0) {
    return (
      <div className={`p-6 text-center ${className}`}>
        <Filter className="w-12 h-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
          No saved filters
        </h3>
        <p className="text-gray-500 dark:text-gray-400">
          Create your first saved filter to quickly access common filter combinations.
        </p>
      </div>
    )
  }

  return (
    <div className={`${className}`}>
      {/* Header with global actions */}
      <div className="flex items-center justify-between mb-4 pb-2 border-b border-gray-200 dark:border-gray-700">
        <h3 className="text-sm font-medium text-gray-900 dark:text-white">
          Saved Filters ({filters.length})
        </h3>
        <SharedFilterHistory className="text-xs" />
      </div>
      
      <div className="space-y-2">
        {filters.map(filter => (
          <div
            key={filter.id}
            className="group relative bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors"
          >
            {/* Main Filter Content */}
            <div 
              className="cursor-pointer"
              onClick={() => handleFilterClick(filter)}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center flex-wrap gap-2 mb-1">
                    <h4 className="text-sm font-medium text-gray-900 dark:text-white truncate">
                      {filter.name}
                    </h4>
                    {getAccessLevelBadge(filter.access_level)}
                    {filter.is_default && (
                      <Star className="w-4 h-4 text-yellow-500" />
                    )}
                    {filter.is_shareable && (
                      <Share2 className="w-4 h-4 text-orange-500" />
                    )}
                    <span className="text-sm" title={`${filter.view_mode} view`}>
                      {getViewModeIcon(filter.view_mode)}
                    </span>
                  </div>
                  
                  {filter.description && (
                    <p className="text-xs text-gray-600 dark:text-gray-400 mb-2 line-clamp-2">
                      {filter.description}
                    </p>
                  )}
                  
                  <div className="flex items-center space-x-4 text-xs text-gray-500 dark:text-gray-400">
                    <div className="flex items-center space-x-1">
                      <Eye className="w-3 h-3" />
                      <span>{filter.usage_count} uses</span>
                    </div>
                    <div className="flex items-center space-x-1">
                      <Clock className="w-3 h-3" />
                      <span>{formatLastUsed(filter.last_used_at)}</span>
                    </div>
                    {filter.share_count > 0 && (
                      <div className="flex items-center space-x-1">
                        <Users className="w-3 h-3" />
                        <span>{filter.share_count} shares</span>
                      </div>
                    )}
                    <div className="flex items-center space-x-1">
                      <span>{(filter.visible_fields || []).length} fields</span>
                    </div>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex items-center space-x-2">
                  {/* Share Button */}
                  <PermissionGuard 
                    category="sharing" 
                    action="create_shared_views"
                    fallback={
                      <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                        <span className="text-xs text-gray-400 px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded" title="You don't have permission to share filters">
                          No permission
                        </span>
                      </div>
                    }
                  >
                    {filter.can_share?.allowed ? (
                      <div 
                        onClick={(e) => e.stopPropagation()}
                      >
                        <ShareFilterButton
                          filter={filter}
                          variant="ghost"
                          size="sm"
                        />
                      </div>
                    ) : (
                      <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                        <span className="text-xs text-gray-400 px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded" title={`Cannot share: ${filter.can_share?.reason || 'Unknown reason'}`}>
                          No share
                        </span>
                      </div>
                    )}
                  </PermissionGuard>

                  {/* Action Menu */}
                  <div className="relative">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        setActionMenuOpen(actionMenuOpen === filter.id ? null : filter.id)
                      }}
                      className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-opacity"
                    >
                      <MoreVertical className="w-4 h-4" />
                    </button>

                  {actionMenuOpen === filter.id && (
                    <div className="absolute right-0 top-8 w-48 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md shadow-lg z-10">
                      <div className="py-1">
                        {!filter.is_default && (
                          <button
                            onClick={() => handleSetDefault(filter)}
                            className="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center space-x-2"
                          >
                            <Star className="w-4 h-4" />
                            <span>Set as default</span>
                          </button>
                        )}
                        
                        {/* Share functionality moved to ShareFilterButton component */}
                        
                        {/* Share History Button */}
                        {filter.share_count > 0 && (
                          <div 
                            onClick={(e) => e.stopPropagation()}
                            className="px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-700"
                          >
                            <SharedFilterHistory 
                              filterKey={filter.id}
                              className="w-full justify-start text-sm font-normal text-gray-700 dark:text-gray-300"
                            />
                          </div>
                        )}
                        
                        <PermissionGuard 
                          category="filters" 
                          action="delete_filters"
                          fallback={
                            <div className="w-full text-left px-4 py-2 text-sm text-gray-400 flex items-center space-x-2">
                              <Trash2 className="w-4 h-4" />
                              <span>Delete (No permission)</span>
                            </div>
                          }
                        >
                          <button
                            onClick={() => handleDeleteFilter(filter)}
                            className="w-full text-left px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center space-x-2"
                          >
                            <Trash2 className="w-4 h-4" />
                            <span>Delete</span>
                          </button>
                        </PermissionGuard>
                      </div>
                    </div>
                  )}
                  </div>
                </div>
              </div>
            </div>

            {/* Click outside to close menu */}
            {actionMenuOpen === filter.id && (
              <div 
                className="fixed inset-0 z-0" 
                onClick={() => setActionMenuOpen(null)}
              />
            )}
          </div>
        ))}
      </div>
    </div>
  )
}