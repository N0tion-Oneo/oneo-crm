import React, { useState, useEffect } from 'react'
import { Textarea } from '@/components/ui/textarea'
import { FieldComponent, FieldRenderProps, ValidationResult, Field } from '../types'
import { getFieldConfig } from '../field-registry'

export const TextareaFieldComponent: FieldComponent = {
  renderInput: (props: FieldRenderProps) => {
    const { field, value, onChange, onBlur, onKeyDown, disabled, error, className, autoFocus } = props
    
    // Local state for editing to prevent re-render issues
    const [localValue, setLocalValue] = useState(value || '')
    const [isEditing, setIsEditing] = useState(false)
    
    // Update local value when external value changes and not editing
    useEffect(() => {
      if (!isEditing) {
        setLocalValue(value || '')
      }
    }, [value, isEditing])
    
    const maxLength = getFieldConfig(field, 'max_length')
    const minLength = getFieldConfig(field, 'min_length')
    const rows = getFieldConfig(field, 'rows', 4)
    const enableRichText = getFieldConfig(field, 'enable_rich_text', false)
    const placeholder = field.placeholder || getFieldConfig(field, 'placeholder') || `Enter ${field.display_name || field.name}`
    
    const inputClass = error 
      ? 'border-red-300 dark:border-red-600 focus:border-red-500 focus:ring-red-500 dark:focus:ring-red-400'
      : className || ''

    const handleFocus = () => {
      setIsEditing(true)
    }
    
    const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const newValue = e.target.value
      
      // Update local state immediately for smooth typing
      setLocalValue(newValue)
      
      // Notify parent of change
      onChange(newValue)
    }
    
    const handleBlur = () => {
      setIsEditing(false)
      onBlur?.()
    }
    
    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Escape') {
        // Reset to original value on escape
        setLocalValue(value || '')
        setIsEditing(false)
      } else if (e.key === 'Enter' && !e.shiftKey) {
        // Enter to save (Shift+Enter adds new lines)
        e.preventDefault()
        e.currentTarget.blur()
      }
      onKeyDown?.(e)
    }

    return (
      <div>
        <Textarea
          value={localValue}
          onChange={handleChange}
          onFocus={handleFocus}
          onBlur={handleBlur}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          className={inputClass}
          placeholder={placeholder}
          maxLength={maxLength}
          rows={rows}
          autoFocus={autoFocus}
          // Required attribute handled by FieldWrapper
        />
        {error && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error}</p>
        )}
        {maxLength && (
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            {(value?.length || 0)}/{maxLength} characters
          </p>
        )}
        {enableRichText && (
          <p className="mt-1 text-xs text-blue-600 dark:text-blue-400">
            Rich text editor enabled (basic HTML formatting allowed)
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
    const maxLength = getFieldConfig(field, 'max_display_length', context === 'table' ? 100 : 500)
    
    if (context === 'table') {
      // For table view, show first line only
      const firstLine = stringValue.split('\n')[0]
      if (firstLine.length > maxLength) {
        return firstLine.substring(0, maxLength) + '...'
      }
      return firstLine
    }
    
    if (stringValue.length > maxLength) {
      return stringValue.substring(0, maxLength) + '...'
    }
    
    return stringValue
  },

  validate: (value: any, field: Field): ValidationResult => {
    // Note: Required validation handled by permission system

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