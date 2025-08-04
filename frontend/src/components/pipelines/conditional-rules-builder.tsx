'use client'

import React, { useState } from 'react'
import { Plus, X, Eye, EyeOff, AlertCircle } from 'lucide-react'

interface ConditionalRule {
  field: string
  condition: string
  value: any
}

interface ConditionalRules {
  show_when?: ConditionalRule[]
  hide_when?: ConditionalRule[]
  require_when?: ConditionalRule[]
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

const RuleRow: React.FC<{
  rule: ConditionalRule
  availableFields: AvailableField[]
  userTypes?: UserType[]
  onRuleChange: (rule: ConditionalRule) => void
  onRemove: () => void
  ruleType: 'show_when' | 'hide_when' | 'require_when'
}> = ({ rule, availableFields, userTypes = [], onRuleChange, onRemove, ruleType }) => {
  const selectedField = availableFields.find(f => f.name === rule.field)
  
  const handleFieldChange = (fieldName: string) => {
    onRuleChange({ ...rule, field: fieldName })
  }
  
  const handleConditionChange = (condition: string) => {
    onRuleChange({ ...rule, condition })
  }
  
  const handleValueChange = (value: string) => {
    onRuleChange({ ...rule, value })
  }

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
}

export const ConditionalRulesBuilder: React.FC<ConditionalRulesBuilderProps> = ({
  field,
  availableFields,
  userTypes = [],
  onChange
}) => {
  const currentRules = field?.business_rules?.conditional_rules || {}
  const [showWhenRules, setShowWhenRules] = useState<ConditionalRule[]>(currentRules.show_when || [])
  const [hideWhenRules, setHideWhenRules] = useState<ConditionalRule[]>(currentRules.hide_when || [])
  const [requireWhenRules, setRequireWhenRules] = useState<ConditionalRule[]>(currentRules.require_when || [])

  // Filter out self-references and add user_type as a virtual field
  const filteredFields = [
    // Add user_type as a virtual field if userTypes are available
    ...(userTypes.length > 0 ? [{
      id: 'user_type',
      name: 'user_type',
      display_name: 'User Type',
      field_type: 'select'
    }] : []),
    // Add regular fields (excluding self-reference)
    ...availableFields.filter(f => f.name !== field?.name)
  ]

  const updateRules = (
    newShowWhen: ConditionalRule[], 
    newHideWhen: ConditionalRule[], 
    newRequireWhen: ConditionalRule[]
  ) => {
    const rules: ConditionalRules = {}
    
    if (newShowWhen.length > 0) rules.show_when = newShowWhen
    if (newHideWhen.length > 0) rules.hide_when = newHideWhen
    if (newRequireWhen.length > 0) rules.require_when = newRequireWhen
    
    onChange(rules)
  }

  const addShowWhenRule = () => {
    const newRules = [...showWhenRules, { field: '', condition: '', value: '' }]
    setShowWhenRules(newRules)
    updateRules(newRules, hideWhenRules, requireWhenRules)
  }

  const addHideWhenRule = () => {
    const newRules = [...hideWhenRules, { field: '', condition: '', value: '' }]
    setHideWhenRules(newRules)
    updateRules(showWhenRules, newRules, requireWhenRules)
  }

  const addRequireWhenRule = () => {
    const newRules = [...requireWhenRules, { field: '', condition: '', value: '' }]
    setRequireWhenRules(newRules)
    updateRules(showWhenRules, hideWhenRules, newRules)
  }

  const updateShowWhenRule = (index: number, rule: ConditionalRule) => {
    const newRules = [...showWhenRules]
    newRules[index] = rule
    setShowWhenRules(newRules)
    updateRules(newRules, hideWhenRules, requireWhenRules)
  }

  const updateHideWhenRule = (index: number, rule: ConditionalRule) => {
    const newRules = [...hideWhenRules]
    newRules[index] = rule
    setHideWhenRules(newRules)
    updateRules(showWhenRules, newRules, requireWhenRules)
  }

  const updateRequireWhenRule = (index: number, rule: ConditionalRule) => {
    const newRules = [...requireWhenRules]
    newRules[index] = rule
    setRequireWhenRules(newRules)
    updateRules(showWhenRules, hideWhenRules, newRules)
  }

  const removeShowWhenRule = (index: number) => {
    const newRules = showWhenRules.filter((_, i) => i !== index)
    setShowWhenRules(newRules)
    updateRules(newRules, hideWhenRules, requireWhenRules)
  }

  const removeHideWhenRule = (index: number) => {
    const newRules = hideWhenRules.filter((_, i) => i !== index)
    setHideWhenRules(newRules)
    updateRules(showWhenRules, newRules, requireWhenRules)
  }

  const removeRequireWhenRule = (index: number) => {
    const newRules = requireWhenRules.filter((_, i) => i !== index)
    setRequireWhenRules(newRules)  
    updateRules(showWhenRules, hideWhenRules, newRules)
  }

  if (filteredFields.length === 0) {
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
      </div>

      {/* Show When Rules */}
      <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
        <div className="flex items-center space-x-2 mb-3">
          <Eye className="w-4 h-4 text-green-600" />
          <h5 className="font-medium text-gray-900 dark:text-white">Show this field when:</h5>
        </div>
        <div className="text-xs text-gray-500 dark:text-gray-400 mb-3">
          Field will only be visible when ALL conditions are true
        </div>
        
        <div className="space-y-2">
          {showWhenRules.map((rule, index) => (
            <RuleRow
              key={index}
              rule={rule}
              availableFields={filteredFields}
              userTypes={userTypes}
              onRuleChange={(rule) => updateShowWhenRule(index, rule)}
              onRemove={() => removeShowWhenRule(index)}
              ruleType="show_when"
            />
          ))}
        </div>
        
        <button
          onClick={addShowWhenRule}
          className="mt-3 inline-flex items-center px-3 py-1.5 text-sm text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-md transition-colors"
        >
          <Plus className="w-3 h-3 mr-1" />
          Add Show Condition
        </button>
      </div>

      {/* Hide When Rules */}
      <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
        <div className="flex items-center space-x-2 mb-3">
          <EyeOff className="w-4 h-4 text-red-600" />
          <h5 className="font-medium text-gray-900 dark:text-white">Hide this field when:</h5>
        </div>
        <div className="text-xs text-gray-500 dark:text-gray-400 mb-3">
          Field will be hidden when ANY condition is true
        </div>
        
        <div className="space-y-2">
          {hideWhenRules.map((rule, index) => (
            <RuleRow
              key={index}
              rule={rule}
              availableFields={filteredFields}
              userTypes={userTypes}
              onRuleChange={(rule) => updateHideWhenRule(index, rule)}
              onRemove={() => removeHideWhenRule(index)}
              ruleType="hide_when"
            />
          ))}
        </div>
        
        <button
          onClick={addHideWhenRule}
          className="mt-3 inline-flex items-center px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md transition-colors"
        >
          <Plus className="w-3 h-3 mr-1" />
          Add Hide Condition
        </button>
      </div>

      {/* Require When Rules */}
      <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
        <div className="flex items-center space-x-2 mb-3">
          <AlertCircle className="w-4 h-4 text-orange-600" />
          <h5 className="font-medium text-gray-900 dark:text-white">Make this field required when:</h5>
        </div>
        <div className="text-xs text-gray-500 dark:text-gray-400 mb-3">
          Field will be required when ANY condition is true
        </div>
        
        <div className="space-y-2">
          {requireWhenRules.map((rule, index) => (
            <RuleRow
              key={index}
              rule={rule}
              availableFields={filteredFields}
              userTypes={userTypes}
              onRuleChange={(rule) => updateRequireWhenRule(index, rule)}
              onRemove={() => removeRequireWhenRule(index)}
              ruleType="require_when"
            />
          ))}
        </div>
        
        <button
          onClick={addRequireWhenRule}
          className="mt-3 inline-flex items-center px-3 py-1.5 text-sm text-orange-600 hover:bg-orange-50 dark:hover:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-md transition-colors"
        >
          <Plus className="w-3 h-3 mr-1" />
          Add Required Condition
        </button>
      </div>

      {/* Summary */}
      {(showWhenRules.length > 0 || hideWhenRules.length > 0 || requireWhenRules.length > 0) && (
        <div className="bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
          <div className="text-sm font-medium text-blue-900 dark:text-blue-100 mb-2">
            Conditional Rules Summary:
          </div>
          <div className="text-xs text-blue-700 dark:text-blue-300 space-y-1">
            {showWhenRules.length > 0 && (
              <div>• {showWhenRules.length} show condition(s)</div>
            )}
            {hideWhenRules.length > 0 && (
              <div>• {hideWhenRules.length} hide condition(s)</div>
            )}
            {requireWhenRules.length > 0 && (
              <div>• {requireWhenRules.length} required condition(s)</div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}