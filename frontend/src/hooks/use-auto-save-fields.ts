import { useCallback, useRef, useEffect } from 'react'
import { api } from '@/lib/api'

interface AutoSaveOptions {
  delay?: number
  onSaveStart?: (field: any) => void
  onSaveSuccess?: (field: any) => void
  onSaveError?: (error: any, field: any) => void
  validateField?: (field: any, allFields: any[]) => string | null
  allFields?: any[]
}

export function useAutoSaveFields(pipelineId: string, options: AutoSaveOptions = {}) {
  const { delay = 1000, onSaveStart, onSaveSuccess, onSaveError, validateField, allFields = [] } = options
  const timeoutRefs = useRef<Map<string, NodeJS.Timeout>>(new Map())
  const pendingSaves = useRef<Set<string>>(new Set())

  const autoSaveField = useCallback(async (field: any) => {
    const fieldId = field.id
    
    // Debug field identification
    console.log('🔍 Field ID analysis:', {
      fieldId,
      fieldIdType: typeof fieldId,
      isNumber: !isNaN(Number(fieldId)),
      startsWithField: fieldId ? fieldId.toString().startsWith('field_') : false,
      fieldName: field.display_name || field.label || field.name
    })
    
    // Check if this is a new field (temporary ID or no ID)
    // Only consider it a new field if it has no ID or has a temporary placeholder ID
    const isNewField = !fieldId || (typeof fieldId === 'string' && fieldId.startsWith('field_') && !fieldId.match(/^\d+$/))
    
    // For new fields, check if they have the minimum required info to be valid
    if (isNewField) {
      const fieldName = field.display_name || field.label || field.name
      const fieldType = field.field_type || field.type
      
      // Skip if field name is clearly a placeholder/default value
      if (!fieldName || 
          fieldName === 'New Field' || 
          fieldName === 'Untitled Field' || 
          fieldName.startsWith('Field ') ||
          /^(Text|Number|Email|Phone|Select|Date|Boolean)\s+\d+$/.test(fieldName)) {
        console.warn('🚫 Auto-save skipped for new field: invalid or placeholder field name:', fieldName)
        return
      }
      
      // Check if field name already exists in the pipeline (only for truly new fields)
      const existingField = allFields.find(existingField => 
        existingField.id !== field.id && // Don't compare with itself
        !existingField.id?.toString().startsWith('field_') && // Ignore other new/temp fields
        (existingField.name === fieldName || 
         existingField.display_name === fieldName ||
         existingField.label === fieldName)
      )
      
      if (existingField) {
        console.warn('🚫 Auto-save skipped for new field: field name already exists:', fieldName, 'existing field ID:', existingField.id)
        return
      }
      
      // Skip if field doesn't have a valid field type set
      if (!fieldType || fieldType === '' || fieldType === 'select_type') {
        console.warn('🚫 Auto-save skipped for new field: missing field type')
        return
      }
      
      // Additional validation for specific field types that need configuration
      if (fieldType === 'select' || fieldType === 'multiselect') {
        const options = field.field_config?.options || field.config?.options
        if (!options || !Array.isArray(options) || options.length === 0) {
          console.warn('🚫 Auto-save skipped for select field: missing options')
          return
        }
      }
      
      // For relation fields, check if target pipeline is set
      if (fieldType === 'relation') {
        const targetPipelineId = field.field_config?.target_pipeline_id || field.config?.target_pipeline_id
        if (!targetPipelineId) {
          console.warn('🚫 Auto-save skipped for relation field: missing target pipeline ID')
          return
        }
      }
      
      // For AI fields, check if prompt is set
      if (fieldType === 'ai') {
        const aiPrompt = field.field_config?.ai_prompt || field.config?.ai_prompt
        if (!aiPrompt || aiPrompt.trim() === '') {
          console.warn('🚫 Auto-save skipped for AI field: missing AI prompt')
          return
        }
      }
      
      console.log('✅ New field ready for auto-save:', fieldName, 'type:', fieldType)
      console.log('🔍 Field data being validated:', {
        name: fieldName,
        field_type: fieldType,
        has_config: !!(field.field_config || field.config),
        config_keys: Object.keys(field.field_config || field.config || {}),
        display_name: field.display_name,
        label: field.label
      })
    }
    
    // Validate field before saving (for both new and existing fields)
    if (validateField) {
      const validationError = validateField(field, allFields)
      if (validationError) {
        console.warn('🚫 Auto-save skipped due to validation error:', validationError)
        // Only show error for existing fields, not new fields being created
        if (!isNewField) {
          onSaveError?.(new Error(validationError), field)
        }
        return
      }
    }
    
    // Helper function to generate slug from name
    const generateSlug = (name: string) => {
      return name
        .toLowerCase()
        .replace(/[^a-z0-9\s]/g, '') // Remove special characters
        .replace(/\s+/g, '_') // Replace spaces with underscores
        .replace(/_{2,}/g, '_') // Replace multiple underscores with single
        .replace(/^_|_$/g, '') // Remove leading/trailing underscores
    }
    
    const fieldName = field.display_name || field.label || field.name
    
    // Transform field data to API format - only include fields that should be updatable
    const apiField: any = {
      name: fieldName,
      slug: field.slug || generateSlug(fieldName), // Generate slug if not provided
      display_name: fieldName,
      description: field.description || '',
      field_type: field.field_type || field.type || 'text',
      help_text: field.help_text || '',
      field_config: field.field_config || field.config || {},
      storage_constraints: field.storage_constraints || {
        allow_null: true,
        max_storage_length: null,
        enforce_uniqueness: false,
        create_index: false
      },
      business_rules: field.business_rules || {
        stage_requirements: {},
        conditional_requirements: [],
        block_transitions: true,
        show_warnings: true
      },
      enforce_uniqueness: field.enforce_uniqueness || false,
      create_index: field.create_index || false,
      is_searchable: field.is_searchable !== false,
      is_ai_field: field.is_ai_field || false,
      display_order: field.display_order !== undefined ? field.display_order : (field.order !== undefined ? field.order : 0),
      is_visible_in_list: field.is_visible_in_list !== undefined ? field.is_visible_in_list : (field.visible !== undefined ? field.visible : true),
      is_visible_in_detail: field.is_visible_in_detail !== false,
      is_visible_in_public_forms: field.is_visible_in_public_forms || false,
      is_visible_in_shared_list_and_detail_views: field.is_visible_in_shared_list_and_detail_views || false,
      ai_config: field.ai_config || {}
    }
    
    // Only include field_group if it's explicitly set (not undefined)
    if (field.field_group !== undefined) {
      console.log('🔍 Processing field_group:', {
        original: field.field_group,
        type: typeof field.field_group,
        isNull: field.field_group === null,
        isStringNull: field.field_group === 'null',
        isEmpty: field.field_group === ''
      })
      
      if (field.field_group === null || field.field_group === 'null' || field.field_group === '') {
        apiField.field_group = null
        console.log('✅ Set field_group to null')
      } else {
        // Convert string ID to integer
        const groupId = parseInt(field.field_group, 10)
        apiField.field_group = isNaN(groupId) ? null : groupId
        console.log('✅ Converted field_group:', {
          from: field.field_group,
          to: apiField.field_group,
          type: typeof apiField.field_group
        })
      }
    } else {
      console.log('⚠️ field_group is undefined, not including in payload')
    }
    
    // Determine if this should be a CREATE or UPDATE operation
    const shouldCreateField = isNewField
    
    console.log('🔄 Operation decision:', {
      fieldId,
      isNewField,
      shouldCreateField,
      operationType: shouldCreateField ? 'CREATE' : 'UPDATE'
    })
    
    if (shouldCreateField) {
      // New field - create it
      try {
        onSaveStart?.(field)
        pendingSaves.current.add(fieldId)
        
        console.log('🔄 Auto-creating new field:', apiField.name)
        const response = await api.post(`/api/pipelines/${pipelineId}/fields/`, apiField)
        
        pendingSaves.current.delete(fieldId)
        onSaveSuccess?.(response.data)
        console.log('✅ Auto-created field:', response.data.name)
        
      } catch (error: any) {
        pendingSaves.current.delete(fieldId)
        
        // Check if this is a validation error (400) vs a real error (500)
        if (error.response?.status === 400) {
          const errorMessages = error.response?.data || []
          const fieldExistsError = errorMessages.find((msg: string) => 
            msg.includes('already exists') || msg.includes('Field with name')
          )
          
          if (fieldExistsError) {
            console.warn('🔄 New field conflicts with existing field, attempting to fetch existing field:', apiField.name)
            
            // Try to fetch existing field with same name and switch to update mode
            try {
              const existingFieldsResponse = await api.get(`/api/pipelines/${pipelineId}/fields/`)
              
              // Debug the API response structure
              console.log('🔍 API response structure:', {
                data: existingFieldsResponse.data,
                dataType: typeof existingFieldsResponse.data,
                isArray: Array.isArray(existingFieldsResponse.data),
                hasResults: existingFieldsResponse.data?.results,
                keys: Object.keys(existingFieldsResponse.data || {})
              })
              
              // Handle different possible response structures
              let fieldsArray = existingFieldsResponse.data
              if (existingFieldsResponse.data?.results) {
                // Paginated response
                fieldsArray = existingFieldsResponse.data.results
              } else if (!Array.isArray(existingFieldsResponse.data)) {
                // Single object response or other structure
                console.error('❌ Unexpected API response structure')
                throw new Error('API response is not an array')
              }
              
              const existingField = fieldsArray.find((f: any) => 
                f.name === apiField.name || 
                f.display_name === apiField.name ||
                f.label === apiField.name
              )
              
              if (existingField) {
                console.log('✅ Found existing field, switching to update mode:', existingField.id)
                
                // Update the field with the real ID and try again as UPDATE
                const fieldToUpdate = { ...field, id: existingField.id }
                
                const updateResponse = await api.patch(`/api/pipelines/${pipelineId}/fields/${existingField.id}/`, apiField)
                pendingSaves.current.delete(fieldId)
                onSaveSuccess?.(updateResponse.data)
                console.log('✅ Successfully updated existing field:', updateResponse.data.name)
                return
              }
            } catch (fetchError) {
              console.error('❌ Failed to fetch existing field:', fetchError)
            }
          }
          
          console.warn('⚠️ Auto-create validation failed:', error.response?.data)
          // For new fields, show the validation error since we thought it was ready
          if (isNewField) {
            console.log('🔄 New field validation failed, may need more required fields')
            // Still call error callback to show user what's missing
            onSaveError?.(error, field)
            return
          }
        } else {
          console.error('❌ Auto-create field failed:', error)
          console.error('❌ Error response data:', error.response?.data)
          console.error('❌ Error status:', error.response?.status)
        }
        
        onSaveError?.(error, field)
      }
    } else {
      // Existing field - update it
      try {
        onSaveStart?.(field)
        pendingSaves.current.add(fieldId)
        
        console.log('🔄 Auto-updating field:', apiField.name, 'field_group:', apiField.field_group, 'type:', typeof apiField.field_group)
        console.log('📝 Full API payload:', JSON.stringify(apiField, null, 2))
        const response = await api.patch(`/api/pipelines/${pipelineId}/fields/${fieldId}/`, apiField)
        
        pendingSaves.current.delete(fieldId)
        onSaveSuccess?.(response.data)
        console.log('✅ Auto-updated field:', response.data.name)
        
      } catch (error: any) {
        pendingSaves.current.delete(fieldId)
        
        // Check if this is a validation error (400) vs a real error (500)
        if (error.response?.status === 400) {
          console.warn('⚠️ Auto-update validation failed:', error.response?.data)
        } else {
          console.error('❌ Auto-update field failed:', error)
          console.error('❌ Error response data:', error.response?.data)
          console.error('❌ Error status:', error.response?.status)
        }
        
        onSaveError?.(error, field)
      }
    }
  }, [pipelineId, onSaveStart, onSaveSuccess, onSaveError, validateField, allFields])

  const scheduleAutoSave = useCallback((field: any) => {
    const fieldId = field.id || `temp_${Date.now()}`
    const isNewField = !field.id || field.id.startsWith('field_')
    
    // Clear existing timeout for this field
    const existingTimeout = timeoutRefs.current.get(fieldId)
    if (existingTimeout) {
      clearTimeout(existingTimeout)
    }
    
    // Don't schedule if already saving
    if (pendingSaves.current.has(fieldId)) {
      return
    }
    
    // Use longer delay for new fields to give users time to add required info
    const saveDelay = isNewField ? Math.max(delay * 2, 3000) : delay
    
    // Schedule new save
    const timeout = setTimeout(() => {
      autoSaveField(field)
      timeoutRefs.current.delete(fieldId)
    }, saveDelay)
    
    timeoutRefs.current.set(fieldId, timeout)
    console.log(`⏰ Scheduled auto-save for ${isNewField ? 'new' : 'existing'} field "${field.name}" in ${saveDelay}ms`)
    
  }, [autoSaveField, delay])

  const cancelAutoSave = useCallback((fieldId: string) => {
    const timeout = timeoutRefs.current.get(fieldId)
    if (timeout) {
      clearTimeout(timeout)
      timeoutRefs.current.delete(fieldId)
      console.log(`🚫 Cancelled auto-save for field ${fieldId}`)
    }
  }, [])

  const isFieldSaving = useCallback((fieldId: string) => {
    return pendingSaves.current.has(fieldId)
  }, [])

  const flushAutoSave = useCallback((fieldId: string) => {
    const timeout = timeoutRefs.current.get(fieldId)
    if (timeout) {
      clearTimeout(timeout)
      timeoutRefs.current.delete(fieldId)
    }
  }, [])

  const saveFieldNow = useCallback((field: any) => {
    const fieldId = field.id || `temp_${Date.now()}`
    
    // Cancel any pending auto-save
    flushAutoSave(fieldId)
    
    // Save immediately
    autoSaveField(field)
  }, [autoSaveField, flushAutoSave])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      timeoutRefs.current.forEach(timeout => clearTimeout(timeout))
      timeoutRefs.current.clear()
    }
  }, [])

  return {
    scheduleAutoSave,
    cancelAutoSave,
    isFieldSaving,
    flushAutoSave,
    autoSaveField,
    saveFieldNow
  }
}