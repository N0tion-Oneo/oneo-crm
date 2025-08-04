'use client'

import { useState, useEffect, useRef, useMemo } from 'react'
import { pipelinesApi, recordsApi } from '@/lib/api'
import { useDocumentSubscription } from '@/hooks/use-websocket-subscription'
import { type RealtimeMessage, type UserPresence, type FieldLock } from '@/contexts/websocket-context'
import { useAuth } from '@/features/auth/context'
import { evaluateFieldPermissions, evaluateConditionalRules, type FieldWithPermissions, type FieldPermissionResult } from '@/utils/field-permissions'
import { FieldRenderer, FieldDisplay, validateFieldValue, getFieldDefaultValue, normalizeRecordData } from '@/lib/field-system/field-renderer'
import { Field } from '@/lib/field-system/types'
import { FieldResolver } from '@/lib/field-system/field-registry'
import { FieldSaveService } from '@/lib/field-system/field-save-service'
import { parseValidationError, formatErrorForDebug, logValidationError, getCleanErrorMessage } from '@/utils/validation-helpers'
// Import field system to ensure initialization
import '@/lib/field-system'
import { 
  X, 
  Save, 
  Edit, 
  History, 
  MessageSquare, 
  Tag, 
  User, 
  Calendar, 
  AlertCircle,
  CheckCircle,
  Clock,
  RefreshCw,
  Plus,
  Trash2,
  Link,
  FileText,
  Image,
  Upload,
  Eye,
  EyeOff,
  Lock,
  Unlock,
  Type,
  Hash,
  Mail,
  Phone,
  CheckSquare,
  Square,
  Bot,
  Share2
} from 'lucide-react'

interface RecordField extends FieldWithPermissions {
  field_config?: { [key: string]: any }
  config?: { [key: string]: any } // Legacy support
  original_slug?: string // Preserve original backend slug for API calls
}

// Convert RecordField to Field type for field registry
const convertToFieldType = (recordField: RecordField): Field => ({
  id: recordField.id,
  name: recordField.name,
  display_name: recordField.display_name,
  field_type: recordField.field_type,
  field_config: recordField.field_config,
  config: recordField.config, // Legacy support
  is_required: recordField.is_required,
  is_readonly: false, // RecordField doesn't have is_readonly
  help_text: undefined, // RecordField doesn't have help_text
  placeholder: undefined // RecordField doesn't have placeholder
})

interface Record {
  id: string
  data: { [key: string]: any }
  stage?: string
  tags?: string[]
  created_at: string
  updated_at: string
  created_by?: {
    id: string
    first_name: string
    last_name: string
    email: string
  }
}

interface Pipeline {
  id: string
  name: string
  description: string
  fields: RecordField[]
  stages?: string[]
}

interface ValidationError {
  field: string
  message: string
}

interface Activity {
  id: string
  type: 'field_change' | 'stage_change' | 'comment' | 'system'
  field?: string
  old_value?: any
  new_value?: any
  message: string
  user: {
    first_name: string
    last_name: string
    email: string
  }
  created_at: string
}

export interface RecordDetailDrawerProps {
  record: Record | null
  pipeline: Pipeline
  isOpen: boolean
  onClose: () => void
  onSave: (recordId: string, data: { [key: string]: any }) => Promise<void>
  onDelete?: (recordId: string) => Promise<void>
}

export function RecordDetailDrawer({ 
  record, 
  pipeline, 
  isOpen, 
  onClose, 
  onSave, 
  onDelete 
}: RecordDetailDrawerProps) {
  const { user } = useAuth()
  const [formData, setFormData] = useState<{ [key: string]: any }>({})
  const [originalData, setOriginalData] = useState<{ [key: string]: any }>({})
  const [activeTab, setActiveTab] = useState<'details' | 'activity' | 'communications'>('details')
  
  // Field-level editing state for enter/exit pattern
  const [editingField, setEditingField] = useState<string | null>(null)
  const [localFieldValues, setLocalFieldValues] = useState<{[key: string]: any}>({})
  const [fieldErrors, setFieldErrors] = useState<{[key: string]: string}>({})
  
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([])
  const [isAutoSaving, setIsAutoSaving] = useState(false)
  const [lastSaved, setLastSaved] = useState<Date | null>(null)
  const [activities, setActivities] = useState<Activity[]>([])
  
  const autoSaveTimeoutRef = useRef<NodeJS.Timeout>()
  const drawerRef = useRef<HTMLDivElement>(null)
  
  // FieldSaveService instance for this form
  const fieldSaveService = useRef(new FieldSaveService()).current

  // Field filtering with conditional visibility support
  const visibleFields = useMemo(() => {
    const userTypeSlug = user?.userType?.slug
    
    return pipeline.fields
      .filter(field => {
        // Basic visibility check
        if (field.is_visible_in_detail === false) return false
        
        // Evaluate conditional rules if they exist
        if (field.business_rules?.conditional_rules) {
          const conditionalResult = evaluateConditionalRules(
            field.business_rules.conditional_rules,
            formData,
            userTypeSlug
          )
          if (!conditionalResult.visible) return false
        }
        
        return true
      })
      .sort((a, b) => (a.display_order || 0) - (b.display_order || 0))
  }, [pipeline.fields, formData, user])

  // Real-time collaboration
  // Subscribe to document updates for collaborative editing
  const { isConnected } = useDocumentSubscription(
    record?.id || '',
    (message: RealtimeMessage) => {
      if (message.type === 'record_update' && message.payload.record_id === record?.id) {
        // Update form data with real-time changes from other users
        if (message.payload.field_name && message.payload.value !== undefined) {
          setFormData(prev => ({
            ...prev,
            [message.payload.field_name]: message.payload.value
          }))
        }
      }
    },
    !!record?.id // Only enable when we have a record ID
  )

  // Simplified collaborative editing (advanced features disabled for now)
  const activeUsers: UserPresence[] = []
  const fieldLocks: FieldLock[] = []
  const lockField = (recordId: string, fieldName: string) => {}
  const unlockField = (recordId: string, fieldName: string) => {}
  const broadcastRecordUpdate = (recordId: string, fieldName: string, value: any) => {
    // TODO: Implement real-time broadcasting
  }
  const isFieldLocked = (recordId: string, fieldName: string) => false
  const getFieldLock = (recordId: string, fieldName: string): FieldLock | null => null

  // Initialize form data when record changes
  useEffect(() => {
    if (record) {
      // Use centralized field normalization to ensure proper data types
      const normalizedData = normalizeRecordData(pipeline.fields, record.data)
      
      console.log('🔧 Normalizing record data:', { 
        raw: record.data, 
        normalized: normalizedData,
        fields: pipeline.fields.map(f => ({ name: f.name, type: f.field_type }))
      })
      
      setFormData(normalizedData)
      setOriginalData(normalizedData)
      loadActivities(record.id)
    } else {
      // New record - initialize with default values using field registry
      const defaultData: { [key: string]: any } = {}
      pipeline.fields.forEach(field => {
        const fieldType = convertToFieldType(field)
        const defaultValue = getFieldDefaultValue(fieldType)
        if (defaultValue !== undefined && defaultValue !== null) {
          // Use field.name as the key since that's what our frontend uses internally
          defaultData[field.name] = defaultValue
        }
      })
      
      console.log('Initializing new record with default data:', {
        defaultData,
        fieldMap: pipeline.fields.map(f => ({ name: f.name, display_name: f.display_name }))
      })
      setFormData(defaultData)
      setOriginalData({})
      setActivities([])
    }
    
    // Reset field editing state
    setEditingField(null)
    setLocalFieldValues({})
    setFieldErrors({})
    setValidationErrors([])
  }, [record, pipeline.fields])

  // Auto-enable editing for new records
  useEffect(() => {
    if (!record && pipeline.fields.length > 0) {
      // New record: enable editing for the first field to get user started
      const firstEditableField = visibleFields.find(field => {
        const permissions = getFieldPermissions(field)
        return permissions.editable && !permissions.readonly
      })
      
      if (firstEditableField) {
        handleFieldEnter(firstEditableField.name, formData[firstEditableField.name] || '')
      }
    } else if (record) {
      // Existing record: start with no fields in edit mode
      setEditingField(null)
      setLocalFieldValues({})
      setFieldErrors({})
    }
  }, [record, pipeline.fields, visibleFields])

  // Cleanup FieldSaveService when component unmounts
  useEffect(() => {
    return () => {
      fieldSaveService.cleanup()
    }
  }, [fieldSaveService])

  // Handle ESC key to close drawer
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        // Only close drawer if no field is being edited
        if (!editingField) {
          e.preventDefault()
          onClose()
        }
      }
    }

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown)
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen, editingField, onClose])

  // Auto-save functionality removed - only save on blur/manual save

  // Load activities
  const loadActivities = async (recordId: string) => {
    try {
      const response = await recordsApi.getRecordActivity(pipeline.id, recordId)
      // Backend now returns {record_id, activities: [...], activity_count: n} 
      // Extract the activities array for the frontend
      const historyData = response.data
      const activities = historyData.activities || historyData.changes || historyData.results || historyData || []
      setActivities(Array.isArray(activities) ? activities : [])
    } catch (error: any) {
      console.error('Failed to load activities:', error)
      // Fall back to empty array if API call fails
      setActivities([])
    }
  }

  // Transform form data to use backend field slugs
  const transformFormDataForBackend = (data: { [key: string]: any }): { [key: string]: any } => {
    console.log('🔄 Starting field transformation...')
    console.log('Pipeline fields available:', pipeline.fields.map(f => ({ 
      name: f.name, 
      original_slug: f.original_slug,
      display_name: f.display_name 
    })))
    
    const transformedData: { [key: string]: any } = {}
    
    // Map frontend field names to backend field slugs
    Object.keys(data).forEach(fieldName => {
      console.log(`🔍 Processing field: ${fieldName} with value:`, data[fieldName])
      
      const field = pipeline.fields.find(f => f.name === fieldName)
      if (field) {
        // Use original_slug if available, otherwise use the field name
        const backendSlug = field.original_slug || field.name
        transformedData[backendSlug] = data[fieldName]
        
        console.log('✅ Field mapped:', {
          frontendName: fieldName,
          backendSlug: backendSlug,
          value: data[fieldName],
          hasOriginalSlug: !!field.original_slug
        })
      } else {
        console.log('❌ Field not found in pipeline:', fieldName)
      }
    })
    
    console.log('🔄 Transformation complete:', {
      originalData: data,
      transformedData: transformedData,
      originalKeys: Object.keys(data),
      transformedKeys: Object.keys(transformedData)
    })
    
    return transformedData
  }

  // Handle auto-save
  const handleAutoSave = async () => {
    const saveId = `save_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    console.log(`🚀 handleAutoSave called [${saveId}]`)
    
    // Prevent multiple simultaneous saves
    if (isAutoSaving) {
      console.log(`⚠️ Save already in progress, skipping... [${saveId}]`)
      return
    }
    
    try {
      // Clear any pending auto-save timeout to prevent double execution
      if (autoSaveTimeoutRef.current) {
        clearTimeout(autoSaveTimeoutRef.current)
        autoSaveTimeoutRef.current = undefined
      }
      
      setIsAutoSaving(true)
      const errors = validateForm()
      console.log('Form validation results:', {
        errors: errors,
        errorCount: errors.length,
        formData: formData,
        isNewRecord: !record
      })
      
      if (errors.length === 0) {
        if (record) {
          // Existing record: update - transform data to use backend field slugs
          const transformedData = transformFormDataForBackend(formData)
          await pipelinesApi.updateRecord(pipeline.id, record.id, { data: transformedData })
          setOriginalData({ ...formData })
          setLastSaved(new Date())
          
          // Also call parent onSave for UI updates (use original formData for UI)
          await onSave(record.id, formData)
        } else {
          // New record: create - transform data to use backend field slugs
          console.log('🚀 About to transform form data:', formData)
          console.log('🚀 Pipeline fields structure:', pipeline.fields)
          const transformedData = transformFormDataForBackend(formData)
          console.log('🚀 Transformation result:', transformedData)
          
          console.log(`📝 Creating new record [${saveId}]:`, {
            pipelineId: pipeline.id,
            originalFormData: formData,
            transformedPayload: { data: transformedData },
            fieldsCount: Object.keys(formData).length,
            fieldNames: Object.keys(formData),
            pipelineFields: pipeline.fields.map(f => ({ 
              id: f.id, 
              name: f.name, 
              display_name: f.display_name,
              field_type: f.field_type,
              original_slug: f.original_slug
            }))
          })
          
          const response = await pipelinesApi.createRecord(pipeline.id, { data: transformedData })
          console.log('Create record response:', response)
          
          const newRecord = response.data
          setOriginalData({ ...formData })
          setLastSaved(new Date())
          
          // Call parent onSave with new record ID (use original formData for UI)
          await onSave(newRecord.id || 'new', formData)
        }
      } else {
        console.log('Setting validation errors:', errors)
        setValidationErrors(errors)
      }
    } catch (error: any) {
      console.error('Save failed:', error)
      
      // Parse backend validation errors if they exist
      const backendErrors = error?.response?.data?.errors
      if (backendErrors) {
        console.log('🔧 Backend validation errors detected:')
        Object.entries(backendErrors).forEach(([field, messages]: [string, any]) => {
          if (Array.isArray(messages)) {
            messages.forEach(msg => logValidationError(field, msg, 'backend-save'))
          }
        })
      }
      
      console.error('Error details:', {
        message: error?.message,
        response: error?.response?.data,
        responseText: error?.response?.statusText,
        status: error?.response?.status,
        headers: error?.response?.headers,
        config: error?.config,
        formData,
        pipelineId: pipeline.id,
        isNewRecord: !record,
        url: error?.config?.url,
        method: error?.config?.method,
        requestData: error?.config?.data
      })
      
      // Also try to parse and log the response data if it exists
      if (error?.response?.data) {
        console.error('Backend error response:', JSON.stringify(error.response.data, null, 2))
        console.error('Backend error response (object):', error.response.data)
      }
      
      // Also log the full error object structure
      console.error('Full error object:', JSON.stringify(error, null, 2))
    } finally {
      setIsAutoSaving(false)
    }
  }

  // Validate form data
  const validateForm = (): ValidationError[] => {
    const errors: ValidationError[] = []

    visibleFields.forEach(field => {
      const permissions = getFieldPermissions(field)
      const value = formData[field.name]
      
      // Debug logging for each field validation
      console.log('Validating field:', {
        name: field.name,
        display_name: field.display_name,
        permissions: permissions,
        value: value,
        hasValue: !!value
      })
      
      // Use field registry validation with permission awareness
      const fieldType = convertToFieldType(field)
      
      // Override required status based on permissions
      fieldType.is_required = permissions.required
      
      const validationResult = validateFieldValue(fieldType, value)
      
      if (!validationResult.isValid && validationResult.error) {
        // Log validation error with source tracking for debugging
        logValidationError(field.name, validationResult.error, 'form-validation')
        errors.push({
          field: field.name,
          message: getCleanErrorMessage(validationResult.error)  // Clean error for display
        })
      }
    })

    return errors
  }

  // Simple field change handler like DynamicFormRenderer
  const handleFieldChange = (fieldName: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      [fieldName]: value
    }))

    // Clear validation error for this field
    setValidationErrors(prev => 
      prev.filter(error => error.field !== fieldName)
    )
  }

  // Field enter/exit handlers for smooth editing
  const handleFieldEnter = (fieldName: string, currentValue: any) => {
    console.log(`🔵 Field enter: ${fieldName}`, currentValue)
    console.log(`🔍 Current formData for ${fieldName}:`, formData[fieldName])
    setEditingField(fieldName)
    setLocalFieldValues(prev => ({ ...prev, [fieldName]: currentValue || '' }))
    setFieldErrors(prev => ({ ...prev, [fieldName]: '' })) // Clear any errors
    
    // Lock field for collaboration if we have a record
    if (record && isConnected) {
      lockField(record.id, fieldName)
    }
  }

  const handleFieldExit = async (fieldName: string, passedValue?: any) => {
    const newValue = passedValue !== undefined ? passedValue : localFieldValues[fieldName]
    const oldValue = formData[fieldName]
    
    console.log(`🔴 Field exit: ${fieldName}`, { 
      oldValue, 
      newValue, 
      passedValue,
      fromState: localFieldValues[fieldName],
      wasPassedDirectly: passedValue !== undefined
    })
    console.log(`🔍 About to update formData with:`, newValue)
    
    // If value hasn't changed, just exit edit mode
    if (newValue === oldValue) {
      setEditingField(null)
      setLocalFieldValues(prev => {
        const { [fieldName]: _, ...rest } = prev
        return rest
      })
      if (record && isConnected) {
        unlockField(record.id, fieldName)
      }
      return
    }

    // Validate the field before saving
    const field = pipeline.fields.find(f => f.name === fieldName)
    if (field) {
      const fieldValidation = validateSingleField(field, newValue)
      if (fieldValidation.error) {
        setFieldErrors(prev => ({ ...prev, [fieldName]: fieldValidation.error! }))
        return // Don't exit edit mode if validation fails
      }
    }

    // Update formData (this will trigger conditional field visibility and auto-save)
    setFormData(prev => {
      const updated = { ...prev, [fieldName]: newValue }
      console.log(`💾 Updated formData for ${fieldName}:`, updated[fieldName])
      return updated
    })

    // Clear validation error for this field
    setValidationErrors(prev => prev.filter(error => error.field !== fieldName))
    
    // Clean up editing state
    setEditingField(null)
    setLocalFieldValues(prev => {
      const { [fieldName]: _, ...rest } = prev
      return rest
    })
    setFieldErrors(prev => ({ ...prev, [fieldName]: '' }))
    
    // Unlock field for collaboration
    if (record && isConnected) {
      unlockField(record.id, fieldName)
    }
  }

  // Validate a single field (used during field exit)
  const validateSingleField = (field: RecordField, value: any): { error?: string } => {
    // Convert to field system format and use field system validation
    const fieldSystemField = convertToFieldType(field)
    const validationResult = FieldResolver.validate(fieldSystemField, value)
    
    // Override required validation with permissions-aware version
    const permissions = getFieldPermissions(field)
    if (permissions.required && FieldResolver.isEmpty(fieldSystemField, value)) {
      return { error: `${field.display_name || field.name} is required` }
    }
    
    // Return field system validation result
    if (!validationResult.isValid && validationResult.error) {
      return { error: validationResult.error }
    }

    return {}
  }

  // Simple field permissions evaluation without complex state tracking
  const getFieldPermissions = (field: RecordField): FieldPermissionResult => {
    if (!user) {
      return {
        visible: false,
        editable: false,
        required: false,
        readonly: true,
        conditionallyHidden: false,
        reasonHidden: 'No user logged in'
      }
    }

    return evaluateFieldPermissions(field, user, formData, 'detail')
  }

  // Auto-save functionality
  useEffect(() => {
    if (!record || Object.keys(formData).length === 0) return

    // Check if data has changed
    const hasChanges = Object.keys(formData).some(key => 
      formData[key] !== originalData[key]
    )

    if (hasChanges) {
      // Clear existing timeout
      if (autoSaveTimeoutRef.current) {
        clearTimeout(autoSaveTimeoutRef.current)
      }

      // Set new timeout for auto-save
      autoSaveTimeoutRef.current = setTimeout(() => {
        handleAutoSave()
      }, 2000) // Auto-save after 2 seconds of inactivity
    }

    return () => {
      if (autoSaveTimeoutRef.current) {
        clearTimeout(autoSaveTimeoutRef.current)
      }
    }
  }, [formData, originalData, record])

  // Handle Enter key for field exit
  const handleFieldKeyDown = (e: React.KeyboardEvent, fieldName: string) => {
    if (e.key === 'Enter' && !e.shiftKey) { // Allow Shift+Enter for new lines in textarea
      e.preventDefault()
      handleFieldExit(fieldName)
    }
    if (e.key === 'Escape') {
      // Cancel editing without saving
      setEditingField(null)
      setLocalFieldValues(prev => {
        const { [fieldName]: _, ...rest } = prev
        return rest
      })
      setFieldErrors(prev => ({ ...prev, [fieldName]: '' }))
      if (record && isConnected) {
        unlockField(record.id, fieldName)
      }
    }
  }

  // Tags are now handled by the field system instead of hardcoded logic

  // Render field input with enter/exit pattern using field registry
  const renderFieldInput = (field: RecordField) => {
    const isEditing = editingField === field.name
    const value = isEditing ? localFieldValues[field.name] : formData[field.name]
    const fieldError = fieldErrors[field.name]
    const fieldLock = record ? getFieldLock(record.id, field.name) : null
    const isLocked = record ? isFieldLocked(record.id, field.name) : false

    // Display mode (not editing)
    if (!isEditing) {
      const canEdit = !isLocked
      const fieldType = convertToFieldType(field)
      
      return (
        <div>
          <div 
            className={`min-h-[42px] px-3 py-2 rounded-md flex items-center justify-between group transition-colors ${
              isLocked 
                ? 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800' 
                : 'bg-gray-50 dark:bg-gray-800 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700'
            }`}
            onClick={() => canEdit && handleFieldEnter(field.name, value)}
          >
            {value ? (
              <FieldDisplay 
                field={fieldType}
                value={value}
                context="detail"
                className="text-gray-900 dark:text-white"
              />
            ) : (
              <span className="text-gray-500 italic">Click to edit</span>
            )}
            
            <div className="flex items-center space-x-2">
              {isLocked && fieldLock && 'user_name' in fieldLock && (
                <div className="flex items-center space-x-1 text-red-600 dark:text-red-400">
                  <Lock className="w-3 h-3" />
                  <span className="text-xs">{fieldLock.user_name}</span>
                </div>
              )}
              {canEdit && (
                <Edit className="w-4 h-4 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" />
              )}
            </div>
          </div>
          
          {/* Lock message */}
          {isLocked && fieldLock && (
            <p className="mt-1 text-xs text-red-600 dark:text-red-400">
              Currently being edited by {fieldLock.user_name}
            </p>
          )}
        </div>
      )
    }

    // Edit mode - use field registry with enter/exit pattern integration
    const fieldType = convertToFieldType(field)
    
    // Special handling for fields that should exit immediately after change
    const shouldExitImmediately = ['select', 'boolean', 'radio', 'relation'].includes(field.field_type)
    
    const handleFieldRegistryChange = (newValue: any) => {
      console.log(`🟢 Field change: ${field.name}`, { newValue, fieldType: field.field_type })
      
      // For NEW records, don't use field-level saving - just update local formData
      // The record will be created when the user clicks "Create Record"
      if (!record || !record.id) {
        console.log(`📝 New record - updating local formData only for ${field.name}`)
        setFormData(prev => ({ ...prev, [field.name]: newValue }))
        return
      }
      
      // For EXISTING records, use FieldSaveService for field-level saving
      const shouldUpdateFormDataImmediately = ['select', 'boolean', 'radio', 'relation'].includes(field.field_type)
      
      fieldSaveService.onFieldChange({
        field: fieldType,
        newValue,
        apiEndpoint: `/api/pipelines/${pipeline.id}/records/${record.id}/`,
        onSuccess: (result) => {
          // Only update formData immediately for fields that save immediately
          // This prevents re-renders during typing for text fields
          if (shouldUpdateFormDataImmediately) {
            setFormData(prev => ({ ...prev, [field.name]: newValue }))
          }
          // Always clear field errors on successful save
          setFieldErrors(prev => ({ ...prev, [field.name]: '' }))
        },
        onError: (error) => {
          // Show field error
          setFieldErrors(prev => ({ 
            ...prev, 
            [field.name]: error.response?.data?.message || error.message || 'Save failed'
          }))
        }
      })
    }

    const handleFieldRegistryBlur = () => {
      console.log(`🔵 Field blur: ${field.name}`)
      
      // For NEW records, don't try to save - just keep the value in formData
      if (!record || !record.id) {
        console.log(`📝 New record - no save on blur for ${field.name}`)
        return
      }
      
      // For EXISTING records, save via FieldSaveService and update formData when successful
      fieldSaveService.onFieldExit(field.name).then((result) => {
        if (result && result.savedValue !== undefined) {
          console.log(`✅ Field ${field.name} saved on exit with value:`, result.savedValue)
          // CRITICAL: Update formData with the actual saved value so UI shows the change
          setFormData(prev => ({ ...prev, [field.name]: result.savedValue }))
        }
      }).catch((error) => {
        // Error already handled by FieldSaveService toast
        console.log(`❌ Failed to save ${field.name} on exit:`, error)
      })
    }

    const handleFieldRegistryKeyDown = (e: React.KeyboardEvent) => {
      handleFieldKeyDown(e, field.name)
    }

    return (
      <div>
        <FieldRenderer
          field={fieldType}
          value={value}
          onChange={handleFieldRegistryChange}
          onBlur={handleFieldRegistryBlur}
          onKeyDown={handleFieldRegistryKeyDown}
          disabled={false}
          error={fieldError}
          autoFocus={true}
          context="drawer"
        />
      </div>
    )
  }

  // Removed formatDisplayValue - now using centralized FieldDisplay component

  // Format activity timestamp
  const formatActivityTime = (timestamp: string) => {
    if (!timestamp) return 'Unknown time'
    
    const date = new Date(timestamp)
    // Check if date is valid
    if (isNaN(date.getTime())) return 'Invalid date'
    
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-end z-50">
      <div 
        ref={drawerRef}
        className="bg-white dark:bg-gray-800 h-full w-full max-w-2xl shadow-xl flex flex-col animate-slide-in-right"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-3">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              {record ? 'Edit Record' : 'New Record'}
            </h2>
            {isAutoSaving && (
              <div className="flex items-center space-x-2 text-sm text-gray-500">
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Saving...</span>
              </div>
            )}
            {lastSaved && (
              <div className="flex items-center space-x-1 text-sm text-green-600">
                <CheckCircle className="w-4 h-4" />
                <span>Saved {formatActivityTime(lastSaved.toISOString())}</span>
              </div>
            )}
            
            {/* Real-time status and users */}
            <div className="flex items-center space-x-2">
              {/* Connection status */}
              <div className={`w-2 h-2 rounded-full ${
                isConnected ? 'bg-green-500' : 'bg-red-500'
              }`} title={isConnected ? 'Connected' : 'Disconnected'} />
              
              {/* Active users */}
              {activeUsers.length > 0 && (
                <div className="flex items-center space-x-1">
                  <div className="flex -space-x-1">
                    {activeUsers.slice(0, 3).map((user, index) => (
                      <div
                        key={user.user_id}
                        className="w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center text-xs text-white font-medium border-2 border-white dark:border-gray-800"
                        title={user.user_name}
                        style={{ zIndex: 10 - index }}
                      >
                        {user.user_name.split(' ').map(n => n[0]).join('').substring(0, 2)}
                      </div>
                    ))}
                    {activeUsers.length > 3 && (
                      <div className="w-6 h-6 bg-gray-500 rounded-full flex items-center justify-center text-xs text-white font-medium border-2 border-white dark:border-gray-800">
                        +{activeUsers.length - 3}
                      </div>
                    )}
                  </div>
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {activeUsers.length} online
                  </span>
                </div>
              )}
            </div>
          </div>
          
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-200 dark:border-gray-700">
          <button
            onClick={() => setActiveTab('details')}
            className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'details'
                ? 'border-primary text-primary'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            Details
          </button>
          <button
            onClick={() => setActiveTab('activity')}
            className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'activity'
                ? 'border-primary text-primary'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            Activity ({activities.length})
          </button>
          <button
            onClick={() => setActiveTab('communications')}
            className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'communications'
                ? 'border-primary text-primary'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            Communications
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {activeTab === 'details' && (
            <div className="p-6 space-y-6">
              {/* Fields (including tags fields handled by field system) */}
              <div className="space-y-4">
                {visibleFields.map((field) => {
                  const permissions = getFieldPermissions(field)
                  return (
                    <div key={field.name}>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        {field.display_name || field.name}
                        {permissions.required && <span className="text-red-500 ml-1">*</span>}
                        {permissions.readonly && <span className="text-gray-500 ml-1">(read-only)</span>}
                      </label>
                      {renderFieldInput(field)}
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {activeTab === 'activity' && (
            <div className="p-6">
              <div className="space-y-4">
                {activities.map((activity, index) => (
                  <div key={activity.id || `activity-${index}-${Date.now()}`} className="flex space-x-3">
                    <div className="flex-shrink-0">
                      <div className="w-8 h-8 bg-gray-200 dark:bg-gray-600 rounded-full flex items-center justify-center">
                        {activity.type === 'system' && activity.message.includes('created') && <Plus className="w-4 h-4 text-green-600 dark:text-green-400" />}
                        {activity.type === 'field_change' && <Edit className="w-4 h-4 text-blue-600 dark:text-blue-400" />}
                        {activity.type === 'stage_change' && <Trash2 className="w-4 h-4 text-red-600 dark:text-red-400" />}
                        {activity.type === 'comment' && <Clock className="w-4 h-4 text-gray-600 dark:text-gray-400" />}
                      </div>
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="text-sm text-gray-900 dark:text-white">
                        <span className="font-medium">
                          {activity.user ? `${activity.user.first_name} ${activity.user.last_name}` : 'System'}
                        </span>
                        <div className="mt-1">
                          {activity.message.split('\n').map((line, index) => (
                            <div key={index} className={index > 0 ? 'mt-1' : ''}>
                              {line}
                            </div>
                          ))}
                        </div>
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                        {formatActivityTime(activity.created_at)}
                      </div>
                    </div>
                  </div>
                ))}
                
                {activities.length === 0 && (
                  <div className="text-center py-8">
                    <History className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    <p className="text-gray-500 dark:text-gray-400">No activity yet</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'communications' && (
            <div className="p-6">
              <div className="text-center py-8">
                <MessageSquare className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-500 dark:text-gray-400">No communications yet</p>
                <p className="text-sm text-gray-400 mt-2">
                  Communication threads will appear here when integrated with UniPile
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            {record && record.created_by && (
              <div className="text-sm text-gray-500 dark:text-gray-400">
                Created by {record.created_by.first_name} {record.created_by.last_name} on{' '}
                {new Date(record.created_at).toLocaleDateString()}
              </div>
            )}
          </div>
          
          <div className="flex items-center space-x-3">
            {record && (
              <button
                onClick={() => {
                  // TODO: Implement record sharing in Phase 6
                  const shareUrl = `${window.location.origin}/forms/shared/${pipeline.id}/${record.id}?token=sharing_token_here`
                  navigator.clipboard.writeText(shareUrl)
                  alert('Share link copied to clipboard! (Full sharing system coming in Phase 6)')
                }}
                className="px-4 py-2 text-blue-600 hover:text-blue-700 border border-blue-300 hover:border-blue-400 rounded-md hover:bg-blue-50 dark:hover:bg-blue-900/20"
                title="Share record (Phase 6 feature preview)"
              >
                <Share2 className="w-4 h-4 mr-2 inline" />
                Share
              </button>
            )}
            
            {record && onDelete && (
              <button
                onClick={() => onDelete(record.id)}
                className="px-4 py-2 text-red-600 hover:text-red-700 border border-red-300 hover:border-red-400 rounded-md hover:bg-red-50 dark:hover:bg-red-900/20"
                title="Move record to trash (can be restored)"
              >
                <Trash2 className="w-4 h-4 mr-2 inline" />
                Move to Trash
              </button>
            )}
            
            <button
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              Cancel
            </button>
            
            <button
              onClick={() => handleAutoSave()}
              disabled={validationErrors.length > 0}
              className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Save className="w-4 h-4 mr-2 inline" />
              {record ? 'Save Changes' : 'Create Record'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}