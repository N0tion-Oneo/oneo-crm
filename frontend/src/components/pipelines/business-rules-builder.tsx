'use client'

import React, { useState, useEffect } from 'react'
import { Save, AlertCircle, Target, Eye, EyeOff, Lock, Unlock, Shield, MessageSquare, Settings, ChevronDown, ChevronRight, CheckCircle, Copy, Check } from 'lucide-react'
import { pipelinesApi } from '@/lib/api'
import { usePermissions } from '@/hooks/usePermissions'
import { PermissionGuard, PermissionButton } from '@/components/permissions/PermissionGuard'

interface PipelineField {
  id: string
  name: string
  display_name?: string
  field_type: string
  field_config?: Record<string, any>
  config?: Record<string, any> // Legacy support
  business_rules?: {
    stage_requirements?: Record<string, { 
      required: boolean
      block_transitions?: boolean
      show_warnings?: boolean
      warning_message?: string
    }>
    user_visibility?: Record<string, { visible: boolean; editable: boolean }>
  }
}

interface Pipeline {
  id: string
  name: string
  description: string
  access_level?: string
  fields: PipelineField[]
  stages: string[]
}

const USER_TYPES = [
  { key: 'admin', label: 'Admin' },
  { key: 'manager', label: 'Manager' },
  { key: 'user', label: 'User' },
  { key: 'viewer', label: 'Viewer' }
]

interface BusinessRulesBuilderProps {
  pipelineId: string
  pipeline?: Pipeline
  onPipelineChange?: (pipeline: Pipeline) => void
}

// Access Denied component for business rules
const BusinessRulesAccessDenied = () => (
  <div className="flex items-center justify-center h-64">
    <div className="text-center max-w-md">
      <Shield className="w-12 h-12 text-red-500 mx-auto mb-4" />
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
        Access Denied
      </h2>
      <p className="text-gray-600 dark:text-gray-400 mb-4">
        You don't have permission to view business rules configuration. Please contact your administrator to request access.
      </p>
      <div className="bg-red-50 dark:bg-red-950/30 rounded-lg p-3">
        <p className="text-sm text-red-700 dark:text-red-300">
          Required permission: <code className="bg-red-100 dark:bg-red-900/50 px-1 rounded">business_rules.read</code>
        </p>
      </div>
    </div>
  </div>
)

export function BusinessRulesBuilder({ 
  pipelineId, 
  pipeline: initialPipeline,
  onPipelineChange 
}: BusinessRulesBuilderProps) {
  const [pipeline, setPipeline] = useState<Pipeline | null>(initialPipeline || null)
  const [loading, setLoading] = useState(!initialPipeline)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [hasChanges, setHasChanges] = useState(false)
  const [selectedStageField, setSelectedStageField] = useState<string>('')
  const [stageOptions, setStageOptions] = useState<string[]>([])
  const [expandedFieldStages, setExpandedFieldStages] = useState<Set<string>>(new Set())
  const [showFormSettings, setShowFormSettings] = useState(false)
  const [showFullFormSettings, setShowFullFormSettings] = useState(false)
  const [copiedUrls, setCopiedUrls] = useState<Set<string>>(new Set())

  // Permission checks
  const permissions = usePermissions()
  const canUpdateBusinessRules = permissions.canUpdateBusinessRules()

  // Helper function to get current tenant information
  const getCurrentTenant = () => {
    if (typeof window !== 'undefined') {
      const hostname = window.location.hostname
      if (hostname.includes('.localhost')) {
        const subdomain = hostname.split('.')[0]
        return subdomain === 'localhost' ? 'demo' : subdomain
      }
      // For production domains
      return hostname.split('.')[0] || 'demo'
    }
    return 'demo'
  }

  // Helper function to copy URL to clipboard
  const copyToClipboard = async (url: string, identifier: string) => {
    try {
      await navigator.clipboard.writeText(url)
      setCopiedUrls(prev => new Set([...prev, identifier]))
      setTimeout(() => {
        setCopiedUrls(prev => {
          const newSet = new Set(prev)
          newSet.delete(identifier)
          return newSet
        })
      }, 2000)
    } catch (err) {
      console.error('Failed to copy URL:', err)
    }
  }

  // Load pipeline data if not provided
  useEffect(() => {
    const loadPipeline = async () => {
      if (initialPipeline) return
      
      try {
        setLoading(true)
        setError(null)
        
        const response = await pipelinesApi.get(pipelineId)
        
        console.log('📊 Pipeline data from API:', {
          id: response.data.id,
          name: response.data.name,
          access_level: response.data.access_level,
          rawData: response.data
        })
        
        const transformedPipeline: Pipeline = {
          id: response.data.id?.toString() || pipelineId,
          name: response.data.name || 'Unknown Pipeline',
          description: response.data.description || '',
          access_level: response.data.access_level || 'internal',
          stages: response.data.stages || ['discovery', 'qualification', 'proposal', 'negotiation', 'closed'],
          fields: (response.data.fields || []).map((field: any) => ({
            id: field.id?.toString() || `field_${Date.now()}`,
            name: field.slug || field.name?.toLowerCase().replace(/\s+/g, '_'),
            display_name: field.name || field.display_name || field.slug,
            field_type: field.field_type || 'text',
            field_config: field.field_config || {},
            config: field.config || {}, // Legacy support
            business_rules: field.business_rules || {
              stage_requirements: {},
              user_visibility: {}
            }
          }))
        }
        
        setPipeline(transformedPipeline)
        if (onPipelineChange) {
          onPipelineChange(transformedPipeline)
        }
      } catch (error: any) {
        console.error('Failed to load pipeline:', error)
        setError(error.response?.data?.message || 'Failed to load pipeline data')
      } finally {
        setLoading(false)
      }
    }

    if (pipelineId && !initialPipeline) {
      loadPipeline()
    }
  }, [pipelineId, initialPipeline, onPipelineChange])

  // Handle stage field selection
  const handleStageFieldChange = (fieldName: string) => {
    setSelectedStageField(fieldName)
    
    if (fieldName) {
      const stageField = pipeline?.fields.find(f => f.name === fieldName)
      
      // Try multiple possible locations for options (field_config.options, config.options)
      let optionsArray = stageField?.field_config?.options || stageField?.config?.options || []
      
      if (optionsArray && optionsArray.length > 0) {
        const extractedOptions = optionsArray.map((opt: any) => {
          // Handle different option formats
          if (typeof opt === 'string') return opt
          // Prefer value over label for stage matching
          return opt.value || opt.label || opt
        }).filter(Boolean) // Remove any empty/null values
        
        setStageOptions(extractedOptions)
      } else {
        setStageOptions([])
      }
    } else {
      setStageOptions([])
    }
  }

  // Get select fields (excluding the selected stage field)
  const getSelectFields = () => {
    if (!pipeline) return []
    return pipeline.fields.filter(field => 
      (field.field_type === 'select' || field.field_type === 'multiselect')
    )
  }

  // Handle stage requirement change
  const handleStageRequirementChange = (fieldId: string, stage: string, required: boolean) => {
    if (!pipeline) return

    const updatedFields = pipeline.fields.map(field => {
      if (field.id === fieldId) {
        return {
          ...field,
          business_rules: {
            ...field.business_rules,
            stage_requirements: {
              ...field.business_rules?.stage_requirements,
              [stage]: { required }
            }
          }
        }
      }
      return field
    })

    const updatedPipeline = { ...pipeline, fields: updatedFields }
    setPipeline(updatedPipeline)
    setHasChanges(true)
    
    if (onPipelineChange) {
      onPipelineChange(updatedPipeline)
    }
  }

  // Handle user visibility change
  const handleUserVisibilityChange = (fieldId: string, userType: string, property: 'visible' | 'editable', value: boolean) => {
    if (!pipeline) return

    const updatedFields = pipeline.fields.map(field => {
      if (field.id === fieldId) {
        const currentVisibility = field.business_rules?.user_visibility?.[userType] || { visible: true, editable: true }
        
        return {
          ...field,
          business_rules: {
            ...field.business_rules,
            user_visibility: {
              ...field.business_rules?.user_visibility,
              [userType]: {
                ...currentVisibility,
                [property]: value
              }
            }
          }
        }
      }
      return field
    })

    const updatedPipeline = { ...pipeline, fields: updatedFields }
    setPipeline(updatedPipeline)
    setHasChanges(true)
    
    if (onPipelineChange) {
      onPipelineChange(updatedPipeline)
    }
  }

  // Toggle field-stage expansion
  const toggleFieldStageExpansion = (fieldId: string, stage: string) => {
    const key = `${fieldId}-${stage}`
    const newExpanded = new Set(expandedFieldStages)
    if (newExpanded.has(key)) {
      newExpanded.delete(key)
    } else {
      newExpanded.add(key)
    }
    setExpandedFieldStages(newExpanded)
  }

  // Check if field-stage has advanced rules configured
  const hasAdvancedRulesForStage = (field: PipelineField, stage: string) => {
    const stageReq = field.business_rules?.stage_requirements?.[stage]
    return stageReq?.warning_message || 
           stageReq?.block_transitions === false || 
           stageReq?.show_warnings === false
  }

  // Handle stage-specific business rule change
  const handleStageBusinessRuleChange = (fieldId: string, stage: string, property: 'block_transitions' | 'show_warnings' | 'warning_message', value: boolean | string) => {
    if (!pipeline) return

    const updatedFields = pipeline.fields.map(field => {
      if (field.id === fieldId) {
        const currentStageReq = field.business_rules?.stage_requirements?.[stage] || { required: false }
        
        return {
          ...field,
          business_rules: {
            ...field.business_rules,
            stage_requirements: {
              ...field.business_rules?.stage_requirements,
              [stage]: {
                ...currentStageReq,
                [property]: value
              }
            }
          }
        }
      }
      return field
    })

    const updatedPipeline = { ...pipeline, fields: updatedFields }
    setPipeline(updatedPipeline)
    setHasChanges(true)
    
    if (onPipelineChange) {
      onPipelineChange(updatedPipeline)
    }
  }


  // Save changes
  const handleSave = async () => {
    if (!pipeline || !hasChanges) return

    try {
      setSaving(true)
      setError(null)

      // Update each field's business rules
      for (const field of pipeline.fields) {
        await pipelinesApi.updateField(pipelineId, field.id, {
          business_rules: field.business_rules
        })
      }

      setHasChanges(false)
    } catch (error: any) {
      console.error('Failed to save business rules:', error)
      setError(error.response?.data?.message || 'Failed to save changes')
    } finally {
      setSaving(false)
    }
  }

  // Toggle public forms access
  const handleTogglePublicForms = async () => {
    if (!pipeline) return

    try {
      setSaving(true)
      setError(null)

      const newAccessLevel = pipeline.access_level === 'public' ? 'internal' : 'public'
      
      console.log('🔄 Toggling public forms:', {
        pipelineId,
        currentAccessLevel: pipeline.access_level,
        newAccessLevel,
        updateData: { access_level: newAccessLevel }
      })
      
      const response = await pipelinesApi.update(pipelineId, {
        access_level: newAccessLevel
      })

      console.log('✅ API Response:', response.data)

      const updatedPipeline = {
        ...pipeline,
        access_level: newAccessLevel
      }
      
      setPipeline(updatedPipeline)
      if (onPipelineChange) {
        onPipelineChange(updatedPipeline)
      }
      
      console.log('✅ Local state updated:', updatedPipeline)
    } catch (error: any) {
      console.error('❌ Failed to toggle public forms:', error)
      setError(error.response?.data?.message || 'Failed to update access level')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400">Loading business rules...</p>
        </div>
      </div>
    )
  }


  if (error && !pipeline) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center max-w-md">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            Failed to Load Business Rules
          </h2>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            {error}
          </p>
        </div>
      </div>
    )
  }

  if (!pipeline) {
    return null
  }

  return (
    <PermissionGuard 
      category="business_rules" 
      action="read"
      fallback={<BusinessRulesAccessDenied />}
    >
      <div className="space-y-8">
      {/* Permission Notice - Show for read-only users */}
      {!canUpdateBusinessRules && (
        <div className="bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
          <div className="flex items-start space-x-3">
            <Shield className="w-5 h-5 text-amber-600 dark:text-amber-400 mt-0.5 flex-shrink-0" />
            <div>
              <h3 className="text-sm font-semibold text-amber-800 dark:text-amber-200 mb-1">
                Read-Only Access
              </h3>
              <p className="text-sm text-amber-700 dark:text-amber-300">
                You have read-only access to business rules configuration. To make changes, you need <code className="bg-amber-100 dark:bg-amber-900/50 px-1 rounded text-xs">business_rules.update</code> permission. 
                Contact your administrator to request additional permissions.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Save Actions Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Configure Business Rules
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Set field requirements by stage and control user access permissions
          </p>
        </div>

        <div className="flex items-center space-x-4">
          {/* Save Status Indicator */}
          <div className="flex items-center space-x-2">
            {hasChanges ? (
              <div className="flex items-center space-x-2 px-3 py-1.5 bg-orange-50 dark:bg-orange-900/20 text-orange-700 dark:text-orange-300 rounded-full text-sm font-medium border border-orange-200 dark:border-orange-800">
                <div className="w-2 h-2 bg-orange-500 rounded-full animate-pulse"></div>
                <span>Unsaved changes</span>
              </div>
            ) : (
              <div className="flex items-center space-x-2 px-3 py-1.5 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 rounded-full text-sm font-medium border border-green-200 dark:border-green-800">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <span>All changes saved</span>
              </div>
            )}
          </div>

          {error && (
            <div className="flex items-center text-red-600 dark:text-red-400 text-sm">
              <AlertCircle className="w-4 h-4 mr-1" />
              {error}
            </div>
          )}
          
          {/* Save Button */}
          <button
            onClick={handleSave}
            disabled={!hasChanges || saving || !canUpdateBusinessRules}
            className={`inline-flex items-center px-6 py-2.5 border border-transparent text-sm font-medium rounded-lg shadow-sm transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 ${
              hasChanges && !saving && canUpdateBusinessRules
                ? 'text-white bg-purple-500 hover:bg-purple-600 hover:shadow-lg transform hover:-translate-y-0.5'
                : 'text-gray-500 bg-gray-100 dark:bg-gray-700 dark:text-gray-400 cursor-not-allowed'
            }`}
            title={!canUpdateBusinessRules ? 'You need business_rules.update permission to save changes' : ''}
          >
            {saving ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4 mr-2" />
                {!canUpdateBusinessRules ? 'Read Only' : hasChanges ? 'Save Changes' : 'Saved'}
              </>
            )}
          </button>
        </div>
      </div>

      {/* Stage Requirements Section */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Stage Requirements
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            Configure which fields are required at each pipeline stage
          </p>
          
          {/* Stage Field Selector */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Select Stage Field
            </label>
            <select
              value={selectedStageField}
              onChange={(e) => handleStageFieldChange(e.target.value)}
              disabled={!canUpdateBusinessRules}
              className="w-full max-w-md px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <option value="">Select which field represents stages...</option>
              {getSelectFields().map(field => (
                <option key={field.id} value={field.name}>
                  {field.display_name} ({field.field_type})
                </option>
              ))}
            </select>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Choose which select field defines the stages in your pipeline
            </p>
          </div>
        </div>

        {selectedStageField && stageOptions.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">
                    Field
                  </th>
                  {stageOptions.map(stage => (
                    <th key={stage} className="text-center py-3 px-4 font-medium text-gray-900 dark:text-white">
                      {typeof stage === 'string' ? stage.charAt(0).toUpperCase() + stage.slice(1) : stage}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {pipeline.fields
                  .filter(field => field.name !== selectedStageField) // Exclude the selected stage field
                  .map(field => (
                    <React.Fragment key={field.id}>
                      {/* Main field row */}
                      <tr className="border-b border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50">
                        <td className="py-3 px-4">
                          <div className="flex items-center space-x-2">
                            <div>
                              <div className="font-medium text-gray-900 dark:text-white">
                                {field.display_name}
                              </div>
                              <div className="text-xs text-gray-500 dark:text-gray-400">
                                {field.field_type}
                              </div>
                            </div>
                          </div>
                        </td>
                        {stageOptions.map(stage => (
                          <td key={stage} className="py-3 px-4 text-center">
                            <div className="flex flex-col items-center space-y-2">
                              <div className="flex items-center space-x-2">
                                <input
                                  type="checkbox"
                                  checked={field.business_rules?.stage_requirements?.[stage]?.required || false}
                                  onChange={(e) => handleStageRequirementChange(field.id, stage, e.target.checked)}
                                  disabled={!canUpdateBusinessRules}
                                  className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
                                />
                                {hasAdvancedRulesForStage(field, stage) && (
                                  <div className="w-2 h-2 bg-blue-500 rounded-full" title="Has advanced rules configured"></div>
                                )}
                              </div>
                              
                              {field.business_rules?.stage_requirements?.[stage]?.required && (
                                <button
                                  onClick={() => toggleFieldStageExpansion(field.id, stage)}
                                  className={`inline-flex items-center px-1 py-0.5 text-xs font-medium rounded transition-colors ${
                                    expandedFieldStages.has(`${field.id}-${stage}`)
                                      ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300'
                                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-400 dark:hover:bg-gray-600'
                                  }`}
                                >
                                  {expandedFieldStages.has(`${field.id}-${stage}`) ? (
                                    <ChevronDown className="w-3 h-3" />
                                  ) : (
                                    <Settings className="w-3 h-3" />
                                  )}
                                </button>
                              )}
                            </div>
                          </td>
                        ))}
                      </tr>
                      
                      {/* Expandable advanced settings rows for each stage */}
                      {stageOptions.map(stage => (
                        expandedFieldStages.has(`${field.id}-${stage}`) && field.business_rules?.stage_requirements?.[stage]?.required && (
                          <tr key={`${field.id}-${stage}-advanced`} className="bg-blue-50 dark:bg-blue-900/10">
                            <td className="py-3 px-4">
                              <div className="text-sm text-gray-600 dark:text-gray-400 pl-4">
                                └ {field.display_name} in {stage.charAt(0).toUpperCase() + stage.slice(1)}
                              </div>
                            </td>
                            <td colSpan={stageOptions.length} className="py-3 px-4">
                              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-3">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                  <div className="flex items-center justify-between">
                                    <div>
                                      <div className="text-sm font-medium text-gray-900 dark:text-white">Block Stage Transitions</div>
                                      <div className="text-xs text-gray-500 dark:text-gray-400">Prevent moving from {stage} if field is empty</div>
                                    </div>
                                    <input
                                      type="checkbox"
                                      checked={field.business_rules?.stage_requirements?.[stage]?.block_transitions !== false}
                                      onChange={(e) => handleStageBusinessRuleChange(field.id, stage, 'block_transitions', e.target.checked)}
                                      className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
                                    />
                                  </div>

                                  <div className="flex items-center justify-between">
                                    <div>
                                      <div className="text-sm font-medium text-gray-900 dark:text-white">Show Warnings</div>
                                      <div className="text-xs text-gray-500 dark:text-gray-400">Display warning messages</div>
                                    </div>
                                    <input
                                      type="checkbox"
                                      checked={field.business_rules?.stage_requirements?.[stage]?.show_warnings !== false}
                                      onChange={(e) => handleStageBusinessRuleChange(field.id, stage, 'show_warnings', e.target.checked)}
                                      className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
                                    />
                                  </div>
                                </div>

                                <div className="mt-3">
                                  <label className="flex items-center space-x-2 text-sm font-medium text-gray-900 dark:text-white mb-2">
                                    <MessageSquare className="w-4 h-4" />
                                    <span>Custom Warning Message for {stage.charAt(0).toUpperCase() + stage.slice(1)}</span>
                                  </label>
                                  <input
                                    type="text"
                                    value={field.business_rules?.stage_requirements?.[stage]?.warning_message || ''}
                                    onChange={(e) => handleStageBusinessRuleChange(field.id, stage, 'warning_message', e.target.value)}
                                    placeholder={`This field is required to progress from ${stage}`}
                                    className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                                  />
                                </div>
                              </div>
                            </td>
                          </tr>
                        )
                      ))}
                    </React.Fragment>
                  ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-8 text-center bg-gray-50 dark:bg-gray-800 rounded-lg">
            <div className="text-gray-500 dark:text-gray-400">
              {selectedStageField ? (
                <div>
                  <p className="mb-2">No stage options found for the selected field.</p>
                  <p className="text-sm">Make sure the selected field has options configured.</p>
                </div>
              ) : (
                <div>
                  <p className="mb-2">Select a stage field to configure requirements.</p>
                  <p className="text-sm">Choose which select field represents the stages in your pipeline.</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>


      {/* User Visibility Section */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Field Visibility by User Type
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Control which user types can see and edit each field
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                <th className="text-left py-3 px-4 font-medium text-gray-900 dark:text-white">
                  Field
                </th>
                {USER_TYPES.map(userType => (
                  <th key={userType.key} className="text-center py-3 px-4 font-medium text-gray-900 dark:text-white">
                    <div>{userType.label}</div>
                    <div className="text-xs font-normal text-gray-500 dark:text-gray-400 mt-1">
                      Visible / Editable
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {pipeline.fields
                .filter(field => field.name !== selectedStageField) // Exclude the selected stage field
                .map(field => (
                <tr key={field.id} className="border-b border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="py-3 px-4">
                    <div>
                      <div className="font-medium text-gray-900 dark:text-white">
                        {field.display_name}
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        {field.field_type}
                      </div>
                    </div>
                  </td>
                  {USER_TYPES.map(userType => {
                    const visibility = field.business_rules?.user_visibility?.[userType.key] || { visible: true, editable: true }
                    
                    return (
                      <td key={userType.key} className="py-3 px-4 text-center">
                        <div className="flex items-center justify-center space-x-3">
                          {/* Visible toggle */}
                          <button
                            onClick={() => handleUserVisibilityChange(field.id, userType.key, 'visible', !visibility.visible)}
                            className={`p-1 rounded ${
                              visibility.visible 
                                ? 'text-green-600 hover:bg-green-100 dark:hover:bg-green-900/20' 
                                : 'text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                            }`}
                            title={visibility.visible ? 'Visible' : 'Hidden'}
                          >
                            {visibility.visible ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                          </button>
                          
                          {/* Editable toggle */}
                          <button
                            onClick={() => handleUserVisibilityChange(field.id, userType.key, 'editable', !visibility.editable)}
                            disabled={!visibility.visible}
                            className={`p-1 rounded ${
                              !visibility.visible
                                ? 'text-gray-300 cursor-not-allowed'
                                : visibility.editable 
                                  ? 'text-blue-600 hover:bg-blue-100 dark:hover:bg-blue-900/20' 
                                  : 'text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                            }`}
                            title={visibility.editable ? 'Editable' : 'Read-only'}
                          >
                            {visibility.editable ? <Unlock className="w-4 h-4" /> : <Lock className="w-4 h-4" />}
                          </button>
                        </div>
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Enhanced Full Pipeline Forms Section */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        {/* Header with gradient background */}
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950/50 dark:to-indigo-950/50 px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/50 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Pipeline Forms Management
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Access complete forms that include all fields in the pipeline
              </p>
            </div>
          </div>
        </div>

        <div className="p-6 space-y-6">
          {/* Public Forms Access Control - Featured Card */}
          <div className={`rounded-xl p-6 border-2 transition-all duration-200 ${
            pipeline?.access_level === 'public' 
              ? 'bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-950/30 dark:to-emerald-950/30 border-green-200 dark:border-green-800' 
              : 'bg-gradient-to-br from-orange-50 to-red-50 dark:from-orange-950/30 dark:to-red-950/30 border-orange-200 dark:border-orange-800'
          }`}>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-3">
                <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                  pipeline?.access_level === 'public' 
                    ? 'bg-green-100 dark:bg-green-900/50' 
                    : 'bg-orange-100 dark:bg-orange-900/50'
                }`}>
                  <Shield className={`w-6 h-6 ${
                    pipeline?.access_level === 'public' 
                      ? 'text-green-600 dark:text-green-400' 
                      : 'text-orange-600 dark:text-orange-400'
                  }`} />
                </div>
                <div>
                  <h4 className={`text-lg font-semibold ${
                    pipeline?.access_level === 'public' 
                      ? 'text-green-900 dark:text-green-100' 
                      : 'text-orange-900 dark:text-orange-100'
                  }`}>
                    Public Forms Access
                  </h4>
                  <p className={`text-sm ${
                    pipeline?.access_level === 'public' 
                      ? 'text-green-700 dark:text-green-300' 
                      : 'text-orange-700 dark:text-orange-300'
                  }`}>
                    {pipeline?.access_level === 'public' 
                      ? 'Anonymous users can submit forms'
                      : 'Only authenticated users can access forms'
                    }
                  </p>
                </div>
              </div>
              <div className="flex items-center space-x-3">
                <div className="text-right">
                  <div className={`text-sm font-medium ${
                    pipeline?.access_level === 'public' 
                      ? 'text-green-600 dark:text-green-400' 
                      : 'text-gray-500 dark:text-gray-400'
                  }`}>
                    {pipeline?.access_level === 'public' ? 'Enabled' : 'Disabled'}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    Public Access
                  </div>
                </div>
                <button
                  onClick={handleTogglePublicForms}
                  disabled={saving || !permissions.canUpdatePipelines()}
                  className={`relative inline-flex h-8 w-14 items-center rounded-full transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 ${
                    pipeline?.access_level === 'public'
                      ? 'bg-green-500 focus:ring-green-500 shadow-lg shadow-green-500/25'
                      : 'bg-gray-300 dark:bg-gray-600 focus:ring-gray-500'
                  } ${saving || !permissions.canUpdatePipelines() ? 'opacity-50 cursor-not-allowed' : 'hover:scale-105'}`}
                  title={!permissions.canUpdatePipelines() ? 'You need pipelines.update permission to modify access level' : ''}
                >
                  <span
                    className={`inline-block h-6 w-6 transform rounded-full bg-white transition-transform duration-200 shadow-lg ${
                      pipeline?.access_level === 'public' ? 'translate-x-7' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>
            </div>
            
            <div className={`p-4 rounded-lg ${
              pipeline?.access_level === 'public' 
                ? 'bg-green-100/50 dark:bg-green-900/20' 
                : 'bg-orange-100/50 dark:bg-orange-900/20'
            }`}>
              <div className="flex items-start space-x-2">
                <div className={`mt-0.5 ${
                  pipeline?.access_level === 'public' 
                    ? 'text-green-600 dark:text-green-400' 
                    : 'text-orange-600 dark:text-orange-400'
                }`}>
                  {pipeline?.access_level === 'public' ? '✅' : '🔒'}
                </div>
                <div>
                  <p className={`text-sm font-medium ${
                    pipeline?.access_level === 'public' 
                      ? 'text-green-800 dark:text-green-200' 
                      : 'text-orange-800 dark:text-orange-200'
                  }`}>
                    {pipeline?.access_level === 'public' 
                      ? 'Public forms are active and accessible to anyone'
                      : 'Public forms are disabled for security'
                    }
                  </p>
                  <p className={`text-xs mt-1 ${
                    pipeline?.access_level === 'public' 
                      ? 'text-green-700 dark:text-green-300' 
                      : 'text-orange-700 dark:text-orange-300'
                  }`}>
                    Field visibility is controlled individually in the Pipeline Builder. 
                    Only fields marked as "visible in public forms" will appear to anonymous users.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Form Access Buttons - Enhanced Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Public Form Card */}
            <div className={`group relative rounded-xl p-6 border-2 transition-all duration-200 ${
              pipeline?.access_level === 'public'
                ? 'bg-gradient-to-br from-green-50 to-green-100 dark:from-green-950/30 dark:to-green-900/30 border-green-200 dark:border-green-700 hover:shadow-lg hover:shadow-green-500/20'
                : 'bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700'
            }`}>
              <div className="flex items-center space-x-3 mb-4">
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                  pipeline?.access_level === 'public'
                    ? 'bg-green-100 dark:bg-green-900/50'
                    : 'bg-gray-100 dark:bg-gray-700'
                }`}>
                  <svg className={`w-5 h-5 ${
                    pipeline?.access_level === 'public'
                      ? 'text-green-600 dark:text-green-400'
                      : 'text-gray-400'
                  }`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9v-9m0 9c0 5-4 9-9 9s-9-4-9-9m9 9v-9" />
                  </svg>
                </div>
                <div>
                  <h4 className={`font-semibold ${
                    pipeline?.access_level === 'public'
                      ? 'text-green-900 dark:text-green-100'
                      : 'text-gray-500 dark:text-gray-400'
                  }`}>
                    Public Form
                  </h4>
                  <p className={`text-sm ${
                    pipeline?.access_level === 'public'
                      ? 'text-green-700 dark:text-green-300'
                      : 'text-gray-500 dark:text-gray-400'
                  }`}>
                    Anonymous access
                  </p>
                </div>
              </div>
              
              <div className="space-y-3">
                {/* Tenant-aware URL display */}
                <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-medium text-gray-700 dark:text-gray-300">Full URL:</span>
                    <button
                      onClick={() => {
                        const currentTenant = getCurrentTenant()
                        const pipelineSlug = pipeline?.name?.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '') || pipeline?.id
                        const fullUrl = `http://${currentTenant}.localhost:3000/forms/${pipelineSlug}`
                        copyToClipboard(fullUrl, `public-full-${pipeline?.id}`)
                      }}
                      className={`inline-flex items-center px-2 py-1 text-xs rounded transition-colors ${
                        copiedUrls.has(`public-full-${pipeline?.id}`)
                          ? 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400'
                          : 'bg-gray-100 hover:bg-gray-200 text-gray-600 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-gray-400'
                      }`}
                    >
                      {copiedUrls.has(`public-full-${pipeline?.id}`) ? (
                        <Check className="w-3 h-3" />
                      ) : (
                        <Copy className="w-3 h-3" />
                      )}
                    </button>
                  </div>
                  <code className="text-xs text-green-600 dark:text-green-400 break-all">
                    http://{getCurrentTenant()}.localhost:3000/forms/{pipeline?.name?.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '') || pipeline?.id}
                  </code>
                </div>
                
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => {
                      if (pipeline?.access_level !== 'public') {
                        alert('Public forms are disabled. Enable them using the toggle above to test the public form.')
                        return
                      }
                      const pipelineSlug = pipeline?.name?.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '') || pipeline?.id
                      window.open(`/forms/${pipelineSlug}`, '_blank')
                    }}
                    disabled={pipeline?.access_level !== 'public'}
                    className={`inline-flex items-center justify-center px-3 py-2 text-sm font-medium rounded-lg transition-all duration-200 ${
                      pipeline?.access_level === 'public'
                        ? 'bg-green-500 text-white hover:bg-green-600 hover:scale-105 shadow-lg shadow-green-500/25'
                        : 'bg-gray-300 dark:bg-gray-600 text-gray-500 dark:text-gray-400 cursor-not-allowed'
                    }`}
                  >
                    <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-1M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                    Open
                  </button>
                  
                  <button
                    onClick={() => {
                      const currentTenant = getCurrentTenant()
                      const pipelineSlug = pipeline?.name?.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '') || pipeline?.id
                      const fullUrl = `http://${currentTenant}.localhost:3000/forms/${pipelineSlug}`
                      copyToClipboard(fullUrl, `public-copy-${pipeline?.id}`)
                    }}
                    className={`inline-flex items-center justify-center px-3 py-2 text-sm font-medium rounded-lg transition-all duration-200 ${
                      copiedUrls.has(`public-copy-${pipeline?.id}`)
                        ? 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
                    }`}
                  >
                    {copiedUrls.has(`public-copy-${pipeline?.id}`) ? (
                      <>
                        <Check className="w-4 h-4 mr-1" />
                        Copied
                      </>
                    ) : (
                      <>
                        <Copy className="w-4 h-4 mr-1" />
                        Copy
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>

            {/* Internal Form Card */}
            <div className="group relative rounded-xl p-6 border-2 bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-950/30 dark:to-blue-900/30 border-blue-200 dark:border-blue-700 hover:shadow-lg hover:shadow-blue-500/20 transition-all duration-200">
              <div className="flex items-center space-x-3 mb-4">
                <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/50 rounded-lg flex items-center justify-center">
                  <svg className="w-5 h-5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <div>
                  <h4 className="font-semibold text-blue-900 dark:text-blue-100">
                    Internal Form
                  </h4>
                  <p className="text-sm text-blue-700 dark:text-blue-300">
                    Authenticated access
                  </p>
                </div>
              </div>
              
              <div className="space-y-3">
                {/* Tenant-aware URL display */}
                <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-medium text-gray-700 dark:text-gray-300">Full URL:</span>
                    <button
                      onClick={() => {
                        const currentTenant = getCurrentTenant()
                        const fullUrl = `http://${currentTenant}.localhost:3000/forms/internal/${pipeline?.id}`
                        copyToClipboard(fullUrl, `internal-full-${pipeline?.id}`)
                      }}
                      className={`inline-flex items-center px-2 py-1 text-xs rounded transition-colors ${
                        copiedUrls.has(`internal-full-${pipeline?.id}`)
                          ? 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400'
                          : 'bg-gray-100 hover:bg-gray-200 text-gray-600 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-gray-400'
                      }`}
                    >
                      {copiedUrls.has(`internal-full-${pipeline?.id}`) ? (
                        <Check className="w-3 h-3" />
                      ) : (
                        <Copy className="w-3 h-3" />
                      )}
                    </button>
                  </div>
                  <code className="text-xs text-blue-600 dark:text-blue-400 break-all">
                    http://{getCurrentTenant()}.localhost:3000/forms/internal/{pipeline?.id}
                  </code>
                </div>
                
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => {
                      window.open(`/forms/internal/${pipeline?.id}`, '_blank')
                    }}
                    className="inline-flex items-center justify-center px-3 py-2 bg-blue-500 text-white text-sm font-medium rounded-lg hover:bg-blue-600 hover:scale-105 transition-all duration-200 shadow-lg shadow-blue-500/25"
                  >
                    <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-1M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                    Open
                  </button>
                  
                  <button
                    onClick={() => {
                      const currentTenant = getCurrentTenant()
                      const fullUrl = `http://${currentTenant}.localhost:3000/forms/internal/${pipeline?.id}`
                      copyToClipboard(fullUrl, `internal-copy-${pipeline?.id}`)
                    }}
                    className={`inline-flex items-center justify-center px-3 py-2 text-sm font-medium rounded-lg transition-all duration-200 ${
                      copiedUrls.has(`internal-copy-${pipeline?.id}`)
                        ? 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
                    }`}
                  >
                    {copiedUrls.has(`internal-copy-${pipeline?.id}`) ? (
                      <>
                        <Check className="w-4 h-4 mr-1" />
                        Copied
                      </>
                    ) : (
                      <>
                        <Copy className="w-4 h-4 mr-1" />
                        Copy
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* API Integration Info - Collapsible */}
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
            <button
              onClick={() => setShowFullFormSettings(!showFullFormSettings)}
              className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center justify-between text-left transition-colors"
            >
              <div className="flex items-center space-x-2">
                <Settings className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                <span className="text-sm font-medium text-gray-900 dark:text-white">
                  API Integration Details
                </span>
              </div>
              <ChevronDown className={`w-4 h-4 text-gray-600 dark:text-gray-400 transition-transform ${showFullFormSettings ? 'rotate-180' : ''}`} />
            </button>
            
            {showFullFormSettings && (
              <div className="px-4 py-3 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
                <div className="space-y-4 text-sm">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <div className="font-medium text-gray-900 dark:text-white mb-3">Internal Form API</div>
                      <div className="space-y-3">
                        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs font-medium text-gray-700 dark:text-gray-300">Schema Endpoint:</span>
                            <button
                              onClick={() => {
                                const currentTenant = getCurrentTenant()
                                const apiUrl = `http://${currentTenant}.localhost:8000/api/pipelines/${pipeline?.id}/forms/internal/`
                                copyToClipboard(apiUrl, `api-internal-schema-${pipeline?.id}`)
                              }}
                              className={`inline-flex items-center px-2 py-1 text-xs rounded transition-colors ${
                                copiedUrls.has(`api-internal-schema-${pipeline?.id}`)
                                  ? 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400'
                                  : 'bg-white hover:bg-gray-100 text-gray-600 dark:bg-gray-600 dark:hover:bg-gray-500 dark:text-gray-400'
                              }`}
                            >
                              {copiedUrls.has(`api-internal-schema-${pipeline?.id}`) ? (
                                <Check className="w-3 h-3" />
                              ) : (
                                <Copy className="w-3 h-3" />
                              )}
                            </button>
                          </div>
                          <code className="text-xs text-blue-600 dark:text-blue-400 break-all">
                            GET http://{getCurrentTenant()}.localhost:8000/api/pipelines/{pipeline?.id}/forms/internal/
                          </code>
                        </div>
                        
                        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs font-medium text-gray-700 dark:text-gray-300">Submit Endpoint:</span>
                            <button
                              onClick={() => {
                                const currentTenant = getCurrentTenant()
                                const apiUrl = `http://${currentTenant}.localhost:8000/api/pipelines/${pipeline?.id}/forms/submit/`
                                copyToClipboard(apiUrl, `api-internal-submit-${pipeline?.id}`)
                              }}
                              className={`inline-flex items-center px-2 py-1 text-xs rounded transition-colors ${
                                copiedUrls.has(`api-internal-submit-${pipeline?.id}`)
                                  ? 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400'
                                  : 'bg-white hover:bg-gray-100 text-gray-600 dark:bg-gray-600 dark:hover:bg-gray-500 dark:text-gray-400'
                              }`}
                            >
                              {copiedUrls.has(`api-internal-submit-${pipeline?.id}`) ? (
                                <Check className="w-3 h-3" />
                              ) : (
                                <Copy className="w-3 h-3" />
                              )}
                            </button>
                          </div>
                          <code className="text-xs text-blue-600 dark:text-blue-400 break-all">
                            POST http://{getCurrentTenant()}.localhost:8000/api/pipelines/{pipeline?.id}/forms/submit/
                          </code>
                        </div>
                      </div>
                    </div>
                    
                    <div>
                      <div className="font-medium text-gray-900 dark:text-white mb-3">Public Form API</div>
                      <div className="space-y-3">
                        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs font-medium text-gray-700 dark:text-gray-300">Schema Endpoint:</span>
                            <button
                              onClick={() => {
                                const currentTenant = getCurrentTenant()
                                const pipelineSlug = pipeline?.name?.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '') || pipeline?.id
                                const apiUrl = `http://${currentTenant}.localhost:8000/api/public-forms/${pipelineSlug}/`
                                copyToClipboard(apiUrl, `api-public-schema-${pipeline?.id}`)
                              }}
                              className={`inline-flex items-center px-2 py-1 text-xs rounded transition-colors ${
                                copiedUrls.has(`api-public-schema-${pipeline?.id}`)
                                  ? 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400'
                                  : 'bg-white hover:bg-gray-100 text-gray-600 dark:bg-gray-600 dark:hover:bg-gray-500 dark:text-gray-400'
                              }`}
                            >
                              {copiedUrls.has(`api-public-schema-${pipeline?.id}`) ? (
                                <Check className="w-3 h-3" />
                              ) : (
                                <Copy className="w-3 h-3" />
                              )}
                            </button>
                          </div>
                          <code className="text-xs text-green-600 dark:text-green-400 break-all">
                            GET http://{getCurrentTenant()}.localhost:8000/api/public-forms/{pipeline?.name?.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '') || pipeline?.id}/
                          </code>
                        </div>
                        
                        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs font-medium text-gray-700 dark:text-gray-300">Submit Endpoint:</span>
                            <button
                              onClick={() => {
                                const currentTenant = getCurrentTenant()
                                const pipelineSlug = pipeline?.name?.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '') || pipeline?.id
                                const apiUrl = `http://${currentTenant}.localhost:8000/api/public-forms/${pipelineSlug}/submit/`
                                copyToClipboard(apiUrl, `api-public-submit-${pipeline?.id}`)
                              }}
                              className={`inline-flex items-center px-2 py-1 text-xs rounded transition-colors ${
                                copiedUrls.has(`api-public-submit-${pipeline?.id}`)
                                  ? 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400'
                                  : 'bg-white hover:bg-gray-100 text-gray-600 dark:bg-gray-600 dark:hover:bg-gray-500 dark:text-gray-400'
                              }`}
                            >
                              {copiedUrls.has(`api-public-submit-${pipeline?.id}`) ? (
                                <Check className="w-3 h-3" />
                              ) : (
                                <Copy className="w-3 h-3" />
                              )}
                            </button>
                          </div>
                          <code className="text-xs text-green-600 dark:text-green-400 break-all">
                            POST http://{getCurrentTenant()}.localhost:8000/api/public-forms/{pipeline?.name?.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '') || pipeline?.id}/submit/
                          </code>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Enhanced Stage Forms Configuration Section */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        {/* Header with gradient background */}
        <div className="bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-950/50 dark:to-pink-950/50 px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-purple-100 dark:bg-purple-900/50 rounded-lg flex items-center justify-center">
              <Target className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Stage Form Configuration
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Configure automatic form triggering and completion prompts for stage transitions
              </p>
            </div>
          </div>
        </div>

        <div className="p-6">
          {selectedStageField && stageOptions.length > 0 ? (
            <div className="space-y-6">
              {/* Enhanced Smart Form Triggers */}
              <div className="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-950/30 dark:to-indigo-950/30 rounded-xl p-6 border-2 border-blue-200 dark:border-blue-800">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center space-x-3">
                    <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/50 rounded-lg flex items-center justify-center">
                      <Settings className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                    </div>
                    <div>
                      <h4 className="text-lg font-semibold text-blue-900 dark:text-blue-100">
                        Smart Form Triggers
                      </h4>
                      <p className="text-sm text-blue-700 dark:text-blue-300">
                        Automatic form generation for stage transitions
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => setShowFormSettings(!showFormSettings)}
                    className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200 transition-colors"
                  >
                    {showFormSettings ? 'Hide Details' : 'Show Details'}
                    <ChevronDown className={`w-4 h-4 ml-1 transition-transform ${showFormSettings ? 'rotate-180' : ''}`} />
                  </button>
                </div>
                
                <div className="bg-blue-100/50 dark:bg-blue-900/20 rounded-lg p-4 mb-4">
                  <p className="text-sm text-blue-800 dark:text-blue-200 mb-3 font-medium">
                    When records move to a new stage with missing required fields, the system automatically:
                  </p>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div className="flex items-center space-x-2">
                      <CheckCircle className="w-4 h-4 text-green-600" />
                      <span className="text-sm text-blue-800 dark:text-blue-200">Generate internal form URLs</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <CheckCircle className="w-4 h-4 text-green-600" />
                      <span className="text-sm text-blue-800 dark:text-blue-200">Generate public form URLs</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <CheckCircle className="w-4 h-4 text-green-600" />
                      <span className="text-sm text-blue-800 dark:text-blue-200">Send completion notifications</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <CheckCircle className="w-4 h-4 text-green-600" />
                      <span className="text-sm text-blue-800 dark:text-blue-200">Track completion analytics</span>
                    </div>
                  </div>
                </div>

                {/* Test Stage Triggers - Prominent Button */}
                <div className="flex items-center justify-between p-4 bg-white dark:bg-gray-800 rounded-lg border border-blue-200 dark:border-blue-700">
                  <div>
                    <div className="font-medium text-gray-900 dark:text-white">Test Configuration</div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">Simulate stage transitions and form generation</div>
                  </div>
                  <button
                    onClick={() => {
                      // In a real implementation, this would open a test modal or redirect to a test page
                      alert('Stage trigger testing would open here - implement in next phase!')
                    }}
                    className="inline-flex items-center px-4 py-2 bg-gradient-to-r from-green-500 to-emerald-500 text-white text-sm font-medium rounded-lg hover:from-green-600 hover:to-emerald-600 hover:scale-105 transition-all duration-200 shadow-lg shadow-green-500/25"
                  >
                    <Target className="w-4 h-4 mr-2" />
                    Test Triggers
                  </button>
                </div>
              </div>

              {/* Enhanced Form URLs Preview */}
              <div className="space-y-4">
                <div className="flex items-center space-x-2 mb-4">
                  <div className="w-8 h-8 bg-gray-100 dark:bg-gray-700 rounded-lg flex items-center justify-center">
                    <svg className="w-4 h-4 text-gray-600 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.102m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                    </svg>
                  </div>
                  <h4 className="text-lg font-semibold text-gray-900 dark:text-white">
                    Generated Stage Form URLs
                  </h4>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  {stageOptions.map((stage, index) => (
                    <div key={stage} className="bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-700 rounded-xl p-5 border border-gray-200 dark:border-gray-600 hover:shadow-md transition-all duration-200">
                      <div className="flex items-center space-x-3 mb-4">
                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold text-white ${
                          index % 4 === 0 ? 'bg-blue-500' :
                          index % 4 === 1 ? 'bg-green-500' :
                          index % 4 === 2 ? 'bg-purple-500' : 'bg-orange-500'
                        }`}>
                          {index + 1}
                        </div>
                        <div>
                          <div className="font-semibold text-gray-900 dark:text-white">
                            {stage.charAt(0).toUpperCase() + stage.slice(1)} Stage
                          </div>
                          <div className="text-xs text-gray-500 dark:text-gray-400">
                            Stage-specific forms
                          </div>
                        </div>
                      </div>
                      
                      <div className="space-y-3">
                        <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border">
                          <div className="flex items-center justify-between mb-1">
                            <div className="text-xs font-medium text-gray-700 dark:text-gray-300">Internal Form</div>
                            <button
                              onClick={() => {
                                const currentTenant = getCurrentTenant()
                                const fullUrl = `http://${currentTenant}.localhost:3000/forms/internal/${pipeline?.id}?stage=${stage}`
                                copyToClipboard(fullUrl, `stage-internal-${pipeline?.id}-${stage}`)
                              }}
                              className={`inline-flex items-center px-2 py-1 text-xs rounded transition-colors ${
                                copiedUrls.has(`stage-internal-${pipeline?.id}-${stage}`)
                                  ? 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400'
                                  : 'bg-gray-100 hover:bg-gray-200 text-gray-600 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-gray-400'
                              }`}
                            >
                              {copiedUrls.has(`stage-internal-${pipeline?.id}-${stage}`) ? (
                                <Check className="w-3 h-3" />
                              ) : (
                                <Copy className="w-3 h-3" />
                              )}
                            </button>
                          </div>
                          <code className="text-xs text-blue-600 dark:text-blue-400 break-all">
                            http://{getCurrentTenant()}.localhost:3000/forms/internal/{pipeline?.id}?stage={stage}
                          </code>
                        </div>
                        <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border">
                          <div className="flex items-center justify-between mb-1">
                            <div className="text-xs font-medium text-gray-700 dark:text-gray-300">Public Form</div>
                            <button
                              onClick={() => {
                                const currentTenant = getCurrentTenant()
                                const pipelineSlug = pipeline?.name?.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '') || pipeline?.id
                                const fullUrl = `http://${currentTenant}.localhost:3000/forms/${pipelineSlug}/stage/${stage}`
                                copyToClipboard(fullUrl, `stage-public-${pipeline?.id}-${stage}`)
                              }}
                              className={`inline-flex items-center px-2 py-1 text-xs rounded transition-colors ${
                                copiedUrls.has(`stage-public-${pipeline?.id}-${stage}`)
                                  ? 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400'
                                  : 'bg-gray-100 hover:bg-gray-200 text-gray-600 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-gray-400'
                              }`}
                            >
                              {copiedUrls.has(`stage-public-${pipeline?.id}-${stage}`) ? (
                                <Check className="w-3 h-3" />
                              ) : (
                                <Copy className="w-3 h-3" />
                              )}
                            </button>
                          </div>
                          <code className="text-xs text-green-600 dark:text-green-400 break-all">
                            http://{getCurrentTenant()}.localhost:3000/forms/{pipeline?.name?.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '') || pipeline?.id}/stage/{stage}
                          </code>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Enhanced API Integration Info */}
              {showFormSettings && (
                <div className="bg-gradient-to-r from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-700 rounded-xl p-6 border border-gray-200 dark:border-gray-700">
                  <div className="flex items-center space-x-2 mb-4">
                    <div className="w-8 h-8 bg-gray-200 dark:bg-gray-600 rounded-lg flex items-center justify-center">
                      <svg className="w-4 h-4 text-gray-600 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                      </svg>
                    </div>
                    <h4 className="text-lg font-semibold text-gray-900 dark:text-white">
                      API Integration Details
                    </h4>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border">
                      <div className="flex items-center justify-between mb-2">
                        <div className="font-medium text-gray-900 dark:text-white">Stage Trigger Status</div>
                        <button
                          onClick={() => {
                            const currentTenant = getCurrentTenant()
                            const apiUrl = `http://${currentTenant}.localhost:8000/api/pipelines/${pipeline?.id}/records/{{record_id}}/stage-trigger-status/`
                            copyToClipboard(apiUrl, `api-stage-trigger-${pipeline?.id}`)
                          }}
                          className={`inline-flex items-center px-2 py-1 text-xs rounded transition-colors ${
                            copiedUrls.has(`api-stage-trigger-${pipeline?.id}`)
                              ? 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400'
                              : 'bg-gray-100 hover:bg-gray-200 text-gray-600 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-gray-400'
                          }`}
                        >
                          {copiedUrls.has(`api-stage-trigger-${pipeline?.id}`) ? (
                            <Check className="w-3 h-3" />
                          ) : (
                            <Copy className="w-3 h-3" />
                          )}
                        </button>
                      </div>
                      <code className="text-xs text-gray-600 dark:text-gray-400 break-all">
                        GET http://{getCurrentTenant()}.localhost:8000/api/pipelines/{pipeline?.id}/records/{{record_id}}/stage-trigger-status/
                      </code>
                    </div>
                    
                    <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border">
                      <div className="flex items-center justify-between mb-2">
                        <div className="font-medium text-gray-900 dark:text-white">Internal Form Schema</div>
                        <button
                          onClick={() => {
                            const currentTenant = getCurrentTenant()
                            const apiUrl = `http://${currentTenant}.localhost:8000/api/pipelines/${pipeline?.id}/forms/stage/{{stage}}/internal/`
                            copyToClipboard(apiUrl, `api-stage-internal-${pipeline?.id}`)
                          }}
                          className={`inline-flex items-center px-2 py-1 text-xs rounded transition-colors ${
                            copiedUrls.has(`api-stage-internal-${pipeline?.id}`)
                              ? 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400'
                              : 'bg-gray-100 hover:bg-gray-200 text-gray-600 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-gray-400'
                          }`}
                        >
                          {copiedUrls.has(`api-stage-internal-${pipeline?.id}`) ? (
                            <Check className="w-3 h-3" />
                          ) : (
                            <Copy className="w-3 h-3" />
                          )}
                        </button>
                      </div>
                      <code className="text-xs text-blue-600 dark:text-blue-400 break-all">
                        GET http://{getCurrentTenant()}.localhost:8000/api/pipelines/{pipeline?.id}/forms/stage/{{stage}}/internal/
                      </code>
                    </div>
                    
                    <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border">
                      <div className="flex items-center justify-between mb-2">
                        <div className="font-medium text-gray-900 dark:text-white">Public Form Schema</div>
                        <button
                          onClick={() => {
                            const currentTenant = getCurrentTenant()
                            const pipelineSlug = pipeline?.name?.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '') || pipeline?.id
                            const apiUrl = `http://${currentTenant}.localhost:8000/api/public-forms/${pipelineSlug}/stage/{{stage}}/`
                            copyToClipboard(apiUrl, `api-stage-public-${pipeline?.id}`)
                          }}
                          className={`inline-flex items-center px-2 py-1 text-xs rounded transition-colors ${
                            copiedUrls.has(`api-stage-public-${pipeline?.id}`)
                              ? 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400'
                              : 'bg-gray-100 hover:bg-gray-200 text-gray-600 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-gray-400'
                          }`}
                        >
                          {copiedUrls.has(`api-stage-public-${pipeline?.id}`) ? (
                            <Check className="w-3 h-3" />
                          ) : (
                            <Copy className="w-3 h-3" />
                          )}
                        </button>
                      </div>
                      <code className="text-xs text-green-600 dark:text-green-400 break-all">
                        GET http://{getCurrentTenant()}.localhost:8000/api/public-forms/{pipeline?.name?.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '') || pipeline?.id}/stage/{{stage}}/
                      </code>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-12">
              <div className="w-16 h-16 bg-purple-100 dark:bg-purple-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
                <Target className="w-8 h-8 text-purple-600 dark:text-purple-400" />
              </div>
              <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                No Stage Field Selected
              </h4>
              <p className="text-gray-600 dark:text-gray-400 mb-4 max-w-md mx-auto">
                Select a stage field in the Stage Requirements section above to configure automatic form triggers for stage transitions.
              </p>
              <div className="bg-purple-50 dark:bg-purple-950/30 rounded-lg p-4 max-w-md mx-auto">
                <p className="text-sm text-purple-700 dark:text-purple-300">
                  💡 <strong>Tip:</strong> Form triggers automatically prompt users to complete required fields when moving between stages.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
    </PermissionGuard>
  )
}