import React from 'react'
import { FieldComponent, FieldRenderProps, ValidationResult, Field } from '../types'
import { getFieldOptions, getFieldConfig } from '../field-registry'

export const SelectFieldComponent: FieldComponent = {
  renderInput: (props: FieldRenderProps) => {
    const { field, value, onChange, onBlur, onKeyDown, disabled, error, className, autoFocus } = props
    
    const options = getFieldOptions(field)
    const allowEmpty = !field.is_required
    const allowCustom = getFieldConfig(field, 'allow_custom', false)
    const placeholder = field.placeholder || `Select ${field.display_name || field.name}`
    
    const inputClass = `w-full px-3 py-2 border rounded-lg transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-0 ${
      error 
        ? 'border-red-300 dark:border-red-600 focus:border-red-500 focus:ring-red-500 dark:focus:ring-red-400' 
        : 'border-gray-300 dark:border-gray-600 focus:border-blue-500 focus:ring-blue-500 dark:focus:ring-blue-400'
    } ${disabled 
        ? 'bg-gray-50 dark:bg-gray-700 cursor-not-allowed text-gray-500 dark:text-gray-400' 
        : 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white'
    } ${className || ''}`

    return (
      <div>
        <select
          value={value || ''}
          onChange={(e) => onChange(e.target.value || null)}
          onBlur={onBlur}
          onKeyDown={onKeyDown}
          disabled={disabled}
          className={inputClass}
          autoFocus={autoFocus}
          required={field.is_required}
        >
          {allowEmpty && (
            <option value="">{placeholder}</option>
          )}
          {options.map((option, index) => (
            <option key={`${option.value}-${index}`} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        {error && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error}</p>
        )}
        {options.length === 0 && (
          <p className="mt-1 text-xs text-yellow-600 dark:text-yellow-400">
            No options configured for this field
          </p>
        )}
        {allowCustom && (
          <p className="mt-1 text-xs text-blue-600 dark:text-blue-400">
            Custom values are allowed for this field
          </p>
        )}
      </div>
    )
  },

  formatValue: (value: any, field: Field, context?: string) => {
    if (value === null || value === undefined || value === '') {
      if (context === 'table') {
        return <span className="text-gray-400 italic">—</span>
      }
      return ''
    }
    
    const options = getFieldOptions(field)
    const option = options.find(opt => opt.value === value)
    
    if (option) {
      return option.label
    }
    
    // Show warning for invalid option values
    if (context === 'table' || context === 'detail') {
      return <span className="text-red-500 italic">Invalid option: {String(value)}</span>
    }
    
    // Fallback to raw value if option not found
    return String(value)
  },

  validate: (value: any, field: Field): ValidationResult => {
    if (field.is_required && (!value || value === '')) {
      return {
        isValid: false,
        error: `${field.display_name || field.name} is required`
      }
    }

    if (value) {
      const options = getFieldOptions(field)
      const validValues = options.map(opt => opt.value)
      const allowCustom = getFieldConfig(field, 'allow_custom', false)
      
      if (options.length > 0 && !validValues.includes(value) && !allowCustom) {
        return {
          isValid: false,
          error: 'Please select a valid option'
        }
      }
    }

    return { isValid: true }
  },

  getDefaultValue: (field: Field) => {
    const options = getFieldOptions(field)
    const defaultValue = field.field_config?.default_value || field.config?.default_value
    
    if (defaultValue !== undefined) {
      return defaultValue
    }
    
    // If only one option and field is required, use it as default
    if (options.length === 1 && field.is_required) {
      return options[0].value
    }
    
    return null
  },

  isEmpty: (value: any) => !value || value === ''
}

export const MultiselectFieldComponent: FieldComponent = {
  renderInput: (props: FieldRenderProps) => {
    const { field, value, onChange, onBlur, onKeyDown, disabled, error, className, autoFocus } = props
    
    const options = getFieldOptions(field)
    const selectedValues = Array.isArray(value) ? value : []
    
    return (
      <div>
        <div className={`space-y-2 ${className || ''}`}>
          {options.map((option, index) => (
            <label key={`${option.value}-${index}`} className="flex items-center">
              <input
                type="checkbox"
                checked={selectedValues.includes(option.value)}
                onChange={(e) => {
                  const newValues = e.target.checked
                    ? [...selectedValues, option.value]
                    : selectedValues.filter(v => v !== option.value)
                  onChange(newValues.length > 0 ? newValues : null)
                }}
                onBlur={onBlur}
                disabled={disabled}
                className="mr-2 rounded border-gray-300 dark:border-gray-600 text-blue-600 focus:ring-blue-500 dark:focus:ring-blue-400 dark:bg-gray-700"
                autoFocus={autoFocus && index === 0}
              />
              <span className="text-sm text-gray-900 dark:text-white">{option.label}</span>
            </label>
          ))}
        </div>
        {error && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error}</p>
        )}
        {options.length === 0 && (
          <p className="mt-1 text-xs text-yellow-600 dark:text-yellow-400">
            No options configured for this field
          </p>
        )}
      </div>
    )
  },

  formatValue: (value: any, field: Field, context?: string) => {
    if (!Array.isArray(value) || value.length === 0) {
      if (context === 'table') {
        return <span className="text-gray-400 italic">None</span>
      }
      return ''
    }
    
    const options = getFieldOptions(field)
    const labels = value.map(val => {
      const option = options.find(opt => opt.value === val)
      return option ? option.label : String(val)
    })
    
    if (context === 'table' && labels.length > 3) {
      return `${labels.slice(0, 3).join(', ')} +${labels.length - 3} more`
    }
    
    return labels.join(', ')
  },

  validate: (value: any, field: Field): ValidationResult => {
    if (field.is_required && (!Array.isArray(value) || value.length === 0)) {
      return {
        isValid: false,
        error: `${field.display_name || field.name} is required`
      }
    }

    if (Array.isArray(value) && value.length > 0) {
      const options = getFieldOptions(field)
      const validValues = options.map(opt => opt.value)
      
      const invalidValues = value.filter(val => !validValues.includes(val))
      if (options.length > 0 && invalidValues.length > 0) {
        return {
          isValid: false,
          error: 'Please select valid options only'
        }
      }
    }

    return { isValid: true }
  },

  getDefaultValue: (field: Field) => {
    const defaultValue = field.field_config?.default_value || field.config?.default_value
    
    if (Array.isArray(defaultValue)) {
      return defaultValue.length > 0 ? defaultValue : null
    }
    
    return null
  },

  isEmpty: (value: any) => !Array.isArray(value) || value.length === 0
}