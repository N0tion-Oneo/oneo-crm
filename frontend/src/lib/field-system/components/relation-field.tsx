import React, { useState, useEffect, useRef } from 'react'
import { FieldComponent, FieldRenderProps, ValidationResult, Field } from '../types'
import { getFieldConfig } from '../field-registry'
import { pipelinesApi } from '../../api'

// Cache for relation lookups to avoid repeated API calls
const relationCache = new Map<string, string>()

// Function to lookup relation display value
const lookupRelationValue = async (
  value: any, 
  targetPipelineId: number, 
  displayField: string
): Promise<string> => {
  const cacheKey = `${targetPipelineId}-${value}-${displayField}`
  
  // Check cache first
  if (relationCache.has(cacheKey)) {
    return relationCache.get(cacheKey)!
  }
  
  try {
    const response = await pipelinesApi.getRecord(targetPipelineId.toString(), value.toString())
    
    if (response.data) {
      const recordDisplayValue = getDisplayValue(response.data, displayField)
      
      // Cache the result
      relationCache.set(cacheKey, recordDisplayValue)
      return recordDisplayValue
    }
  } catch (error) {
    console.error(`❌ Failed to load relation record ${value}:`, error)
  }
  
  // Fallback to Record #ID
  const fallback = `Record #${value}`
  relationCache.set(cacheKey, fallback)
  return fallback
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

export const RelationFieldComponent: FieldComponent = {
  renderInput: (props: FieldRenderProps) => {
    const { field, value, onChange, onBlur, onKeyDown, disabled, error, className, autoFocus } = props
    
    // Get field configuration
    const targetPipelineId = getFieldConfig(field, 'target_pipeline_id')
    const displayField = getFieldConfig(field, 'display_field', 'title')
    const placeholder = field.placeholder || `Select ${field.display_name || field.name}`
    
    // State for loading records from target pipeline
    const [records, setRecords] = useState<RecordOption[]>([])
    const [loading, setLoading] = useState(false)
    const [loadError, setLoadError] = useState<string | null>(null)
    const [isOpen, setIsOpen] = useState(false)
    const selectRef = useRef<HTMLSelectElement>(null)
    
    // Load records from target pipeline
    useEffect(() => {
      if (!targetPipelineId) return
      
      const loadRecords = async () => {
        setLoading(true)
        setLoadError(null)
        
        try {
          const response = await pipelinesApi.getRecords(targetPipelineId.toString())
          
          if (response.data && response.data.results) {
            setRecords(response.data.results)
          } else if (response.data && Array.isArray(response.data)) {
            setRecords(response.data)
          } else {
            setRecords([])
          }
        } catch (err) {
          console.error('❌ Error loading records:', err)
          setLoadError('Failed to load records')
          setRecords([])
        } finally {
          setLoading(false)
        }
      }
      
      loadRecords()
    }, [targetPipelineId])
    
    const inputClass = `w-full px-3 py-2 border rounded-lg transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-0 ${
      error 
        ? 'border-red-300 dark:border-red-600 focus:border-red-500 focus:ring-red-500 dark:focus:ring-red-400' 
        : 'border-gray-300 dark:border-gray-600 focus:border-blue-500 focus:ring-blue-500 dark:focus:ring-blue-400'
    } ${disabled || loading
        ? 'bg-gray-50 dark:bg-gray-700 cursor-not-allowed text-gray-500 dark:text-gray-400' 
        : 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white'
    } ${className || ''}`

    // Check if the current value exists in our records
    const valueExists = value ? records.some(record => record.id.toString() === value.toString()) : false
    
    console.log('🔍 Relation field render:', { 
      storedValue: value, 
      valueExists,
      recordsCount: records.length,
      loading,
      records: records.map(r => ({ id: r.id, display: getDisplayValue(r, displayField) }))
    })

    // Fixed: Removed key prop that was causing re-renders and display issues

    return (
      <div>
        <select
          ref={selectRef}
          value={value?.toString() || ''}
          onChange={(e) => {
            const selectedId = e.target.value
            onChange(selectedId || null)
          }}
          onBlur={onBlur}
          onKeyDown={onKeyDown}
          disabled={disabled || loading}
          className={inputClass}
          autoFocus={autoFocus}
          required={field.is_required}
        >
          <option value="">
            {loading ? 'Loading...' : placeholder}
          </option>
          {records.map((record) => {
            const displayName = getDisplayValue(record, displayField)
            return (
              <option key={record.id} value={record.id.toString()}>
                {displayName}
              </option>
            )
          })}
        </select>
        
        {error && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error}</p>
        )}
        
        {loadError && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{loadError}</p>
        )}
        
        {!targetPipelineId && (
          <p className="mt-1 text-xs text-yellow-600 dark:text-yellow-400">
            No target pipeline configured
          </p>
        )}
        
        {targetPipelineId && !loadError && (
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            {loading 
              ? `Loading records from Pipeline ${targetPipelineId}...`
              : `${records.length} records available | Display: ${displayField}`
            }
          </p>
        )}
      </div>
    )
  },

  formatValue: (value: any, field: Field, context?: string) => {
    if (value === null || value === undefined || value === '') {
      if (context === 'table') {
        return <span className="text-gray-400 italic">—</span>
      }
      return ''
    }
    
    // Use the RelationDisplayValue component for proper record lookup and display
    return <RelationDisplayValue value={value} field={field} context={context} />
  },

  validate: (value: any, field: Field): ValidationResult => {
    if (field.is_required && (!value || value === '')) {
      return {
        isValid: false,
        error: `${field.display_name || field.name} is required`
      }
    }

    const targetPipelineId = getFieldConfig(field, 'target_pipeline_id')
    if (!targetPipelineId) {
      return {
        isValid: false,
        error: 'Relation field must have a target pipeline configured'
      }
    }

    return { isValid: true }
  },

  getDefaultValue: (field: Field) => {
    return getFieldConfig(field, 'default_value', null)
  },

  isEmpty: (value: any) => !value || value === ''
}