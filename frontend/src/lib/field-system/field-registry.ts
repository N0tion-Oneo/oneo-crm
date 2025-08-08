// Field registry system for centralized field management
import React from 'react'
import { FieldComponent, Field, FieldRenderProps, FieldDisplayProps, ValidationResult } from './types'

// Registry to store field components
const fieldRegistry = new Map<string, FieldComponent>()

/**
 * Register a field component for a specific field type
 */
export function registerFieldComponent(fieldType: string, component: FieldComponent) {
  fieldRegistry.set(fieldType, component)
}

/**
 * Get field component for a specific field type
 */
export function getFieldComponent(fieldType: string): FieldComponent | undefined {
  return fieldRegistry.get(fieldType)
}

/**
 * Get all registered field types
 */
export function getRegisteredFieldTypes(): string[] {
  return Array.from(fieldRegistry.keys())
}

/**
 * Check if a field type is registered
 */
export function isFieldTypeRegistered(fieldType: string): boolean {
  return fieldRegistry.has(fieldType)
}

/**
 * Smart field component resolver - handles fallbacks and configuration
 */
export class FieldResolver {
  /**
   * Resolve field component with fallback logic
   */
  static resolveComponent(field: Field): FieldComponent {
    // Try exact field type match first
    let component = fieldRegistry.get(field.field_type)
    
    if (component) {
      return component
    }

    // Fallback mapping for similar types
    const fallbackMap: Record<string, string> = {
      'text': 'text',
      'textarea': 'textarea', 
      'number': 'number',
      'decimal': 'number',
      'currency': 'number',
      'percentage': 'number',
      'integer': 'number',
      'float': 'number',
      'boolean': 'boolean',
      'date': 'date',
      'datetime': 'datetime',
      'time': 'time',
      'select': 'select',
      'multiselect': 'multiselect',
      'radio': 'select', // Radio uses select component with single selection
      'checkbox': 'multiselect', // Checkbox group uses multiselect
      'email': 'email',
      'phone': 'phone',
      'url': 'url',
      'file': 'file',
      'image': 'file',
      'address': 'address',
      'tags': 'tags',
      'relation': 'relation',
      'button': 'button',
      'record_data': 'record_data',
      'ai_field': 'ai',
      'ai': 'ai',
      'ai_generated': 'ai',
      'user': 'user',
      'computed': 'computed',
      'formula': 'formula'
    }

    const fallbackType = fallbackMap[field.field_type]
    if (fallbackType) {
      component = fieldRegistry.get(fallbackType)
      if (component) {
        return component
      }
    }

    // Final fallback to text component
    component = fieldRegistry.get('text')
    if (component) {
      return component
    }

    // If no text component, create a minimal default
    return {
      renderInput: (props: FieldRenderProps) => {
        return React.createElement('input', {
          type: 'text',
          value: props.value || '',
          onChange: (e: any) => props.onChange(e.target.value),
          onBlur: props.onBlur,
          onKeyDown: props.onKeyDown,
          disabled: props.disabled,
          className: `w-full px-3 py-2 border rounded-lg ${props.error ? 'border-red-500' : 'border-gray-300'} ${props.className || ''}`,
          placeholder: field.placeholder || `Enter ${field.display_name || field.name}`,
          autoFocus: props.autoFocus
        })
      },
      formatValue: (value: any) => {
        if (value === null || value === undefined || value === '') {
          return ''
        }
        return String(value)
      },
      validate: (value: any, field: Field): ValidationResult => {
        // Note: Required field validation handled by permission system
        return { isValid: true }
      },
      getDefaultValue: () => '',
      isEmpty: (value: any) => !value || value === ''
    }
  }

  /**
   * Render field input with resolved component
   */
  static renderInput(field: Field, props: Omit<FieldRenderProps, 'field'>): JSX.Element {
    const component = this.resolveComponent(field)
    return component.renderInput({ ...props, field })
  }

  /**
   * Format field value with resolved component
   */
  static formatValue(field: Field, value: any, context?: string): string | JSX.Element {
    const component = this.resolveComponent(field)
    return component.formatValue(value, field, context)
  }

  /**
   * Validate field value with resolved component
   */
  static validate(field: Field, value: any): ValidationResult {
    const component = this.resolveComponent(field)
    if (component.validate) {
      return component.validate(value, field)
    }
    
    // Note: Default validation no longer checks is_required 
    // Requirements are handled by the permission system
    
    return { isValid: true }
  }

  /**
   * Get default value for field
   */
  static getDefaultValue(field: Field): any {
    const component = this.resolveComponent(field)
    if (component.getDefaultValue) {
      return component.getDefaultValue(field)
    }
    
    // Extract from field config
    const config = field.field_config || field.config || {}
    if (config.default_value !== undefined) {
      return config.default_value
    }
    
    return null
  }

  /**
   * Check if field value is empty
   */
  static isEmpty(field: Field, value: any): boolean {
    const component = this.resolveComponent(field)
    if (component.isEmpty) {
      return component.isEmpty(value)
    }
    
    return !value || value === ''
  }
}

/**
 * Utility function to get field configuration with fallbacks
 */
export function getFieldConfig(field: Field, key: string, defaultValue?: any): any {
  // Try field_config first (new format)
  if (field.field_config && field.field_config[key] !== undefined) {
    return field.field_config[key]
  }
  
  // Fall back to config (legacy format)
  if (field.config && field.config[key] !== undefined) {
    return field.config[key]
  }
  
  return defaultValue
}

/**
 * Utility function to get field options (for select/multiselect fields)
 */
export function getFieldOptions(field: Field): Array<{ value: any, label: string }> {
  const options = getFieldConfig(field, 'options', [])
  
  // Ensure options are in correct format
  if (Array.isArray(options)) {
    return options.map(option => {
      if (typeof option === 'string') {
        return { value: option, label: option }
      }
      if (typeof option === 'object' && option.value !== undefined) {
        return {
          value: option.value,
          label: option.label || String(option.value)
        }
      }
      return { value: option, label: String(option) }
    })
  }
  
  return []
}

/**
 * Registry initialization and cleanup
 */
export function clearFieldRegistry() {
  fieldRegistry.clear()
}

export function getRegistryStats() {
  return {
    totalRegistered: fieldRegistry.size,
    registeredTypes: Array.from(fieldRegistry.keys())
  }
}