'use client'

import { ReactNode } from 'react'
import { useAuth } from '@/features/auth/context'

interface PermissionGuardProps {
  children: ReactNode
  category: string
  action: string
  fallback?: ReactNode
  requireAll?: boolean
}

interface MultiPermissionGuardProps {
  children: ReactNode
  permissions: Array<{ category: string; action: string }>
  requireAll?: boolean
  fallback?: ReactNode
}

/**
 * Permission Guard Component
 * Conditionally renders children based on user permissions
 */
export function PermissionGuard({ 
  children, 
  category, 
  action, 
  fallback = null 
}: PermissionGuardProps) {
  const { hasPermission } = useAuth()
  
  if (!hasPermission(category, action)) {
    return <>{fallback}</>
  }
  
  return <>{children}</>
}

/**
 * Multiple Permission Guard Component
 * Conditionally renders children based on multiple permissions
 */
export function MultiPermissionGuard({ 
  children, 
  permissions, 
  requireAll = false, 
  fallback = null 
}: MultiPermissionGuardProps) {
  const { hasPermission } = useAuth()
  
  const hasRequiredPermissions = requireAll
    ? permissions.every(({ category, action }) => hasPermission(category, action))
    : permissions.some(({ category, action }) => hasPermission(category, action))
  
  if (!hasRequiredPermissions) {
    return <>{fallback}</>
  }
  
  return <>{children}</>
}

/**
 * Admin Only Guard
 * Restricts content to users with system full access
 */
export function AdminOnlyGuard({ children, fallback = null }: { 
  children: ReactNode; 
  fallback?: ReactNode 
}) {
  return (
    <PermissionGuard 
      category="system" 
      action="full_access" 
      fallback={fallback}
    >
      {children}
    </PermissionGuard>
  )
}

/**
 * Manager Plus Guard
 * Restricts content to managers and admins
 */
export function ManagerPlusGuard({ children, fallback = null }: { 
  children: ReactNode; 
  fallback?: ReactNode 
}) {
  return (
    <MultiPermissionGuard 
      permissions={[
        { category: 'system', action: 'full_access' },
        { category: 'users', action: 'create' }  // Check resource permission for manager-level actions
      ]}
      requireAll={false}
      fallback={fallback}
    >
      {children}
    </MultiPermissionGuard>
  )
}

/**
 * Permission Button
 * Button that's disabled/hidden based on permissions
 */
interface PermissionButtonProps {
  category: string
  action: string
  onClick: () => void
  children: ReactNode
  className?: string
  disabled?: boolean
  hideWhenNoPermission?: boolean
  variant?: 'primary' | 'secondary' | 'danger'
}

export function PermissionButton({
  category,
  action,
  onClick,
  children,
  className = '',
  disabled = false,
  hideWhenNoPermission = false,
  variant = 'primary'
}: PermissionButtonProps) {
  const { hasPermission } = useAuth()
  
  if (!hasPermission(category, action)) {
    if (hideWhenNoPermission) {
      return null
    }
    
    // Show disabled button with tooltip
    return (
      <button
        disabled={true}
        className={`opacity-50 cursor-not-allowed ${getButtonClasses(variant)} ${className}`}
        title="You don't have permission for this action"
      >
        {children}
      </button>
    )
  }
  
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`${getButtonClasses(variant)} ${className} ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
    >
      {children}
    </button>
  )
}

function getButtonClasses(variant: string): string {
  switch (variant) {
    case 'primary':
      return 'bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md transition-colors'
    case 'secondary':
      return 'bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-md transition-colors'
    case 'danger':
      return 'bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-md transition-colors'
    default:
      return 'bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md transition-colors'
  }
}