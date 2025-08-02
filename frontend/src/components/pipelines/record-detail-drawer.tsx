'use client'

import { useState, useEffect, useRef } from 'react'
import { pipelinesApi, recordsApi } from '@/lib/api'
import { useDocumentSubscription } from '@/hooks/use-websocket-subscription'
import { type RealtimeMessage, type UserPresence, type FieldLock } from '@/contexts/websocket-context'
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

interface RecordField {
  id: string
  name: string
  display_name?: string
  field_type: string
  is_required?: boolean
  is_visible_in_list?: boolean
  is_visible_in_detail?: boolean
  display_order: number
  field_config?: { [key: string]: any }
  config?: { [key: string]: any } // Legacy support
  original_slug?: string // Preserve original backend slug for API calls
  business_rules?: {
    stage_requirements?: { [key: string]: { 
      required: boolean
      block_transitions?: boolean
      show_warnings?: boolean
      warning_message?: string
    }}
    user_visibility?: { [key: string]: { visible: boolean; editable: boolean }}
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

export function RecordDetailDrawer({ 
  record, 
  pipeline, 
  isOpen, 
  onClose, 
  onSave, 
  onDelete 
}: RecordDetailDrawerProps) {
  const [formData, setFormData] = useState<{ [key: string]: any }>({})
  const [originalData, setOriginalData] = useState<{ [key: string]: any }>({})
  const [activeTab, setActiveTab] = useState<'details' | 'activity' | 'communications'>('details')
  const [editingFields, setEditingFields] = useState<Set<string>>(new Set())
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([])
  const [isAutoSaving, setIsAutoSaving] = useState(false)
  const [lastSaved, setLastSaved] = useState<Date | null>(null)
  const [activities, setActivities] = useState<Activity[]>([])
  const [tags, setTags] = useState<string[]>([])
  const [newTag, setNewTag] = useState('')
  const [showTagInput, setShowTagInput] = useState(false)
  
  const autoSaveTimeoutRef = useRef<NodeJS.Timeout>()
  const drawerRef = useRef<HTMLDivElement>(null)

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
      setFormData({ ...record.data })
      setOriginalData({ ...record.data })
      setTags(record.tags || [])
      loadActivities(record.id)
    } else {
      // New record - initialize with default values
      const defaultData: { [key: string]: any } = {}
      pipeline.fields.forEach(field => {
        // Check both field_config and config for default values (legacy support)
        const defaultValue = field.field_config?.default_value || field.config?.default_value
        if (defaultValue !== undefined) {
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
      setTags([])
      setActivities([])
    }
    setEditingFields(new Set())
    setValidationErrors([])
  }, [record, pipeline.fields])

  // Auto-enable editing for new records
  useEffect(() => {
    if (!record && pipeline.fields.length > 0) {
      // New record: enable editing for all visible fields
      const editableFields = pipeline.fields
        .filter(field => field.is_visible_in_detail !== false)
        .map(field => field.name)
      setEditingFields(new Set(editableFields))
    } else if (record) {
      // Existing record: start with no fields in edit mode
      setEditingFields(new Set())
    }
  }, [record, pipeline.fields])

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

    pipeline.fields.forEach(field => {
      const value = formData[field.name]
      const currentStage = formData['pipeline_stages'] || 'Lead' // Default stage
      const stageRequirements = field.business_rules?.stage_requirements?.[currentStage]
      const isRequiredForStage = stageRequirements?.required || false
      
      // Debug logging for each field validation
      console.log('Validating field:', {
        name: field.name,
        display_name: field.display_name,
        is_required: field.is_required,
        currentStage: currentStage,
        isRequiredForStage: isRequiredForStage,
        stageRequirements: stageRequirements,
        value: value,
        hasValue: !!value
      })
      
      // Stage-specific required field validation (only use business rules, ignore generic is_required)
      const fieldIsRequired = isRequiredForStage
      if (fieldIsRequired && (!value || value === '')) {
        console.log('Required field missing for stage:', field.name, 'stage:', currentStage)
        errors.push({
          field: field.name,
          message: `${field.display_name || field.name} is required for ${currentStage} stage`
        })
      }

      // Type-specific validation
      if (value && value !== '') {
        switch (field.field_type) {
          case 'email':
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
            if (!emailRegex.test(value)) {
              errors.push({
                field: field.name,
                message: 'Please enter a valid email address'
              })
            }
            break
          case 'url':
            try {
              new URL(value)
            } catch {
              errors.push({
                field: field.name,
                message: 'Please enter a valid URL'
              })
            }
            break
          case 'number':
          case 'decimal':
            if (isNaN(Number(value))) {
              errors.push({
                field: field.name,
                message: 'Please enter a valid number'
              })
            }
            break
        }
      }
    })

    return errors
  }

  // Handle field change
  const handleFieldChange = (fieldName: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      [fieldName]: value
    }))

    // Clear validation error for this field
    setValidationErrors(prev => 
      prev.filter(error => error.field !== fieldName)
    )

    // Broadcast real-time update to other users
    if (record && isConnected) {
      broadcastRecordUpdate(record.id, fieldName, value)
    }
  }

  // Handle field edit mode
  const toggleFieldEdit = (fieldName: string) => {
    // For new records (when record is null), allow editing without restrictions
    if (record) {
      // Existing record: check if field is locked by another user
      if (isFieldLocked(record.id, fieldName)) {
        return // Cannot edit locked field
      }
    }

    const newEditing = new Set(editingFields)
    if (newEditing.has(fieldName)) {
      // Exiting edit mode
      newEditing.delete(fieldName)
      // Only handle real-time locking for existing records
      if (record && isConnected) {
        unlockField(record.id, fieldName)
      }
    } else {
      // Entering edit mode
      newEditing.add(fieldName)
      // Only handle real-time locking for existing records
      if (record && isConnected) {
        lockField(record.id, fieldName)
      }
    }
    setEditingFields(newEditing)
  }

  // Add tag
  const handleAddTag = () => {
    if (newTag.trim() && !tags.includes(newTag.trim())) {
      setTags([...tags, newTag.trim()])
      setNewTag('')
      setShowTagInput(false)
    }
  }

  // Remove tag
  const handleRemoveTag = (tagToRemove: string) => {
    setTags(tags.filter(tag => tag !== tagToRemove))
  }

  // Render field input
  const renderFieldInput = (field: RecordField) => {
    const value = formData[field.name] || ''
    const isNewRecord = !record
    const isEditing = isNewRecord || editingFields.has(field.name)
    const hasError = validationErrors.some(error => error.field === field.name)
    const error = validationErrors.find(error => error.field === field.name)
    const fieldLock = record ? getFieldLock(record.id, field.name) : null
    const isLocked = record ? isFieldLocked(record.id, field.name) : false

    const inputClass = `w-full px-3 py-2 border rounded-md transition-colors ${
      hasError 
        ? 'border-red-300 focus:border-red-500 focus:ring-red-500' 
        : 'border-gray-300 dark:border-gray-600 focus:border-primary focus:ring-primary'
    } bg-white dark:bg-gray-700 text-gray-900 dark:text-white`

    if (!isEditing) {
      return (
        <div>
          <div 
            className={`min-h-[42px] px-3 py-2 rounded-md flex items-center justify-between group transition-colors ${
              isLocked 
                ? 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800' 
                : 'bg-gray-50 dark:bg-gray-800 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700'
            }`}
            onClick={() => !isLocked && toggleFieldEdit(field.name)}
          >
            <span className={value ? 'text-gray-900 dark:text-white' : 'text-gray-500 italic'}>
              {formatDisplayValue(field, value) || 'Click to edit'}
            </span>
            
            <div className="flex items-center space-x-2">
              {isLocked && fieldLock && 'user_name' in fieldLock && (
                <div className="flex items-center space-x-1 text-red-600 dark:text-red-400">
                  <Lock className="w-3 h-3" />
                  <span className="text-xs">{fieldLock.user_name}</span>
                </div>
              )}
              {!isLocked && (
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

    switch (field.field_type) {
      case 'textarea':
        return (
          <div>
            <textarea
              value={value}
              onChange={(e) => handleFieldChange(field.name, e.target.value)}
              onBlur={() => toggleFieldEdit(field.name)}
              className={`${inputClass} min-h-[100px] resize-vertical`}
              placeholder={`Enter ${(field.display_name || field.name).toLowerCase()}...`}
              autoFocus
            />
            {hasError && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error?.message}</p>
            )}
          </div>
        )

      case 'select':
        const options = field.config?.options || []
        return (
          <div>
            <select
              value={value}
              onChange={(e) => handleFieldChange(field.name, e.target.value)}
              onBlur={() => toggleFieldEdit(field.name)}
              className={inputClass}
              autoFocus
            >
              <option value="">Select {field.display_name || field.name}</option>
              {options.map((option: any) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            {hasError && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error?.message}</p>
            )}
          </div>
        )

      case 'boolean':
        return (
          <div>
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={Boolean(value)}
                onChange={(e) => handleFieldChange(field.name, e.target.checked)}
                onBlur={() => toggleFieldEdit(field.name)}
                className="mr-2 rounded border-gray-300 text-primary focus:ring-primary"
                autoFocus
              />
              <span className="text-sm">{field.display_name || field.name}</span>
            </label>
          </div>
        )

      case 'date':
        return (
          <div>
            <input
              type="date"
              value={value ? new Date(value).toISOString().split('T')[0] : ''}
              onChange={(e) => handleFieldChange(field.name, e.target.value)}
              onBlur={() => toggleFieldEdit(field.name)}
              className={inputClass}
              autoFocus
            />
            {hasError && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error?.message}</p>
            )}
          </div>
        )

      case 'datetime':
        return (
          <div>
            <input
              type="datetime-local"
              value={value ? new Date(value).toISOString().slice(0, 16) : ''}
              onChange={(e) => handleFieldChange(field.name, e.target.value)}
              onBlur={() => toggleFieldEdit(field.name)}
              className={inputClass}
              autoFocus
            />
            {hasError && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error?.message}</p>
            )}
          </div>
        )

      case 'number':
      case 'decimal':
        return (
          <div>
            <input
              type="number"
              step={field.field_type === 'decimal' ? '0.01' : '1'}
              value={value}
              onChange={(e) => handleFieldChange(field.name, e.target.value)}
              onBlur={() => toggleFieldEdit(field.name)}
              className={inputClass}
              placeholder={`Enter ${(field.display_name || field.name).toLowerCase()}...`}
              autoFocus
            />
            {hasError && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error?.message}</p>
            )}
          </div>
        )

      default:
        return (
          <div>
            <input
              type={field.field_type === 'email' ? 'email' : field.field_type === 'url' ? 'url' : 'text'}
              value={value}
              onChange={(e) => handleFieldChange(field.name, e.target.value)}
              onBlur={() => toggleFieldEdit(field.name)}
              className={inputClass}
              placeholder={`Enter ${(field.display_name || field.name).toLowerCase()}...`}
              autoFocus
            />
            {hasError && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error?.message}</p>
            )}
          </div>
        )
    }
  }

  // Format display value
  const formatDisplayValue = (field: RecordField, value: any) => {
    if (value === null || value === undefined || value === '') return ''

    switch (field.field_type) {
      case 'date':
        return new Date(value).toLocaleDateString()
      case 'datetime':
        return new Date(value).toLocaleString()
      case 'boolean':
        return value ? 'Yes' : 'No'
      case 'decimal':
        return typeof value === 'number' ? value.toLocaleString(undefined, { minimumFractionDigits: 2 }) : value
      case 'number':
        return typeof value === 'number' ? value.toLocaleString() : value
      default:
        return String(value)
    }
  }

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
              {/* Tags */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Tags
                </label>
                <div className="flex flex-wrap gap-2 mb-2">
                  {tags.map((tag) => (
                    <span
                      key={tag}
                      className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
                    >
                      {tag}
                      <button
                        onClick={() => handleRemoveTag(tag)}
                        className="ml-1.5 text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-200"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  ))}
                  
                  {showTagInput ? (
                    <div className="flex items-center space-x-2">
                      <input
                        type="text"
                        value={newTag}
                        onChange={(e) => setNewTag(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleAddTag()}
                        onBlur={() => setShowTagInput(false)}
                        className="px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700"
                        placeholder="Enter tag..."
                        autoFocus
                      />
                    </div>
                  ) : (
                    <button
                      onClick={() => setShowTagInput(true)}
                      className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border-2 border-dashed border-gray-300 dark:border-gray-600 text-gray-500 hover:border-gray-400 dark:hover:border-gray-500"
                    >
                      <Plus className="w-3 h-3 mr-1" />
                      Add Tag
                    </button>
                  )}
                </div>
              </div>

              {/* Fields */}
              <div className="space-y-4">
                {pipeline.fields
                  .filter(field => field.is_visible_in_detail !== false)
                  .sort((a, b) => (a.display_order || 0) - (b.display_order || 0))
                  .map((field) => (
                    <div key={field.name}>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        {field.display_name || field.name}
                        {field.is_required && <span className="text-red-500 ml-1">*</span>}
                      </label>
                      {renderFieldInput(field)}
                    </div>
                  ))}
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
                        {activity.action === 'created' && <Plus className="w-4 h-4 text-green-600 dark:text-green-400" />}
                        {activity.action === 'updated' && <Edit className="w-4 h-4 text-blue-600 dark:text-blue-400" />}
                        {activity.action === 'deleted' && <Trash2 className="w-4 h-4 text-red-600 dark:text-red-400" />}
                        {!['created', 'updated', 'deleted'].includes(activity.action) && <Clock className="w-4 h-4 text-gray-600 dark:text-gray-400" />}
                      </div>
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="text-sm text-gray-900 dark:text-white">
                        <span className="font-medium">
                          {activity.user_name || activity.user || 'System'}
                        </span>
                        {' '}
                        <span>{activity.changes}</span>
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        {formatActivityTime(activity.timestamp || activity.created_at)}
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
                  const shareUrl = `${window.location.origin}/forms/shared/${pipeline.slug}/${record.id}?token=sharing_token_here`
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
              >
                <Trash2 className="w-4 h-4 mr-2 inline" />
                Delete
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