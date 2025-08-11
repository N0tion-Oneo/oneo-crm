// useFieldOptions - Hook for loading dynamic field options (tags, users, relations)
import { useState, useCallback, useMemo } from 'react'
import { Pipeline, RecordField, FieldOption } from '@/types/records'
import { RecordDataService } from '@/services/records'

export interface UseFieldOptionsReturn {
  fieldOptionsCache: Record<string, FieldOption[]>
  loading: Record<string, boolean>
  errors: Record<string, string>
  // Actions
  fetchFieldOptions: (fieldName: string, fieldType: string) => Promise<FieldOption[]>
  clearCache: (fieldName?: string) => void
  refreshFieldOptions: (fieldName: string, fieldType: string) => Promise<FieldOption[]>
  // Helpers
  getFieldOptions: (fieldName: string) => FieldOption[]
  isLoading: (fieldName: string) => boolean
  getError: (fieldName: string) => string | null
}

export function useFieldOptions(pipeline: Pipeline): UseFieldOptionsReturn {
  const [fieldOptionsCache, setFieldOptionsCache] = useState<Record<string, FieldOption[]>>({})
  const [loading, setLoading] = useState<Record<string, boolean>>({})
  const [errors, setErrors] = useState<Record<string, string>>({})

  const fetchFieldOptions = useCallback(async (
    fieldName: string, 
    fieldType: string
  ): Promise<FieldOption[]> => {
    // Return cached options if available
    if (fieldOptionsCache[fieldName]) {
      return fieldOptionsCache[fieldName]
    }

    // Set loading state
    setLoading(prev => ({ ...prev, [fieldName]: true }))
    setErrors(prev => ({ ...prev, [fieldName]: '' }))

    try {
      let options: FieldOption[] = []

      switch (fieldType) {
        case 'tags':
          options = await RecordDataService.fetchTagOptions(pipeline.id, fieldName)
          break

        case 'user':
          options = await RecordDataService.fetchUsers()
          break

        case 'relation':
        case 'relationship':
        case 'related':
          const field = pipeline.fields.find(f => f.name === fieldName)
          const targetPipelineId = field?.field_config?.target_pipeline_id || 
                                   field?.field_config?.target_pipeline
          const displayFieldSlug = field?.field_config?.display_field

          if (targetPipelineId) {
            options = await RecordDataService.fetchRelationOptions(
              targetPipelineId, 
              displayFieldSlug
            )
          }
          break

        case 'select':
        case 'multiselect':
          // For select fields, options come from field configuration
          const selectField = pipeline.fields.find(f => f.name === fieldName)
          if (selectField?.field_config?.options) {
            options = selectField.field_config.options.map((option: any) => ({
              value: option.value || option,
              label: option.label || option.value || option
            }))
          }
          break

        default:
          options = []
      }

      // Cache the options
      setFieldOptionsCache(prev => ({ ...prev, [fieldName]: options }))
      return options

    } catch (error: any) {
      console.error(`Failed to fetch options for field ${fieldName}:`, error)
      const errorMessage = error?.message || 'Failed to load field options'
      setErrors(prev => ({ ...prev, [fieldName]: errorMessage }))
      return []
    } finally {
      setLoading(prev => ({ ...prev, [fieldName]: false }))
    }
  }, [pipeline.id, pipeline.fields, fieldOptionsCache])

  const clearCache = useCallback((fieldName?: string) => {
    if (fieldName) {
      setFieldOptionsCache(prev => {
        const newCache = { ...prev }
        delete newCache[fieldName]
        return newCache
      })
    } else {
      setFieldOptionsCache({})
    }
  }, [])

  const refreshFieldOptions = useCallback(async (
    fieldName: string, 
    fieldType: string
  ): Promise<FieldOption[]> => {
    // Clear cached options first
    clearCache(fieldName)
    // Fetch fresh options
    return fetchFieldOptions(fieldName, fieldType)
  }, [clearCache, fetchFieldOptions])

  const getFieldOptions = useCallback((fieldName: string): FieldOption[] => {
    return fieldOptionsCache[fieldName] || []
  }, [fieldOptionsCache])

  const isLoading = useCallback((fieldName: string): boolean => {
    return loading[fieldName] || false
  }, [loading])

  const getError = useCallback((fieldName: string): string | null => {
    return errors[fieldName] || null
  }, [errors])

  return {
    fieldOptionsCache,
    loading,
    errors,
    fetchFieldOptions,
    clearCache,
    refreshFieldOptions,
    getFieldOptions,
    isLoading,
    getError
  }
}