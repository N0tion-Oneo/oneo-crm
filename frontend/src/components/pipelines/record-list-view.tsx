'use client'

import React, { useState, useEffect, useMemo, useRef } from 'react'
import { pipelinesApi, usersApi, relationshipsApi } from '@/lib/api'
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
  // is_required: recordField.is_required, // Removed - not needed for filtering
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

interface FilterGroup {
  id: string
  logic: 'AND' | 'OR'
  filters: Filter[]
}

interface BooleanQuery {
  groups: FilterGroup[]
  groupLogic: 'AND' | 'OR'
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
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('')
  const [selectedRecords, setSelectedRecords] = useState<Set<string>>(new Set())
  const [showFilters, setShowFilters] = useState(false)
  // draftFilters removed - filters now apply immediately
  const [appliedFilters, setAppliedFilters] = useState<Filter[]>([]) // Filters applied to server
  const [booleanQuery, setBooleanQuery] = useState<BooleanQuery>({
    groups: [{
      id: 'group-1',
      logic: 'AND',
      filters: []
    }],
    groupLogic: 'AND'
  })
  const [sort, setSort] = useState<Sort>({ field: 'updated_at', direction: 'desc' })
  const searchTimeoutRef = useRef<NodeJS.Timeout>()
  const [visibleFields, setVisibleFields] = useState<Set<string>>(new Set())
  const [currentPage, setCurrentPage] = useState(1)
  const [recordsPerPage] = useState(50)
  const [viewMode, setViewMode] = useState<ViewMode>('table')
  const [kanbanField, setKanbanField] = useState<string>('')
  const [calendarField, setCalendarField] = useState<string>('')
  
  // Filter builder state
  const [newFilterField, setNewFilterField] = useState('')
  const [newFilterOperator, setNewFilterOperator] = useState<FilterOperator>('equals')
  const [newFilterValue, setNewFilterValue] = useState('')
  const [selectedGroupId, setSelectedGroupId] = useState<string>('group-1') // Default to first group
  const [fieldOptionsCache, setFieldOptionsCache] = useState<Record<string, {value: string, label: string}[]>>({})

  // Debounced search to avoid API calls on every keystroke
  useEffect(() => {
    // Clear existing timeout
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current)
    }

    // Set new timeout
    searchTimeoutRef.current = setTimeout(() => {
      setDebouncedSearchQuery(searchQuery)
    }, 500) // 500ms delay

    // Cleanup function
    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current)
      }
    }
  }, [searchQuery])

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

  // Fetch field options from server
  const fetchFieldOptions = async (fieldName: string, fieldType: string): Promise<{value: string, label: string}[]> => {
    try {
      switch (fieldType) {
        case 'tags':
          // Fetch all records to extract unique tags
          const tagsResponse = await pipelinesApi.getRecords(pipeline.id, { 
            limit: 500, // Get a good sample size to find most tags
            page_size: 500 // Alternative parameter name
          })
          
          const uniqueTags = new Set<string>()
          
          // Extract tags from the response
          if (tagsResponse.data.results) {
            tagsResponse.data.results.forEach((record: any) => {
              // Check both the top-level tags property and the field name in data
              const topLevelTags = record.tags
              const fieldTags = record.data?.[fieldName] // Use the actual field name
              
              // Try both locations (field data first, then top-level)
              const tagsToProcess = fieldTags || topLevelTags
              
              if (tagsToProcess && Array.isArray(tagsToProcess)) {
                tagsToProcess.forEach((tag: string) => {
                  if (tag && tag.trim()) {
                    uniqueTags.add(tag.trim())
                  }
                })
              }
            })
          }
          
          return Array.from(uniqueTags).sort().map(tag => ({ value: tag, label: tag }))
          
        case 'user':
          // Fetch available users for this tenant
          const usersResponse = await usersApi.list()
          
          // Handle different possible response structures
          const users = usersResponse.data.results || usersResponse.data || []
          return users.map((user: any) => ({
            value: user.id.toString(),
            label: `${user.first_name || ''} ${user.last_name || ''}`.trim() || user.email || user.username || `User ${user.id}`
          }))
          
        case 'relation':
        case 'relationship':
        case 'related':
          // For relations, we need to find the target pipeline from field configuration
          const field = pipeline.fields.find(f => f.name === fieldName)
          console.log(`🔗 Relation field "${fieldName}" config:`, field?.field_config)
          
          // Check for both possible config keys
          const targetPipelineId = field?.field_config?.target_pipeline_id || field?.field_config?.target_pipeline
          
          if (!targetPipelineId) {
            console.log(`🔗 No target pipeline specified for relation field ${fieldName}`)
            return []
          }
          console.log(`🔗 Fetching records from target pipeline ${targetPipelineId}`)
          
          try {
            // Fetch records from the target pipeline
            const relationResponse = await pipelinesApi.getRecords(targetPipelineId, { 
              limit: 200 // Get a reasonable number of options
            })
            
            if (relationResponse.data.results) {
              const configuredDisplayField = field.field_config.display_field
              const sampleRecordDataKeys = Object.keys(relationResponse.data.results[0]?.data || {})
              
              // The display_field should ideally be a field slug, but handle display names as fallback
              let displayFieldSlug = configuredDisplayField
              
              // If the configured field doesn't exist in record data, try normalized version
              if (!sampleRecordDataKeys.includes(displayFieldSlug)) {
                const normalizedSlug = configuredDisplayField.toLowerCase().replace(/\s+/g, '_')
                if (sampleRecordDataKeys.includes(normalizedSlug)) {
                  displayFieldSlug = normalizedSlug
                }
              }
              
              const relationOptions = relationResponse.data.results.map((record: any) => {
                let label = null
                
                // 1. Use the specified display field slug from the target pipeline records
                if (displayFieldSlug && record.data?.[displayFieldSlug]) {
                  label = record.data[displayFieldSlug]
                  console.log(`🔗 Record ${record.id}: Using display field slug "${displayFieldSlug}" = "${label}"`)
                }
                // 2. If configured display field is empty/missing, try common fallbacks
                else if (displayFieldSlug) {
                  console.log(`🔗 Record ${record.id}: Display field slug "${displayFieldSlug}" not found or empty, trying fallbacks`)
                  label = record.data?.name || 
                         record.data?.title || 
                         record.data?.company_name ||
                         record.data?.first_name || 
                         record.data?.email ||
                         record.title
                }
                // 3. No display field configured, use best guess
                else {
                  console.log(`🔗 Record ${record.id}: No display field configured, using best guess`)
                  label = record.data?.name || 
                         record.data?.title || 
                         record.data?.company_name ||
                         record.data?.first_name || 
                         record.data?.email ||
                         record.title
                }
                
                // 4. If still no label, use first non-empty field
                if (!label && record.data) {
                  const dataValues = Object.values(record.data).filter(v => v && String(v).trim())
                  if (dataValues.length > 0) {
                    label = String(dataValues[0])
                    console.log(`🔗 Record ${record.id}: Using first available field as label: "${label}"`)
                  }
                }
                
                // 5. Final fallback
                if (!label) {
                  label = `Record ${record.id}`
                  console.log(`🔗 Record ${record.id}: Using fallback label`)
                }
                
                return {
                  value: record.id.toString(),
                  label: String(label).trim()
                }
              }).filter(option => option.label && option.label !== 'Record undefined')
              
              console.log(`🔗 Found ${relationOptions.length} relation options:`, relationOptions)
              return relationOptions
            }
          } catch (error) {
            console.error(`Failed to fetch relation options for ${fieldName}:`, error)
          }
          
          return []
          
        default:
          return []
      }
    } catch (error) {
      console.error(`Failed to fetch options for ${fieldName} (${fieldType}):`, error)
      return []
    }
  }

  // Get field options based on field type (synchronous, uses cache)
  const getFieldOptions = (fieldName: string) => {
    const field = pipeline.fields.find(f => f.name === fieldName)
    if (!field) return []

    switch (field.field_type) {
      case 'select':
      case 'multiselect':
        return field.field_config?.options || []
      case 'boolean':
        return [
          { value: 'true', label: 'Yes' },
          { value: 'false', label: 'No' }
        ]
      case 'user':
      case 'tags':
      case 'relation':
      case 'relationship':
      case 'related':
        // Return cached options or empty array if not yet fetched
        return fieldOptionsCache[fieldName] || []
      default:
        return []
    }
  }

  // Check if field has predefined options
  const fieldHasOptions = (fieldName: string) => {
    const field = pipeline.fields.find(f => f.name === fieldName)
    if (!field) return false
    
    return ['select', 'multiselect', 'boolean', 'user', 'tags', 'relation', 'relationship', 'related'].includes(field.field_type)
  }

  // Fetch field options when a field is selected
  useEffect(() => {
    if (newFilterField) {
      const field = pipeline.fields.find(f => f.name === newFilterField)
      
      if (field && ['user', 'tags', 'relation', 'relationship', 'related'].includes(field.field_type) && !fieldOptionsCache[newFilterField]) {
        fetchFieldOptions(newFilterField, field.field_type).then(options => {
          setFieldOptionsCache(prev => ({
            ...prev,
            [newFilterField]: options
          }))
        })
      }
    }
  }, [newFilterField, pipeline.fields, fieldOptionsCache])

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
        
        // Add search query (debounced)
        if (debouncedSearchQuery.trim()) {
          params.search = debouncedSearchQuery.trim()
        }
        
        // Add applied filters using DRF-compatible parameter names
        appliedFilters.forEach((filter) => {
          const fieldName = filter.field
          const fieldType = pipeline.fields.find(f => f.name === fieldName)?.field_type
          
          // Handle different field types with appropriate query parameters
          if (fieldType === 'tags') {
            // Tags are stored as arrays, use JSONB array operators
            const paramName = `data__${fieldName}`
            switch (filter.operator) {
              case 'equals':
                // For tags, 'equals' means array contains this exact tag
                params[`${paramName}__contains`] = filter.value
                break
              case 'contains':
                // Search for tags containing this string (partial match)
                params[`${paramName}__icontains`] = filter.value
                break
              case 'is_empty':
                // Empty array or null
                params[`${paramName}__isnull`] = true
                break
              case 'is_not_empty':
                // Non-empty array
                params[`${paramName}__isnull`] = false
                break
            }
          } else if (fieldType === 'user') {
            // User assignments - search within array of user objects
            const paramName = `data__${fieldName}`
            
            switch (filter.operator) {
              case 'contains':
              case 'equals':
                // Use the custom user_id filter for JSONB array searching
                params[`${paramName}__user_id`] = parseInt(filter.value)
                break
              case 'is_empty':
                params[`${paramName}__isnull`] = true
                break
              case 'is_not_empty':
                params[`${paramName}__isnull`] = false
                break
            }
          } else if (fieldType === 'relation' || fieldType === 'relationship') {
            // Relations can be stored as single IDs or arrays of IDs
            const field = pipeline.fields.find(f => f.name === fieldName)
            const allowMultiple = field?.field_config?.allow_multiple
            const paramName = `data__${fieldName}`
            
            switch (filter.operator) {
              case 'contains':
              case 'equals':
                if (allowMultiple) {
                  // For multiple relations (arrays), use contains to check if array includes this ID
                  params[`${paramName}__contains`] = parseInt(filter.value)
                } else {
                  // For single relations, direct equality
                  params[paramName] = parseInt(filter.value)
                }
                break
              case 'is_empty':
                params[`${paramName}__isnull`] = true
                break
              case 'is_not_empty':
                params[`${paramName}__isnull`] = false
                break
            }
          } else {
            // Default handling for other field types (text, number, etc.)
            const paramName = `data__${fieldName}`
            
            switch (filter.operator) {
              case 'equals':
                params[paramName] = filter.value
                break
              case 'contains':
                params[`${paramName}__icontains`] = filter.value
                break
              case 'starts_with':
                params[`${paramName}__istartswith`] = filter.value
                break
              case 'ends_with':
                params[`${paramName}__iendswith`] = filter.value
                break
              case 'greater_than':
                params[`${paramName}__gt`] = filter.value
                break
              case 'less_than':
                params[`${paramName}__lt`] = filter.value
                break
              case 'is_empty':
                params[`${paramName}__isnull`] = true
                break
              case 'is_not_empty':
                params[`${paramName}__isnull`] = false
                break
            }
          }
        })
        
        // Add sorting
        if (sort.field && sort.direction) {
          params.ordering = sort.direction === 'desc' ? `-${sort.field}` : sort.field
        }
        
        const response = await pipelinesApi.getRecords(pipeline.id, params)
        const records = response.data.results || response.data
        
        setRecords(records)
      } catch (error: any) {
        console.error('Failed to load records:', error)
        setError(error.response?.data?.message || error.message || 'Failed to load records')
        setRecords([])
      } finally {
        setLoading(false)
      }
    }

    loadRecords()
  }, [pipeline.id, appliedFilters, sort, debouncedSearchQuery, currentPage, recordsPerPage])

  // Filter and sort records
  const filteredAndSortedRecords = useMemo(() => {
    let filtered = records

    // Apply search (client-side search is still needed since API doesn't handle general search)
    if (searchQuery) {
      filtered = filtered.filter(record => 
        Object.values(record.data).some(value =>
          String(value).toLowerCase().includes(searchQuery.toLowerCase())
        )
      )
    }

    // Skip client-side filtering - the API already filters the results server-side
    // This prevents double filtering issues, especially for complex field types like user, tags, relationships

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
  }, [records, searchQuery, sort])

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
              Filters {appliedFilters.length > 0 && `(${appliedFilters.length})`}
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
              onClick={() => {
                setAppliedFilters([])
                setBooleanQuery({
                  groups: [{
                    id: 'group-1',
                    logic: 'AND',
                    filters: []
                  }],
                  groupLogic: 'AND'
                })
                setSelectedGroupId('group-1')
                setCurrentPage(1)
              }}
              className="text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
            >
              Clear all
            </button>
          </div>
          
          {/* Filter Builder */}
          <div className="space-y-4">


            {/* Boolean Query Groups */}
            {booleanQuery.groups.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wide">Filter Groups</h4>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500">Groups connected by:</span>
                    <select
                      value={booleanQuery.groupLogic}
                      onChange={(e) => setBooleanQuery(prev => ({
                        ...prev,
                        groupLogic: e.target.value as 'AND' | 'OR'
                      }))}
                      className="text-xs px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800"
                    >
                      <option value="AND">AND</option>
                      <option value="OR">OR</option>
                    </select>
                    <button
                      onClick={() => {
                        setBooleanQuery(prev => ({
                          ...prev,
                          groups: [...prev.groups, {
                            id: `group-${Date.now()}`,
                            logic: 'AND',
                            filters: []
                          }]
                        }))
                      }}
                      className="text-xs px-2 py-1 bg-purple-100 text-purple-700 rounded hover:bg-purple-200"
                    >
                      Add Group
                    </button>
                  </div>
                </div>
                
                {booleanQuery.groups.map((group, groupIndex) => (
                  <div key={group.id} className="p-3 border border-purple-200 dark:border-purple-700 rounded-lg bg-purple-50 dark:bg-purple-900/10">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-purple-700 dark:text-purple-300">Group {groupIndex + 1}</span>
                        <select
                          value={group.logic}
                          onChange={(e) => {
                            setBooleanQuery(prev => ({
                              ...prev,
                              groups: prev.groups.map(g => 
                                g.id === group.id ? { ...g, logic: e.target.value as 'AND' | 'OR' } : g
                              )
                            }))
                          }}
                          className="text-xs px-2 py-1 border border-purple-300 dark:border-purple-600 rounded bg-white dark:bg-gray-800"
                        >
                          <option value="AND">AND</option>
                          <option value="OR">OR</option>
                        </select>
                      </div>
                      {booleanQuery.groups.length > 1 && (
                        <button
                          onClick={() => {
                            setBooleanQuery(prev => ({
                              ...prev,
                              groups: prev.groups.filter(g => g.id !== group.id)
                            }))
                          }}
                          className="text-red-500 hover:text-red-700"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                    
                    {/* Show filters in this group */}
                    {group.filters.length > 0 && (
                      <div className="flex flex-wrap gap-2 text-sm">
                        {group.filters.map((filter, filterIndex) => {
                          const field = pipeline.fields.find(f => f.name === filter.field)
                          const fieldDisplayName = field?.display_name || filter.field
                          
                          // Get display value for select fields
                          let displayValue = filter.value
                          if (fieldHasOptions(filter.field)) {
                            const options = getFieldOptions(filter.field)
                            const option = options.find((opt: any) => (opt.value || opt) === filter.value)
                            if (option) {
                              displayValue = option.label || option.value || option
                            }
                          }
                          
                          return (
                            <div key={filterIndex} className="inline-flex items-center gap-1 px-2 py-1 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300 rounded-md text-sm border border-yellow-200 dark:border-yellow-700">
                              <span className="font-medium">{fieldDisplayName}</span>
                              <span className="text-yellow-600 dark:text-yellow-400">{filter.operator.replace('_', ' ')}</span>
                              {!['is_empty', 'is_not_empty'].includes(filter.operator) && (
                                <span className="font-medium">"{displayValue}"</span>
                              )}
                              <button
                                onClick={() => {
                                  // Remove from boolean query group
                                  const updatedBooleanQuery = {
                                    ...booleanQuery,
                                    groups: booleanQuery.groups.map(g => 
                                      g.id === group.id 
                                        ? { ...g, filters: g.filters.filter((_, i) => i !== filterIndex) }
                                        : g
                                    )
                                  }
                                  
                                  setBooleanQuery(updatedBooleanQuery)
                                  
                                  // Immediately update applied filters
                                  const allFilters: Filter[] = []
                                  updatedBooleanQuery.groups.forEach(group => {
                                    allFilters.push(...group.filters)
                                  })
                                  
                                  setAppliedFilters(allFilters)
                                  setCurrentPage(1) // Reset to first page when removing filters
                                }}
                                className="ml-1 text-yellow-600 hover:text-yellow-800 dark:text-yellow-400 dark:hover:text-yellow-200"
                              >
                                <X className="w-3 h-3" />
                              </button>
                            </div>
                          )
                        })}
                      </div>
                    )}
                    
                    {group.filters.length === 0 && (
                      <div className="text-xs text-gray-500 italic">No filters in this group yet</div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Add New Filter */}
            <div className="space-y-3">
              <h4 className="text-xs font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wide">Add Filter</h4>
              
              {/* Filter Builder Row */}
              <div className="flex items-center gap-2 p-3 bg-white dark:bg-gray-700 rounded-lg border border-gray-200 dark:border-gray-600">
                {/* Field Selection */}
                <div className="min-w-0 flex-1">
                  <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Field</label>
                  <select
                    value={newFilterField}
                    onChange={(e) => {
                      const fieldName = e.target.value
                      const fieldType = pipeline.fields.find(f => f.name === fieldName)?.field_type
                      
                      setNewFilterField(fieldName)
                      setNewFilterValue('') // Reset value when field changes
                      
                      // Reset operator to appropriate default for field type
                      if (fieldType === 'user' || fieldType === 'tags' || fieldType === 'relation' || fieldType === 'relationship') {
                        setNewFilterOperator('contains') // Default to contains for these field types
                      } else if (fieldType === 'number') {
                        setNewFilterOperator('equals') // Default to equals for numbers
                      } else {
                        setNewFilterOperator('equals') // Default to equals for other types
                      }
                    }}
                    className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                  >
                    <option value="">Select field...</option>
                    {pipeline.fields
                      .filter(field => ['text', 'textarea', 'email', 'number', 'decimal', 'select', 'multiselect', 'boolean', 'date', 'datetime', 'user', 'tags', 'relation'].includes(field.field_type))
                      .map(field => (
                      <option key={field.id} value={field.name}>
                        {field.display_name || field.name}
                      </option>
                    ))}
                  </select>
                </div>
                
                {/* Operator Selection */}
                <div className="min-w-0 flex-1">
                  <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Condition</label>
                  <select
                    value={newFilterOperator}
                    onChange={(e) => setNewFilterOperator(e.target.value as FilterOperator)}
                    className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                  >
                    {(() => {
                      const fieldType = pipeline.fields.find(f => f.name === newFilterField)?.field_type
                      
                      // For user, tag, and relationship fields, only show contains and empty/not empty
                      if (fieldType === 'user' || fieldType === 'tags' || fieldType === 'relation' || fieldType === 'relationship') {
                        return (
                          <>
                            <option value="contains">Contains</option>
                            <option value="is_empty">Is empty</option>
                            <option value="is_not_empty">Is not empty</option>
                          </>
                        )
                      }
                      
                      // For number fields, show numeric operators
                      if (fieldType === 'number') {
                        return (
                          <>
                            <option value="equals">Equals</option>
                            <option value="greater_than">Greater than</option>
                            <option value="less_than">Less than</option>
                            <option value="is_empty">Is empty</option>
                            <option value="is_not_empty">Is not empty</option>
                          </>
                        )
                      }
                      
                      // For text fields, show text operators
                      if (fieldType === 'text' || fieldType === 'textarea' || fieldType === 'email') {
                        return (
                          <>
                            <option value="equals">Equals</option>
                            <option value="contains">Contains</option>
                            <option value="starts_with">Starts with</option>
                            <option value="ends_with">Ends with</option>
                            <option value="is_empty">Is empty</option>
                            <option value="is_not_empty">Is not empty</option>
                          </>
                        )
                      }
                      
                      // Default: show all operators
                      return (
                        <>
                          <option value="equals">Equals</option>
                          <option value="contains">Contains</option>
                          <option value="starts_with">Starts with</option>
                          <option value="ends_with">Ends with</option>
                          <option value="greater_than">Greater than</option>
                          <option value="less_than">Less than</option>
                          <option value="is_empty">Is empty</option>
                          <option value="is_not_empty">Is not empty</option>
                        </>
                      )
                    })()}
                  </select>
                </div>
                
                {/* Value Input */}
                {!['is_empty', 'is_not_empty'].includes(newFilterOperator) && (
                  <div className="min-w-0 flex-1">
                    <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Value</label>
                    {fieldHasOptions(newFilterField) ? (
                      <select
                        value={newFilterValue}
                        onChange={(e) => setNewFilterValue(e.target.value)}
                        className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                      >
                        <option value="">Select option...</option>
                        {getFieldOptions(newFilterField).map((option: any, index: number) => (
                          <option key={index} value={option.value || option}>
                            {option.label || option}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type="text"
                        value={newFilterValue}
                        onChange={(e) => setNewFilterValue(e.target.value)}
                        placeholder="Enter value..."
                        className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                      />
                    )}
                  </div>
                )}
                
                {/* Group Selection */}
                {booleanQuery.groups.length > 1 && (
                  <div className="min-w-0 flex-1">
                    <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Add to Group</label>
                    <select
                      value={selectedGroupId}
                      onChange={(e) => setSelectedGroupId(e.target.value)}
                      className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                    >
                      {booleanQuery.groups.map((group, index) => (
                        <option key={group.id} value={group.id}>
                          Group {index + 1} ({group.logic})
                        </option>
                      ))}
                    </select>
                  </div>
                )}
                
                {/* Add Filter Button */}
                <div className="flex-shrink-0">
                  <label className="block text-xs text-transparent mb-1">Add</label>
                  <button
                    onClick={() => {
                      if (newFilterField && (newFilterValue || ['is_empty', 'is_not_empty'].includes(newFilterOperator))) {
                        const newFilter = { 
                          field: newFilterField, 
                          operator: newFilterOperator, 
                          value: newFilterValue 
                        }
                        
                        // Add to the selected boolean query group
                        setBooleanQuery(prev => ({
                          ...prev,
                          groups: prev.groups.map(group => 
                            group.id === selectedGroupId 
                              ? { ...group, filters: [...group.filters, newFilter] }
                              : group
                          )
                        }))
                        
                        // Immediately apply the filter by updating applied filters
                        const updatedBooleanQuery = {
                          ...booleanQuery,
                          groups: booleanQuery.groups.map(group => 
                            group.id === selectedGroupId 
                              ? { ...group, filters: [...group.filters, newFilter] }
                              : group
                          )
                        }
                        
                        const allFilters: Filter[] = []
                        updatedBooleanQuery.groups.forEach(group => {
                          allFilters.push(...group.filters)
                        })
                        
                        setAppliedFilters(allFilters)
                        setCurrentPage(1) // Reset to first page when applying filters
                        
                        // Reset form
                        setNewFilterField('')
                        setNewFilterOperator('equals')
                        setNewFilterValue('')
                      }
                    }}
                    className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 flex items-center gap-1"
                  >
                    <Plus className="w-3 h-3" />
                    Add
                  </button>
                </div>
              </div>

            </div>
          </div>
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
              {searchQuery || appliedFilters.length > 0
                ? 'Try adjusting your search or filters.'
                : 'Get started by adding your first record.'}
            </p>
            {!searchQuery && appliedFilters.length === 0 && (
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