'use client'

import React, { useState, useEffect } from 'react'
import { pipelinesApi } from '@/lib/api'
import { MigrationProgressTracker } from './migration-progress-tracker'
import { 
  AlertTriangle, 
  CheckCircle, 
  X, 
  ArrowRight, 
  Info,
  AlertCircle,
  Ban,
  Lightbulb,
  Shield,
  Zap,
  Database,
  Clock,
  TrendingUp,
  ArrowLeft
} from 'lucide-react'

interface ValidationStatus {
  allowed: boolean
  category: 'safe' | 'risky' | 'denied'
  risk_level: 'low' | 'medium' | 'high'
  reason?: string
  explanation?: string
  alternatives?: string[]
  data_loss_warning?: string
  description?: string
  performance_estimate?: {
    total_records: number
    records_with_data: number
    estimated_time_formatted: string
    complexity: string
    requires_backup: boolean
    recommended_maintenance_window: boolean
  }
  data_preview?: {
    has_samples: boolean
    sample_count: number
    samples: Array<{
      record_id: string
      record_title: string
      current_value: any
      transformed_value: any
      success: boolean
    }>
  }
}

interface FieldTypeOption {
  type: string
  label: string
  description: string
  icon?: React.ReactNode
  validation?: ValidationStatus
  validating?: boolean
}

interface MigrationWizardProps {
  isOpen: boolean
  onClose: () => void
  pipelineId: string
  field: {
    id: string
    name: string
    display_name?: string
    field_type: string
    field_config: any
  }
  onMigrationSuccess: () => void
}

const FIELD_TYPES: Omit<FieldTypeOption, 'validation' | 'validating'>[] = [
  {
    type: 'text',
    label: 'Text',
    description: 'Single-line text input',
    icon: <div className="w-5 h-5 rounded bg-blue-100 flex items-center justify-center text-blue-600 text-xs font-bold">T</div>
  },
  {
    type: 'textarea',
    label: 'Textarea', 
    description: 'Multi-line text input',
    icon: <div className="w-5 h-5 rounded bg-blue-100 flex items-center justify-center text-blue-600 text-xs font-bold">¶</div>
  },
  {
    type: 'number',
    label: 'Number',
    description: 'All numeric types (integer/decimal/currency)',
    icon: <div className="w-5 h-5 rounded bg-green-100 flex items-center justify-center text-green-600 text-xs font-bold">#</div>
  },
  {
    type: 'boolean',
    label: 'Boolean',
    description: 'True/false checkbox',
    icon: <div className="w-5 h-5 rounded bg-gray-100 flex items-center justify-center text-gray-600 text-xs font-bold">☑</div>
  },
  {
    type: 'date',
    label: 'Date',
    description: 'Date picker with optional time',
    icon: <div className="w-5 h-5 rounded bg-orange-100 flex items-center justify-center text-orange-600 text-xs font-bold">📅</div>
  },
  {
    type: 'phone',
    label: 'Phone',
    description: 'Phone number with country code',
    icon: <div className="w-5 h-5 rounded bg-purple-100 flex items-center justify-center text-purple-600 text-xs font-bold">📞</div>
  },
  {
    type: 'email',
    label: 'Email',
    description: 'Email address input',
    icon: <div className="w-5 h-5 rounded bg-purple-100 flex items-center justify-center text-purple-600 text-xs font-bold">@</div>
  },
  {
    type: 'address',
    label: 'Address',
    description: 'Structured address input',
    icon: <div className="w-5 h-5 rounded bg-cyan-100 flex items-center justify-center text-cyan-600 text-xs font-bold">🏠</div>
  },
  {
    type: 'select',
    label: 'Select',
    description: 'Single choice dropdown',
    icon: <div className="w-5 h-5 rounded bg-indigo-100 flex items-center justify-center text-indigo-600 text-xs font-bold">▼</div>
  },
  {
    type: 'multiselect',
    label: 'Multi-Select',
    description: 'Multiple choice selection',
    icon: <div className="w-5 h-5 rounded bg-indigo-100 flex items-center justify-center text-indigo-600 text-xs font-bold">☰</div>
  },
  {
    type: 'tags',
    label: 'Tags',
    description: 'Tag input with autocomplete',
    icon: <div className="w-5 h-5 rounded bg-yellow-100 flex items-center justify-center text-yellow-600 text-xs font-bold">#</div>
  },
  {
    type: 'url',
    label: 'URL',
    description: 'URL input with validation',
    icon: <div className="w-5 h-5 rounded bg-purple-100 flex items-center justify-center text-purple-600 text-xs font-bold">🔗</div>
  },
  {
    type: 'file',
    label: 'File',
    description: 'File upload (includes images)',
    icon: <div className="w-5 h-5 rounded bg-red-100 flex items-center justify-center text-red-600 text-xs font-bold">📁</div>
  },
  {
    type: 'button',
    label: 'Button',
    description: 'Action button powered by workflows',
    icon: <div className="w-5 h-5 rounded bg-slate-100 flex items-center justify-center text-slate-600 text-xs font-bold">⚡</div>
  },
  {
    type: 'relation',
    label: 'Relation',
    description: 'Reference to another pipeline record',
    icon: <div className="w-5 h-5 rounded bg-pink-100 flex items-center justify-center text-pink-600 text-xs font-bold">🔗</div>
  },
  {
    type: 'ai_generated',
    label: 'AI Generated',
    description: 'AI-powered field with latest OpenAI models',
    icon: <div className="w-5 h-5 rounded bg-violet-100 flex items-center justify-center text-violet-600 text-xs font-bold">🤖</div>
  }
]

export function MigrationWizard({
  isOpen,
  onClose,
  pipelineId,
  field,
  onMigrationSuccess
}: MigrationWizardProps) {
  const [step, setStep] = useState<'select' | 'confirm' | 'progress' | 'complete'>('select')
  const [fieldTypes, setFieldTypes] = useState<FieldTypeOption[]>([])
  const [validatingTypes, setValidatingTypes] = useState<Set<string>>(new Set())
  const [selectedFieldType, setSelectedFieldType] = useState('')
  const [validation, setValidation] = useState<ValidationStatus | null>(null)
  const [migrationTaskId, setMigrationTaskId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [migrationResult, setMigrationResult] = useState<any>(null)
  const [isPreview, setIsPreview] = useState(false)

  // Initialize field types and start validation when opened
  useEffect(() => {
    if (!isOpen) return
    
    setStep('select')
    setSelectedFieldType('')
    setValidation(null)
    setMigrationTaskId(null)
    setError(null)
    setMigrationResult(null)
    setIsPreview(false)
    
    // Initialize field types and start validation
    const initialFieldTypes = FIELD_TYPES
      .filter(ft => ft.type !== field.field_type) // Exclude current field type
      .map(ft => ({ ...ft, validating: true }))
    
    setFieldTypes(initialFieldTypes)
    setValidatingTypes(new Set(initialFieldTypes.map(ft => ft.type)))
    
    // Start validation for all field types
    initialFieldTypes.forEach(fieldType => {
      validateFieldType(fieldType.type)
    })
  }, [isOpen, field.field_type])

  const validateFieldType = async (targetType: string) => {
    try {
      const response = await pipelinesApi.validateMigration(pipelineId, field.id, {
        new_config: {
          field_type: targetType,
          field_config: {} // Basic validation without specific config
        },
        include_impact_preview: false // Just validation, no detailed analysis
      })

      const validation: ValidationStatus = response.data.validation
      
      // Add performance estimate if available
      if (response.data.performance_estimate) {
        validation.performance_estimate = response.data.performance_estimate
      }
      
      // Add data preview if available
      if (response.data.data_preview) {
        validation.data_preview = response.data.data_preview
      }

      // Update the field type with validation result
      setFieldTypes(prev => prev.map(ft => 
        ft.type === targetType 
          ? { ...ft, validation, validating: false }
          : ft
      ))

      // Remove from validating set
      setValidatingTypes(prev => {
        const newSet = new Set(prev)
        newSet.delete(targetType)
        return newSet
      })

    } catch (error) {
      console.error(`Validation failed for ${targetType}:`, error)
      
      // Mark as failed validation
      setFieldTypes(prev => prev.map(ft => 
        ft.type === targetType 
          ? { 
              ...ft, 
              validating: false,
              validation: {
                allowed: false,
                category: 'denied',
                risk_level: 'high',
                reason: 'Validation failed',
                explanation: 'Could not validate this field type conversion'
              }
            }
          : ft
      ))
      
      setValidatingTypes(prev => {
        const newSet = new Set(prev)
        newSet.delete(targetType)
        return newSet
      })
    }
  }

  const handleFieldTypeSelect = (fieldType: FieldTypeOption) => {
    if (!fieldType.validation || !fieldType.validation.allowed) return
    
    setSelectedFieldType(fieldType.type)
    setValidation(fieldType.validation)
    setStep('confirm')
  }

  const executeMigration = async (force: boolean = false, dryRun: boolean = false) => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await pipelinesApi.migrateFieldSchema(pipelineId, field.id, {
        new_config: {
          field_type: selectedFieldType,
          field_config: {} // Basic migration, config handled in pipeline configurator
        },
        dry_run: dryRun,
        force: force
      })
      
      setMigrationResult(response.data)
      
      // Handle dry run (preview) differently from actual migration
      if (dryRun) {
        // For dry runs, show the preview in a modal or section
        // The response should contain preview data without actually executing
        setIsPreview(true)
        setStep('complete') // Will show preview results
      } else {
        // If migration started in background, show progress tracker
        if (response.data.migration_started && response.data.task_id) {
          setMigrationTaskId(response.data.task_id)
          setStep('progress')
        } else {
          // Simple migration completed immediately
          setStep('complete')
          
          // Auto-close for successful simple migrations
          if (response.data.migration_completed) {
            setTimeout(() => {
              onMigrationSuccess()
              onClose()
            }, 2000)
          }
        }
      }
      
    } catch (err: any) {
      setError(err.response?.data?.error || 'Migration failed')
    } finally {
      setLoading(false)
    }
  }

  const handleMigrationComplete = (success: boolean, result: any) => {
    setMigrationResult(result)
    setStep('complete')
    
    if (success) {
      setTimeout(() => {
        onMigrationSuccess()
        onClose()
      }, 2000)
    }
  }

  const getValidationIcon = (validation?: ValidationStatus, validating?: boolean) => {
    if (validating) {
      return <div className="w-5 h-5 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin" />
    }
    
    if (!validation) return null

    switch (validation.category) {
      case 'safe':
        return <CheckCircle className="w-5 h-5 text-green-500" />
      case 'risky':
        return <AlertTriangle className="w-5 h-5 text-orange-500" />
      case 'denied':
        return <Ban className="w-5 h-5 text-red-500" />
      default:
        return <Info className="w-5 h-5 text-gray-400" />
    }
  }

  const getValidationColor = (validation?: ValidationStatus) => {
    if (!validation) return 'border-gray-200 hover:border-gray-300'
    
    switch (validation.category) {
      case 'safe':
        return 'border-green-200 bg-green-50 hover:border-green-300 hover:bg-green-100'
      case 'risky':
        return 'border-orange-200 bg-orange-50 hover:border-orange-300 hover:bg-orange-100'
      case 'denied':
        return 'border-red-200 bg-red-50 cursor-not-allowed'
      default:
        return 'border-gray-200 hover:border-gray-300'
    }
  }

  const getRiskIcon = (category: string) => {
    switch (category) {
      case 'safe':
        return <Shield className="w-5 h-5 text-green-500" />
      case 'risky':
        return <AlertTriangle className="w-5 h-5 text-orange-500" />
      case 'denied':
        return <Ban className="w-5 h-5 text-red-500" />
      default:
        return <CheckCircle className="w-5 h-5 text-blue-500" />
    }
  }

  const getRiskColor = (category: string) => {
    switch (category) {
      case 'safe':
        return 'border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-900/20'
      case 'risky':
        return 'border-orange-200 bg-orange-50 dark:border-orange-800 dark:bg-orange-900/20'
      case 'denied':
        return 'border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20'
      default:
        return 'border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-900/20'
    }
  }

  const isSelectable = (validation?: ValidationStatus) => {
    return validation?.allowed !== false
  }

  if (!isOpen) return null

  // Progress tracking for background migrations
  if (step === 'progress' && migrationTaskId) {
    return (
      <MigrationProgressTracker
        isOpen={true}
        onClose={onClose}
        taskId={migrationTaskId}
        fieldName={field.display_name || field.name}
        onMigrationComplete={handleMigrationComplete}
      />
    )
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center p-6 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              {step === 'select' ? 'Migrate Field Type' : 'Confirm Migration'}
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              {step === 'select' 
                ? `${field.display_name || field.name} - Current type: ${field.field_type}`
                : `${field.display_name || field.name}: ${field.field_type} → ${selectedFieldType}`
              }
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        <div className="p-6">
          {step === 'select' && (
            <div>
              <div className="mb-6">
                <div className="flex items-center space-x-4 text-sm">
                  <div className="flex items-center">
                    <Shield className="w-4 h-4 text-green-500 mr-1" />
                    <span className="text-green-700">Safe</span>
                  </div>
                  <div className="flex items-center">
                    <AlertTriangle className="w-4 h-4 text-orange-500 mr-1" />
                    <span className="text-orange-700">Risky</span>
                  </div>
                  <div className="flex items-center">
                    <Ban className="w-4 h-4 text-red-500 mr-1" />
                    <span className="text-red-700">Blocked</span>
                  </div>
                  {validatingTypes.size > 0 && (
                    <div className="flex items-center text-gray-500">
                      <div className="w-4 h-4 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin mr-1" />
                      <span>Analyzing {validatingTypes.size} migrations...</span>
                    </div>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {fieldTypes.map((fieldType) => (
                  <div
                    key={fieldType.type}
                    onClick={() => handleFieldTypeSelect(fieldType)}
                    className={`p-4 border-2 rounded-lg transition-all ${getValidationColor(fieldType.validation)} ${
                      isSelectable(fieldType.validation) ? 'cursor-pointer' : 'cursor-not-allowed'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center space-x-3">
                        {fieldType.icon}
                        <div>
                          <h3 className="font-medium text-gray-900 dark:text-white">
                            {fieldType.label}
                          </h3>
                        </div>
                      </div>
                      <div className="flex-shrink-0">
                        {getValidationIcon(fieldType.validation, fieldType.validating)}
                      </div>
                    </div>
                    
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                      {fieldType.description}
                    </p>

                    {/* Validation Status */}
                    {fieldType.validation && !fieldType.validating && (
                      <div className="space-y-2">
                        <div className={`text-xs font-medium ${
                          fieldType.validation.category === 'safe' ? 'text-green-700' :
                          fieldType.validation.category === 'risky' ? 'text-orange-700' :
                          'text-red-700'
                        }`}>
                          {fieldType.validation.category === 'safe' && '✓ Safe Migration'}
                          {fieldType.validation.category === 'risky' && '⚠ Risky Migration'}
                          {fieldType.validation.category === 'denied' && '✗ Migration Blocked'}
                        </div>
                        
                        <p className="text-xs text-gray-600 dark:text-gray-400">
                          {fieldType.validation.description || fieldType.validation.reason}
                        </p>

                        {/* Performance Preview */}
                        {fieldType.validation.performance_estimate && (
                          <div className="mt-2 p-2 bg-gray-100 dark:bg-gray-700 rounded text-xs">
                            <div className="flex justify-between items-center">
                              <div className="flex items-center">
                                <Database className="w-3 h-3 mr-1" />
                                <span>{fieldType.validation.performance_estimate.records_with_data} records</span>
                              </div>
                              <div className="flex items-center">
                                <Clock className="w-3 h-3 mr-1" />
                                <span>{fieldType.validation.performance_estimate.estimated_time_formatted}</span>
                              </div>
                            </div>
                            {fieldType.validation.performance_estimate.requires_backup && (
                              <div className="mt-1 text-orange-600 flex items-center">
                                <AlertTriangle className="w-3 h-3 mr-1" />
                                <span>Backup recommended</span>
                              </div>
                            )}
                          </div>
                        )}

                        {/* Data Loss Warning for Risky */}
                        {fieldType.validation.category === 'risky' && fieldType.validation.data_loss_warning && (
                          <div className="mt-2 p-2 bg-orange-100 dark:bg-orange-900/20 rounded text-xs text-orange-700 dark:text-orange-300">
                            {fieldType.validation.data_loss_warning}
                          </div>
                        )}

                        {/* Alternatives for Denied */}
                        {fieldType.validation.category === 'denied' && fieldType.validation.alternatives && (
                          <div className="mt-2 space-y-1">
                            <div className="text-xs font-medium text-gray-700 dark:text-gray-300 flex items-center">
                              <Lightbulb className="w-3 h-3 mr-1" />
                              Alternatives:
                            </div>
                            <ul className="text-xs text-gray-600 dark:text-gray-400 space-y-1">
                              {fieldType.validation.alternatives.slice(0, 2).map((alt, index) => (
                                <li key={index} className="flex items-start">
                                  <ArrowRight className="w-3 h-3 mr-1 mt-0.5 flex-shrink-0" />
                                  <span>{alt}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Selection hint */}
                        {isSelectable(fieldType.validation) && (
                          <div className="mt-2 text-xs text-blue-600 dark:text-blue-400 font-medium">
                            Click to proceed →
                          </div>
                        )}
                      </div>
                    )}

                    {/* Loading state */}
                    {fieldType.validating && (
                      <div className="text-xs text-gray-500 flex items-center">
                        <div className="w-3 h-3 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin mr-2" />
                        Analyzing migration...
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {fieldTypes.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  <Database className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p>Loading available field types...</p>
                </div>
              )}
            </div>
          )}

          {step === 'confirm' && validation && (
            <div className="space-y-6">
              {/* Migration Status Banner */}
              <div className={`p-4 rounded-lg border-2 ${getRiskColor(validation.category)}`}>
                <div className="flex items-start space-x-3">
                  {getRiskIcon(validation.category)}
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900 dark:text-white capitalize">
                      {validation.category} Migration
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      {validation.description || validation.reason}
                    </p>
                    {validation.explanation && (
                      <p className="text-sm text-gray-500 dark:text-gray-500 mt-2">
                        {validation.explanation}
                      </p>
                    )}
                  </div>
                </div>
              </div>

              {/* Performance Summary */}
              {validation.performance_estimate && (
                <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                  <h4 className="font-medium text-blue-900 dark:text-blue-100 mb-3 flex items-center">
                    <TrendingUp className="w-4 h-4 mr-2" />
                    Migration Impact
                  </h4>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div className="flex items-center">
                      <Database className="w-4 h-4 mr-2 text-blue-500" />
                      <div>
                        <div className="text-blue-700 dark:text-blue-300">Records</div>
                        <div className="font-medium">{validation.performance_estimate.records_with_data} of {validation.performance_estimate.total_records}</div>
                      </div>
                    </div>
                    <div className="flex items-center">
                      <Clock className="w-4 h-4 mr-2 text-blue-500" />
                      <div>
                        <div className="text-blue-700 dark:text-blue-300">Est. Time</div>
                        <div className="font-medium">{validation.performance_estimate.estimated_time_formatted}</div>
                      </div>
                    </div>
                    <div>
                      <div className="text-blue-700 dark:text-blue-300">Complexity</div>
                      <div className="font-medium capitalize">{validation.performance_estimate.complexity}</div>
                    </div>
                    {validation.performance_estimate.requires_backup && (
                      <div className="flex items-center text-orange-600">
                        <AlertTriangle className="w-4 h-4 mr-1" />
                        <span className="text-sm">Backup Required</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Data Preview */}
              {validation.data_preview?.has_samples && (
                <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-4">
                  <h4 className="font-medium text-gray-900 dark:text-white mb-3">
                    Sample Data Transformations
                  </h4>
                  <div className="space-y-2 max-h-32 overflow-y-auto">
                    {validation.data_preview.samples.slice(0, 3).map((sample, index) => (
                      <div key={index} className="text-xs bg-white dark:bg-gray-800 rounded p-2">
                        <div className="flex justify-between items-center">
                          <span className="font-medium">{sample.record_title}</span>
                          <span className={`px-2 py-1 rounded ${sample.success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                            {sample.success ? '✓' : '✗'}
                          </span>
                        </div>
                        <div className="flex justify-between mt-1 text-gray-600 dark:text-gray-400">
                          <span>From: {JSON.stringify(sample.current_value)}</span>
                          <span>To: {JSON.stringify(sample.transformed_value)}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Risky Migration Warning */}
              {validation.category === 'risky' && validation.data_loss_warning && (
                <div className="bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg p-4">
                  <h4 className="font-medium text-orange-900 dark:text-orange-100 mb-2 flex items-center">
                    <AlertTriangle className="w-4 h-4 mr-2" />
                    Data Loss Warning
                  </h4>
                  <p className="text-sm text-orange-800 dark:text-orange-200">
                    {validation.data_loss_warning}
                  </p>
                </div>
              )}

              {/* Safe Migration Benefits */}
              {validation.category === 'safe' && (
                <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
                  <h4 className="font-medium text-green-900 dark:text-green-100 mb-2 flex items-center">
                    <Shield className="w-4 h-4 mr-2" />
                    Safe Migration
                  </h4>
                  <p className="text-sm text-green-800 dark:text-green-200">
                    This migration preserves all existing data and can be safely executed.
                  </p>
                </div>
              )}

              {/* Action buttons */}
              <div className="flex justify-between pt-4 border-t border-gray-200 dark:border-gray-700">
                <button
                  onClick={() => setStep('select')}
                  className="flex items-center px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
                >
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back to Selection
                </button>
                
                <div className="flex space-x-3">
                  <button
                    onClick={onClose}
                    className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
                  >
                    Cancel
                  </button>

                  {validation.category === 'risky' && (
                    <button
                      onClick={() => executeMigration(true, true)}
                      disabled={loading}
                      className="px-4 py-2 border border-orange-300 dark:border-orange-600 text-orange-700 dark:text-orange-300 rounded-lg hover:bg-orange-50 dark:hover:bg-orange-900/20"
                    >
                      Preview Changes
                    </button>
                  )}
                  
                  <button
                    onClick={() => executeMigration(validation.category === 'risky', false)}
                    disabled={loading}
                    className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark disabled:opacity-50 flex items-center"
                  >
                    {loading && <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />}
                    {loading ? 'Starting Migration...' : validation.category === 'risky' ? 'Proceed with Migration' : 'Execute Migration'}
                  </button>
                </div>
              </div>
            </div>
          )}

          {step === 'complete' && migrationResult && (
            <div className="text-center space-y-4">
              {isPreview ? (
                <>
                  <Info className="w-12 h-12 text-blue-500 mx-auto" />
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                    Migration Preview
                  </h3>
                  <p className="text-gray-600 dark:text-gray-400">
                    This is a preview of what would happen during migration. No changes have been made.
                  </p>
                  
                  {/* Show preview data if available */}
                  {migrationResult.impact_analysis ? (
                    <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 text-left max-w-2xl mx-auto">
                      <h4 className="font-medium text-blue-900 dark:text-blue-100 mb-3">Migration Impact Analysis</h4>
                      <div className="text-sm text-blue-800 dark:text-blue-200 space-y-2">
                        <p><strong>Total records:</strong> {migrationResult.impact_analysis.record_count || 0}</p>
                        <p><strong>Records with data:</strong> {migrationResult.impact_analysis.records_with_data || 0}</p>
                        <p><strong>Risk level:</strong> <span className={`font-medium ${
                          migrationResult.impact_analysis.risk_level === 'high' ? 'text-red-600' :
                          migrationResult.impact_analysis.risk_level === 'medium' ? 'text-orange-600' :
                          'text-green-600'
                        }`}>{migrationResult.impact_analysis.risk_level || 'low'}</span></p>
                        {migrationResult.impact_analysis.dependent_systems?.length > 0 && (
                          <p><strong>Dependent systems:</strong> {migrationResult.impact_analysis.dependent_systems.join(', ')}</p>
                        )}
                        {migrationResult.impact_analysis.data_loss_estimate && (
                          <p className="text-orange-600"><strong>Potential data loss:</strong> {migrationResult.impact_analysis.data_loss_estimate}</p>
                        )}
                      </div>
                      
                      {/* Sample data transformations if available */}
                      {migrationResult.impact_analysis.sample_transformations && migrationResult.impact_analysis.sample_transformations.length > 0 && (
                        <div className="mt-4">
                          <h5 className="font-medium text-blue-900 dark:text-blue-100 mb-2">Sample Data Transformations</h5>
                          <div className="space-y-2 max-h-32 overflow-y-auto">
                            {migrationResult.impact_analysis.sample_transformations.slice(0, 3).map((sample, index) => (
                              <div key={index} className="text-xs bg-white dark:bg-gray-800 rounded p-2">
                                <div className="flex justify-between items-center">
                                  <span className="font-medium">{sample.record_title}</span>
                                  <span className={`px-2 py-1 rounded ${sample.success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                                    {sample.success ? '✓' : '✗'}
                                  </span>
                                </div>
                                <div className="flex justify-between mt-1 text-blue-700 dark:text-blue-300">
                                  <span>From: {JSON.stringify(sample.current_value)}</span>
                                  <span>To: {JSON.stringify(sample.transformed_value)}</span>
                                </div>
                                {sample.data_type_change && (
                                  <div className="mt-1 text-blue-600 dark:text-blue-400 text-xs">
                                    {sample.data_type_change}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : migrationResult.data_preview?.has_samples ? (
                    <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 text-left max-w-2xl mx-auto">
                      <h4 className="font-medium text-blue-900 dark:text-blue-100 mb-3">Sample Data Transformations</h4>
                      <div className="space-y-2 max-h-32 overflow-y-auto">
                        {migrationResult.data_preview.samples.slice(0, 3).map((sample, index) => (
                          <div key={index} className="text-xs bg-white dark:bg-gray-800 rounded p-2">
                            <div className="flex justify-between items-center">
                              <span className="font-medium">{sample.record_title}</span>
                              <span className={`px-2 py-1 rounded ${sample.success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                                {sample.success ? '✓' : '✗'}
                              </span>
                            </div>
                            <div className="flex justify-between mt-1 text-blue-700 dark:text-blue-300">
                              <span>From: {JSON.stringify(sample.current_value)}</span>
                              <span>To: {JSON.stringify(sample.transformed_value)}</span>
                            </div>
                            {sample.data_type_change && (
                              <div className="mt-1 text-blue-600 dark:text-blue-400 text-xs">
                                {sample.data_type_change}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                      <div className="mt-3 text-xs text-blue-700 dark:text-blue-300">
                        <p><strong>Total records with data:</strong> {migrationResult.data_preview.total_records}</p>
                        <p><strong>Sample count:</strong> {migrationResult.data_preview.sample_count}</p>
                      </div>
                    </div>
                  ) : (
                    <div className="bg-gray-50 dark:bg-gray-900/20 border border-gray-200 dark:border-gray-800 rounded-lg p-4 text-center max-w-2xl mx-auto">
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        {migrationResult.message || 'Preview completed successfully. No additional impact data available.'}
                      </p>
                    </div>
                  )}

                  <div className="flex justify-center space-x-3">
                    <button
                      onClick={() => setStep('confirm')}
                      className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
                    >
                      Back to Confirm
                    </button>
                    <button
                      onClick={() => executeMigration(validation?.category === 'risky', false)}
                      className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark"
                    >
                      Proceed with Actual Migration
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <CheckCircle className="w-12 h-12 text-green-500 mx-auto" />
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                    Migration Complete!
                  </h3>
                  <p className="text-gray-600 dark:text-gray-400">
                    {migrationResult.message || 'Field type has been successfully changed.'}
                  </p>
                  
                  <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4 text-left">
                    <h4 className="font-medium text-green-900 dark:text-green-100 mb-2">Next Steps</h4>
                    <ul className="text-sm text-green-800 dark:text-green-200 space-y-1">
                      <li>• Configure field settings in the pipeline configurator</li>
                      <li>• Update any validation rules as needed</li>
                      <li>• Review and test the migrated data</li>
                    </ul>
                  </div>

                  <button
                    onClick={() => {
                      onMigrationSuccess()
                      onClose()
                    }}
                    className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark"
                  >
                    Done
                  </button>
                </>
              )}
            </div>
          )}

          {error && (
            <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
              <div className="flex items-center">
                <AlertTriangle className="w-5 h-5 text-red-500 mr-2" />
                <span className="text-red-700 dark:text-red-300">{error}</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}