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
  
  // Debug logging to help troubleshoot
  console.log('🔧 API Base URL generated:', {
    currentHost,
    fullUrl: window.location.href,
    generatedBaseUrl: baseUrl
  })
  
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
    
    // Debug: Log the full URL being called
    const fullUrl = `${config.baseURL}${config.url}`
    console.log('🌐 API Request:', config.method?.toUpperCase(), fullUrl)
    
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
  (response) => response,
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
}

// Forms API - New unified endpoints
export const formsApi = {
  // Validation rules
  getValidationRules: () => api.get('/api/v1/validation-rules/'),
  getValidationRule: (id: string) => api.get(`/api/v1/validation-rules/${id}/`),
  createValidationRule: (data: any) => api.post('/api/v1/validation-rules/', data),
  updateValidationRule: (id: string, data: any) => api.patch(`/api/v1/validation-rules/${id}/`, data),
  deleteValidationRule: (id: string) => api.delete(`/api/v1/validation-rules/${id}/`),
  testValidationRule: (id: string, data: any) => api.post(`/api/v1/validation-rules/${id}/test_rule/`, data),
  
  // Enhanced validation endpoints (using new metadata endpoint)
  getRuleTypes: () => api.get('/api/v1/validation-metadata/?type=rule_types'),
  getPatternLibrary: (category?: string) => api.get(`/api/v1/validation-metadata/?type=pattern_library${category ? `&category=${category}` : ''}`),
  validateCrossField: (data: any) => api.post('/api/v1/validation-rules/validate_cross_field/', data),
  testBusinessRule: (data: any) => api.post('/api/v1/validation-rules/test_business_rule/', data),
  testRule: (data: any) => api.post('/api/v1/validation-metadata/', { action: 'test_rule', ...data }),
  
  // External API validation services
  testExternalValidation: (data: any) => api.post('/api/v1/validation-rules/test_external/', data),
  getValidationServices: () => api.get('/api/v1/validation-rules/external_services/'),
  testApiConnection: (data: any) => api.post('/api/v1/validation-rules/test_connection/', data),
  
  // Form templates
  getForms: () => api.get('/api/v1/forms/'),
  getForm: (id: string) => api.get(`/api/v1/forms/${id}/`),
  createForm: (data: any) => api.post('/api/v1/forms/', data),
  updateForm: (id: string, data: any) => api.patch(`/api/v1/forms/${id}/`, data),
  deleteForm: (id: string) => api.delete(`/api/v1/forms/${id}/`),
  
  // Form validation and submission
  validateForm: (id: string, data: any) => api.post(`/api/v1/forms/${id}/validate_form/`, data),
  submitForm: (id: string, data: any) => api.post(`/api/v1/forms/${id}/submit_form/`, data),
  getFormAnalytics: (id: string, params?: any) => api.get(`/api/v1/forms/${id}/analytics/`, { params }),
  
  // Form field configurations
  getFormFields: () => api.get('/api/v1/form-fields/'),
  getFormField: (id: string) => api.get(`/api/v1/form-fields/${id}/`),
  createFormField: (data: any) => api.post('/api/v1/form-fields/', data),
  updateFormField: (id: string, data: any) => api.patch(`/api/v1/form-fields/${id}/`, data),
  deleteFormField: (id: string) => api.delete(`/api/v1/form-fields/${id}/`),
  
  // Form submissions
  getFormSubmissions: () => api.get('/api/v1/form-submissions/'),
  getFormSubmission: (id: string) => api.get(`/api/v1/form-submissions/${id}/`),
  
  // Public forms (no authentication required)
  getPublicForms: () => api.get('/api/v1/public-forms/'),
  getPublicForm: (slug: string) => api.get(`/api/v1/public-forms/${slug}/`),
  submitPublicForm: (slug: string, data: any) => api.post(`/api/v1/public-forms/${slug}/submit/`, data),
}

// Duplicates API - New unified endpoints
export const duplicatesApi = {
  // Duplicate rules
  getDuplicateRules: () => api.get('/api/v1/duplicate-rules/'),
  getDuplicateRule: (id: string) => api.get(`/api/v1/duplicate-rules/${id}/`),
  createDuplicateRule: (data: any) => api.post('/api/v1/duplicate-rules/', data),
  updateDuplicateRule: (id: string, data: any) => api.patch(`/api/v1/duplicate-rules/${id}/`, data),
  deleteDuplicateRule: (id: string) => api.delete(`/api/v1/duplicate-rules/${id}/`),
  testDuplicateRule: (id: string, data: any) => api.post(`/api/v1/duplicate-rules/${id}/detect/`, data),
  
  // Duplicate matches
  getDuplicateMatches: () => api.get('/api/v1/duplicate-matches/'),
  getDuplicateMatch: (id: string) => api.get(`/api/v1/duplicate-matches/${id}/`),
  resolveDuplicateMatch: (id: string, data: any) => api.post(`/api/v1/duplicate-matches/${id}/resolve/`, data),
  bulkResolveDuplicates: (data: any) => api.post('/api/v1/duplicate-matches/bulk_resolve/', data),
  
  // Duplicate analytics
  getDuplicateAnalytics: () => api.get('/api/v1/duplicate-analytics/'),
  getDuplicateStatistics: () => api.get('/api/v1/duplicate-analytics/statistics/'),
  
  // Duplicate exclusions
  getDuplicateExclusions: () => api.get('/api/v1/duplicate-exclusions/'),
  createDuplicateExclusion: (data: any) => api.post('/api/v1/duplicate-exclusions/', data),
  deleteDuplicateExclusion: (id: string) => api.delete(`/api/v1/duplicate-exclusions/${id}/`),
}

export default api