export interface User {
  id: string
  email: string
  username: string
  firstName: string
  lastName: string
  avatar?: string
  isActive: boolean
  isSuperuser: boolean
  userType: UserType
  tenantId: string
  permissions: UserPermissions
  lastActivity?: string
  createdAt: string
}

export interface UserType {
  id: string
  name: string
  slug: string
  description?: string
  basePermissions: Record<string, any>
  isSystemDefault: boolean
}

export interface UserPermissions {
  system: string[]
  pipelines: Record<string, string[]>
  users: string[]
  settings: string[]
  [key: string]: any
}

export interface LoginCredentials {
  email: string
  password: string
}

export interface LoginResponse {
  access: string
  refresh: string
  user: User
  tenant: Tenant
}

export interface Tenant {
  id: string
  name: string
  schemaName: string
  maxUsers: number
  featuresEnabled: Record<string, any>
  billingSettings: Record<string, any>
  aiEnabled: boolean
  aiUsageLimit: number
  aiCurrentUsage: number
  createdOn: string
  domains: TenantDomain[]
}

export interface TenantDomain {
  id: string
  domain: string
  isPrimary: boolean
  tenantId: string
}

export interface AuthContextType {
  user: User | null
  tenant: Tenant | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (credentials: LoginCredentials) => Promise<void>
  logout: () => Promise<void>
  refreshSession: () => Promise<void>
  hasPermission: (category: string, action: string) => boolean
  hasAnyPermission: (category: string, actions: string[]) => boolean
  hasAllPermissions: (category: string, actions: string[]) => boolean
}

export interface SessionToken {
  access: string
  refresh: string
  expiresAt: Date
}