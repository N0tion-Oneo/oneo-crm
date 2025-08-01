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
  const [isLoading, setIsLoading] = useState(true)
  const router = useRouter()

  const isAuthenticated = !!user && !!tenant

  // Initialize auth state on mount
  useEffect(() => {
    initializeAuth()
  }, [])

  const initializeAuth = async () => {
    try {
      // Check if we have JWT tokens
      const accessToken = Cookies.get('oneo_access_token')
      const refreshToken = Cookies.get('oneo_refresh_token')

      if (!accessToken && !refreshToken) {
        // No tokens available
        clearAuthData()
        setIsLoading(false)
        return
      }

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

      // Try to get user and tenant data
      const [userResponse, tenantResponse] = await Promise.allSettled([
        authApi.getCurrentUser(),
        authApi.getCurrentTenant()
      ])

      if (userResponse.status === 'fulfilled' && tenantResponse.status === 'fulfilled') {
        if (userResponse.value.data && tenantResponse.value.data) {
          // Get user permissions from the me endpoint which includes permissions
          try {
            const meResponse = await fetch(`${window.location.protocol}//${window.location.hostname}:8000/auth/me/`, {
              headers: {
                'Authorization': `Bearer ${Cookies.get('oneo_access_token')}`,
                'Content-Type': 'application/json'
              }
            })
            
            if (meResponse.ok) {
              const meData = await meResponse.json()
              const userWithPermissions = {
                ...userResponse.value.data,
                permissions: meData.permissions || {},
                // Transform backend user structure to frontend interface
                id: meData.user.id.toString(),
                email: meData.user.email,
                username: meData.user.username,
                firstName: meData.user.first_name,
                lastName: meData.user.last_name,
                isActive: meData.user.is_active,
                isSuperuser: meData.user.is_staff,
                userType: {
                  id: meData.user.user_type.toString(),
                  name: meData.user.user_type_name,
                  slug: meData.user.user_type_name.toLowerCase().replace(/\s+/g, '_'),
                  description: '',
                  basePermissions: {},
                  isSystemDefault: true
                },
                tenantId: '1', // TODO: Get from tenant context
                lastActivity: meData.user.last_activity,
                createdAt: meData.user.date_joined
              }
              setUser(userWithPermissions)
            } else {
              setUser(userResponse.value.data)
            }
          } catch (error) {
            console.warn('Failed to load user permissions:', error)
            setUser(userResponse.value.data)
          }
          
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
      
      const response = await authApi.login(credentials)
      const { user: userData, permissions } = response.data

      // Get tenant info after successful login
      const tenantResponse = await authApi.getCurrentTenant()
      const tenantData = tenantResponse.data

      // Store tenant info for tenant identification
      Cookies.set('oneo_tenant', tenantData?.schema_name || 'unknown', {
        expires: 7,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'lax'
      })

      setUser({...userData, permissions})
      setTenant(tenantData as any)

      // Use setTimeout to ensure state updates are processed before redirect
      setTimeout(() => {
        const urlParams = new URLSearchParams(window.location.search)
        const redirectTo = urlParams.get('redirect') || '/dashboard'
        console.log('Redirecting to:', redirectTo)
        router.push(redirectTo)
      }, 100)
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
    Cookies.remove('oneo_tenant')
    setUser(null)
    setTenant(null)
  }

  const hasPermission = (category: string, action: string): boolean => {
    if (!user || !user.permissions) return false
    
    // Check system-level permissions first
    const systemPermissions = user.permissions.system || []
    if (systemPermissions.includes('full_access')) {
      return true
    }
    
    // Check category-specific permissions
    const categoryPermissions = user.permissions[category] || []
    return categoryPermissions.includes(action)
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