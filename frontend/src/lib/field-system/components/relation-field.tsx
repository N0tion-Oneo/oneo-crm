import React, { useState, useEffect, useRef } from 'react'
import { FieldComponent, FieldRenderProps, ValidationResult, Field } from '../types'
import { getFieldConfig } from '../field-registry'
import { pipelinesApi, relationshipsApi } from '../../api'
import { X, Plus, Link, Settings } from 'lucide-react'

// Global cache for relation lookups to avoid repeated API calls
const relationCache = new Map<string, string>()
const pendingRequests = new Map<string, Promise<string>>()

// Function to lookup relation display value with request deduplication
const lookupRelationValue = async (
  value: any, 
  targetPipelineId: number, 
  displayField: string
): Promise<string> => {
  const cacheKey = `${targetPipelineId}-${value}-${displayField}`
  
  // Check cache first
  if (relationCache.has(cacheKey)) {
    console.log(`🟢 CACHE HIT: Record ${value} from cache`)
    return relationCache.get(cacheKey)!
  }
  
  // Check if request is already pending to avoid duplicate API calls
  if (pendingRequests.has(cacheKey)) {
    console.log(`🟡 REQUEST PENDING: Waiting for existing request for record ${value}`)
    return pendingRequests.get(cacheKey)!
  }
  
  console.log(`🔴 CACHE MISS: Fetching record ${value} from API`)
  
  // Create the promise and store it to prevent duplicate requests
  const requestPromise = (async () => {
    try {
      const response = await pipelinesApi.getRecord(targetPipelineId.toString(), value.toString())
    
      if (response.data) {
        const recordDisplayValue = getDisplayValue(response.data, displayField)
        
        // Cache the result
        relationCache.set(cacheKey, recordDisplayValue)
        console.log(`✅ CACHED: Record ${value} cached as "${recordDisplayValue}"`)
        return recordDisplayValue
      }
    } catch (error) {
      console.error(`❌ Failed to load relation record ${value}:`, error)
    }
    
    // Fallback to Record #ID
    const fallback = `Record #${value}`
    relationCache.set(cacheKey, fallback)
    console.log(`⚠️ FALLBACK: Record ${value} cached as fallback "${fallback}"`)
    return fallback
  })()
  
  // Store the promise to prevent duplicate requests
  pendingRequests.set(cacheKey, requestPromise)
  
  try {
    const result = await requestPromise
    return result
  } finally {
    // Clean up the pending request
    pendingRequests.delete(cacheKey)
  }
}

// Component for displaying relation values with proper record lookup
const RelationDisplayValue: React.FC<{
  value: any
  field: Field
  context?: string
}> = ({ value, field, context }) => {
  const [displayText, setDisplayText] = useState<string>(`Record #${value}`)
  const [loading, setLoading] = useState(true)
  
  const targetPipelineId = getFieldConfig(field, 'target_pipeline_id')
  const displayField = getFieldConfig(field, 'display_field', 'title')
  
  useEffect(() => {
    const fetchData = async () => {
      if (!targetPipelineId || !value) {
        setLoading(false)
        return
      }
      
      const result = await lookupRelationValue(value, targetPipelineId, displayField)
      setDisplayText(result)
      setLoading(false)
    }
    
    fetchData()
  }, [value, targetPipelineId, displayField])
  
  if (loading) {
    return <span className="text-gray-500">Loading...</span>
  }
  
  // For table and detail contexts, show a link-like appearance
  if (context === 'table' || context === 'detail') {
    return (
      <span className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 cursor-pointer">
        {displayText}
        {targetPipelineId && (
          <span className="text-xs text-gray-500 dark:text-gray-400 ml-1">
            (Pipeline {targetPipelineId})
          </span>
        )}
      </span>
    )
  }
  
  // For other contexts, return simple text
  return <>{displayText}</>
}

interface RecordOption {
  id: number
  title: string
  [key: string]: any
}

interface RelationshipType {
  id: number
  name: string
  slug: string
  description: string
  cardinality: 'one_to_one' | 'one_to_many' | 'many_to_many' | 'many_to_one' | 'one_to_one_bidirectional' | 'one_to_many_bidirectional' | 'many_to_many_bidirectional'
  is_bidirectional: boolean
  forward_label: string
  reverse_label: string
}

interface EnhancedRelationship {
  record_id: number | string
  relationship_type?: string
  metadata?: Record<string, any>
}

// Enhanced value type for multiple relationships
type RelationshipValue = number | string | EnhancedRelationship | (number | string | EnhancedRelationship)[] | null

// Helper function to get display value from record
function getDisplayValue(record: any, displayField: string): string {
  if (!record) return 'Unknown Record'
  
  // Try to get the configured display field from record.data
  if (displayField && record.data && record.data[displayField] !== undefined) {
    const value = record.data[displayField]
    
    // Handle different value types properly
    if (value === null || value === undefined || value === '') {
      return `Record #${record.id}` // Fallback if field is empty
    }
    return String(value)
  }
  
  // Try to find the field by searching for similar names (in case of slug vs display name mismatch)
  if (displayField && record.data) {
    const dataKeys = Object.keys(record.data)
    
    // Look for exact match (case insensitive)
    const exactMatch = dataKeys.find(key => key.toLowerCase() === displayField.toLowerCase())
    if (exactMatch && record.data[exactMatch] !== undefined && record.data[exactMatch] !== null && record.data[exactMatch] !== '') {
      return String(record.data[exactMatch])
    }
    
    // Look for slug-like match (convert display name to slug)
    const slugified = displayField.toLowerCase().replace(/[^a-z0-9]/g, '_').replace(/_+/g, '_')
    const slugMatch = dataKeys.find(key => key === slugified)
    if (slugMatch && record.data[slugMatch] !== undefined && record.data[slugMatch] !== null && record.data[slugMatch] !== '') {
      return String(record.data[slugMatch])
    }
  }
  
  // Fallback to record.title if it exists
  if (record.title) {
    return String(record.title)
  }
  
  // Fallback to record ID
  return `Record #${record.id}`
}

// Enhanced Multi-Relationship Component
const EnhancedRelationshipInput: React.FC<FieldRenderProps> = (props) => {
  const { field, value, onChange, onBlur, onKeyDown, disabled, error, className, autoFocus, pipeline_id } = props
  
  // Get enhanced field configuration
  const targetPipelineId = getFieldConfig(field, 'target_pipeline_id')
  const displayField = getFieldConfig(field, 'display_field', 'title')
  const allowMultiple = getFieldConfig(field, 'allow_multiple', false)
  const allowRelationshipTypeSelection = getFieldConfig(field, 'allow_relationship_type_selection', false)
  const allowSelfReference = getFieldConfig(field, 'allow_self_reference', false)
  const maxRelationships = getFieldConfig(field, 'max_relationships', null)
  const defaultRelationshipType = getFieldConfig(field, 'default_relationship_type', 'related_to')
  
  // State management
  const [records, setRecords] = useState<RecordOption[]>([])
  const [relationshipTypes, setRelationshipTypes] = useState<RelationshipType[]>([])
  const [loading, setLoading] = useState(false)
  const [loadingTypes, setLoadingTypes] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [showDropdown, setShowDropdown] = useState(false)
  const [filteredRecords, setFilteredRecords] = useState<RecordOption[]>([])
  const dropdownRef = useRef<HTMLDivElement>(null)
  
  // Normalize value to always work with arrays for consistency
  // Handle both backend format (simple IDs) and UI format (enhanced objects)
  const normalizedValue = React.useMemo(() => {
    if (!value) return []
    
    if (Array.isArray(value)) {
      return value.map(v => {
        if (typeof v === 'object' && v.record_id) {
          // Already in enhanced format
          return v as EnhancedRelationship
        } else {
          // Backend format: simple ID, convert to enhanced format for UI
          return { 
            record_id: typeof v === 'number' ? v.toString() : v, 
            relationship_type: defaultRelationshipType 
          } as EnhancedRelationship
        }
      })
    }
    
    if (typeof value === 'object' && value.record_id) {
      // Already in enhanced format
      return [value as EnhancedRelationship]
    }
    
    // Backend format: simple ID, convert to enhanced format for UI
    return [{ 
      record_id: typeof value === 'number' ? value.toString() : value, 
      relationship_type: defaultRelationshipType 
    } as EnhancedRelationship]
  }, [value, defaultRelationshipType])
  
  // Load target pipeline records
  useEffect(() => {
    if (!targetPipelineId) return
    
    const loadRecords = async () => {
      setLoading(true)
      setLoadError(null)
      
      try {
        // If self-reference is enabled, use the current pipeline
        const pipelineToLoad = allowSelfReference && pipeline_id ? pipeline_id : targetPipelineId
        const response = await pipelinesApi.getRecords(pipelineToLoad.toString())
        
        const recordsData = response.data?.results || response.data || []
        setRecords(recordsData)
      } catch (err) {
        console.error('❌ Error loading records:', err)
        setLoadError('Failed to load records')
        setRecords([])
      } finally {
        setLoading(false)
      }
    }
    
    loadRecords()
  }, [targetPipelineId, allowSelfReference, pipeline_id])
  
  // Load relationship types if needed
  useEffect(() => {
    if (!allowRelationshipTypeSelection) return
    
    const loadRelationshipTypes = async () => {
      setLoadingTypes(true)
      
      try {
        const response = await relationshipsApi.getRelationshipTypes()
        console.log('🔗 Relationship types API response:', response)
        
        // Handle different response structures
        let types = []
        if (Array.isArray(response.data)) {
          types = response.data
        } else if (response.data?.results && Array.isArray(response.data.results)) {
          types = response.data.results
        } else if (response.data?.relationship_types && Array.isArray(response.data.relationship_types)) {
          types = response.data.relationship_types
        } else {
          console.warn('🔗 Unexpected API response structure:', response.data)
          types = []
        }
        
        console.log('🔗 Setting relationship types:', types)
        setRelationshipTypes(types)
      } catch (error) {
        console.error('❌ Failed to load relationship types:', error)
        setRelationshipTypes([])
      } finally {
        setLoadingTypes(false)
      }
    }
    
    loadRelationshipTypes()
  }, [allowRelationshipTypeSelection])

  // Filter records based on search term
  useEffect(() => {
    if (!searchTerm.trim()) {
      setFilteredRecords(records)
      return
    }
    
    const filtered = records.filter(record => {
      const searchLower = searchTerm.toLowerCase()
      const displayName = getDisplayValue(record, displayField).toLowerCase()
      const recordId = record.id.toString().toLowerCase()
      
      return displayName.includes(searchLower) || recordId.includes(searchLower)
    })
    
    setFilteredRecords(filtered)
  }, [searchTerm, records, displayField])

  // Click outside to close dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        // Use setTimeout to prevent immediate state changes that could cause render issues
        setTimeout(() => {
          setShowDropdown(false)
          setSearchTerm('') // Clear search when closing
        }, 0)
      }
    }
    
    if (showDropdown) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => {
        document.removeEventListener('mousedown', handleClickOutside)
      }
    }
  }, [showDropdown])
  
  // Handle adding a new relationship
  const addRelationship = (recordId: string, relationshipType?: string) => {
    if (!recordId) return
    
    const recordIdInt = parseInt(recordId)
    
    if (allowMultiple) {
      // Check max relationships limit
      if (maxRelationships && normalizedValue.length >= maxRelationships) {
        return // Don't add if exceeds limit
      }
      
      // For multiple relationships, maintain array of IDs
      const currentIds = normalizedValue.map(rel => parseInt(rel.record_id.toString()))
      if (!currentIds.includes(recordIdInt)) {
        const updatedIds = [...currentIds, recordIdInt]
        onChange(updatedIds)
      }
    } else {
      // For single relationship, send just the ID
      onChange(recordIdInt)
    }
    setSearchTerm('')
    setShowDropdown(false)
  }
  
  // Handle removing a relationship
  const removeRelationship = (index: number) => {
    if (allowMultiple) {
      const currentIds = normalizedValue.map(rel => parseInt(rel.record_id.toString()))
      const updatedIds = currentIds.filter((_, i) => i !== index)
      if (updatedIds.length > 0) {
        onChange(updatedIds)
      } else {
        onChange(null)
      }
    } else {
      onChange(null)
    }
  }
  
  // Handle updating relationship type
  const updateRelationshipType = (index: number, newType: string) => {
    // Note: Since we're sending simple IDs to backend, relationship type changes 
    // are stored locally for UI display but don't affect the saved value
    // This would need to be integrated with a proper relationship management system
    console.warn('Relationship type updates not fully implemented - backend expects simple IDs')
    
    // For now, just update the local state for UI purposes
    if (allowMultiple) {
      const updatedValue = [...normalizedValue]
      updatedValue[index] = { ...updatedValue[index], relationship_type: newType }
      // Still send simple IDs to backend
      const backendValue = updatedValue.map(rel => 
        typeof rel.record_id === 'string' ? parseInt(rel.record_id) : rel.record_id
      )
      onChange(backendValue)
    } else if (normalizedValue[0]) {
      // For single relationships, send just the record ID
      const recordIdInt = typeof normalizedValue[0].record_id === 'string' 
        ? parseInt(normalizedValue[0].record_id) 
        : normalizedValue[0].record_id
      onChange(recordIdInt)
    }
  }
  
  // Calculate inline to avoid potential initialization issues
  const canAddMore = !maxRelationships || normalizedValue.length < maxRelationships
  
  return (
    <div className={className}>
      {/* Current relationships */}
      <div className="space-y-2 mb-3">
        {normalizedValue.map((relationship, index) => {
          const record = records.find(r => r.id.toString() === relationship.record_id.toString())
          const recordDisplay = record ? getDisplayValue(record, displayField) : `Record #${relationship.record_id}`
          const hasRequiredType = !allowRelationshipTypeSelection || (relationship.relationship_type && relationship.relationship_type.trim() !== '')
          
          return (
            <div key={`${relationship.record_id}-${index}`} className={`flex items-center gap-2 p-2 rounded-lg ${
              hasRequiredType 
                ? 'bg-blue-50 dark:bg-blue-900/20' 
                : 'bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800'
            }`}>
              <Link className="w-4 h-4 text-gray-500" />
              
              <div className="flex-1">
                <div className="font-medium text-sm text-gray-900 dark:text-gray-100">
                  {recordDisplay}
                </div>
                {allowRelationshipTypeSelection && relationship.relationship_type ? (
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    {relationship.relationship_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </div>
                ) : (
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    Record #{relationship.record_id} • {displayField}
                  </div>
                )}
                {allowRelationshipTypeSelection && !hasRequiredType && (
                  <div className="text-xs text-amber-600 dark:text-amber-400 font-medium">
                    Relationship type selection required
                  </div>
                )}
              </div>
              
              {allowRelationshipTypeSelection && !disabled && (
                <select
                  value={relationship.relationship_type || ''}
                  onChange={(e) => updateRelationshipType(index, e.target.value)}
                  disabled={disabled || loadingTypes}
                  className={`text-xs border rounded px-2 py-1 transition-colors focus:outline-none focus:ring-1 focus:ring-offset-0 ${
                    !hasRequiredType
                      ? 'border-amber-300 dark:border-amber-600 bg-amber-50 dark:bg-amber-900/20 focus:border-amber-500 focus:ring-amber-500'
                      : 'border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:border-blue-500 focus:ring-blue-500'
                  }`}
                >
                  <option value="">Select type...</option>
                  {Array.isArray(relationshipTypes) ? relationshipTypes.map(type => (
                    <option key={type.slug} value={type.slug}>
                      {type.name} {type.is_bidirectional ? '↔' : '→'}
                    </option>
                  )) : (
                    <option value={defaultRelationshipType}>
                      {defaultRelationshipType.replace('_', ' ')} (default)
                    </option>
                  )}
                </select>
              )}
              
              {!disabled && (
                <button
                  onClick={() => removeRelationship(index)}
                  className="text-red-500 hover:text-red-700 text-sm font-bold"
                  type="button"
                  title="Remove relationship"
                >
                  ×
                </button>
              )}
            </div>
          )
        })}
        {normalizedValue.length === 0 && (
          <div className="text-gray-500 dark:text-gray-400 text-sm italic">
            No relationships selected
          </div>
        )}
      </div>
      
      {/* Add relationship interface */}
      {!disabled && (allowMultiple || normalizedValue.length === 0) && (
        <div className={`space-y-2 ${(!canAddMore || (maxRelationships && normalizedValue.length >= maxRelationships)) ? 'sr-only' : ''}`}>
          {maxRelationships && normalizedValue.length > 0 && (
            <div className="text-xs text-gray-500 dark:text-gray-400 mb-2">
              {normalizedValue.length} of {maxRelationships} relationships selected
            </div>
          )}
          <div className="relative" ref={dropdownRef}>
            <button
              type="button"
              onClick={() => setShowDropdown(!showDropdown)}
              disabled={disabled}
              className={`w-full px-3 py-2 border rounded-lg transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-0 text-left flex items-center justify-between ${
                error 
                  ? 'border-red-300 dark:border-red-600 focus:border-red-500 focus:ring-red-500 dark:focus:ring-red-400' 
                  : 'border-gray-300 dark:border-gray-600 focus:border-blue-500 focus:ring-blue-500 dark:focus:ring-blue-400'
              } ${disabled 
                  ? 'bg-gray-50 dark:bg-gray-700 cursor-not-allowed text-gray-500 dark:text-gray-400' 
                  : 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white hover:bg-gray-50 dark:hover:bg-gray-600'
              } ${className || ''}`}
            >
              <span className="text-gray-500 dark:text-gray-400">
                {loading ? 'Loading records...' : `Select ${field.display_name || field.name}... (${records.length} available)`}
              </span>
              <svg className={`w-4 h-4 transition-transform ${showDropdown ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            
            {/* Record dropdown */}
            {showDropdown && (
              <div className="absolute z-50 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg max-h-64 overflow-hidden">
                {/* Search input inside dropdown */}
                <div className="p-2 border-b border-gray-200 dark:border-gray-700">
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Type to filter records..."
                    className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    autoFocus
                    onKeyDown={(e) => {
                      if (e.key === 'Escape') {
                        setShowDropdown(false)
                        setSearchTerm('')
                      }
                    }}
                  />
                </div>
                
                {/* Record list */}
                <div className="max-h-48 overflow-y-auto">
                  {loading && (
                    <div className="p-3 text-center text-gray-500">Loading...</div>
                  )}
                  {!loading && filteredRecords.length === 0 && (
                    <div className="p-3 text-center text-gray-500">
                      {searchTerm ? `No records found matching "${searchTerm}"` : 'No records available'}
                      <div className="text-xs mt-1">
                        Available: {records.length}, Filtered: {filteredRecords.length}
                      </div>
                    </div>
                  )}
                  {!loading && filteredRecords.map((record) => {
                    // Don't show already selected records
                    const isAlreadySelected = normalizedValue.some(rel => rel.record_id.toString() === record.id.toString())
                    if (isAlreadySelected) return null
                    
                    return (
                      <div
                        key={record.id}
                        onClick={(e) => {
                          e.preventDefault()
                          e.stopPropagation()
                          addRelationship(record.id.toString(), allowRelationshipTypeSelection ? undefined : defaultRelationshipType)
                        }}
                        className="w-full text-left px-3 py-2 hover:bg-blue-50 dark:hover:bg-blue-900/20 flex items-center gap-2 transition-colors cursor-pointer"
                      >
                        <Link className="w-4 h-4 text-gray-500" />
                        <div className="flex-1">
                          <div className="font-medium text-sm text-gray-900 dark:text-gray-100">
                            {getDisplayValue(record, displayField)}
                          </div>
                          <div className="text-xs text-gray-500 dark:text-gray-400">
                            Record #{record.id}
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
      
      {/* Status Information */}
      <div className="text-xs text-gray-500 dark:text-gray-400 space-y-1">
        {loading && <div>Loading records...</div>}
        {loadError && <div className="text-red-500">{loadError}</div>}
        
        {!loading && !loadError && (
          <div>
            {records.length} records available
            {allowMultiple && maxRelationships && (
              <span> • {normalizedValue.length}/{maxRelationships} selected</span>
            )}
            {allowSelfReference && <span> • Self-reference enabled</span>}
            {allowRelationshipTypeSelection && <span> • Relationship types enabled</span>}
          </div>
        )}
        
        {error && <div className="text-red-500">{error}</div>}
      </div>
    </div>
  )
}

export const RelationFieldComponent: FieldComponent = {
  renderInput: (props: FieldRenderProps) => {
    // Always use the unified enhanced relationship component
    // It handles both simple and complex relationship scenarios
    return <EnhancedRelationshipInput {...props} />
  },

  formatValue: (value: any, field: Field, context?: string) => {
    if (value === null || value === undefined || value === '') {
      if (context === 'table') {
        return <span className="text-gray-400 italic">—</span>
      }
      return ''
    }
    
    // Check if this is an enhanced relationship field with multiple values
    const allowMultiple = getFieldConfig(field, 'allow_multiple', false)
    const allowRelationshipTypeSelection = getFieldConfig(field, 'allow_relationship_type_selection', false)
    
    if (allowMultiple && Array.isArray(value)) {
      return (
        <div className="space-y-1">
          {value.map((relationship, index) => {
            const recordId = typeof relationship === 'object' ? relationship.record_id : relationship
            const relationshipType = typeof relationship === 'object' ? relationship.relationship_type : null
            
            return (
              <div key={`${recordId}-${index}`} className="flex items-center gap-2">
                <Link className="w-3 h-3 text-gray-500" />
                <RelationDisplayValue value={recordId} field={field} context={context} />
                {allowRelationshipTypeSelection && relationshipType && (
                  <span className="text-xs text-gray-500 bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded">
                    {relationshipType.replace('_', ' ')}
                  </span>
                )}
              </div>
            )
          })}
        </div>
      )
    }
    
    // Handle enhanced single relationship
    if (typeof value === 'object' && value.record_id) {
      return (
        <div className="flex items-center gap-2">
          <Link className="w-3 h-3 text-gray-500" />
          <RelationDisplayValue value={value.record_id} field={field} context={context} />
          {allowRelationshipTypeSelection && value.relationship_type && (
            <span className="text-xs text-gray-500 bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded">
              {value.relationship_type.replace('_', ' ')}
            </span>
          )}
        </div>
      )
    }
    
    // Fall back to simple single relationship display
    return <RelationDisplayValue value={value} field={field} context={context} />
  },

  validate: (value: any, field: Field): ValidationResult => {
    // Note: Required validation handled by permission system

    const targetPipelineId = getFieldConfig(field, 'target_pipeline_id')
    if (!targetPipelineId) {
      return {
        isValid: false,
        error: 'Relation field must have a target pipeline configured'
      }
    }

    // Enhanced relationship validation
    const allowMultiple = getFieldConfig(field, 'allow_multiple', false)
    const maxRelationships = getFieldConfig(field, 'max_relationships', null)
    
    if (value) {
      // Check if value is in enhanced format
      if (allowMultiple && Array.isArray(value)) {
        // Validate multiple relationships
        if (maxRelationships && value.length > maxRelationships) {
          return {
            isValid: false,
            error: `Too many relationships. Maximum allowed: ${maxRelationships}`
          }
        }
        
        // Validate each relationship
        for (const rel of value) {
          if (typeof rel === 'object' && rel.record_id) {
            if (!rel.record_id) {
              return {
                isValid: false,
                error: 'Each relationship must have a valid record ID'
              }
            }
          }
        }
      } else if (typeof value === 'object' && value.record_id && !value.record_id) {
        return {
          isValid: false,
          error: 'Relationship must have a valid record ID'
        }
      }
    }

    return { isValid: true }
  },

  getDefaultValue: (field: Field) => {
    return getFieldConfig(field, 'default_value', null)
  },

  isEmpty: (value: any) => {
    if (!value || value === '') return true
    
    // Handle enhanced relationship arrays
    if (Array.isArray(value)) {
      return value.length === 0 || value.every(rel => {
        if (typeof rel === 'object' && rel.record_id) {
          return !rel.record_id
        }
        return !rel
      })
    }
    
    // Handle enhanced relationship objects
    if (typeof value === 'object' && value.record_id) {
      return !value.record_id
    }
    
    return false
  }
}