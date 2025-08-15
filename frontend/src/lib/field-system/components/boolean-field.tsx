import React from 'react'
import { Checkbox } from '@/components/ui/checkbox'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Switch } from '@/components/ui/switch'
import { FieldComponent, FieldRenderProps, ValidationResult, Field } from '../types'
import { getFieldConfig } from '../field-registry'

export const BooleanFieldComponent: FieldComponent = {
  renderInput: (props: FieldRenderProps) => {
    const { field, value, onChange, onBlur, onKeyDown, disabled, error, className, autoFocus } = props
    
    const displayStyle = getFieldConfig(field, 'display_style', 'checkbox') // checkbox, toggle, radio
    const trueLabel = getFieldConfig(field, 'true_label', 'Yes')
    const falseLabel = getFieldConfig(field, 'false_label', 'No')
    
    const isChecked = Boolean(value)

    if (displayStyle === 'radio') {
      return (
        <div className={className}>
          <div className="space-y-2">
            <label className="flex items-center">
              <input
                type="radio"
                name={field.name}
                checked={isChecked === true}
                onChange={() => onChange(true)}
                onBlur={onBlur}
                disabled={disabled}
                className="mr-2 text-blue-600 focus:ring-blue-500 dark:focus:ring-blue-400"
                autoFocus={autoFocus}
              />
              <span className="text-sm text-gray-900 dark:text-white">{trueLabel}</span>
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                name={field.name}
                checked={isChecked === false}
                onChange={() => onChange(false)}
                onBlur={onBlur}
                disabled={disabled}
                className="mr-2 text-blue-600 focus:ring-blue-500 dark:focus:ring-blue-400"
              />
              <span className="text-sm text-gray-900 dark:text-white">{falseLabel}</span>
            </label>
          </div>
          {error && (
            <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error}</p>
          )}
        </div>
      )
    }

    if (displayStyle === 'toggle') {
      return (
        <div className={className}>
          <label className="flex items-center cursor-pointer">
            <div className="relative">
              <input
                type="checkbox"
                checked={isChecked}
                onChange={(e) => onChange(e.target.checked)}
                onBlur={onBlur}
                onKeyDown={onKeyDown}
                disabled={disabled}
                className="sr-only"
                autoFocus={autoFocus}
              />
              <div 
                className={`block w-14 h-8 rounded-full transition-colors ${isChecked ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600'} ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                onClick={() => !disabled && onChange(!isChecked)}
              >
                <div className={`absolute left-1 top-1 bg-white w-6 h-6 rounded-full transition-transform ${isChecked ? 'transform translate-x-6' : ''}`}></div>
              </div>
            </div>
            <span className="ml-3 text-sm text-gray-900 dark:text-white">
              {field.display_name || field.name}
            </span>
          </label>
          {error && (
            <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error}</p>
          )}
        </div>
      )
    }

    // Default checkbox style
    return (
      <div className={className}>
        <label className="flex items-center">
          <input
            type="checkbox"
            checked={isChecked}
            onChange={(e) => onChange(e.target.checked)}
            onBlur={onBlur}
            onKeyDown={onKeyDown}
            disabled={disabled}
            className="mr-2 rounded border-gray-300 dark:border-gray-600 text-blue-600 focus:ring-blue-500 dark:focus:ring-blue-400 dark:bg-gray-700"
            autoFocus={autoFocus}
          />
          <span className="text-sm text-gray-900 dark:text-white">
            {field.display_name || field.name}
          </span>
        </label>
        {error && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error}</p>
        )}
      </div>
    )
  },

  formatValue: (value: any, field: Field, context?: string) => {
    const trueLabel = getFieldConfig(field, 'true_label', 'Yes')
    const falseLabel = getFieldConfig(field, 'false_label', 'No')
    
    if (context === 'table') {
      return value ? '✓' : '✗'
    }
    
    return value ? trueLabel : falseLabel
  },

  validate: (value: any, field: Field): ValidationResult => {
    // Note: Required validation handled by permission system
    // Boolean fields generally don't require additional validation
    return { isValid: true }
  },

  getDefaultValue: (field: Field) => {
    const defaultValue = getFieldConfig(field, 'default_value')
    if (defaultValue !== undefined) {
      return Boolean(defaultValue)
    }
    return false
  },

  isEmpty: (value: any) => value === null || value === undefined
}