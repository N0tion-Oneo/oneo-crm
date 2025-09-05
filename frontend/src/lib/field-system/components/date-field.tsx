import React, { useState } from 'react'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { FieldComponent, FieldRenderProps, ValidationResult, Field } from '../types'
import { getFieldConfig } from '../field-registry'

// Duration input component
const DurationInput: React.FC<{
  value: any
  onChange: (value: any) => void
  onBlur?: () => void
  field: Field
  disabled?: boolean
  error?: string
  className?: string
}> = ({ value, onChange, onBlur, field, disabled, error, className }) => {
  const durationUnits = getFieldConfig(field, 'duration_units', ['days', 'weeks', 'months', 'years'])
  const allowCustom = getFieldConfig(field, 'allow_custom_duration', true)
  
  // Parse duration value (format: {value: number, unit: string})
  const parsedValue = value && typeof value === 'object' ? value : { value: '', unit: durationUnits[0] }
  
  const [customValue, setCustomValue] = useState(parsedValue.value?.toString() || '')
  const [selectedUnit, setSelectedUnit] = useState(parsedValue.unit || durationUnits[0])
  
  const updateDuration = (newValue: string, newUnit: string) => {
    const numericValue = parseInt(newValue)
    if (newValue === '' || isNaN(numericValue)) {
      onChange(null)
    } else {
      onChange({ value: numericValue, unit: newUnit })
    }
  }
  
  const inputClass = error 
    ? 'border-red-300 dark:border-red-600 focus:border-red-500 focus:ring-red-500 dark:focus:ring-red-400'
    : className || ''

  return (
    <div className="space-y-2">
      <div className="flex space-x-2">
        <Input
          type="number"
          value={customValue}
          onChange={(e) => {
            setCustomValue(e.target.value)
            updateDuration(e.target.value, selectedUnit)
          }}
          onBlur={onBlur}
          placeholder="Enter duration"
          min="0"
          disabled={disabled}
          className={`${inputClass} flex-1`}
        />
        <Select
          value={selectedUnit}
          onValueChange={(unit) => {
            setSelectedUnit(unit)
            updateDuration(customValue, unit)
            // Trigger immediate save when unit changes (like other select fields)
            if (onBlur) {
              onBlur()
            }
          }}
          disabled={disabled}
        >
          <SelectTrigger className="w-32">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {durationUnits.map((unit: string) => (
              <SelectItem key={unit} value={unit}>
                {unit.charAt(0).toUpperCase() + unit.slice(1)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      {error && (
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
      )}
    </div>
  )
}

export const DateFieldComponent: FieldComponent = {
  renderInput: (props: FieldRenderProps) => {
    const { field, value, onChange, onBlur, onKeyDown, disabled, error, className, autoFocus } = props
    
    // Get field configurations
    const fieldMode = getFieldConfig(field, 'field_mode', 'date')
    const includeTime = getFieldConfig(field, 'include_time', false)
    const timeFormat = getFieldConfig(field, 'time_format', '24h')
    
    const [inputMode, setInputMode] = useState<'date' | 'duration'>(
      fieldMode === 'duration' ? 'duration' : 'date'
    )
    
    const inputClass = error 
      ? 'border-red-300 dark:border-red-600 focus:border-red-500 focus:ring-red-500 dark:focus:ring-red-400'
      : className || ''

    // Handle duration-only mode
    if (fieldMode === 'duration') {
      return (
        <DurationInput
          value={value}
          onChange={onChange}
          onBlur={onBlur}
          field={field}
          disabled={disabled}
          error={error}
          className={className}
        />
      )
    }

    // Handle date-only mode
    if (fieldMode === 'date') {
      const inputType = includeTime ? 'datetime-local' : 'date'
      
      // Convert value to appropriate format for date input
      let inputValue = ''
      if (value && typeof value === 'string') {
        try {
          const date = new Date(value)
          if (includeTime) {
            inputValue = date.toISOString().slice(0, 16)
          } else {
            inputValue = date.toISOString().split('T')[0]
          }
        } catch {
          inputValue = ''
        }
      }

      return (
        <div>
          <Input
            type={inputType}
            value={inputValue}
            step={includeTime ? "300" : undefined}
            onChange={(e) => {
              const newValue = e.target.value
              if (newValue) {
                onChange(new Date(newValue).toISOString())
              } else {
                onChange(null)
              }
            }}
            onBlur={onBlur}
            onKeyDown={onKeyDown}
            disabled={disabled}
            className={inputClass}
            autoFocus={autoFocus}
          />
          {error && (
            <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error}</p>
          )}
          {includeTime && (
            <p className="mt-1 text-xs text-blue-600 dark:text-blue-400">
              Time format: {timeFormat === '12h' ? '12-hour (AM/PM)' : '24-hour'} • 5-minute intervals
            </p>
          )}
        </div>
      )
    }

    // Handle 'both' mode - allow switching between date and duration
    return (
      <div className="space-y-3">
        <div className="flex space-x-2">
          <Button
            type="button"
            variant={inputMode === 'date' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setInputMode('date')}
            disabled={disabled}
          >
            Date
          </Button>
          <Button
            type="button"
            variant={inputMode === 'duration' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setInputMode('duration')}
            disabled={disabled}
          >
            Duration
          </Button>
        </div>
        
        {inputMode === 'date' ? (
          <div>
            <Input
              type={includeTime ? 'datetime-local' : 'date'}
              value={value && typeof value === 'string' ? 
                (includeTime ? 
                  new Date(value).toISOString().slice(0, 16) : 
                  new Date(value).toISOString().split('T')[0]
                ) : ''
              }
              step={includeTime ? "300" : undefined}
              onChange={(e) => {
                const newValue = e.target.value
                if (newValue) {
                  onChange(new Date(newValue).toISOString())
                } else {
                  onChange(null)
                }
              }}
              onBlur={onBlur}
              onKeyDown={onKeyDown}
              disabled={disabled}
              className={inputClass}
              autoFocus={autoFocus}
            />
          </div>
        ) : (
          <DurationInput
            value={value}
            onChange={onChange}
            onBlur={onBlur}
            field={field}
            disabled={disabled}
            error={error}
            className={className}
          />
        )}
        
        {error && (
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
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
    
    const fieldMode = getFieldConfig(field, 'field_mode', 'date')
    
    // Handle duration values
    if (value && typeof value === 'object' && value.value && value.unit) {
      const durationDisplayFormat = getFieldConfig(field, 'duration_display_format', 'full')
      
      switch (durationDisplayFormat) {
        case 'short':
          const shortUnits: Record<string, string> = {
            'minutes': 'm', 'hours': 'h', 'days': 'd', 
            'weeks': 'w', 'months': 'mo', 'years': 'y'
          }
          return `${value.value}${shortUnits[value.unit] || value.unit.charAt(0)}`
        
        case 'numeric':
          // Convert to days for numeric display
          const toDays: Record<string, number> = {
            'minutes': 1/1440, 'hours': 1/24, 'days': 1,
            'weeks': 7, 'months': 30, 'years': 365
          }
          const days = value.value * (toDays[value.unit] || 1)
          return `${Math.round(days)} days`
        
        case 'full':
        default:
          const unit = value.value === 1 ? value.unit.slice(0, -1) : value.unit
          return `${value.value} ${unit}`
      }
    }
    
    // Handle date values (existing logic)
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
      const fieldMode = getFieldConfig(field, 'field_mode', 'date')
      
      // Handle duration validation
      if (value && typeof value === 'object' && value.value && value.unit) {
        const durationValue = value.value
        const durationUnit = value.unit
        
        if (typeof durationValue !== 'number' || durationValue <= 0) {
          return {
            isValid: false,
            error: 'Duration must be a positive number'
          }
        }
        
        const validUnits = getFieldConfig(field, 'duration_units', ['days', 'weeks', 'months', 'years'])
        if (!validUnits.includes(durationUnit)) {
          return {
            isValid: false,
            error: `Invalid duration unit: ${durationUnit}`
          }
        }
        
        // Check duration constraints
        const minDurationDays = getFieldConfig(field, 'min_duration_days')
        const maxDurationDays = getFieldConfig(field, 'max_duration_days')
        
        if (minDurationDays || maxDurationDays) {
          // Convert duration to days for comparison
          const toDays: Record<string, number> = {
            'minutes': 1/1440, 'hours': 1/24, 'days': 1,
            'weeks': 7, 'months': 30, 'years': 365
          }
          const durationInDays = durationValue * (toDays[durationUnit] || 1)
          
          if (minDurationDays && durationInDays < minDurationDays) {
            return {
              isValid: false,
              error: `Duration must be at least ${minDurationDays} days`
            }
          }
          
          if (maxDurationDays && durationInDays > maxDurationDays) {
            return {
              isValid: false,
              error: `Duration must be no more than ${maxDurationDays} days`
            }
          }
        }
        
        return { isValid: true }
      }
      
      // Handle date validation (existing logic)
      if (typeof value === 'string') {
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
    
    const inputClass = error 
      ? 'border-red-300 dark:border-red-600 focus:border-red-500 focus:ring-red-500 dark:focus:ring-red-400'
      : className || ''

    // Convert value to datetime-local format (YYYY-MM-DDTHH:mm)
    const datetimeValue = value ? new Date(value).toISOString().slice(0, 16) : ''

    return (
      <div>
        <Input
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
    
    const inputClass = error 
      ? 'border-red-300 dark:border-red-600 focus:border-red-500 focus:ring-red-500 dark:focus:ring-red-400'
      : className || ''

    return (
      <div>
        <Input
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