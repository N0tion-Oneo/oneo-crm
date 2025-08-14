'use client'

import React, { useState, useEffect } from 'react'
import { X, Save } from 'lucide-react'
import { savedFiltersApi } from '@/lib/api'
import { BooleanQuery } from '@/types/records'

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
}

export function SaveFilterModal({
  isOpen,
  onClose,
  onSaved,
  booleanQuery,
  pipeline,
  currentViewMode = 'table',
  visibleFields = [],
  sortConfig = {}
}: SaveFilterModalProps) {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    view_mode: currentViewMode,
    is_default: false
  })
  const [selectedVisibleFields, setSelectedVisibleFields] = useState<string[]>(visibleFields || [])
  const [loading, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      setFormData({
        name: '',
        description: '',
        view_mode: currentViewMode,
        is_default: false
      })
      setSelectedVisibleFields(visibleFields || [])
      setError(null)
    }
  }, [isOpen, currentViewMode, visibleFields])

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
        is_shareable: true, // All saved filters are shareable by default
        is_default: formData.is_default
      }

      console.log('💾 Saving filter with payload:', payload)
      
      const response = await savedFiltersApi.create(payload)
      
      console.log('✅ Filter saved successfully:', response.data)
      
      if (onSaved) {
        onSaved(response.data)
      }
      
      onClose()
    } catch (err: any) {
      console.error('❌ Error saving filter:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to save filter')
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
            <Save className="w-6 h-6 text-blue-500" />
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                Save Current View
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {hasActiveFilters 
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


            {/* Current View Summary */}
            <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
              <h4 className="font-medium text-gray-900 dark:text-white mb-2">What Will Be Saved</h4>
              <div className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                <p><strong>View Mode:</strong> {currentViewMode} view</p>
                <p><strong>Visible Fields:</strong> {selectedVisibleFields.length} fields</p>
                <p><strong>Active Filters:</strong> {hasActiveFilters ? 'Current filter configuration' : 'No filters applied'}</p>
                <p className="text-xs italic mt-2">This will save exactly what you're currently viewing.</p>
              </div>
            </div>

            {/* Note about sharing */}
            <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
              <p className="text-sm text-blue-600 dark:text-blue-400">
                💡 After saving, you can share this filter with others using the share button in the saved filters list.
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
          <button
            onClick={handleSave}
            disabled={loading || !formData.name.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
          >
            <Save className="w-4 h-4" />
            <span>{loading ? 'Saving...' : 'Save Filter'}</span>
          </button>
        </div>
      </div>
    </div>
  )
}