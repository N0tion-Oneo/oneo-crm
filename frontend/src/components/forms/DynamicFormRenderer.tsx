'use client'

import React, { useState, useEffect } from 'react'
import { api } from '@/lib/api'
import { Save, AlertCircle, CheckCircle, RefreshCw } from 'lucide-react'

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
  form_validation_rules: Record<string, any>
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
  onSubmit?: (data: Record<string, any>) => void
  onError?: (error: string) => void
  embedMode?: boolean
  className?: string
}

export function DynamicFormRenderer({
  pipelineId,
  pipelineSlug,
  formType,
  stage,
  recordId,
  recordData,
  onSubmit,
  onError,
  embedMode = false,
  className = ''
}: DynamicFormRendererProps) {
  const [formSchema, setFormSchema] = useState<DynamicFormSchema | null>(null)
  const [formData, setFormData] = useState<Record<string, any>>({})
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load form schema
  useEffect(() => {
    loadFormSchema()
  }, [pipelineId, pipelineSlug, formType, stage, recordId])

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
          endpoint = `/api/public-forms/${pipelineSlug || pipelineId}/`
          break
        case 'stage_internal':
          endpoint = `/api/pipelines/${pipelineId}/forms/stage/${stage}/internal/`
          break
        case 'stage_public':
          endpoint = `/api/public-forms/${pipelineSlug || pipelineId}/stage/${stage}/`
          break
        case 'shared_record':
          endpoint = `/api/pipelines/${pipelineId}/records/${recordId}/share/`
          break
      }
      
      const response = await api.get(endpoint)
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
      
      // Required field validation
      if (field.is_required && (!value || value === '')) {
        errors.push({
          field: field.slug,
          message: `${field.display_name} is required`
        })
      }

      // Form validation rules
      if (value && field.form_validation_rules) {
        const rules = field.form_validation_rules
        
        // Type validation
        if (rules.type === 'email') {
          const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
          if (!emailRegex.test(value)) {
            errors.push({
              field: field.slug,
              message: rules.customMessage || 'Please enter a valid email address'
            })
          }
        }
        
        // Length validation
        if (rules.minLength && value.length < rules.minLength) {
          errors.push({
            field: field.slug,
            message: rules.customMessage || `Minimum length is ${rules.minLength} characters`
          })
        }
        
        if (rules.maxLength && value.length > rules.maxLength) {
          errors.push({
            field: field.slug,
            message: rules.customMessage || `Maximum length is ${rules.maxLength} characters`
          })
        }
        
        // Pattern validation
        if (rules.pattern) {
          const regex = new RegExp(rules.pattern)
          if (!regex.test(value)) {
            errors.push({
              field: field.slug,
              message: rules.customMessage || 'Please enter a valid value'
            })
          }
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
      if (formType.includes('public')) {
        endpoint = `/api/public-forms/${pipelineSlug || pipelineId}/submit/`
      } else {
        endpoint = `/api/pipelines/${pipelineId}/forms/submit/`
      }
      
      const response = await api.post(endpoint, submitData)
      
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
    const value = formData[field.slug] || ''
    const hasError = validationErrors.some(error => error.field === field.slug)
    const error = validationErrors.find(error => error.field === field.slug)

    const inputClass = `w-full px-3 py-2 border rounded-lg transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-0 ${
      hasError 
        ? 'border-red-300 dark:border-red-600 focus:border-red-500 focus:ring-red-500 dark:focus:ring-red-400' 
        : 'border-gray-300 dark:border-gray-600 focus:border-blue-500 focus:ring-blue-500 dark:focus:ring-blue-400'
    } ${field.is_readonly 
        ? 'bg-gray-50 dark:bg-gray-700 cursor-not-allowed text-gray-500 dark:text-gray-400' 
        : 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white'
    }`

    switch (field.type) {
      case 'textarea':
        return (
          <div>
            <textarea
              value={value}
              onChange={(e) => handleFieldChange(field.slug, e.target.value)}
              className={`${inputClass} min-h-[100px] resize-vertical`}
              placeholder={field.placeholder}
              disabled={field.is_readonly}
              required={field.is_required}
            />
            {hasError && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error?.message}</p>
            )}
          </div>
        )

      case 'select':
        const options = field.field_config?.options || []
        return (
          <div>
            <select
              value={value}
              onChange={(e) => handleFieldChange(field.slug, e.target.value)}
              className={inputClass}
              disabled={field.is_readonly}
              required={field.is_required}
            >
              <option value="">Select {field.display_name}</option>
              {options.map((option: any) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            {hasError && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error?.message}</p>
            )}
          </div>
        )

      case 'boolean':
        return (
          <div>
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={Boolean(value)}
                onChange={(e) => handleFieldChange(field.slug, e.target.checked)}
                className="mr-2 rounded border-gray-300 dark:border-gray-600 text-blue-600 focus:ring-blue-500 dark:focus:ring-blue-400 dark:bg-gray-700"
                disabled={field.is_readonly}
              />
              <span className="text-sm">{field.display_name}</span>
            </label>
          </div>
        )

      case 'date':
        return (
          <div>
            <input
              type="date"
              value={value ? new Date(value).toISOString().split('T')[0] : ''}
              onChange={(e) => handleFieldChange(field.slug, e.target.value)}
              className={inputClass}
              disabled={field.is_readonly}
              required={field.is_required}
            />
            {hasError && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error?.message}</p>
            )}
          </div>
        )

      case 'number':
      case 'decimal':
        return (
          <div>
            <input
              type="number"
              step={field.type === 'decimal' ? '0.01' : '1'}
              value={value}
              onChange={(e) => handleFieldChange(field.slug, e.target.value)}
              className={inputClass}
              placeholder={field.placeholder}
              disabled={field.is_readonly}
              required={field.is_required}
            />
            {hasError && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error?.message}</p>
            )}
          </div>
        )

      case 'multiselect':
        const multiselectOptions = field.field_config?.options || []
        const selectedValues = Array.isArray(value) ? value : []
        return (
          <div>
            <div className="space-y-2">
              {multiselectOptions.map((option: any) => (
                <label key={option.value} className="flex items-center">
                  <input
                    type="checkbox"
                    checked={selectedValues.includes(option.value)}
                    onChange={(e) => {
                      const newValues = e.target.checked
                        ? [...selectedValues, option.value]
                        : selectedValues.filter(v => v !== option.value)
                      handleFieldChange(field.slug, newValues)
                    }}
                    className="mr-2 rounded border-gray-300 dark:border-gray-600 text-blue-600 focus:ring-blue-500 dark:focus:ring-blue-400 dark:bg-gray-700"
                    disabled={field.is_readonly}
                  />
                  <span className="text-sm">{option.label}</span>
                </label>
              ))}
            </div>
            {hasError && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error?.message}</p>
            )}
          </div>
        )

      case 'phone':
        return (
          <div>
            <input
              type="tel"
              value={value}
              onChange={(e) => handleFieldChange(field.slug, e.target.value)}
              className={inputClass}
              placeholder={field.placeholder}
              disabled={field.is_readonly}
              required={field.is_required}
            />
            {hasError && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error?.message}</p>
            )}
          </div>
        )

      case 'file':
        return (
          <div>
            <input
              type="file"
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (file) {
                  handleFieldChange(field.slug, file.name)
                }
              }}
              className={`${inputClass} file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100`}
              disabled={field.is_readonly}
              required={field.is_required}
            />
            {hasError && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error?.message}</p>
            )}
          </div>
        )

      case 'ai':
        return (
          <div>
            <div className="bg-purple-50 border border-purple-200 rounded-lg p-3 mb-2">
              <div className="flex items-center text-purple-800 text-sm">
                <span className="w-2 h-2 bg-purple-500 rounded-full mr-2"></span>
                AI-Enhanced Field
              </div>
              <p className="text-purple-600 text-xs mt-1">
                This field will be processed by AI after form submission
              </p>
            </div>
            <textarea
              value={value}
              onChange={(e) => handleFieldChange(field.slug, e.target.value)}
              className={`${inputClass} min-h-[80px] resize-vertical`}
              placeholder={field.placeholder || 'Enter information for AI processing...'}
              disabled={field.is_readonly}
              required={field.is_required}
            />
            {hasError && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error?.message}</p>
            )}
          </div>
        )

      default:
        return (
          <div>
            <input
              type={field.type === 'email' ? 'email' : field.type === 'url' ? 'url' : 'text'}
              value={value}
              onChange={(e) => handleFieldChange(field.slug, e.target.value)}
              className={inputClass}
              placeholder={field.placeholder}
              disabled={field.is_readonly}
              required={field.is_required}
            />
            {hasError && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error?.message}</p>
            )}
          </div>
        )
    }
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
          .filter(field => field.is_visible)
          .sort((a, b) => a.display_order - b.display_order)
          .map((field) => (
            <div key={field.slug}>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                {field.display_name}
                {field.is_required && <span className="text-red-500 ml-1">*</span>}
              </label>
              {field.help_text && (
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">{field.help_text}</p>
              )}
              {renderFieldInput(field)}
            </div>
          ))}

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
      </form>
    </div>
  )
}