'use client'

import React, { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { X, Check, AlertCircle, Palette, Folder, Users, Settings, Tag, Star } from 'lucide-react'

interface FieldGroup {
  id: string
  name: string
  description?: string
  color: string
  icon: string
  display_order: number
  field_count: number
  created_at: string
  created_by: any
  updated_at: string
  updated_by?: any
}

interface FieldGroupSettingsPanelProps {
  group: FieldGroup
  isOpen: boolean
  onClose: () => void
  onSave: (groupId: string, updates: Partial<FieldGroup>) => Promise<void>
  existingGroups: FieldGroup[]
}

// Available icons for field groups
const FIELD_GROUP_ICONS = [
  { value: 'folder', label: 'Folder', icon: Folder },
  { value: 'users', label: 'Users', icon: Users },
  { value: 'settings', label: 'Settings', icon: Settings },
  { value: 'tag', label: 'Tag', icon: Tag },
  { value: 'star', label: 'Star', icon: Star },
  { value: 'palette', label: 'Palette', icon: Palette },
]

// Predefined colors for field groups
const FIELD_GROUP_COLORS = [
  '#3B82F6', // Blue
  '#10B981', // Green
  '#F59E0B', // Yellow
  '#EF4444', // Red
  '#8B5CF6', // Purple
  '#F97316', // Orange
  '#06B6D4', // Cyan
  '#84CC16', // Lime
  '#EC4899', // Pink
  '#6B7280', // Gray
]

export const FieldGroupSettingsPanel: React.FC<FieldGroupSettingsPanelProps> = ({
  group,
  isOpen,
  onClose,
  onSave,
  existingGroups
}) => {
  const [formData, setFormData] = useState({
    name: group.name,
    description: group.description || '',
    color: group.color,
    icon: group.icon
  })
  const [saving, setSaving] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})

  // Reset form when group changes
  useEffect(() => {
    setFormData({
      name: group.name,
      description: group.description || '',
      color: group.color,
      icon: group.icon
    })
    setErrors({})
  }, [group])

  // Validation
  const validateForm = () => {
    const newErrors: Record<string, string> = {}

    // Name validation
    const trimmedName = formData.name.trim()
    if (!trimmedName) {
      newErrors.name = 'Group name is required'
    } else if (trimmedName.length < 2) {
      newErrors.name = 'Group name must be at least 2 characters'
    } else if (trimmedName.length > 100) {
      newErrors.name = 'Group name must be less than 100 characters'
    } else {
      // Check for duplicate names (excluding current group)
      const isDuplicate = existingGroups.some(g => 
        g.id !== group.id && 
        g.name.toLowerCase() === trimmedName.toLowerCase()
      )
      if (isDuplicate) {
        newErrors.name = 'A group with this name already exists'
      }
    }

    // Description validation (optional but has limits)
    if (formData.description && formData.description.length > 500) {
      newErrors.description = 'Description must be less than 500 characters'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSave = async () => {
    if (!validateForm()) {
      return
    }

    setSaving(true)
    try {
      const updates = {
        name: formData.name.trim(),
        description: formData.description.trim(),
        color: formData.color,
        icon: formData.icon
      }
      
      await onSave(group.id, updates)
      onClose()
    } catch (error) {
      console.error('Failed to save field group:', error)
      setErrors({ general: 'Failed to save changes. Please try again.' })
    } finally {
      setSaving(false)
    }
  }

  const handleCancel = () => {
    // Reset form to original values
    setFormData({
      name: group.name,
      description: group.description || '',
      color: group.color,
      icon: group.icon
    })
    setErrors({})
    onClose()
  }

  if (!isOpen) return null

  const hasChanges = (
    formData.name !== group.name ||
    formData.description !== (group.description || '') ||
    formData.color !== group.color ||
    formData.icon !== group.icon
  )

  const selectedIcon = FIELD_GROUP_ICONS.find(i => i.value === formData.icon)
  const IconComponent = selectedIcon?.icon || Folder

  // Use portal to render outside the component tree
  return createPortal(
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[9999]">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-md mx-4 max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-3">
            <div 
              className="w-8 h-8 rounded-lg flex items-center justify-center text-white text-sm"
              style={{ backgroundColor: formData.color }}
            >
              <IconComponent className="w-4 h-4" />
            </div>
            <h2 className="text-lg font-medium text-gray-900 dark:text-white">
              Group Settings
            </h2>
          </div>
          <button
            onClick={handleCancel}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <div className="p-4 space-y-4 overflow-y-auto">
          {/* General Error */}
          {errors.general && (
            <div className="flex items-center space-x-2 text-red-600 dark:text-red-400 text-sm">
              <AlertCircle className="w-4 h-4" />
              <span>{errors.general}</span>
            </div>
          )}

          {/* Group Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Group Name *
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
              onBlur={validateForm}
              className={`w-full px-3 py-2 border rounded-md text-sm ${
                errors.name
                  ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                  : 'border-gray-300 dark:border-gray-600 focus:border-blue-500 focus:ring-blue-500'
              } dark:bg-gray-700 dark:text-white`}
              placeholder="Enter group name"
            />
            {errors.name && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.name}</p>
            )}
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Description
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              onBlur={validateForm}
              rows={3}
              className={`w-full px-3 py-2 border rounded-md text-sm resize-none ${
                errors.description
                  ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                  : 'border-gray-300 dark:border-gray-600 focus:border-blue-500 focus:ring-blue-500'
              } dark:bg-gray-700 dark:text-white`}
              placeholder="Optional description for this group"
            />
            {errors.description && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.description}</p>
            )}
          </div>

          {/* Color Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Group Color
            </label>
            <div className="grid grid-cols-5 gap-2">
              {FIELD_GROUP_COLORS.map((color) => (
                <button
                  key={color}
                  type="button"
                  onClick={() => setFormData(prev => ({ ...prev, color }))}
                  className={`w-8 h-8 rounded-md border-2 ${
                    formData.color === color
                      ? 'border-gray-800 dark:border-white'
                      : 'border-gray-300 dark:border-gray-600'
                  } hover:scale-110 transition-transform`}
                  style={{ backgroundColor: color }}
                  title={color}
                />
              ))}
            </div>
          </div>

          {/* Icon Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Group Icon
            </label>
            <div className="grid grid-cols-3 gap-2">
              {FIELD_GROUP_ICONS.map((iconOption) => {
                const IconComp = iconOption.icon
                return (
                  <button
                    key={iconOption.value}
                    type="button"
                    onClick={() => setFormData(prev => ({ ...prev, icon: iconOption.value }))}
                    className={`flex items-center space-x-2 px-3 py-2 rounded-md border text-sm transition-colors ${
                      formData.icon === iconOption.value
                        ? 'bg-blue-50 border-blue-300 text-blue-800 dark:bg-blue-900/20 dark:border-blue-600 dark:text-blue-300'
                        : 'border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                    }`}
                  >
                    <IconComp className="w-4 h-4" />
                    <span>{iconOption.label}</span>
                  </button>
                )
              })}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end space-x-2 p-4 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={handleCancel}
            className="px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
            disabled={saving}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !hasChanges || Object.keys(errors).length > 0}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
          >
            {saving ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Saving...</span>
              </>
            ) : (
              <>
                <Check className="w-4 h-4" />
                <span>Save Changes</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>,
    document.body
  )
}