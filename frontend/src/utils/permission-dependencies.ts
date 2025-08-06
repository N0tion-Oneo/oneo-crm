/**
 * Permission Dependency Management Utilities
 * 
 * This module provides helper functions to determine permission dependencies
 * and UI state for the permission matrix system.
 */

export interface UserType {
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

export interface DynamicPermissionItem {
  id: string | number
  name: string
  description?: string
  is_dynamic: boolean
  [key: string]: any
}

export type PermissionState = 'disabled' | 'enabled' | 'available'

/**
 * Permission dependency rules
 * Defines which static permissions are required for dynamic permissions
 */
export const PERMISSION_DEPENDENCIES = {
  pipelines: {
    requiredStatic: ['access', 'read'], // User needs pipelines.access OR pipelines.read
    description: 'Pipeline access requires static pipeline permissions'
  },
  workflows: {
    requiredStatic: ['read'],
    description: 'Workflow access requires static workflow read permission'
  },
  fields: {
    requiredStatic: ['read'],
    description: 'Field-level permissions require static field read permission'
  },
  records: {
    requiredStatic: ['read'],
    description: 'Record access requires static record read permission'
  }
} as const

/**
 * Check if a user type has a specific static permission
 */
export const hasStaticPermission = (
  userType: UserType,
  category: string,
  action: string
): boolean => {
  const categoryPermissions = userType.base_permissions?.[category] || []
  return categoryPermissions.includes(action)
}

/**
 * Check if a user type has any of the required static permissions for dynamic access
 */
export const hasRequiredStaticPermissions = (
  userType: UserType,
  resourceType: string
): boolean => {
  const dependency = PERMISSION_DEPENDENCIES[resourceType as keyof typeof PERMISSION_DEPENDENCIES]
  if (!dependency) return true // No dependencies defined, allow access
  
  return dependency.requiredStatic.some(action => 
    hasStaticPermission(userType, resourceType, action)
  )
}

/**
 * Check if a user type has dynamic permission for a specific resource
 */
export const hasDynamicPermission = (
  userType: UserType,
  resourceType: string,
  resourceId: string | number,
  dynamicPermissions: any[]
): boolean => {
  // Different resource types may have different permission structures
  switch (resourceType) {
    case 'pipelines':
      return dynamicPermissions.some(
        perm => perm.user_type === userType.id && perm.pipeline_id === resourceId
      )
    case 'workflows':
      return dynamicPermissions.some(
        perm => perm.user_type === userType.id && perm.workflow_id === resourceId
      )
    default:
      return false
  }
}

/**
 * Get the permission state for a specific resource
 */
export const getPermissionState = (
  userType: UserType,
  resourceType: string,
  resourceId: string | number,
  dynamicPermissions: any[]
): PermissionState => {
  // First check if user has required static permissions
  if (!hasRequiredStaticPermissions(userType, resourceType)) {
    return 'disabled'
  }
  
  // Check if user has dynamic permission for this specific resource
  if (hasDynamicPermission(userType, resourceType, resourceId, dynamicPermissions)) {
    return 'enabled'
  }
  
  return 'available'
}

/**
 * Get missing static permissions for a resource type
 */
export const getMissingStaticPermissions = (
  userType: UserType,
  resourceType: string
): string[] => {
  const dependency = PERMISSION_DEPENDENCIES[resourceType as keyof typeof PERMISSION_DEPENDENCIES]
  if (!dependency) return []
  
  return dependency.requiredStatic.filter(action => 
    !hasStaticPermission(userType, resourceType, action)
  )
}

/**
 * Check if a resource type tab should be visible
 */
export const shouldShowResourceTab = (
  userType: UserType,
  resourceType: string
): boolean => {
  // For now, show tabs even if user lacks permissions (but disable contents)
  // This provides better UX by showing what's available
  return true
}

/**
 * Get tooltip message for permission state
 */
export const getPermissionTooltip = (
  state: PermissionState,
  userType: UserType,
  resourceType: string,
  resourceName: string
): string => {
  switch (state) {
    case 'disabled':
      const missingPerms = getMissingStaticPermissions(userType, resourceType)
      const permissionList = missingPerms.map(perm => `${resourceType}.${perm}`).join(' or ')
      return `${userType.name} needs static '${permissionList}' permission before accessing specific ${resourceType}`
    
    case 'enabled':
      return `${userType.name} has access to ${resourceName}`
    
    case 'available':
      return `Click to grant ${userType.name} access to ${resourceName}`
    
    default:
      return ''
  }
}

/**
 * Get CSS classes for permission state
 */
export const getPermissionStateClasses = (state: PermissionState): string => {
  switch (state) {
    case 'disabled':
      return 'opacity-30 cursor-not-allowed bg-gray-100 border-gray-200'
    
    case 'enabled':
      return 'bg-green-500 border-green-500 text-white cursor-pointer hover:bg-green-600'
    
    case 'available':
      return 'border-gray-300 bg-white cursor-pointer hover:border-green-400 hover:bg-green-50'
    
    default:
      return ''
  }
}

/**
 * Get dependency warning message for a user type and resource type
 */
export const getDependencyWarning = (
  userType: UserType,
  resourceType: string
): string | null => {
  if (hasRequiredStaticPermissions(userType, resourceType)) {
    return null
  }
  
  const dependency = PERMISSION_DEPENDENCIES[resourceType as keyof typeof PERMISSION_DEPENDENCIES]
  if (!dependency) return null
  
  const missingPerms = getMissingStaticPermissions(userType, resourceType)
  const permissionList = missingPerms.map(perm => `${resourceType}.${perm}`).join(' or ')
  
  return `${userType.name} needs static '${permissionList}' permission before ${resourceType} access can be granted.`
}

/**
 * Check if any dynamic permissions can be granted for a user type
 */
export const canGrantAnyDynamicPermissions = (
  userType: UserType,
  resourceType: string
): boolean => {
  return hasRequiredStaticPermissions(userType, resourceType)
}