import React, { useState, useEffect } from 'react'
import { FieldComponent, FieldRenderProps, ValidationResult, Field } from '../types'
import { getFieldConfig } from '../field-registry'

export const EmailFieldComponent: FieldComponent = {
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
    
    const placeholder = field.placeholder || getFieldConfig(field, 'placeholder') || `Enter ${field.display_name || field.name}`
    const autoLowercase = getFieldConfig(field, 'auto_lowercase', true)
    const trimWhitespace = getFieldConfig(field, 'trim_whitespace', true)
    
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
      
      // Apply configurations
      if (trimWhitespace) {
        newValue = newValue.trim()
      }
      if (autoLowercase) {
        newValue = newValue.toLowerCase()
      }
      
      // Update local state immediately for smooth typing
      setLocalValue(newValue)
      
      // Notify parent of change
      onChange(newValue)
    }
    
    const handleBlur = () => {
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
          type="email"
          value={localValue}
          onChange={handleChange}
          onFocus={handleFocus}
          onBlur={handleBlur}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          className={inputClass}
          placeholder={placeholder}
          autoFocus={autoFocus}
          required={field.is_required}
        />
        {error && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error}</p>
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
    
    const email = String(value)
    
    if (context === 'table' || context === 'detail') {
      return (
        <a 
          href={`mailto:${email}`} 
          className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 hover:underline"
          onClick={(e) => e.stopPropagation()}
        >
          {email}
        </a>
      )
    }
    
    return email
  },

  validate: (value: any, field: Field): ValidationResult => {
    if (field.is_required && (!value || value === '')) {
      return {
        isValid: false,
        error: `${field.display_name || field.name} is required`
      }
    }

    if (value) {
      const email = String(value).trim()
      
      // Basic email validation
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
      if (!emailRegex.test(email)) {
        return {
          isValid: false,
          error: 'Please enter a valid email address'
        }
      }
      
      // Check for common typos
      const commonTypos = [
        /@gmai\.com$/, /@gmail\.co$/, /@gmial\.com$/,
        /@yahoo\.co$/, /@yahooo\.com$/,
        /@hotmai\.com$/, /@hotmail\.co$/
      ]
      
      for (const typo of commonTypos) {
        if (typo.test(email)) {
          return {
            isValid: false,
            error: 'Please check the email address for typos'
          }
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


export const UrlFieldComponent: FieldComponent = {
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
    
    const handleFocus = () => {
      setIsEditing(true)
    }
    
    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      const newValue = e.target.value
      
      // Update local state immediately for smooth typing
      setLocalValue(newValue)
      
      // Notify parent
      onChange(newValue)
    }
    
    const handleBlur = () => {
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
    
    const placeholder = field.placeholder || getFieldConfig(field, 'placeholder') || `Enter ${field.display_name || field.name}`
    
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
        <input
          type="url"
          value={localValue}
          onChange={handleChange}
          onFocus={handleFocus}
          onBlur={handleBlur}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          className={inputClass}
          placeholder={placeholder}
          autoFocus={autoFocus}
          required={field.is_required}
        />
        {error && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error}</p>
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
    
    const url = String(value)
    
    if (context === 'table' || context === 'detail') {
      const displayUrl = url.length > 50 ? url.substring(0, 47) + '...' : url
      
      return (
        <a 
          href={url} 
          target="_blank" 
          rel="noopener noreferrer"
          className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 hover:underline"
          onClick={(e) => e.stopPropagation()}
        >
          {displayUrl}
        </a>
      )
    }
    
    return url
  },

  validate: (value: any, field: Field): ValidationResult => {
    if (field.is_required && (!value || value === '')) {
      return {
        isValid: false,
        error: `${field.display_name || field.name} is required`
      }
    }

    if (value) {
      const url = String(value).trim()
      
      try {
        new URL(url)
      } catch {
        // Try with https:// prefix
        try {
          new URL(`https://${url}`)
        } catch {
          return {
            isValid: false,
            error: 'Please enter a valid URL'
          }
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