'use client'

import React from 'react'
import { Field, FieldRenderProps, FieldDisplayProps } from './types'
import { FieldResolver } from './field-registry'
import { evaluateFieldPermissions, type FieldWithPermissions } from '@/utils/field-permissions'
import { User } from '@/types/auth'

/**
 * Universal field input renderer - Pure UI component
 * 
 * No save logic - just renders the appropriate field component
 * and passes through all events to parent (which handles saving via FieldSaveService)
 */
export function FieldRenderer({ 
  field, 
  value, 
  onChange, 
  onBlur, 
  onKeyDown,
  disabled = false,
  error,
  className,
  autoFocus = false,
  context = 'form',
  pipeline_id,
  record_id
}: FieldRenderProps) {
  
  // Pure UI rendering - no save management
  // Parent components use FieldSaveService for intelligent saving
  return FieldResolver.renderInput(field, {
    value,
    onChange,
    onBlur,
    onKeyDown,
    disabled,
    error,
    className,
    autoFocus,
    context,
    pipeline_id,
    record_id
  })
}

/**
 * Universal field display renderer for read-only contexts
 */
export function FieldDisplay({ 
  field, 
  value, 
  context = 'detail',
  className 
}: FieldDisplayProps) {
  
  const formattedValue = FieldResolver.formatValue(field, value, context)
  
  if (typeof formattedValue === 'string') {
    return (
      <span className={className}>
        {formattedValue}
      </span>
    )
  }
  
  // JSX element returned from formatValue
  return (
    <div className={className}>
      {formattedValue}
    </div>
  )
}

/**
 * Field wrapper with label, help text, and error display
 */
export interface FieldWrapperProps {
  field: Field
  value: any
  onChange: (value: any) => void
  onBlur?: () => void
  onKeyDown?: (e: React.KeyboardEvent) => void
  disabled?: boolean
  error?: string
  className?: string
  autoFocus?: boolean
  context?: 'form' | 'drawer' | 'table' | 'display'
  showLabel?: boolean
  showHelp?: boolean
  labelClassName?: string
  helpClassName?: string
  // New props for permission-based requirements
  user?: User | null
  formData?: Record<string, any>
  // Context data for specific field types (like USER fields)
  pipeline_id?: number
  record_id?: number
}

export function FieldWrapper({
  field,
  value,
  onChange,
  onBlur,
  onKeyDown,
  disabled = false,
  error,
  className = '',
  autoFocus = false,
  context = 'form',
  showLabel = true,
  showHelp = true,
  labelClassName = '',
  helpClassName = '',
  user,
  formData = {},
  pipeline_id,
  record_id
}: FieldWrapperProps) {
  
  const fieldLabel = field.display_name || field.name
  const helpText = field.help_text
  
  // Use permission-based requirement evaluation instead of static is_required
  const mappedContext = context === 'table' ? 'list' : context === 'drawer' ? 'detail' : context === 'display' ? 'detail' : context as ("form" | "list" | "detail" | undefined)
  const permissions = user ? evaluateFieldPermissions(
    field as FieldWithPermissions, 
    user, 
    formData, 
    mappedContext
  ) : { required: false, visible: true, editable: true, readonly: false, conditionallyHidden: false }
  
  const isRequired = permissions.required
  
  return (
    <div className={`field-wrapper ${className}`}>
      {showLabel && (
        <label className={`block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 ${labelClassName}`}>
          {fieldLabel}
          {isRequired && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}
      
      {showHelp && helpText && (
        <p className={`text-xs text-gray-500 dark:text-gray-400 mb-2 ${helpClassName}`}>
          {helpText}
        </p>
      )}
      
      <FieldRenderer
        field={field}
        value={value}
        onChange={onChange}
        onBlur={onBlur}
        onKeyDown={onKeyDown}
        disabled={disabled}
        error={error}
        autoFocus={autoFocus}
        context={context}
        pipeline_id={pipeline_id}
        record_id={record_id}
      />
    </div>
  )
}

/**
 * Validation helper for field values
 */
export function validateFieldValue(field: Field, value: any) {
  return FieldResolver.validate(field, value)
}

/**
 * Get default value for field
 */
export function getFieldDefaultValue(field: Field) {
  return FieldResolver.getDefaultValue(field)
}

/**
 * Check if field value is empty
 */
export function isFieldEmpty(field: Field, value: any) {
  return FieldResolver.isEmpty(field, value)
}

/**
 * Normalize field value to ensure proper data types
 * Handles backend data inconsistencies (empty strings vs arrays for tags/multiselect)
 */
export function normalizeFieldValue(field: Field, rawValue: any): any {
  // Special handling for array fields (tags, multiselect) that might come as empty strings from backend
  if (field.field_type === 'tags' || field.field_type === 'multiselect') {
    if (rawValue === '' || rawValue === null || rawValue === undefined) {
      return null // Use null for empty arrays to match field system expectations
    } else if (Array.isArray(rawValue)) {
      return rawValue
    } else {
      // Convert non-array values to arrays if needed
      return rawValue ? [rawValue] : null
    }
  }
  
  // Relation field - preserve new format from backend
  if (field.field_type === 'relation') {
    if (rawValue === '' || rawValue === null || rawValue === undefined) {
      return null
    }

    // NEW FORMAT: Backend sends {id, display_value} objects
    // Just return the data as-is, don't transform it
    return rawValue
  }
  
  // Boolean fields - ensure proper boolean type
  if (field.field_type === 'boolean') {
    if (rawValue === 'true' || rawValue === '1' || rawValue === 1) return true
    if (rawValue === 'false' || rawValue === '0' || rawValue === 0) return false
    return Boolean(rawValue)
  }
  
  // Number fields - ensure proper numeric type
  if (field.field_type === 'number') {
    if (rawValue === '' || rawValue === null || rawValue === undefined) return null
    const numValue = Number(rawValue)
    return isNaN(numValue) ? rawValue : numValue
  }
  
  // For all other field types, return as-is
  return rawValue
}

/**
 * Normalize record data for all fields in a pipeline
 * Ensures consistent data types across all field values
 */
export function normalizeRecordData(fields: Field[], recordData: Record<string, any>): Record<string, any> {
  const normalizedData: Record<string, any> = {}
  
  fields.forEach(field => {
    const rawValue = recordData[field.name]
    normalizedData[field.name] = normalizeFieldValue(field, rawValue)
  })
  
  return normalizedData
}