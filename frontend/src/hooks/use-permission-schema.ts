'use client'

import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { api } from '@/lib/api'
import { usePermissionUpdatesSubscription } from '@/hooks/use-websocket-subscription'

interface PermissionCategory {
  actions: string[]
  description: string
  category_display: string
  resource_type?: string
  resource_id?: string | number
  is_dynamic?: boolean
  parent_category?: string
  metadata?: Record<string, any>
}

interface PermissionSchema {
  [category: string]: PermissionCategory
}

interface PermissionMatrix {
  categories: PermissionSchema
  grouped_categories: Record<string, {
    items: Array<{ key: string; data: PermissionCategory }>
    is_expandable: boolean
    total_resources: number
  }>
  action_descriptions: Record<string, string>
  tenant_info: {
    schema_name: string
    name: string
    max_users: number
    features_enabled: Record<string, any>
  }
  ui_config: {
    collapsible_categories: boolean
    bulk_operations: boolean
    search_enabled: boolean
    export_enabled: boolean
    real_time_updates: boolean
    resource_grouping: boolean
  }
  validation_rules: {
    required_admin_permissions: string[]
    protected_permissions: string[]
    category_dependencies: Record<string, string[]>
    dynamic_resource_limits: Record<string, number>
  }
}

interface FrontendMatrixConfig extends PermissionMatrix {
  frontend_helpers: {
    action_icons: Record<string, string>
    category_colors: Record<string, string>
    permission_levels: Record<string, { label: string; color: string }>
    category_descriptions: Record<string, string>
  }
  permission_dependencies: Record<string, string[]>
  user_type_recommendations: Record<string, {
    name: string
    description: string
    recommended_permissions: string[]
    warning: string
  }>
  bulk_operation_templates: Record<string, {
    name: string
    description: string
    permissions?: string[]
    remove_permissions?: string[]
  }>
  validation_schemas: Record<string, any>
  cached: boolean
  generated_at: string
}

interface UsePermissionSchemaReturn {
  // Core schema data
  schema: PermissionSchema | null
  matrix: PermissionMatrix | null
  frontendConfig: FrontendMatrixConfig | null
  
  // Loading states
  loading: boolean
  schemaLoading: boolean
  matrixLoading: boolean
  frontendLoading: boolean
  
  // Error states
  error: string | null
  schemaError: string | null
  matrixError: string | null
  frontendError: string | null
  
  // Refresh functions
  refreshSchema: () => Promise<void>
  refreshMatrix: () => Promise<void>
  refreshFrontendConfig: () => Promise<void>
  refreshAll: () => Promise<void>
  
  // Cache management
  clearCache: () => Promise<void>
  
  // Utility functions
  getCategoryActions: (category: string) => string[]
  getActionDescription: (action: string) => string
  getCategoryColor: (category: string) => string
  getActionIcon: (action: string) => string
  isStaticCategory: (category: string) => boolean
  isDynamicCategory: (category: string) => boolean
  getDynamicResources: (parentCategory?: string) => Array<{ key: string; data: PermissionCategory }>
  
  // Validation functions
  validatePermissionSet: (permissions: Record<string, string[]>) => Promise<any>
  
  // Bulk operations
  applyBulkOperation: (userTypeId: number, operationName: string, customPermissions?: string[]) => Promise<any>
  
  // Comparison
  compareUserTypes: (userTypeIds: number[]) => Promise<any>
  
  // Analytics
  getAnalytics: () => Promise<any>
}

/**
 * Hook for managing dynamic permission schemas
 * Replaces hardcoded permissions with API-driven dynamic schemas
 */
export function usePermissionSchema(): UsePermissionSchemaReturn {
  // State for different data types
  const [schema, setSchema] = useState<PermissionSchema | null>(null)
  const [matrix, setMatrix] = useState<PermissionMatrix | null>(null)
  const [frontendConfig, setFrontendConfig] = useState<FrontendMatrixConfig | null>(null)
  
  // Loading states
  const [schemaLoading, setSchemaLoading] = useState(false)
  const [matrixLoading, setMatrixLoading] = useState(false)
  const [frontendLoading, setFrontendLoading] = useState(false)
  
  // Error states
  const [schemaError, setSchemaError] = useState<string | null>(null)
  const [matrixError, setMatrixError] = useState<string | null>(null)
  const [frontendError, setFrontendError] = useState<string | null>(null)
  
  // Combined loading state
  const loading = schemaLoading || matrixLoading || frontendLoading
  
  // Combined error state
  const error = schemaError || matrixError || frontendError
  
  // Fetch permission schema
  const fetchSchema = useCallback(async () => {
    setSchemaLoading(true)
    setSchemaError(null)
    
    try {
      const response = await api.get('/api/v1/auth/permission_schema/')
      setSchema(response.data.schema)
    } catch (err: any) {
      const errorMessage = err.response?.data?.error || 'Failed to fetch permission schema'
      setSchemaError(errorMessage)
      console.error('Permission schema fetch error:', err)
    } finally {
      setSchemaLoading(false)
    }
  }, [])
  
  // Fetch permission matrix
  const fetchMatrix = useCallback(async () => {
    setMatrixLoading(true)
    setMatrixError(null)
    
    try {
      const response = await api.get('/api/v1/auth/permission_matrix/')
      setMatrix(response.data.matrix)
    } catch (err: any) {
      const errorMessage = err.response?.data?.error || 'Failed to fetch permission matrix'
      setMatrixError(errorMessage)
      console.error('Permission matrix fetch error:', err)
    } finally {
      setMatrixLoading(false)
    }
  }, [])
  
  // Fetch frontend configuration
  const fetchFrontendConfig = useCallback(async () => {
    setFrontendLoading(true)
    setFrontendError(null)
    
    try {
      const response = await api.get('/api/v1/auth/frontend_matrix/')
      setFrontendConfig(response.data)
    } catch (err: any) {
      const errorMessage = err.response?.data?.error || 'Failed to fetch frontend configuration'
      setFrontendError(errorMessage)
      console.error('Frontend config fetch error:', err)
    } finally {
      setFrontendLoading(false)
    }
  }, [])
  
  // Refresh functions
  const refreshSchema = useCallback(async () => {
    await fetchSchema()
  }, [fetchSchema])
  
  const refreshMatrix = useCallback(async () => {
    await fetchMatrix()
  }, [fetchMatrix])
  
  const refreshFrontendConfig = useCallback(async () => {
    await fetchFrontendConfig()
  }, [fetchFrontendConfig])
  
  const refreshAll = useCallback(async () => {
    await Promise.all([
      fetchSchema(),
      fetchMatrix(),
      fetchFrontendConfig()
    ])
  }, [fetchSchema, fetchMatrix, fetchFrontendConfig])
  
  // Clear cache (disabled - cache removed from backend)
  const clearCache = useCallback(async () => {
    try {
      console.log('Cache clearing disabled - permission cache has been removed from backend')
      // Just refresh all data since cache was removed
      await refreshAll()
    } catch (err: any) {
      console.error('Refresh error:', err)
      throw new Error(err.response?.data?.error || 'Failed to refresh data')
    }
  }, [refreshAll])
  
  // Utility functions
  const getCategoryActions = useCallback((category: string): string[] => {
    return schema?.[category]?.actions || []
  }, [schema])
  
  const getActionDescription = useCallback((action: string): string => {
    return frontendConfig?.action_descriptions?.[action] || action.replace('_', ' ').toLowerCase()
  }, [frontendConfig])
  
  const getCategoryColor = useCallback((category: string): string => {
    return frontendConfig?.frontend_helpers?.category_colors?.[category] || '#64748b'
  }, [frontendConfig])
  
  const getActionIcon = useCallback((action: string): string => {
    return frontendConfig?.frontend_helpers?.action_icons?.[action] || 'circle'
  }, [frontendConfig])
  
  const isStaticCategory = useCallback((category: string): boolean => {
    return !schema?.[category]?.is_dynamic
  }, [schema])
  
  const isDynamicCategory = useCallback((category: string): boolean => {
    return schema?.[category]?.is_dynamic === true
  }, [schema])
  
  const getDynamicResources = useCallback((parentCategory?: string) => {
    if (!frontendConfig?.grouped_categories) return []
    
    if (parentCategory) {
      return frontendConfig.grouped_categories[parentCategory]?.items || []
    }
    
    // Return all dynamic resources
    return Object.values(frontendConfig.grouped_categories)
      .filter(group => group.is_expandable)
      .flatMap(group => group.items)
  }, [frontendConfig])
  
  // Validation functions
  const validatePermissionSet = useCallback(async (permissions: Record<string, string[]>) => {
    try {
      const response = await api.post('/api/v1/auth/validate_permissions/', { permissions })
      return response.data
    } catch (err: any) {
      console.error('Permission validation error:', err)
      throw new Error(err.response?.data?.error || 'Failed to validate permissions')
    }
  }, [])
  
  // Bulk operations
  const applyBulkOperation = useCallback(async (
    userTypeId: number, 
    operationName: string, 
    customPermissions?: string[]
  ) => {
    try {
      const response = await api.post('/api/v1/auth/bulk_permission_operation/', {
        user_type_id: userTypeId,
        operation_name: operationName,
        custom_permissions: customPermissions
      })
      
      // Refresh data after successful operation
      if (response.data.success) {
        await refreshFrontendConfig()
      }
      
      return response.data
    } catch (err: any) {
      console.error('Bulk operation error:', err)
      throw new Error(err.response?.data?.error || 'Failed to apply bulk operation')
    }
  }, [refreshFrontendConfig])
  
  // Comparison
  const compareUserTypes = useCallback(async (userTypeIds: number[]) => {
    try {
      const response = await api.post('/api/v1/auth/compare_user_types/', { user_type_ids: userTypeIds })
      return response.data
    } catch (err: any) {
      console.error('User type comparison error:', err)
      throw new Error(err.response?.data?.error || 'Failed to compare user types')
    }
  }, [])
  
  // Analytics
  const getAnalytics = useCallback(async () => {
    try {
      const response = await api.get('/api/v1/auth/permission_analytics/')
      return response.data
    } catch (err: any) {
      console.error('Permission analytics error:', err)
      throw new Error(err.response?.data?.error || 'Failed to get permission analytics')
    }
  }, [])
  
  // Initial load
  useEffect(() => {
    refreshAll()
  }, [refreshAll])

  // Debounce refresh to prevent race conditions from multiple WebSocket updates
  const refreshTimeout = useRef<NodeJS.Timeout | null>(null)
  const categoryOperationInProgress = useRef<boolean>(false)
  
  // Function to temporarily disable WebSocket refresh during category operations
  const disableWebSocketRefreshTemporarily = useCallback((duration: number = 3000) => {
    console.log(`🚫 Temporarily disabling WebSocket refresh for ${duration}ms during category operation`)
    categoryOperationInProgress.current = true
    setTimeout(() => {
      categoryOperationInProgress.current = false
      console.log(`✅ Re-enabling WebSocket refresh after category operation`)
    }, duration)
  }, [])
  
  // For now, disable WebSocket-triggered refreshes since they cause full page re-renders
  // The permissions page updates immediately after API calls, so WebSocket is mainly for other users
  // TODO: Implement targeted permission updates instead of full refreshAll()
  const handlePermissionMessage = useCallback((message: any) => {
    if (message.type === 'permission_update') {
      console.log('🔄 Permission update received via centralized WebSocket (not refreshing):', message)
      // Currently disabled to prevent full page refresh
      // Individual permissions already update immediately after API calls
    }
  }, [])

  // Subscribe to permission updates using centralized WebSocket (but don't trigger refreshes)
  const { isConnected: permissionWebSocketConnected } = usePermissionUpdatesSubscription(
    handlePermissionMessage,
    true // Still connected for future targeted updates
  )
  
  // Memoized return value
  return useMemo(() => ({
    // Core data
    schema,
    matrix,
    frontendConfig,
    
    // Loading states
    loading,
    schemaLoading,
    matrixLoading,
    frontendLoading,
    
    // Error states
    error,
    schemaError,
    matrixError,
    frontendError,
    
    // Refresh functions
    refreshSchema,
    refreshMatrix,
    refreshFrontendConfig,
    refreshAll,
    
    // Cache management
    clearCache,
    
    // Utility functions
    getCategoryActions,
    getActionDescription,
    getCategoryColor,
    getActionIcon,
    isStaticCategory,
    isDynamicCategory,
    getDynamicResources,
    
    // Operations
    validatePermissionSet,
    applyBulkOperation,
    compareUserTypes,
    getAnalytics,
    
    // Category operation helpers
    disableWebSocketRefreshTemporarily
  }), [
    schema,
    matrix,
    frontendConfig,
    loading,
    schemaLoading,
    matrixLoading,
    frontendLoading,
    error,
    schemaError,
    matrixError,
    frontendError,
    refreshSchema,
    refreshMatrix,
    refreshFrontendConfig,
    refreshAll,
    clearCache,
    getCategoryActions,
    getActionDescription,
    getCategoryColor,
    getActionIcon,
    isStaticCategory,
    isDynamicCategory,
    getDynamicResources,
    validatePermissionSet,
    applyBulkOperation,
    compareUserTypes,
    getAnalytics,
    disableWebSocketRefreshTemporarily
  ])
}

export default usePermissionSchema