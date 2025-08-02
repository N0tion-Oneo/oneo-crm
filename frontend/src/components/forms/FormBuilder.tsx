'use client'

import React, { useState, useEffect } from 'react'
import { formsApi, pipelinesApi } from '@/lib/api'
import { FormTemplate, FormData, FieldConfig, InlineValidation } from '@/types/forms'

interface FormBuilderProps {
  form: FormTemplate | null
  pipelines: any[]
  onSave: (form: FormTemplate) => void
  onCancel: () => void
}

export default function FormBuilder({ form, pipelines, onSave, onCancel }: FormBuilderProps) {
  const [currentStep, setCurrentStep] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Form data state
  const [formData, setFormData] = useState<FormData>({
    name: form?.name || '',
    description: form?.description || '',
    pipeline: form?.pipeline?.toString() || '',
    form_type: form?.form_type || 'custom',
    success_message: form?.success_message || 'Thank you for your submission!',
    is_active: form?.is_active !== false
  })

  // Field management state
  const [fields, setFields] = useState<FieldConfig[]>([])
  const [availableFields, setAvailableFields] = useState<any[]>([])
  const [editingField, setEditingField] = useState<FieldConfig | null>(null)
  const [showFieldModal, setShowFieldModal] = useState(false)

  useEffect(() => {
    if (formData.pipeline) {
      loadPipelineFields()
    }
  }, [formData.pipeline])

  useEffect(() => {
    if (form?.field_configs && availableFields.length > 0) {
      const configuredFields = form.field_configs.map((config, index) => ({
        id: config.id,
        pipeline_field: typeof config.pipeline_field === 'string' ? parseInt(config.pipeline_field) : config.pipeline_field,
        pipelineField: availableFields.find(f => f.id == config.pipeline_field),
        display_order: config.display_order,
        is_visible: config.is_visible,
        is_readonly: config.is_readonly,
        custom_label: config.custom_label || '',
        custom_placeholder: config.custom_placeholder || '',
        custom_help_text: config.custom_help_text || '',
        validation: config.conditional_logic as InlineValidation || {},
        default_value: config.default_value,
        field_width: config.field_width,
        is_active: config.is_active
      }))
      setFields(configuredFields)
    }
  }, [form, availableFields])

  const loadPipelineFields = async () => {
    try {
      if (!formData.pipeline) return
      
      const response = await pipelinesApi.getFields(formData.pipeline.toString())
      setAvailableFields(response.data.results || [])
    } catch (err: any) {
      console.error('Error loading pipeline fields:', err)
      setError('Failed to load pipeline fields')
    }
  }

  const handleFormDataChange = (field: keyof FormData, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const handleAddField = (pipelineField: any) => {
    const newField: FieldConfig = {
      tempId: `temp_${Date.now()}`,
      pipeline_field: pipelineField.id,
      pipelineField,
      display_order: fields.length,
      is_visible: true,
      is_readonly: false,
      custom_label: '',
      custom_placeholder: '',
      custom_help_text: '',
      validation: {},
      default_value: null,
      field_width: 'full',
      is_active: true
    }
    
    setFields(prev => [...prev, newField])
  }

  const handleRemoveField = (fieldId: string | number) => {
    setFields(prev => prev.filter(f => 
      (typeof fieldId === 'string' ? f.tempId === fieldId : f.id === fieldId)
    ))
  }

  const handleFieldEdit = (field: FieldConfig) => {
    setEditingField(field)
    setShowFieldModal(true)
  }

  const handleFieldSave = (updatedField: FieldConfig) => {
    setFields(prev => prev.map(f => 
      (f.id === updatedField.id || f.tempId === updatedField.tempId) ? updatedField : f
    ))
    setShowFieldModal(false)
    setEditingField(null)
  }

  const handleMoveField = (fromIndex: number, toIndex: number) => {
    const newFields = [...fields]
    const [moved] = newFields.splice(fromIndex, 1)
    newFields.splice(toIndex, 0, moved)
    
    const updatedFields = newFields.map((field, index) => ({
      ...field,
      display_order: index
    }))
    
    setFields(updatedFields)
  }

  const handleSave = async () => {
    try {
      setLoading(true)
      setError(null)

      if (!formData.name || !formData.pipeline) {
        setError('Please fill in all required fields')
        return
      }

      if (fields.length === 0) {
        setError('Please add at least one field to the form')
        return
      }

      // Find the selected pipeline to get its slug
      const selectedPipeline = pipelines.find(p => p.id.toString() === formData.pipeline)
      if (!selectedPipeline) {
        setError('Selected pipeline not found')
        return
      }

      // Prepare form payload with pipeline slug
      const formPayload = {
        ...formData,
        pipeline: selectedPipeline.slug // Send slug instead of ID
      }

      // Create or update form
      let savedForm: FormTemplate
      if (form) {
        const response = await formsApi.updateForm(form.id.toString(), formPayload)
        savedForm = response.data
      } else {
        const response = await formsApi.createForm(formPayload)
        savedForm = response.data
      }

      // Save field configurations
      const fieldPromises = fields.map(async (field) => {
        // Find the pipeline field to get its slug
        const pipelineField = availableFields.find(f => f.id === field.pipeline_field)
        if (!pipelineField) {
          throw new Error(`Pipeline field with ID ${field.pipeline_field} not found`)
        }

        const fieldPayload = {
          form_template: savedForm.id,
          pipeline_field: pipelineField.slug, // Use slug instead of ID
          display_order: field.display_order,
          is_visible: field.is_visible,
          is_readonly: field.is_readonly,
          custom_label: field.custom_label,
          custom_placeholder: field.custom_placeholder,
          custom_help_text: field.custom_help_text,
          conditional_logic: field.validation, // Store validation in conditional_logic
          default_value: field.default_value,
          field_width: field.field_width,
          is_active: field.is_active
        }

        if (field.id) {
          return formsApi.updateFormField(field.id.toString(), fieldPayload)
        } else {
          return formsApi.createFormField(fieldPayload)
        }
      })

      await Promise.all(fieldPromises)

      // Return saved form with field configs
      const finalForm = { 
        ...savedForm, 
        field_configs: fields.map(f => ({
          ...f,
          form_template: savedForm.id,
          conditional_logic: f.validation
        })) as any
      }
      onSave(finalForm)
      
    } catch (err: any) {
      console.error('Error saving form:', err)
      setError(err.response?.data?.message || 'Failed to save form')
    } finally {
      setLoading(false)
    }
  }

  const renderStepIndicator = () => (
    <div className="flex items-center justify-center mb-8">
      {[1, 2].map((step) => (
        <div key={step} className="flex items-center">
          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
            currentStep >= step 
              ? 'bg-blue-600 text-white' 
              : 'bg-gray-200 text-gray-600'
          }`}>
            {step}
          </div>
          {step < 2 && (
            <div className={`w-16 h-0.5 mx-2 ${
              currentStep > step ? 'bg-blue-600' : 'bg-gray-200'
            }`} />
          )}
        </div>
      ))}
    </div>
  )

  const renderBasicConfiguration = () => (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Form Configuration</h2>
        <p className="text-gray-600 mb-6">Set up the basic information for your form.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Form Name *
          </label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => handleFormDataChange('name', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="Enter form name"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Source Pipeline *
          </label>
          <select
            value={formData.pipeline}
            onChange={(e) => handleFormDataChange('pipeline', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="">Select a pipeline</option>
            {pipelines.map(pipeline => (
              <option key={pipeline.id} value={pipeline.id}>
                {pipeline.name}
              </option>
            ))}
          </select>
        </div>

        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Description
          </label>
          <textarea
            value={formData.description}
            onChange={(e) => handleFormDataChange('description', e.target.value)}
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="Describe the purpose of this form"
          />
        </div>

        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Success Message
          </label>
          <textarea
            value={formData.success_message}
            onChange={(e) => handleFormDataChange('success_message', e.target.value)}
            rows={2}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="Thank you for your submission!"
          />
        </div>

        <div className="md:col-span-2">
          <div className="flex items-center">
            <input
              type="checkbox"
              id="is_active"
              checked={formData.is_active}
              onChange={(e) => handleFormDataChange('is_active', e.target.checked)}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
            <label htmlFor="is_active" className="ml-2 text-sm font-medium text-gray-700">
              Form is active and available for use
            </label>
          </div>
        </div>
      </div>
    </div>
  )

  const renderFieldConfiguration = () => (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Configure Form Fields</h2>
        <p className="text-gray-600 mb-6">Choose which fields to include and configure their validation.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Available Fields */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h3 className="font-medium text-gray-900 mb-4">Available Fields</h3>
          {availableFields.length > 0 ? (
            <div className="space-y-2">
              {availableFields.filter(field => 
                !fields.some(f => f.pipeline_field === field.id)
              ).map(field => (
                <div
                  key={field.id}
                  className="flex items-center justify-between p-3 bg-white border border-gray-200 rounded-lg hover:border-blue-300 cursor-pointer"
                  onClick={() => handleAddField(field)}
                >
                  <div>
                    <div className="font-medium text-sm">{field.display_name || field.name}</div>
                    <div className="text-xs text-gray-500">{field.field_type}</div>
                  </div>
                  <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-500">No available fields. Select a pipeline first.</p>
          )}
        </div>

        {/* Form Fields */}
        <div className="lg:col-span-2">
          <div className="flex justify-between items-center mb-4">
            <h3 className="font-medium text-gray-900">Form Fields ({fields.length})</h3>
          </div>
          
          {fields.length > 0 ? (
            <div className="space-y-3">
              {fields.map((field, index) => (
                <div
                  key={field.id || field.tempId}
                  className="flex items-center justify-between p-4 bg-white border border-gray-200 rounded-lg"
                >
                  <div className="flex items-center space-x-3">
                    <div className="flex flex-col space-y-1">
                      <button
                        onClick={() => index > 0 && handleMoveField(index, index - 1)}
                        disabled={index === 0}
                        className="text-gray-400 hover:text-gray-600 disabled:opacity-30"
                      >
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                        </svg>
                      </button>
                      <button
                        onClick={() => index < fields.length - 1 && handleMoveField(index, index + 1)}
                        disabled={index === fields.length - 1}
                        className="text-gray-400 hover:text-gray-600 disabled:opacity-30"
                      >
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                      </button>
                    </div>
                    <div>
                      <div className="font-medium text-sm">
                        {field.custom_label || field.pipelineField?.display_name || field.pipelineField?.name}
                      </div>
                      <div className="text-xs text-gray-500">
                        {field.pipelineField?.field_type} • {field.field_width}
                        {field.validation.required && ' • Required'}
                        {field.is_readonly && ' • Read-only'}
                        {!field.is_visible && ' • Hidden'}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => handleFieldEdit(field)}
                      className="px-3 py-1 text-blue-600 hover:bg-blue-50 rounded text-sm"
                    >
                      Configure
                    </button>
                    <button
                      onClick={() => handleRemoveField(field.id || field.tempId!)}
                      className="px-3 py-1 text-red-600 hover:bg-red-50 rounded text-sm"
                    >
                      Remove
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 border-2 border-dashed border-gray-300 rounded-lg">
              <p className="text-gray-500">No fields added yet. Add fields from the left panel.</p>
            </div>
          )}

          {/* Form Preview */}
          {fields.length > 0 && (
            <div className="mt-6 bg-gray-50 rounded-lg p-4">
              <h4 className="font-medium text-gray-900 mb-3">Form Preview</h4>
              <div className="space-y-3 bg-white p-4 rounded-lg border">
                <h5 className="font-medium text-gray-900">{formData.name || 'Untitled Form'}</h5>
                {formData.description && (
                  <p className="text-sm text-gray-600">{formData.description}</p>
                )}
                <div className="space-y-3">
                  {fields.filter(f => f.is_visible).map((field) => (
                    <div key={field.id || field.tempId} className="space-y-1">
                      <label className="block text-sm font-medium text-gray-700">
                        {field.custom_label || field.pipelineField?.display_name || field.pipelineField?.name}
                        {field.validation.required && <span className="text-red-500">*</span>}
                      </label>
                      <div className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                        {field.pipelineField?.field_type} field
                        {field.validation.type && ` • ${field.validation.type} validation`}
                        {field.custom_placeholder && ` • "${field.custom_placeholder}"`}
                      </div>
                    </div>
                  ))}
                </div>
                <div className="pt-3 border-t border-gray-200">
                  <button className="px-4 py-2 bg-blue-600 text-white rounded text-sm" disabled>
                    Submit Form
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )

  return (
    <div className="max-w-6xl mx-auto p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            {form ? 'Edit Form' : 'Create Form'}
          </h1>
          <p className="text-gray-600 mt-1">
            {form ? 'Modify your existing form' : 'Build a new form with custom fields and validation'}
          </p>
        </div>
        <button
          onClick={onCancel}
          className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
        >
          Cancel
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex">
            <svg className="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="ml-3">
              <p className="text-red-800">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Step Indicator */}
      {renderStepIndicator()}

      {/* Step Content */}
      <div className="bg-white rounded-lg border border-gray-200 p-8 mb-8">
        {currentStep === 1 ? renderBasicConfiguration() : renderFieldConfiguration()}
      </div>

      {/* Navigation */}
      <div className="flex justify-between">
        <button
          onClick={() => setCurrentStep(Math.max(1, currentStep - 1))}
          disabled={currentStep === 1}
          className="px-6 py-2 text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Previous
        </button>

        <div className="flex space-x-3">
          {currentStep < 2 ? (
            <button
              onClick={() => setCurrentStep(Math.min(2, currentStep + 1))}
              disabled={!formData.name || !formData.pipeline}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next: Configure Fields
            </button>
          ) : (
            <button
              onClick={handleSave}
              disabled={loading || fields.length === 0}
              className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
            >
              {loading && (
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              )}
              {form ? 'Update Form' : 'Create Form'}
            </button>
          )}
        </div>
      </div>

      {/* Field Configuration Modal */}
      {showFieldModal && editingField && (
        <FieldConfigurationModal
          field={editingField}
          onSave={handleFieldSave}
          onCancel={() => {
            setShowFieldModal(false)
            setEditingField(null)
          }}
        />
      )}
    </div>
  )
}

// Field Configuration Modal with Inline Validation
interface FieldModalProps {
  field: FieldConfig
  onSave: (field: FieldConfig) => void
  onCancel: () => void
}

function FieldConfigurationModal({ field, onSave, onCancel }: FieldModalProps) {
  const [fieldData, setFieldData] = useState<FieldConfig>(field)

  const handleChange = (key: keyof FieldConfig, value: any) => {
    setFieldData(prev => ({ ...prev, [key]: value }))
  }

  const handleValidationChange = (key: keyof InlineValidation, value: any) => {
    setFieldData(prev => ({
      ...prev,
      validation: { ...prev.validation, [key]: value }
    }))
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">
            Configure Field: {field.pipelineField?.display_name || field.pipelineField?.name}
          </h2>
        </div>

        <div className="p-6 space-y-6">
          {/* Display Configuration */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-4">Display Settings</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Custom Label
                </label>
                <input
                  type="text"
                  value={fieldData.custom_label || ''}
                  onChange={(e) => handleChange('custom_label', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder={field.pipelineField?.display_name || field.pipelineField?.name}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Field Width
                </label>
                <select
                  value={fieldData.field_width}
                  onChange={(e) => handleChange('field_width', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="full">Full Width</option>
                  <option value="half">Half Width</option>
                  <option value="third">Third Width</option>
                  <option value="quarter">Quarter Width</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Placeholder Text
                </label>
                <input
                  type="text"
                  value={fieldData.custom_placeholder || ''}
                  onChange={(e) => handleChange('custom_placeholder', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Enter placeholder text"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Default Value
                </label>
                <input
                  type="text"
                  value={fieldData.default_value || ''}
                  onChange={(e) => handleChange('default_value', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Enter default value"
                />
              </div>
            </div>

            <div className="mt-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Help Text
              </label>
              <textarea
                value={fieldData.custom_help_text || ''}
                onChange={(e) => handleChange('custom_help_text', e.target.value)}
                rows={2}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Provide helpful instructions for this field"
              />
            </div>
          </div>

          {/* Validation Configuration */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-4">Validation Rules</h3>
            
            {/* Required Field */}
            <div className="flex items-center mb-4">
              <input
                type="checkbox"
                id="required"
                checked={fieldData.validation.required || false}
                onChange={(e) => handleValidationChange('required', e.target.checked)}
                className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              <label htmlFor="required" className="ml-2 text-sm text-gray-700">
                Required field
              </label>
            </div>

            {/* Validation Type */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Validation Type
                </label>
                <select
                  value={fieldData.validation.type || ''}
                  onChange={(e) => handleValidationChange('type', e.target.value || undefined)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">No specific validation</option>
                  <option value="email">Email</option>
                  <option value="phone">Phone Number</option>
                  <option value="url">URL</option>
                  <option value="number">Number</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Custom Pattern (Regex)
                </label>
                <input
                  type="text"
                  value={fieldData.validation.pattern || ''}
                  onChange={(e) => handleValidationChange('pattern', e.target.value || undefined)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="^[A-Za-z0-9]+$"
                />
              </div>
            </div>

            {/* Length/Value Constraints */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Min Length
                </label>
                <input
                  type="number"
                  value={fieldData.validation.minLength || ''}
                  onChange={(e) => handleValidationChange('minLength', e.target.value ? parseInt(e.target.value) : undefined)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="0"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Max Length
                </label>
                <input
                  type="number"
                  value={fieldData.validation.maxLength || ''}
                  onChange={(e) => handleValidationChange('maxLength', e.target.value ? parseInt(e.target.value) : undefined)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="100"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Min Value
                </label>
                <input
                  type="number"
                  value={fieldData.validation.minValue || ''}
                  onChange={(e) => handleValidationChange('minValue', e.target.value ? parseFloat(e.target.value) : undefined)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="0"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Max Value
                </label>
                <input
                  type="number"
                  value={fieldData.validation.maxValue || ''}
                  onChange={(e) => handleValidationChange('maxValue', e.target.value ? parseFloat(e.target.value) : undefined)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="100"
                />
              </div>
            </div>

            {/* Custom Error Message */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Custom Error Message
              </label>
              <input
                type="text"
                value={fieldData.validation.customMessage || ''}
                onChange={(e) => handleValidationChange('customMessage', e.target.value || undefined)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Please enter a valid value"
              />
            </div>
          </div>

          {/* Field Options */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-4">Field Options</h3>
            <div className="space-y-3">
              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="is_visible"
                  checked={fieldData.is_visible}
                  onChange={(e) => handleChange('is_visible', e.target.checked)}
                  className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
                <label htmlFor="is_visible" className="ml-2 text-sm text-gray-700">
                  Field is visible
                </label>
              </div>

              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="is_readonly"
                  checked={fieldData.is_readonly}
                  onChange={(e) => handleChange('is_readonly', e.target.checked)}
                  className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
                <label htmlFor="is_readonly" className="ml-2 text-sm text-gray-700">
                  Field is read-only
                </label>
              </div>

              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="is_active"
                  checked={fieldData.is_active}
                  onChange={(e) => handleChange('is_active', e.target.checked)}
                  className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
                <label htmlFor="is_active" className="ml-2 text-sm text-gray-700">
                  Field is active
                </label>
              </div>
            </div>
          </div>
        </div>

        <div className="p-6 border-t border-gray-200 flex justify-end space-x-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
          >
            Cancel
          </button>
          <button
            onClick={() => onSave(fieldData)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Save Configuration
          </button>
        </div>
      </div>
    </div>
  )
}