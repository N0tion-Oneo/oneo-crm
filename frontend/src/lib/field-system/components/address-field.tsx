import React from 'react'
import { FieldComponent, FieldRenderProps, ValidationResult, Field } from '../types'
import { getFieldConfig } from '../field-registry'

export const AddressFieldComponent: FieldComponent = {
  renderInput: (props: FieldRenderProps) => {
    const { field, value, onChange, onBlur, onKeyDown, disabled, error, className, autoFocus } = props
    
    const addressFormat = getFieldConfig(field, 'address_format', 'structured')
    const components = getFieldConfig(field, 'components', {
      street_address: true,
      apartment_suite: true,
      city: true,
      state_province: true,
      postal_code: true,
      country: true
    })
    
    const inputClass = `w-full px-3 py-2 border rounded-lg transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-0 ${
      error 
        ? 'border-red-300 dark:border-red-600 focus:border-red-500 focus:ring-red-500 dark:focus:ring-red-400' 
        : 'border-gray-300 dark:border-gray-600 focus:border-blue-500 focus:ring-blue-500 dark:focus:ring-blue-400'
    } ${disabled 
        ? 'bg-gray-50 dark:bg-gray-700 cursor-not-allowed text-gray-500 dark:text-gray-400' 
        : 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white'
    } ${className || ''}`

    if (addressFormat === 'single_line') {
      return (
        <div>
          <input
            type="text"
            value={typeof value === 'string' ? value : value?.full_address || ''}
            onChange={(e) => onChange(e.target.value)}
            onBlur={onBlur}
            onKeyDown={onKeyDown}
            disabled={disabled}
            className={inputClass}
            placeholder={field.placeholder || 'Enter full address'}
            autoFocus={autoFocus}
            required={field.is_required}
          />
          {error && (
            <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error}</p>
          )}
        </div>
      )
    }

    // Structured address format
    const addressValue = typeof value === 'object' ? value : {}
    
    const updateAddressField = (fieldName: string, fieldValue: string) => {
      const newAddress = { ...addressValue, [fieldName]: fieldValue }
      onChange(newAddress)
    }

    return (
      <div className="space-y-3">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {components.street_address && (
            <div className="md:col-span-2">
              <input
                type="text"
                value={addressValue.street_address || ''}
                onChange={(e) => updateAddressField('street_address', e.target.value)}
                onBlur={onBlur}
                onKeyDown={onKeyDown}
                disabled={disabled}
                className={inputClass}
                placeholder="Street Address"
                autoFocus={autoFocus}
              />
            </div>
          )}
          
          {components.apartment_suite && (
            <div className="md:col-span-2">
              <input
                type="text"
                value={addressValue.apartment_suite || ''}
                onChange={(e) => updateAddressField('apartment_suite', e.target.value)}
                onBlur={onBlur}
                onKeyDown={onKeyDown}
                disabled={disabled}
                className={inputClass}
                placeholder="Apartment, suite, etc."
              />
            </div>
          )}
          
          {components.city && (
            <div>
              <input
                type="text"
                value={addressValue.city || ''}
                onChange={(e) => updateAddressField('city', e.target.value)}
                onBlur={onBlur}
                onKeyDown={onKeyDown}
                disabled={disabled}
                className={inputClass}
                placeholder="City"
              />
            </div>
          )}
          
          {components.state_province && (
            <div>
              <input
                type="text"
                value={addressValue.state_province || ''}
                onChange={(e) => updateAddressField('state_province', e.target.value)}
                onBlur={onBlur}
                onKeyDown={onKeyDown}
                disabled={disabled}
                className={inputClass}
                placeholder="State/Province"
              />
            </div>
          )}
          
          {components.postal_code && (
            <div>
              <input
                type="text"
                value={addressValue.postal_code || ''}
                onChange={(e) => updateAddressField('postal_code', e.target.value)}
                onBlur={onBlur}
                onKeyDown={onKeyDown}
                disabled={disabled}
                className={inputClass}
                placeholder="Postal Code"
              />
            </div>
          )}
          
          {components.country && (
            <div>
              <input
                type="text"
                value={addressValue.country || ''}
                onChange={(e) => updateAddressField('country', e.target.value)}
                onBlur={onBlur}
                onKeyDown={onKeyDown}
                disabled={disabled}
                className={inputClass}
                placeholder="Country"
              />
            </div>
          )}
        </div>
        
        {error && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error}</p>
        )}
      </div>
    )
  },

  formatValue: (value: any, field: Field, context?: string) => {
    if (!value) {
      if (context === 'table') {
        return <span className="text-gray-400 italic">No address</span>
      }
      return ''
    }
    
    const addressFormat = getFieldConfig(field, 'address_format', 'structured')
    
    if (addressFormat === 'single_line' || typeof value === 'string') {
      const address = typeof value === 'string' ? value : value.full_address || ''
      
      if (context === 'table' && address.length > 50) {
        return address.substring(0, 47) + '...'
      }
      
      return address
    }
    
    // Format structured address
    const components = getFieldConfig(field, 'components', {})
    const parts = []
    
    if (components.street_address && value.street_address) {
      parts.push(value.street_address)
    }
    if (components.apartment_suite && value.apartment_suite) {
      parts.push(value.apartment_suite)
    }
    if (components.city && value.city) {
      parts.push(value.city)
    }
    if (components.state_province && value.state_province) {
      parts.push(value.state_province)
    }
    if (components.postal_code && value.postal_code) {
      parts.push(value.postal_code)
    }
    if (components.country && value.country) {
      parts.push(value.country)
    }
    
    const fullAddress = parts.join(', ')
    
    if (context === 'table' && fullAddress.length > 50) {
      return fullAddress.substring(0, 47) + '...'
    }
    
    return fullAddress
  },

  validate: (value: any, field: Field): ValidationResult => {
    if (field.is_required && !value) {
      return {
        isValid: false,
        error: `${field.display_name || field.name} is required`
      }
    }

    if (value) {
      const addressFormat = getFieldConfig(field, 'address_format', 'structured')
      
      if (addressFormat === 'single_line') {
        const address = typeof value === 'string' ? value : value.full_address || ''
        if (field.is_required && !address.trim()) {
          return {
            isValid: false,
            error: 'Address cannot be empty'
          }
        }
      } else {
        // Validate structured address
        const components = getFieldConfig(field, 'components', {})
        const requiredComponents = Object.entries(components)
          .filter(([_, required]) => required)
          .map(([component, _]) => component)
        
        for (const component of requiredComponents) {
          if (!value[component] || !value[component].trim()) {
            const componentName = component.replace('_', ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())
            return {
              isValid: false,
              error: `${componentName} is required`
            }
          }
        }
      }
    }

    return { isValid: true }
  },

  getDefaultValue: (field: Field) => {
    const addressFormat = getFieldConfig(field, 'address_format', 'structured')
    const defaultValue = getFieldConfig(field, 'default_value')
    
    if (defaultValue !== undefined) {
      return defaultValue
    }
    
    return addressFormat === 'single_line' ? '' : {}
  },

  isEmpty: (value: any) => {
    if (!value) return true
    
    if (typeof value === 'string') {
      return !value.trim()
    }
    
    if (typeof value === 'object') {
      const hasAnyValue = Object.values(value).some(v => v && String(v).trim())
      return !hasAnyValue
    }
    
    return true
  }
}