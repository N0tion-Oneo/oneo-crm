// FilterPanel - Complex boolean query builder interface with unified controls
import React, { useState, useEffect } from 'react'
import { X, Plus, BookmarkPlus, Bookmark } from 'lucide-react'
import { 
  Filter, 
  FilterGroup, 
  BooleanQuery, 
  FilterOperator, 
  RecordField,
  FieldOption 
} from '@/types/records'
import { FilterTransformService } from '@/services/records'
import { pipelinesApi, usersApi } from '@/lib/api'
import { SaveFilterModal, SavedFiltersList } from '@/components/pipelines/saved-filters'

export interface FilterPanelProps {
  booleanQuery: BooleanQuery
  onBooleanQueryChange: (query: BooleanQuery) => void
  pipeline: { 
    id: string; 
    name: string;
    fields: RecordField[] 
  }
  showFilters: boolean
  onClose: () => void
  onGetFieldOptions: (fieldName: string, fieldType: string) => Promise<FieldOption[]>
  // New props for save/load functionality
  currentViewMode?: 'table' | 'kanban' | 'calendar'
  visibleFields?: string[]
  sortConfig?: any
  onFilterSelect?: (filter: any) => void
  className?: string
}

export function FilterPanel({
  booleanQuery,
  onBooleanQueryChange,
  pipeline,
  showFilters,
  onClose,
  onGetFieldOptions,
  currentViewMode = 'table',
  visibleFields = [],
  sortConfig = {},
  onFilterSelect,
  className = ""
}: FilterPanelProps) {
  const [newFilterField, setNewFilterField] = useState('')
  const [newFilterOperator, setNewFilterOperator] = useState<FilterOperator>('equals')
  const [newFilterValue, setNewFilterValue] = useState('')
  const [newFilterRole, setNewFilterRole] = useState('') // For user field role filtering
  const [selectedGroupId, setSelectedGroupId] = useState<string>('group-1')
  const [fieldOptionsCache, setFieldOptionsCache] = useState<Record<string, FieldOption[]>>({})
  
  // Save/Load modal states
  const [showSaveFilterModal, setShowSaveFilterModal] = useState(false)
  const [showSavedFiltersList, setShowSavedFiltersList] = useState(false)

  // Reset selected group when query changes
  useEffect(() => {
    if (booleanQuery && booleanQuery.groups && booleanQuery.groups.length > 0 && !booleanQuery.groups.find(g => g.id === selectedGroupId)) {
      setSelectedGroupId(booleanQuery.groups[0].id)
    }
  }, [booleanQuery, selectedGroupId])

  // Fetch field options when a field is selected
  useEffect(() => {
    if (newFilterField) {
      const field = pipeline.fields.find(f => f.name === newFilterField)
      
      if (field && ['user', 'tags', 'relation', 'relationship', 'related'].includes(field.field_type) && !fieldOptionsCache[newFilterField]) {
        loadFieldOptions(newFilterField, field.field_type)
      }
    }
  }, [newFilterField, pipeline.fields, fieldOptionsCache])

  if (!showFilters) {
    return null
  }

  // Include all filterable field types (matching original backup + additional types)
  const filterableFields = pipeline.fields.filter(field => 
    [
      // Text types
      'text', 'textarea', 'email', 'phone', 'url',
      // Numeric types  
      'number', 'decimal', 'integer', 'float', 'currency', 'percentage',
      // Selection types
      'select', 'multiselect', 'radio', 'checkbox', 'boolean',
      // Temporal types
      'date', 'datetime', 'time',
      // Special types
      'user', 'tags', 'relation', 'relationship', 'related'
    ].includes(field.field_type)
  )

  const fieldHasOptions = (fieldName: string): boolean => {
    if (!fieldName) return false
    const field = pipeline.fields.find(f => f.name === fieldName)
    return [
      'select', 'multiselect', 'radio', 'checkbox', 'boolean', 
      'user', 'tags', 'relation', 'relationship', 'related'
    ].includes(field?.field_type || '')
  }

  const getUserRoleOptions = (fieldName: string): FieldOption[] => {
    if (!fieldName) return []
    const field = pipeline.fields.find(f => f.name === fieldName)
    if (!field || field.field_type !== 'user') return []
    
    const userConfig = field.field_config || {}
    const allowedRoles = userConfig.allowed_roles || ['assigned', 'owner', 'collaborator', 'reviewer']
    
    return allowedRoles.map((role: string) => ({
      value: role,
      label: role.charAt(0).toUpperCase() + role.slice(1)
    }))
  }

  const isUserField = (fieldName: string): boolean => {
    if (!fieldName) return false
    const field = pipeline.fields.find(f => f.name === fieldName)
    return field?.field_type === 'user'
  }

  const getFieldOptions = (fieldName: string): FieldOption[] => {
    const field = pipeline.fields.find(f => f.name === fieldName)
    if (!field) return []
    
    switch (field.field_type) {
      case 'select':
      case 'multiselect':
      case 'radio':
      case 'checkbox':
        return field.field_config?.options || []
      case 'boolean':
        return [
          { value: 'true', label: 'Yes' },
          { value: 'false', label: 'No' }
        ]
      case 'user':
        // For user fields, return just the user options
        // Role filtering will be handled separately
        return fieldOptionsCache[fieldName] || []
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

  // Comprehensive field options loading (matching original implementation exactly)
  const loadFieldOptions = async (fieldName: string, fieldType: string) => {
    if (fieldOptionsCache[fieldName]) return
    if (!['user', 'tags', 'relation', 'relationship', 'related'].includes(fieldType)) return

    try {
      console.log(`🔍 Loading field options for ${fieldName} (${fieldType})`)
      
      let options: FieldOption[] = []

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
          
          options = Array.from(uniqueTags).sort().map(tag => ({ value: tag, label: tag }))
          break

        case 'user':
          // Fetch available users for this tenant
          console.log(`🔍 Fetching users from API...`)
          const usersResponse = await usersApi.list()
          console.log(`👥 Users API response:`, usersResponse)
          
          // Handle different possible response structures
          const users = usersResponse.data.results || usersResponse.data || []
          console.log(`👥 Processed users array:`, users)
          
          options = users.map((user: any) => ({
            value: user.id.toString(),
            label: `${user.first_name || ''} ${user.last_name || ''}`.trim() || user.email || user.username || `User ${user.id}`
          }))
          console.log(`👥 Final user options:`, options)
          break

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
            options = []
            break
          }
          console.log(`🔗 Fetching records from target pipeline ${targetPipelineId}`)
          
          try {
            // Fetch records from the target pipeline
            const relationResponse = await pipelinesApi.getRecords(targetPipelineId, { 
              limit: 200 // Get a reasonable number of options
            })
            
            if (relationResponse.data.results) {
              const configuredDisplayField = field.field_config?.display_field
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
              }).filter((option: any) => option.label && option.label !== 'Record undefined')
              
              console.log(`🔗 Found ${relationOptions.length} relation options:`, relationOptions)
              options = relationOptions
            }
          } catch (error) {
            console.error(`Failed to fetch relation options for ${fieldName}:`, error)
            options = []
          }
          break

        default:
          options = []
      }

      console.log(`✅ Loaded ${options.length} options for ${fieldName}:`, options.slice(0, 3))
      setFieldOptionsCache(prev => ({ ...prev, [fieldName]: options }))
    } catch (error) {
      console.error(`Failed to load options for field ${fieldName}:`, error)
      setFieldOptionsCache(prev => ({ ...prev, [fieldName]: [] }))
    }
  }


  const removeFilter = (groupId: string, filterIndex: number) => {
    const updatedQuery = FilterTransformService.removeFilterFromGroup(booleanQuery, groupId, filterIndex)
    onBooleanQueryChange(updatedQuery)
  }

  const addFilter = () => {
    // For user fields, require at least user or role
    if (isUserField(newFilterField)) {
      if (!newFilterValue && !newFilterRole && !['is_empty', 'is_not_empty'].includes(newFilterOperator)) {
        return
      }
    } else {
      if (!newFilterField || (!newFilterValue && !['is_empty', 'is_not_empty'].includes(newFilterOperator))) {
        return
      }
    }

    let filterValue = newFilterValue

    // For user fields, handle structured filtering
    if (isUserField(newFilterField)) {
      if (newFilterValue && newFilterRole) {
        // Both user and role specified
        filterValue = JSON.stringify({
          user_id: newFilterValue,
          role: newFilterRole
        })
      } else if (newFilterValue) {
        // Only user specified
        filterValue = JSON.stringify({
          user_id: newFilterValue
        })
      } else if (newFilterRole) {
        // Only role specified
        filterValue = JSON.stringify({
          role: newFilterRole
        })
      }
    }

    const newFilter: Filter = {
      field: newFilterField,
      operator: newFilterOperator,
      value: filterValue
    }

    const updatedQuery = FilterTransformService.addFilterToGroup(booleanQuery, selectedGroupId, newFilter)
    onBooleanQueryChange(updatedQuery)

    // Reset form
    setNewFilterField('')
    setNewFilterOperator('equals')
    setNewFilterValue('')
    setNewFilterRole('')
  }

  const addFilterGroup = () => {
    const updatedQuery = FilterTransformService.addFilterGroup(booleanQuery)
    onBooleanQueryChange(updatedQuery)
  }

  const removeFilterGroup = (groupId: string) => {
    const updatedQuery = FilterTransformService.removeFilterGroup(booleanQuery, groupId)
    onBooleanQueryChange(updatedQuery)
  }

  const updateGroupLogic = (groupId: string, logic: 'AND' | 'OR') => {
    const updatedQuery = FilterTransformService.updateGroupLogic(booleanQuery, groupId, logic)
    onBooleanQueryChange(updatedQuery)
  }

  const updateQueryLogic = (logic: 'AND' | 'OR') => {
    onBooleanQueryChange({ ...booleanQuery, groupLogic: logic })
  }

  // Check if there are active filters
  const hasActiveFilters = booleanQuery && booleanQuery.groups ? booleanQuery.groups.some(group => 
    group.filters.length > 0
  ) : false

  // Handler for save filter
  const handleSaveFilter = () => {
    setShowSaveFilterModal(true)
  }

  // Handler for filter selection
  const handleFilterSelect = (filter: any) => {
    if (onFilterSelect) {
      onFilterSelect(filter)
    }
    setShowSavedFiltersList(false)
  }

  return (
    <div className={`p-4 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 ${className}`}>
      {/* Unified Filter Controls */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-gray-900 dark:text-white">Filters</h3>
        
        <div className="flex items-center space-x-2">
          {/* Save Filter Button */}
          <button
            onClick={handleSaveFilter}
            disabled={!hasActiveFilters && visibleFields.length === 0}
            className="px-3 py-1 border border-blue-300 dark:border-blue-600 text-blue-600 dark:text-blue-400 rounded-md hover:bg-blue-50 dark:hover:bg-blue-900/20 disabled:opacity-50 disabled:cursor-not-allowed flex items-center text-sm"
            title="Save current filter and view settings"
          >
            <BookmarkPlus className="w-4 h-4 mr-1" />
            Save
          </button>

          {/* Saved Filters Dropdown */}
          <div className="relative">
            <button
              onClick={() => setShowSavedFiltersList(!showSavedFiltersList)}
              className={`px-3 py-1 border rounded-md flex items-center text-sm ${
                showSavedFiltersList 
                  ? 'border-blue-300 bg-blue-50 text-blue-600 dark:border-blue-600 dark:bg-blue-900/20 dark:text-blue-400'
                  : 'border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'
              }`}
            >
              <Bookmark className="w-4 h-4 mr-1" />
              Saved
            </button>

            {showSavedFiltersList && (
              <div className="absolute right-0 top-8 w-80 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-20 max-h-80 overflow-hidden">
                <div className="p-3 border-b border-gray-200 dark:border-gray-700">
                  <h3 className="font-medium text-gray-900 dark:text-white">Saved Filters</h3>
                </div>
                <div className="max-h-64 overflow-y-auto">
                  <SavedFiltersList
                    pipeline={pipeline}
                    onFilterSelect={handleFilterSelect}
                  />
                </div>
              </div>
            )}
          </div>
          
          {/* Clear All Button */}
          <button
            onClick={() => {
              // Clear all filters
              const emptyQuery = {
                groups: [{
                  id: 'group-1',
                  logic: 'AND' as const,
                  filters: []
                }],
                groupLogic: 'AND' as const
              }
              onBooleanQueryChange(emptyQuery)
            }}
            className="text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
          >
            Clear all
          </button>
        </div>
      </div>

        {/* Boolean Query Groups */}
        {booleanQuery && booleanQuery.groups && booleanQuery.groups.length > 0 && (
          <div className="space-y-4 mb-6">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">Filter Groups</h4>
              {booleanQuery && booleanQuery.groups && booleanQuery.groups.length > 1 && (
                <div className="flex items-center space-x-2 text-sm">
                  <span className="text-gray-500 dark:text-gray-400">Connect groups with:</span>
                  <select
                    value={booleanQuery.groupLogic}
                    onChange={(e) => updateQueryLogic(e.target.value as 'AND' | 'OR')}
                    className="px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700"
                  >
                    <option value="AND">AND</option>
                    <option value="OR">OR</option>
                  </select>
                </div>
              )}
            </div>

            {booleanQuery && booleanQuery.groups ? booleanQuery.groups.map((group, groupIndex) => (
              <div key={group.id} className="border border-gray-200 dark:border-gray-600 rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Group {groupIndex + 1}
                    </span>
                    {group.filters.length > 1 && (
                      <select
                        value={group.logic}
                        onChange={(e) => updateGroupLogic(group.id, e.target.value as 'AND' | 'OR')}
                        className="px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700"
                      >
                        <option value="AND">AND</option>
                        <option value="OR">OR</option>
                      </select>
                    )}
                  </div>
                  
                  {booleanQuery && booleanQuery.groups && booleanQuery.groups.length > 1 && (
                    <button
                      onClick={() => removeFilterGroup(group.id)}
                      className="text-gray-400 hover:text-red-600 dark:hover:text-red-400"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>

                {group.filters.length > 0 && (
                  <div className="flex flex-wrap gap-2 text-sm">
                    {group.filters.map((filter, filterIndex) => (
                      <div key={filterIndex} className="inline-flex items-center gap-1 px-2 py-1 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300 rounded-md text-sm border border-yellow-200 dark:border-yellow-700">
                        <span className="font-medium">{pipeline.fields.find(f => f.name === filter.field)?.display_name || filter.field}</span>
                        <span className="text-yellow-600 dark:text-yellow-400">{filter.operator.replace('_', ' ')}</span>
                        {!['is_empty', 'is_not_empty'].includes(filter.operator) && (
                          <span className="font-medium">"{(() => {
                            // Handle structured user+role filter values
                            if (isUserField(filter.field) && filter.value) {
                              try {
                                const parsedValue = JSON.parse(filter.value)
                                if (parsedValue.user_id && parsedValue.role) {
                                  const userOptions = getFieldOptions(filter.field)
                                  const userOption = userOptions.find((opt: any) => (opt.value || opt) === parsedValue.user_id)
                                  const userName = userOption?.label || `User ${parsedValue.user_id}`
                                  return `${userName} (${parsedValue.role})`
                                } else if (parsedValue.user_id) {
                                  const userOptions = getFieldOptions(filter.field)
                                  const userOption = userOptions.find((opt: any) => (opt.value || opt) === parsedValue.user_id)
                                  return userOption?.label || `User ${parsedValue.user_id}`
                                } else if (parsedValue.role) {
                                  return `Any ${parsedValue.role}`
                                }
                              } catch (e) {
                                // Fallback to regular display for non-structured values
                              }
                            }
                            
                            // Get display value for select fields
                            let displayValue = filter.value
                            if (fieldHasOptions(filter.field)) {
                              const options = getFieldOptions(filter.field)
                              const option = options.find((opt: any) => (opt.value || opt) === filter.value)
                              if (option) {
                                displayValue = option.label || option.value || option
                              }
                            }
                            return displayValue
                          })()}"</span>
                        )}
                        <button
                          onClick={() => removeFilter(group.id, filterIndex)}
                          className="ml-1 text-yellow-600 hover:text-yellow-800 dark:text-yellow-400 dark:hover:text-yellow-200"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                {group.filters.length === 0 && (
                  <div className="text-xs text-gray-500 italic">No filters in this group yet</div>
                )}
              </div>
            )) : []}

            <button
              onClick={addFilterGroup}
              className="w-full py-2 border border-dashed border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-500 dark:text-gray-400 hover:border-gray-400 dark:hover:border-gray-500"
            >
              <Plus className="w-4 h-4 inline mr-1" />
              Add Filter Group
            </button>
          </div>
        )}

        {/* Add New Filter */}
        <div className="space-y-3">
          <h4 className="text-xs font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wide">Add Filter</h4>
          
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
                  if (fieldType && ['user', 'tags', 'relation', 'relationship', 'related'].includes(fieldType)) {
                    setNewFilterOperator('contains') // Default to contains for these field types
                  } else if (fieldType && ['number', 'decimal', 'integer', 'float', 'currency', 'percentage'].includes(fieldType)) {
                    setNewFilterOperator('equals') // Default to equals for numeric types
                  } else {
                    setNewFilterOperator('equals') // Default to equals for other types
                  }
                }}
                className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              >
                <option value="">Select field...</option>
                {filterableFields.map(field => (
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
                  if (fieldType && ['user', 'tags', 'relation', 'relationship', 'related'].includes(fieldType)) {
                    return (
                      <>
                        <option value="contains">Contains</option>
                        <option value="is_empty">Is empty</option>
                        <option value="is_not_empty">Is not empty</option>
                      </>
                    )
                  }
                  
                  // For numeric fields, show numeric operators
                  if (fieldType && ['number', 'decimal', 'integer', 'float', 'currency', 'percentage'].includes(fieldType)) {
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
                  if (fieldType && ['text', 'textarea', 'email', 'phone', 'url'].includes(fieldType)) {
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
                  
                  // For temporal fields, show date/time operators
                  if (fieldType && ['date', 'datetime', 'time'].includes(fieldType)) {
                    return (
                      <>
                        <option value="equals">Equals</option>
                        <option value="greater_than">After</option>
                        <option value="less_than">Before</option>
                        <option value="is_empty">Is empty</option>
                        <option value="is_not_empty">Is not empty</option>
                      </>
                    )
                  }
                  
                  // For selection fields, show equals and empty operators
                  if (fieldType && ['select', 'multiselect', 'radio', 'checkbox', 'boolean'].includes(fieldType)) {
                    return (
                      <>
                        <option value="equals">Equals</option>
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
              <>
                <div className="min-w-0 flex-1">
                  <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
                    {isUserField(newFilterField) ? 'User' : 'Value'}
                  </label>
                  {fieldHasOptions(newFilterField) ? (
                    <select
                      value={newFilterValue}
                      onChange={(e) => setNewFilterValue(e.target.value)}
                      className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                    >
                      <option value="">Select option...</option>
                      {getFieldOptions(newFilterField).map((option: any, index: number) => (
                        <option 
                          key={index} 
                          value={option.value || option}
                          disabled={option.value === 'separator'}
                          style={option.value === 'separator' ? { 
                            color: '#6B7280', 
                            fontSize: '12px',
                            textAlign: 'center'
                          } : {}}
                        >
                          {option.label || option.value || option}
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
                
                {/* Role Input for User Fields */}
                {isUserField(newFilterField) && (
                  <div className="min-w-0 flex-1">
                    <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Role</label>
                    <select
                      value={newFilterRole}
                      onChange={(e) => setNewFilterRole(e.target.value)}
                      className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                    >
                      <option value="">Any role</option>
                      {getUserRoleOptions(newFilterField).map((option: any, index: number) => (
                        <option key={index} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </>
            )}
            
            {/* Group Selection */}
            {booleanQuery && booleanQuery.groups && booleanQuery.groups.length > 1 && (
              <div className="min-w-0 flex-1">
                <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Add to Group</label>
                <select
                  value={selectedGroupId}
                  onChange={(e) => setSelectedGroupId(e.target.value)}
                  className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                >
                  {booleanQuery && booleanQuery.groups ? booleanQuery.groups.map((group, index) => (
                    <option key={group.id} value={group.id}>
                      Group {index + 1} ({group.logic})
                    </option>
                  )) : []}
                </select>
              </div>
            )}
            
            {/* Add Filter Button */}
            <div className="flex-shrink-0">
              <label className="block text-xs text-transparent mb-1">Add</label>
              <button
                onClick={addFilter}
                disabled={!newFilterField || (!newFilterValue && !['is_empty', 'is_not_empty'].includes(newFilterOperator))}
                className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 flex items-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Plus className="w-3 h-3" />
                Add
              </button>
            </div>
          </div>
        </div>

        {/* Save Filter Modal */}
        <SaveFilterModal
          isOpen={showSaveFilterModal}
          onClose={() => setShowSaveFilterModal(false)}
          onSaved={(savedFilter) => {
            console.log('✅ Filter saved:', savedFilter)
            setShowSaveFilterModal(false)
          }}
          booleanQuery={booleanQuery}
          pipeline={{
            id: pipeline.id,
            name: pipeline.name
          }}
          currentViewMode={currentViewMode}
          visibleFields={visibleFields}
          sortConfig={sortConfig}
        />

        {/* Click outside to close saved filters dropdown */}
        {showSavedFiltersList && (
          <div 
            className="fixed inset-0 z-10" 
            onClick={() => setShowSavedFiltersList(false)}
          />
        )}
    </div>
  )
}