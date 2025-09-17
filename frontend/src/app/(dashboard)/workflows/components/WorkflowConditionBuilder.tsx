'use client'

import React, { useMemo, useCallback, useState, useEffect } from 'react'
import { Plus, X, Layers, ChevronDown, ChevronRight, Loader2 } from 'lucide-react'
import { RecordDataService } from '@/services/records/RecordDataService'

interface Condition {
  field: string
  operator: string
  value: any
  value_to?: any
}

interface ConditionGroup {
  logic: 'AND' | 'OR'
  conditions: (Condition | ConditionGroup)[]
}

// Check if item is a group
const isConditionGroup = (item: Condition | ConditionGroup): item is ConditionGroup => {
  return 'logic' in item && 'conditions' in item
}

interface ConditionRowProps {
  condition: Condition
  fields: any[]
  onUpdate: (condition: Condition) => void
  onRemove: () => void
  supportsChangeOperators?: boolean
  pipelineId?: string
}

const ConditionRow: React.FC<ConditionRowProps> = ({
  condition,
  fields,
  onUpdate,
  onRemove,
  supportsChangeOperators = false,
  pipelineId
}) => {
  const selectedField = fields.find(f => f.name === condition.field)
  const [fieldOptions, setFieldOptions] = useState<Array<{value: string, label: string}>>([])
  const [loadingOptions, setLoadingOptions] = useState(false)

  // Fetch field options when field changes
  useEffect(() => {
    if (!selectedField) {
      setFieldOptions([])
      return
    }

    const fetchOptions = async () => {
      setLoadingOptions(true)
      try {
        let options: Array<{value: string, label: string}> = []

        switch (selectedField.field_type) {
          case 'user':
            options = await RecordDataService.fetchUsers()
            break

          case 'tags':
            if (pipelineId) {
              options = await RecordDataService.fetchTagOptions(pipelineId, selectedField.name)
            }
            break

          case 'relation':
            const targetPipelineId = selectedField.field_config?.target_pipeline_id ||
                                   selectedField.field_config?.target_pipeline
            const displayField = selectedField.field_config?.display_field

            if (targetPipelineId) {
              options = await RecordDataService.fetchRelationOptions(targetPipelineId, displayField)
            }
            break

          case 'select':
          case 'multiselect':
            // Options come from field config
            if (selectedField.field_config?.options) {
              options = selectedField.field_config.options.map((opt: any) => ({
                value: opt.value || opt,
                label: opt.label || opt
              }))
            }
            break
        }

        setFieldOptions(options)
      } catch (error) {
        console.error('Failed to fetch field options:', error)
        setFieldOptions([])
      } finally {
        setLoadingOptions(false)
      }
    }

    fetchOptions()
  }, [selectedField?.name, selectedField?.field_type, pipelineId])

  const renderValueInput = () => {
    const fieldType = selectedField?.field_type || 'text'
    const operator = condition.operator

    // Handle 'between' operator for numbers and dates
    if (operator === 'between') {
      if (fieldType === 'number' || fieldType === 'decimal') {
        return (
          <div className="flex space-x-2 flex-1">
            <input
              type="number"
              value={condition.value || ''}
              onChange={(e) => onUpdate({ ...condition, value: e.target.value })}
              placeholder="From"
              className="flex-1 text-sm border rounded px-2 py-1"
            />
            <input
              type="number"
              value={condition.value_to || ''}
              onChange={(e) => onUpdate({ ...condition, value_to: e.target.value })}
              placeholder="To"
              className="flex-1 text-sm border rounded px-2 py-1"
            />
          </div>
        )
      } else if (fieldType === 'date' || fieldType === 'datetime') {
        return (
          <div className="flex space-x-2 flex-1">
            <input
              type={fieldType === 'datetime' ? 'datetime-local' : 'date'}
              value={condition.value || ''}
              onChange={(e) => onUpdate({ ...condition, value: e.target.value })}
              className="flex-1 text-sm border rounded px-2 py-1"
            />
            <input
              type={fieldType === 'datetime' ? 'datetime-local' : 'date'}
              value={condition.value_to || ''}
              onChange={(e) => onUpdate({ ...condition, value_to: e.target.value })}
              className="flex-1 text-sm border rounded px-2 py-1"
            />
          </div>
        )
      }
    }

    // Handle 'in_last_days' and 'in_next_days' for dates
    if (operator === 'in_last_days' || operator === 'in_next_days') {
      return (
        <input
          type="number"
          value={condition.value || ''}
          onChange={(e) => onUpdate({ ...condition, value: e.target.value })}
          placeholder="Number of days"
          min="1"
          className="flex-1 text-sm border rounded px-2 py-1"
        />
      )
    }

    // Handle 'in' and 'not_in' operators for select/multiselect
    if ((operator === 'in' || operator === 'not_in') && (fieldType === 'select' || fieldType === 'multiselect')) {
      const fieldConfig = selectedField?.field_config || {}
      const options = fieldConfig.options || []

      if (options.length > 0) {
        return (
          <select
            multiple
            value={Array.isArray(condition.value) ? condition.value : []}
            onChange={(e) => {
              const selectedValues = Array.from(e.target.selectedOptions, option => option.value)
              onUpdate({ ...condition, value: selectedValues })
            }}
            className="flex-1 text-sm border rounded px-2 py-1"
            size={3}
          >
            {options.map((opt: any) => (
              <option key={opt.value || opt} value={opt.value || opt}>
                {opt.label || opt}
              </option>
            ))}
          </select>
        )
      }
    }

    // Field type specific inputs
    switch (fieldType) {
      case 'number':
      case 'decimal':
        return (
          <input
            type="number"
            value={condition.value || ''}
            onChange={(e) => onUpdate({ ...condition, value: e.target.value })}
            placeholder="Value"
            step={fieldType === 'decimal' ? '0.01' : '1'}
            className="flex-1 text-sm border rounded px-2 py-1"
          />
        )

      case 'date':
        return (
          <input
            type="date"
            value={condition.value || ''}
            onChange={(e) => onUpdate({ ...condition, value: e.target.value })}
            className="flex-1 text-sm border rounded px-2 py-1"
          />
        )

      case 'datetime':
        return (
          <input
            type="datetime-local"
            value={condition.value || ''}
            onChange={(e) => onUpdate({ ...condition, value: e.target.value })}
            className="flex-1 text-sm border rounded px-2 py-1"
          />
        )

      case 'select':
      case 'multiselect':
        const selectOptions = selectedField?.field_config?.options || []
        if (selectOptions.length > 0) {
          return (
            <select
              value={condition.value || ''}
              onChange={(e) => onUpdate({ ...condition, value: e.target.value })}
              className="flex-1 text-sm border rounded px-2 py-1"
            >
              <option value="">Select...</option>
              {selectOptions.map((opt: any) => (
                <option key={opt.value || opt} value={opt.value || opt}>
                  {opt.label || opt}
                </option>
              ))}
            </select>
          )
        }
        // Fallback to text input if no options defined
        return (
          <input
            type="text"
            value={condition.value || ''}
            onChange={(e) => onUpdate({ ...condition, value: e.target.value })}
            placeholder="Enter value"
            className="flex-1 text-sm border rounded px-2 py-1"
          />
        )

      case 'boolean':
      case 'checkbox':
        // For boolean fields, provide a simple dropdown
        return (
          <select
            value={condition.value || ''}
            onChange={(e) => onUpdate({ ...condition, value: e.target.value === 'true' })}
            className="flex-1 text-sm border rounded px-2 py-1"
          >
            <option value="">Select...</option>
            <option value="true">True</option>
            <option value="false">False</option>
          </select>
        )

      case 'user':
        // Show dropdown of actual users
        if (loadingOptions) {
          return (
            <div className="flex-1 flex items-center justify-center">
              <Loader2 className="h-4 w-4 animate-spin" />
            </div>
          )
        }

        if (operator === 'in' || operator === 'not_in') {
          // Multi-select for in/not_in operators
          return (
            <select
              multiple
              value={Array.isArray(condition.value) ? condition.value : []}
              onChange={(e) => {
                const selectedValues = Array.from(e.target.selectedOptions, option => option.value)
                onUpdate({ ...condition, value: selectedValues })
              }}
              className="flex-1 text-sm border rounded px-2 py-1"
              size={3}
            >
              {fieldOptions.map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          )
        }

        return (
          <select
            value={condition.value || ''}
            onChange={(e) => onUpdate({ ...condition, value: e.target.value })}
            className="flex-1 text-sm border rounded px-2 py-1"
          >
            <option value="">Select user...</option>
            {fieldOptions.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        )

      case 'relation':
        // Show dropdown of related records
        if (loadingOptions) {
          return (
            <div className="flex-1 flex items-center justify-center">
              <Loader2 className="h-4 w-4 animate-spin" />
            </div>
          )
        }

        if (operator === 'in' || operator === 'not_in') {
          // Multi-select for in/not_in operators
          return (
            <select
              multiple
              value={Array.isArray(condition.value) ? condition.value : []}
              onChange={(e) => {
                const selectedValues = Array.from(e.target.selectedOptions, option => option.value)
                onUpdate({ ...condition, value: selectedValues })
              }}
              className="flex-1 text-sm border rounded px-2 py-1"
              size={3}
            >
              {fieldOptions.map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          )
        }

        return (
          <select
            value={condition.value || ''}
            onChange={(e) => onUpdate({ ...condition, value: e.target.value })}
            className="flex-1 text-sm border rounded px-2 py-1"
          >
            <option value="">Select record...</option>
            {fieldOptions.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        )

      case 'tags':
        // Show dropdown of existing tags
        if (loadingOptions) {
          return (
            <div className="flex-1 flex items-center justify-center">
              <Loader2 className="h-4 w-4 animate-spin" />
            </div>
          )
        }

        // For tags, always allow multiple selection
        return (
          <select
            multiple
            value={Array.isArray(condition.value) ? condition.value : (condition.value ? [condition.value] : [])}
            onChange={(e) => {
              const selectedValues = Array.from(e.target.selectedOptions, option => option.value)
              onUpdate({ ...condition, value: selectedValues })
            }}
            className="flex-1 text-sm border rounded px-2 py-1"
            size={3}
          >
            {fieldOptions.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
            {fieldOptions.length === 0 && (
              <option disabled>No tags available</option>
            )}
          </select>
        )

      default:
        // Text input for text, email, url, etc.
        return (
          <input
            type="text"
            value={condition.value || ''}
            onChange={(e) => onUpdate({ ...condition, value: e.target.value })}
            placeholder={fieldType === 'email' ? 'email@example.com' : 'Value'}
            className="flex-1 text-sm border rounded px-2 py-1"
          />
        )
    }

    // Default fallback
    return (
      <input
        type="text"
        value={condition.value || ''}
        onChange={(e) => onUpdate({ ...condition, value: e.target.value })}
        placeholder="Value"
        className="flex-1 text-sm border rounded px-2 py-1"
      />
    )
  }

  const getOperators = () => {
    const fieldType = selectedField?.field_type || 'text'

    // Base operators for all types
    const commonOperators = [
      { value: 'equals', label: 'equals' },
      { value: 'not_equals', label: 'not equals' },
      { value: 'is_empty', label: 'is empty' },
      { value: 'is_not_empty', label: 'is not empty' }
    ]

    // Type-specific operators
    let typeOperators: any[] = []

    switch (fieldType) {
      case 'text':
      case 'textarea':
      case 'email':
      case 'url':
        typeOperators = [
          { value: 'contains', label: 'contains' },
          { value: 'not_contains', label: 'not contains' },
          { value: 'starts_with', label: 'starts with' },
          { value: 'ends_with', label: 'ends with' }
        ]
        break

      case 'number':
      case 'decimal':
        typeOperators = [
          { value: 'greater_than', label: 'greater than' },
          { value: 'greater_than_or_equal', label: 'greater than or equal' },
          { value: 'less_than', label: 'less than' },
          { value: 'less_than_or_equal', label: 'less than or equal' },
          { value: 'between', label: 'between' }
        ]
        break

      case 'date':
      case 'datetime':
        typeOperators = [
          { value: 'before', label: 'before' },
          { value: 'after', label: 'after' },
          { value: 'between', label: 'between' },
          { value: 'in_last_days', label: 'in last X days' },
          { value: 'in_next_days', label: 'in next X days' }
        ]
        break

      case 'boolean':
      case 'checkbox':
        typeOperators = [
          { value: 'is_true', label: 'is true' },
          { value: 'is_false', label: 'is false' }
        ]
        // Remove common operators for boolean
        return typeOperators

      case 'select':
      case 'multiselect':
        typeOperators = [
          { value: 'in', label: 'is one of' },
          { value: 'not_in', label: 'is not one of' }
        ]
        break

      case 'relation':
      case 'user':
        typeOperators = [
          { value: 'in', label: 'is one of' },
          { value: 'not_in', label: 'is not one of' }
        ]
        break
    }

    // Add change operators if supported
    if (supportsChangeOperators) {
      typeOperators.push(
        { value: 'changed', label: 'changed' },
        { value: 'changed_to', label: 'changed to' },
        { value: 'changed_from', label: 'changed from' }
      )
    }

    return [...commonOperators, ...typeOperators]
  }

  return (
    <div className="flex items-center space-x-2 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
      {/* Field Selector */}
      <select
        value={condition.field || ''}
        onChange={(e) => onUpdate({
          ...condition,
          field: e.target.value,
          operator: '', // Reset operator when field changes
          value: '',    // Reset value when field changes
          value_to: undefined // Reset value_to when field changes
        })}
        className="flex-1 text-sm border rounded px-2 py-1"
      >
        <option value="">Select field...</option>
        {fields.map(field => (
          <option key={field.name} value={field.name}>
            {field.display_name || field.name} ({field.field_type})
          </option>
        ))}
      </select>

      {/* Operator Selector */}
      <select
        value={condition.operator || ''}
        onChange={(e) => {
          const newOperator = e.target.value
          // Reset value if switching to/from operators that don't need values
          const noValueOps = ['is_empty', 'is_not_empty', 'changed', 'is_true', 'is_false']
          if (noValueOps.includes(newOperator) || noValueOps.includes(condition.operator)) {
            onUpdate({ ...condition, operator: newOperator, value: '', value_to: undefined })
          } else {
            onUpdate({ ...condition, operator: newOperator })
          }
        }}
        className="flex-1 text-sm border rounded px-2 py-1"
      >
        <option value="">Select operator...</option>
        {getOperators().map(op => (
          <option key={op.value} value={op.value}>
            {op.label}
          </option>
        ))}
      </select>

      {/* Value Input */}
      {condition.operator && !['is_empty', 'is_not_empty', 'changed', 'is_true', 'is_false'].includes(condition.operator) && (
        <>
          {renderValueInput()}
        </>
      )}

      {/* Remove Button */}
      <button
        onClick={onRemove}
        className="p-1 text-red-500 hover:bg-red-100 rounded"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  )
}

interface GroupBuilderProps {
  group: ConditionGroup
  fields: any[]
  onUpdate: (group: ConditionGroup) => void
  onRemove?: () => void
  depth?: number
  supportsChangeOperators?: boolean
  pipelineId?: string
}

const GroupBuilder: React.FC<GroupBuilderProps> = ({
  group,
  fields,
  onUpdate,
  onRemove,
  depth = 0,
  supportsChangeOperators = false,
  pipelineId
}) => {
  const [isCollapsed, setIsCollapsed] = React.useState(false)

  const addCondition = () => {
    const newCondition: Condition = { field: '', operator: '', value: '' }
    onUpdate({
      ...group,
      conditions: [...group.conditions, newCondition]
    })
  }

  const addGroup = () => {
    const newGroup: ConditionGroup = { logic: 'AND', conditions: [] }
    onUpdate({
      ...group,
      conditions: [...group.conditions, newGroup]
    })
  }

  const updateItem = (index: number, item: Condition | ConditionGroup) => {
    const newConditions = [...group.conditions]
    newConditions[index] = item
    onUpdate({ ...group, conditions: newConditions })
  }

  const removeItem = (index: number) => {
    onUpdate({
      ...group,
      conditions: group.conditions.filter((_, i) => i !== index)
    })
  }

  const getLogicColor = (logic: string) => {
    return logic === 'OR'
      ? 'text-orange-600 bg-orange-50 border-orange-200'
      : 'text-blue-600 bg-blue-50 border-blue-200'
  }

  return (
    <div className={`border rounded-lg ${
      depth > 0 ? 'ml-4 bg-gray-50/50' : 'bg-white'
    }`}>
      {/* Group Header */}
      <div className="flex items-center justify-between p-3 border-b">
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="p-1 hover:bg-gray-200 rounded"
          >
            {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>

          <Layers className="w-4 h-4 text-gray-500" />

          <select
            value={group.logic}
            onChange={(e) => onUpdate({ ...group, logic: e.target.value as 'AND' | 'OR' })}
            className={`text-sm font-medium border rounded px-3 py-1 ${getLogicColor(group.logic)}`}
          >
            <option value="AND">All conditions must be true (AND)</option>
            <option value="OR">Any condition can be true (OR)</option>
          </select>

          <span className="text-xs text-gray-500">
            {group.conditions.length} condition{group.conditions.length !== 1 ? 's' : ''}
          </span>
        </div>

        {onRemove && depth > 0 && (
          <button
            onClick={onRemove}
            className="p-1 text-red-500 hover:bg-red-100 rounded"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Group Content */}
      {!isCollapsed && (
        <div className="p-3 space-y-3">
          {group.conditions.map((item, index) => (
            <div key={index}>
              {index > 0 && (
                <div className="flex justify-center py-1">
                  <span className={`text-xs px-2 py-1 rounded ${getLogicColor(group.logic)}`}>
                    {group.logic}
                  </span>
                </div>
              )}

              {isConditionGroup(item) ? (
                <GroupBuilder
                  group={item}
                  fields={fields}
                  onUpdate={(updated) => updateItem(index, updated)}
                  onRemove={() => removeItem(index)}
                  depth={depth + 1}
                  supportsChangeOperators={supportsChangeOperators}
                  pipelineId={pipelineId}
                />
              ) : (
                <ConditionRow
                  condition={item}
                  fields={fields}
                  onUpdate={(updated) => updateItem(index, updated)}
                  onRemove={() => removeItem(index)}
                  supportsChangeOperators={supportsChangeOperators}
                  pipelineId={pipelineId}
                />
              )}
            </div>
          ))}

          {group.conditions.length === 0 && (
            <div className="text-center py-6 text-gray-500">
              <Layers className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No conditions added yet</p>
            </div>
          )}

          <div className="flex items-center space-x-2 pt-2 border-t">
            <button
              onClick={addCondition}
              className="inline-flex items-center px-3 py-1.5 text-sm text-blue-600 hover:bg-blue-50 border border-blue-200 rounded-md"
            >
              <Plus className="w-3 h-3 mr-1" />
              Add Condition
            </button>

            <button
              onClick={addGroup}
              className="inline-flex items-center px-3 py-1.5 text-sm text-green-600 hover:bg-green-50 border border-green-200 rounded-md"
            >
              <Layers className="w-3 h-3 mr-1" />
              Add Group
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

interface WorkflowConditionBuilderProps {
  fields: any[]
  value: any // Can be array or group structure
  onChange: (value: any) => void
  supportsChangeOperators?: boolean
  pipelineId?: string
}

export const WorkflowConditionBuilder: React.FC<WorkflowConditionBuilderProps> = ({
  fields,
  value,
  onChange,
  supportsChangeOperators = false,
  pipelineId
}) => {
  // Convert flat array to group structure if needed
  const rootGroup = useMemo(() => {
    if (!value) {
      return { logic: 'AND' as const, conditions: [] }
    }

    // If it's already a group structure
    if (value.logic && value.conditions) {
      return value as ConditionGroup
    }

    // If it's a flat array, wrap it in a group
    if (Array.isArray(value)) {
      return {
        logic: 'AND' as const,
        conditions: value
      }
    }

    return { logic: 'AND' as const, conditions: [] }
  }, [value])

  const handleUpdate = useCallback((group: ConditionGroup) => {
    // If we only have simple conditions at root level, return as array
    if (group.conditions.every(c => !isConditionGroup(c))) {
      onChange(group.conditions)
    } else {
      // Otherwise return the full group structure
      onChange(group)
    }
  }, [onChange])

  return (
    <GroupBuilder
      group={rootGroup}
      fields={fields}
      onUpdate={handleUpdate}
      supportsChangeOperators={supportsChangeOperators}
      pipelineId={pipelineId}
    />
  )
}