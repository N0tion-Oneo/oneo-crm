'use client'

import React, { useState, useEffect } from 'react'
import { X, Shield, Save, AlertCircle, Check } from 'lucide-react'
import { api } from '@/lib/api'

interface UserType {
  id?: number
  name: string
  slug: string
  description: string
  is_system_default: boolean
  is_custom: boolean
  base_permissions: Record<string, string[]>
  user_count?: number
}

interface UserTypeModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  userType?: UserType | null
  mode: 'create' | 'edit'
}

interface ValidationErrors {
  name?: string
  slug?: string
  description?: string
}


export default function UserTypeModal({ isOpen, onClose, onSuccess, userType, mode }: UserTypeModalProps) {
  const [formData, setFormData] = useState<UserType>({
    name: '',
    slug: '',
    description: '',
    is_system_default: false,
    is_custom: true,
    base_permissions: {}
  })
  
  const [errors, setErrors] = useState<ValidationErrors>({})
  const [loading, setLoading] = useState(false)

  // Initialize form data when modal opens or userType changes
  useEffect(() => {
    if (isOpen) {
      if (mode === 'edit' && userType) {
        setFormData({
          ...userType,
          base_permissions: userType.base_permissions || {}
        })
      } else {
        // Reset for create mode
        setFormData({
          name: '',
          slug: '',
          description: '',
          is_system_default: false,
          is_custom: true,
          base_permissions: {}
        })
      }
      setErrors({})
    }
  }, [isOpen, mode, userType])

  // Auto-generate slug from name
  useEffect(() => {
    if (mode === 'create' && formData.name && !formData.slug) {
      const slug = formData.name
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '_')
        .replace(/^_+|_+$/g, '')
        .substring(0, 50)
      
      setFormData(prev => ({ ...prev, slug }))
    }
  }, [formData.name, mode])

  const validateForm = (): boolean => {
    const newErrors: ValidationErrors = {}

    // Name validation
    if (!formData.name.trim()) {
      newErrors.name = 'User type name is required'
    } else if (formData.name.length < 2) {
      newErrors.name = 'Name must be at least 2 characters'
    } else if (formData.name.length > 100) {
      newErrors.name = 'Name must be less than 100 characters'
    }

    // Slug validation
    if (!formData.slug.trim()) {
      newErrors.slug = 'Slug is required'
    } else if (!/^[a-z0-9_]+$/.test(formData.slug)) {
      newErrors.slug = 'Slug can only contain lowercase letters, numbers, and underscores'
    } else if (formData.slug.length > 50) {
      newErrors.slug = 'Slug must be less than 50 characters'
    }

    // Description validation
    if (formData.description && formData.description.length > 500) {
      newErrors.description = 'Description must be less than 500 characters'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleInputChange = (field: keyof UserType, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }))
    
    // Clear specific error when user starts typing
    if (errors[field as keyof ValidationErrors]) {
      setErrors(prev => ({
        ...prev,
        [field]: undefined
      }))
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!validateForm()) {
      return
    }

    setLoading(true)
    try {
      const payload = {
        name: formData.name.trim(),
        slug: formData.slug.trim(),
        description: formData.description.trim(),
        // Start with minimal default permissions for new custom user types
        base_permissions: mode === 'create' ? {
          users: ['read'],
          pipelines: ['read'],
          records: ['read'],
          api_access: ['read']
        } : formData.base_permissions
      }

      if (mode === 'create') {
        await api.post('/auth/user-types/', payload)
      } else if (mode === 'edit' && userType) {
        await api.put(`/auth/user-types/${userType.id}/`, payload)
      }

      onSuccess()
      onClose()
    } catch (error: any) {
      console.error('Failed to save user type:', error)
      
      // Handle API validation errors
      if (error.response?.data) {
        const apiErrors: ValidationErrors = {}
        const data = error.response.data
        
        if (data.name) apiErrors.name = Array.isArray(data.name) ? data.name[0] : data.name
        if (data.slug) apiErrors.slug = Array.isArray(data.slug) ? data.slug[0] : data.slug
        if (data.description) apiErrors.description = Array.isArray(data.description) ? data.description[0] : data.description
        
        setErrors(apiErrors)
      } else {
        alert('Failed to save user type. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  const isSystemDefault = userType?.is_system_default || false
  const canEditPermissions = !isSystemDefault || mode === 'edit'

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            <Shield className="w-6 h-6 text-primary mr-3" />
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                {mode === 'create' ? 'Create User Type' : `Edit ${userType?.name}`}
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                {mode === 'create' 
                  ? 'Create a custom user type. Configure permissions using the Permission Matrix after creation.'
                  : isSystemDefault 
                    ? 'Editing system default user type (name and description only)'
                    : 'Edit custom user type details. Use Permission Matrix to modify permissions.'
                }
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-500 dark:hover:text-gray-300 p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto max-h-[calc(90vh-140px)]">
          <form onSubmit={handleSubmit} className="p-6 space-y-6">
            {/* Basic Information */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">Basic Information</h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    User Type Name *
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => handleInputChange('name', e.target.value)}
                    disabled={isSystemDefault}
                    className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:border-gray-600 dark:text-white ${
                      errors.name ? 'border-red-500' : 'border-gray-300'
                    } ${isSystemDefault ? 'bg-gray-100 dark:bg-gray-600 cursor-not-allowed' : ''}`}
                    placeholder="e.g., Sales Manager"
                    maxLength={100}
                  />
                  {errors.name && (
                    <p className="mt-1 text-sm text-red-600 flex items-center">
                      <AlertCircle className="w-4 h-4 mr-1" />
                      {errors.name}
                    </p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Slug *
                  </label>
                  <input
                    type="text"
                    value={formData.slug}
                    onChange={(e) => handleInputChange('slug', e.target.value)}
                    disabled={isSystemDefault}
                    className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:border-gray-600 dark:text-white ${
                      errors.slug ? 'border-red-500' : 'border-gray-300'
                    } ${isSystemDefault ? 'bg-gray-100 dark:bg-gray-600 cursor-not-allowed' : ''}`}
                    placeholder="e.g., sales_manager"
                    maxLength={50}
                  />
                  {errors.slug && (
                    <p className="mt-1 text-sm text-red-600 flex items-center">
                      <AlertCircle className="w-4 h-4 mr-1" />
                      {errors.slug}
                    </p>
                  )}
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    Lowercase letters, numbers, and underscores only
                  </p>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Description
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => handleInputChange('description', e.target.value)}
                  className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:border-gray-600 dark:text-white ${
                    errors.description ? 'border-red-500' : 'border-gray-300'
                  }`}
                  placeholder="Describe the role and responsibilities..."
                  rows={3}
                  maxLength={500}
                />
                {errors.description && (
                  <p className="mt-1 text-sm text-red-600 flex items-center">
                    <AlertCircle className="w-4 h-4 mr-1" />
                    {errors.description}
                  </p>
                )}
              </div>
            </div>

            {/* Permission Configuration Info */}
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md p-4">
              <div className="flex items-start">
                <Shield className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5 mr-3 flex-shrink-0" />
                <div>
                  <h4 className="text-sm font-medium text-blue-900 dark:text-blue-100 mb-1">
                    Permission Configuration
                  </h4>
                  <p className="text-sm text-blue-800 dark:text-blue-200">
                    {mode === 'create' 
                      ? 'New user types start with basic read permissions. Use the Permission Matrix to configure detailed permissions after creation.'
                      : 'Use the Permission Matrix to modify permissions for this user type.'
                    }
                  </p>
                </div>
              </div>
            </div>
          </form>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end space-x-3 p-6 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/50">
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-600 border border-gray-300 dark:border-gray-500 rounded-md hover:bg-gray-50 dark:hover:bg-gray-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Cancel
          </button>
          <button
            type="submit"
            onClick={handleSubmit}
            disabled={loading}
            className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-primary hover:bg-primary/90 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4 mr-2" />
                {mode === 'create' ? 'Create User Type' : 'Save Changes'}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}