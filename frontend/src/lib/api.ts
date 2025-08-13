import axios, { AxiosInstance, AxiosRequestConfig } from 'axios'
import Cookies from 'js-cookie'

// API Configuration - Dynamic URL based on current hostname
const getApiBaseUrl = () => {
  if (typeof window === 'undefined') {
    // Server-side: use environment variable or default
    return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  }
  
  // Client-side: use current hostname but change port to 8000
  const currentHost = window.location.hostname
  const port = '8000'
  const baseUrl = `http://${currentHost}:${port}`
  
  // Debug logging in development only
  if (process.env.NODE_ENV === 'development') {
    console.log('🔧 API Base URL generated:', {
      currentHost,
      generatedBaseUrl: baseUrl
    })
  }
  
  return baseUrl
}

// Create axios instance with dynamic base URL
export const api: AxiosInstance = axios.create({
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
})

// Request interceptor to add JWT tokens and dynamic base URL
api.interceptors.request.use(
  (config) => {
    // Set dynamic base URL
    config.baseURL = getApiBaseUrl()
    
    // API request logging in development only
    if (process.env.NODE_ENV === 'development') {
      const fullUrl = `${config.baseURL}${config.url}`
      console.log(`🟠 API STEP 1: HTTP Request Outgoing`)
      console.log(`   🌐 ${config.method?.toUpperCase()} ${fullUrl}`)
    }
    
    // Add JWT token if available
    const accessToken = Cookies.get('oneo_access_token')
    if (accessToken) {
      config.headers['Authorization'] = `Bearer ${accessToken}`
    }

    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor to handle authentication errors and token refresh
api.interceptors.response.use(
  (response) => {
    // API response logging in development only
    if (process.env.NODE_ENV === 'development') {
      console.log(`🟠 API STEP 2: HTTP Response Received`)
      console.log(`   ✅ ${response.status} ${response.config.method?.toUpperCase()} ${response.config.url}`)
    }
    return response
  },
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      // Try to refresh the token
      const refreshToken = Cookies.get('oneo_refresh_token')
      if (refreshToken) {
        try {
          const response = await axios.post(`${getApiBaseUrl()}/auth/token/refresh/`, {
            refresh: refreshToken
          })
          
          const { access } = response.data
          
          // Update the stored token
          Cookies.set('oneo_access_token', access, {
            expires: 1/24, // 1 hour
            secure: process.env.NODE_ENV === 'production',
            sameSite: 'lax'
          })
          
          // Retry the original request with new token
          originalRequest.headers['Authorization'] = `Bearer ${access}`
          return api(originalRequest)
        } catch (refreshError) {
          // Refresh failed, clear tokens and redirect to login
          Cookies.remove('oneo_access_token')
          Cookies.remove('oneo_refresh_token')
          Cookies.remove('oneo_tenant')
          
          if (typeof window !== 'undefined') {
            window.location.href = '/login'
          }
        }
      } else {
        // No refresh token, clear auth data and redirect to login
        Cookies.remove('oneo_access_token')
        Cookies.remove('oneo_refresh_token')
        Cookies.remove('oneo_tenant')
        
        if (typeof window !== 'undefined') {
          window.location.href = '/login'
        }
      }
      
      return Promise.reject(error)
    }

    return Promise.reject(error)
  }
)

// API methods - Updated to use JWT DRF endpoints
export const authApi = {
  login: async (credentials: { email: string; password: string }) => {
    const response = await api.post('/auth/login/', credentials)
    
    // Store JWT tokens
    const { access, refresh, user, permissions } = response.data
    
    Cookies.set('oneo_access_token', access, {
      expires: 1/24, // 1 hour
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax'
    })
    
    Cookies.set('oneo_refresh_token', refresh, {
      expires: 7, // 7 days
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax'
    })
    
    return {
      data: {
        user,
        permissions,
        message: 'Login successful'
      }
    }
  },
  
  register: (userData: { 
    first_name: string
    last_name: string
    email: string
    password: string
    organization_name: string
    subdomain: string
  }) =>
    api.post('/api/tenants/register/', userData),
  
  checkSubdomainAvailability: (subdomain: string) =>
    api.get(`/api/tenants/check-subdomain/?subdomain=${encodeURIComponent(subdomain)}`),
  
  logout: async () => {
    const refreshToken = Cookies.get('oneo_refresh_token')
    
    try {
      // Call logout endpoint with refresh token
      await api.post('/auth/logout/', { 
        refresh_token: refreshToken 
      })
    } catch (error) {
      // Continue with logout even if server call fails
      console.warn('Logout API call failed:', error)
    }
    
    // Clear all tokens
    Cookies.remove('oneo_access_token')
    Cookies.remove('oneo_refresh_token')
    Cookies.remove('oneo_tenant')
    
    return {
      data: {
        message: 'Logged out successfully'
      }
    }
  },
  
  getCurrentUser: async () => {
    const response = await api.get('/auth/me/')
    return {
      data: response.data.user
    }
  },
  
  getCurrentTenant: () => {
    // For now, we'll extract tenant info from the current hostname
    if (typeof window === 'undefined') {
      return Promise.resolve({ data: null })
    }
    
    const hostname = window.location.hostname
    const subdomain = hostname.split('.')[0]
    
    // Mock tenant data based on subdomain
    return Promise.resolve({
      data: {
        name: subdomain.charAt(0).toUpperCase() + subdomain.slice(1),
        schema_name: subdomain,
        subdomain: subdomain
      }
    })
  },
}

export const tenantsApi = {
  list: () =>
    api.get('/api/tenants/'),
  
  get: (id: string) =>
    api.get(`/api/tenants/${id}/`),
  
  create: (data: any) =>
    api.post('/api/tenants/', data),
  
  update: (id: string, data: any) =>
    api.patch(`/api/tenants/${id}/`, data),
  
  delete: (id: string) =>
    api.delete(`/api/tenants/${id}/`),
  
  getDomains: (tenantId: string) =>
    api.get(`/api/tenants/${tenantId}/domains/`),
  
  createDomain: (tenantId: string, data: any) =>
    api.post(`/api/tenants/${tenantId}/domains/`, data),
}

export const usersApi = {
  list: () =>
    api.get('/auth/users/'),
  
  get: (id: string) =>
    api.get(`/auth/users/${id}/`),
  
  create: (data: any) =>
    api.post('/auth/users/', data),
  
  update: (id: string, data: any) =>
    api.patch(`/auth/users/${id}/`, data),
  
  delete: (id: string) =>
    api.delete(`/auth/users/${id}/`),
  
  // Current user profile
  profile: () =>
    api.get('/auth/me/'),
  
  updateProfile: (data: any) =>
    api.patch('/auth/me/', data),
  
  invite: (data: { email: string; userTypeId: string }) =>
    api.post('/auth/users/invite/', data),
}

export const permissionsApi = {
  getUserTypes: () =>
    api.get('/auth/user-types/'),
  
  getUserPermissions: () =>
    api.get('/auth/me/').then(res => res.data.permissions),
  
  checkPermission: (resourceType: string, resource: string, action: string, resourceId?: string) => {
    const params = new URLSearchParams({ resource_type: resourceType, resource, action })
    if (resourceId) params.append('resource_id', resourceId)
    return api.get(`/auth/check-permission/?${params.toString()}`)
  },
  
  getUserTypePermissions: (userTypeId: string) =>
    api.get(`/auth/user-types/${userTypeId}/`),
  
  updateUserTypePermissions: (userTypeId: string, permissions: any) =>
    api.patch(`/auth/user-types/${userTypeId}/`, { permissions }),
}

export const pipelinesApi = {
  list: () =>
    api.get('/api/pipelines/'),
  
  get: (id: string) =>
    api.get(`/api/pipelines/${id}/`),
  
  create: (data: any) =>
    api.post('/api/pipelines/', data),
  
  update: (id: string, data: any) =>
    api.patch(`/api/pipelines/${id}/`, data),
  
  delete: (id: string) =>
    api.delete(`/api/pipelines/${id}/`),
  
  // Field management - using nested API structure consistently
  getFields: (pipelineId: string) =>
    api.get(`/api/pipelines/${pipelineId}/fields/`),
  
  createField: (pipelineId: string, data: any) =>
    api.post(`/api/pipelines/${pipelineId}/fields/`, data),
  
  updateField: (pipelineId: string, fieldId: string, data: any) =>
    api.patch(`/api/pipelines/${pipelineId}/fields/${fieldId}/`, data),
  
  deleteField: (pipelineId: string, fieldId: string) =>
    api.delete(`/api/pipelines/${pipelineId}/fields/${fieldId}/`),

  // Advanced field lifecycle management (nested under pipelines)
  manageField: (pipelineId: string, fieldId: string, action: 'soft_delete' | 'restore' | 'schedule_hard_delete' | 'impact_analysis', data?: any) =>
    api.post(`/api/pipelines/${pipelineId}/fields/${fieldId}/manage/`, { action, ...data }),

  // Migration validation and execution
  validateMigration: (pipelineId: string, fieldId: string, data: { new_config: any; include_impact_preview?: boolean }) =>
    api.post(`/api/pipelines/${pipelineId}/fields/${fieldId}/validate_migration/`, data),

  migrateFieldSchema: (pipelineId: string, fieldId: string, data: { new_config: any; dry_run?: boolean; batch_size?: number; force?: boolean }) =>
    api.post(`/api/pipelines/${pipelineId}/fields/${fieldId}/migrate_schema/`, data),

  // Enhanced field recovery endpoints (using nested router structure)
  getDeletedFields: (pipelineId: string) =>
    api.get(`/api/pipelines/${pipelineId}/fields/deleted/`),

  restoreField: (pipelineId: string, fieldId: string, options: { reason?: string; dry_run?: boolean; force?: boolean } = {}) =>
    api.post(`/api/pipelines/${pipelineId}/fields/${fieldId}/restore/`, options),

  bulkRestoreFields: (pipelineId: string, data: { field_ids: string[]; reason?: string; force?: boolean }) =>
    api.post(`/api/pipelines/${pipelineId}/fields/bulk_restore/`, data),

  // Legacy global endpoints (for backward compatibility)
  getAllDeletedFields: () =>
    api.get('/api/fields/deleted/'),

  getScheduledFields: () =>
    api.get('/api/fields/scheduled_for_deletion/'),

  getMigrationStatus: (taskId: string) =>
    api.get('/api/fields/migration_status/', { params: { task_id: taskId } }),

  validateFieldValue: (pipelineId: string, fieldId: string, value: any, isRequired?: boolean) =>
    api.post(`/api/pipelines/${pipelineId}/fields/${fieldId}/validate_value/`, { value, is_required: isRequired }),
  
  // Field Groups management
  getFieldGroups: (pipelineId: string) =>
    api.get(`/api/pipelines/${pipelineId}/field-groups/`),
  
  createFieldGroup: (pipelineId: string, data: any) =>
    api.post(`/api/pipelines/${pipelineId}/field-groups/`, data),
  
  updateFieldGroup: (pipelineId: string, groupId: string, data: any) =>
    api.patch(`/api/pipelines/${pipelineId}/field-groups/${groupId}/`, data),
  
  deleteFieldGroup: (pipelineId: string, groupId: string) =>
    api.delete(`/api/pipelines/${pipelineId}/field-groups/${groupId}/`),
  
  reorderFieldGroups: (pipelineId: string, groupOrders: { id: string; display_order: number }[]) =>
    api.post(`/api/pipelines/${pipelineId}/field-groups/reorder/`, { group_orders: groupOrders }),
  
  assignFieldsToGroup: (pipelineId: string, groupId: string, fieldIds: string[]) =>
    api.post(`/api/pipelines/${pipelineId}/field-groups/${groupId}/assign_fields/`, { field_ids: fieldIds }),
  
  ungroupFields: (pipelineId: string, groupId: string, fieldIds: string[]) =>
    api.post(`/api/pipelines/${pipelineId}/field-groups/${groupId}/ungroup_fields/`, { field_ids: fieldIds }),
  
  // Record management
  getRecords: (pipelineId: string, params?: any) =>
    api.get(`/api/pipelines/${pipelineId}/records/`, { params }),
  
  getRecord: (pipelineId: string, recordId: string) =>
    api.get(`/api/pipelines/${pipelineId}/records/${recordId}/`),
  
  createRecord: (pipelineId: string, data: any) =>
    api.post(`/api/pipelines/${pipelineId}/records/`, data),
  
  updateRecord: (pipelineId: string, recordId: string, data: any) =>
    api.patch(`/api/pipelines/${pipelineId}/records/${recordId}/`, data),
  
  // Soft delete (default) - can be restored
  deleteRecord: (pipelineId: string, recordId: string) =>
    api.post(`/api/pipelines/${pipelineId}/records/${recordId}/soft_delete/`),
  
  // Hard delete (permanent) - cannot be restored  
  hardDeleteRecord: (pipelineId: string, recordId: string) =>
    api.delete(`/api/pipelines/${pipelineId}/records/${recordId}/`),
  
  // Restore soft-deleted record
  restoreRecord: (pipelineId: string, recordId: string) =>
    api.post(`/api/pipelines/${pipelineId}/records/${recordId}/restore/`),
  
  // Get deleted records
  getDeletedRecords: (pipelineId: string, params?: any) =>
    api.get(`/api/pipelines/${pipelineId}/records/deleted/`, { params }),
  
  // Bulk operations
  bulkUpdateRecords: (pipelineId: string, data: any) =>
    api.post(`/api/records/bulk_update/`, { ...data, pipeline: parseInt(pipelineId) }),
  
  bulkDeleteRecords: (pipelineId: string, data: any) =>
    api.post(`/api/records/bulk_delete/`, { ...data, pipeline: parseInt(pipelineId) }),
  
  // Export
  exportRecords: (pipelineId: string, format: 'csv' | 'json' | 'excel', params?: any) =>
    api.get(`/api/records/export/`, { 
      params: { ...params, format, pipeline: parseInt(pipelineId) },
      responseType: 'blob'
    }),
  
  // Pipeline templates
  getTemplates: () =>
    api.get('/api/templates/'),
  
  createFromTemplate: (templateId: string, data: any) =>
    api.post(`/api/pipelines/from_template/`, { template_id: templateId, ...data }),
}

export const recordsApi = {
  // Global search across all pipelines
  globalSearch: (query: string, params?: any) =>
    api.get('/api/search/', { params: { q: query, ...params } }),
  
  // Record activity/history
  getRecordActivity: (pipelineId: string, recordId: string) =>
    api.get(`/api/pipelines/${pipelineId}/records/${recordId}/history/`),
  
  // Record comments (placeholder - endpoint may not exist)
  getRecordComments: (pipelineId: string, recordId: string) =>
    api.get(`/api/pipelines/${pipelineId}/records/${recordId}/comments/`),
  
  createRecordComment: (pipelineId: string, recordId: string, data: any) =>
    api.post(`/api/pipelines/${pipelineId}/records/${recordId}/comments/`, data),
  
  // Record relationships (using correct nested endpoint)
  getRecordRelationships: (pipelineId: string, recordId: string) =>
    api.get(`/api/pipelines/${pipelineId}/records/${recordId}/relationships/`),
  
  createRecordRelationship: (pipelineId: string, recordId: string, data: any) =>
    api.post(`/api/pipelines/${pipelineId}/records/${recordId}/relationships/`, data),
  
  // Share link generation (encrypted sharing)
  generateShareLink: (pipelineId: string, recordId: string, data?: { 
    access_mode?: 'readonly' | 'editable'
    intended_recipient_email?: string 
  }) =>
    api.post(`/api/pipelines/${pipelineId}/records/${recordId}/generate_share_link/`, data || {}),
  
  previewSharedForm: (pipelineId: string, recordId: string) =>
    api.get(`/api/pipelines/${pipelineId}/records/${recordId}/preview_shared_form/`),
  
  // Sharing history and management
  getSharingHistory: (pipelineId: string, recordId: string) =>
    api.get(`/api/pipelines/${pipelineId}/records/${recordId}/sharing-history/`),
  
  getShareAccessLogs: (shareId: string) =>
    api.get(`/api/shared-record-history/${shareId}/access_logs/`),
  
  revokeShare: (shareId: string, data?: { reason?: string }) =>
    api.post(`/api/shared-record-history/${shareId}/revoke/`, data || {}),
  
  // Global sharing analytics
  getSharingAnalytics: () =>
    api.get('/api/shared-record-history/analytics/'),
}

// Shared Records API (no authentication required)
export const sharedRecordsApi = {
  // Access shared record via encrypted token
  getSharedRecord: (encryptedToken: string) =>
    api.get(`/api/v1/shared-records/${encryptedToken}/`),
  
  // Get analytics for shared record access
  getSharedRecordAnalytics: (encryptedToken: string) =>
    api.get(`/api/v1/shared-records/${encryptedToken}/analytics/`),
}

// Field Types API
export const fieldTypesApi = {
  getAll: () => api.get('/api/field-types/'),
  get: (fieldType: string) => api.get(`/api/field-types/${fieldType}/`),
  getConfigSchema: (fieldType: string) => api.get(`/api/field-types/${fieldType}/config_schema/`),
  getCategories: () => api.get('/api/field-types/categories/'),
}

// Global Options API  
export const globalOptionsApi = {
  getAll: () => api.get('/api/global-options/'),
  getCurrencies: () => api.get('/api/global-options/currencies/'),
  getCountries: () => api.get('/api/global-options/countries/'),
  getOpenAIModels: () => api.get('/api/global-options/openai_models/'),
  getRecordDataOptions: () => api.get('/api/global-options/record_data_options/'),
  getUserTypes: () => api.get('/api/global-options/user_types/'),
}

// Relationships API - For relationship types and management
export const relationshipsApi = {
  // Relationship Types
  getRelationshipTypes: () =>
    api.get('/api/relationship-types/'),
    
  getRelationshipType: (id: string) =>
    api.get(`/api/relationship-types/${id}/`),
    
  // Relationships
  getRelationships: (params?: any) =>
    api.get('/api/relationships/', { params }),
    
  createRelationship: (data: any) =>
    api.post('/api/relationships/', data),
    
  updateRelationship: (id: string, data: any) =>
    api.patch(`/api/relationships/${id}/`, data),
    
  deleteRelationship: (id: string) =>
    api.delete(`/api/relationships/${id}/`),
}

// Duplicates API - Pipeline-scoped endpoints
export const duplicatesApi = {
  // Duplicate rules (pipeline-scoped)
  getDuplicateRules: (pipelineId?: string) => {
    const url = pipelineId ? `/api/v1/pipelines/${pipelineId}/duplicate-rules/` : '/api/v1/duplicate-rules/'
    return api.get(url)
  },
  getDuplicateRule: (id: string, pipelineId?: string) => {
    const url = pipelineId ? `/api/v1/pipelines/${pipelineId}/duplicate-rules/${id}/` : `/api/v1/duplicate-rules/${id}/`
    return api.get(url)
  },
  createDuplicateRule: (data: any, pipelineId?: string) => {
    const url = pipelineId ? `/api/v1/pipelines/${pipelineId}/duplicate-rules/` : '/api/v1/duplicate-rules/'
    return api.post(url, data)
  },
  updateDuplicateRule: (id: string, data: any, pipelineId?: string) => {
    const url = pipelineId ? `/api/v1/pipelines/${pipelineId}/duplicate-rules/${id}/` : `/api/v1/duplicate-rules/${id}/`
    return api.patch(url, data)
  },
  deleteDuplicateRule: (id: string, pipelineId?: string) => {
    const url = pipelineId ? `/api/v1/pipelines/${pipelineId}/duplicate-rules/${id}/` : `/api/v1/duplicate-rules/${id}/`
    return api.delete(url)
  },
  testDuplicateRule: (id: string, data: any, pipelineId?: string) => {
    const url = pipelineId ? `/api/v1/pipelines/${pipelineId}/duplicate-rules/${id}/test_rule/` : `/api/v1/duplicate-rules/${id}/test_rule/`
    return api.post(url, data)
  },
  
  // URL extraction rules (pipeline-scoped)
  getUrlExtractionRules: (pipelineId?: string) => {
    const url = pipelineId ? `/api/v1/pipelines/${pipelineId}/url-extraction-rules/` : '/api/v1/url-extraction-rules/'
    return api.get(url)
  },
  getUrlExtractionRule: (id: string, pipelineId?: string) => {
    const url = pipelineId ? `/api/v1/pipelines/${pipelineId}/url-extraction-rules/${id}/` : `/api/v1/url-extraction-rules/${id}/`
    return api.get(url)
  },
  createUrlExtractionRule: (data: any, pipelineId?: string) => {
    const url = pipelineId ? `/api/v1/pipelines/${pipelineId}/url-extraction-rules/` : '/api/v1/url-extraction-rules/'
    return api.post(url, data)
  },
  updateUrlExtractionRule: (id: string, data: any, pipelineId?: string) => {
    const url = pipelineId ? `/api/v1/pipelines/${pipelineId}/url-extraction-rules/${id}/` : `/api/v1/url-extraction-rules/${id}/`
    return api.patch(url, data)
  },
  deleteUrlExtractionRule: (id: string, pipelineId?: string) => {
    const url = pipelineId ? `/api/v1/pipelines/${pipelineId}/url-extraction-rules/${id}/` : `/api/v1/url-extraction-rules/${id}/`
    return api.delete(url)
  },
  testUrlExtractionRule: (id: string, data: any, pipelineId?: string) => {
    const url = pipelineId ? `/api/v1/pipelines/${pipelineId}/url-extraction-rules/${id}/test_extraction/` : `/api/v1/url-extraction-rules/${id}/test_extraction/`
    return api.post(url, data)
  },
  
  // Smart URL processor - live testing
  liveTestUrls: (data: any) => api.post('/api/v1/url-extraction-rules/live_test/', data),
  
  // Get duplicate count for record using duplicate-matches endpoint
  getRecordDuplicateCount: (recordId: string, pipelineId: string) => {
    return api.get(`/api/v1/pipelines/${pipelineId}/duplicate-matches/?record_id=${recordId}`)
  },
  
  // Merge records with field-level control
  mergeRecords: (data: any) => api.post('/api/v1/duplicate-matches/merge_records/', data),
  
  // Rollback resolution
  rollbackResolution: (data: any) => api.post('/api/v1/duplicate-matches/rollback_resolution/', data),
  
  // Duplicate matches (pipeline-scoped)
  getDuplicateMatches: (pipelineId?: string) => {
    const url = pipelineId ? `/api/v1/pipelines/${pipelineId}/duplicate-matches/` : '/api/v1/duplicate-matches/'
    return api.get(url)
  },
  getDuplicateMatch: (id: string, pipelineId?: string) => {
    const url = pipelineId ? `/api/v1/pipelines/${pipelineId}/duplicate-matches/${id}/` : `/api/v1/duplicate-matches/${id}/`
    return api.get(url)
  },
  resolveDuplicateMatch: (id: string, data: any, pipelineId?: string) => {
    const url = pipelineId ? `/api/v1/pipelines/${pipelineId}/duplicate-matches/${id}/resolve/` : `/api/v1/duplicate-matches/${id}/resolve/`
    return api.post(url, data)
  },
  bulkResolveDuplicates: (data: any, pipelineId?: string) => {
    const url = pipelineId ? `/api/v1/pipelines/${pipelineId}/duplicate-matches/bulk_resolve/` : '/api/v1/duplicate-matches/bulk_resolve/'
    return api.post(url, data)
  },
  
  // Duplicate analytics
  getDuplicateAnalytics: () => api.get('/api/v1/duplicate-analytics/'),
  getDuplicateStatistics: () => api.get('/api/v1/duplicate-analytics/statistics/'),
  
  // Duplicate exclusions
  getDuplicateExclusions: () => api.get('/api/v1/duplicate-exclusions/'),
  createDuplicateExclusion: (data: any) => api.post('/api/v1/duplicate-exclusions/', data),
  deleteDuplicateExclusion: (id: string) => api.delete(`/api/v1/duplicate-exclusions/${id}/`),
}

// AI API client functions
export const aiApi = {
  // Jobs
  jobs: {
    list: (params?: any) => api.get('/api/v1/ai-jobs/', { params }),
    create: (data: any) => api.post('/api/v1/ai-jobs/', data),
    get: (id: string) => api.get(`/api/v1/ai-jobs/${id}/`),
    retry: (id: string) => api.post(`/api/v1/ai-jobs/${id}/retry/`),
    cancel: (id: string) => api.post(`/api/v1/ai-jobs/${id}/cancel/`),
    analyze: (data: any) => api.post('/api/v1/ai-jobs/analyze/', data),
    tenantConfig: () => api.get('/api/v1/ai-jobs/tenant_config/'),
    updateTenantConfig: (data: any) => api.post('/api/v1/ai-jobs/update_tenant_config/', data),
    deleteApiKey: (provider: string) => api.post('/api/v1/ai-jobs/delete_api_key/', { provider })
  },
  
  // Usage Analytics
  analytics: {
    list: (params?: any) => api.get('/api/v1/ai-usage-analytics/', { params }),
    tenantSummary: (params?: any) => api.get('/api/v1/ai-usage-analytics/tenant_summary/', { params }),
    export: (params?: any) => api.get('/api/v1/ai-usage-analytics/export/', { params })
  },
  
  // Prompt Templates
  templates: {
    list: (params?: any) => api.get('/api/v1/ai-prompt-templates/', { params }),
    create: (data: any) => api.post('/api/v1/ai-prompt-templates/', data),
    get: (id: string) => api.get(`/api/v1/ai-prompt-templates/${id}/`),
    update: (id: string, data: any) => api.put(`/api/v1/ai-prompt-templates/${id}/`, data),
    delete: (id: string) => api.delete(`/api/v1/ai-prompt-templates/${id}/`),
    validate: (id: string, variables: any) => api.post(`/api/v1/ai-prompt-templates/${id}/validate_template/`, { variables }),
    clone: (id: string) => api.post(`/api/v1/ai-prompt-templates/${id}/clone/`)
  },
  
  // Embeddings & Semantic Search
  embeddings: {
    list: (params?: any) => api.get('/api/v1/ai-embeddings/', { params }),
    search: (params: any) => api.get('/api/v1/ai-embeddings/search/', { params }),
    generate: (data: any) => api.post('/api/v1/ai-embeddings/generate/', data)
  }
}

export default api