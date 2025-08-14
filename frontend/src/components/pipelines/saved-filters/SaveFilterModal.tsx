'use client'

import React, { useState, useEffect } from 'react'
import { X, Save, Edit, Plus } from 'lucide-react'
import { savedFiltersApi } from '@/lib/api'
import { BooleanQuery } from '@/types/records'
import { PermissionGuard } from '@/components/permissions/PermissionGuard'
import { useAuth } from '@/features/auth/context'

export interface SaveFilterModalProps {
  isOpen: boolean
  onClose: () => void
  onSaved?: (savedFilter: any) => void
  // Filter state from existing filter system
  booleanQuery: BooleanQuery
  pipeline: {
    id: string
    name: string
  }
  currentViewMode?: 'table' | 'kanban' | 'calendar'
  visibleFields?: string[]
  sortConfig?: any
  // Current saved filter (if we're editing/updating an existing one)
  currentSavedFilter?: {
    id: string
    name: string
    description: string
    access_level: 'private' | 'pipeline_users'
    is_default: boolean
  }
  // Force the modal into a specific mode (no radio button selection)
  forceMode?: 'update' | 'new'
}

export function SaveFilterModal({
  isOpen,
  onClose,
  onSaved,
  booleanQuery,
  pipeline,
  currentViewMode = 'table',
  visibleFields = [],
  sortConfig = {},
  currentSavedFilter,
  forceMode
}: SaveFilterModalProps) {
  const { hasPermission } = useAuth()
  const [saveMode, setSaveMode] = useState<'update' | 'new'>('new')
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    view_mode: currentViewMode,
    access_level: 'private' as 'private' | 'pipeline_users',
    is_default: false
  })
  const [selectedVisibleFields, setSelectedVisibleFields] = useState<string[]>(visibleFields || [])
  const [loading, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      // Use forceMode if provided, otherwise determine based on currentSavedFilter
      const mode = forceMode || (currentSavedFilter ? 'update' : 'new')
      setSaveMode(mode)
      
      if (mode === 'update' && currentSavedFilter) {
        // Pre-populate with existing filter data
        setFormData({
          name: currentSavedFilter.name,
          description: currentSavedFilter.description,
          view_mode: currentViewMode,
          access_level: currentSavedFilter.access_level,
          is_default: currentSavedFilter.is_default
        })
      } else {
        // Start fresh or save as new
        const baseName = currentSavedFilter && mode === 'new' 
          ? `${currentSavedFilter.name} (Copy)`
          : ''
        
        // When saving as new from existing filter, preserve access level
        const defaultAccessLevel = currentSavedFilter && mode === 'new'
          ? currentSavedFilter.access_level
          : 'private'
        
        setFormData({
          name: baseName,
          description: '',
          view_mode: currentViewMode,
          access_level: defaultAccessLevel,
          is_default: false
        })
      }
      setSelectedVisibleFields(visibleFields || [])
      setError(null)
    }
  }, [isOpen, currentViewMode, visibleFields, currentSavedFilter, forceMode])

  // Handle save mode changes to update form data (only if no forceMode)
  useEffect(() => {
    if (!forceMode && currentSavedFilter && saveMode === 'new') {
      // When switching to "new" mode, suggest a copy name and preserve access level
      setFormData(prev => ({
        ...prev,
        name: `${currentSavedFilter.name} (Copy)`,
        access_level: currentSavedFilter.access_level, // Preserve access level
        is_default: false // New copies shouldn't be default
      }))
    } else if (!forceMode && currentSavedFilter && saveMode === 'update') {
      // When switching back to update mode, restore original data
      setFormData(prev => ({
        ...prev,
        name: currentSavedFilter.name,
        access_level: currentSavedFilter.access_level,
        is_default: currentSavedFilter.is_default
      }))
    }
  }, [saveMode, currentSavedFilter, forceMode])

  // Auto-capture current view state

  const handleSave = async () => {
    try {
      setSaving(true)
      setError(null)

      if (!formData.name.trim()) {
        setError('Filter name is required')
        return
      }

      const payload = {
        name: formData.name.trim(),
        description: formData.description.trim(),
        pipeline: pipeline.id,
        filter_config: booleanQuery,
        view_mode: formData.view_mode,
        visible_fields: selectedVisibleFields,
        sort_config: sortConfig,
        access_level: formData.access_level,
        is_shareable: true, // Both private and pipeline users can be shared
        is_default: formData.is_default
      }

      console.log(`💾 ${saveMode === 'update' ? 'Updating' : 'Creating'} filter with payload:`, payload)
      
      let response
      if (saveMode === 'update' && currentSavedFilter) {
        response = await savedFiltersApi.update(currentSavedFilter.id, payload)
        console.log('✅ Filter updated successfully:', response.data)
      } else {
        response = await savedFiltersApi.create(payload)
        console.log('✅ Filter created successfully:', response.data)
      }
      
      if (onSaved) {
        onSaved(response.data)
      }
      
      onClose()
    } catch (err: any) {
      console.error(`❌ Error ${saveMode === 'update' ? 'updating' : 'creating'} filter:`, err)
      setError(err.response?.data?.detail || err.message || `Failed to ${saveMode === 'update' ? 'update' : 'save'} filter`)
    } finally {
      setSaving(false)
    }
  }

  // selectedVisibleFields is automatically set from props and represents current view state

  const hasActiveFilters = booleanQuery && booleanQuery.groups ? booleanQuery.groups.some(group => 
    group.filters.length > 0
  ) : false

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-3">
            {saveMode === 'update' ? (
              <Edit className="w-6 h-6 text-green-500" />
            ) : (
              <Save className="w-6 h-6 text-blue-500" />
            )}
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                {saveMode === 'update' ? `Update "${currentSavedFilter?.name}"` : 'Save New Filter'}
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {saveMode === 'update' 
                  ? `Update "${currentSavedFilter?.name}" with current settings`
                  : hasActiveFilters 
                    ? 'Save your current filters, view mode, and field visibility settings'
                    : 'Save the current view settings and field visibility (no active filters)'
                }
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
          {error && (
            <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md">
              <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
            </div>
          )}

          <div className="space-y-6">
            {/* Save Mode Selection (only show if we have a current saved filter AND no forceMode) */}
            {currentSavedFilter && !forceMode && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Save Action
                </label>
                <div className="space-y-3">
                  <label className={`flex items-start space-x-3 p-3 rounded-lg border-2 cursor-pointer transition-colors ${
                    saveMode === 'update' 
                      ? 'border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-900/20' 
                      : 'border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500'
                  }`}>
                    <input
                      type="radio"
                      name="save_mode"
                      value="update"
                      checked={saveMode === 'update'}
                      onChange={() => setSaveMode('update')}
                      className="mt-0.5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <div>
                      <div className="font-medium text-gray-900 dark:text-white">🔄 Update Existing Filter</div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">Overwrite "{currentSavedFilter.name}" with current view settings</div>
                    </div>
                  </label>
                  
                  <label className={`flex items-start space-x-3 p-3 rounded-lg border-2 cursor-pointer transition-colors ${
                    saveMode === 'new' 
                      ? 'border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-900/20' 
                      : 'border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500'
                  }`}>
                    <input
                      type="radio"
                      name="save_mode"
                      value="new"
                      checked={saveMode === 'new'}
                      onChange={() => setSaveMode('new')}
                      className="mt-0.5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <div>
                      <div className="font-medium text-gray-900 dark:text-white">➕ Save as New Filter</div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">Create a new saved filter with current view settings</div>
                    </div>
                  </label>
                </div>
              </div>
            )}

            {/* Basic Information */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Filter Name *
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                placeholder="Enter a descriptive name for this filter..."
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Description (Optional)
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                placeholder="Describe what this filter shows..."
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
              />
            </div>

            {/* Access Level Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Access Level
              </label>
              <div className="space-y-3">
                <label className="flex items-start space-x-3">
                  <input
                    type="radio"
                    name="access_level"
                    value="private"
                    checked={formData.access_level === 'private'}
                    onChange={(e) => setFormData(prev => ({ ...prev, access_level: e.target.value as any }))}
                    className="mt-0.5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <div>
                    <div className="font-medium text-gray-900 dark:text-white">🔒 Private</div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">Only you can see and use this filter</div>
                  </div>
                </label>
                
                <label className="flex items-start space-x-3">
                  <input
                    type="radio"
                    name="access_level"
                    value="pipeline_users"
                    checked={formData.access_level === 'pipeline_users'}
                    onChange={(e) => setFormData(prev => ({ ...prev, access_level: e.target.value as any }))}
                    className="mt-0.5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <div>
                    <div className="font-medium text-gray-900 dark:text-white">🏢 Pipeline Users</div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">All users with access to this pipeline can use this filter</div>
                  </div>
                </label>
                
              </div>
            </div>

            {/* Current View Summary */}
            <div className={`p-3 border rounded-md ${
              saveMode === 'update' 
                ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
                : 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800'
            }`}>
              <h4 className="font-medium text-gray-900 dark:text-white mb-2">
                {saveMode === 'update' ? 'What Will Be Updated' : 'What Will Be Saved'}
              </h4>
              <div className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                {saveMode === 'update' && (
                  <p><strong>Action:</strong> Update existing "{currentSavedFilter?.name}" filter</p>
                )}
                <p><strong>View Mode:</strong> {currentViewMode} view</p>
                <p><strong>Visible Fields:</strong> {selectedVisibleFields.length} fields</p>
                <p><strong>Active Filters:</strong> {hasActiveFilters ? 'Current filter configuration' : 'No filters applied'}</p>
                <p><strong>Access Level:</strong> {formData.access_level === 'private' ? '🔒 Private' : '🏢 Pipeline Users'}</p>
                <p className="text-xs italic mt-2">
                  {saveMode === 'update' 
                    ? 'This will overwrite the existing filter with current settings.'
                    : 'This will create a new filter with exactly what you\'re currently viewing.'
                  }
                </p>
              </div>
            </div>

            {/* Note about sharing */}
            <div className="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-md">
              <p className="text-sm text-green-600 dark:text-green-400">
                💡 All saved filters can be shared with external users via secure links, regardless of access level.
              </p>
            </div>

            {/* Default Filter */}
            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="is_default"
                checked={formData.is_default}
                onChange={(e) => setFormData(prev => ({ ...prev, is_default: e.target.checked }))}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <label htmlFor="is_default" className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Set as default filter for this pipeline
              </label>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end space-x-3 p-6 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white"
          >
            Cancel
          </button>
          <PermissionGuard 
            category="filters" 
            action={saveMode === 'update' ? 'edit_filters' : 'create_filters'}
            fallback={
              <button
                disabled
                className="px-4 py-2 text-gray-400 bg-gray-300 rounded-md cursor-not-allowed flex items-center space-x-2"
              >
                {saveMode === 'update' ? (
                  <Edit className="w-4 h-4" />
                ) : (
                  <Save className="w-4 h-4" />
                )}
                <span>No permission to {saveMode === 'update' ? 'edit' : 'create'} filters</span>
              </button>
            }
          >
            <button
              onClick={handleSave}
              disabled={loading || !formData.name.trim()}
              className={`px-4 py-2 text-white rounded-md disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2 ${
                saveMode === 'update' 
                  ? 'bg-green-600 hover:bg-green-700'
                  : 'bg-blue-600 hover:bg-blue-700'
              }`}
            >
              {saveMode === 'update' ? (
                <Edit className="w-4 h-4" />
              ) : (
                <Save className="w-4 h-4" />
              )}
              <span>{loading ? (saveMode === 'update' ? 'Updating...' : 'Saving...') : (saveMode === 'update' ? 'Update Filter' : 'Save Filter')}</span>
            </button>
          </PermissionGuard>
        </div>
      </div>
    </div>
  )
}