import React, { useState, useEffect } from 'react'
import { FieldComponent, FieldRenderProps, ValidationResult, Field } from '../types'
import { getFieldConfig } from '../field-registry'

export const TextFieldComponent: FieldComponent = {
  renderInput: (props: FieldRenderProps) => {
    const { field, value, onChange, onBlur, onKeyDown, disabled, error, className, autoFocus } = props
    
    // Local state for editing to prevent re-render issues
    const [localValue, setLocalValue] = useState(value || '')
    const [isEditing, setIsEditing] = useState(false)
    
    // Update local value when external value changes and not editing
    useEffect(() => {
      if (!isEditing) {
        // Always sync with external value when not actively editing
        setLocalValue(value || '')
      }
    }, [value, isEditing])
    
    const maxLength = getFieldConfig(field, 'max_length')
    const minLength = getFieldConfig(field, 'min_length')
    const placeholder = field.placeholder || getFieldConfig(field, 'placeholder') || `Enter ${field.display_name || field.name}`
    const autoFormat = getFieldConfig(field, 'auto_format', false)
    const caseSensitive = getFieldConfig(field, 'case_sensitive', true)
    
    const inputClass = `w-full px-3 py-2 border rounded-lg transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-0 ${
      error 
        ? 'border-red-300 dark:border-red-600 focus:border-red-500 focus:ring-red-500 dark:focus:ring-red-400' 
        : 'border-gray-300 dark:border-gray-600 focus:border-blue-500 focus:ring-blue-500 dark:focus:ring-blue-400'
    } ${disabled 
        ? 'bg-gray-50 dark:bg-gray-700 cursor-not-allowed text-gray-500 dark:text-gray-400' 
        : 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white'
    } ${className || ''}`

    const handleFocus = () => {
      setIsEditing(true)
    }
    
    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      let newValue = e.target.value
      
      // Apply auto-formatting if enabled
      if (autoFormat) {
        // Title case formatting
        newValue = newValue.replace(/\w\S*/g, (txt) => 
          txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase()
        )
      }
      
      // Apply case sensitivity
      if (!caseSensitive) {
        newValue = newValue.toLowerCase()
      }
      
      // Update local state immediately for smooth typing
      setLocalValue(newValue)
      
      // Notify parent of change
      onChange(newValue)
    }
    
    const handleBlur = () => {
      // Ensure parent has the latest value before we stop editing
      if (localValue !== value) {
        onChange(localValue)
      }
      setIsEditing(false)
      onBlur?.()
    }
    
    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Escape') {
        // Reset to original value on escape
        setLocalValue(value || '')
        setIsEditing(false)
      } else if (e.key === 'Enter') {
        // Trigger blur to save the field
        e.currentTarget.blur()
      }
      onKeyDown?.(e)
    }

    return (
      <div>
        <input
          type="text"
          value={localValue}
          onChange={handleChange}
          onFocus={handleFocus}
          onBlur={handleBlur}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          className={inputClass}
          placeholder={placeholder}
          maxLength={maxLength}
          autoFocus={autoFocus}
          // Required attribute handled by FieldWrapper with permission evaluation
        />
        {error && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error}</p>
        )}
        {maxLength && (
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            {(value?.length || 0)}/{maxLength} characters
          </p>
        )}
      </div>
    )
  },

  formatValue: (value: any, field: Field, context?: string) => {
    if (value === null || value === undefined || value === '') {
      if (context === 'table') {
        return <span className="text-gray-400 italic">Empty</span>
      }
      return ''
    }
    
    const stringValue = String(value)
    
    // Use field builder max_length or fallback to context-based limits
    const configMaxLength = getFieldConfig(field, 'max_length')
    const displayMaxLength = context === 'table' ? 50 : (context === 'detail' ? 200 : configMaxLength || 500)
    
    if (stringValue.length > displayMaxLength) {
      return stringValue.substring(0, displayMaxLength) + '...'
    }
    
    return stringValue
  },

  validate: (value: any, field: Field): ValidationResult => {
    // Note: Required field validation is now handled by the permission system
    // and form-level validation. Individual field components only validate format/constraints.

    if (value) {
      const stringValue = String(value)
      const minLength = getFieldConfig(field, 'min_length')
      const maxLength = getFieldConfig(field, 'max_length')
      
      if (minLength && stringValue.length < minLength) {
        return {
          isValid: false,
          error: `Minimum length is ${minLength} characters`
        }
      }
      
      if (maxLength && stringValue.length > maxLength) {
        return {
          isValid: false,
          error: `Maximum length is ${maxLength} characters`
        }
      }
    }

    return { isValid: true }
  },

  getDefaultValue: (field: Field) => {
    return getFieldConfig(field, 'default_value', '')
  },

  isEmpty: (value: any) => !value || String(value).trim() === ''
}