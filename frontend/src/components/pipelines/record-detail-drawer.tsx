'use client'

import { useState, useEffect, useRef } from 'react'
import { pipelinesApi, recordsApi } from '@/lib/api'
import { useRealtime, type RealtimeMessage, type UserPresence, type FieldLock } from '@/hooks/use-realtime'
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
  Bot
} from 'lucide-react'

interface RecordField {
  id: string
  name: string
  label: string
  field_type: string
  required: boolean
  visible: boolean
  order: number
  config: { [key: string]: any }
  stage_visibility?: { [key: string]: boolean }
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
  const {
    isConnected,
    activeUsers,
    fieldLocks,
    lockField,
    unlockField,
    broadcastRecordUpdate,
    isFieldLocked,
    getFieldLock
  } = useRealtime({
    room: record ? `document:${record.id}` : undefined,
    autoConnect: false, // Disabled to prevent WebSocket errors
    onMessage: (message: RealtimeMessage) => {
      if (message.type === 'record_update' && message.payload.record_id === record?.id) {
        // Update form data with real-time changes from other users
        if (message.payload.field_name && message.payload.value !== undefined) {
          setFormData(prev => ({
            ...prev,
            [message.payload.field_name]: message.payload.value
          }))
        }
      }
    }
  })

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
        // Defensive programming: check if config exists and has default_value
        const defaultValue = field.config?.default_value
        if (defaultValue !== undefined) {
          defaultData[field.name] = defaultValue
        }
      })
      setFormData(defaultData)
      setOriginalData({})
      setTags([])
      setActivities([])
    }
    setEditingFields(new Set())
    setValidationErrors([])
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
      // TODO: Replace with actual API call
      const mockActivities: Activity[] = [
        {
          id: '1',
          type: 'field_change',
          field: 'stage',
          old_value: 'lead',
          new_value: 'qualified',
          message: 'Changed stage from Lead to Qualified',
          user: { first_name: 'John', last_name: 'Doe', email: 'john@example.com' },
          created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString()
        },
        {
          id: '2',
          type: 'comment',
          message: 'Had a great call with the client. They are very interested in our solution.',
          user: { first_name: 'Jane', last_name: 'Smith', email: 'jane@example.com' },
          created_at: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString()
        },
        {
          id: '3',
          type: 'system',
          message: 'Record created',
          user: { first_name: 'System', last_name: '', email: '' },
          created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString()
        }
      ]
      setActivities(mockActivities)
      
      // TODO: Replace with actual API call when backend is ready
      // const response = await recordsApi.getRecordActivity(pipeline.id, recordId)
      // setActivities(response.data.results || response.data)
    } catch (error) {
      console.error('Failed to load activities:', error)
    }
  }

  // Handle auto-save
  const handleAutoSave = async () => {
    if (!record) return

    try {
      setIsAutoSaving(true)
      const errors = validateForm()
      
      if (errors.length === 0) {
        // Use API directly for auto-save
        await pipelinesApi.updateRecord(pipeline.id, record.id, {
          data: formData,
          tags: tags
        })
        setOriginalData({ ...formData })
        setLastSaved(new Date())
        
        // Also call parent onSave for UI updates
        await onSave(record.id, formData)
      } else {
        setValidationErrors(errors)
      }
    } catch (error) {
      console.error('Auto-save failed:', error)
    } finally {
      setIsAutoSaving(false)
    }
  }

  // Validate form data
  const validateForm = (): ValidationError[] => {
    const errors: ValidationError[] = []

    pipeline.fields.forEach(field => {
      const value = formData[field.name]
      
      // Required field validation
      if (field.required && (!value || value === '')) {
        errors.push({
          field: field.name,
          message: `${field.label} is required`
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
    if (!record) return

    // Check if field is locked by another user
    if (isFieldLocked(record.id, fieldName)) {
      return // Cannot edit locked field
    }

    const newEditing = new Set(editingFields)
    if (newEditing.has(fieldName)) {
      // Exiting edit mode - unlock field
      newEditing.delete(fieldName)
      if (isConnected) {
        unlockField(record.id, fieldName)
      }
    } else {
      // Entering edit mode - lock field
      newEditing.add(fieldName)
      if (isConnected) {
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
    const isEditing = editingFields.has(field.name)
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
              {isLocked && fieldLock && (
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
              placeholder={`Enter ${field.label.toLowerCase()}...`}
              autoFocus
            />
            {hasError && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error?.message}</p>
            )}
          </div>
        )

      case 'select':
        const options = field.config.options || []
        return (
          <div>
            <select
              value={value}
              onChange={(e) => handleFieldChange(field.name, e.target.value)}
              onBlur={() => toggleFieldEdit(field.name)}
              className={inputClass}
              autoFocus
            >
              <option value="">Select {field.label}</option>
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
              <span className="text-sm">{field.label}</span>
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
              placeholder={`Enter ${field.label.toLowerCase()}...`}
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
              placeholder={`Enter ${field.label.toLowerCase()}...`}
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
    const date = new Date(timestamp)
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
                  .filter(field => field.visible)
                  .sort((a, b) => a.order - b.order)
                  .map((field) => (
                    <div key={field.name}>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        {field.label}
                        {field.required && <span className="text-red-500 ml-1">*</span>}
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
                {activities.map((activity) => (
                  <div key={activity.id} className="flex space-x-3">
                    <div className="flex-shrink-0">
                      <div className="w-8 h-8 bg-gray-200 dark:bg-gray-600 rounded-full flex items-center justify-center">
                        {activity.type === 'field_change' && <Edit className="w-4 h-4 text-gray-600 dark:text-gray-400" />}
                        {activity.type === 'comment' && <MessageSquare className="w-4 h-4 text-gray-600 dark:text-gray-400" />}
                        {activity.type === 'system' && <Clock className="w-4 h-4 text-gray-600 dark:text-gray-400" />}
                      </div>
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="text-sm text-gray-900 dark:text-white">
                        <span className="font-medium">
                          {activity.user.first_name} {activity.user.last_name}
                        </span>
                        {' '}
                        <span>{activity.message}</span>
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
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
              onClick={() => record && handleAutoSave()}
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