'use client'

import React, { useState } from 'react'
import { FieldRenderer, FieldDisplay } from '@/lib/field-system/field-renderer'
import { Field } from '@/lib/field-system/types'
// Import field system to ensure initialization
import '@/lib/field-system'

const testFields: Field[] = [
  {
    id: '1',
    name: 'text_field',
    display_name: 'Limited Text Field',
    field_type: 'text',
    is_required: true,
    placeholder: 'Enter some text...',
    field_config: { 
      max_length: 50,
      min_length: 5
    }
  },
  {
    id: '2',
    name: 'textarea_field',
    display_name: 'Multi-line Text',
    field_type: 'textarea',
    is_required: false,
    placeholder: 'Enter multiple lines...',
    field_config: { 
      enable_rich_text: false
    }
  },
  {
    id: '3', 
    name: 'currency_field',
    display_name: 'Currency Field (USD)',
    field_type: 'number',
    is_required: false,
    field_config: { 
      format: 'currency',
      currency_code: 'USD',
      decimal_places: 2
    }
  },
  {
    id: '4',
    name: 'percentage_field',
    display_name: 'Percentage Field',
    field_type: 'number',
    is_required: false,
    field_config: {
      format: 'percentage',
      decimal_places: 1
    }
  },
  {
    id: '5',
    name: 'integer_field',
    display_name: 'Integer Field',
    field_type: 'number',
    is_required: false,
    field_config: {
      format: 'integer'
    }
  },
  {
    id: '6',
    name: 'email_field',
    display_name: 'Email Address',
    field_type: 'email',
    is_required: false,
    placeholder: 'Enter email address...',
    field_config: {
      auto_lowercase: true,
      trim_whitespace: true
    }
  },
  {
    id: '7',
    name: 'phone_field',
    display_name: 'Phone Number',
    field_type: 'phone',
    is_required: false,
    field_config: {
      require_country_code: true,
      default_country: 'US',
      format_display: true
    }
  },
  {
    id: '8',
    name: 'select_field', 
    display_name: 'Priority Level',
    field_type: 'select',
    is_required: true,
    field_config: {
      options: [
        { value: 'low', label: 'Low Priority' },
        { value: 'medium', label: 'Medium Priority' },
        { value: 'high', label: 'High Priority' },
        { value: 'urgent', label: 'Urgent' }
      ]
    }
  },
  {
    id: '9',
    name: 'multiselect_field',
    display_name: 'Multiple Skills',
    field_type: 'multiselect',
    is_required: false,
    field_config: {
      options: [
        { value: 'javascript', label: 'JavaScript' },
        { value: 'python', label: 'Python' },
        { value: 'react', label: 'React' },
        { value: 'django', label: 'Django' }
      ],
      allow_multiple: true
    }
  },
  {
    id: '10',
    name: 'tags_field',
    display_name: 'Tags',
    field_type: 'tags',
    is_required: false,
    field_config: {
      predefined_tags: ['urgent', 'important', 'followup', 'waiting'],
      allow_custom_tags: true,
      max_tags: 5
    }
  },
  {
    id: '11',
    name: 'date_field',
    display_name: 'Date Field', 
    field_type: 'date',
    is_required: false,
    field_config: {
      include_time: false,
      date_format: 'MM/DD/YYYY'
    }
  },
  {
    id: '12',
    name: 'datetime_field',
    display_name: 'Date & Time Field', 
    field_type: 'date',
    is_required: false,
    field_config: {
      include_time: true,
      date_format: 'MM/DD/YYYY',
      time_format: '12h'
    }
  },
  {
    id: '13',
    name: 'boolean_field',
    display_name: 'Agreement Checkbox',
    field_type: 'boolean',
    is_required: false,
    field_config: {}
  },
  {
    id: '14',
    name: 'url_field',
    display_name: 'Website URL',
    field_type: 'url',
    is_required: false,
    field_config: {
      auto_add_protocol: true,
      open_in_new_tab: true
    }
  },
  {
    id: '15',
    name: 'file_field',
    display_name: 'Upload File',
    field_type: 'file',
    is_required: false,
    field_config: {
      allowed_types: ['pdf', 'doc', 'docx', 'txt'],
      max_size: 5242880 // 5MB
    }
  },
  {
    id: '16',
    name: 'relation_field',
    display_name: 'Related Record (Test)',
    field_type: 'relation',
    is_required: false,
    field_config: {
      target_pipeline_id: 1,
      display_field: 'title'
    }
  },
  {
    id: '17',
    name: 'tags_field',
    display_name: 'Tags Field (Test)',
    field_type: 'tags',
    is_required: false,
    field_config: {
      predefined_tags: ['urgent', 'important', 'follow-up', 'marketing', 'sales'],
      allow_custom_tags: true,
      max_tags: 5,
      case_sensitive: false
    }
  }
]

export function TestFieldSystem() {
  const [formData, setFormData] = useState<Record<string, any>>({})
  const [errors, setErrors] = useState<Record<string, string>>({})

  const handleFieldChange = (fieldName: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      [fieldName]: value
    }))
    
    // Clear error for this field
    if (errors[fieldName]) {
      setErrors(prev => {
        const newErrors = { ...prev }
        delete newErrors[fieldName]
        return newErrors
      })
    }
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">Field Registry System Demo</h1>
      <p className="text-gray-600 dark:text-gray-400 mb-6">
        This demonstrates how field builder configurations are now applied automatically. 
        Try entering values to see formatting, validation, and contextual behavior.
      </p>
      
      <div className="space-y-4">
        {testFields.map(field => (
          <div key={field.id} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="flex justify-between items-start mb-3">
              <div>
                <label className="block text-sm font-medium mb-1">
                  {field.display_name}
                  {field.is_required && <span className="text-red-500 ml-1">*</span>}
                </label>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Type: {field.field_type} | Config: {JSON.stringify(field.field_config || {})}
                </p>
              </div>
            </div>
            
            <FieldRenderer
              field={field}
              value={formData[field.name] || ''}
              onChange={(value) => handleFieldChange(field.name, value)}
              error={errors[field.name]}
              context="form"
            />
          </div>
        ))}
      </div>
      
      <div className="mt-8 space-y-6">
        {/* Display formatted values */}
        <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <h3 className="font-semibold mb-4 text-blue-800 dark:text-blue-200">Formatted Display Values</h3>
          <div className="space-y-2">
            {testFields.map(field => {
              const value = formData[field.name]
              if (value === undefined || value === '') return null
              
              return (
                <div key={field.id} className="flex justify-between items-center py-1">
                  <span className="text-sm font-medium text-blue-700 dark:text-blue-300">
                    {field.display_name}:
                  </span>
                  <span className="text-sm text-blue-900 dark:text-blue-100">
                    <FieldDisplay field={field} value={value} context="detail" />
                  </span>
                </div>
              )
            })}
          </div>
        </div>
        
        {/* Raw form data */}
        <div className="p-4 bg-gray-100 dark:bg-gray-800 rounded-lg">
          <h3 className="font-semibold mb-2">Raw Form Data:</h3>
          <pre className="text-sm overflow-auto">
            {JSON.stringify(formData, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  )
}