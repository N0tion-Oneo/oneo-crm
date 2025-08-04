'use client'

import React, { useState } from 'react'
import { FieldRenderer } from '@/lib/field-system/field-renderer'
import { Field } from '@/lib/field-system/types'
// Import field system to ensure initialization
import '@/lib/field-system'

const enhancedInputTests: Field[] = [
  {
    id: 'datetime_field',
    name: 'datetime_field',
    display_name: 'Interview DateTime (with time picker)',
    field_type: 'date',
    field_config: {
      include_time: true,
      time_format: '12h',
      date_format: 'MM/DD/YYYY'
    }
  },
  {
    id: 'date_only_field',
    name: 'date_only_field', 
    display_name: 'Date Only (no time)',
    field_type: 'date',
    field_config: {
      include_time: false,
      date_format: 'DD/MM/YYYY'
    }
  },
  {
    id: 'toggle_boolean',
    name: 'toggle_boolean',
    display_name: 'Toggle Switch Style',
    field_type: 'boolean',
    field_config: {
      display_style: 'toggle',
      true_label: 'Enabled',
      false_label: 'Disabled'
    }
  },
  {
    id: 'radio_boolean',
    name: 'radio_boolean',
    display_name: 'Radio Button Style',
    field_type: 'boolean', 
    field_config: {
      display_style: 'radio',
      true_label: 'I Agree to Terms',
      false_label: 'I Do Not Agree'
    }
  },
  {
    id: 'auto_increment_number',
    name: 'auto_increment_number',
    display_name: 'Auto-Increment ID (Read-Only)',
    field_type: 'number',
    field_config: {
      format: 'auto_increment'
    }
  },
  {
    id: 'currency_usd',
    name: 'currency_usd',
    display_name: 'USD Currency Field',
    field_type: 'number',
    field_config: {
      format: 'currency',
      currency_code: 'USD',
      decimal_places: 2,
      thousands_separator: true
    }
  },
  {
    id: 'currency_zar_fixed',
    name: 'currency_zar_fixed',
    display_name: 'ZAR Currency Field (Fixed - like your Sales Pipeline)',
    field_type: 'number',
    field_config: {
      format: 'currency',
      currency_code: 'ZAR',
      decimal_places: 2,
      thousands_separator: true,
      allow_currency_selection: false
    }
  },
  {
    id: 'currency_any',
    name: 'currency_any',
    display_name: 'Multi-Currency Field (User Can Select Currency)',
    field_type: 'number',
    field_config: {
      format: 'currency',
      decimal_places: 2,
      thousands_separator: true,
      allow_currency_selection: true
    }
  },
  {
    id: 'percentage_field',
    name: 'percentage_field',
    display_name: 'Percentage Field',
    field_type: 'number',
    field_config: {
      format: 'percentage',
      decimal_places: 1,
      min_value: 0,
      max_value: 100
    }
  },
  {
    id: 'select_custom',
    name: 'select_custom',
    display_name: 'Select with Custom Values Allowed',
    field_type: 'select',
    field_config: {
      options: [
        { value: 'small', label: 'Small Business' },
        { value: 'medium', label: 'Medium Enterprise' },
        { value: 'large', label: 'Large Corporation' }
      ],
      allow_custom: true
    }
  },
  {
    id: 'formatted_text',
    name: 'formatted_text',
    display_name: 'Auto-Formatted Text (Title Case)',
    field_type: 'text',
    field_config: {
      auto_format: true,
      case_sensitive: false,
      max_length: 50
    }
  },
  {
    id: 'rich_textarea',
    name: 'rich_textarea',
    display_name: 'Rich Text Area',
    field_type: 'textarea',
    field_config: {
      enable_rich_text: true,
      max_length: 500,
      rows: 6
    }
  },
  {
    id: 'auto_email',
    name: 'auto_email',
    display_name: 'Auto-Lowercase Email',
    field_type: 'email',
    field_config: {
      auto_lowercase: true,
      trim_whitespace: true
    }
  }
]

export function TestEnhancedInputs() {
  const [formData, setFormData] = useState<Record<string, any>>({
    auto_increment_number: 42, // Example auto-increment value
    datetime_field: new Date().toISOString(),
    toggle_boolean: true,
    currency_usd: 15750.25, // Simple number (fixed currency)
    currency_zar_fixed: 3000.00, // Simple number (fixed currency)
    currency_any: { amount: 5000.00, currency: 'EUR' }, // Currency object (user selectable)
    percentage_field: 67.5
  })
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
      <h1 className="text-2xl font-bold mb-2">Enhanced Input Controls Test</h1>
      <p className="text-gray-600 dark:text-gray-400 mb-6">
        Testing enhanced input components with backend field configurations. 
        These should show time pickers, toggles, auto-formatting, etc.
      </p>
      
      <div className="space-y-6">
        {enhancedInputTests.map(field => (
          <div key={field.id} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="mb-3">
              <h3 className="font-medium text-lg">{field.display_name}</h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Type: {field.field_type} | Config: {JSON.stringify(field.field_config)}
              </p>
            </div>
            
            <FieldRenderer
              field={field}
              value={formData[field.name]}
              onChange={(value) => handleFieldChange(field.name, value)}
              error={errors[field.name]}
              context="form"
            />
            
            {formData[field.name] !== undefined && formData[field.name] !== '' && (
              <div className="mt-3 p-2 bg-gray-50 dark:bg-gray-800 rounded text-sm">
                <strong>Current Value:</strong> {JSON.stringify(formData[field.name])}
              </div>
            )}
          </div>
        ))}
      </div>
      
      <div className="mt-8 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
        <h3 className="font-semibold mb-2 text-blue-800 dark:text-blue-200">Expected Behaviors:</h3>
        <ul className="text-sm text-blue-700 dark:text-blue-300 space-y-1">
          <li>• <strong>DateTime field</strong> should show date + time picker (datetime-local input)</li>
          <li>• <strong>Date Only field</strong> should show only date picker</li>
          <li>• <strong>Toggle Boolean</strong> should show a sliding switch, not checkbox</li>
          <li>• <strong>Radio Boolean</strong> should show two radio buttons for Yes/No</li>
          <li>• <strong>Auto-Increment</strong> should be read-only with # prefix (e.g., #000042)</li>
          <li>• <strong>USD Currency</strong> should show fixed "$ USD" + number input (currency is fixed)</li>
          <li>• <strong>ZAR Fixed Currency</strong> should show fixed "R ZAR" + number input (like your Sales Pipeline)</li>
          <li>• <strong>Multi-Currency</strong> should show dropdown selector with all currencies + number input (check console for debug messages)</li>
          <li>• <strong>Percentage</strong> should show number input with % symbol and min/max validation</li>
          <li>• <strong>Select Custom</strong> should indicate custom values are allowed</li>
          <li>• <strong>Auto-Format Text</strong> should convert to Title Case as you type</li>
          <li>• <strong>Rich Textarea</strong> should indicate rich text capabilities</li>
          <li>• <strong>Auto Email</strong> should convert to lowercase as you type</li>
        </ul>
      </div>
      
      <div className="mt-4 p-4 bg-gray-100 dark:bg-gray-800 rounded-lg">
        <h3 className="font-semibold mb-2">All Form Data:</h3>
        <pre className="text-sm overflow-auto">
          {JSON.stringify(formData, null, 2)}
        </pre>
      </div>
    </div>
  )
}