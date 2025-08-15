import React, { useState, useEffect } from 'react'
import { Input } from '@/components/ui/input'
import { FieldComponent, FieldRenderProps, ValidationResult, Field } from '../types'
import { getFieldConfig } from '../field-registry'

export const NumberFieldComponent: FieldComponent = {
  renderInput: (props: FieldRenderProps) => {
    const { field, value, onChange, onBlur, onKeyDown, disabled, error, className, autoFocus } = props
    
    // Local state for editing to prevent re-render issues  
    // Extract display value from complex objects for input field
    const getDisplayValue = (val: any): string => {
      if (!val) return ''
      if (typeof val === 'object' && val.amount !== undefined) {
        return val.amount.toString()
      }
      return val.toString()
    }
    
    const [localValue, setLocalValue] = useState(getDisplayValue(value))
    const [isEditing, setIsEditing] = useState(false)
    
    // Update local value when external value changes and not editing
    useEffect(() => {
      if (!isEditing) {
        setLocalValue(getDisplayValue(value))
      }
    }, [value, isEditing])
    
    // Get field builder configurations
    const format = getFieldConfig(field, 'format', '')
    const currencyCode = getFieldConfig(field, 'currency_code')
    const decimalPlaces = getFieldConfig(field, 'decimal_places', 2)
    const min = getFieldConfig(field, 'min_value')
    const max = getFieldConfig(field, 'max_value')
    const step = format === 'currency' || field.field_type === 'decimal' ? '0.01' : '1'
    
    // Simple currency display for fixed currency fields
    const isCurrency = format === 'currency'
    const isPercentage = format === 'percentage'
    const isAutoIncrement = format === 'auto_increment'
    
    // Currency symbols
    const getCurrencySymbol = (code: string) => {
      const symbols: Record<string, string> = {
        'USD': '$', 'EUR': '€', 'GBP': '£', 'ZAR': 'R',
        'CAD': 'CA$', 'AUD': 'A$', 'JPY': '¥', 'CNY': '¥'
      }
      return symbols[code] || code
    }
    
    // Auto-increment fields should be read-only
    const isFieldDisabled = disabled || isAutoIncrement
    
    // Common handlers for all input types
    const handleFocus = () => {
      setIsEditing(true)
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
    
    const handleNumberChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      const newValue = e.target.value
      
      // Update local state immediately for smooth typing
      setLocalValue(newValue)
      
      // Parse and notify parent
      if (newValue === '') {
        onChange(null)
      } else {
        const numValue = parseFloat(newValue)
        if (!isNaN(numValue)) {
          // For currency fields with fixed currency code, send currency object
          if (isCurrency && currencyCode) {
            const currencyObject = {
              amount: numValue,
              currency: currencyCode
            }
            onChange(currencyObject)
          } else {
            // For non-currency fields, send simple numbers
            onChange(numValue)
          }
        }
      }
    }
    
    const inputClass = error 
      ? 'border-red-300 dark:border-red-600 focus:border-red-500 focus:ring-red-500 dark:focus:ring-red-400'
      : className || ''

    return (
      <div>
        {isCurrency && currencyCode ? (
          // Fixed currency field with prefix
          <div className="flex items-center space-x-2">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {getCurrencySymbol(currencyCode)}
            </span>
            <Input
              type="number"
              value={localValue}
              onChange={handleNumberChange}
              onFocus={handleFocus}
              onBlur={handleBlur}
              onKeyDown={handleKeyDown}
              disabled={isFieldDisabled}
              className={`flex-1 ${inputClass}`}
              placeholder="Enter amount"
              min={min}
              max={max}
              step={step}
              autoFocus={autoFocus}
              // Required attribute handled by FieldWrapper
            />
          </div>
        ) : isPercentage ? (
          // Percentage input with % indicator
          <div className="relative">
            <Input
              type="number"
              value={localValue}
              onChange={handleNumberChange}
              onFocus={handleFocus}
              onBlur={handleBlur}
              onKeyDown={handleKeyDown}
              disabled={isFieldDisabled}
              className={`${inputClass} pr-8`}
              placeholder="Enter percentage"
              min={min}
              max={max}
              step="0.1"
              autoFocus={autoFocus}
              // Required attribute handled by FieldWrapper
            />
            <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
              <span className="text-gray-500 dark:text-gray-400 text-sm">%</span>
            </div>
          </div>
        ) : isCurrency && !currencyCode ? (
          (() => {
            // State management for currency fields
            const [currentCurrency, setCurrentCurrency] = useState(() => {
              // Parse existing value to get currency
              if (value && typeof value === 'object' && value.currency) {
                return value.currency
              }
              return 'USD' // Default currency
            })
            
            const [currentAmount, setCurrentAmount] = useState(() => {
              // Parse existing value to get amount
              if (typeof value === 'number') {
                return value
              } else if (value && typeof value === 'object' && value.amount !== undefined) {
                return value.amount
              }
              return 0
            })
            
            // Sync currency state with external value changes (from backend saves)
            useEffect(() => {
              if (!isEditing) {
                if (value && typeof value === 'object' && value.currency) {
                  setCurrentCurrency(value.currency)
                  if (value.amount !== undefined) {
                    setCurrentAmount(value.amount)
                  }
                } else if (typeof value === 'number') {
                  setCurrentAmount(value)
                } else if (value === null || value === undefined) {
                  setCurrentAmount(0)
                }
              }
            }, [value, isEditing])
            
            const updateCurrencyValue = (newAmount: number | null, newCurrency: string) => {
              if (newAmount === null) {
                onChange(null)
              } else {
                // Send currency object with both amount and currency for proper backend validation
                const currencyObject = {
                  amount: newAmount,
                  currency: newCurrency
                }
                
                
                // Send complete currency object so backend can validate and store both amount and currency
                onChange(currencyObject)
              }
            }
            
            return (
              <div 
                className="flex items-center space-x-2" 
                onBlur={(e) => {
                  // Only call parent onBlur if focus is leaving the entire currency field container
                  const isLeavingContainer = !e.currentTarget.contains(e.relatedTarget as Node)
                  if (isLeavingContainer && onBlur) {
                    onBlur()
                  }
                }}
              >
                {/* Currency selector */}
                <select
                  className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 min-w-[100px]"
                  value={currentCurrency}
                  disabled={isFieldDisabled}
                  onChange={(e) => {
                    const newCurrency = e.target.value
                    setCurrentCurrency(newCurrency)
                    updateCurrencyValue(currentAmount, newCurrency)
                  }}
                >
                  <option value="USD">USD $</option>
                  <option value="EUR">EUR €</option>
                  <option value="GBP">GBP £</option>
                  <option value="ZAR">ZAR R</option>
                  <option value="CAD">CAD $</option>
                  <option value="AUD">AUD $</option>
                  <option value="JPY">JPY ¥</option>
                  <option value="CNY">CNY ¥</option>
                </select>

                {/* Amount input */}
                <Input
                  type="number"
                  value={localValue}
                  onChange={(e) => {
                    const newValue = e.target.value
                    // Update local value for smooth typing
                    setLocalValue(newValue)
                    
                    if (newValue === '') {
                      setCurrentAmount(0)
                      updateCurrencyValue(null, currentCurrency)
                    } else {
                      const numValue = parseFloat(newValue)
                      if (!isNaN(numValue)) {
                        setCurrentAmount(numValue)
                        updateCurrencyValue(numValue, currentCurrency)
                      }
                    }
                  }}
                  onFocus={handleFocus}
                  onKeyDown={handleKeyDown}
                  disabled={isFieldDisabled}
                  className={`flex-1 ${inputClass}`}
                  placeholder="Enter amount"
                  min={min}
                  max={max}
                  step={step}
                  autoFocus={autoFocus}
                  // Required attribute handled by FieldWrapper
                />
              </div>
            )
          })()
        ) : (
          // Regular number or auto-increment input
          <Input
            type={isAutoIncrement ? "text" : "number"}
            value={isAutoIncrement ? `#${(value || 0).toString().padStart(6, '0')}` : localValue}
            onChange={isAutoIncrement ? undefined : handleNumberChange}
            onFocus={isAutoIncrement ? undefined : handleFocus}
            onBlur={isAutoIncrement ? onBlur : handleBlur}
            onKeyDown={isAutoIncrement ? onKeyDown : handleKeyDown}
            disabled={isFieldDisabled}
            className={inputClass}
            placeholder={isAutoIncrement ? "Auto-generated" : field.placeholder || `Enter ${field.display_name || field.name}`}
            min={isAutoIncrement ? undefined : min}
            max={isAutoIncrement ? undefined : max}
            step={isAutoIncrement ? undefined : step}
            autoFocus={isAutoIncrement ? false : autoFocus}
            // Required attribute handled by FieldWrapper
            readOnly={isAutoIncrement}
          />
        )}
        
        {error && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error}</p>
        )}
        
        {isAutoIncrement && (
          <p className="mt-1 text-xs text-blue-600 dark:text-blue-400">
            This field is automatically generated and cannot be edited
          </p>
        )}
      </div>
    )
  },

  formatValue: (value: any, field: Field, context?: string) => {
    // Handle currency objects with null/empty amounts
    if (typeof value === 'object' && value !== null && value.amount !== undefined) {
      if (value.amount === null || value.amount === undefined || value.amount === '') {
        if (context === 'table') {
          return <span className="text-gray-400 italic">—</span>
        }
        return ''
      }
      // For currency objects, format as currency with the object's currency
      const numValue = Number(value.amount)
      if (isNaN(numValue)) {
        return String(value)
      }
      
      const decimalPlaces = getFieldConfig(field, 'decimal_places', 2)
      try {
        return new Intl.NumberFormat('en-US', {
          style: 'currency',
          currency: value.currency || 'USD',
          minimumFractionDigits: decimalPlaces,
          maximumFractionDigits: decimalPlaces
        }).format(numValue)
      } catch {
        // Fallback for unsupported currency codes
        const symbols: Record<string, string> = {
          'USD': '$', 'EUR': '€', 'GBP': '£', 'ZAR': 'R',
          'CAD': 'CA$', 'AUD': 'A$', 'JPY': '¥', 'CNY': '¥'
        }
        const symbol = symbols[value.currency] || value.currency
        return `${symbol} ${numValue.toLocaleString('en-US', { 
          minimumFractionDigits: decimalPlaces,
          maximumFractionDigits: decimalPlaces 
        })}`
      }
    }
    
    if (value === null || value === undefined || value === '') {
      if (context === 'table') {
        return <span className="text-gray-400 italic">—</span>
      }
      return ''
    }
    
    const numValue = Number(value)
    if (isNaN(numValue)) {
      return String(value)
    }

    const format = getFieldConfig(field, 'format', '')
    const currencyCode = getFieldConfig(field, 'currency_code', 'USD')
    const decimalPlaces = getFieldConfig(field, 'decimal_places', field.field_type === 'decimal' ? 2 : 0)
    
    // Format based on field configuration
    if (format === 'currency') {
      try {
        return new Intl.NumberFormat('en-US', {
          style: 'currency',
          currency: currencyCode,
          minimumFractionDigits: decimalPlaces,
          maximumFractionDigits: decimalPlaces
        }).format(numValue)
      } catch {
        // Fallback for unsupported currency codes
        const symbols: Record<string, string> = {
          'USD': '$', 'EUR': '€', 'GBP': '£', 'ZAR': 'R',
          'CAD': 'CA$', 'AUD': 'A$', 'JPY': '¥', 'CNY': '¥'
        }
        const symbol = symbols[currencyCode] || currencyCode
        return `${symbol} ${numValue.toLocaleString('en-US', { 
          minimumFractionDigits: decimalPlaces,
          maximumFractionDigits: decimalPlaces 
        })}`
      }
    }
    
    if (format === 'percentage') {
      return `${numValue.toFixed(decimalPlaces)}%`
    }
    
    if (format === 'auto_increment') {
      return `#${numValue.toString().padStart(6, '0')}`
    }
    
    if (field.field_type === 'decimal' || decimalPlaces > 0) {
      return numValue.toLocaleString('en-US', { 
        minimumFractionDigits: decimalPlaces,
        maximumFractionDigits: decimalPlaces 
      })
    }
    
    return numValue.toLocaleString('en-US')
  },

  validate: (value: any, field: Field): ValidationResult => {
    // Handle currency objects - check if amount is null/empty
    let actualValue = value
    if (typeof value === 'object' && value !== null && value.amount !== undefined) {
      actualValue = value.amount
    }
    
    // Check if field is required and value is empty
    const isEmpty = actualValue === null || actualValue === undefined || actualValue === ''
    // Note: Required validation handled by permission system

    // If not empty, validate the numeric value
    if (!isEmpty) {
      let numValue: number
      
      // Handle currency objects
      if (typeof value === 'object' && value !== null && value.amount !== undefined) {
        numValue = Number(value.amount)
      } else {
        numValue = Number(value)
      }
      
      if (isNaN(numValue)) {
        return {
          isValid: false,
          error: 'Please enter a valid number'
        }
      }
      
      const min = getFieldConfig(field, 'min_value')
      const max = getFieldConfig(field, 'max_value')
      
      if (min !== undefined && numValue < min) {
        return {
          isValid: false,
          error: `Value must be at least ${min}`
        }
      }
      
      if (max !== undefined && numValue > max) {
        return {
          isValid: false,
          error: `Value must be no more than ${max}`
        }
      }
    }

    return { isValid: true }
  },

  getDefaultValue: (field: Field) => {
    const defaultValue = getFieldConfig(field, 'default_value')
    if (defaultValue !== undefined) {
      const numValue = Number(defaultValue)
      return isNaN(numValue) ? null : numValue
    }
    return null
  },

  isEmpty: (value: any) => {
    // Handle currency objects - check if amount is null/empty
    if (typeof value === 'object' && value !== null && value.amount !== undefined) {
      return value.amount === null || value.amount === undefined || value.amount === ''
    }
    return value === null || value === undefined || value === ''
  }
}