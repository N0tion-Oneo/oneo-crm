'use client'

import { useAuth } from '@/features/auth/context'
import { useMutation, useQuery } from '@tanstack/react-query'
import { authApi, usersApi, permissionsApi } from '@/lib/api'
import type { LoginCredentials } from '@/types/auth'

// Main auth hook
export const useAuthState = () => {
  return useAuth()
}

// Login hook with mutation
export const useLogin = () => {
  const { login } = useAuth()
  
  return useMutation({
    mutationFn: (credentials: LoginCredentials) => login(credentials),
    onError: (error) => {
      console.error('Login mutation error:', error)
    }
  })
}

// Register hook with mutation
export const useRegister = () => {
  return useMutation({
    mutationFn: async (userData: { 
      first_name: string
      last_name: string
      email: string
      password: string
      organization_name: string
      subdomain: string
    }) => {
      const response = await authApi.register(userData)
      return response
    },
    onError: (error) => {
      console.error('Registration mutation error:', error)
    }
  })
}

// Subdomain availability check hook
export const useCheckSubdomain = () => {
  return useMutation({
    mutationFn: async (subdomain: string) => {
      const response = await authApi.checkSubdomainAvailability(subdomain)
      return response.data
    },
    onError: (error) => {
      console.error('Subdomain check error:', error)
    }
  })
}

// Logout hook
export const useLogout = () => {
  const { logout } = useAuth()
  
  return useMutation({
    mutationFn: () => logout(),
    onError: (error) => {
      console.error('Logout mutation error:', error)
    }
  })
}

// Session refresh hook
export const useSessionRefresh = () => {
  const { refreshSession } = useAuth()
  
  return useMutation({
    mutationFn: () => refreshSession(),
    onError: (error) => {
      console.error('Session refresh error:', error)
    }
  })
}

// User permissions hook
export const useUserPermissions = () => {
  const { user, isAuthenticated } = useAuth()
  
  return useQuery({
    queryKey: ['user-permissions', user?.id],
    queryFn: () => authApi.getCurrentUser().then(res => res.data.permissions),
    enabled: isAuthenticated && !!user?.id,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

// Check if user has specific permission
export const useHasPermission = (resource: string, action: string) => {
  const { user } = useAuth()
  
  if (!user?.permissions) return false
  
  // Check system-level permissions first
  if (user.permissions.system?.includes('full_access')) {
    return true
  }
  
  // Check resource-specific permissions
  const resourcePermissions = user.permissions[resource]
  if (Array.isArray(resourcePermissions)) {
    return resourcePermissions.includes(action)
  }
  
  if (typeof resourcePermissions === 'object' && resourcePermissions !== null) {
    return resourcePermissions.default?.includes(action) || false
  }
  
  return false
}

// User types query
export const useUserTypes = () => {
  const { isAuthenticated } = useAuth()
  
  return useQuery({
    queryKey: ['user-types'],
    queryFn: () => permissionsApi.getUserTypes().then(res => res.data),
    enabled: isAuthenticated,
    staleTime: 10 * 60 * 1000, // 10 minutes
  })
}

// Users list query
export const useUsers = () => {
  const { isAuthenticated } = useAuth()
  
  return useQuery({
    queryKey: ['users'],
    queryFn: () => usersApi.list().then(res => res.data),
    enabled: isAuthenticated,
    staleTime: 2 * 60 * 1000, // 2 minutes
  })
}

// User invitation mutation
export const useInviteUser = () => {
  return useMutation({
    mutationFn: (data: { email: string; userTypeId: string }) => 
      usersApi.invite(data),
    onError: (error) => {
      console.error('User invitation error:', error)
    }
  })
}

// Helper hook to check if user is admin
export const useIsAdmin = () => {
  const { user } = useAuth()
  return user?.isSuperuser || 
         user?.userType?.slug === 'admin' || 
         useHasPermission('system', 'full_access')
}

// Helper hook to check if user can manage users
export const useCanManageUsers = () => {
  return useHasPermission('users', 'create') || 
         useHasPermission('users', 'update') || 
         useHasPermission('users', 'delete')
}

// Helper hook to check if user can manage tenants
export const useCanManageTenants = () => {
  return useIsAdmin() || useHasPermission('tenants', 'manage')
}