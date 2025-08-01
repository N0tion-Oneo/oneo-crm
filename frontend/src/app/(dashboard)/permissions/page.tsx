'use client'

import React, { useState, useEffect } from 'react'
import { Shield, Users, Database, Settings, Eye, Edit, Trash2, Plus, ChevronDown, ChevronRight, Filter, Search, Grid3X3, List, Lock, Info } from 'lucide-react'
import { useAuth } from '@/features/auth/context'
import { api } from '@/lib/api'
import UserTypeModal from '@/components/user-types/UserTypeModal'
import DeleteUserTypeModal from '@/components/user-types/DeleteUserTypeModal'

interface Permission {
  id: number
  name: string
  description: string
  category: string
  is_system: boolean
  pipeline_id?: number
  field_id?: number
}

interface UserType {
  id: number
  name: string
  slug: string
  description: string
  is_system_default: boolean
  is_custom: boolean
  base_permissions: Record<string, string[]>
  user_count?: number
  created_at: string
  updated_at: string
}

interface PermissionMatrix {
  [userType: string]: {
    [permission: string]: boolean
  }
}

interface Pipeline {
  id: number
  name: string
  slug: string
  description: string
  pipeline_type: string
  icon: string
  color: string
}

export default function PermissionsPage() {
  const { user } = useAuth()
  const [userTypes, setUserTypes] = useState<UserType[]>([])
  const [permissions, setPermissions] = useState<Permission[]>([])
  const [permissionMatrix, setPermissionMatrix] = useState<PermissionMatrix>({})
  const [pipelines, setPipelines] = useState<Pipeline[]>([])
  const [fieldPermissions, setFieldPermissions] = useState<any[]>([])
  const [pipelineFields, setPipelineFields] = useState<any[]>([])
  const [pipelinePermissions, setPipelinePermissions] = useState<any[]>([])
  const [selectedPipelineForFields, setSelectedPipelineForFields] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [fieldLoading, setFieldLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'matrix' | 'fields' | 'roles'>('matrix')
  
  // UI state
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(['system', 'users', 'pipelines']))
  
  // Modal states
  const [showUserTypeModal, setShowUserTypeModal] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [selectedUserType, setSelectedUserType] = useState<UserType | null>(null)
  const [userTypeModalMode, setUserTypeModalMode] = useState<'create' | 'edit'>('create')

  // Load data
  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true)
        const [userTypesResponse, pipelinesResponse, pipelinePermissionsResponse] = await Promise.all([
          api.get('/auth/user-types/'), // Get user types with their permissions
          api.get('/api/pipelines/').catch(() => ({ data: { results: [] } })), // Get pipelines, fallback to empty if error
          api.get('/auth/user-type-pipeline-permissions/').catch(() => ({ data: { results: [] } })) // Get pipeline access permissions
        ])

        const userTypesData = userTypesResponse.data.results || userTypesResponse.data || []
        const pipelinesData = pipelinesResponse.data.results || pipelinesResponse.data || []
        const pipelinePermissionsData = pipelinePermissionsResponse.data.results || pipelinePermissionsResponse.data || []
        
        // Generate permissions including system permissions + pipeline-specific permissions
        const allPermissions: Permission[] = []
        let permissionId = 1
        
        // System permissions (from base_permissions in user types)
        const systemPermissions = {
          system: ['full_access'],
          users: ['create', 'read', 'update', 'delete', 'impersonate', 'assign_roles'],
          user_types: ['create', 'read', 'update', 'delete'],
          pipelines: ['access', 'create', 'read', 'update', 'delete', 'clone', 'export', 'import'],
          records: ['create', 'read', 'update', 'delete', 'bulk_edit', 'export', 'import'],
          fields: ['create', 'read', 'update', 'delete', 'configure'],
          relationships: ['create', 'read', 'update', 'delete', 'traverse'],
          workflows: ['create', 'read', 'update', 'delete', 'execute'],
          communications: ['create', 'read', 'update', 'delete', 'send'],
          settings: ['read', 'update'],
          monitoring: ['read', 'update'],
          ai_features: ['create', 'read', 'update', 'delete', 'configure'],
          reports: ['create', 'read', 'update', 'delete', 'export'],
          api_access: ['read', 'write', 'full_access']
        }

        // Add system permissions
        Object.entries(systemPermissions).forEach(([category, actions]) => {
          actions.forEach((action: string) => {
            // Special description for access action
            const description = action === 'access' 
              ? `Select which specific ${category} this user type can access`
              : `Allows ${action} operations on ${category}`
              
            allPermissions.push({
              id: permissionId++,
              name: `${action.charAt(0).toUpperCase() + action.slice(1)} ${category.charAt(0).toUpperCase() + category.slice(1)}`,
              description,
              category: category.charAt(0).toUpperCase() + category.slice(1),
              is_system: category === 'system' || action === 'full_access'
            })
          })
        })

        // Remove individual pipeline permissions from system matrix - they belong in Pipeline Access tab
        console.log('📊 System permissions generated (no individual pipeline permissions in matrix):', allPermissions.length)
        
        console.log('📋 Total permissions generated:', allPermissions.length)
        console.log('🗂️ Categories:', [...new Set(allPermissions.map(p => p.category))])

        setUserTypes(userTypesData)
        setPermissions(allPermissions)
        setPipelines(pipelinesData)
        setPipelinePermissions(pipelinePermissionsData)

        // Build permission matrix from base_permissions (system-level only)
        const matrix: PermissionMatrix = {}
        userTypesData.forEach((userType: any) => {
          matrix[userType.name] = {}
          allPermissions.forEach((permission: Permission) => {
            // All permissions in the matrix are now system permissions from base_permissions
            const parts = permission.name.split(' ')
            const action = parts[0].toLowerCase()
            const category = parts[1].toLowerCase()
            
            const hasPermission = userType.base_permissions?.[category]?.includes(action) || false
            matrix[userType.name][permission.name] = hasPermission
          })
        })
        setPermissionMatrix(matrix)

      } catch (error) {
        console.error('Failed to load permissions data:', error)
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [])

  // Helper functions
  const hasPipelineAccess = (userTypeId: number, pipelineId: number): boolean => {
    return pipelinePermissions.some(
      perm => perm.user_type === userTypeId && perm.pipeline_id === pipelineId
    )
  }

  // Get accessible pipelines for field controls - only show pipelines that at least one user type has access to
  const getAccessiblePipelinesForFields = (): Pipeline[] => {
    return pipelines.filter(pipeline => 
      userTypes.some(userType => hasPipelineAccess(userType.id, pipeline.id))
    )
  }

  // Get user types that have access to the selected pipeline for field controls
  const getUserTypesWithPipelineAccess = (pipelineId: number): UserType[] => {
    return userTypes.filter(userType => hasPipelineAccess(userType.id, pipelineId))
  }

  const togglePipelineAccess = async (userTypeId: number, pipelineId: number, hasAccess: boolean) => {
    const userType = userTypes.find(ut => ut.id === userTypeId)
    const pipeline = pipelines.find(p => p.id === pipelineId)
    if (!userType || !pipeline) return

    try {
      if (hasAccess) {
        // Try new backend endpoint first
        try {
          const response = await api.post(`/auth/user-types/${userTypeId}/grant_pipeline_access/`, {
            pipeline_id: pipelineId,
            access_level: 'read',
            permissions: ['read']
          })
          
          // Update local state
          setPipelinePermissions(prev => [...prev, response.data.pipeline_permission])
        } catch (newApiError) {
          console.log('New API failed, trying fallback...')
          // Fallback to old API
          const response = await api.post('/auth/user-type-pipeline-permissions/', {
            user_type: userTypeId,
            pipeline_id: pipelineId,
            permissions: ['read'],
            access_level: 'read'
          })
          
          setPipelinePermissions(prev => [...prev, response.data])
        }
      } else {
        // Try new backend endpoint first
        try {
          await api.post(`/auth/user-types/${userTypeId}/revoke_pipeline_access/`, {
            pipeline_id: pipelineId
          })
          
          // Update local state - remove the permission
          setPipelinePermissions(prev => 
            prev.filter(perm => !(perm.user_type === userTypeId && perm.pipeline_id === pipelineId))
          )
        } catch (newApiError) {
          console.log('New API failed, trying fallback...')
          // Fallback to old API - find and delete existing permission
          const existingPermission = pipelinePermissions.find(
            perm => perm.user_type === userTypeId && perm.pipeline_id === pipelineId
          )
          
          if (existingPermission) {
            await api.delete(`/auth/user-type-pipeline-permissions/${existingPermission.id}/`)
            
            // Update local state
            setPipelinePermissions(prev => 
              prev.filter(perm => perm.id !== existingPermission.id)
            )
          }
        }
      }

      // Show success notification
      const action = hasAccess ? 'granted' : 'revoked'
      const notification = document.createElement('div')
      notification.className = 'fixed top-4 right-4 bg-green-500 text-white px-4 py-2 rounded-md shadow-lg z-50'
      notification.textContent = `Pipeline access ${action}: ${pipeline.name} for ${userType.name}`
      document.body.appendChild(notification)
      
      setTimeout(() => {
        document.body.removeChild(notification)
      }, 3000)

    } catch (error: any) {
      console.error('Failed to update pipeline access:', error)
      console.error('Error details:', {
        status: error?.response?.status,
        data: error?.response?.data,
        message: error?.message,
        url: error?.config?.url
      })
      
      // Show error notification with more details
      const errorMessage = error?.response?.data?.error || 
                          error?.response?.data?.detail || 
                          error?.message || 
                          'Unknown error occurred'
      const notification = document.createElement('div')
      notification.className = 'fixed top-4 right-4 bg-red-500 text-white px-4 py-2 rounded-md shadow-lg z-50 max-w-md'
      notification.innerHTML = `
        <div class="font-semibold">Failed to update pipeline access for ${pipeline.name}</div>
        <div class="text-sm mt-1">${errorMessage}</div>
        <div class="text-xs mt-1 opacity-75">Status: ${error?.response?.status || 'Network Error'}</div>
      `
      document.body.appendChild(notification)
      
      setTimeout(() => {
        if (document.body.contains(notification)) {
          document.body.removeChild(notification)
        }
      }, 8000)
    }
  }

  const getSelectedPipelineCount = (userTypeId: number): number => {
    return pipelinePermissions.filter(perm => perm.user_type === userTypeId).length
  }

  const toggleCategory = (category: string) => {
    const newExpanded = new Set(expandedCategories)
    if (newExpanded.has(category)) {
      newExpanded.delete(category)
    } else {
      newExpanded.add(category)
    }
    setExpandedCategories(newExpanded)
  }

  const expandAllCategories = () => {
    setExpandedCategories(new Set(Object.keys(permissionsByCategory)))
  }

  const collapseAllCategories = () => {
    setExpandedCategories(new Set())
  }

  const toggleCategoryPermissions = async (category: string, userTypeName: string) => {
    const categoryPermissions = permissionsByCategory[category] || []
    const userType = userTypes.find(ut => ut.name === userTypeName)
    if (!userType) return

    // Check if all permissions in this category are granted
    const allGranted = categoryPermissions.every(permission => 
      permissionMatrix[userTypeName]?.[permission.name] === true
    )

    // Toggle all permissions in category
    const updates = categoryPermissions.map(permission => ({
      permission,
      newValue: !allGranted
    }))

    // Optimistically update UI
    setPermissionMatrix(prev => {
      const newMatrix = { ...prev }
      updates.forEach(({ permission, newValue }) => {
        if (!newMatrix[userTypeName]) newMatrix[userTypeName] = {}
        newMatrix[userTypeName][permission.name] = newValue
      })
      return newMatrix
    })

    // Make API calls
    try {
      const promises = updates.map(async ({ permission, newValue }) => {
        const parts = permission.name.split(' ')
        const action = parts[0].toLowerCase()
        const categoryName = parts[1].toLowerCase()

        if (newValue) {
          return api.post(`/auth/user-types/${userType.id}/add_permission/`, {
            category: categoryName,
            action
          })
        } else {
          return api.post(`/auth/user-types/${userType.id}/remove_permission/`, {
            category: categoryName,
            action
          })
        }
      })

      await Promise.all(promises)
      
      // Show success notification
      const notification = document.createElement('div')
      notification.className = 'fixed top-4 right-4 bg-green-500 text-white px-4 py-2 rounded-md shadow-lg z-50'
      notification.textContent = `${allGranted ? 'Revoked' : 'Granted'} all ${category} permissions for ${userTypeName}`
      document.body.appendChild(notification)
      
      setTimeout(() => {
        document.body.removeChild(notification)
      }, 3000)

    } catch (error) {
      // Revert on error
      setPermissionMatrix(prev => {
        const newMatrix = { ...prev }
        updates.forEach(({ permission, newValue }) => {
          if (!newMatrix[userTypeName]) newMatrix[userTypeName] = {}
          newMatrix[userTypeName][permission.name] = !newValue
        })
        return newMatrix
      })

      console.error('Failed to update category permissions:', error)
      
      const notification = document.createElement('div')
      notification.className = 'fixed top-4 right-4 bg-red-500 text-white px-4 py-2 rounded-md shadow-lg z-50'
      notification.textContent = `Failed to update ${category} permissions for ${userTypeName}`
      document.body.appendChild(notification)
      
      setTimeout(() => {
        document.body.removeChild(notification)
      }, 5000)
    }
  }






  // Field permission functions
  const loadPipelineFields = async (pipelineId: number) => {
    try {
      setFieldLoading(true)
      const response = await api.get(`/api/pipelines/${pipelineId}/fields/`)
      setPipelineFields(response.data.results || response.data || [])
    } catch (error) {
      console.error('Failed to load pipeline fields:', error)
      setPipelineFields([])
    } finally {
      setFieldLoading(false)
    }
  }

  const loadFieldPermissions = async () => {
    if (activeTab !== 'fields') return
    
    try {
      setFieldLoading(true)
      const response = await api.get('/auth/user-type-field-permissions/')
      setFieldPermissions(response.data.results || response.data || [])
    } catch (error) {
      console.error('Failed to load field permissions:', error)
      setFieldPermissions([])
    } finally {
      setFieldLoading(false)
    }
  }

  const updateFieldPermission = async (userTypeId: number, pipelineId: number, fieldId: number, property: string, value: any) => {
    try {
      // Find existing permission or create new one
      let permission = fieldPermissions.find(
        p => p.user_type === userTypeId && p.pipeline_id === pipelineId && p.field_id === fieldId
      )

      if (!permission) {
        // Create new permission
        const response = await api.post('/auth/user-type-field-permissions/', {
          user_type: userTypeId,
          pipeline_id: pipelineId,
          field_id: fieldId,
          [property]: value,
          can_view: property === 'can_view' ? value : true,
          can_edit: property === 'can_edit' ? value : false,
          visibility: property === 'visibility' ? value : 'visible'
        })
        permission = response.data
        setFieldPermissions(prev => [...prev, permission])
      } else {
        // Update existing permission
        const response = await api.put(`/auth/user-type-field-permissions/${permission.id}/`, {
          ...permission,
          [property]: value
        })

        setFieldPermissions(prev => 
          prev.map(p => p.id === permission.id ? response.data : p)
        )
      }

      // Show success notification
      const notification = document.createElement('div')
      notification.className = 'fixed top-4 right-4 bg-green-500 text-white px-4 py-2 rounded-md shadow-lg z-50'
      notification.textContent = `Updated field ${property}`
      document.body.appendChild(notification)
      
      setTimeout(() => {
        document.body.removeChild(notification)
      }, 3000)

    } catch (error) {
      console.error('Failed to update field permission:', error)
      
      const notification = document.createElement('div')
      notification.className = 'fixed top-4 right-4 bg-red-500 text-white px-4 py-2 rounded-md shadow-lg z-50'
      notification.textContent = 'Failed to update field permission'
      document.body.appendChild(notification)
      
      setTimeout(() => {
        document.body.removeChild(notification)
      }, 5000)
    }
  }

  const getFieldPermission = (userTypeId: number, pipelineId: number, fieldId: number, property: string): any => {
    const permission = fieldPermissions.find(
      p => p.user_type === userTypeId && p.pipeline_id === pipelineId && p.field_id === fieldId
    )
    return permission?.[property] ?? (property === 'can_view' ? true : property === 'can_edit' ? false : property === 'visibility' ? 'visible' : null)
  }

  // Load field permissions when switching to fields tab
  React.useEffect(() => {
    if (activeTab === 'fields') {
      loadFieldPermissions()
      const accessiblePipelines = getAccessiblePipelinesForFields()
      if (accessiblePipelines.length > 0 && !selectedPipelineForFields) {
        setSelectedPipelineForFields(accessiblePipelines[0].id)
      }
    }
  }, [activeTab, pipelines.length, pipelinePermissions.length])

  // Load fields when pipeline selection changes
  React.useEffect(() => {
    if (selectedPipelineForFields && activeTab === 'fields') {
      loadPipelineFields(selectedPipelineForFields)
    }
  }, [selectedPipelineForFields, activeTab])


  // Filter and search logic
  const filteredPermissions = permissions.filter(permission => {
    const matchesSearch = searchTerm === '' || 
      permission.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      permission.description.toLowerCase().includes(searchTerm.toLowerCase())
    
    const matchesCategory = selectedCategory === 'all' || 
      permission.category.toLowerCase() === selectedCategory.toLowerCase()
    
    return matchesSearch && matchesCategory
  })

  // Group permissions by category
  const permissionsByCategory = filteredPermissions.reduce((acc, permission) => {
    const category = permission.category || 'General'
    if (!acc[category]) {
      acc[category] = []
    }
    acc[category].push(permission)
    return acc
  }, {} as { [category: string]: Permission[] })
  
  // Debug logging for permissions
  React.useEffect(() => {
    console.log('🗂️ Permissions by category:', Object.keys(permissionsByCategory).map(cat => ({
      category: cat,
      count: permissionsByCategory[cat].length,
      samplePermissions: permissionsByCategory[cat].slice(0, 3).map(p => p.name)
    })))
  }, [permissionsByCategory])

  const togglePermission = async (userTypeName: string, permissionName: string) => {
    const newValue = !permissionMatrix[userTypeName][permissionName]
    
    // Find the user type and permission
    const userType = userTypes.find(ut => ut.name === userTypeName)
    const permission = permissions.find(p => p.name === permissionName)
    if (!userType || !permission) return
    
    // All permissions in the matrix are now system-level permissions
    // Pipeline-specific permissions are handled in the Pipeline Access tab
    
    // Check if this is a system default type and we're trying to remove critical permissions
    if (userType.is_system_default && !newValue) {
      const parts = permissionName.split(' ')
      const action = parts[0].toLowerCase()
      const category = parts[1].toLowerCase()
      
      // Prevent removing critical permissions from Admin
      if (userType.slug === 'admin' && category === 'system' && action === 'full_access') {
        alert('Cannot remove full system access from Admin user type')
        return
      }
    }
    
    // Extract category and action from permission name
    const parts = permissionName.split(' ')
    const action = parts[0].toLowerCase()
    const category = parts[1].toLowerCase()
    
    // Optimistically update the UI
    setPermissionMatrix(prev => ({
      ...prev,
      [userTypeName]: {
        ...prev[userTypeName],
        [permissionName]: newValue
      }
    }))

    try {
      if (newValue) {
        // Add permission
        await api.post(`/auth/user-types/${userType.id}/add_permission/`, {
          category,
          action
        })
      } else {
        // Remove permission
        await api.post(`/auth/user-types/${userType.id}/remove_permission/`, {
          category,
          action
        })
      }
      
      console.log(`✅ ${newValue ? 'Added' : 'Removed'} ${permissionName} for ${userTypeName}`)
      
      // Show success feedback
      const action_text = newValue ? 'granted' : 'revoked'
      const notification = document.createElement('div')
      notification.className = 'fixed top-4 right-4 bg-green-500 text-white px-4 py-2 rounded-md shadow-lg z-50'
      notification.textContent = `Permission ${action_text}: ${permissionName} for ${userTypeName}`
      document.body.appendChild(notification)
      
      setTimeout(() => {
        document.body.removeChild(notification)
      }, 3000)
      
    } catch (error: any) {
      // Revert on error
      setPermissionMatrix(prev => ({
        ...prev,
        [userTypeName]: {
          ...prev[userTypeName],
          [permissionName]: !newValue
        }
      }))
      
      console.error('Failed to update permission:', error)
      
      // Show user-friendly error
      let errorMessage = 'Failed to update permission'
      if (error.response?.data?.error) {
        errorMessage = error.response.data.error
      } else if (error.response?.status === 403) {
        errorMessage = 'You do not have permission to modify user type permissions'
      } else if (error.response?.status === 400) {
        errorMessage = error.response.data?.detail || 'Invalid permission configuration'
      }
      
      // Show error notification
      const notification = document.createElement('div')
      notification.className = 'fixed top-4 right-4 bg-red-500 text-white px-4 py-2 rounded-md shadow-lg z-50'
      notification.textContent = `Error: ${errorMessage}`
      document.body.appendChild(notification)
      
      setTimeout(() => {
        document.body.removeChild(notification)
      }, 5000)
    }
  }

  // User type management handlers
  const handleCreateUserType = () => {
    setSelectedUserType(null)
    setUserTypeModalMode('create')
    setShowUserTypeModal(true)
  }

  const handleEditUserType = (userType: UserType) => {
    setSelectedUserType(userType)
    setUserTypeModalMode('edit')
    setShowUserTypeModal(true)
  }

  const handleDeleteUserType = (userType: UserType) => {
    setSelectedUserType(userType)
    setShowDeleteModal(true)
  }

  const handleUserTypeSuccess = () => {
    // Reload data to reflect changes
    const loadData = async () => {
      try {
        setLoading(true)
        const [userTypesResponse, pipelinesResponse] = await Promise.all([
          api.get('/auth/user-types/'),
          api.get('/api/v1/pipelines/').catch(() => ({ data: { results: [] } }))
        ])

        const userTypesData = userTypesResponse.data.results || userTypesResponse.data || []
        const pipelinesData = pipelinesResponse.data.results || pipelinesResponse.data || []
        
        // Define comprehensive permission categories and actions
        const comprehensivePermissions = {
          system: ['full_access'],
          users: ['create', 'read', 'update', 'delete', 'impersonate', 'assign_roles'],
          user_types: ['create', 'read', 'update', 'delete'],
          pipelines: ['create', 'read', 'update', 'delete', 'clone', 'export', 'import'],
          records: ['create', 'read', 'update', 'delete', 'bulk_edit', 'export', 'import'],
          fields: ['create', 'read', 'update', 'delete', 'configure'],
          relationships: ['create', 'read', 'update', 'delete', 'traverse'],
          workflows: ['create', 'read', 'update', 'delete', 'execute'],
          communications: ['create', 'read', 'update', 'delete', 'send'],
          settings: ['read', 'update'],
          monitoring: ['read', 'update'],
          ai_features: ['create', 'read', 'update', 'delete', 'configure'],
          reports: ['create', 'read', 'update', 'delete', 'export'],
          api_access: ['read', 'write', 'full_access']
        }

        // Generate all possible permissions from comprehensive set
        const mockPermissions: Permission[] = []
        let permissionId = 1
        
        Object.entries(comprehensivePermissions).forEach(([category, actions]) => {
          actions.forEach((action: string) => {
            mockPermissions.push({
              id: permissionId++,
              name: `${action.charAt(0).toUpperCase() + action.slice(1)} ${category.charAt(0).toUpperCase() + category.slice(1)}`,
              description: `Allows ${action} operations on ${category}`,
              category: category.charAt(0).toUpperCase() + category.slice(1),
              is_system: category === 'system' || action === 'full_access'
            })
          })
        })

        setUserTypes(userTypesData)
        setPermissions(mockPermissions)
        setPipelines(pipelinesData)

        // Build permission matrix from base_permissions
        const matrix: PermissionMatrix = {}
        userTypesData.forEach((userType: any) => {
          matrix[userType.name] = {}
          mockPermissions.forEach((permission: Permission) => {
            // Extract category and action from permission name
            const parts = permission.name.split(' ')
            const action = parts[0].toLowerCase()
            const category = parts[1].toLowerCase()
            
            const hasPermission = userType.base_permissions?.[category]?.includes(action) || false
            matrix[userType.name][permission.name] = hasPermission
          })
        })
        setPermissionMatrix(matrix)

      } catch (error) {
        console.error('Failed to load permissions data:', error)
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }

  const getPermissionIcon = (category: string) => {
    switch (category.toLowerCase()) {
      case 'user management':
      case 'users':
        return Users
      case 'data':
      case 'pipelines':
        return Database
      case 'system':
      case 'admin':
        return Settings
      case 'security':
        return Shield
      default:
        return Eye
    }
  }

  const getRoleColor = (slug: string) => {
    switch (slug.toLowerCase()) {
      case 'admin':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
      case 'manager':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
      case 'user':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
      case 'viewer':
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
    }
  }

  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-300 dark:bg-gray-600 rounded w-1/4 mb-4"></div>
          <div className="h-4 bg-gray-300 dark:bg-gray-600 rounded w-1/2 mb-8"></div>
          <div className="h-64 bg-gray-300 dark:bg-gray-600 rounded"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              Permissions
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mt-2">
              Manage system permissions and field controls. Use <strong>System Permissions</strong> for platform-wide access and specific pipeline selection, and <strong>Field Controls</strong> for granular field permissions.
            </p>
          </div>
        </div>
      </div>

      {/* Permission Hierarchy Info */}
      <div className="mb-6 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <div className="flex items-start">
          <Info className="w-5 h-5 text-blue-600 dark:text-blue-400 mr-3 mt-0.5 flex-shrink-0" />
          <div>
            <h3 className="text-sm font-semibold text-blue-800 dark:text-blue-200 mb-1">
              Permission System Hierarchy
            </h3>
            <div className="text-xs text-blue-700 dark:text-blue-300 space-y-1">
              <div className="flex items-center">
                <span className="font-medium mr-2">1. Pipeline Access:</span>
                <span>Select which specific pipelines each user type can access (multiselect dropdown)</span>
              </div>
              <div className="flex items-center">
                <span className="font-medium mr-2">2. Pipeline Permissions:</span>
                <span>Define what actions user can perform within accessible pipelines (create, read, update, delete, etc.)</span>
              </div>
              <div className="flex items-center">
                <span className="font-medium mr-2">3. Field Controls:</span>
                <span>Granular field-level permissions within accessible pipelines (view, edit, visibility)</span>
              </div>
              <div className="mt-2 p-2 bg-blue-100 dark:bg-blue-800/30 rounded">
                <span className="font-medium">💡 Logic:</span> First select accessible pipelines, then permissions apply to those selected pipelines
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="mb-6">
        <nav className="flex space-x-8 border-b border-gray-200 dark:border-gray-700">
          {[
            { id: 'matrix', name: 'System Permissions', icon: Shield, count: permissions.length },
            { id: 'fields', name: 'Field Controls', icon: Settings, count: getAccessiblePipelinesForFields().length },
            { id: 'roles', name: 'User Roles', icon: Users, count: userTypes.length },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center px-1 py-4 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-primary text-primary'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
              }`}
            >
              <tab.icon className="w-4 h-4 mr-2" />
              {tab.name}
              {tab.count > 0 && (
                <span className="ml-2 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 px-2 py-1 rounded-full text-xs">
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* Permission Matrix Tab */}
      {activeTab === 'matrix' && (
        <div className="space-y-6">
          {/* Enhanced Controls Bar */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                {/* Search */}
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search permissions..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white"
                  />
                </div>
                
                {/* Category Filter */}
                <select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white"
                >
                  <option value="all">All Categories</option>
                  {Object.keys(permissionsByCategory).map((category) => (
                    <option key={category} value={category}>
                      {category} ({permissionsByCategory[category].length})
                    </option>
                  ))}
                </select>

              </div>
              
              {/* Enhanced Legend */}
              <div className="flex items-center space-x-4 text-xs">
                <div className="flex items-center">
                  <div className="w-4 h-4 bg-primary rounded border mr-2"></div>
                  <span className="text-gray-600 dark:text-gray-400">Granted</span>
                </div>
                <div className="flex items-center">
                  <div className="w-4 h-4 border border-gray-300 dark:border-gray-600 rounded mr-2"></div>
                  <span className="text-gray-600 dark:text-gray-400">Not Granted</span>
                </div>
                <div className="flex items-center">
                  <div className="relative">
                    <div className="w-4 h-4 border border-gray-300 dark:border-gray-600 rounded ring-2 ring-blue-200 dark:ring-blue-800 mr-2"></div>
                    <div className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 bg-blue-500 rounded-full"></div>
                  </div>
                  <span className="text-gray-600 dark:text-gray-400">Custom Role</span>
                </div>
                <div className="flex items-center">
                  <Lock className="w-4 h-4 text-gray-400 mr-2" />
                  <span className="text-gray-600 dark:text-gray-400">Protected</span>
                </div>
              </div>
            </div>
          </div>

          {/* Enhanced Permission Matrix */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden shadow-sm">
            {/* Matrix Header with User Type Cards */}
            <div className="border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-gray-50 to-gray-100 dark:from-gray-700 dark:to-gray-800">
              <div className="overflow-x-auto">
                <div className="min-w-full">
                  <div className="flex">
                    {/* Permission column header */}
                    <div className="flex-none w-80 px-6 py-4">
                      <div className="flex items-center justify-between">
                        <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
                          System Permissions
                        </h4>
                        <div className="flex items-center space-x-2">
                          <button 
                            onClick={expandAllCategories}
                            className="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 px-2 py-1 rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                          >
                            Expand All
                          </button>
                          <button 
                            onClick={collapseAllCategories}
                            className="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 px-2 py-1 rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                          >
                            Collapse All
                          </button>
                        </div>
                      </div>
                    </div>
                    
                    {/* User type columns */}
                    <div className="flex flex-1 min-w-0">
                      {userTypes.map((userType) => (
                        <div key={userType.id} className="flex-1 min-w-32 px-4 py-4 border-l border-gray-200 dark:border-gray-600">
                          <div className="text-center">
                            <div className="flex items-center justify-center mb-2">
                              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-medium ${getRoleColor(userType.slug || userType.name.toLowerCase()).replace('bg-', 'bg-').replace('-100', '-500').replace('-900', '-600')}`}>
                                {userType.name.charAt(0)}
                              </div>
                            </div>
                            <div className="text-sm font-medium text-gray-900 dark:text-white mb-1">
                              {userType.name}
                            </div>
                            <div className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getRoleColor(userType.slug || userType.name.toLowerCase())}`}>
                              {userType.slug || userType.name.toLowerCase()}
                            </div>
                            <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                              {userType.user_count || 0} users
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Permission Matrix Body */}
            <div className="overflow-x-auto max-h-96 overflow-y-auto">
              <div className="min-w-full">
                {Object.entries(permissionsByCategory).map(([category, categoryPermissions]) => (
                  <div key={`category-group-${category}`} className="border-b border-gray-100 dark:border-gray-700 last:border-b-0">
                    {/* Enhanced Category header */}
                    <div className="bg-gray-50 dark:bg-gray-750 border-b border-gray-200 dark:border-gray-600">
                      <div className="flex">
                        <div className="flex-none w-80 px-6 py-3">
                          <button
                            onClick={() => toggleCategory(category)}
                            className="flex items-center w-full text-left hover:bg-gray-100 dark:hover:bg-gray-600 rounded-md p-2 -m-2 transition-colors group"
                          >
                            {expandedCategories.has(category) ? (
                              <ChevronDown className="w-4 h-4 mr-3 text-gray-500 dark:text-gray-400 group-hover:text-gray-700 dark:group-hover:text-gray-300" />
                            ) : (
                              <ChevronRight className="w-4 h-4 mr-3 text-gray-500 dark:text-gray-400 group-hover:text-gray-700 dark:group-hover:text-gray-300" />
                            )}
                            {(() => {
                              const IconComponent = getPermissionIcon(category)
                              return <IconComponent className="w-5 h-5 mr-3 text-gray-600 dark:text-gray-400 group-hover:text-gray-700 dark:group-hover:text-gray-300" />
                            })()}
                            <div>
                              <div className="text-sm font-semibold text-gray-900 dark:text-white group-hover:text-gray-800 dark:group-hover:text-gray-100">
                                {category}
                              </div>
                              <div className="text-xs text-gray-500 dark:text-gray-400">
                                {categoryPermissions.length} permission{categoryPermissions.length !== 1 ? 's' : ''}
                              </div>
                            </div>
                          </button>
                        </div>
                        
                        {/* Category-level bulk actions */}
                        <div className="flex flex-1 min-w-0">
                          {userTypes.map((userType) => {
                            const allGranted = categoryPermissions.every(permission => 
                              permissionMatrix[userType.name]?.[permission.name] === true
                            )
                            const someGranted = categoryPermissions.some(permission => 
                              permissionMatrix[userType.name]?.[permission.name] === true
                            )
                            
                            return (
                              <div key={userType.id} className="flex-1 min-w-32 px-4 py-3 border-l border-gray-200 dark:border-gray-600 flex items-center justify-center">
                                <button 
                                  onClick={() => toggleCategoryPermissions(category, userType.name)}
                                  className={`text-xs px-2 py-1 rounded transition-colors ${
                                    allGranted 
                                      ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300 hover:bg-green-200 dark:hover:bg-green-800'
                                      : someGranted
                                      ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300 hover:bg-yellow-200 dark:hover:bg-yellow-800'
                                      : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-600'
                                  }`}
                                  title={`Toggle all ${category} permissions for ${userType.name} (${allGranted ? 'All granted' : someGranted ? 'Partially granted' : 'None granted'})`}
                                >
                                  {allGranted ? '✓ All' : someGranted ? '◐ Some' : 'None'}
                                </button>
                              </div>
                            )
                          })}
                        </div>
                      </div>
                    </div>
                    
                    {/* Permission rows for this category - only show if expanded */}
                    {expandedCategories.has(category) && categoryPermissions.map((permission, index) => (
                      <div key={`permission-${permission.id}`} className={`flex hover:bg-gray-50 dark:hover:bg-gray-700/50 ${index !== categoryPermissions.length - 1 ? 'border-b border-gray-100 dark:border-gray-700' : ''}`}>
                        <div className="flex-none w-80 px-6 py-4">
                          <div className="flex items-start">
                            <div className="flex-1">
                              <div className="text-sm font-medium text-gray-900 dark:text-white">
                                {permission.name}
                              </div>
                              <div className="text-xs text-gray-500 dark:text-gray-400 mt-1 leading-relaxed">
                                {permission.description}
                              </div>
                              {permission.is_system && (
                                <div className="mt-2">
                                  <span className="inline-flex items-center px-2 py-1 text-xs bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200 rounded-full">
                                    <Lock className="w-3 h-3 mr-1" />
                                    System
                                  </span>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                        
                        <div className="flex flex-1 min-w-0">
                          {userTypes.map((userType) => {
                            const hasPermission = permissionMatrix[userType.name]?.[permission.name]
                            const isSystemProtected = permission.is_system && userType.slug !== 'admin'
                            const isCustomType = userType.is_custom
                            
                            // Special handling for "Access Pipelines" permission - show multiselect instead of checkbox
                            if (permission.name === 'Access Pipelines') {
                              return (
                                <div key={`permission-${permission.id}-usertype-${userType.id}`} className="flex-1 min-w-32 px-4 py-4 border-l border-gray-200 dark:border-gray-600 flex items-center justify-center">
                                  <div className="w-full">
                                    {pipelines.length === 0 ? (
                                      <div className="text-center">
                                        <div className="text-xs text-gray-400 mb-2">No pipelines</div>
                                        <a 
                                          href="/pipelines"
                                          className="text-xs text-blue-600 hover:text-blue-700 underline"
                                        >
                                          Create Pipeline
                                        </a>
                                      </div>
                                    ) : (
                                      <div className="w-full border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 shadow-sm">
                                        <div className="max-h-32 overflow-y-auto p-1">
                                          <div className="space-y-1">
                                            {pipelines.map((pipeline) => (
                                              <label key={pipeline.id} className="flex items-center p-2 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-md cursor-pointer transition-colors group">
                                                <input
                                                  type="checkbox"
                                                  checked={hasPipelineAccess(userType.id, pipeline.id)}
                                                  className="w-4 h-4 text-primary bg-white border-2 border-gray-300 rounded focus:ring-primary focus:ring-2 dark:bg-gray-700 dark:border-gray-600 dark:focus:ring-primary mr-3 flex-shrink-0"
                                                  onChange={(e) => {
                                                    togglePipelineAccess(userType.id, pipeline.id, e.target.checked)
                                                  }}
                                                  title={`${pipeline.description || 'Toggle access to this pipeline'}`}
                                                />
                                                <div className="flex items-center flex-1 min-w-0">
                                                  <div 
                                                    className="w-3 h-3 rounded-sm flex-shrink-0 mr-2 shadow-sm border border-white/20"
                                                    style={{ backgroundColor: pipeline.color || '#3B82F6' }}
                                                  ></div>
                                                  <div className="flex-1 min-w-0">
                                                    <div className="text-xs font-medium text-gray-900 dark:text-white truncate group-hover:text-primary transition-colors">
                                                      {pipeline.name}
                                                    </div>
                                                    {pipeline.description && (
                                                      <div className="text-xs text-gray-500 dark:text-gray-400 truncate mt-0.5">
                                                        {pipeline.description}
                                                      </div>
                                                    )}
                                                  </div>
                                                  <div className="text-xs text-gray-400 ml-2 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
                                                    {pipeline.pipeline_type || 'Pipeline'}
                                                  </div>
                                                </div>
                                              </label>
                                            ))}
                                          </div>
                                        </div>
                                      </div>
                                    )}
                                    <div className="text-xs text-gray-500 dark:text-gray-400 mt-2 text-center">
                                      {getSelectedPipelineCount(userType.id)} of {pipelines.length} selected
                                    </div>
                                  </div>
                                </div>
                              )
                            }
                            
                            return (
                              <div key={`permission-${permission.id}-usertype-${userType.id}`} className="flex-1 min-w-32 px-4 py-4 border-l border-gray-200 dark:border-gray-600 flex items-center justify-center">
                                <div className="relative group">
                                  <button
                                    onClick={() => togglePermission(userType.name, permission.name)}
                                    disabled={isSystemProtected}
                                    className={`w-8 h-8 rounded-lg border-2 transition-all duration-200 flex items-center justify-center ${
                                      hasPermission
                                        ? 'bg-green-500 border-green-500 text-white shadow-md shadow-green-200 dark:shadow-green-900/30'
                                        : 'border-gray-300 dark:border-gray-600 hover:border-green-400 hover:shadow-md hover:shadow-green-100 dark:hover:shadow-green-900/20 bg-white dark:bg-gray-800'
                                    } ${
                                      isSystemProtected
                                        ? 'opacity-50 cursor-not-allowed'
                                        : 'cursor-pointer hover:scale-105 active:scale-95'
                                    } ${
                                      isCustomType && hasPermission
                                        ? 'ring-2 ring-blue-300 dark:ring-blue-600'
                                        : ''
                                    }`}
                                    title={
                                      isSystemProtected
                                        ? 'System permission - cannot be modified'
                                        : `${hasPermission ? 'Remove' : 'Grant'} ${permission.name} for ${userType.name}${isCustomType ? ' (Custom Role)' : ''}`
                                    }
                                  >
                                    {hasPermission && (
                                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                        <path fillRule="evenodd" d="M16.7 4.3a1 1 0 010 1.4l-8 8a1 1 0 01-1.4 0l-4-4a1 1 0 011.4-1.4L8 11.6l7.3-7.3a1 1 0 011.4 0z" clipRule="evenodd" />
                                      </svg>
                                    )}
                                  </button>
                                  
                                  {/* Custom role indicator */}
                                  {isCustomType && hasPermission && (
                                    <div className="absolute -top-1 -right-1 w-3 h-3 bg-blue-500 rounded-full border border-white dark:border-gray-800" 
                                         title="Custom Role"></div>
                                  )}
                                  
                                  {/* Tooltip on hover */}
                                  <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 text-xs bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 rounded opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
                                    {hasPermission ? 'Click to revoke' : 'Click to grant'}
                                  </div>
                                </div>
                              </div>
                            )
                          })}
                        </div>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </div>
            
            {/* Matrix Footer with Summary */}
            <div className="border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-750 px-6 py-3">
              <div className="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400">
                <div>
                  <strong>System Permissions:</strong> Showing {filteredPermissions.length} of {permissions.length} platform-wide permissions
                </div>
                <div className="flex items-center space-x-4">
                  <span>{userTypes.length} user types configured</span>
                  <span>•</span>
                  <span>{Object.keys(permissionsByCategory).length} permission categories</span>
                </div>
              </div>
            </div>
          </div>

        </div>
      )}


      {/* Field Controls Tab */}
      {activeTab === 'fields' && (
        <div className="space-y-6">
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden shadow-sm">
            <div className="border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-gray-50 to-gray-100 dark:from-gray-700 dark:to-gray-800 p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                    Field-Level Permission Controls
                  </h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                    Configure granular field visibility, editing permissions, and conditional access. Only showing pipelines accessible by at least one user type. <strong>Hierarchy:</strong> System → Pipeline → Field permissions.
                  </p>
                </div>
                <div className="flex items-center space-x-4">
                  {/* Pipeline selector */}
                  <select
                    value={selectedPipelineForFields || ''}
                    onChange={(e) => setSelectedPipelineForFields(Number(e.target.value) || null)}
                    className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white"
                  >
                    <option value="">Select Pipeline</option>
                    {getAccessiblePipelinesForFields().map((pipeline) => (
                      <option key={pipeline.id} value={pipeline.id}>
                        {pipeline.name}
                      </option>
                    ))}
                  </select>
                  {fieldLoading && (
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-primary"></div>
                  )}
                  <Settings className="w-5 h-5 text-blue-500" />
                </div>
              </div>
            </div>

            {getAccessiblePipelinesForFields().length === 0 ? (
              <div className="text-center py-12">
                <Lock className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                  No Accessible Pipelines
                </h4>
                <p className="text-gray-500 dark:text-gray-400 mb-4">
                  No pipelines are currently accessible by any user type. Grant pipeline access in System Permissions first.
                </p>
                <button 
                  onClick={() => setActiveTab('matrix')}
                  className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary hover:bg-primary/90 transition-colors"
                >
                  <Shield className="w-4 h-4 mr-2" />
                  Go to System Permissions
                </button>
              </div>
            ) : !selectedPipelineForFields ? (
              <div className="text-center py-12">
                <Settings className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                  Select a Pipeline
                </h4>
                <p className="text-gray-500 dark:text-gray-400">
                  Choose an accessible pipeline to configure field-level permissions for each user type.
                </p>
              </div>
            ) : pipelineFields.length === 0 && !fieldLoading ? (
              <div className="text-center py-12">
                <Database className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                  No Fields Found
                </h4>
                <p className="text-gray-500 dark:text-gray-400 mb-4">
                  This pipeline doesn't have any fields configured yet.
                </p>
                <a 
                  href={`/pipelines/${selectedPipelineForFields}`}
                  className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary hover:bg-primary/90 transition-colors"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Add Fields
                </a>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full">
                  <thead className="bg-gray-50 dark:bg-gray-700">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                        Field
                      </th>
                      {getUserTypesWithPipelineAccess(selectedPipelineForFields!).map((userType) => (
                        <th key={userType.id} className="px-6 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                          <div className="flex flex-col items-center">
                            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-medium mb-1 ${getRoleColor(userType.slug || userType.name.toLowerCase()).replace('bg-', 'bg-').replace('-100', '-500').replace('-900', '-600')}`}>
                              {userType.name.charAt(0)}
                            </div>
                            <span>{userType.name}</span>
                          </div>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                    {pipelineFields.map((field) => (
                      <tr key={field.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                        <td className="px-6 py-4">
                          <div className="flex items-start">
                            <div className="flex-1">
                              <div className="text-sm font-medium text-gray-900 dark:text-white">
                                {field.display_name || field.name}
                              </div>
                              <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                                {field.field_type} • {field.description || 'No description'}
                              </div>
                              {field.is_required && (
                                <div className="mt-1">
                                  <span className="inline-flex items-center px-2 py-0.5 text-xs bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 rounded">
                                    Required
                                  </span>
                                </div>
                              )}
                            </div>
                          </div>
                        </td>
                        {getUserTypesWithPipelineAccess(selectedPipelineForFields!).map((userType) => (
                          <td key={userType.id} className="px-6 py-4">
                            <div className="flex flex-col items-center space-y-3">
                              {/* View Permission */}
                              <div className="flex items-center space-x-2">
                                <button
                                  onClick={() => updateFieldPermission(
                                    userType.id, 
                                    selectedPipelineForFields!, 
                                    field.id, 
                                    'can_view', 
                                    !getFieldPermission(userType.id, selectedPipelineForFields!, field.id, 'can_view')
                                  )}
                                  className={`w-6 h-6 rounded border-2 transition-all duration-200 flex items-center justify-center ${
                                    getFieldPermission(userType.id, selectedPipelineForFields!, field.id, 'can_view')
                                      ? 'bg-blue-500 border-blue-500 text-white shadow-sm'
                                      : 'border-gray-300 dark:border-gray-600 hover:border-blue-400 bg-white dark:bg-gray-800'
                                  } cursor-pointer hover:scale-105 active:scale-95`}
                                  title={`${getFieldPermission(userType.id, selectedPipelineForFields!, field.id, 'can_view') ? 'Remove' : 'Grant'} view access`}
                                >
                                  {getFieldPermission(userType.id, selectedPipelineForFields!, field.id, 'can_view') && (
                                    <Eye className="w-3 h-3" />
                                  )}
                                </button>
                                <span className="text-xs text-gray-500 dark:text-gray-400">View</span>
                              </div>

                              {/* Edit Permission */}
                              <div className="flex items-center space-x-2">
                                <button
                                  onClick={() => updateFieldPermission(
                                    userType.id, 
                                    selectedPipelineForFields!, 
                                    field.id, 
                                    'can_edit', 
                                    !getFieldPermission(userType.id, selectedPipelineForFields!, field.id, 'can_edit')
                                  )}
                                  className={`w-6 h-6 rounded border-2 transition-all duration-200 flex items-center justify-center ${
                                    getFieldPermission(userType.id, selectedPipelineForFields!, field.id, 'can_edit')
                                      ? 'bg-green-500 border-green-500 text-white shadow-sm'
                                      : 'border-gray-300 dark:border-gray-600 hover:border-green-400 bg-white dark:bg-gray-800'
                                  } cursor-pointer hover:scale-105 active:scale-95`}
                                  title={`${getFieldPermission(userType.id, selectedPipelineForFields!, field.id, 'can_edit') ? 'Remove' : 'Grant'} edit access`}
                                >
                                  {getFieldPermission(userType.id, selectedPipelineForFields!, field.id, 'can_edit') && (
                                    <Edit className="w-3 h-3" />
                                  )}
                                </button>
                                <span className="text-xs text-gray-500 dark:text-gray-400">Edit</span>
                              </div>

                              {/* Visibility Level */}
                              <div className="flex flex-col items-center space-y-1">
                                <select
                                  value={getFieldPermission(userType.id, selectedPipelineForFields!, field.id, 'visibility')}
                                  onChange={(e) => updateFieldPermission(
                                    userType.id, 
                                    selectedPipelineForFields!, 
                                    field.id, 
                                    'visibility', 
                                    e.target.value
                                  )}
                                  className="text-xs px-2 py-1 border border-gray-300 dark:border-gray-600 rounded focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary dark:bg-gray-700 dark:text-white"
                                >
                                  <option value="visible">Visible</option>
                                  <option value="hidden">Hidden</option>
                                  <option value="readonly">Read Only</option>
                                  <option value="conditional">Conditional</option>
                                </select>
                                <span className="text-xs text-gray-500 dark:text-gray-400">Visibility</span>
                              </div>
                            </div>
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            
            {/* Field permissions footer */}
            {selectedPipelineForFields && pipelineFields.length > 0 && (
              <div className="border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-750 px-6 py-3">
                <div className="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400">
                  <div>
                    <strong>Field Controls:</strong> Showing {pipelineFields.length} field{pipelineFields.length !== 1 ? 's' : ''} • {getUserTypesWithPipelineAccess(selectedPipelineForFields!).length}/{userTypes.length} user type{getUserTypesWithPipelineAccess(selectedPipelineForFields!).length !== 1 ? 's' : ''} with access
                  </div>
                  <div className="flex items-center space-x-6">
                    <div className="flex items-center space-x-1">
                      <Eye className="w-3 h-3 text-blue-500" />
                      <span>View</span>
                    </div>
                    <div className="flex items-center space-x-1">
                      <Edit className="w-3 h-3 text-green-500" />
                      <span>Edit</span>
                    </div>
                    <div className="flex items-center space-x-1">
                      <Settings className="w-3 h-3 text-gray-500" />
                      <span>Visibility</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* User Roles Tab */}
      {activeTab === 'roles' && (
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              User Roles
            </h3>
            <button 
              onClick={handleCreateUserType}
              className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary hover:bg-primary/90"
            >
              <Plus className="w-4 h-4 mr-2" />
              Add Role
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {userTypes.map((userType) => (
              <div key={userType.id} className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h4 className="text-lg font-semibold text-gray-900 dark:text-white">
                      {userType.name}
                    </h4>
                    <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getRoleColor(userType.slug || userType.name.toLowerCase())}`}>
                      {userType.slug || userType.name.toLowerCase()}
                    </span>
                  </div>
                  <div className="flex space-x-2">
                    <button 
                      onClick={() => handleEditUserType(userType)}
                      className="text-gray-400 hover:text-gray-500 dark:hover:text-gray-300 p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700"
                      title="Edit user type"
                    >
                      <Edit className="w-4 h-4" />
                    </button>
                    <button 
                      onClick={() => handleDeleteUserType(userType)}
                      className="text-gray-400 hover:text-red-500 p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700"
                      title="Delete user type"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                  {userType.description}
                </p>

                <div className="space-y-2">
                  <div className="text-sm font-medium text-gray-900 dark:text-white">
                    Permissions ({Object.keys(userType.base_permissions || {}).length})
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {Object.entries(userType.base_permissions || {}).slice(0, 3).map(([category, actions]) => (
                      <span key={category} className="inline-flex px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded">
                        {category}
                      </span>
                    ))}
                    {Object.keys(userType.base_permissions || {}).length > 3 && (
                      <span className="inline-flex px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded">
                        +{Object.keys(userType.base_permissions || {}).length - 3} more
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}


      {/* User Type Modal */}
      <UserTypeModal
        isOpen={showUserTypeModal}
        onClose={() => setShowUserTypeModal(false)}
        onSuccess={handleUserTypeSuccess}
        userType={selectedUserType}
        mode={userTypeModalMode}
      />

      {/* Delete User Type Modal */}
      <DeleteUserTypeModal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        onSuccess={handleUserTypeSuccess}
        userType={selectedUserType}
      />
    </div>
  )
}