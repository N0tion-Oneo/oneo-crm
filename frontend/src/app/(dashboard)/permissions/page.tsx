'use client'

import React, { useState, useEffect, memo, useCallback } from 'react'
import { Shield, Users, Database, Settings, Eye, Edit, Trash2, Plus, ChevronDown, ChevronRight, Filter, Search, Grid3X3, List, Lock, Info, Workflow, FileText, BarChart3, LayoutDashboard, Key, Circle } from 'lucide-react'
import { useAuth } from '@/features/auth/context'
import { api } from '@/lib/api'
import UserTypeModal from '@/components/user-types/UserTypeModal'
import DeleteUserTypeModal from '@/components/user-types/DeleteUserTypeModal'
import { usePermissionSchema } from '@/hooks/use-permission-schema'
import { PermissionGuard } from '@/components/permissions/PermissionGuard'
import DependencyWarning from '@/components/permissions/DependencyWarning'
import PermissionCheckbox from '@/components/permissions/PermissionCheckbox'
import { 
  getPermissionState
} from '@/utils/permission-dependencies'

interface Permission {
  id: number
  name: string
  description: string
  category: string
  action: string
  is_system: boolean
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

// Helper function to get icon component for resource types
const getResourceTypeIcon = (iconName: string) => {
  const iconMap: Record<string, any> = {
    'database': Database,
    'workflow': Workflow,
    'file-text': FileText,
    'bar-chart-3': BarChart3,
    'layout-dashboard': LayoutDashboard,
    'key': Key,
    'circle': Circle,
  }
  return iconMap[iconName] || Circle
}

export default function PermissionsPage() {
  const { user } = useAuth()
  const { 
    frontendConfig, 
    loading: schemaLoading, 
    error: schemaError,
    getCategoryActions,
    getCategoryColor,
    getActionIcon,
    getActionDescription,
    getDynamicResources,
    refreshAll
  } = usePermissionSchema()


  
  const [userTypes, setUserTypes] = useState<UserType[]>([])
  const [pipelines, setPipelines] = useState<Pipeline[]>([])
  const [pipelinePermissions, setPipelinePermissions] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'matrix' | 'pipeline-access' | 'roles'>('matrix')
  const [ongoingPermissionChanges, setOngoingPermissionChanges] = useState<Set<string>>(new Set())
  
  // UI state
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(['system', 'users', 'pipelines']))
  
  // Modal states
  const [showUserTypeModal, setShowUserTypeModal] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [selectedUserType, setSelectedUserType] = useState<UserType | null>(null)
  const [userTypeModalMode, setUserTypeModalMode] = useState<'create' | 'edit'>('create')

  // Load local data that's not handled by usePermissionSchema hook
  useEffect(() => {
    const loadLocalData = async () => {
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
        
        setUserTypes(userTypesData)
        setPipelines(pipelinesData)
        setPipelinePermissions(pipelinePermissionsData)

        // Debug logging for pipeline permissions
        console.log('🔍 Pipeline permissions loaded:', pipelinePermissionsData)
        console.log('👤 Manager permissions:', pipelinePermissionsData.filter((p: any) => p.user_type === 2))
        console.log('📊 Total permissions loaded:', pipelinePermissionsData.length)

      } catch (error) {
        console.error('Failed to load local permissions data:', error)
      } finally {
        setLoading(false)
      }
    }

    loadLocalData()
  }, []) // Remove frontendConfig dependency to break the cascade

  // Helper functions
  const hasPipelineAccess = (userTypeId: number, pipelineId: number): boolean => {
    const hasAccess = pipelinePermissions.some(
      perm => perm.user_type === userTypeId && perm.pipeline_id === pipelineId
    )
    
    // Debug logging for Manager
    if (userTypeId === 2) {
      console.log(`🔍 hasPipelineAccess(${userTypeId}, ${pipelineId}):`, hasAccess)
      console.log('Available permissions:', pipelinePermissions.filter(p => p.user_type === userTypeId))
    }
    
    return hasAccess
  }


  const togglePipelineAccess = async (userTypeId: number, pipelineId: number, hasAccess: boolean) => {
    const userType = userTypes.find(ut => ut.id === userTypeId)
    const pipeline = pipelines.find(p => p.id === pipelineId)
    if (!userType || !pipeline) return

    // Create unique key for this dynamic permission change
    const changeKey = `dynamic-pipelines-${userTypeId}-${pipelineId}`
    
    // Prevent multiple simultaneous calls for the same permission
    if (ongoingPermissionChanges.has(changeKey)) {
      console.log(`🚫 Ignoring duplicate dynamic permission change for ${changeKey}`)
      return
    }

    // Mark this permission change as ongoing
    setOngoingPermissionChanges(prev => new Set([...prev, changeKey]))

    try {
      if (hasAccess) {
        // Grant access - Create new permission using standard REST endpoint
        const response = await api.post('/auth/user-type-pipeline-permissions/', {
          user_type: userTypeId,
          pipeline_id: pipelineId,
          permissions: ['read'],
          access_level: 'read'
        })
        
        // Update local state
        setPipelinePermissions(prev => [...prev, response.data])
      } else {
        // Revoke access - Find and delete existing permission using standard REST endpoint
        const existingPermission = pipelinePermissions.find(
          perm => perm.user_type === userTypeId && perm.pipeline_id === pipelineId
        )
        
        if (existingPermission) {
          await api.delete(`/auth/user-type-pipeline-permissions/${existingPermission.id}/`)
          
          // Update local state
          setPipelinePermissions(prev => 
            prev.filter(perm => perm.id !== existingPermission.id)
          )
        } else {
          throw new Error(`No permission found for UserType ${userTypeId} and Pipeline ${pipelineId}`)
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
    } finally {
      // Remove from ongoing changes
      setOngoingPermissionChanges(prev => {
        const newSet = new Set(prev)
        newSet.delete(changeKey)
        return newSet
      })
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

    // Check current state - use the same logic as individual toggles
    const allGranted = categoryPermissions.every(permission => 
      permissionMatrix[userTypeName]?.[permission.name] === true
    )
    const newValue = !allGranted // Toggle: All->None, Some->All, None->All
    
    console.log(`🔄 Category toggle: ${category} for ${userTypeName} → ${newValue ? 'Grant All' : 'Revoke All'}`)

    // Disable WebSocket refresh during category operation to prevent interference
    // disableWebSocketRefreshTemporarily(5000) // 5 seconds - function removed

    try {
      // Process each permission individually using EXACT same logic as togglePermission
      for (const permission of categoryPermissions) {
        const [schemaCategory, action] = permission.name.split(':')
        
        if (!schemaCategory || !action) {
          console.warn(`Invalid permission format: ${permission.name}`)
          continue
        }

        try {
          console.log(`📤 ${newValue ? 'Adding' : 'Removing'} ${permission.name}`)
          
          // Use IDENTICAL API calls as individual toggles
          let response
          if (newValue) {
            response = await api.post(`/auth/user-types/${userType.id}/add_permission/`, {
              category: schemaCategory,
              action
            })
          } else {
            response = await api.post(`/auth/user-types/${userType.id}/remove_permission/`, {
              category: schemaCategory,
              action
            })
          }
          
          // Update state after each API call (like individual toggles)
          if (response.data && response.data.base_permissions) {
            setUserTypes(prev => prev.map(ut => {
              if (ut.id === userType.id) {
                return { ...ut, base_permissions: response.data.base_permissions }
              }
              return ut
            }))
          }
          
          console.log(`✅ ${permission.name} ${newValue ? 'added' : 'removed'}`)
        } catch (error: any) {
          console.error(`Failed to ${newValue ? 'add' : 'remove'} ${permission.name}:`, error?.response?.data)
        }
      }
      
      showNotification(`${newValue ? 'Granted' : 'Revoked'} all ${category} permissions for ${userTypeName}`, 'success')
    } catch (error: any) {
      console.error('Category toggle error:', error)
      showNotification(`Failed to update ${category} permissions for ${userTypeName}`, 'error')
    }
  }

  // Generate ONLY static permissions for the matrix (dynamic permissions go to resource access tabs)
  const permissions = React.useMemo(() => {
    if (!frontendConfig?.categories) return []
    
    const staticPermissions: Permission[] = []
    
    Object.entries(frontendConfig.categories).forEach(([categoryKey, categoryData]) => {
      // Skip dynamic permissions - they are handled in resource access tabs
      if (categoryData.is_dynamic) {
        console.log(`⏩ Skipping dynamic permission category: ${categoryKey}`)
        return
      }
      
      const categoryName = categoryData.category_display || categoryKey.charAt(0).toUpperCase() + categoryKey.slice(1)
      
      categoryData.actions.forEach((action: string) => {
        staticPermissions.push({
          id: staticPermissions.length + 1,
          name: `${categoryKey}:${action}`,
          description: `${action.charAt(0).toUpperCase() + action.slice(1)} ${categoryName.toLowerCase()}`,
          category: categoryName,
          action: action,
          is_system: categoryKey === 'system'
        })
      })
    })
    
    console.log(`📊 Generated ${staticPermissions.length} static permissions for matrix view`)
    return staticPermissions
  }, [frontendConfig])
  
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
  
  // Generate permission matrix from user types (eliminates local matrix state)
  // Memoized to prevent re-computation unless userTypes actually change
  const permissionMatrix = React.useMemo(() => {
    const matrix: PermissionMatrix = {}
    
    userTypes.forEach(userType => {
      matrix[userType.name] = {}
      
      // Convert userType.base_permissions object to permission matrix format
      Object.entries(userType.base_permissions || {}).forEach(([category, actions]) => {
        if (Array.isArray(actions)) {
          actions.forEach(action => {
            const permissionName = `${category}:${action}`
            matrix[userType.name][permissionName] = true
          })
        }
      })
    })
    
    console.log(`🔑 Permission matrix recalculated:`, userTypes.map(ut => ({
      name: ut.name,
      permissionCount: Object.keys(matrix[ut.name] || {}).length,
      hasUserManagement: Object.keys(matrix[ut.name] || {}).filter(p => p.startsWith('users:')).length
    })))
    
    return matrix
  }, [userTypes])
  
  // Debug logging for permissions
  React.useEffect(() => {
    console.log('🗂️ Permissions by category:', Object.keys(permissionsByCategory).map(cat => ({
      category: cat,
      count: permissionsByCategory[cat].length,
      samplePermissions: permissionsByCategory[cat].slice(0, 3).map(p => p.name)
    })))
    
    console.log('👤 User types with permissions:', userTypes.map(ut => ({
      name: ut.name,
      hasBasePermissions: !!ut.base_permissions,
      permissionCount: Object.keys(ut.base_permissions || {}).length,
      samplePermissions: Object.entries(ut.base_permissions || {}).slice(0, 2)
    })))
    
    console.log('🔑 Generated permission matrix:', Object.keys(permissionMatrix).map(userType => ({
      userType,
      permissionCount: Object.keys(permissionMatrix[userType]).length,
      samplePermissions: Object.entries(permissionMatrix[userType]).slice(0, 3)
    })))
    
    console.log('🎨 UI Debug - Should be rendering BUTTONS not checkboxes!')
    console.log('🎯 Frontend config:', !!frontendConfig)
    console.log('🎯 Permissions count:', permissions.length)
    console.log('🎯 User types count:', userTypes.length)
  }, [permissionsByCategory, userTypes, permissionMatrix, frontendConfig, permissions])

  const togglePermission = async (userTypeName: string, category: string, action: string, permissionName: string) => {
    const userType = userTypes.find(ut => ut.name === userTypeName)
    if (!userType) return

    // Create unique key for this permission change
    const changeKey = `${userType.id}-${category}-${action}`
    
    // Prevent multiple simultaneous calls for the same permission
    if (ongoingPermissionChanges.has(changeKey)) {
      console.log(`🚫 Ignoring duplicate permission change for ${changeKey}`)
      return
    }

    // Get current value from backend data, not UI state
    const currentPermissions = userType.base_permissions?.[category] || []
    const currentValue = currentPermissions.includes(action)
    const newValue = !currentValue
    
    console.log(`🔄 Permission toggle:`, {
      userType: userTypeName,
      category,
      action,
      currentValue,
      newValue,
      currentPermissions
    })
    
    // Check if this is a system default type and we're trying to remove critical permissions
    if (userType.is_system_default && !newValue && userType.slug === 'admin' && category === 'system' && action === 'full_access') {
      alert('Cannot remove full system access from Admin user type')
      return
    }
    
    // Mark this permission change as ongoing
    setOngoingPermissionChanges(prev => new Set([...prev, changeKey]))
    
    // Show loading state
    const permissionButton = document.querySelector(`[data-permission-toggle="${changeKey}"]`)
    if (permissionButton) {
      permissionButton.classList.add('opacity-50', 'cursor-wait')
    }

    try {
      // Make API call FIRST
      // Make API call first - NO optimistic updates
      let response
      if (newValue) {
        response = await api.post(`/auth/user-types/${userType.id}/add_permission/`, {
          category,
          action
        })
      } else {
        response = await api.post(`/auth/user-types/${userType.id}/remove_permission/`, {
          category,
          action
        })
      }
      
      console.log(`📡 API Response:`, response.data)
      
      // Only update UI if API call succeeded and returned updated data
      if (response.data && response.data.base_permissions) {
        console.log(`✅ Backend confirmed permission change - updating UI`)
        
        // Update the specific user type with the data returned from backend
        setUserTypes(prev => prev.map(ut => {
          if (ut.id === userType.id) {
            console.log(`✅ Updating ${ut.name} with backend response:`, response.data.base_permissions)
            return { ...ut, base_permissions: response.data.base_permissions }
          }
          return ut
        }))
        
        // Only show success toast after confirmed backend update
        const actionText = newValue ? 'granted' : 'revoked'
        showNotification(`Permission ${actionText}: ${permissionName} for ${userTypeName}`, 'success')
        console.log(`✅ ${newValue ? 'Added' : 'Removed'} ${category}:${action} for ${userTypeName}`)
      } else {
        console.warn('API response missing expected base_permissions data:', response.data)
        showNotification(`Warning: Permission change may not have been saved properly`, 'error')
      }
      
    } catch (error: any) {
      console.error('Failed to update permission:', error)
      
      // Log detailed error information for debugging
      console.error('Individual permission update error details:', {
        userType: userType?.name,
        userTypeId: userType?.id,
        category,
        action,
        permissionName,
        currentValue,
        newValue,
        errorResponse: error?.response?.data,
        status: error?.response?.status,
        url: error?.config?.url,
        requestData: error?.config?.data
      })
      
      // Show user-friendly error
      let errorMessage = 'Failed to update permission'
      if (error.response?.data?.error) {
        errorMessage = error.response.data.error
      } else if (error.response?.status === 403) {
        errorMessage = 'You do not have permission to modify user type permissions'
      } else if (error.response?.status === 400) {
        errorMessage = error.response.data?.detail || 'Invalid permission configuration'
      }
      
      showNotification(`Error: ${errorMessage}`, 'error')
    } finally {
      // Remove loading state
      if (permissionButton) {
        permissionButton.classList.remove('opacity-50', 'cursor-wait')
      }
      
      // Remove from ongoing changes
      setOngoingPermissionChanges(prev => {
        const newSet = new Set(prev)
        newSet.delete(changeKey)
        return newSet
      })
      
      // Permission change completed - visual state already updated
    }
  }

  // Helper function for notifications
  const showNotification = (message: string, type: 'success' | 'error') => {
    const notification = document.createElement('div')
    const bgColor = type === 'success' ? 'bg-green-500' : 'bg-red-500'
    notification.className = `fixed top-4 right-4 ${bgColor} text-white px-4 py-2 rounded-md shadow-lg z-50`
    notification.textContent = message
    document.body.appendChild(notification)
    
    setTimeout(() => {
      if (document.body.contains(notification)) {
        document.body.removeChild(notification)
      }
    }, type === 'error' ? 5000 : 3000)
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

  const handleUserTypeSuccess = async () => {
    // Reload data to reflect changes
    try {
      setLoading(true)
      
      // Use the main schema refresh to ensure consistency
      await refreshAll()
      
      // Reload the local data
      const [userTypesResponse, pipelinesResponse, pipelinePermissionsResponse] = await Promise.all([
        api.get('/auth/user-types/'),
        api.get('/api/pipelines/').catch(() => ({ data: { results: [] } })),
        api.get('/auth/user-type-pipeline-permissions/').catch(() => ({ data: { results: [] } }))
      ])

      const userTypesData = userTypesResponse.data.results || userTypesResponse.data || []
      const pipelinesData = pipelinesResponse.data.results || pipelinesResponse.data || []
      const pipelinePermissionsData = pipelinePermissionsResponse.data.results || pipelinePermissionsResponse.data || []
      
      setUserTypes(userTypesData)
      setPipelines(pipelinesData)
      setPipelinePermissions(pipelinePermissionsData)
      
    } catch (error) {
      console.error('Failed to reload data after user type change:', error)
    } finally {
      setLoading(false)
    }
  }

  // Enhanced icon mapping using fallback logic (category_icons not available in backend yet)
  const getPermissionIcon = (category: string) => {
    // Fallback to existing logic (backend category_icons not implemented yet)
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

  if (schemaError) {
    return (
      <div className="p-6">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800 dark:text-red-200">
                Permission Schema Error
              </h3>
              <div className="mt-2 text-sm text-red-700 dark:text-red-300">
                <p>{schemaError}</p>
              </div>
              <div className="mt-4">
                <button
                  type="button"
                  onClick={refreshAll}
                  className="bg-red-100 dark:bg-red-800/50 hover:bg-red-200 dark:hover:bg-red-800/70 text-red-800 dark:text-red-200 px-3 py-2 rounded-md text-sm font-medium"
                >
                  Retry
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (loading || schemaLoading) {
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
    <PermissionGuard 
      category="permissions" 
      action="read"
      fallback={
        <div className="p-6">
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6 text-center">
            <Shield className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-red-900 dark:text-red-200 mb-2">
              Access Denied
            </h3>
            <p className="text-red-700 dark:text-red-300">
              You don't have permission to view the permissions management page. 
              Contact your administrator to request access.
            </p>
          </div>
        </div>
      }
    >
      <div className="p-6">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              Permissions
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mt-2">
              Manage user permissions across the platform. <strong>Static Permissions</strong> control system-wide access to features, while <strong>Resource Access</strong> tabs control access to specific resources (pipelines, workflows, etc.).
            </p>
          </div>
        </div>
      </div>



      {/* Tabs */}
      <div className="mb-6">
        <nav className="flex space-x-8 border-b border-gray-200 dark:border-gray-700">
          {(() => {
            // Generate tabs for static permissions and dynamic resource access
            const resourceTabs = Object.entries(frontendConfig?.grouped_categories || {})
              .filter(([resourceType, metadata]) => {
                // Count only dynamic permissions for resource access tabs
                const dynamicCount = metadata.items?.filter(item => item.data?.is_dynamic)?.length || 0
                return dynamicCount > 0 || ['pipelines', 'workflows'].includes(resourceType)
              })
              .map(([resourceType, metadata]) => {
                // Count only dynamic permissions, not static ones
                const dynamicCount = metadata.items?.filter(item => item.data?.is_dynamic)?.length || 0
                return {
                  id: `${resourceType}-access`,
                  name: `${resourceType.charAt(0).toUpperCase() + resourceType.slice(1)} Access`,
                  icon: getResourceTypeIcon('database'),
                  count: dynamicCount
                }
              })

            const allTabs = [
              { id: 'matrix', name: 'Static Permissions', icon: Shield, count: permissions.length },
              ...resourceTabs,
              { id: 'roles', name: 'User Roles', icon: Users, count: userTypes.length },
            ]

            console.log(`🏷️ Generated tabs:`, allTabs.map(t => `${t.name} (${t.count})`))
            console.log(`📊 Tab counts: Static permissions = ${permissions.length}, Dynamic permissions only for resource tabs`)
            return allTabs
          })().map((tab) => (
            <button
              type="button"
              key={tab.id}
              onClick={(e) => {
                e.preventDefault()
                e.stopPropagation()
                setActiveTab(tab.id as any)
              }}
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
                <div className="flex items-center">
                  <div className="w-4 h-4 bg-gray-100 border border-gray-200 rounded opacity-30 mr-2 flex items-center justify-center">
                    <Lock className="w-2 h-2 text-gray-400" />
                  </div>
                  <span className="text-gray-600 dark:text-gray-400">Requires Static Permission</span>
                </div>
              </div>
            </div>
          </div>

          {/* Enhanced Permission Matrix */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden shadow-sm">
            {/* Controls Header */}
            <div className="border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-gray-50 to-gray-100 dark:from-gray-700 dark:to-gray-800 px-6 py-4">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
                  Static Permissions Matrix
                </h4>
                <div className="flex items-center space-x-2">
                  <button 
                    type="button"
                    onClick={expandAllCategories}
                    className="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 px-2 py-1 rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                  >
                    Expand All
                  </button>
                  <button 
                    type="button"
                    onClick={collapseAllCategories}
                    className="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 px-2 py-1 rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                  >
                    Collapse All
                  </button>
                </div>
              </div>
            </div>

            {/* Permission Matrix Table */}
            <div className="overflow-x-auto">
              <table className="w-full">
                {/* Table Header */}
                <thead className="bg-gradient-to-r from-gray-50 to-gray-100 dark:from-gray-700 dark:to-gray-800 sticky top-0 z-10">
                  <tr>
                    <th className="px-6 py-4 text-left border-r border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 sticky left-0 z-20 w-72">
                      <div className="text-sm font-semibold text-gray-900 dark:text-white">
                        Permissions
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        {filteredPermissions.length} total
                      </div>
                    </th>
                    {userTypes.map((userType) => (
                      <th key={userType.id} className="px-3 py-4 text-center border-l border-gray-200 dark:border-gray-600 w-24">
                        <div className="flex flex-col items-center space-y-2">
                          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-medium ${getRoleColor(userType.slug || userType.name.toLowerCase()).replace('bg-', 'bg-').replace('-100', '-500').replace('-900', '-600')}`}>
                            {userType.name.charAt(0)}
                          </div>
                          <div className="text-sm font-medium text-gray-900 dark:text-white">
                            {userType.name}
                          </div>
                          <div className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getRoleColor(userType.slug || userType.name.toLowerCase())}`}>
                            {userType.slug || userType.name.toLowerCase()}
                          </div>
                          <div className="text-xs text-gray-500 dark:text-gray-400">
                            {userType.user_count || 0} users
                          </div>
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>

                {/* Table Body */}
                <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  {Object.entries(permissionsByCategory).map(([category, categoryPermissions]) => (
                    <React.Fragment key={`category-group-${category}`}>
                      {/* Category Header Row */}
                      <tr className="bg-gray-50 dark:bg-gray-700/50 border-t border-gray-200 dark:border-gray-600">
                        <td className="px-6 py-3 border-r border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 sticky left-0 z-10 w-72">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.preventDefault()
                              e.stopPropagation()
                              toggleCategory(category)
                            }}
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
                        </td>
                        
                        {/* Category-level bulk actions */}
                        {userTypes.map((userType) => {
                          const allGranted = categoryPermissions.every(permission => 
                            permissionMatrix[userType.name]?.[permission.name] === true
                          )
                          const someGranted = categoryPermissions.some(permission => 
                            permissionMatrix[userType.name]?.[permission.name] === true
                          )
                          
                          return (
                            <td key={userType.id} className="px-3 py-3 text-center border-l border-gray-200 dark:border-gray-600 w-24">
                              <button 
                                type="button"
                                onClick={(e) => {
                                  e.preventDefault()
                                  e.stopPropagation()
                                  toggleCategoryPermissions(category, userType.name)
                                }}
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
                            </td>
                          )
                        })}
                      </tr>
                      
                      {/* Permission rows for this category - only show if expanded */}
                      {expandedCategories.has(category) && categoryPermissions.map((permission, index) => (
                        <tr key={`permission-${permission.id}`} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                          <td className="px-6 py-4 border-r border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 sticky left-0 z-10 w-72">
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
                          </td>
                          
                          {userTypes.map((userType) => {
                            const hasPermission = permissionMatrix[userType.name]?.[permission.name]
                            
                            // Check if current user can modify permissions for this user type
                            const currentUserPermissions = user?.permissions || user?.userType?.basePermissions || {}
                            const canModifyPermissions = 
                              currentUserPermissions.permissions?.includes('grant') || 
                              currentUserPermissions.permissions?.includes('revoke') ||
                              currentUserPermissions.permissions?.includes('update')
                            

                            
                            // System permissions are protected unless user has permission management rights
                            const isSystemProtected = permission.is_system && !canModifyPermissions
                            const isCustomType = userType.is_custom
                            
                            // Special handling for "Access Pipelines" permission - show multiselect instead of checkbox
                            if (permission.name === 'Access Pipelines') {
                              return (
                                <td key={`permission-${permission.id}-usertype-${userType.id}`} className="px-3 py-4 text-center border-l border-gray-200 dark:border-gray-600 w-24">
                                  <div className="w-full">
                                    {pipelines.length === 0 ? (
                                      <div className="text-center">
                                        <div className="text-xs text-gray-400 mb-2">No pipelines</div>
                                        <button 
                                          type="button"
                                          onClick={() => window.location.href = "/pipelines"}
                                          className="text-xs text-blue-600 hover:text-blue-700 underline cursor-pointer bg-transparent border-none"
                                        >
                                          Create Pipeline
                                        </button>
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
                                </td>
                              )
                            }
                            
                            // Calculate schema category once to avoid repetition
                            const schemaCategory = Object.keys(frontendConfig?.categories || {}).find(key => {
                              const categoryData = frontendConfig?.categories?.[key]
                              const displayName = categoryData?.category_display || key.charAt(0).toUpperCase() + key.slice(1)
                              return permission.category === displayName
                            }) || 'unknown'
                            
                            // Extract action from permission name for consistent changeKey
                            const [, extractedAction] = permission.name.split(':')
                            const changeKey = `${userType.id}-${schemaCategory}-${extractedAction}`
                            
                            // Get dynamic color for this category from backend
                            const categoryColor = getCategoryColor(schemaCategory) || '#64748b'
                            const actionIcon = getActionIcon(extractedAction || 'circle')
                            
                            return (
                              <td key={`permission-${permission.id}-usertype-${userType.id}`} className="px-3 py-4 border-l border-gray-200 dark:border-gray-600 w-24">
                                <div className="flex items-center justify-center">
                                  <div className="relative group">
                                  <button
                                    type="button"
                                    onClick={(e) => {
                                      e.preventDefault()
                                      e.stopPropagation()
                                      
                                      if (schemaCategory !== 'unknown') {
                                        // Extract action from permission name (format: "category:action")
                                        const [, action] = permission.name.split(':')
                                        if (action) {
                                          togglePermission(userType.name, schemaCategory, action, permission.name)
                                        } else {
                                          console.warn(`Could not extract action from permission name: ${permission.name}`)
                                        }
                                      } else {
                                        console.warn(`Could not find schema category for permission: ${permission.name}`)
                                      }
                                    }}
                                    data-permission-toggle={changeKey}
                                    disabled={isSystemProtected || ongoingPermissionChanges.has(changeKey)}
                                    style={hasPermission && !ongoingPermissionChanges.has(changeKey) ? {
                                      backgroundColor: categoryColor,
                                      borderColor: categoryColor,
                                      boxShadow: `0 4px 6px -1px ${categoryColor}20, 0 2px 4px -1px ${categoryColor}10`
                                    } : {}}
                                    className={`w-8 h-8 rounded-lg border-2 transition-all duration-150 flex items-center justify-center ${
                                      ongoingPermissionChanges.has(changeKey)
                                        ? 'bg-blue-500 border-blue-500 text-white animate-pulse'
                                        : hasPermission
                                        ? 'text-white shadow-md'
                                        : 'border-gray-300 dark:border-gray-600 hover:shadow-md bg-white dark:bg-gray-800'
                                    } ${
                                      isSystemProtected || ongoingPermissionChanges.has(changeKey)
                                        ? 'opacity-50 cursor-not-allowed'
                                        : 'cursor-pointer hover:scale-105 active:scale-95'
                                    } ${
                                      isCustomType && hasPermission && !ongoingPermissionChanges.has(changeKey)
                                        ? 'ring-2 ring-blue-300 dark:ring-blue-600'
                                        : ''
                                    }`}
                                    title={
                                      isSystemProtected
                                        ? 'System permission - cannot be modified'
                                        : `${hasPermission ? 'Remove' : 'Grant'} ${permission.name} for ${userType.name}${isCustomType ? ' (Custom Role)' : ''}`
                                    }
                                  >
                                    {ongoingPermissionChanges.has(changeKey) ? (
                                      <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                        <path className="opacity-75" fill="currentColor" d="m4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                      </svg>
                                    ) : hasPermission ? (
                                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                        <path fillRule="evenodd" d="M16.7 4.3a1 1 0 010 1.4l-8 8a1 1 0 01-1.4 0l-4-4a1 1 0 011.4-1.4L8 11.6l7.3-7.3a1 1 0 011.4 0z" clipRule="evenodd" />
                                      </svg>
                                    ) : null}
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
                              </td>
                            )
                          })}
                        </tr>
                      ))}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
            </div>
            
            {/* Enhanced Matrix Footer with Rich Data Summary */}
            <div className="border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/50 px-6 py-3">
              <div className="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400">
                <div>
                  <strong>Static Permissions:</strong> Showing {filteredPermissions.length} of {permissions.length} platform-wide permissions
                  {frontendConfig?.frontend_helpers && (
                    <span className="ml-2 inline-flex items-center px-2 py-1 text-xs bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 rounded-full">
                      <Circle className="w-3 h-3 mr-1" />
                      Enhanced UI Active
                    </span>
                  )}
                </div>
                <div className="flex items-center space-x-4">
                  <span>{userTypes.length} user types configured</span>
                  <span>•</span>
                  <span>{Object.keys(permissionsByCategory).length} permission categories</span>
                  {frontendConfig?.bulk_operation_templates && (
                    <>
                      <span>•</span>
                      <span className="text-blue-600 dark:text-blue-400">
                        {Object.keys(frontendConfig.bulk_operation_templates).length} bulk operations available
                      </span>
                    </>
                  )}
                  {frontendConfig?.frontend_helpers?.action_icons && (
                    <>
                      <span>•</span>
                      <span className="text-purple-600 dark:text-purple-400">
                        {Object.keys(frontendConfig.frontend_helpers.action_icons).length} action icons
                      </span>
                    </>
                  )}
                </div>
              </div>
              
              {/* Rich Data Indicators */}
              {frontendConfig?.frontend_helpers && (
                <div className="flex items-center justify-center mt-2 pt-2 border-t border-gray-200 dark:border-gray-600">
                  <div className="flex items-center space-x-6 text-xs">
                    <div className="flex items-center text-green-600 dark:text-green-400">
                      <div className="w-2 h-2 bg-green-500 rounded-full mr-1"></div>
                      Dynamic Colors Active
                    </div>
                    <div className="flex items-center text-blue-600 dark:text-blue-400">
                      <div className="w-2 h-2 bg-blue-500 rounded-full mr-1"></div>
                      Backend Data Connected
                    </div>
                    <div className="flex items-center text-purple-600 dark:text-purple-400">
                      <div className="w-2 h-2 bg-purple-500 rounded-full mr-1"></div>
                      Advanced Features Enabled
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

        </div>
      )}

      {/* Resource Access Tabs (Pipeline, Workflow, Form, etc.) */}
      {activeTab.endsWith('-access') && (() => {
        const resourceType = activeTab.replace('-access', '')
        const resourceMetadata = frontendConfig?.grouped_categories?.[resourceType]
        const ResourceIcon = Database
        const resourceDisplayName = resourceType.charAt(0).toUpperCase() + resourceType.slice(1) + ' Access'
        const dynamicResourceCount = resourceMetadata?.items?.filter(item => item.data?.is_dynamic)?.length || 0
        
        // Use dynamic permissions from backend config
        const dynamicItems = resourceMetadata?.items?.filter(item => item.data?.is_dynamic) || []
        const hasData = dynamicItems.length > 0
        const items = dynamicItems.map(item => ({
          id: item.data?.resource_id,
          name: item.data?.metadata?.pipeline_name || item.data?.category_display || item.key,
          description: item.data?.description || '',
          color: '#3B82F6', // Default blue
          // Convert backend dynamic item to frontend format
          ...item.data?.metadata
        }))
        
        console.log(`🎯 Resource Tab: ${resourceType}`)
        console.log(`   Metadata:`, resourceMetadata)
        console.log(`   Total items: ${resourceMetadata?.items?.length || 0}`)
        console.log(`   Dynamic items: ${dynamicItems.length}`)
        console.log(`   Processed items:`, items)
        console.log(`   Has data: ${hasData}`)
        
        return (
          <div className="space-y-6">
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden shadow-sm">
              <div className="border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-gray-50 to-gray-100 dark:from-gray-700 dark:to-gray-800 p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                      {resourceDisplayName} Management
                    </h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                      Control access to specific {resourceType} resources. This manages <strong>dynamic permissions</strong> - individual resource access. Users must first have static "{resourceType}" permissions, then specific resource access.
                    </p>
                  </div>
                  <ResourceIcon className="w-5 h-5 text-blue-500" />
                </div>
              </div>

              {!hasData ? (
                <div className="text-center py-12">
                  <ResourceIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                    No {resourceType.charAt(0).toUpperCase() + resourceType.slice(1)} Available
                  </h4>
                  <p className="text-gray-500 dark:text-gray-400 mb-4">
                    Create {resourceType} first to manage access permissions.
                  </p>
                  {resourceType === 'pipelines' && (
                    <button 
                      type="button"
                      onClick={() => window.location.href = "/pipelines"}
                      className="text-xs text-blue-600 hover:text-blue-700 underline cursor-pointer bg-transparent border-none"
                    >
                      Create Pipeline
                    </button>
                  )}
                </div>
              ) : (
                <div>
                  <div className="p-6 space-y-4">
                    {/* Dependency Warnings for each user type */}
                    {userTypes.map((userType) => (
                                          <DependencyWarning
                      key={userType.id}
                      userType={userType}
                      resourceType={resourceType}
                    />
                    ))}
                  </div>
                  <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 dark:bg-gray-700/50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        {resourceType.charAt(0).toUpperCase() + resourceType.slice(1)} Resource
                      </th>
                      {userTypes.map((userType) => (
                        <th 
                          key={userType.id} 
                          className="px-6 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
                        >
                          <div className="flex flex-col items-center">
                            <span>{userType.name}</span>
                            <span className="text-xs text-gray-400 mt-1">
                              ({userType.user_count || 0} users)
                            </span>
                          </div>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                    {items.map((item) => (
                      <tr key={item.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            <div 
                              className="w-3 h-3 rounded-full mr-3"
                              style={{ backgroundColor: item.color }}
                            />
                            <div>
                              <div className="text-sm font-medium text-gray-900 dark:text-white">
                                {item.name}
                              </div>
                              <div className="text-sm text-gray-500 dark:text-gray-400">
                                {item.description}
                              </div>
                              <div className="text-xs text-gray-400 mt-1">
                                Dynamic Permission ID: {item.id}
                              </div>
                            </div>
                          </div>
                        </td>
                        {userTypes.map((userType) => {
                          // Get permission state using the new dependency checking
                          const permissionState = getPermissionState(
                            userType, 
                            resourceType, 
                            item.id || 0, 
                            pipelinePermissions
                          )
                          
                          const isChanging = ongoingPermissionChanges.has(`dynamic-${resourceType}-${userType.id}-${item.id || 'unknown'}`)
                          
                          return (
                            <td key={userType.id} className="px-6 py-4">
                              <div className="flex justify-center">
                                <PermissionCheckbox
                                userType={userType}
                                resourceType={resourceType}
                                resourceName={item.name}
                                resourceId={item.id || 0}
                                state={permissionState}
                                isChanging={isChanging}
                                onChange={async (granted: boolean) => {
                                  if (resourceType === 'pipelines' && item.id) {
                                    const pipelineId = typeof item.id === 'string' ? parseInt(item.id) : item.id
                                    await togglePipelineAccess(userType.id, pipelineId, granted)
                                  }
                                  // Future: Add workflow toggle when implemented
                                  // else if (resourceType === 'workflows' && item.id) {
                                  //   const workflowId = typeof item.id === 'string' ? parseInt(item.id) : item.id
                                  //   await toggleWorkflowAccess(userType.id, workflowId, granted)
                                  // }
                                }}
                              />
                              </div>
                            </td>
                          )
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Dynamic Resource Access Summary */}
              {items.length > 0 && (
              <div className="border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/50 px-6 py-4">
                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center space-x-6">
                    <span className="text-gray-500 dark:text-gray-400">
                      Dynamic {resourceType}: {items.length} resources
                    </span>
                    <span className="text-blue-600 dark:text-blue-400">
                      Resource Type: {resourceType}
                    </span>
                    <span className="text-green-600 dark:text-green-400">
                      Backend Connected ✓
                    </span>
                  </div>
                  <div className="flex items-center text-xs text-gray-400">
                    <span>💡 Resource access = Dynamic permissions for specific resources. Users need both static permissions + resource access.</span>
                  </div>
                </div>
              </div>
              )}
                </div>
              )}
          </div>
        </div>
        )
      })()}


      {/* User Roles Tab */}
      {activeTab === 'roles' && (
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              User Roles
            </h3>
            <button 
              type="button"
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
                      type="button"
                      onClick={() => handleEditUserType(userType)}
                      className="text-gray-400 hover:text-gray-500 dark:hover:text-gray-300 p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700"
                      title="Edit user type"
                    >
                      <Edit className="w-4 h-4" />
                    </button>
                    <button 
                      type="button"
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
    </PermissionGuard>
  )
}