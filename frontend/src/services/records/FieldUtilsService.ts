// FieldUtilsService - Field formatting, validation, and utility functions
import React from 'react'
import { RecordField, Record, FieldGroup } from '@/types/records'
import { Field } from '@/lib/field-system/types'
import { FieldResolver } from '@/lib/field-system/field-registry'

export class FieldUtilsService {
  /**
   * Convert RecordField to Field type for field registry
   */
  static convertToFieldType(recordField: RecordField): Field {
    return {
      id: recordField.id,
      name: recordField.name,
      display_name: recordField.display_name,
      field_type: recordField.field_type as string,
      field_config: recordField.field_config,
      config: recordField.config,
      is_readonly: false,
      help_text: undefined,
      placeholder: undefined
    }
  }


  /**
   * Format field value for display in table (returns JSX or string)
   */
  static formatFieldValue(field: RecordField, value: any): React.ReactNode {
    if (value === null || value === undefined) {
      return ''
    }

    try {
      const fieldForRegistry = this.convertToFieldType(field)
      const formattedValue = FieldResolver.formatValue(fieldForRegistry, value, 'table')
      
      // Return JSX elements directly for proper rendering
      if (React.isValidElement(formattedValue)) {
        return formattedValue
      }
      
      return String(formattedValue || '')
    } catch (error) {
      console.warn(`Error formatting field ${field.name}:`, error)
      return this.fallbackFormat(field.field_type, value)
    }
  }

  /**
   * Fallback formatting when field registry fails
   */
  private static fallbackFormat(fieldType: string, value: any): React.ReactNode {
    switch (fieldType) {
      case 'date':
        return value ? new Date(value).toLocaleDateString() : ''
      
      case 'datetime':
        return value ? new Date(value).toLocaleString() : ''
      
      case 'time':
        return value ? new Date(`1970-01-01T${value}`).toLocaleTimeString() : ''
      
      case 'boolean':
        return value ? 'Yes' : 'No'
      
      case 'tags':
        return Array.isArray(value) ? value.join(', ') : ''
      
      case 'multiselect':
        return Array.isArray(value) ? value.join(', ') : ''
      
      case 'currency':
        return value ? `$${Number(value).toFixed(2)}` : ''
      
      case 'percentage':
        return value ? `${Number(value)}%` : ''
      
      case 'email':
        return value || ''
      
      case 'phone':
        return value || ''
      
      case 'url':
        return value || ''
      
      default:
        return String(value || '')
    }
  }

  /**
   * Get column width class for field type
   */
  static getColumnWidth(field: RecordField): string {
    switch (field.field_type) {
      case 'boolean':
        return 'w-20' // Very small for checkboxes
      case 'date':
      case 'datetime':
        return 'w-32' // Medium for dates
      case 'time':
        return 'w-24' // Small for time
      case 'number':
      case 'decimal':
        return 'w-24' // Small for numbers
      case 'email':
      case 'phone':
        return 'w-48' // Medium for contact info
      case 'url':
        return 'w-40' // Medium for URLs
      case 'tags':
        return 'w-56' // Larger for tag arrays
      case 'textarea':
        return 'w-64' // Larger for long text
      case 'ai_field':
        return 'w-64' // Larger for AI-generated content
      case 'button':
        return 'w-32' // Medium for buttons
      case 'file':
      case 'image':
        return 'w-40' // Medium for file names
      case 'relation':
        return 'w-48' // Medium for related records
      case 'select':
      case 'multiselect':
        return 'w-40' // Medium for selections
      default:
        return 'w-48' // Default medium width for text fields
    }
  }

  /**
   * Check if field should be interactive in table context
   */
  static isInteractiveField(field: RecordField): boolean {
    return ['button', 'boolean', 'relation'].includes(field.field_type)
  }

  /**
   * Get field type icon mapping
   */
  static getFieldTypeIcon(fieldType: string): string {
    const iconMap: { [key: string]: string } = {
      text: 'Type',
      textarea: 'FileText',
      number: 'Hash',
      decimal: 'Hash',
      integer: 'Hash',
      float: 'Hash',
      currency: 'Hash',
      percentage: 'Hash',
      boolean: 'CheckSquare',
      date: 'Calendar',
      datetime: 'Calendar',
      time: 'Calendar',
      select: 'CheckSquare',
      multiselect: 'CheckSquare',
      radio: 'CheckSquare',
      checkbox: 'CheckSquare',
      email: 'Mail',
      phone: 'Phone',
      url: 'Link',
      address: 'Hash',
      file: 'FileText',
      image: 'Image',
      relation: 'Link',
      user: 'Users',
      ai: 'Bot',
      ai_field: 'Bot',
      button: 'Bot',
      tags: 'Tag'
    }
    
    return iconMap[fieldType] || 'Type'
  }

  /**
   * Get visible fields sorted by display order
   */
  static getVisibleFieldsSorted(
    fields: RecordField[], 
    visibleFields: Set<string>
  ): RecordField[] {
    return fields
      .filter(field => visibleFields.has(field.name))
      .sort((a, b) => (a.display_order || 0) - (b.display_order || 0))
  }

  /**
   * Get visible fields sorted by field groups, then by display order within each group
   */
  static getVisibleFieldsGroupSorted(
    fields: RecordField[], 
    visibleFields: Set<string>,
    fieldGroups: FieldGroup[] = []
  ): RecordField[] {
    const visibleFieldsList = fields.filter(field => visibleFields.has(field.name))
    
    // If no field groups, fallback to regular sorting
    if (fieldGroups.length === 0) {
      return this.getVisibleFieldsSorted(fields, visibleFields)
    }

    // Group fields by field_group
    const groups = new Map<string | null, RecordField[]>()
    
    // Organize visible fields by group
    visibleFieldsList.forEach(field => {
      // Normalize field group ID to string for consistent comparison
      const groupId = field.field_group ? String(field.field_group) : null
      if (!groups.has(groupId)) {
        groups.set(groupId, [])
      }
      groups.get(groupId)!.push(field)
    })
    
    // Sort fields within each group by display_order
    groups.forEach(groupFields => {
      groupFields.sort((a, b) => (a.display_order || 0) - (b.display_order || 0))
    })
    
    // Sort groups by display order and flatten
    const sortedFields: RecordField[] = []
    
    // Process defined field groups first (sorted by display_order)
    const sortedFieldGroups = [...fieldGroups].sort((a, b) => a.display_order - b.display_order)
    
    sortedFieldGroups.forEach(group => {
      const groupFields = groups.get(String(group.id))
      if (groupFields && groupFields.length > 0) {
        sortedFields.push(...groupFields)
      }
    })
    
    // Add ungrouped fields last
    const ungroupedFields = groups.get(null)
    if (ungroupedFields && ungroupedFields.length > 0) {
      sortedFields.push(...ungroupedFields)
    }
    
    return sortedFields
  }

  /**
   * Get default visible fields
   */
  static getDefaultVisibleFields(fields: RecordField[]): Set<string> {
    const defaultVisible = fields
      .filter(field => field.is_visible_in_list !== false)
      .map(field => field.name)
    
    return new Set(defaultVisible)
  }

  /**
   * Get select fields for Kanban view
   */
  static getSelectFields(fields: RecordField[]): Array<{
    value: string
    label: string
    options: any[]
  }> {
    return fields
      .filter(field => field.field_type === 'select' || field.field_type === 'multiselect')
      .map(field => ({
        value: field.name,
        label: field.display_name || field.name,
        options: field.field_config?.options || []
      }))
  }

  /**
   * Get date fields for Calendar view
   */
  static getDateFields(fields: RecordField[]): Array<{
    value: string
    label: string
    type: 'date' | 'datetime'
  }> {
    return fields
      .filter(field => field.field_type === 'date' || field.field_type === 'datetime')
      .map(field => ({
        value: field.name,
        label: field.display_name || field.name,
        type: field.field_type as 'date' | 'datetime'
      }))
  }

  /**
   * Validate field value
   */
  static validateFieldValue(field: RecordField, value: any): boolean {
    if (field.is_required && (value === null || value === undefined || value === '')) {
      return false
    }

    switch (field.field_type) {
      case 'email':
        if (value) {
          const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
          return emailRegex.test(value)
        }
        return true

      case 'number':
      case 'decimal':
      case 'integer':
      case 'float':
      case 'currency':
      case 'percentage':
        if (value !== null && value !== undefined && value !== '') {
          return !isNaN(Number(value))
        }
        return true

      case 'date':
      case 'datetime':
        if (value) {
          return !isNaN(Date.parse(value))
        }
        return true

      case 'url':
        if (value) {
          try {
            new URL(value)
            return true
          } catch {
            return false
          }
        }
        return true

      default:
        return true
    }
  }

  /**
   * Get field validation error message
   */
  static getFieldValidationError(field: RecordField, value: any): string | null {
    if (field.is_required && (value === null || value === undefined || value === '')) {
      return `${field.display_name || field.name} is required`
    }

    if (!this.validateFieldValue(field, value)) {
      switch (field.field_type) {
        case 'email':
          return 'Please enter a valid email address'
        case 'number':
        case 'decimal':
        case 'integer':
        case 'float':
        case 'currency':
        case 'percentage':
          return 'Please enter a valid number'
        case 'date':
        case 'datetime':
          return 'Please enter a valid date'
        case 'url':
          return 'Please enter a valid URL'
        default:
          return 'Invalid value'
      }
    }

    return null
  }
}