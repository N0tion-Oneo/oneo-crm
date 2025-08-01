'use client'

import { useAuth } from '@/features/auth/context'

/**
 * Custom hook for permission checking
 * Provides convenient methods for common permission patterns
 */
export function usePermissions() {
  const { hasPermission, hasAnyPermission, hasAllPermissions, user } = useAuth()

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

    // Complex combinations
    canManageSystem,
    canManageContent,
    canManageTeam,

    // User info
    user
  }
}