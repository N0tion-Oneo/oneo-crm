import React from 'react'
import { FieldComponent, FieldRenderProps, ValidationResult, Field } from '../types'
import { getFieldConfig } from '../field-registry'

export const DateFieldComponent: FieldComponent = {
  renderInput: (props: FieldRenderProps) => {
    const { field, value, onChange, onBlur, onKeyDown, disabled, error, className, autoFocus } = props
    
    // Get field configurations
    const includeTime = getFieldConfig(field, 'include_time', false)
    const timeFormat = getFieldConfig(field, 'time_format', '24h')
    
    const inputClass = `w-full px-3 py-2 border rounded-lg transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-0 ${
      error 
        ? 'border-red-300 dark:border-red-600 focus:border-red-500 focus:ring-red-500 dark:focus:ring-red-400' 
        : 'border-gray-300 dark:border-gray-600 focus:border-blue-500 focus:ring-blue-500 dark:focus:ring-blue-400'
    } ${disabled 
        ? 'bg-gray-50 dark:bg-gray-700 cursor-not-allowed text-gray-500 dark:text-gray-400' 
        : 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white'
    } ${className || ''}`

    // Choose input type based on configuration
    const inputType = includeTime ? 'datetime-local' : 'date'
    
    // Convert value to appropriate format
    let inputValue = ''
    if (value) {
      const date = new Date(value)
      if (includeTime) {
        // For datetime-local: YYYY-MM-DDTHH:MM
        inputValue = date.toISOString().slice(0, 16)
      } else {
        // For date: YYYY-MM-DD
        inputValue = date.toISOString().split('T')[0]
      }
    }

    return (
      <div>
        <input
          type={inputType}
          value={inputValue}
          onChange={(e) => {
            const newValue = e.target.value
            if (newValue) {
              // Convert to ISO string for consistency
              const date = new Date(newValue)
              onChange(date.toISOString())
            } else {
              onChange(null)
            }
          }}
          onBlur={onBlur}
          onKeyDown={onKeyDown}
          disabled={disabled}
          className={inputClass}
          autoFocus={autoFocus}
          // Required attribute handled by FieldWrapper
        />
        {error && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error}</p>
        )}
        {includeTime && (
          <p className="mt-1 text-xs text-blue-600 dark:text-blue-400">
            Time format: {timeFormat === '12h' ? '12-hour (AM/PM)' : '24-hour'}
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
    
    try {
      const date = new Date(value)
      if (isNaN(date.getTime())) {
        return String(value)
      }
      
      // Use field builder date_format configuration
      const dateFormat = getFieldConfig(field, 'date_format', 'MM/DD/YYYY')
      const includeTime = getFieldConfig(field, 'include_time', false)
      const timeFormat = getFieldConfig(field, 'time_format', '24h')
      
      const day = date.getDate().toString().padStart(2, '0')
      const month = (date.getMonth() + 1).toString().padStart(2, '0')
      const year = date.getFullYear()
      
      let formattedDate = ''
      // Apply configured date format
      switch (dateFormat) {
        case 'DD/MM/YYYY':
          formattedDate = `${day}/${month}/${year}`
          break
        case 'YYYY-MM-DD':
          formattedDate = `${year}-${month}-${day}`
          break
        case 'MM/DD/YYYY':
        default:
          formattedDate = `${month}/${day}/${year}`
          break
      }
      
      // Add time if configured
      if (includeTime) {
        let hours = date.getHours()
        const minutes = date.getMinutes().toString().padStart(2, '0')
        
        if (timeFormat === '12h') {
          const ampm = hours >= 12 ? 'PM' : 'AM'
          hours = hours % 12
          if (hours === 0) hours = 12
          formattedDate += ` ${hours}:${minutes} ${ampm}`
        } else {
          formattedDate += ` ${hours.toString().padStart(2, '0')}:${minutes}`
        }
      }
      
      return formattedDate
    } catch {
      return String(value)
    }
  },

  validate: (value: any, field: Field): ValidationResult => {
    // Note: Required validation handled by permission system

    if (value) {
      const date = new Date(value)
      if (isNaN(date.getTime())) {
        return {
          isValid: false,
          error: 'Please enter a valid date'
        }
      }
      
      const minDate = getFieldConfig(field, 'min_date')
      const maxDate = getFieldConfig(field, 'max_date')
      
      if (minDate) {
        const min = new Date(minDate)
        if (date < min) {
          return {
            isValid: false,
            error: `Date must be after ${min.toLocaleDateString()}`
          }
        }
      }
      
      if (maxDate) {
        const max = new Date(maxDate)
        if (date > max) {
          return {
            isValid: false,
            error: `Date must be before ${max.toLocaleDateString()}`
          }
        }
      }
    }

    return { isValid: true }
  },

  getDefaultValue: (field: Field) => {
    const defaultValue = getFieldConfig(field, 'default_value')
    
    if (defaultValue) {
      if (defaultValue === 'today') {
        return new Date().toISOString()
      }
      
      try {
        const date = new Date(defaultValue)
        return isNaN(date.getTime()) ? null : date.toISOString()
      } catch {
        return null
      }
    }
    
    return null
  },

  isEmpty: (value: any) => !value || value === ''
}

export const DateTimeFieldComponent: FieldComponent = {
  renderInput: (props: FieldRenderProps) => {
    const { field, value, onChange, onBlur, onKeyDown, disabled, error, className, autoFocus } = props
    
    const inputClass = `w-full px-3 py-2 border rounded-lg transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-0 ${
      error 
        ? 'border-red-300 dark:border-red-600 focus:border-red-500 focus:ring-red-500 dark:focus:ring-red-400' 
        : 'border-gray-300 dark:border-gray-600 focus:border-blue-500 focus:ring-blue-500 dark:focus:ring-blue-400'
    } ${disabled 
        ? 'bg-gray-50 dark:bg-gray-700 cursor-not-allowed text-gray-500 dark:text-gray-400' 
        : 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white'
    } ${className || ''}`

    // Convert value to datetime-local format (YYYY-MM-DDTHH:mm)
    const datetimeValue = value ? new Date(value).toISOString().slice(0, 16) : ''

    return (
      <div>
        <input
          type="datetime-local"
          value={datetimeValue}
          onChange={(e) => {
            const newValue = e.target.value
            if (newValue) {
              // Convert to ISO string for consistency
              const date = new Date(newValue)
              onChange(date.toISOString())
            } else {
              onChange(null)
            }
          }}
          onBlur={onBlur}
          onKeyDown={onKeyDown}
          disabled={disabled}
          className={inputClass}
          autoFocus={autoFocus}
          // Required attribute handled by FieldWrapper
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
    
    try {
      const date = new Date(value)
      if (isNaN(date.getTime())) {
        return String(value)
      }
      
      if (context === 'table') {
        // Shorter format for table view
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
      
      return date.toLocaleString()
    } catch {
      return String(value)
    }
  },

  validate: (value: any, field: Field): ValidationResult => {
    // Note: Required validation handled by permission system

    if (value) {
      const date = new Date(value)
      if (isNaN(date.getTime())) {
        return {
          isValid: false,
          error: 'Please enter a valid date and time'
        }
      }
    }

    return { isValid: true }
  },

  getDefaultValue: (field: Field) => {
    const defaultValue = getFieldConfig(field, 'default_value')
    
    if (defaultValue) {
      if (defaultValue === 'now') {
        return new Date().toISOString()
      }
      
      try {
        const date = new Date(defaultValue)
        return isNaN(date.getTime()) ? null : date.toISOString()
      } catch {
        return null
      }
    }
    
    return null
  },

  isEmpty: (value: any) => !value || value === ''
}

export const TimeFieldComponent: FieldComponent = {
  renderInput: (props: FieldRenderProps) => {
    const { field, value, onChange, onBlur, onKeyDown, disabled, error, className, autoFocus } = props
    
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
          type="time"
          value={value || ''}
          onChange={(e) => onChange(e.target.value || null)}
          onBlur={onBlur}
          onKeyDown={onKeyDown}
          disabled={disabled}
          className={inputClass}
          autoFocus={autoFocus}
          // Required attribute handled by FieldWrapper
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
    
    // Time format is usually HH:MM
    return String(value)
  },

  validate: (value: any, field: Field): ValidationResult => {
    // Note: Required validation handled by permission system

    if (value) {
      // Basic time format validation (HH:MM)
      const timeRegex = /^([01]?[0-9]|2[0-3]):[0-5][0-9]$/
      if (!timeRegex.test(value)) {
        return {
          isValid: false,
          error: 'Please enter a valid time (HH:MM)'
        }
      }
    }

    return { isValid: true }
  },

  getDefaultValue: (field: Field) => {
    const defaultValue = getFieldConfig(field, 'default_value')
    
    if (defaultValue) {
      if (defaultValue === 'now') {
        const now = new Date()
        return `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`
      }
      
      return defaultValue
    }
    
    return null
  },

  isEmpty: (value: any) => !value || value === ''
}