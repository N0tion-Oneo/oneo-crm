'use client'

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { useRouter } from 'next/navigation'
import Cookies from 'js-cookie'
import { authApi } from '@/lib/api'
import type { 
  AuthContextType, 
  User, 
  Tenant, 
  LoginCredentials, 
  LoginResponse 
} from '@/types/auth'

const AuthContext = createContext<AuthContextType | null>(null)

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null)
  const [tenant, setTenant] = useState<Tenant | null>(null)
  // Start with false if we can quickly check for tokens
  const [isLoading, setIsLoading] = useState(() => {
    if (typeof window === 'undefined') return true
    const hasTokens = !!(Cookies.get('oneo_access_token') || Cookies.get('oneo_refresh_token'))
    // Start with false to minimize loading states, but set to true if we have tokens to validate
    return hasTokens
  })
  const router = useRouter()

  // Check authentication status - ensure we have essential user data
  const isAuthenticated = !!user && !!tenant && !!user.email
  
  // Debug authentication state
  useEffect(() => {
    console.log('🔐 Auth state changed:', {
      hasUser: !!user,
      hasTenant: !!tenant,
      hasEmail: !!user?.email,
      isAuthenticated,
      userFirstName: user?.firstName,
      userEmail: user?.email
    })
  }, [user, tenant, isAuthenticated])

  // Initialize auth state on mount
  useEffect(() => {
    initializeAuth()
  }, [])

  const initializeAuth = async () => {
    console.log('🔐 Initializing auth...')
    try {
      // Check if we have JWT tokens
      const accessToken = Cookies.get('oneo_access_token')
      const refreshToken = Cookies.get('oneo_refresh_token')

      console.log('🔐 Token check:', { hasAccess: !!accessToken, hasRefresh: !!refreshToken })

      if (!accessToken && !refreshToken) {
        // No tokens available
        console.log('🔐 No tokens found, clearing auth data')
        clearAuthData()
        setIsLoading(false)
        return
      }

      // We have tokens, so show loading while validating
      setIsLoading(true)

      if (!accessToken && refreshToken) {
        // Try to refresh the access token
        try {
          const response = await fetch(`${window.location.protocol}//${window.location.hostname}:8000/auth/token/refresh/`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ refresh: refreshToken })
          })

          if (response.ok) {
            const { access } = await response.json()
            Cookies.set('oneo_access_token', access, {
              expires: 1/24, // 1 hour
              secure: process.env.NODE_ENV === 'production',
              sameSite: 'lax'
            })
          } else {
            throw new Error('Token refresh failed')
          }
        } catch (error) {
          console.error('Token refresh failed:', error)
          clearAuthData()
          setIsLoading(false)
          return
        }
      }

      // Get complete user and tenant data in one go
      const [meResponse, tenantResponse] = await Promise.allSettled([
        authApi.getCurrentUser(), // This already calls /auth/me/ and returns full data
        authApi.getCurrentTenant()
      ])

      if (meResponse.status === 'fulfilled' && tenantResponse.status === 'fulfilled') {
        const userData = meResponse.value.data
        const tenantData = tenantResponse.value.data
        
        if (userData && tenantData) {
          // Transform the complete user data from /auth/me/
          const completeUser = {
            id: userData.id?.toString() || '1',
            email: userData.email || '',
            username: userData.username || userData.email || '',
            firstName: userData.first_name || userData.email?.split('@')[0] || 'User',
            lastName: userData.last_name || '',
            isActive: userData.is_active !== false,
            isSuperuser: userData.is_staff || false,
            userType: {
              id: userData.user_type?.toString() || '1',
              name: userData.user_type_name || 'User',
              slug: (userData.user_type_name || 'user').toLowerCase().replace(/\s+/g, '_'),
              description: '',
              basePermissions: userData.permissions || {},
              isSystemDefault: true
            },
            tenantId: '1', // TODO: Get from tenant context
            lastActivity: userData.last_activity,
            createdAt: userData.date_joined,
            permissions: userData.permissions || {}
          }
          
          console.log('🔧 Setting complete user data:', {
            firstName: completeUser.firstName,
            lastName: completeUser.lastName,
            email: completeUser.email,
            permissions: completeUser.permissions,
            userType: completeUser.userType.name,
            source: 'auth/me endpoint'
          })
          setUser(completeUser)
          
          setTenant(tenantResponse.value.data as any)
          
          // Store tenant info for API requests
          Cookies.set('oneo_tenant', tenantResponse.value.data.schema_name, {
            expires: 7,
            secure: process.env.NODE_ENV === 'production',
            sameSite: 'lax'
          })
        } else {
          clearAuthData()
        }
      } else {
        clearAuthData()
      }
    } catch (error) {
      console.error('Failed to initialize auth:', error)
      clearAuthData()
    } finally {
      setIsLoading(false)
    }
  }

  const login = async (credentials: LoginCredentials) => {
    try {
      setIsLoading(true)
      
      // Perform login to get JWT tokens
      const response = await authApi.login(credentials)
      console.log('🔑 Login successful, getting complete user data...')

      // Get complete user and tenant data (same as initializeAuth)
      const [meResponse, tenantResponse] = await Promise.allSettled([
        authApi.getCurrentUser(), // This calls /auth/me/ with full user data
        authApi.getCurrentTenant()
      ])

      if (meResponse.status === 'fulfilled' && tenantResponse.status === 'fulfilled') {
        const userData = meResponse.value.data
        const tenantData = tenantResponse.value.data
        
        if (userData && tenantData) {
          // Transform the complete user data (same logic as initializeAuth)
          const completeUser = {
            id: userData.id?.toString() || '1',
            email: userData.email || '',
            username: userData.username || userData.email || '',
            firstName: userData.first_name || userData.email?.split('@')[0] || 'User',
            lastName: userData.last_name || '',
            isActive: userData.is_active !== false,
            isSuperuser: userData.is_staff || false,
            userType: {
              id: userData.user_type?.toString() || '1',
              name: userData.user_type_name || 'User',
              slug: (userData.user_type_name || 'user').toLowerCase().replace(/\s+/g, '_'),
              description: '',
              basePermissions: userData.permissions || {},
              isSystemDefault: true
            },
            tenantId: '1',
            lastActivity: userData.last_activity,
            createdAt: userData.date_joined,
            permissions: userData.permissions || {}
          }

          console.log('🔧 Login: Setting complete user data:', {
            firstName: completeUser.firstName,
            lastName: completeUser.lastName,
            email: completeUser.email,
            permissions: completeUser.permissions,
            userType: completeUser.userType.name
          })
          
          setUser(completeUser)
          setTenant(tenantData as any)

          // Store tenant info for API requests
          Cookies.set('oneo_tenant', tenantData?.schema_name || 'unknown', {
            expires: 7,
            secure: process.env.NODE_ENV === 'production',
            sameSite: 'lax'
          })

          // Use setTimeout to ensure state updates are processed before redirect
          setTimeout(() => {
            const urlParams = new URLSearchParams(window.location.search)
            const redirectTo = urlParams.get('redirect') || '/dashboard'
            console.log('🚀 Redirecting to:', redirectTo)
            router.push(redirectTo)
          }, 100)
        } else {
          throw new Error('Failed to get complete user data after login')
        }
      } else {
        throw new Error('Failed to fetch user or tenant data after login')
      }
    } catch (error: any) {
      console.error('Login failed:', error)
      
      // Extract error message (handle both REST and DRF errors)
      const errorMessage = error.message || 
                          error.response?.data?.detail || 
                          error.response?.data?.error || 
                          error.response?.data?.message || 
                          'Login failed. Please check your credentials.'
      
      throw new Error(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }

  const logout = async () => {
    try {
      setIsLoading(true)
      console.log('Auth context: Starting logout...')
      
      // Call logout endpoint
      const result = await authApi.logout()
      console.log('Auth context: Logout API response:', result)
    } catch (error) {
      console.error('Auth context: Logout API error:', error)
      // Continue with cleanup even if server logout fails
    } finally {
      console.log('Auth context: Clearing auth data and redirecting...')
      clearAuthData()
      setIsLoading(false)
      router.push('/login')
    }
  }

  const refreshSession = async () => {
    // Session refresh is handled automatically by Django sessions
    // Just try to get current user to verify session is still valid
    try {
      const response = await authApi.getCurrentUser()
      if (response.data) {
        setUser(response.data)
        return response.data
      } else {
        throw new Error('No user data returned')
      }
    } catch (error) {
      console.error('Session refresh failed:', error)
      clearAuthData()
      router.push('/login')
      throw error
    }
  }

  const clearAuthData = () => {
    // Clear all auth-related cookies
    Cookies.remove('oneo_tenant')
    Cookies.remove('oneo_access_token')
    Cookies.remove('oneo_refresh_token')
    setUser(null)
    setTenant(null)
  }

  const hasPermission = (category: string, action: string): boolean => {
    if (!user || !user.permissions) {
      console.log('🔒 Permission check failed: No user or permissions', { category, action, hasUser: !!user, hasPermissions: !!user?.permissions })
      return false
    }
    
    // Check system-level permissions first
    const systemPermissions = user.permissions.system || []
    if (systemPermissions.includes('full_access')) {
      console.log('🔑 Permission granted via system full_access', { category, action })
      return true
    }
    
    // Check category-specific permissions
    const categoryPermissions = user.permissions[category] || []
    const hasAccess = categoryPermissions.includes(action)
    
    console.log('🔍 Permission check:', { 
      category, 
      action, 
      categoryPermissions, 
      systemPermissions,
      hasAccess,
      allPermissions: user.permissions 
    })
    
    return hasAccess
  }

  const hasAnyPermission = (category: string, actions: string[]): boolean => {
    return actions.some(action => hasPermission(category, action))
  }

  const hasAllPermissions = (category: string, actions: string[]): boolean => {
    return actions.every(action => hasPermission(category, action))
  }

  const value: AuthContextType = {
    user,
    tenant,
    isLoading,
    isAuthenticated,
    login,
    logout,
    refreshSession,
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}