'use client'

import React, { useState, useEffect, useMemo } from 'react'
import { pipelinesApi } from '@/lib/api'
import { usePipelineRecordsSubscription } from '@/hooks/use-websocket-subscription'
import { type RealtimeMessage } from '@/contexts/websocket-context'
import { useAuth } from '@/features/auth/context'
import { RealtimeDiagnostics } from '../realtime-diagnostics'
import { FieldResolver } from '@/lib/field-system/field-registry'
import { Field } from '@/lib/field-system/types'
import { KanbanView } from './kanban-view'
import { CalendarView } from './calendar-view'
// Import field system to ensure initialization
import '@/lib/field-system'
import { 
  Search, 
  Filter, 
  Plus, 
  MoreHorizontal, 
  ArrowUpDown, 
  ArrowUp, 
  ArrowDown,
  Eye,
  Edit,
  Trash2,
  Download,
  Upload,
  RefreshCw,
  CheckSquare,
  Square,
  X,
  Tag,
  Calendar,
  User,
  Hash,
  Type,
  Mail,
  Phone,
  Link,
  FileText,
  Image,
  Database,
  Users,
  Bot,
  AlertCircle,
  Table,
  Columns,
  CalendarDays
} from 'lucide-react'

// Field type icons
const FIELD_ICONS = {
  text: Type,
  textarea: FileText,
  number: Hash,
  decimal: Hash,
  integer: Hash,
  float: Hash,
  currency: Hash,
  percentage: Hash,
  boolean: CheckSquare,
  date: Calendar,
  datetime: Calendar,
  time: Calendar,
  select: CheckSquare,
  multiselect: CheckSquare,
  radio: CheckSquare,
  checkbox: CheckSquare,
  email: Mail,
  phone: Phone,
  url: Link,
  address: Hash,
  file: FileText,
  image: Image,
  relation: Link,
  user: Users,
  ai: Bot,
  ai_field: Bot,
  button: Bot,
  tags: Tag
}

export interface RecordField {
  id: string
  name: string
  display_name?: string
  field_type: keyof typeof FIELD_ICONS
  is_required?: boolean
  is_visible_in_list?: boolean
  is_visible_in_detail?: boolean
  display_order: number
  field_config?: { [key: string]: any }
  config?: { [key: string]: any } // Legacy support
  business_rules?: {
    stage_requirements?: {[key: string]: { 
      required: boolean
      block_transitions?: boolean
      show_warnings?: boolean
      warning_message?: string
    }}
    user_visibility?: {[key: string]: { visible: boolean; editable: boolean }}
  }
}

// Convert RecordField to Field type for field registry
export const convertToFieldType = (recordField: RecordField): Field => ({
  id: recordField.id,
  name: recordField.name,
  display_name: recordField.display_name,
  field_type: recordField.field_type as string,
  field_config: recordField.field_config,
  config: recordField.config, // Legacy support
  is_required: recordField.is_required,
  is_readonly: false, // List view doesn't handle readonly
  help_text: undefined,
  placeholder: undefined
})

export interface Record {
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

export interface Pipeline {
  id: string
  name: string
  description: string
  fields: RecordField[]
  stages?: string[]
  record_count: number
}

export interface RecordListViewProps {
  pipeline: Pipeline
  onEditRecord: (record: Record) => void
  onCreateRecord: () => void
}

type ViewMode = 'table' | 'kanban' | 'calendar'
type SortDirection = 'asc' | 'desc' | null
type FilterOperator = 'equals' | 'contains' | 'starts_with' | 'ends_with' | 'greater_than' | 'less_than' | 'is_empty' | 'is_not_empty'

interface Filter {
  field: string
  operator: FilterOperator
  value: any
}

interface Sort {
  field: string
  direction: SortDirection
}

export function RecordListView({ pipeline, onEditRecord, onCreateRecord }: RecordListViewProps) {
  const { user } = useAuth()
  const [records, setRecords] = useState<Record[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedRecords, setSelectedRecords] = useState<Set<string>>(new Set())
  const [showFilters, setShowFilters] = useState(false)
  const [filters, setFilters] = useState<Filter[]>([])
  const [sort, setSort] = useState<Sort>({ field: 'updated_at', direction: 'desc' })
  const [visibleFields, setVisibleFields] = useState<Set<string>>(new Set())
  const [currentPage, setCurrentPage] = useState(1)
  const [recordsPerPage] = useState(50)
  const [viewMode, setViewMode] = useState<ViewMode>('table')
  const [kanbanField, setKanbanField] = useState<string>('')
  const [calendarField, setCalendarField] = useState<string>('')

  // WebSocket integration for real-time updates
  const handleRealtimeMessage = (message: RealtimeMessage) => {
    console.log('📨 Record list received realtime message:', message)
    console.log('🔍 Pipeline comparison:', {
      messagePipelineId: message.payload?.pipeline_id,
      currentPipelineId: pipeline.id,
      matches: message.payload?.pipeline_id === pipeline.id
    })
    
    switch (message.type) {
      case 'record_create':
        if (String(message.payload?.pipeline_id) === String(pipeline.id)) {
          // Construct record object from payload
          const newRecord = {
            id: message.payload.record_id,
            data: message.payload.data || {},
            created_at: message.payload.updated_at || new Date().toISOString(),
            updated_at: message.payload.updated_at || new Date().toISOString(),
            created_by: message.payload.updated_by
          }
          setRecords(prev => [newRecord, ...prev])
          console.log('✅ Added new record to list:', newRecord.id)
        }
        break
        
      case 'record_update':
        if (String(message.payload?.pipeline_id) === String(pipeline.id)) {
          // Construct updated record object from payload
          const updatedRecord = {
            id: message.payload.record_id,
            data: message.payload.data || {},
            updated_at: message.payload.updated_at || new Date().toISOString(),
            created_by: message.payload.updated_by
          }
          
          console.log('🔄 RECORD UPDATE DEBUG:', {
            messageRecordId: message.payload.record_id,
            messagePipelineId: message.payload.pipeline_id,
            currentPipelineId: pipeline.id,
            existingRecordsCount: records.length,
            recordExists: records.some(r => String(r.id) === String(updatedRecord.id))
          })
          
          setRecords(prev => {
            const newRecords = prev.map(record => {
              if (String(record.id) === String(updatedRecord.id)) {
                // CRITICAL: Merge with existing data to prevent data loss
                const mergedRecord = {
                  ...record, // Keep all existing record data
                  ...updatedRecord, // Apply updates
                  data: {
                    ...record.data, // Keep all existing field data
                    ...updatedRecord.data // Apply only the updated fields
                  }
                }
                console.log('🔄 MERGE DEBUG:', {
                  originalData: record.data,
                  updateData: updatedRecord.data,
                  mergedData: mergedRecord.data
                })
                return mergedRecord
              }
              return record
            })
            console.log('✅ Updated record in list:', updatedRecord.id, 'New count:', newRecords.length)
            return newRecords
          })
        } else {
          console.log('❌ Pipeline ID mismatch for record_update:', {
            messagePipelineId: message.payload?.pipeline_id,
            currentPipelineId: pipeline.id
          })
        }
        break
        
      case 'record_delete':
        if (String(message.payload?.pipeline_id) === String(pipeline.id)) {
          // Remove record from the list
          const deletedRecordId = message.payload.record_id
          setRecords(prev => prev.filter(record => String(record.id) !== String(deletedRecordId)))
          console.log('✅ Removed record from list:', deletedRecordId)
        } else {
          console.log('❌ Pipeline ID mismatch for record_delete:', {
            messagePipelineId: message.payload?.pipeline_id,
            currentPipelineId: pipeline.id
          })
        }
        break
    }
  }

  // Subscribe to pipeline record updates using centralized WebSocket
  const { isConnected } = usePipelineRecordsSubscription(
    pipeline.id,
    handleRealtimeMessage
  )

  // Debug log for WebSocket connection with enhanced status
  useEffect(() => {
    console.log('🔌 REALTIME STATUS for Record List:', {
      pipelineId: pipeline.id,
      channel: `pipeline_records_${pipeline.id}`,
      isConnected,
      recordCount: records.length,
      timestamp: new Date().toISOString()
    })
    
    // Test WebSocket connectivity by logging subscription
    if (isConnected) {
      console.log('✅ WebSocket CONNECTED - Ready for real-time updates')
    } else {
      console.log('❌ WebSocket DISCONNECTED - Real-time updates unavailable')
    }
  }, [pipeline.id, isConnected, records.length])

  // Initialize visible fields (show all columns, permissions applied per row)
  useEffect(() => {
    const defaultVisible = pipeline.fields
      .filter(field => field.is_visible_in_list !== false)
      .map(field => field.name)
    setVisibleFields(new Set(defaultVisible))
  }, [pipeline.fields])

  // Field analysis for view capabilities
  const getSelectFields = useMemo(() => {
    return pipeline.fields.filter(field => 
      field.field_type === 'select' || field.field_type === 'multiselect'
    ).map(field => ({
      value: field.name,
      label: field.display_name || field.name,
      options: field.field_config?.options || []
    }))
  }, [pipeline.fields])

  const getDateFields = useMemo(() => {
    return pipeline.fields.filter(field => 
      field.field_type === 'date' || field.field_type === 'datetime'
    ).map(field => ({
      value: field.name,
      label: field.display_name || field.name,
      type: field.field_type
    }))
  }, [pipeline.fields])

  // Auto-select default fields for views
  useEffect(() => {
    if (!kanbanField && getSelectFields.length > 0) {
      // Look for common status/stage field names first
      const statusField = getSelectFields.find(f => 
        ['status', 'stage', 'phase', 'state', 'pipeline_stage'].includes(f.value.toLowerCase())
      )
      setKanbanField(statusField?.value || getSelectFields[0].value)
    }

    if (!calendarField && getDateFields.length > 0) {
      // Look for common date field names first
      const dateField = getDateFields.find(f => 
        ['due_date', 'start_date', 'end_date', 'created_at', 'updated_at'].includes(f.value.toLowerCase())
      )
      setCalendarField(dateField?.value || getDateFields[0].value)
    }
  }, [getSelectFields, getDateFields, kanbanField, calendarField])

  // Load records
  useEffect(() => {
    const loadRecords = async () => {
      try {
        setLoading(true)
        setError(null)
        
        // Build query parameters
        const params: any = {
          page: currentPage,
          page_size: recordsPerPage,
        }
        
        // Add search query
        if (searchQuery.trim()) {
          params.search = searchQuery.trim()
        }
        
        // Add filters
        if (filters.length > 0) {
          filters.forEach((filter, index) => {
            params[`filter_${index}_field`] = filter.field
            params[`filter_${index}_operator`] = filter.operator
            params[`filter_${index}_value`] = filter.value
          })
        }
        
        // Add sorting
        if (sort.field && sort.direction) {
          params.ordering = sort.direction === 'desc' ? `-${sort.field}` : sort.field
        }
        
        const response = await pipelinesApi.getRecords(pipeline.id, params)
        setRecords(response.data.results || response.data)
      } catch (error: any) {
        console.error('Failed to load records:', error)
        setError(error.response?.data?.message || error.message || 'Failed to load records')
        setRecords([])
      } finally {
        setLoading(false)
      }
    }

    loadRecords()
  }, [pipeline.id, filters, sort, searchQuery, currentPage, recordsPerPage])

  // Filter and sort records
  const filteredAndSortedRecords = useMemo(() => {
    let filtered = records

    // Apply search
    if (searchQuery) {
      filtered = filtered.filter(record => 
        Object.values(record.data).some(value =>
          String(value).toLowerCase().includes(searchQuery.toLowerCase())
        )
      )
    }

    // Apply filters
    filtered = filtered.filter(record => {
      return filters.every(filter => {
        const value = record.data[filter.field]
        
        switch (filter.operator) {
          case 'equals':
            return value === filter.value
          case 'contains':
            return String(value).toLowerCase().includes(String(filter.value).toLowerCase())
          case 'starts_with':
            return String(value).toLowerCase().startsWith(String(filter.value).toLowerCase())
          case 'ends_with':
            return String(value).toLowerCase().endsWith(String(filter.value).toLowerCase())
          case 'greater_than':
            return Number(value) > Number(filter.value)
          case 'less_than':
            return Number(value) < Number(filter.value)
          case 'is_empty':
            return !value || value === ''
          case 'is_not_empty':
            return value && value !== ''
          default:
            return true
        }
      })
    })

    // Apply sorting
    if (sort.field && sort.direction) {
      filtered.sort((a, b) => {
        const aValue = a.data[sort.field] || ''
        const bValue = b.data[sort.field] || ''
        
        if (sort.direction === 'asc') {
          return aValue > bValue ? 1 : -1
        } else {
          return aValue < bValue ? 1 : -1
        }
      })
    }

    return filtered
  }, [records, searchQuery, filters, sort])

  // Pagination
  const totalPages = Math.ceil(filteredAndSortedRecords.length / recordsPerPage)
  const paginatedRecords = filteredAndSortedRecords.slice(
    (currentPage - 1) * recordsPerPage,
    currentPage * recordsPerPage
  )

  // Handle sort
  const handleSort = (fieldName: string) => {
    setSort(prev => ({
      field: fieldName,
      direction: prev.field === fieldName 
        ? prev.direction === 'asc' ? 'desc' : 'asc'
        : 'asc'
    }))
  }

  // Handle select all
  const handleSelectAll = () => {
    if (selectedRecords.size === paginatedRecords.length) {
      setSelectedRecords(new Set())
    } else {
      setSelectedRecords(new Set(paginatedRecords.map(r => r.id)))
    }
  }

  // Handle select record
  const handleSelectRecord = (recordId: string) => {
    const newSelected = new Set(selectedRecords)
    if (newSelected.has(recordId)) {
      newSelected.delete(recordId)
    } else {
      newSelected.add(recordId)
    }
    setSelectedRecords(newSelected)
  }

  // Format field value for display using field registry
  const formatFieldValue = (field: RecordField, value: any) => {
    const fieldType = convertToFieldType(field)
    const formattedValue = FieldResolver.formatValue(fieldType, value, 'table')
    
    // Ensure JSX elements are properly rendered
    if (React.isValidElement(formattedValue)) {
      return formattedValue
    }
    
    // Handle null/undefined values
    if (value === null || value === undefined || value === '') {
      return (
        <span className="text-gray-400 dark:text-gray-500 italic text-xs">
          Empty
        </span>
      )
    }
    
    return formattedValue
  }
  
  // Render interactive field in table context
  const renderInteractiveField = (field: RecordField, record: Record) => {
    const fieldType = convertToFieldType(field)
    const value = record.data[field.name]
    
    if (field.field_type === 'button') {
      // Extract button configuration
      const buttonConfig = field.field_config || {}
      const buttonText = buttonConfig.button_text || 'Click Me'
      const buttonStyle = buttonConfig.button_style || 'primary'
      const buttonSize = 'small' // Always use small size in tables
      const requireConfirmation = buttonConfig.require_confirmation || false
      const confirmationMessage = buttonConfig.confirmation_message || 'Are you sure?'
      const disableAfterClick = buttonConfig.disable_after_click || false
      const workflowId = buttonConfig.workflow_id
      
      // Check if button has been clicked (complex object check)
      const hasBeenClicked = value && typeof value === 'object' && value.triggered === true
      const isDisabled = disableAfterClick && hasBeenClicked
      
      const buttonStyles = {
        primary: 'bg-blue-600 hover:bg-blue-700 text-white',
        secondary: 'bg-gray-600 hover:bg-gray-700 text-white',
        success: 'bg-green-600 hover:bg-green-700 text-white',
        warning: 'bg-yellow-600 hover:bg-yellow-700 text-white',
        danger: 'bg-red-600 hover:bg-red-700 text-white'
      }
      
      const handleButtonClick = async (e: React.MouseEvent) => {
        e.stopPropagation() // Prevent row click
        
        if (requireConfirmation) {
          if (!window.confirm(confirmationMessage)) {
            return
          }
        }
        
        // For existing records, save the button click state
        if (record && record.id) {
          try {
            console.log(`🔘 BUTTON STEP 1: Button Click Handler Started`)
            console.log(`   🎯 Button: "${buttonText}" (${field.name})`)
            console.log(`   📋 Record ID: ${record.id}`)
            console.log(`   📊 Pipeline ID: ${pipeline.id}`)
            console.log(`   🔄 Current Value: ${value}`)
            console.log(`   ⚙️  Disable After Click: ${disableAfterClick}`)
            
            // ✅ CRITICAL FIX: Always create a detectable change for button clicks  
            // Each click must create a unique change to trigger AI processing
            // This matches the button-field.tsx implementation exactly
            const currentValue = value || {}
            const clickTimestamp = new Date().toISOString()
            
            const newValue = {
              type: 'button',
              triggered: true,
              last_triggered: clickTimestamp,
              click_count: (currentValue.click_count || 0) + 1, // Always increment for unique change
              config: {
                help_text: field.field_config?.help_text,
                button_text: buttonText,
                button_style: buttonStyle,
                button_size: 'small',
                workflow_id: workflowId,
                workflow_params: {},
                require_confirmation: requireConfirmation,
                confirmation_message: confirmationMessage,
                disable_after_click: disableAfterClick,
                visible_to_roles: [],
                clickable_by_roles: []
              }
            }
            
            console.log(`🔘 BUTTON STEP 2: Preparing API Update`)
            console.log(`   🎯 New Value: ${JSON.stringify(newValue)} (${typeof newValue})`)
            console.log(`   🔍 Has Last Triggered: ${!!newValue.last_triggered}`)
            console.log(`   🔍 Has Click Count: ${!!newValue.click_count}`)
            
            // Call the API to update the record
            console.log(`🔘 BUTTON STEP 3: Making API Call`)
            await pipelinesApi.updateRecord(pipeline.id, record.id, {
              data: {
                [field.name]: newValue
              }
            })
            
            console.log(`🔘 BUTTON STEP 4: API Call Completed Successfully`)
            console.log(`   ✅ Button "${buttonText}" processed for record ${record.id}`)
            
            // If there's a workflow, trigger it
            if (workflowId) {
              console.log(`Triggering workflow: ${workflowId}`)
              // TODO: Implement workflow trigger API call
            }
            
          } catch (error) {
            console.error('Failed to update button field:', error)
          }
        } else {
          // For new records (shouldn't happen in list view), just log
          console.log(`Button "${buttonText}" clicked`)
        }
      }
      
      return (
        <button
          type="button"
          onClick={handleButtonClick}
          disabled={isDisabled}
          className={`
            px-3 py-1.5 text-xs rounded-md transition-all duration-200 font-medium focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-blue-500
            ${buttonStyles[buttonStyle as keyof typeof buttonStyles] || buttonStyles.primary}
            ${isDisabled 
              ? 'opacity-50 cursor-not-allowed' 
              : 'hover:shadow-sm transform hover:scale-105'
            }
          `}
          title={disableAfterClick && hasBeenClicked ? 'Button has been clicked' : undefined}
        >
          {buttonText}
          {disableAfterClick && hasBeenClicked && ' ✓'}
        </button>
      )
    }
    
    if (field.field_type === 'boolean') {
      const handleToggle = async (e: React.MouseEvent) => {
        e.stopPropagation() // Prevent row click
        
        if (record && record.id) {
          try {
            const newValue = !value
            
            // Call the API to update the record
            await pipelinesApi.updateRecord(pipeline.id, record.id, {
              data: {
                [field.name]: newValue
              }
            })
            
            console.log(`Boolean field "${field.name}" toggled for record ${record.id}`)
            
          } catch (error) {
            console.error('Failed to update boolean field:', error)
          }
        }
      }
      
      return (
        <button
          type="button"
          onClick={handleToggle}
          className="text-gray-600 hover:text-blue-600 dark:text-gray-400 dark:hover:text-blue-400 transition-colors"
        >
          {value ? (
            <CheckSquare className="w-4 h-4 text-green-600" />
          ) : (
            <Square className="w-4 h-4" />
          )}
        </button>
      )
    }
    
    // For other interactive fields, fall back to formatted value
    return formatFieldValue(field, value)
  }
  
  // Get column width based on field type
  const getColumnWidth = (field: RecordField): string => {
    switch (field.field_type) {
      case 'boolean':
        return 'w-16' // Narrow for checkboxes
      case 'date':
      case 'datetime':
        return 'w-32' // Medium for dates
      case 'time':
        return 'w-24' // Small for time
      case 'number':
      case 'decimal':
        return 'w-24' // Small for numbers
      case 'email':
      case 'phone':
        return 'w-48' // Medium for contact info
      case 'url':
        return 'w-40' // Medium for URLs
      case 'tags':
        return 'w-56' // Larger for tag arrays
      case 'textarea':
        return 'w-64' // Larger for long text
      case 'ai_field':
        return 'w-64' // Larger for AI-generated content
      case 'button':
        return 'w-32' // Medium for buttons
      case 'file':
      case 'image':
        return 'w-40' // Medium for file names
      case 'relation':
        return 'w-48' // Medium for related records
      case 'select':
      case 'multiselect':
        return 'w-40' // Medium for selections
      default:
        return 'w-48' // Default medium width for text fields
    }
  }
  
  // Check if field should be interactive in table context
  const isInteractiveField = (field: RecordField): boolean => {
    return ['button', 'boolean'].includes(field.field_type)
  }

  // Handle record field update (for Kanban drag & drop)
  const handleUpdateRecord = async (recordId: string, fieldName: string, value: any) => {
    try {
      await pipelinesApi.updateRecord(pipeline.id, recordId, {
        data: {
          [fieldName]: value
        }
      })
      console.log(`Updated record ${recordId} field ${fieldName} to:`, value)
      // Real-time system will update the UI automatically
    } catch (error) {
      console.error('Failed to update record:', error)
      throw error
    }
  }

  // Get visible fields for table
  const visibleFieldsList = pipeline.fields
    .filter(field => visibleFields.has(field.name))
    .sort((a, b) => (a.display_order || 0) - (b.display_order || 0))

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-primary mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Loading records...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center max-w-md">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            Failed to Load Records
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            {error}
          </p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90"
          >
            <RefreshCw className="w-4 h-4 mr-2 inline" />
            Try Again
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              {pipeline.name}
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              {pipeline.description}
            </p>
          </div>
          
          <div className="flex items-center space-x-3">
            <button
              onClick={onCreateRecord}
              className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90"
            >
              <Plus className="w-4 h-4 mr-2 inline" />
              Add Record
            </button>
            
            {/* WebSocket Connection Status */}
            <div className="flex items-center space-x-2 text-sm text-gray-500 dark:text-gray-400">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
              <span>{isConnected ? 'Live' : 'Offline'}</span>
            </div>
          </div>
        </div>

        {/* Search and Filters */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            {/* View Mode Selector */}
            <div className="flex items-center border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700">
              <button
                onClick={() => setViewMode('table')}
                className={`px-3 py-2 flex items-center text-sm transition-colors ${
                  viewMode === 'table'
                    ? 'bg-primary text-white'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                <Table className="w-4 h-4 mr-2" />
                Table
              </button>
              
              <button
                onClick={() => setViewMode('kanban')}
                disabled={getSelectFields.length === 0}
                className={`px-3 py-2 flex items-center text-sm transition-colors border-l border-gray-300 dark:border-gray-600 ${
                  viewMode === 'kanban'
                    ? 'bg-primary text-white'
                    : getSelectFields.length === 0
                    ? 'text-gray-400 dark:text-gray-500 cursor-not-allowed'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                }`}
                title={getSelectFields.length === 0 ? 'No select fields available for Kanban view' : ''}
              >
                <Columns className="w-4 h-4 mr-2" />
                Kanban
              </button>
              
              <button
                onClick={() => setViewMode('calendar')}
                disabled={getDateFields.length === 0}
                className={`px-3 py-2 flex items-center text-sm transition-colors border-l border-gray-300 dark:border-gray-600 ${
                  viewMode === 'calendar'
                    ? 'bg-primary text-white'
                    : getDateFields.length === 0
                    ? 'text-gray-400 dark:text-gray-500 cursor-not-allowed'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                }`}
                title={getDateFields.length === 0 ? 'No date fields available for Calendar view' : ''}
              >
                <CalendarDays className="w-4 h-4 mr-2" />
                Calendar
              </button>
            </div>

            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search records..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white w-80"
              />
            </div>
            
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`px-3 py-2 border rounded-md flex items-center ${
                showFilters 
                  ? 'border-primary bg-primary/10 text-primary'
                  : 'border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'
              }`}
            >
              <Filter className="w-4 h-4 mr-2" />
              Filters {filters.length > 0 && `(${filters.length})`}
            </button>
          </div>

          <div className="flex items-center space-x-2">
            {selectedRecords.size > 0 && (
              <div className="flex items-center space-x-2 px-3 py-1.5 bg-blue-50 dark:bg-blue-900/20 rounded-md">
                <span className="text-sm text-blue-700 dark:text-blue-300">
                  {selectedRecords.size} selected
                </span>
                <button className="text-blue-600 hover:text-blue-800 dark:hover:text-blue-400">
                  <Trash2 className="w-4 h-4" />
                </button>
                <button className="text-blue-600 hover:text-blue-800 dark:hover:text-blue-400">
                  <Download className="w-4 h-4" />
                </button>
              </div>
            )}
            
            <button className="p-2 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700">
              <Download className="w-4 h-4" />
            </button>
            <button className="p-2 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700">
              <Upload className="w-4 h-4" />
            </button>
            <button 
              onClick={() => window.location.reload()}
              className="p-2 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* View Configuration Panel */}
      {(viewMode === 'kanban' || viewMode === 'calendar') && (
        <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-6">
            {viewMode === 'kanban' && getSelectFields.length > 0 && (
              <div className="flex items-center space-x-2">
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Group by:
                </label>
                <select
                  value={kanbanField}
                  onChange={(e) => setKanbanField(e.target.value)}
                  className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-sm"
                >
                  {getSelectFields.map(field => (
                    <option key={field.value} value={field.value}>
                      {field.label} ({field.options.length} options)
                    </option>
                  ))}
                </select>
              </div>
            )}
            
            {viewMode === 'calendar' && getDateFields.length > 0 && (
              <div className="flex items-center space-x-2">
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Date field:
                </label>
                <select
                  value={calendarField}
                  onChange={(e) => setCalendarField(e.target.value)}
                  className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-sm"
                >
                  {getDateFields.map(field => (
                    <option key={field.value} value={field.value}>
                      {field.label} ({field.type})
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Filters Panel */}
      {showFilters && (
        <div className="p-4 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-gray-900 dark:text-white">Filters</h3>
            <button
              onClick={() => setFilters([])}
              className="text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
            >
              Clear all
            </button>
          </div>
          
          {/* Filter rows would go here */}
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Filter functionality coming soon...
          </p>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex-1 overflow-auto">
        {viewMode === 'table' && (
          <table className="w-full">
          <thead className="bg-gray-50 dark:bg-gray-800 sticky top-0 z-10">
            <tr>
              <th className="w-12 px-4 py-3">
                <button
                  onClick={handleSelectAll}
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  {selectedRecords.size === paginatedRecords.length && paginatedRecords.length > 0 ? (
                    <CheckSquare className="w-4 h-4" />
                  ) : (
                    <Square className="w-4 h-4" />
                  )}
                </button>
              </th>
              
              {visibleFieldsList.map((field) => {
                const Icon = FIELD_ICONS[field.field_type] || Type
                const isSorted = sort.field === field.name
                const columnWidth = getColumnWidth(field)
                
                return (
                  <th
                    key={field.name}
                    className={`${columnWidth} px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider`}
                  >
                    <button
                      onClick={() => handleSort(field.name)}
                      className="flex items-center space-x-2 hover:text-gray-700 dark:hover:text-gray-200"
                    >
                      <Icon className="w-4 h-4" />
                      <span className="truncate">{field.display_name || field.name}</span>
                      {isSorted && (
                        sort.direction === 'asc' ? (
                          <ArrowUp className="w-3 h-3" />
                        ) : (
                          <ArrowDown className="w-3 h-3" />
                        )
                      )}
                    </button>
                  </th>
                )
              })}
              
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          
          <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
            {paginatedRecords.map((record) => (
              <tr
                key={record.id}
                className="hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer"
                onClick={() => onEditRecord(record)}
              >
                <td className="px-4 py-3">
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      handleSelectRecord(record.id)
                    }}
                    className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                  >
                    {selectedRecords.has(record.id) ? (
                      <CheckSquare className="w-4 h-4 text-primary" />
                    ) : (
                      <Square className="w-4 h-4" />
                    )}
                  </button>
                </td>
                
                {visibleFieldsList.map((field) => {
                  const columnWidth = getColumnWidth(field)
                  const isInteractive = isInteractiveField(field)
                  
                  return (
                    <td 
                      key={field.name} 
                      className={`${columnWidth} px-4 py-3 text-sm text-gray-900 dark:text-white`}
                      onClick={(e) => {
                        // Prevent row click for interactive fields
                        if (isInteractive) {
                          e.stopPropagation()
                        }
                      }}
                    >
                      <div className={`${field.field_type === 'textarea' || field.field_type === 'ai_field' ? 'max-h-20 overflow-hidden' : ''}`}>
                        {isInteractive ? (
                          // For interactive fields, render actual interactive components
                          <div className="inline-block">
                            {renderInteractiveField(field, record)}
                          </div>
                        ) : (
                          // For display-only fields, show formatted value with truncation
                          <div className="truncate" title={String(record.data[field.name] || '')}>
                            {formatFieldValue(field, record.data[field.name])}
                          </div>
                        )}
                      </div>
                    </td>
                  )
                })}
                
                <td className="px-4 py-3">
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        onEditRecord(record)
                      }}
                      className="text-gray-400 hover:text-blue-600 dark:hover:text-blue-400"
                    >
                      <Edit className="w-4 h-4" />
                    </button>
                    <button className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
                      <MoreHorizontal className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
          </table>
        )}

        {viewMode === 'kanban' && (
          getSelectFields.length === 0 ? (
            <div className="text-center py-12">
              <Columns className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                No Select Fields Available
              </h3>
              <p className="text-gray-500 dark:text-gray-400">
                Add select or multiselect fields to your pipeline to use Kanban view.
              </p>
            </div>
          ) : (
            <KanbanView
              pipeline={pipeline}
              records={filteredAndSortedRecords}
              kanbanField={kanbanField}
              onEditRecord={onEditRecord}
              onCreateRecord={onCreateRecord}
              onUpdateRecord={handleUpdateRecord}
            />
          )
        )}

        {viewMode === 'calendar' && (
          getDateFields.length === 0 ? (
            <div className="text-center py-12">
              <CalendarDays className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                No Date Fields Available
              </h3>
              <p className="text-gray-500 dark:text-gray-400">
                Add date or datetime fields to your pipeline to use Calendar view.
              </p>
            </div>
          ) : (
            <CalendarView
              pipeline={pipeline}
              records={filteredAndSortedRecords}
              calendarField={calendarField}
              onEditRecord={onEditRecord}
              onCreateRecord={onCreateRecord}
            />
          )
        )}
        
        {viewMode === 'table' && paginatedRecords.length === 0 && (
          <div className="text-center py-12">
            <Database className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              No records found
            </h3>
            <p className="text-gray-500 dark:text-gray-400 mb-6">
              {searchQuery || filters.length > 0
                ? 'Try adjusting your search or filters.'
                : 'Get started by adding your first record.'}
            </p>
            {!searchQuery && filters.length === 0 && (
              <button
                onClick={onCreateRecord}
                className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90"
              >
                <Plus className="w-4 h-4 mr-2 inline" />
                Add First Record
              </button>
            )}
          </div>
        )}
      </div>

      {/* Pagination (Table view only) */}
      {viewMode === 'table' && totalPages > 1 && (
        <div className="p-4 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Showing {((currentPage - 1) * recordsPerPage) + 1} to {Math.min(currentPage * recordsPerPage, filteredAndSortedRecords.length)} of {filteredAndSortedRecords.length} records
          </div>
          
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
              disabled={currentPage === 1}
              className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              const page = i + 1
              return (
                <button
                  key={page}
                  onClick={() => setCurrentPage(page)}
                  className={`px-3 py-1 border rounded-md ${
                    currentPage === page
                      ? 'border-primary bg-primary text-white'
                      : 'border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'
                  }`}
                >
                  {page}
                </button>
              )
            })}
            
            <button
              onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
              disabled={currentPage === totalPages}
              className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* Realtime Diagnostics (development only) */}
      <RealtimeDiagnostics pipelineId={pipeline.id} />
    </div>
  )
}