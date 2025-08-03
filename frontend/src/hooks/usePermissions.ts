'use client'

import { useAuth } from '@/features/auth/context'
import { usePermissionSchema } from './use-permission-schema'
import { useMemo, useCallback } from 'react'

/**
 * Enhanced custom hook for permission checking
 * Integrates static permission checking with dynamic schema-based features
 * Provides convenient methods for common permission patterns
 */
export function usePermissions() {
  const { hasPermission, hasAnyPermission, hasAllPermissions, user } = useAuth()
  const { 
    frontendConfig, 
    getCategoryActions, 
    isStaticCategory, 
    isDynamicCategory,
    getDynamicResources,
    validatePermissionSet
  } = usePermissionSchema()

  // User management permissions
  const canCreateUsers = () => hasPermission('users', 'create')
  const canReadUsers = () => hasPermission('users', 'read')
  const canUpdateUsers = () => hasPermission('users', 'update')
  const canDeleteUsers = () => hasPermission('users', 'delete')
  const canAssignRoles = () => hasPermission('users', 'assign_roles')
  const canImpersonateUsers = () => hasPermission('users', 'impersonate')

  // User type management permissions
  const canManageUserTypes = () => hasPermission('user_types', 'update')
  const canCreateUserTypes = () => hasPermission('user_types', 'create')
  const canDeleteUserTypes = () => hasPermission('user_types', 'delete')

  // Pipeline management permissions
  const canCreatePipelines = () => hasPermission('pipelines', 'create')
  const canUpdatePipelines = () => hasPermission('pipelines', 'update')
  const canDeletePipelines = () => hasPermission('pipelines', 'delete')
  const canClonePipelines = () => hasPermission('pipelines', 'clone')
  const canExportPipelines = () => hasPermission('pipelines', 'export')

  // Record management permissions
  const canCreateRecords = () => hasPermission('records', 'create')
  const canUpdateRecords = () => hasPermission('records', 'update')
  const canDeleteRecords = () => hasPermission('records', 'delete')
  const canBulkEditRecords = () => hasPermission('records', 'bulk_edit')
  const canExportRecords = () => hasPermission('records', 'export')

  // Workflow permissions
  const canCreateWorkflows = () => hasPermission('workflows', 'create')
  const canExecuteWorkflows = () => hasPermission('workflows', 'execute')
  const canUpdateWorkflows = () => hasPermission('workflows', 'update')
  const canDeleteWorkflows = () => hasPermission('workflows', 'delete')

  // Business rules permissions
  const canCreateBusinessRules = () => hasPermission('business_rules', 'create')
  const canReadBusinessRules = () => hasPermission('business_rules', 'read')
  const canUpdateBusinessRules = () => hasPermission('business_rules', 'update')
  const canDeleteBusinessRules = () => hasPermission('business_rules', 'delete')

  // Communication permissions
  const canSendCommunications = () => hasPermission('communications', 'send')
  const canCreateCommunications = () => hasPermission('communications', 'create')

  // System permissions
  const isSystemAdmin = () => hasPermission('system', 'full_access')
  const canManageSettings = () => hasPermission('settings', 'update')
  const canViewMonitoring = () => hasPermission('monitoring', 'read')

  // AI permissions
  const canUseAI = () => hasAnyPermission('ai_features', ['read', 'update'])
  const canConfigureAI = () => hasPermission('ai_features', 'configure')

  // Reports permissions
  const canCreateReports = () => hasPermission('reports', 'create')
  const canExportReports = () => hasPermission('reports', 'export')

  // Role-based checks
  const isAdmin = () => user?.userType?.name === 'Admin' || isSystemAdmin()
  const isManager = () => user?.userType?.name === 'Manager' || isAdmin()
  const isUser = () => user?.userType?.name === 'User' || isManager()
  const isViewer = () => user?.userType?.name === 'Viewer' || isUser()

  // Permission level checks
  const hasUserManagementAccess = () => hasAnyPermission('users', ['read', 'create', 'update'])
  const hasFullUserManagement = () => hasAllPermissions('users', ['create', 'read', 'update', 'delete'])
  const hasPipelineAccess = () => hasAnyPermission('pipelines', ['read', 'create', 'update'])
  const hasWorkflowAccess = () => hasAnyPermission('workflows', ['read', 'create', 'execute'])
  const hasBusinessRulesAccess = () => hasAnyPermission('business_rules', ['read', 'create', 'update'])

  // Complex permission combinations
  const canManageSystem = () => isSystemAdmin() || canManageSettings()
  const canManageContent = () => hasPipelineAccess() || canCreateRecords()
  const canManageTeam = () => hasUserManagementAccess() || canAssignRoles()

  // Check if user can perform action on specific resource
  const canPerformAction = (category: string, action: string) => hasPermission(category, action)

  // Check multiple permissions at once
  const hasPermissions = (permissions: Array<{ category: string; action: string }>, requireAll = false) => {
    return requireAll
      ? permissions.every(({ category, action }) => hasPermission(category, action))
      : permissions.some(({ category, action }) => hasPermission(category, action))
  }

  // Get all user permissions for debugging
  const getAllPermissions = () => user?.permissions || {}

  // Enhanced dynamic permission functions
  
  // Get available actions for a category from schema
  const getAvailableActions = useCallback((category: string): string[] => {
    return getCategoryActions(category)
  }, [getCategoryActions])
  
  // Check if a category exists in the schema
  const isCategoryAvailable = useCallback((category: string): boolean => {
    return frontendConfig?.categories?.[category] !== undefined
  }, [frontendConfig])
  
  // Check if an action is valid for a category
  const isActionAvailable = useCallback((category: string, action: string): boolean => {
    const actions = getCategoryActions(category)
    return actions.includes(action)
  }, [getCategoryActions])
  
  // Get dynamic resource permissions (e.g., pipeline_123, workflow_456)
  const getDynamicResourcePermissions = useCallback((resourceType?: string) => {
    const dynamicResources = getDynamicResources()
    
    if (resourceType) {
      return dynamicResources.filter(resource => 
        resource.data.resource_type === resourceType
      )
    }
    
    return dynamicResources
  }, [getDynamicResources])
  
  // Check permission on a specific dynamic resource
  const hasResourcePermission = useCallback((
    resourceType: string, 
    resourceId: string | number, 
    action: string
  ): boolean => {
    const resourceKey = `${resourceType}_${resourceId}`
    return hasPermission(resourceKey, action)
  }, [hasPermission])
  
  // Check pipeline-specific permissions
  const hasPipelinePermission = useCallback((pipelineId: string | number, action: string): boolean => {
    return hasResourcePermission('pipeline', pipelineId, action)
  }, [hasResourcePermission])
  
  // Check workflow-specific permissions
  const hasWorkflowPermission = useCallback((workflowId: string | number, action: string): boolean => {
    return hasResourcePermission('workflow', workflowId, action)
  }, [hasResourcePermission])
  
  // Check form-specific permissions
  const hasFormPermission = useCallback((formId: string | number, action: string): boolean => {
    return hasResourcePermission('form', formId, action)
  }, [hasResourcePermission])
  
  // Get all pipelines user has access to
  const getAccessiblePipelines = useCallback(() => {
    const pipelineResources = getDynamicResourcePermissions('pipeline')
    return pipelineResources.filter(resource => 
      hasResourcePermission('pipeline', resource.data.resource_id!, 'access') ||
      hasResourcePermission('pipeline', resource.data.resource_id!, 'read')
    )
  }, [getDynamicResourcePermissions, hasResourcePermission])
  
  // Get all workflows user can execute
  const getExecutableWorkflows = useCallback(() => {
    const workflowResources = getDynamicResourcePermissions('workflow')
    return workflowResources.filter(resource => 
      hasResourcePermission('workflow', resource.data.resource_id!, 'execute') ||
      hasResourcePermission('workflow', resource.data.resource_id!, 'view')
    )
  }, [getDynamicResourcePermissions, hasResourcePermission])
  
  // Enhanced permission validation
  const validateUserPermissions = useCallback(async (permissions: Record<string, string[]>) => {
    try {
      return await validatePermissionSet(permissions)
    } catch (error) {
      console.error('Permission validation error:', error)
      return {
        valid: false,
        errors: ['Failed to validate permissions'],
        warnings: [],
        validated_permissions: {}
      }
    }
  }, [validatePermissionSet])
  
  // Get permission summary for current user
  const getPermissionSummary = useMemo(() => {
    if (!user?.permissions || !frontendConfig?.categories) {
      return {
        totalCategories: 0,
        totalPermissions: 0,
        staticCategories: 0,
        dynamicResources: 0,
        hasSystemAccess: false,
        hasAdminAccess: false
      }
    }
    
    const userPermissions = user.permissions
    const allCategories = Object.keys(frontendConfig.categories)
    const staticCats = allCategories.filter(cat => isStaticCategory(cat))
    const dynamicResources = getDynamicResources()
    
    const totalPermissions = Object.values(userPermissions).reduce(
      (total, actions) => total + (Array.isArray(actions) ? actions.length : 0), 0
    )
    
    return {
      totalCategories: allCategories.length,
      totalPermissions,
      staticCategories: staticCats.length,
      dynamicResources: dynamicResources.length,
      hasSystemAccess: isSystemAdmin(),
      hasAdminAccess: isAdmin()
    }
  }, [user?.permissions, frontendConfig, isStaticCategory, getDynamicResources, isSystemAdmin, isAdmin])
  
  // Get category-specific permissions for user
  const getCategoryPermissions = useCallback((category: string) => {
    const userPerms = user?.permissions?.[category] || []
    const availableActions = getCategoryActions(category)
    
    return {
      category,
      userPermissions: userPerms,
      availableActions,
      hasFullAccess: availableActions.every(action => userPerms.includes(action)),
      hasPartialAccess: availableActions.some(action => userPerms.includes(action)),
      missingPermissions: availableActions.filter(action => !userPerms.includes(action))
    }
  }, [user?.permissions, getCategoryActions])

  return {
    // Core permission functions
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    canPerformAction,
    hasPermissions,
    getAllPermissions,

    // User management
    canCreateUsers,
    canReadUsers,
    canUpdateUsers,
    canDeleteUsers,
    canAssignRoles,
    canImpersonateUsers,

    // User type management
    canManageUserTypes,
    canCreateUserTypes,
    canDeleteUserTypes,

    // Pipeline management
    canCreatePipelines,
    canUpdatePipelines,
    canDeletePipelines,
    canClonePipelines,
    canExportPipelines,

    // Record management
    canCreateRecords,
    canUpdateRecords,
    canDeleteRecords,
    canBulkEditRecords,
    canExportRecords,

    // Workflow management
    canCreateWorkflows,
    canExecuteWorkflows,
    canUpdateWorkflows,
    canDeleteWorkflows,

    // Business rules management
    canCreateBusinessRules,
    canReadBusinessRules,
    canUpdateBusinessRules,
    canDeleteBusinessRules,

    // Communication management
    canSendCommunications,
    canCreateCommunications,

    // System management
    isSystemAdmin,
    canManageSettings,
    canViewMonitoring,

    // AI features
    canUseAI,
    canConfigureAI,

    // Reports
    canCreateReports,
    canExportReports,

    // Role-based checks
    isAdmin,
    isManager,
    isUser,
    isViewer,

    // Permission level checks
    hasUserManagementAccess,
    hasFullUserManagement,
    hasPipelineAccess,
    hasWorkflowAccess,
    hasBusinessRulesAccess,

    // Complex combinations
    canManageSystem,
    canManageContent,
    canManageTeam,

    // User info
    user,

    // Enhanced dynamic permission functions
    getAvailableActions,
    isCategoryAvailable,
    isActionAvailable,
    getDynamicResourcePermissions,
    hasResourcePermission,
    hasPipelinePermission,
    hasWorkflowPermission,
    hasFormPermission,
    getAccessiblePipelines,
    getExecutableWorkflows,
    validateUserPermissions,
    getPermissionSummary,
    getCategoryPermissions,

    // Schema integration helpers
    frontendConfig,
    isStaticCategory,
    isDynamicCategory
  }
}