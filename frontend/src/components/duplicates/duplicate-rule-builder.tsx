'use client'

import { useState, useEffect } from 'react'
import { 
  X, 
  Plus, 
  Trash2, 
  Settings, 
  TestTube,
  Save,
  AlertCircle,
  CheckCircle,
  Info,
  Lightbulb
} from 'lucide-react'
import { duplicatesApi, pipelinesApi } from '@/lib/api'

interface Field {
  id: string
  name: string
  display_name: string
  field_type: string
}

interface Pipeline {
  id: string
  name: string
  fields: Field[]
}

interface LogicCondition {
  field: string
  operator: 'exact_match' | 'fuzzy_match' | 'contains' | 'starts_with' | 'ends_with' | 'regex'
  threshold?: number
  value?: string
  weight?: number
}

interface RuleLogic {
  operator: 'AND' | 'OR'
  conditions: LogicCondition[]
}

interface DuplicateRuleBuilderProps {
  isOpen: boolean
  onClose: () => void
  onSave: (rule: any) => void
  pipelineId: string
  editingRule?: any
}

export function DuplicateRuleBuilder({ 
  isOpen, 
  onClose, 
  onSave, 
  pipelineId,
  editingRule 
}: DuplicateRuleBuilderProps) {
  const [pipeline, setPipeline] = useState<Pipeline | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  
  // Rule form state
  const [ruleName, setRuleName] = useState('')
  const [ruleDescription, setRuleDescription] = useState('')
  const [actionOnDuplicate, setActionOnDuplicate] = useState<'warn' | 'prevent' | 'merge' | 'flag'>('warn')
  const [isActive, setIsActive] = useState(true)
  const [logic, setLogic] = useState<RuleLogic>({
    operator: 'AND',
    conditions: []
  })
  
  const [errors, setErrors] = useState<{ [key: string]: string }>({})

  // Load pipeline data
  useEffect(() => {
    if (isOpen && pipelineId) {
      loadPipelineData()
    }
  }, [isOpen, pipelineId])

  // Load editing rule data
  useEffect(() => {
    if (editingRule && isOpen) {
      setRuleName(editingRule.name || '')
      setRuleDescription(editingRule.description || '')
      setActionOnDuplicate(editingRule.action_on_duplicate || 'warn')
      setIsActive(editingRule.is_active ?? true)
      setLogic(editingRule.logic || { operator: 'AND', conditions: [] })
    } else if (isOpen) {
      // Reset form for new rule
      setRuleName('')
      setRuleDescription('')
      setActionOnDuplicate('warn')
      setIsActive(true)
      setLogic({ operator: 'AND', conditions: [] })
    }
    setErrors({})
  }, [editingRule, isOpen])

  const loadPipelineData = async () => {
    try {
      setLoading(true)
      const response = await pipelinesApi.get(pipelineId)
      
      const transformedPipeline: Pipeline = {
        id: response.data.id?.toString() || pipelineId,
        name: response.data.name || 'Unknown Pipeline',
        fields: (response.data.fields || []).map((field: any) => ({
          id: field.id?.toString() || '',
          name: field.slug || field.name?.toLowerCase().replace(/\s+/g, '_'),
          display_name: field.name || field.display_name || field.slug || 'Unknown Field',
          field_type: field.field_type || 'text'
        }))
      }
      
      setPipeline(transformedPipeline)
    } catch (error) {
      console.error('Failed to load pipeline data:', error)
    } finally {
      setLoading(false)
    }
  }

  const addCondition = () => {
    const newCondition: LogicCondition = {
      field: '',
      operator: 'exact_match',
      weight: 1.0
    }
    setLogic({
      ...logic,
      conditions: [...logic.conditions, newCondition]
    })
  }

  const updateCondition = (index: number, updates: Partial<LogicCondition>) => {
    const newConditions = [...logic.conditions]
    newConditions[index] = { ...newConditions[index], ...updates }
    setLogic({
      ...logic,
      conditions: newConditions
    })
  }

  const removeCondition = (index: number) => {
    setLogic({
      ...logic,
      conditions: logic.conditions.filter((_, i) => i !== index)
    })
  }

  const validateForm = (): boolean => {
    const newErrors: { [key: string]: string } = {}

    if (!ruleName.trim()) {
      newErrors.ruleName = 'Rule name is required'
    }

    if (logic.conditions.length === 0) {
      newErrors.conditions = 'At least one condition is required'
    }

    logic.conditions.forEach((condition, index) => {
      if (!condition.field) {
        newErrors[`condition_${index}_field`] = 'Field is required'
      }
      if (condition.operator === 'fuzzy_match' && (!condition.threshold || condition.threshold < 0 || condition.threshold > 1)) {
        newErrors[`condition_${index}_threshold`] = 'Threshold must be between 0 and 1'
      }
      if (['contains', 'starts_with', 'ends_with', 'regex'].includes(condition.operator) && !condition.value) {
        newErrors[`condition_${index}_value`] = 'Value is required for this operator'
      }
    })

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSave = async () => {
    if (!validateForm()) {
      return
    }

    try {
      setSaving(true)

      const ruleData = {
        name: ruleName,
        description: ruleDescription,
        pipeline: parseInt(pipelineId),
        logic,
        action_on_duplicate: actionOnDuplicate,
        is_active: isActive
      }

      let savedRule
      if (editingRule) {
        savedRule = await duplicatesApi.updateDuplicateRule(editingRule.id, ruleData)
      } else {
        savedRule = await duplicatesApi.createDuplicateRule(ruleData)
      }

      onSave(savedRule.data)
      onClose()
    } catch (error: any) {
      console.error('Failed to save rule:', error)
      setErrors({
        save: error?.response?.data?.detail || error?.message || 'Failed to save rule'
      })
    } finally {
      setSaving(false)
    }
  }

  const getOperatorLabel = (operator: string) => {
    const labels = {
      exact_match: 'Exact Match',
      fuzzy_match: 'Fuzzy Match',
      contains: 'Contains',
      starts_with: 'Starts With',
      ends_with: 'Ends With',
      regex: 'Regular Expression'
    }
    return labels[operator as keyof typeof labels] || operator
  }

  const getActionLabel = (action: string) => {
    const labels = {
      warn: 'Warn Only',
      prevent: 'Prevent Creation',
      merge: 'Suggest Merge',
      flag: 'Flag for Review'
    }
    return labels[action as keyof typeof labels] || action
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg w-full max-w-4xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
              {editingRule ? 'Edit Duplicate Rule' : 'Create New Duplicate Rule'}
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Configure conditions to automatically detect duplicate records
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-500"></div>
            </div>
          ) : (
            <>
              {/* Basic Information */}
              <div className="space-y-4">
                <h4 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Basic Information
                </h4>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Rule Name *
                    </label>
                    <input
                      type="text"
                      value={ruleName}
                      onChange={(e) => setRuleName(e.target.value)}
                      placeholder="e.g., Email Duplicate Detection"
                      className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 ${
                        errors.ruleName 
                          ? 'border-red-500 dark:border-red-400' 
                          : 'border-gray-300 dark:border-gray-600'
                      } bg-white dark:bg-gray-700 text-gray-900 dark:text-white`}
                    />
                    {errors.ruleName && (
                      <p className="text-sm text-red-500 mt-1">{errors.ruleName}</p>
                    )}
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Action on Duplicate
                    </label>
                    <select
                      value={actionOnDuplicate}
                      onChange={(e) => setActionOnDuplicate(e.target.value as any)}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    >
                      <option value="warn">Warn Only</option>
                      <option value="prevent">Prevent Creation</option>
                      <option value="merge">Suggest Merge</option>
                      <option value="flag">Flag for Review</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Description
                  </label>
                  <textarea
                    value={ruleDescription}
                    onChange={(e) => setRuleDescription(e.target.value)}
                    placeholder="Describe what this rule detects..."
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                </div>

                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="isActive"
                    checked={isActive}
                    onChange={(e) => setIsActive(e.target.checked)}
                    className="w-4 h-4 text-orange-600 bg-gray-100 border-gray-300 rounded focus:ring-orange-500 dark:focus:ring-orange-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
                  />
                  <label htmlFor="isActive" className="ml-2 text-sm font-medium text-gray-700 dark:text-gray-300">
                    Active (rule will run automatically)
                  </label>
                </div>
              </div>

              {/* Logic Builder */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="text-lg font-semibold text-gray-900 dark:text-white">
                    Detection Logic
                  </h4>
                  <div className="flex items-center space-x-2">
                    <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Logic Operator:
                    </label>
                    <select
                      value={logic.operator}
                      onChange={(e) => setLogic({ ...logic, operator: e.target.value as 'AND' | 'OR' })}
                      className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
                    >
                      <option value="AND">AND (all conditions must match)</option>
                      <option value="OR">OR (any condition can match)</option>
                    </select>
                  </div>
                </div>

                {/* Info Box */}
                <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                  <div className="flex items-start space-x-2">
                    <Info className="w-5 h-5 text-blue-500 mt-0.5" />
                    <div>
                      <h5 className="text-sm font-semibold text-blue-800 dark:text-blue-300">
                        How Detection Logic Works
                      </h5>
                      <p className="text-sm text-blue-700 dark:text-blue-400 mt-1">
                        {logic.operator === 'AND' 
                          ? 'Records are marked as duplicates only if ALL conditions are met.'
                          : 'Records are marked as duplicates if ANY of the conditions are met.'
                        }
                      </p>
                    </div>
                  </div>
                </div>

                {/* Conditions */}
                <div className="space-y-3">
                  {logic.conditions.map((condition, index) => (
                    <div key={index} className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                          Condition {index + 1}
                        </span>
                        <button
                          onClick={() => removeCondition(index)}
                          className="text-red-500 hover:text-red-700 p-1"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                        {/* Field Selection */}
                        <div>
                          <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                            Field *
                          </label>
                          <select
                            value={condition.field}
                            onChange={(e) => updateCondition(index, { field: e.target.value })}
                            className={`w-full px-3 py-2 text-sm border rounded-md focus:ring-2 focus:ring-orange-500 focus:border-orange-500 ${
                              errors[`condition_${index}_field`] 
                                ? 'border-red-500 dark:border-red-400' 
                                : 'border-gray-300 dark:border-gray-600'
                            } bg-white dark:bg-gray-800 text-gray-900 dark:text-white`}
                          >
                            <option value="">Select field</option>
                            {pipeline?.fields.map((field) => (
                              <option key={field.id} value={field.name}>
                                {field.display_name} ({field.field_type})
                              </option>
                            ))}
                          </select>
                          {errors[`condition_${index}_field`] && (
                            <p className="text-xs text-red-500 mt-1">{errors[`condition_${index}_field`]}</p>
                          )}
                        </div>

                        {/* Operator Selection */}
                        <div>
                          <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                            Operator
                          </label>
                          <select
                            value={condition.operator}
                            onChange={(e) => updateCondition(index, { operator: e.target.value as any })}
                            className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md focus:ring-2 focus:ring-orange-500 focus:border-orange-500 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                          >
                            <option value="exact_match">Exact Match</option>
                            <option value="fuzzy_match">Fuzzy Match</option>
                            <option value="contains">Contains</option>
                            <option value="starts_with">Starts With</option>
                            <option value="ends_with">Ends With</option>
                            <option value="regex">Regular Expression</option>
                          </select>
                        </div>

                        {/* Threshold (for fuzzy match) */}
                        {condition.operator === 'fuzzy_match' && (
                          <div>
                            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                              Threshold (0-1)
                            </label>
                            <input
                              type="number"
                              min="0"
                              max="1"
                              step="0.1"
                              value={condition.threshold || 0.8}
                              onChange={(e) => updateCondition(index, { threshold: parseFloat(e.target.value) })}
                              className={`w-full px-3 py-2 text-sm border rounded-md focus:ring-2 focus:ring-orange-500 focus:border-orange-500 ${
                                errors[`condition_${index}_threshold`] 
                                  ? 'border-red-500 dark:border-red-400' 
                                  : 'border-gray-300 dark:border-gray-600'
                              } bg-white dark:bg-gray-800 text-gray-900 dark:text-white`}
                            />
                            {errors[`condition_${index}_threshold`] && (
                              <p className="text-xs text-red-500 mt-1">{errors[`condition_${index}_threshold`]}</p>
                            )}
                          </div>
                        )}

                        {/* Value (for specific operators) */}
                        {['contains', 'starts_with', 'ends_with', 'regex'].includes(condition.operator) && (
                          <div>
                            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                              Value *
                            </label>
                            <input
                              type="text"
                              value={condition.value || ''}
                              onChange={(e) => updateCondition(index, { value: e.target.value })}
                              placeholder={condition.operator === 'regex' ? 'Enter regex pattern' : 'Enter value'}
                              className={`w-full px-3 py-2 text-sm border rounded-md focus:ring-2 focus:ring-orange-500 focus:border-orange-500 ${
                                errors[`condition_${index}_value`] 
                                  ? 'border-red-500 dark:border-red-400' 
                                  : 'border-gray-300 dark:border-gray-600'
                              } bg-white dark:bg-gray-800 text-gray-900 dark:text-white`}
                            />
                            {errors[`condition_${index}_value`] && (
                              <p className="text-xs text-red-500 mt-1">{errors[`condition_${index}_value`]}</p>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}

                  {/* Add Condition Button */}
                  <button
                    onClick={addCondition}
                    className="w-full py-3 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg hover:border-orange-500 hover:bg-orange-50 dark:hover:bg-orange-900/20 flex items-center justify-center space-x-2 text-gray-600 dark:text-gray-400 hover:text-orange-600 dark:hover:text-orange-400"
                  >
                    <Plus className="w-4 h-4" />
                    <span>Add Condition</span>
                  </button>

                  {errors.conditions && (
                    <p className="text-sm text-red-500">{errors.conditions}</p>
                  )}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-gray-200 dark:border-gray-700 p-6">
          {errors.save && (
            <div className="mb-4 flex items-center space-x-2 text-red-600 dark:text-red-400">
              <AlertCircle className="w-4 h-4" />
              <span className="text-sm">{errors.save}</span>
            </div>
          )}
          
          <div className="flex items-center justify-end space-x-3">
            <button
              onClick={onClose}
              disabled={saving}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving || loading}
              className="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
            >
              {saving ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  <span>Saving...</span>
                </>
              ) : (
                <>
                  <Save className="w-4 h-4" />
                  <span>{editingRule ? 'Update Rule' : 'Create Rule'}</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}