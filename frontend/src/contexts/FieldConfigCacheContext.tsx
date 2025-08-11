'use client'

import React, { createContext, useContext, useState, useEffect, useCallback, useRef, ReactNode } from 'react'
import { fieldTypesApi, globalOptionsApi, relationshipsApi, aiApi, pipelinesApi } from '@/lib/api'

// Types for cached data
interface FieldTypeMetadata {
  key: string
  label: string
  description: string
  category: string
  icon: string
  config_schema: any
  supports_validation: boolean
  is_computed: boolean
  config_class: string
}

interface GlobalOptions {
  currencies: Array<{code: string; name: string; symbol: string}>
  countries: Array<{code: string; name: string; phone_code: string}>
  openai_models: Array<{key: string; name: string; description: string}>
  record_data_options: any
  userTypes: Array<{name: string; slug: string; description?: string}>
}

interface RelationshipType {
  id: number
  name: string
  slug: string
  description: string
  cardinality: string
  is_bidirectional: boolean
  forward_label: string
  reverse_label: string
}

interface Pipeline {
  id: string
  name: string
  slug: string
}

interface TenantAIConfig {
  available_models: string[]
  default_model: string
  api_key_configured: boolean
  usage_limits: any
}

interface CacheState {
  // Field types cache
  fieldTypes: Record<string, FieldTypeMetadata>
  fieldTypesLoading: boolean
  fieldTypesError: string | null
  
  // Global options cache  
  globalOptions: GlobalOptions | null
  globalOptionsLoading: boolean
  globalOptionsError: string | null
  
  // Relationship types cache
  relationshipTypes: RelationshipType[]
  relationshipTypesLoading: boolean
  relationshipTypesError: string | null
  
  // Pipelines cache
  pipelines: Pipeline[]
  pipelinesLoading: boolean
  pipelinesError: string | null
  
  // Tenant AI config cache
  tenantAIConfig: TenantAIConfig | null
  tenantAIConfigLoading: boolean
  tenantAIConfigError: string | null
  
  // Pipeline fields cache (keyed by pipeline ID)
  pipelineFields: Record<string, Array<{id: string; name: string; display_name: string; field_type: string}>>
  pipelineFieldsLoading: Record<string, boolean>
  pipelineFieldsError: Record<string, string | null>
}

interface FieldConfigCacheContextType extends CacheState {
  // Methods to load data
  loadFieldType: (fieldType: string) => Promise<FieldTypeMetadata | null>
  loadGlobalOptions: () => Promise<GlobalOptions | null>
  loadRelationshipTypes: () => Promise<RelationshipType[]>
  loadPipelines: () => Promise<Pipeline[]>
  loadTenantAIConfig: () => Promise<TenantAIConfig | null>
  loadPipelineFields: (pipelineId: string) => Promise<Array<{id: string; name: string; display_name: string; field_type: string}>>
  
  // Cache management
  invalidateCache: (cacheKey: keyof CacheState) => void
  refreshAll: () => Promise<void>
}

const FieldConfigCacheContext = createContext<FieldConfigCacheContextType | undefined>(undefined)

interface FieldConfigCacheProviderProps {
  children: ReactNode
}

export function FieldConfigCacheProvider({ children }: FieldConfigCacheProviderProps) {
  const [cacheState, setCacheState] = useState<CacheState>({
    fieldTypes: {},
    fieldTypesLoading: false,
    fieldTypesError: null,
    
    globalOptions: null,
    globalOptionsLoading: false,
    globalOptionsError: null,
    
    relationshipTypes: [],
    relationshipTypesLoading: false,
    relationshipTypesError: null,
    
    pipelines: [],
    pipelinesLoading: false,
    pipelinesError: null,
    
    tenantAIConfig: null,
    tenantAIConfigLoading: false,
    tenantAIConfigError: null,
    
    pipelineFields: {},
    pipelineFieldsLoading: {},
    pipelineFieldsError: {}
  })
  
  // Use ref to access current cache state in callbacks without dependencies
  const cacheStateRef = useRef(cacheState)
  useEffect(() => {
    cacheStateRef.current = cacheState
  }, [cacheState])

  // Load a specific field type
  const loadFieldType = useCallback(async (fieldType: string): Promise<FieldTypeMetadata | null> => {
    // Check cache first using ref for current state
    if (cacheStateRef.current.fieldTypes[fieldType]) {
      console.log(`[FieldConfigCache] Returning cached field type: ${fieldType}`)
      return cacheStateRef.current.fieldTypes[fieldType]
    }

    try {
      console.log(`[FieldConfigCache] Loading field type: ${fieldType}`)
      setCacheState(prev => ({ ...prev, fieldTypesLoading: true, fieldTypesError: null }))
      
      const response = await fieldTypesApi.get(fieldType)
      const metadata = response.data

      setCacheState(prev => ({
        ...prev,
        fieldTypes: { ...prev.fieldTypes, [fieldType]: metadata },
        fieldTypesLoading: false
      }))

      return metadata
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load field type'
      setCacheState(prev => ({
        ...prev,
        fieldTypesLoading: false,
        fieldTypesError: errorMessage
      }))
      return null
    }
  }, []) // No dependencies - stable function with ref access

  // Load global options (currencies, countries, etc.)
  const loadGlobalOptions = useCallback(async (): Promise<GlobalOptions | null> => {
    // Check cache first
    if (cacheState.globalOptions) {
      return cacheState.globalOptions
    }

    try {
      setCacheState(prev => ({ ...prev, globalOptionsLoading: true, globalOptionsError: null }))
      
      const response = await globalOptionsApi.getAll()
      const options = response.data

      setCacheState(prev => ({
        ...prev,
        globalOptions: options,
        globalOptionsLoading: false
      }))

      return options
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load global options'
      setCacheState(prev => ({
        ...prev,
        globalOptionsLoading: false,
        globalOptionsError: errorMessage
      }))
      return null
    }
  }, [cacheState.globalOptions])

  // Load relationship types
  const loadRelationshipTypes = useCallback(async (): Promise<RelationshipType[]> => {
    // Check cache first
    if (cacheState.relationshipTypes.length > 0) {
      return cacheState.relationshipTypes
    }

    try {
      setCacheState(prev => ({ ...prev, relationshipTypesLoading: true, relationshipTypesError: null }))
      
      const response = await relationshipsApi.getRelationshipTypes()
      
      // Handle different response structures
      let types: RelationshipType[] = []
      if (Array.isArray(response.data)) {
        types = response.data
      } else if (response.data?.results && Array.isArray(response.data.results)) {
        types = response.data.results
      } else if (response.data?.relationship_types && Array.isArray(response.data.relationship_types)) {
        types = response.data.relationship_types
      }

      setCacheState(prev => ({
        ...prev,
        relationshipTypes: types,
        relationshipTypesLoading: false
      }))

      return types
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load relationship types'
      setCacheState(prev => ({
        ...prev,
        relationshipTypesLoading: false,
        relationshipTypesError: errorMessage
      }))
      return []
    }
  }, [cacheState.relationshipTypes])

  // Load pipelines
  const loadPipelines = useCallback(async (): Promise<Pipeline[]> => {
    // Check cache first
    if (cacheState.pipelines.length > 0) {
      return cacheState.pipelines
    }

    try {
      setCacheState(prev => ({ ...prev, pipelinesLoading: true, pipelinesError: null }))
      
      const response = await pipelinesApi.list()
      const pipelines = response.data.results || []

      setCacheState(prev => ({
        ...prev,
        pipelines,
        pipelinesLoading: false
      }))

      return pipelines
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load pipelines'
      setCacheState(prev => ({
        ...prev,
        pipelinesLoading: false,
        pipelinesError: errorMessage
      }))
      return []
    }
  }, [cacheState.pipelines])

  // Load tenant AI config
  const loadTenantAIConfig = useCallback(async (): Promise<TenantAIConfig | null> => {
    // Check cache first
    if (cacheState.tenantAIConfig) {
      return cacheState.tenantAIConfig
    }

    try {
      setCacheState(prev => ({ ...prev, tenantAIConfigLoading: true, tenantAIConfigError: null }))
      
      const response = await aiApi.jobs.tenantConfig()
      const config = response.data

      setCacheState(prev => ({
        ...prev,
        tenantAIConfig: config,
        tenantAIConfigLoading: false
      }))

      return config
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load tenant AI config'
      setCacheState(prev => ({
        ...prev,
        tenantAIConfigLoading: false,
        tenantAIConfigError: errorMessage
      }))
      return null
    }
  }, [cacheState.tenantAIConfig])

  // Load pipeline fields
  const loadPipelineFields = useCallback(async (pipelineId: string) => {
    // Check cache first
    if (cacheState.pipelineFields[pipelineId]) {
      return cacheState.pipelineFields[pipelineId]
    }

    try {
      setCacheState(prev => ({
        ...prev,
        pipelineFieldsLoading: { ...prev.pipelineFieldsLoading, [pipelineId]: true },
        pipelineFieldsError: { ...prev.pipelineFieldsError, [pipelineId]: null }
      }))
      
      const response = await pipelinesApi.getFields(pipelineId)
      
      // Handle different response structures
      let fields = []
      if (Array.isArray(response.data)) {
        fields = response.data
      } else if (response.data?.results && Array.isArray(response.data.results)) {
        fields = response.data.results
      } else if (response.data?.fields && Array.isArray(response.data.fields)) {
        fields = response.data.fields
      }

      setCacheState(prev => ({
        ...prev,
        pipelineFields: { ...prev.pipelineFields, [pipelineId]: fields },
        pipelineFieldsLoading: { ...prev.pipelineFieldsLoading, [pipelineId]: false }
      }))

      return fields
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load pipeline fields'
      setCacheState(prev => ({
        ...prev,
        pipelineFieldsLoading: { ...prev.pipelineFieldsLoading, [pipelineId]: false },
        pipelineFieldsError: { ...prev.pipelineFieldsError, [pipelineId]: errorMessage }
      }))
      return []
    }
  }, [cacheState.pipelineFields])

  // Invalidate specific cache
  const invalidateCache = useCallback((cacheKey: keyof CacheState) => {
    setCacheState(prev => {
      const newState = { ...prev }
      
      switch (cacheKey) {
        case 'fieldTypes':
          newState.fieldTypes = {}
          newState.fieldTypesError = null
          break
        case 'globalOptions':
          newState.globalOptions = null
          newState.globalOptionsError = null
          break
        case 'relationshipTypes':
          newState.relationshipTypes = []
          newState.relationshipTypesError = null
          break
        case 'pipelines':
          newState.pipelines = []
          newState.pipelinesError = null
          break
        case 'tenantAIConfig':
          newState.tenantAIConfig = null
          newState.tenantAIConfigError = null
          break
        case 'pipelineFields':
          newState.pipelineFields = {}
          newState.pipelineFieldsError = {}
          break
      }
      
      return newState
    })
  }, [])

  // Refresh all cached data
  const refreshAll = useCallback(async () => {
    // Clear all caches
    setCacheState({
      fieldTypes: {},
      fieldTypesLoading: false,
      fieldTypesError: null,
      
      globalOptions: null,
      globalOptionsLoading: false,
      globalOptionsError: null,
      
      relationshipTypes: [],
      relationshipTypesLoading: false,
      relationshipTypesError: null,
      
      pipelines: [],
      pipelinesLoading: false,
      pipelinesError: null,
      
      tenantAIConfig: null,
      tenantAIConfigLoading: false,
      tenantAIConfigError: null,
      
      pipelineFields: {},
      pipelineFieldsLoading: {},
      pipelineFieldsError: {}
    })

    // Pre-load commonly used data
    await Promise.allSettled([
      loadGlobalOptions(),
      loadRelationshipTypes(),
      loadPipelines(),
      loadTenantAIConfig()
    ])
  }, [loadGlobalOptions, loadRelationshipTypes, loadPipelines, loadTenantAIConfig])

  // Pre-load critical data on mount
  useEffect(() => {
    const preloadData = async () => {
      try {
        // Load the most commonly used data immediately
        const results = await Promise.allSettled([
          loadGlobalOptions(),
          loadRelationshipTypes(),
          loadPipelines()
        ])
        
        // Log any failures for debugging
        results.forEach((result, index) => {
          if (result.status === 'rejected') {
            const names = ['globalOptions', 'relationshipTypes', 'pipelines']
            console.warn(`Failed to preload ${names[index]}:`, result.reason)
          }
        })
      } catch (error) {
        console.error('Error during preload:', error)
      }
    }

    preloadData()
  }, [loadGlobalOptions, loadRelationshipTypes, loadPipelines])

  const contextValue: FieldConfigCacheContextType = {
    ...cacheState,
    loadFieldType,
    loadGlobalOptions,
    loadRelationshipTypes,
    loadPipelines,
    loadTenantAIConfig,
    loadPipelineFields,
    invalidateCache,
    refreshAll
  }

  return (
    <FieldConfigCacheContext.Provider value={contextValue}>
      {children}
    </FieldConfigCacheContext.Provider>
  )
}

// Custom hook to use the cache context
export function useFieldConfigCache() {
  const context = useContext(FieldConfigCacheContext)
  if (context === undefined) {
    throw new Error('useFieldConfigCache must be used within a FieldConfigCacheProvider')
  }
  return context
}

// Convenience hooks for specific data types
export function useGlobalOptions() {
  const { globalOptions, globalOptionsLoading, globalOptionsError, loadGlobalOptions } = useFieldConfigCache()
  
  useEffect(() => {
    if (!globalOptions && !globalOptionsLoading && !globalOptionsError) {
      console.log('[useGlobalOptions] Loading global options...')
      loadGlobalOptions().catch(error => {
        console.error('[useGlobalOptions] Failed to load global options:', error)
      })
    }
  }, [globalOptions, globalOptionsLoading, globalOptionsError, loadGlobalOptions])

  // Debug logging for state changes (commented out for performance)
  // useEffect(() => {
  //   console.log('[useGlobalOptions] State:', {
  //     hasOptions: !!globalOptions,
  //     loading: globalOptionsLoading,
  //     error: globalOptionsError,
  //     currencies: globalOptions?.currencies?.length || 0,
  //     countries: globalOptions?.countries?.length || 0
  //   })
  // }, [globalOptions, globalOptionsLoading, globalOptionsError])

  return { globalOptions, loading: globalOptionsLoading, error: globalOptionsError }
}

export function useRelationshipTypes() {
  const { relationshipTypes, relationshipTypesLoading, relationshipTypesError, loadRelationshipTypes } = useFieldConfigCache()
  
  useEffect(() => {
    if (relationshipTypes.length === 0 && !relationshipTypesLoading && !relationshipTypesError) {
      console.log('[useRelationshipTypes] Loading relationship types...')
      loadRelationshipTypes().catch(error => {
        console.error('[useRelationshipTypes] Failed to load relationship types:', error)
      })
    }
  }, [relationshipTypes, relationshipTypesLoading, relationshipTypesError, loadRelationshipTypes])

  // Debug logging for state changes (commented out for performance)
  // useEffect(() => {
  //   console.log('[useRelationshipTypes] State:', {
  //     count: relationshipTypes.length,
  //     loading: relationshipTypesLoading,
  //     error: relationshipTypesError,
  //     types: relationshipTypes.map(t => ({ name: t.name, slug: t.slug }))
  //   })
  // }, [relationshipTypes, relationshipTypesLoading, relationshipTypesError])

  return { relationshipTypes, loading: relationshipTypesLoading, error: relationshipTypesError }
}

export function usePipelines() {
  const { pipelines, pipelinesLoading, pipelinesError, loadPipelines } = useFieldConfigCache()
  
  useEffect(() => {
    if (pipelines.length === 0 && !pipelinesLoading && !pipelinesError) {
      loadPipelines().catch(error => {
        console.error('usePipelines: Failed to load pipelines:', error)
      })
    }
  }, [pipelines, pipelinesLoading, pipelinesError, loadPipelines])

  return { pipelines, loading: pipelinesLoading, error: pipelinesError }
}

export function useTenantAIConfig() {
  const { tenantAIConfig, tenantAIConfigLoading, tenantAIConfigError, loadTenantAIConfig } = useFieldConfigCache()
  
  useEffect(() => {
    if (!tenantAIConfig && !tenantAIConfigLoading) {
      loadTenantAIConfig()
    }
  }, [tenantAIConfig, tenantAIConfigLoading, loadTenantAIConfig])

  return { tenantAIConfig, loading: tenantAIConfigLoading, error: tenantAIConfigError }
}

export function usePipelineFields(pipelineId: string) {
  const { pipelineFields, pipelineFieldsLoading, pipelineFieldsError, loadPipelineFields } = useFieldConfigCache()
  
  useEffect(() => {
    if (pipelineId && !pipelineFields[pipelineId] && !pipelineFieldsLoading[pipelineId]) {
      loadPipelineFields(pipelineId)
    }
  }, [pipelineId, pipelineFields, pipelineFieldsLoading, loadPipelineFields])

  return { 
    fields: pipelineFields[pipelineId] || [], 
    loading: pipelineFieldsLoading[pipelineId] || false, 
    error: pipelineFieldsError[pipelineId] || null 
  }
}

export function useFieldType(fieldType: string) {
  const { fieldTypes, fieldTypesLoading, fieldTypesError, loadFieldType } = useFieldConfigCache()
  
  useEffect(() => {
    if (fieldType && !fieldTypes[fieldType] && !fieldTypesLoading) {
      console.log(`[useFieldType] Loading field type: ${fieldType}`)
      loadFieldType(fieldType).catch(error => {
        console.error('[useFieldType] Failed to load field type:', error)
      })
    }
  }, [fieldType, fieldTypes, fieldTypesLoading, loadFieldType])

  // Debug logging for field type state (commented out for performance)
  // useEffect(() => {
  //   console.log('[useFieldType] State:', {
  //     fieldType,
  //     hasFieldType: !!fieldTypes[fieldType],
  //     loading: fieldTypesLoading,
  //     error: fieldTypesError
  //   })
  // }, [fieldType, fieldTypes, fieldTypesLoading, fieldTypesError])

  return { 
    fieldTypeConfig: fieldTypes[fieldType] || null, 
    loading: fieldTypesLoading, 
    error: fieldTypesError 
  }
}