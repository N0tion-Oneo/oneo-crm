'use client'

import React, { useState, useCallback, useMemo } from 'react'
import { Plus, X, Eye, EyeOff, AlertCircle, Layers, ChevronDown, ChevronRight } from 'lucide-react'

// Simple debounce utility
const debounce = (func: (...args: any[]) => void, delay: number) => {
  let timeoutId: NodeJS.Timeout
  return (...args: any[]) => {
    clearTimeout(timeoutId)
    timeoutId = setTimeout(() => func(...args), delay)
  }
}

interface ConditionalRule {
  field: string
  condition: string
  value: any
  description?: string
}

interface ConditionalRuleGroup {
  logic: 'AND' | 'OR'
  rules: (ConditionalRule | ConditionalRuleGroup)[]
}

interface ConditionalRules {
  show_when?: ConditionalRuleGroup
  hide_when?: ConditionalRuleGroup
  require_when?: ConditionalRuleGroup
}

interface AvailableField {
  id: string
  name: string
  display_name: string
  field_type: string
}

interface UserType {
  id: string
  name: string
  slug: string
  description?: string
}

interface ConditionalRulesBuilderProps {
  field: any
  availableFields: AvailableField[]
  userTypes?: UserType[]  // Optional, if not provided user type rules won't be shown
  onChange: (rules: ConditionalRules) => void
}

const CONDITION_OPERATORS = [
  { value: 'equals', label: 'equals', icon: '=' },
  { value: 'not_equals', label: 'not equals', icon: '≠' },
  { value: 'contains', label: 'contains', icon: '⊃' },
  { value: 'not_contains', label: 'not contains', icon: '⊅' },
  { value: 'greater_than', label: 'greater than', icon: '>' },
  { value: 'less_than', label: 'less than', icon: '<' },
  { value: 'is_empty', label: 'is empty', icon: '∅' },
  { value: 'is_not_empty', label: 'is not empty', icon: '∅̸' },
  { value: 'starts_with', label: 'starts with', icon: 'A*' },
  { value: 'ends_with', label: 'ends with', icon: '*Z' }
]

// Helper functions for working with conditional rule configs
const isRuleGroup = (item: ConditionalRule | ConditionalRuleGroup): item is ConditionalRuleGroup => {
  return 'logic' in item && 'rules' in item
}

const createEmptyRuleGroup = (): ConditionalRuleGroup => ({
  logic: 'AND',
  rules: []
})

const createEmptyRule = (): ConditionalRule => ({
  field: '',
  condition: 'equals',
  value: ''
})

const RuleRow: React.FC<{
  rule: ConditionalRule
  availableFields: AvailableField[]
  userTypes?: UserType[]
  onRuleChange: (rule: ConditionalRule) => void
  onRemove: () => void
  ruleType: 'show_when' | 'hide_when' | 'require_when'
}> = React.memo(({ rule, availableFields, userTypes = [], onRuleChange, onRemove, ruleType }) => {
  const selectedField = useMemo(() => 
    availableFields.find(f => f.name === rule.field), 
    [availableFields, rule.field]
  )
  
  const handleFieldChange = useCallback((fieldName: string) => {
    onRuleChange({ ...rule, field: fieldName })
  }, [rule, onRuleChange])
  
  const handleConditionChange = useCallback((condition: string) => {
    onRuleChange({ ...rule, condition })
  }, [rule, onRuleChange])
  
  const handleValueChange = useCallback((value: string) => {
    onRuleChange({ ...rule, value })
  }, [rule, onRuleChange])

  return (
    <div className="flex items-center space-x-2 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
      {/* Field Selector */}
      <div className="flex-1">
        <select
          value={rule.field || ''}
          onChange={(e) => handleFieldChange(e.target.value)}
          className="w-full text-sm border border-gray-200 dark:border-gray-600 rounded px-2 py-1 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
        >
          <option value="">Select field...</option>
          {availableFields.map(field => (
            <option key={field.name} value={field.name}>
              {field.display_name} ({field.field_type})
            </option>
          ))}
        </select>
      </div>
      
      {/* Condition Selector */}
      <div className="flex-1">
        <select
          value={rule.condition || ''}
          onChange={(e) => handleConditionChange(e.target.value)}
          className="w-full text-sm border border-gray-200 dark:border-gray-600 rounded px-2 py-1 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
        >
          <option value="">Select condition...</option>
          {CONDITION_OPERATORS.map(op => (
            <option key={op.value} value={op.value}>
              {op.label} {op.icon}
            </option>
          ))}
        </select>
      </div>
      
      {/* Value Input */}
      {rule.condition && !['is_empty', 'is_not_empty'].includes(rule.condition) && (
        <div className="flex-1">
          {rule.field === 'user_type' ? (
            // Special dropdown for user_type field
            <select
              value={rule.value || ''}
              onChange={(e) => handleValueChange(e.target.value)}
              className="w-full text-sm border border-gray-200 dark:border-gray-600 rounded px-2 py-1 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            >
              <option value="">Select user type</option>
              {userTypes.map(userType => (
                <option key={userType.slug} value={userType.slug}>
                  {userType.name}
                </option>
              ))}
            </select>
          ) : (
            // Regular text input for other fields
            <input
              type="text"
              value={rule.value || ''}
              onChange={(e) => handleValueChange(e.target.value)}
              placeholder="Value"
              className="w-full text-sm border border-gray-200 dark:border-gray-600 rounded px-2 py-1 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          )}
        </div>
      )}
      
      {/* Remove Button */}
      <button
        onClick={onRemove}
        className="p-1 text-red-500 hover:bg-red-100 dark:hover:bg-red-900/20 rounded"
        title="Remove rule"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  )
})

const RuleGroupBuilder: React.FC<{
  group: ConditionalRuleGroup
  availableFields: AvailableField[]
  userTypes: UserType[]
  onGroupChange: (group: ConditionalRuleGroup) => void
  onRemove?: () => void
  depth?: number
  ruleType: 'show_when' | 'hide_when' | 'require_when'
}> = React.memo(({ group, availableFields, userTypes, onGroupChange, onRemove, depth = 0, ruleType }) => {
  const [isCollapsed, setIsCollapsed] = useState(false)

  const updateLogic = useCallback((logic: 'AND' | 'OR') => {
    onGroupChange({ ...group, logic })
  }, [group, onGroupChange])

  const addRule = useCallback(() => {
    const newRule = createEmptyRule()
    onGroupChange({
      ...group,
      rules: [...group.rules, newRule]
    })
  }, [group, onGroupChange])

  const addGroup = useCallback(() => {
    const newGroup = createEmptyRuleGroup()
    onGroupChange({
      ...group,
      rules: [...group.rules, newGroup]
    })
  }, [group, onGroupChange])

  const updateRule = useCallback((index: number, updatedItem: ConditionalRule | ConditionalRuleGroup) => {
    const newRules = [...group.rules]
    newRules[index] = updatedItem
    onGroupChange({ ...group, rules: newRules })
  }, [group, onGroupChange])

  const removeRule = useCallback((index: number) => {
    const newRules = group.rules.filter((_, i) => i !== index)
    onGroupChange({ ...group, rules: newRules })
  }, [group, onGroupChange])

  const getLogicColor = useMemo(() => (logic: string) => {
    return logic === 'OR' ? 'text-orange-600 bg-orange-50 border-orange-200 dark:bg-orange-900/20 dark:text-orange-400 dark:border-orange-800' 
                          : 'text-blue-600 bg-blue-50 border-blue-200 dark:bg-blue-900/20 dark:text-blue-400 dark:border-blue-800'
  }, [])

  return (
    <div className={`border rounded-lg transition-all duration-200 ${
      depth > 0 ? 'ml-4 bg-gray-50/50 dark:bg-gray-800/50' : 'bg-white dark:bg-gray-800'
    } ${depth > 0 ? 'border-gray-200 dark:border-gray-700' : 'border-gray-300 dark:border-gray-600'}`}>
      {/* Group Header */}
      <div className="flex items-center justify-between p-3 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center space-x-3">
          {/* Collapse Toggle */}
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded"
          >
            {isCollapsed ? (
              <ChevronRight className="w-4 h-4 text-gray-500" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-500" />
            )}
          </button>

          {/* Logic Selector */}
          <div className="flex items-center space-x-2">
            <Layers className="w-4 h-4 text-gray-500" />
            <select
              value={group.logic}
              onChange={(e) => updateLogic(e.target.value as 'AND' | 'OR')}
              className={`text-sm font-medium border rounded px-3 py-1 transition-colors ${getLogicColor(group.logic)}`}
            >
              <option value="AND">All conditions must be true (AND)</option>
              <option value="OR">Any condition can be true (OR)</option>
            </select>
          </div>

          {/* Rule Count */}
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {group.rules.length} rule{group.rules.length !== 1 ? 's' : ''}
          </span>
        </div>

        {/* Remove Group Button */}
        {onRemove && depth > 0 && (
          <button
            onClick={onRemove}
            className="p-1 text-red-500 hover:bg-red-100 dark:hover:bg-red-900/20 rounded transition-colors"
            title="Remove group"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Group Content */}
      {!isCollapsed && (
        <div className="p-3 space-y-3">
          {/* Rules */}
          {group.rules.map((rule, index) => (
            <div key={index} className="space-y-2">
              {index > 0 && (
                <div className="flex justify-center">
                  <span className={`text-xs font-medium px-2 py-1 rounded ${getLogicColor(group.logic)}`}>
                    {group.logic}
                  </span>
                </div>
              )}
              
              {isRuleGroup(rule) ? (
                <RuleGroupBuilder
                  group={rule}
                  availableFields={availableFields}
                  userTypes={userTypes}
                  onGroupChange={(updatedGroup) => updateRule(index, updatedGroup)}
                  onRemove={() => removeRule(index)}
                  depth={depth + 1}
                  ruleType={ruleType}
                />
              ) : (
                <RuleRow
                  rule={rule}
                  availableFields={availableFields}
                  userTypes={userTypes}
                  onRuleChange={(updatedRule) => updateRule(index, updatedRule)}
                  onRemove={() => removeRule(index)}
                  ruleType={ruleType}
                />
              )}
            </div>
          ))}

          {/* Empty State */}
          {group.rules.length === 0 && (
            <div className="text-center py-6 text-gray-500 dark:text-gray-400">
              <Layers className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No conditions added yet</p>
              <p className="text-xs mt-1">Add conditions or nested groups below</p>
            </div>
          )}

          {/* Add Buttons */}
          <div className="flex items-center space-x-2 pt-2 border-t border-gray-200 dark:border-gray-700">
            <button
              onClick={addRule}
              className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-200 hover:bg-blue-50 dark:hover:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md transition-colors"
            >
              <Plus className="w-3 h-3 mr-1" />
              Add Condition
            </button>
            
            <button
              onClick={addGroup}
              className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-green-600 hover:text-green-800 dark:text-green-400 dark:hover:text-green-200 hover:bg-green-50 dark:hover:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-md transition-colors"
            >
              <Layers className="w-3 h-3 mr-1" />
              Add Group
            </button>
          </div>
        </div>
      )}
    </div>
  )
})

export const ConditionalRulesBuilder: React.FC<ConditionalRulesBuilderProps> = ({
  field,
  availableFields,
  userTypes = [],
  onChange
}) => {
  const currentRules = field?.business_rules?.conditional_rules || {}
  
  // Initialize rule groups from current state
  const [showWhenGroup, setShowWhenGroup] = useState<ConditionalRuleGroup>(() => 
    currentRules.show_when || createEmptyRuleGroup()
  )
  const [hideWhenGroup, setHideWhenGroup] = useState<ConditionalRuleGroup>(() => 
    currentRules.hide_when || createEmptyRuleGroup()
  )
  const [requireWhenGroup, setRequireWhenGroup] = useState<ConditionalRuleGroup>(() => 
    currentRules.require_when || createEmptyRuleGroup()
  )

  // Create enhanced field list with stage funnel indicators (memoized)
  const enhancedFields = useMemo(() => [
    // Add user_type as a virtual field if userTypes are available
    ...(userTypes.length > 0 ? [{
      id: 'user_type',
      name: 'user_type',
      display_name: 'User Type',
      field_type: 'select'
    }] : []),
    // Add regular fields (excluding self-reference)
    ...availableFields.filter(f => f.name !== field?.name).map(f => {
      if (f.field_type === 'select') {
        return {
          ...f,
          display_name: `📊 ${f.display_name} (Stage Funnel)`,
          isStageField: true
        }
      }
      return f
    })
  ], [userTypes.length, availableFields, field?.name])

  // Debounced rule updates to prevent excessive processing
  const debouncedOnChange = useMemo(
    () => debounce(onChange, 300),
    [onChange]
  )

  const updateRules = useCallback((
    newShowWhenGroup: ConditionalRuleGroup, 
    newHideWhenGroup: ConditionalRuleGroup, 
    newRequireWhenGroup: ConditionalRuleGroup
  ) => {
    const rules: ConditionalRules = {}
    
    // Only include groups that have rules
    if (newShowWhenGroup.rules.length > 0) {
      rules.show_when = newShowWhenGroup
    }
    if (newHideWhenGroup.rules.length > 0) {
      rules.hide_when = newHideWhenGroup  
    }
    if (newRequireWhenGroup.rules.length > 0) {
      rules.require_when = newRequireWhenGroup
    }
    
    debouncedOnChange(rules)
  }, [debouncedOnChange])

  const handleShowWhenChange = useCallback((group: ConditionalRuleGroup) => {
    setShowWhenGroup(group)
    updateRules(group, hideWhenGroup, requireWhenGroup)
  }, [hideWhenGroup, requireWhenGroup, updateRules])

  const handleHideWhenChange = useCallback((group: ConditionalRuleGroup) => {
    setHideWhenGroup(group)
    updateRules(showWhenGroup, group, requireWhenGroup)
  }, [showWhenGroup, requireWhenGroup, updateRules])

  const handleRequireWhenChange = useCallback((group: ConditionalRuleGroup) => {
    setRequireWhenGroup(group)
    updateRules(showWhenGroup, hideWhenGroup, group)
  }, [showWhenGroup, hideWhenGroup, updateRules])


  if (enhancedFields.length === 0) {
    return (
      <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="flex items-center space-x-2 text-gray-500 dark:text-gray-400">
          <AlertCircle className="w-4 h-4" />
          <span className="text-sm">No other fields available for conditional rules.</span>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="text-sm text-gray-600 dark:text-gray-400">
        Configure when this field should be shown, hidden, or required based on other field values.
        Use AND/OR logic to create complex conditional rules.
      </div>

      {/* Show When Rules */}
      <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
        <div className="flex items-center space-x-2 mb-3">
          <Eye className="w-4 h-4 text-green-600" />
          <h5 className="font-medium text-gray-900 dark:text-white">Show this field when:</h5>
        </div>
        <div className="text-xs text-gray-500 dark:text-gray-400 mb-3">
          Field will only be visible when conditions are met
        </div>
        
        <RuleGroupBuilder
          group={showWhenGroup}
          availableFields={enhancedFields}
          userTypes={userTypes}
          onGroupChange={handleShowWhenChange}
          ruleType="show_when"
        />
      </div>

      {/* Hide When Rules */}
      <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
        <div className="flex items-center space-x-2 mb-3">
          <EyeOff className="w-4 h-4 text-red-600" />
          <h5 className="font-medium text-gray-900 dark:text-white">Hide this field when:</h5>
        </div>
        <div className="text-xs text-gray-500 dark:text-gray-400 mb-3">
          Field will be hidden when conditions are met
        </div>
        
        <RuleGroupBuilder
          group={hideWhenGroup}
          availableFields={enhancedFields}
          userTypes={userTypes}
          onGroupChange={handleHideWhenChange}
          ruleType="hide_when"
        />
      </div>

      {/* Require When Rules */}
      <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
        <div className="flex items-center space-x-2 mb-3">
          <AlertCircle className="w-4 h-4 text-orange-600" />
          <h5 className="font-medium text-gray-900 dark:text-white">Make this field required when:</h5>
        </div>
        <div className="text-xs text-gray-500 dark:text-gray-400 mb-3">
          Field will be required when conditions are met
        </div>
        
        <RuleGroupBuilder
          group={requireWhenGroup}
          availableFields={enhancedFields}
          userTypes={userTypes}
          onGroupChange={handleRequireWhenChange}
          ruleType="require_when"
        />
      </div>

      {/* Summary */}
      {(showWhenGroup.rules.length > 0 || hideWhenGroup.rules.length > 0 || requireWhenGroup.rules.length > 0) && (
        <div className="bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
          <div className="text-sm font-medium text-blue-900 dark:text-blue-100 mb-2">
            Conditional Rules Summary:
          </div>
          <div className="text-xs text-blue-700 dark:text-blue-300 space-y-1">
            {showWhenGroup.rules.length > 0 && (
              <div>• {showWhenGroup.rules.length} show condition(s) with {showWhenGroup.logic} logic</div>
            )}
            {hideWhenGroup.rules.length > 0 && (
              <div>• {hideWhenGroup.rules.length} hide condition(s) with {hideWhenGroup.logic} logic</div>
            )}
            {requireWhenGroup.rules.length > 0 && (
              <div>• {requireWhenGroup.rules.length} required condition(s) with {requireWhenGroup.logic} logic</div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}