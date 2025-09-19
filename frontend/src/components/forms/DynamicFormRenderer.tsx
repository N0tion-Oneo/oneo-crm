'use client'

import React, { useState, useEffect } from 'react'
import { api } from '@/lib/api'
import { Save, AlertCircle, CheckCircle, RefreshCw } from 'lucide-react'
import { useAuth } from '@/features/auth/context'
import { evaluateConditionalRules, evaluateFieldPermissions, type FieldWithPermissions } from '@/utils/field-permissions'
import { FieldWrapper, FieldResolver } from '@/lib/field-system'

interface DynamicFieldConfig {
  id: number
  slug: string
  name: string
  type: string
  display_name: string
  help_text: string
  placeholder: string
  is_required: boolean
  is_visible: boolean
  is_readonly: boolean
  display_order: number
  field_config: Record<string, any>
  ai_config?: Record<string, any> // Add AI config support
  form_validation_rules: Record<string, any>
  business_rules?: {
    conditional_rules?: {
      show_when?: any
      hide_when?: any
      require_when?: any
    }
    user_visibility?: Record<string, any>
  }
  default_value: any
  current_value: any
}

interface DynamicFormSchema {
  pipeline_id: number
  pipeline_name: string
  form_mode: string
  target_stage?: string
  metadata: {
    total_fields: number
    required_fields: number
    visible_fields: number
  }
  fields: DynamicFieldConfig[]
}

interface ValidationError {
  field: string
  message: string
}

interface DynamicFormRendererProps {
  pipelineId?: string
  pipelineSlug?: string
  formType: 'internal_full' | 'public_filtered' | 'stage_internal' | 'stage_public' | 'shared_record'
  stage?: string
  recordId?: string
  recordData?: Record<string, any>
  encryptedToken?: string  // For shared records
  onSubmit?: (data: Record<string, any>) => void
  onError?: (error: string) => void
  embedMode?: boolean
  className?: string
  readOnly?: boolean
}

export function DynamicFormRenderer({
  pipelineId,
  pipelineSlug,
  formType,
  stage,
  recordId,
  recordData,
  encryptedToken,
  onSubmit,
  onError,
  embedMode = false,
  className = '',
  readOnly = false
}: DynamicFormRendererProps) {
  const { user } = useAuth()
  const [formSchema, setFormSchema] = useState<DynamicFormSchema | null>(null)
  const [formData, setFormData] = useState<Record<string, any>>({})
  const [fieldStates, setFieldStates] = useState<Record<string, { visible: boolean; required: boolean }>>({})
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load form schema
  useEffect(() => {
    loadFormSchema()
  }, [pipelineId, pipelineSlug, formType, stage, recordId, encryptedToken])

  // Initialize form data from schema
  useEffect(() => {
    if (formSchema) {
      const initialData: Record<string, any> = {}
      
      formSchema.fields.forEach(field => {
        // Use current_value for shared records, default_value otherwise
        const value = field.current_value !== null ? field.current_value : field.default_value
        if (value !== null && value !== undefined) {
          initialData[field.slug] = value
        }
      })
      
      // Override with provided record data
      if (recordData) {
        Object.assign(initialData, recordData)
      }
      
      setFormData(initialData)
    }
  }, [formSchema, recordData])

  // Evaluate field states when form data changes
  useEffect(() => {
    if (!formSchema || !formSchema.fields || !Array.isArray(formSchema.fields)) return

    const newFieldStates: Record<string, { visible: boolean; required: boolean }> = {}
    
    try {
      formSchema.fields.forEach(field => {
        if (field && field.slug) {
          if (field.business_rules?.conditional_rules) {
            // Add stage to form data for evaluation if provided
            const evaluationData = { ...formData }
            if (stage) {
              evaluationData.stage = stage
            }
            
            const conditionalResult = evaluateConditionalRules(
              field.business_rules.conditional_rules,
              evaluationData,
              user?.userType?.slug
            )
            
            // Debug: Log conditional rules evaluation
            if (field.slug && conditionalResult.required) {
              console.log('📋 Field Required by Conditional Rules:', {
                fieldSlug: field.slug,
                evaluationData,
                conditionalRules: field.business_rules.conditional_rules,
                result: conditionalResult
              })
            }
            
            newFieldStates[field.slug] = {
              visible: conditionalResult.visible,
              required: conditionalResult.required // Only use conditional rules for requirements
            }
          } else {
            // No conditional rules - field is never required unless business rules specify
            newFieldStates[field.slug] = {
              visible: field.is_visible !== false,
              required: false // Only conditional rules determine requirements
            }
          }
        }
      })
    } catch (error) {
      console.error('Error evaluating field states:', error)
      // Fallback to basic field states (no requirements without conditional rules)
      formSchema.fields.forEach(field => {
        if (field && field.slug) {
          newFieldStates[field.slug] = {
            visible: field.is_visible !== false,
            required: false // Only conditional rules should determine requirements
          }
        }
      })
    }
    
    setFieldStates(newFieldStates)
  }, [formSchema, formData, stage, user])

  const loadFormSchema = async () => {
    try {
      setLoading(true)
      setError(null)
      
      let endpoint = ''
      
      // Build endpoint based on form type
      switch (formType) {
        case 'internal_full':
          endpoint = `/api/pipelines/${pipelineId}/forms/internal/`
          break
        case 'public_filtered':
          endpoint = `/api/v1/public-forms/${pipelineSlug || pipelineId}/`
          break
        case 'stage_internal':
          endpoint = `/api/v1/pipelines/${pipelineId}/forms/stage/${stage}/internal/`
          break
        case 'stage_public':
          endpoint = `/api/v1/public-forms/${pipelineSlug || pipelineId}/stage/${stage}/`
          break
        case 'shared_record':
          if (!encryptedToken) {
            throw new Error('encryptedToken is required for shared_record formType')
          }
          endpoint = `/api/v1/shared-records/${encryptedToken}/form/`
          break
      }
      
      const response = await api.get(endpoint)
      
      // Debug: Log form schema to understand what backend is returning
      console.log('🔍 Dynamic Form Schema Loaded:', {
        endpoint,
        fieldCount: response.data?.fields?.length || 0,
        sampleField: response.data?.fields?.[0] || null,
        fieldsWithLegacyRequired: response.data?.fields?.filter((f: any) => f.is_required === true) || []
      })
      
      setFormSchema(response.data)
      
    } catch (err: any) {
      console.error('Failed to load form schema:', err)
      const errorMessage = err.response?.data?.error || err.message || 'Failed to load form'
      setError(errorMessage)
      if (onError) onError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const handleFieldChange = (fieldSlug: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      [fieldSlug]: value
    }))

    // Clear validation error for this field
    setValidationErrors(prev => 
      prev.filter(error => error.field !== fieldSlug)
    )
  }

  const validateForm = (): ValidationError[] => {
    const errors: ValidationError[] = []

    if (!formSchema) return errors

    formSchema.fields.forEach(field => {
      const value = formData[field.slug]
      const fieldState = fieldStates[field.slug]
      
      // Skip validation for hidden fields
      if (!fieldState?.visible) return
      
      // Use dynamic required state
      const isDynamicallyRequired = fieldState?.required || false
      
      // Convert DynamicFieldConfig to Field format expected by field system
      const fieldSystemField = {
        id: field.id.toString(),
        name: field.slug,
        display_name: field.display_name,
        field_type: field.type,
        field_config: field.field_config,
        ai_config: field.ai_config,
        // Use dynamic required state from fieldStates for validation
        is_required: isDynamicallyRequired,
        is_readonly: field.is_readonly,
        help_text: field.help_text,
        placeholder: field.placeholder,
        business_rules: field.business_rules
      }
      
      // Use the field system's validation
      const validationResult = FieldResolver.validate(fieldSystemField, value)
      if (!validationResult.isValid && validationResult.error) {
        errors.push({
          field: field.slug,
          message: validationResult.error
        })
      }

      // Additional form validation rules (custom rules from form builder)
      if (value && field.form_validation_rules) {
        const rules = field.form_validation_rules
        
        // Length validation
        if (rules.minLength && String(value).length < rules.minLength) {
          errors.push({
            field: field.slug,
            message: rules.customMessage || `Minimum length is ${rules.minLength} characters`
          })
        }
        
        if (rules.maxLength && String(value).length > rules.maxLength) {
          errors.push({
            field: field.slug,
            message: rules.customMessage || `Maximum length is ${rules.maxLength} characters`
          })
        }
        
        // Pattern validation
        if (rules.pattern) {
          const regex = new RegExp(rules.pattern)
          if (!regex.test(String(value))) {
            errors.push({
              field: field.slug,
              message: rules.customMessage || 'Please enter a valid value'
            })
          }
        }
        
        // Range validation for numbers
        if (rules.min !== undefined && parseFloat(value) < rules.min) {
          errors.push({
            field: field.slug,
            message: rules.customMessage || `Value must be at least ${rules.min}`
          })
        }
        
        if (rules.max !== undefined && parseFloat(value) > rules.max) {
          errors.push({
            field: field.slug,
            message: rules.customMessage || `Value must be at most ${rules.max}`
          })
        }
      }
    })

    return errors
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    const errors = validateForm()
    if (errors.length > 0) {
      setValidationErrors(errors)
      return
    }

    try {
      setSubmitting(true)
      
      const submitData = {
        form_mode: formType,
        stage,
        record_id: recordId,
        data: formData
      }
      
      let endpoint = ''
      let response

      if (formType.includes('public')) {
        endpoint = `/api/v1/public-forms/${pipelineSlug || pipelineId}/submit/`
        response = await api.post(endpoint, submitData)
      } else if (formType === 'shared_record') {
        // For shared records, don't make an API call here - let the parent component handle it
        // This allows the parent to use the correct SharedRecordViewSet endpoint with accessor info
        if (onSubmit) {
          onSubmit(formData)
        }
        setSubmitted(true)
        return
      } else {
        // Use the new dynamic forms endpoint that properly tracks submissions
        endpoint = `/api/v1/pipelines/${pipelineId}/forms/submit/`
        response = await api.post(endpoint, submitData)
      }
      
      setSubmitted(true)
      if (onSubmit) {
        onSubmit(formData)
      }
      
    } catch (err: any) {
      console.error('Form submission failed:', err)
      const errorMessage = err.response?.data?.error || err.message || 'Form submission failed'
      setError(errorMessage)
      if (onError) onError(errorMessage)
    } finally {
      setSubmitting(false)
    }
  }

  const renderFieldInput = (field: DynamicFieldConfig) => {
    const value = formData[field.slug]
    const hasError = validationErrors.some(error => error.field === field.slug)
    const error = validationErrors.find(error => error.field === field.slug)
    const fieldState = fieldStates[field.slug]
    
    // Use dynamic required state
    const isDynamicallyRequired = fieldState?.required || false
    
    // Convert DynamicFieldConfig to Field format expected by field system
    const fieldSystemField = {
      id: field.id.toString(),
      name: field.slug,
      display_name: field.display_name,
      field_type: field.type,
      field_config: field.field_config,
      ai_config: field.ai_config,
      // Removed is_required - FieldWrapper now evaluates requirements dynamically via business_rules
      is_readonly: field.is_readonly,
      help_text: field.help_text,
      placeholder: field.placeholder,
      business_rules: field.business_rules // Include business_rules for permission evaluation
    }
    
    return (
      <FieldWrapper
        field={fieldSystemField}
        value={value}
        onChange={(newValue) => handleFieldChange(field.slug, newValue)}
        onBlur={() => {}}
        disabled={field.is_readonly || readOnly}
        error={error?.message}
        autoFocus={false}
        context="form"
        showLabel={false} // We handle labels in the outer form
        showHelp={false}  // We handle help text in the outer form
        user={user} // Pass user context for permission evaluation
        formData={formData} // Pass form data for conditional rule evaluation
        pipeline_id={pipelineId ? Number(pipelineId) : undefined} // Pass pipeline context for USER fields
        record_id={recordId ? Number(recordId) : undefined} // Pass record context for USER fields
      />
    )
  }

  if (loading) {
    return (
      <div className={`flex items-center justify-center min-h-96 ${className}`}>
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 dark:border-blue-400 mx-auto mb-4"></div>
          <span className="text-gray-600 dark:text-gray-400">Loading form...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={`bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-6 ${className}`}>
        <div className="flex">
          <AlertCircle className="w-5 h-5 text-red-400 dark:text-red-300" />
          <div className="ml-3">
            <h3 className="text-red-800 dark:text-red-200 font-medium">Error Loading Form</h3>
            <p className="text-red-600 dark:text-red-300 mt-1">{error}</p>
            <button 
              onClick={loadFormSchema}
              className="mt-3 px-4 py-2 bg-red-100 dark:bg-red-900/40 text-red-800 dark:text-red-200 rounded-lg hover:bg-red-200 dark:hover:bg-red-900/60 transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (submitted) {
    return (
      <div className={`bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-xl p-6 text-center ${className}`}>
        <CheckCircle className="w-12 h-12 text-green-600 dark:text-green-400 mx-auto mb-4" />
        <h3 className="text-green-800 dark:text-green-200 font-medium text-lg">Form Submitted Successfully</h3>
        <p className="text-green-600 dark:text-green-300 mt-2">Thank you for your submission!</p>
      </div>
    )
  }

  if (!formSchema) {
    return (
      <div className={`text-center py-8 ${className}`}>
        <p className="text-gray-500 dark:text-gray-400">No form schema available</p>
      </div>
    )
  }

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 ${className}`}>
      {!embedMode && (
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">{formSchema.pipeline_name}</h2>
          <p className="text-gray-600 dark:text-gray-400 text-sm mt-1">
            {formSchema.metadata.visible_fields} fields • {formSchema.metadata.required_fields} required
          </p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="p-6 space-y-6">
        {formSchema.fields
          .filter(field => {
            const fieldState = fieldStates[field.slug]
            
            // Use dynamic visibility from field states if available
            if (fieldState !== undefined) {
              return fieldState.visible
            }
            
            // Fallback to basic visibility check
            if (!field.is_visible) return false
            
            // For public forms, no user permission checks needed
            if (formType.includes('public')) return true
            
            // For internal forms, check user permissions if user is available
            if (user) {
              // Convert form field to permission field format
              const permissionField: FieldWithPermissions = {
                id: field.id.toString(),
                name: field.slug,
                display_name: field.display_name,
                field_type: field.type,
                is_required: false, // Only conditional rules determine requirements
                is_visible_in_detail: field.is_visible,
                display_order: field.display_order,
                business_rules: field.business_rules || {}
              }
              
              const permissions = evaluateFieldPermissions(permissionField, user, formData, 'form')
              return permissions.visible
            }
            
            // Default to visible if no user (shouldn't happen for internal forms)
            return true
          })
          .sort((a, b) => a.display_order - b.display_order)
          .map((field) => {
            const fieldState = fieldStates[field.slug]
            const isDynamicallyRequired = fieldState?.required || false // Only use dynamic state
            
            return (
              <div key={field.slug}>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  {field.display_name}
                  {isDynamicallyRequired && <span className="text-red-500 ml-1">*</span>}
                </label>
                {field.help_text && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">{field.help_text}</p>
                )}
                {renderFieldInput(field)}
              </div>
            )
          })}

        {!readOnly && (
          <div className="pt-6 border-t border-gray-200 dark:border-gray-700">
            <button
              type="submit"
              disabled={submitting || validationErrors.length > 0}
              className={`w-full inline-flex items-center justify-center px-6 py-3 border border-transparent text-sm font-medium rounded-lg shadow-sm transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 ${
                submitting || validationErrors.length > 0
                  ? 'text-gray-500 bg-gray-100 dark:bg-gray-700 dark:text-gray-400 cursor-not-allowed'
                  : 'text-white bg-blue-600 hover:bg-blue-700 hover:shadow-lg transform hover:-translate-y-0.5'
              }`}
            >
              {submitting && (
                <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
              )}
              {submitting ? 'Submitting...' : recordId ? 'Update Record' : 'Submit Form'}
            </button>
          </div>
        )}
      </form>
    </div>
  )
}