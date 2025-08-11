'use client'

import { useState, useEffect, useRef, useMemo } from 'react'
import { pipelinesApi, recordsApi } from '@/lib/api'
import { useDocumentSubscription } from '@/hooks/use-websocket-subscription'
import { type RealtimeMessage, type UserPresence, type FieldLock } from '@/contexts/websocket-context'
import { useAuth } from '@/features/auth/context'
import { evaluateFieldPermissions, evaluateConditionalRules, type FieldWithPermissions, type FieldPermissionResult } from '@/utils/field-permissions'
import { FieldRenderer, FieldDisplay, validateFieldValue, getFieldDefaultValue, normalizeRecordData, normalizeFieldValue } from '@/lib/field-system/field-renderer'
import { Field } from '@/lib/field-system/types'
import { FieldResolver } from '@/lib/field-system/field-registry'
import { FieldSaveService, getSaveStrategy } from '@/lib/field-system/field-save-service'
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
  Share2,
  AlignLeft,
  Calculator,
  Globe,
  ChevronDown,
  List,
  ToggleLeft,
  GitBranch,
  MapPin,
  MousePointer,
  Database,
  HelpCircle
} from 'lucide-react'

// Import tooltip components
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui'

interface RecordField extends FieldWithPermissions {
  field_config?: { [key: string]: any }
  config?: { [key: string]: any } // Legacy support
  ai_config?: { [key: string]: any } // AI field configuration
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
  original_slug: recordField.original_slug, // ⭐ CRITICAL: Include backend slug for FieldSaveService
  is_readonly: false, // RecordField doesn't have is_readonly
  help_text: undefined, // RecordField doesn't have help_text
  placeholder: undefined, // RecordField doesn't have placeholder
  // Pass through AI config for AI fields
  ...(recordField.ai_config && { ai_config: recordField.ai_config })
} as Field)


// Provide fallback default values for field types that return null/undefined
const getFallbackDefaultValue = (fieldType: string): any => {
  switch (fieldType) {
    case 'text':
    case 'textarea':
    case 'email':
    case 'phone':
    case 'url':
    case 'address':
      return '' // Empty string for text-based fields - ensures editability
    
    case 'number':
    case 'integer':
    case 'decimal':
    case 'float':
    case 'currency':
    case 'percentage':
    case 'date':
    case 'datetime':
    case 'time':
    case 'select':
    case 'relation':
    case 'user':
    case 'file':
    case 'image':
    case 'ai_generated':
    case 'button':
      return null // Null for fields that should remain unset initially
    
    case 'boolean':
      return false // Boolean fields default to false
    
    case 'multiselect':
    case 'tags':
      return [] // Empty array for multi-value fields
    
    default:
      return null // Safe fallback
  }
}

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

// Field icons mapping (from pipeline-field-builder)
const FIELD_ICONS: Record<string, any> = {
  text: AlignLeft,
  textarea: FileText,
  number: Hash,
  decimal: Calculator,
  currency: Calculator,
  percentage: Calculator,
  auto_increment: Hash,
  email: Mail,
  phone: Phone,
  date: Calendar,
  boolean: ToggleLeft,
  select: ChevronDown,
  multiselect: List,
  url: Globe,
  file: FileText,
  relation: GitBranch,
  ai_generated: Bot,
  ai_field: Bot,
  ai: Bot,
  tags: Tag,
  address: MapPin,
  button: MousePointer,
  user: User,
}

// Utility function to get field icon component
const getFieldIcon = (fieldType: string) => {
  const IconComponent = FIELD_ICONS[fieldType] || Type
  return IconComponent
}

// Utility function to format field name for display
const formatFieldName = (field: RecordField): string => {
  // Priority order: display_name -> formatted name/slug -> fallback
  if (field.display_name?.trim()) {
    return field.display_name.trim()
  }
  
  if (field.name?.trim()) {
    // Convert slug to readable format: company_name -> Company Name
    return field.name
      .replace(/_/g, ' ')
      .replace(/\b\w/g, l => l.toUpperCase())
      .trim()
  }
  
  return 'Unnamed Field'
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
  
  const [fieldErrors, setFieldErrors] = useState<{[key: string]: string}>({})
  
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([])
  const [isAutoSaving, setIsAutoSaving] = useState(false)
  const [lastSaved, setLastSaved] = useState<Date | null>(null)
  const [activities, setActivities] = useState<Activity[]>([])
  
  const drawerRef = useRef<HTMLDivElement>(null)
  
  // FieldSaveService instance for this form
  const fieldSaveService = useRef(new FieldSaveService()).current
  const isSavingRef = useRef(false)  // Track when we're saving to prevent formData reset


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
  }, [pipeline.fields, formData, user?.userType?.slug])

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
      } else if (message.type === 'activity_update') {
        // Handle real-time activity updates
        const activityData = message.data || message.payload
        if (activityData && String(activityData.record_id) === String(record?.id)) {
          // Add new activity to the beginning of the activities list
          setActivities(prev => [activityData, ...prev])
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

  // Initialize form data when record ID changes (not on every record update)
  useEffect(() => {

    if (record) {
      // Record ID changed - initialize with existing record data
      
      // Map backend field slugs to frontend field names and normalize data types
      const formData: { [key: string]: any } = {}
      
      pipeline.fields.forEach(field => {
        const fieldType = convertToFieldType(field)
        const backendSlug = field.original_slug || field.name
        
        // Try multiple ways to get the value from backend data
        let backendValue = record.data?.[backendSlug]
        
        // Fallback attempts if primary slug doesn't work
        if (backendValue === undefined) {
          // Try with the field name directly
          backendValue = record.data?.[field.name]
        }
        
        if (backendValue === undefined && field.original_slug) {
          // Try with display_name or slug transformations
          backendValue = record.data?.[field.display_name?.toLowerCase().replace(/\s+/g, '_')]
        }
        
        // Always try to map the value, even if it's empty string, 0, false, etc.
        if (backendValue !== undefined) {
          // Use field system normalization for proper data types
          const normalizedValue = normalizeFieldValue(fieldType, backendValue)
          formData[field.name] = normalizedValue
        } else {
          // Only use defaults if the field is truly missing from backend data
          const defaultValue = getFieldDefaultValue(fieldType)
          const fallbackDefault = defaultValue !== undefined && defaultValue !== null 
            ? defaultValue 
            : getFallbackDefaultValue(field.field_type)
          formData[field.name] = fallbackDefault
        }
      })
      
      
      setFormData(formData)
      setOriginalData(formData)
      loadActivities(record.id)
    } else {
      // New record - initialize ALL fields with appropriate defaults
      const defaultData: { [key: string]: any } = {}
      
      pipeline.fields.forEach(field => {
        const fieldType = convertToFieldType(field)
        const defaultValue = getFieldDefaultValue(fieldType)
        
        // Initialize ALL fields, including those with null/undefined defaults
        // This ensures every field exists in formData to prevent input loss
        if (defaultValue !== undefined && defaultValue !== null) {
          defaultData[field.name] = defaultValue
        } else {
          // Provide appropriate fallback defaults for null/undefined values
          const fallbackDefault = getFallbackDefaultValue(field.field_type)
          defaultData[field.name] = fallbackDefault
        }
      })
      

      setFormData(defaultData)
      setOriginalData({})
      setActivities([])
    }
    
    // Reset field errors and validation errors
    setFieldErrors({})
    setValidationErrors([])
  }, [record?.id, pipeline.fields.length])  // Dependencies: only reset when record ID or field count changes


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
        e.preventDefault()
        onClose()
      }
    }

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown)
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen, onClose])

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
    const transformedData: { [key: string]: any } = {}
    
    // Map frontend field names to backend field slugs
    Object.keys(data).forEach(fieldName => {
      const field = pipeline.fields.find(f => f.name === fieldName)
      if (field) {
        // Use original_slug if available, otherwise use the field name
        const backendSlug = field.original_slug || field.name
        transformedData[backendSlug] = data[fieldName]
      }
    })
    
    return transformedData
  }



  // Validate form data
  const validateForm = (): ValidationError[] => {
    const errors: ValidationError[] = []

    visibleFields.forEach(field => {
      const permissions = getFieldPermissions(field)
      const value = formData[field.name]
      
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

  // Handle new record creation only
  const handleCreateRecord = async () => {
    if (record) {
      // Existing records are auto-saved by FieldSaveService, just close
      // DO NOT call onSave for existing records to prevent bulk overwrites
      onClose()
      return
    }

    try {
      setIsAutoSaving(true)
      const errors = validateForm()
      
      if (errors.length === 0) {
        // Transform data to use backend field slugs
        const transformedData = transformFormDataForBackend(formData)
        const response = await pipelinesApi.createRecord(pipeline.id, { data: transformedData })
        const newRecord = response.data
        setOriginalData({ ...formData })
        setLastSaved(new Date())
        
        // Call parent onSave with new record ID
        await onSave(newRecord.id || 'new', formData)
        onClose()
      } else {
        setValidationErrors(errors)
      }
    } catch (error: any) {
      console.error('Create record failed:', error)
    } finally {
      setIsAutoSaving(false)
    }
  }




  

  // Render field input - unified single path for all field types
  const renderFieldInput = (field: RecordField) => {
    const value = formData[field.name]
    const fieldError = fieldErrors[field.name]
    const fieldType = convertToFieldType(field)
    
    console.log('renderFieldInput:', { fieldName: field.name, fieldType: field.field_type, value, formData: formData[field.name] }) // DEBUG
    
    
    const handleFieldChange = (newValue: any) => {
      console.log('RecordDrawer handleFieldChange:', { fieldName: field.name, newValue, recordId: record?.id }) // DEBUG
      
      // For NEW records, just update formData - record will be created when user clicks "Create Record"
      if (!record || !record.id) {
        console.log('NEW record - updating formData:', { fieldName: field.name, newValue }) // DEBUG
        setFormData(prev => {
          const updated = { ...prev, [field.name]: newValue }
          console.log('formData updated:', updated) // DEBUG
          return updated
        })
        
        // Clear validation error for this field
        setValidationErrors(prev => prev.filter(error => error.field !== field.name))
        setFieldErrors(prev => ({ ...prev, [field.name]: '' }))
        return
      }
      
      // For EXISTING records, use FieldSaveService based on save strategy
      console.log('EXISTING record - using FieldSaveService:', { fieldName: field.name, newValue, isSaving: isSavingRef.current }) // DEBUG
      isSavingRef.current = true
      fieldSaveService.onFieldChange({
        field: fieldType,
        newValue,
        apiEndpoint: `/api/pipelines/${pipeline.id}/records/${record.id}/`,
        onSuccess: (result) => {
          console.log('FieldSaveService SUCCESS - updating formData:', { fieldName: field.name, newValue, result }) // DEBUG
          setFormData(prev => {
            const updated = { ...prev, [field.name]: newValue }
            console.log('EXISTING record formData updated:', updated) // DEBUG
            return updated
          })
          setFieldErrors(prev => ({ ...prev, [field.name]: '' }))
          setValidationErrors(prev => prev.filter(error => error.field !== field.name))
          isSavingRef.current = false
        },
        onError: (error) => {
          console.log('FieldSaveService ERROR:', { fieldName: field.name, error }) // DEBUG
          setFieldErrors(prev => ({ 
            ...prev, 
            [field.name]: error.response?.data?.message || error.message || 'Save failed'
          }))
          isSavingRef.current = false
        }
      })
    }

    const handleFieldBlur = () => {
      // For NEW records, no blur handling needed
      if (!record || !record.id) {
        return
      }
      
      // For EXISTING records, handle field exit via FieldSaveService
      isSavingRef.current = true
      fieldSaveService.onFieldExit(field.name).then((result) => {
        if (result && result.savedValue !== undefined) {
          const normalizedValue = normalizeFieldValue(fieldType, result.savedValue)
          setFormData(prev => ({ ...prev, [field.name]: normalizedValue }))
        }
      }).catch((error) => {
        // Error already handled by FieldSaveService toast
      }).finally(() => {
        isSavingRef.current = false
      })
    }

    return (
      <div>
        <FieldRenderer
          field={fieldType}
          value={value}
          onChange={handleFieldChange}
          onBlur={handleFieldBlur}
          disabled={false}
          error={fieldError}
          autoFocus={false}
          context="drawer"
          pipeline_id={pipeline?.id}
          record_id={record?.id}
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
                  const IconComponent = getFieldIcon(field.field_type)
                  const fieldName = formatFieldName(field)
                  const hasHelpText = field.help_text?.trim()
                  
                  return (
                    <TooltipProvider key={field.name}>
                      <div>
                        <div className="flex items-center mb-2">
                          {/* Field Icon */}
                          <IconComponent className="w-4 h-4 mr-2 text-gray-500 dark:text-gray-400 flex-shrink-0" />
                          
                          {/* Field Label */}
                          <label className="block text-sm font-bold text-gray-900 dark:text-white flex-grow">
                            {fieldName}
                            {permissions.required && <span className="text-red-500 ml-1">*</span>}
                            {permissions.readonly && <span className="text-gray-500 ml-1 font-normal">(read-only)</span>}
                          </label>
                          
                          {/* Help Text Tooltip */}
                          {hasHelpText && (
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <HelpCircle className="w-4 h-4 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help ml-1 flex-shrink-0" />
                              </TooltipTrigger>
                              <TooltipContent>
                                <p className="max-w-xs">{field.help_text}</p>
                              </TooltipContent>
                            </Tooltip>
                          )}
                        </div>
                        
                        {/* Field Input */}
                        {renderFieldInput(field)}
                      </div>
                    </TooltipProvider>
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
              onClick={handleCreateRecord}
              disabled={validationErrors.length > 0}
              className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Save className="w-4 h-4 mr-2 inline" />
              {record ? 'Close' : 'Create Record'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}