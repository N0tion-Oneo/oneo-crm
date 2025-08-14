'use client'

import React, { useState, useEffect, useRef } from 'react'
import { 
  X, 
  Search, 
  Filter,
  Star,
  Trash2,
  Eye,
  Clock,
  Users,
  ArrowUpDown,
  RefreshCw,
  Lock,
  Building,
  Globe
} from 'lucide-react'
import { savedFiltersApi } from '@/lib/api'
import { SavedFilter } from './SavedFiltersList'
import { ShareFilterButton } from './ShareFilterButton'
import { SharedFilterHistory } from './SharedFilterHistory'

// Access level configuration
const accessLevelConfig = {
  private: { 
    label: 'Private', 
    icon: Lock, 
    color: 'text-gray-600', 
    bgColor: 'bg-gray-50', 
    borderColor: 'border-gray-200',
    description: 'Only you can use this filter'
  },
  pipeline_users: { 
    label: 'Pipeline Users', 
    icon: Building, 
    color: 'text-blue-600', 
    bgColor: 'bg-blue-50', 
    borderColor: 'border-blue-200',
    description: 'All users with pipeline access can use this filter'
  }
}

interface SavedFiltersModalProps {
  isOpen: boolean
  onClose: () => void
  pipeline: { id: string; name: string }
  onFilterSelect: (filter: SavedFilter) => void
  className?: string
}

type SortField = 'name' | 'created_at' | 'last_used_at' | 'usage_count'
type SortDirection = 'asc' | 'desc'

export function SavedFiltersModal({
  isOpen,
  onClose,
  pipeline,
  onFilterSelect,
  className = ""
}: SavedFiltersModalProps) {
  // Data state
  const [filters, setFilters] = useState<SavedFilter[]>([])
  const [filteredFilters, setFilteredFilters] = useState<SavedFilter[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // UI state
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedAccessLevels, setSelectedAccessLevels] = useState<string[]>(['private', 'pipeline_users'])
  const [sortField, setSortField] = useState<SortField>('last_used_at')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')
  const [updatingFilters, setUpdatingFilters] = useState<Set<string>>(new Set())
  
  // Ref to track if component is mounted
  const isMountedRef = useRef(true)

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      isMountedRef.current = false
    }
  }, [])

  // Load filters when modal opens
  useEffect(() => {
    if (isOpen) {
      isMountedRef.current = true
      loadFilters()
    }
  }, [isOpen, pipeline.id])

  // Filter and sort filters when criteria change
  useEffect(() => {
    let result = [...filters]

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      result = result.filter(filter =>
        filter.name.toLowerCase().includes(query) ||
        filter.description.toLowerCase().includes(query) ||
        filter.created_by.email.toLowerCase().includes(query)
      )
    }

    // Apply access level filter
    result = result.filter(filter =>
      selectedAccessLevels.includes(filter.access_level)
    )

    // Apply sorting
    result.sort((a, b) => {
      let aVal: any, bVal: any

      switch (sortField) {
        case 'name':
          aVal = a.name.toLowerCase()
          bVal = b.name.toLowerCase()
          break
        case 'created_at':
          aVal = new Date(a.created_at)
          bVal = new Date(b.created_at)
          break
        case 'last_used_at':
          aVal = a.last_used_at ? new Date(a.last_used_at) : new Date(0)
          bVal = b.last_used_at ? new Date(b.last_used_at) : new Date(0)
          break
        case 'usage_count':
          aVal = a.usage_count
          bVal = b.usage_count
          break
        default:
          aVal = a[sortField]
          bVal = b[sortField]
      }

      if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1
      if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1
      return 0
    })

    setFilteredFilters(result)
  }, [filters, searchQuery, selectedAccessLevels, sortField, sortDirection])

  const loadFilters = async () => {
    if (!isMountedRef.current) return
    
    try {
      setLoading(true)
      setError(null)
      
      const response = await savedFiltersApi.list({
        pipeline: pipeline.id,
        ordering: '-last_used_at,-created_at'
      })
      
      if (isMountedRef.current) {
        setFilters(response.data.results || response.data)
      }
    } catch (err: any) {
      console.error('Failed to load saved filters:', err)
      if (isMountedRef.current) {
        setError(err.response?.data?.detail || err.message || 'Failed to load filters')
      }
    } finally {
      if (isMountedRef.current) {
        setLoading(false)
      }
    }
  }


  const handleFilterSelect = async (filter: SavedFilter) => {
    try {
      // Track usage
      await savedFiltersApi.useFilter(filter.id)
      
      // Apply filter
      onFilterSelect(filter)
      onClose()
      
      // Refresh the list to update usage stats
      loadFilters()
    } catch (error) {
      console.error('Failed to apply filter:', error)
      // Still apply the filter even if tracking fails
      onFilterSelect(filter)
      onClose()
    }
  }

  const handleDeleteFilter = async (filter: SavedFilter, event?: React.MouseEvent) => {
    if (event) {
      event.stopPropagation() // Prevent filter selection when clicking delete button
    }
    
    if (!confirm(`Are you sure you want to delete "${filter.name}"?`)) {
      return
    }

    // Set loading state to prevent multiple deletions
    if (!isMountedRef.current) return
    setLoading(true)
    setError(null)

    try {
      await savedFiltersApi.delete(filter.id)
      
      // Update local state only if component is still mounted
      if (isMountedRef.current) {
        setFilters(prev => {
          const updated = prev.filter(f => f.id !== filter.id)
          console.log(`✅ Successfully deleted filter "${filter.name}". Remaining filters:`, updated.length)
          return updated
        })
      }
      
    } catch (error: any) {
      console.error('Failed to delete filter:', error)
      if (isMountedRef.current) {
        setError(error.response?.data?.detail || error.message || 'Failed to delete filter')
      }
    } finally {
      if (isMountedRef.current) {
        setLoading(false)
      }
    }
  }

  const handleToggleAccessLevel = async (filter: SavedFilter, event: React.MouseEvent) => {
    event.stopPropagation() // Prevent filter selection
    
    const newAccessLevel = filter.access_level === 'private' ? 'pipeline_users' : 'private'
    
    // Add to updating set
    setUpdatingFilters(prev => new Set(prev).add(filter.id))
    
    try {
      const updatePayload = {
        ...filter,
        access_level: newAccessLevel,
        // Keep other fields as they are
        pipeline: filter.pipeline,
        filter_config: filter.filter_config,
        view_mode: filter.view_mode,
        visible_fields: filter.visible_fields,
        sort_config: filter.sort_config,
        is_shareable: true // Both levels can be shared
      }

      await savedFiltersApi.update(filter.id, updatePayload)
      
      // Update local state
      setFilters(prev => prev.map(f => 
        f.id === filter.id 
          ? { ...f, access_level: newAccessLevel }
          : f
      ))
      
      console.log(`✅ Updated filter "${filter.name}" access level to ${newAccessLevel}`)
    } catch (error) {
      console.error('Failed to update filter access level:', error)
      setError('Failed to update filter access level')
    } finally {
      // Remove from updating set
      setUpdatingFilters(prev => {
        const newSet = new Set(prev)
        newSet.delete(filter.id)
        return newSet
      })
    }
  }

  const handleSetDefault = async (filter: SavedFilter) => {
    try {
      await savedFiltersApi.setDefault(filter.id)
      loadFilters() // Refresh to update default status
    } catch (error) {
      console.error('Failed to set default filter:', error)
      setError('Failed to set default filter')
    }
  }


  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('desc')
    }
  }

  const getAccessLevelBadge = (filter: SavedFilter, isClickable = false) => {
    const config = accessLevelConfig[filter.access_level as keyof typeof accessLevelConfig]
    if (!config) return null

    const IconComponent = config.icon
    const isUpdating = updatingFilters.has(filter.id)
    
    if (isClickable) {
      return (
        <button
          onClick={(e) => handleToggleAccessLevel(filter, e)}
          disabled={isUpdating}
          className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border transition-colors hover:opacity-80 disabled:opacity-50 ${config.color} ${config.bgColor} ${config.borderColor}`}
          title={isUpdating ? 'Updating...' : `Click to change to ${filter.access_level === 'private' ? 'Pipeline Users' : 'Private'}`}
        >
          {isUpdating ? (
            <RefreshCw className="w-3 h-3 mr-1 animate-spin" />
          ) : (
            <IconComponent className="w-3 h-3 mr-1" />
          )}
          {config.label}
        </button>
      )
    }
    
    return (
      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${config.color} ${config.bgColor} ${config.borderColor} border`}>
        <IconComponent className="w-3 h-3 mr-1" />
        {config.label}
      </span>
    )
  }

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


  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className={`bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-hidden ${className}`}>
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-3">
            <Filter className="w-6 h-6 text-blue-500" />
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Saved Filters</h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">{pipeline.name} • {filteredFilters.length} filters</p>
            </div>
          </div>

          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
          {error && (
            <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md">
              <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
            </div>
          )}

          <div className="space-y-6">
            {/* Search */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Search Filters
              </label>
              <div className="relative">
                <Search className="w-4 h-4 absolute left-3 top-2.5 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search by name, description, or creator..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                />
              </div>
            </div>

            {/* Access Level Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Filter by Access Level
              </label>
              <div className="flex flex-wrap gap-2">
                {Object.entries(accessLevelConfig).map(([level, config]) => {
                  const IconComponent = config.icon
                  const isSelected = selectedAccessLevels.includes(level)
                  return (
                    <button
                      key={level}
                      onClick={() => {
                        setSelectedAccessLevels(prev =>
                          isSelected
                            ? prev.filter(l => l !== level)
                            : [...prev, level]
                        )
                      }}
                      className={`px-3 py-2 text-sm rounded-md border flex items-center ${
                        isSelected
                          ? `${config.color} ${config.bgColor} ${config.borderColor}`
                          : 'text-gray-600 dark:text-gray-300 bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600'
                      }`}
                    >
                      <IconComponent className="w-4 h-4 mr-2" />
                      {config.label}
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Sort Options */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Sort By
              </label>
              <div className="flex flex-wrap gap-2">
                {[
                  { field: 'last_used_at', label: 'Last Used' },
                  { field: 'usage_count', label: 'Most Used' },
                  { field: 'created_at', label: 'Date Created' },
                  { field: 'name', label: 'Name' }
                ].map(({ field, label }) => (
                  <button
                    key={field}
                    onClick={() => handleSort(field as SortField)}
                    className={`px-3 py-2 text-sm rounded-md border flex items-center ${
                      sortField === field
                        ? 'bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-900/20 dark:text-blue-400 dark:border-blue-800'
                        : 'border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'
                    }`}
                  >
                    {label}
                    {sortField === field && (
                      <ArrowUpDown className={`w-4 h-4 ml-2 ${sortDirection === 'desc' ? 'rotate-180' : ''}`} />
                    )}
                  </button>
                ))}
              </div>
            </div>

            {/* Filter Results */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Available Filters ({filteredFilters.length})
              </label>

              {loading ? (
                <div className="text-center py-8">
                  <RefreshCw className="w-8 h-8 animate-spin text-gray-400 mx-auto mb-2" />
                  <p className="text-gray-500 dark:text-gray-400">Loading filters...</p>
                </div>
              ) : filteredFilters.length === 0 ? (
                <div className="text-center py-8 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                  <Filter className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                    {searchQuery || selectedAccessLevels.length < 2 ? 'No filters match your criteria' : 'No saved filters yet'}
                  </h3>
                  <p className="text-gray-500 dark:text-gray-400 mb-4">
                    {searchQuery || selectedAccessLevels.length < 2 
                      ? 'Try adjusting your search or filter criteria'
                      : 'Create your first saved filter to quickly access common filter combinations'
                    }
                  </p>
                </div>
              ) : (
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {filteredFilters.map(filter => (
                    <div
                      key={filter.id}
                      className="group bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg p-4 hover:bg-gray-50 dark:hover:bg-gray-600 cursor-pointer transition-colors"
                      onClick={() => handleFilterSelect(filter)}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-2 mb-2">
                            <h3 className="font-medium text-gray-900 dark:text-white truncate">{filter.name}</h3>
                            {filter.is_default && <Star className="w-4 h-4 text-yellow-500" />}
                            {getAccessLevelBadge(filter, true)}
                          </div>
                          
                          {filter.description && (
                            <p className="text-sm text-gray-500 dark:text-gray-400 mb-3 line-clamp-2">{filter.description}</p>
                          )}
                          
                          <div className="flex items-center space-x-4 text-xs text-gray-400">
                            <span className="flex items-center">
                              <Eye className="w-3 h-3 mr-1" />
                              {filter.usage_count} uses
                            </span>
                            <span className="flex items-center">
                              <Clock className="w-3 h-3 mr-1" />
                              {formatLastUsed(filter.last_used_at)}
                            </span>
                            <span>{(filter.visible_fields || []).length} fields</span>
                            {filter.share_count > 0 && (
                              <span className="flex items-center">
                                <Users className="w-3 h-3 mr-1" />
                                {filter.share_count} shares
                              </span>
                            )}
                            <span>by {filter.created_by.email}</span>
                          </div>
                        </div>

                        <div className="flex items-center space-x-2 ml-4">
                          {filter.can_share?.allowed && (
                            <div onClick={(e) => e.stopPropagation()}>
                              <ShareFilterButton filter={filter} variant="ghost" size="sm" />
                            </div>
                          )}

                          <button
                            onClick={(e) => handleDeleteFilter(filter, e)}
                            className="p-1 text-gray-400 hover:text-red-600 dark:hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end space-x-3 p-6 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}