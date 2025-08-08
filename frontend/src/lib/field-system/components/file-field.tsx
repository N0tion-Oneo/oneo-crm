import React, { useState, useEffect, useRef } from 'react'
import { FieldComponent, FieldRenderProps, ValidationResult, Field } from '../types'
import { getFieldConfig } from '../field-registry'

export const FileFieldComponent: FieldComponent = {
  renderInput: (props: FieldRenderProps) => {
    const { field, value, onChange, onBlur, onKeyDown, disabled, error, className, autoFocus } = props
    
    // Local state management for file field
    const [localValue, setLocalValue] = useState(value)
    const [isEditing, setIsEditing] = useState(false)
    const [fileError, setFileError] = useState<string | null>(null)
    const [isProcessing, setIsProcessing] = useState(false)
    const fileInputRef = useRef<HTMLInputElement>(null)
    
    // Update local value when external value changes and not editing
    useEffect(() => {
      if (!isEditing) {
        setLocalValue(value)
      }
    }, [value, isEditing])
    
    const allowedTypes = getFieldConfig(field, 'allowed_types', [])
    const maxSize = getFieldConfig(field, 'max_size', 10485760) // 10MB default
    const acceptString = allowedTypes.length > 0 ? allowedTypes.map((type: string) => `.${type}`).join(',') : '*'
    
    const inputClass = `w-full px-3 py-2 border rounded-lg transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-0 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 dark:file:bg-blue-900 dark:file:text-blue-300 ${
      error 
        ? 'border-red-300 dark:border-red-600 focus:border-red-500 focus:ring-red-500 dark:focus:ring-red-400' 
        : 'border-gray-300 dark:border-gray-600 focus:border-blue-500 focus:ring-blue-500 dark:focus:ring-blue-400'
    } ${disabled 
        ? 'bg-gray-50 dark:bg-gray-700 cursor-not-allowed text-gray-500 dark:text-gray-400' 
        : 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white'
    } ${className || ''}`

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      setFileError(null)
      setIsEditing(true)
      
      if (!file) {
        setLocalValue(null)
        onChange(null)
        setIsEditing(false)
        return
      }
      
      setIsProcessing(true)
      
      try {
        // Validate file type
        if (allowedTypes.length > 0) {
          const fileExtension = file.name.split('.').pop()?.toLowerCase()
          if (!fileExtension || !allowedTypes.includes(fileExtension)) {
            throw new Error(`File type must be one of: ${allowedTypes.join(', ')}`)
          }
        }
        
        // Validate file size
        if (file.size > maxSize) {
          const maxSizeMB = Math.round(maxSize / 1024 / 1024)
          throw new Error(`File size must be less than ${maxSizeMB}MB`)
        }
        
        // Create file object
        const fileData = {
          name: file.name,
          size: file.size,
          type: file.type,
          lastModified: file.lastModified
        }
        
        setLocalValue(fileData)
        onChange(fileData)
        setIsEditing(false)
        
      } catch (error) {
        // Clear the input and show error
        e.target.value = ''
        setFileError(error instanceof Error ? error.message : 'Invalid file')
        setLocalValue(null)
        onChange(null)
        setIsEditing(false)
      } finally {
        setIsProcessing(false)
      }
    }
    
    const handleRemoveFile = () => {
      setLocalValue(null)
      setFileError(null)
      setIsEditing(true)
      onChange(null)
      setIsEditing(false)
      
      // Clear the file input
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
    
    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Escape') {
        // Reset to original value
        setLocalValue(value)
        setFileError(null)
        setIsEditing(false)
        if (fileInputRef.current) {
          fileInputRef.current.value = ''
        }
        onKeyDown?.(e)
      } else if (e.key === 'Enter') {
        // If there's a file, save and exit
        if (localValue) {
          setIsEditing(false)
          onBlur?.()
        }
      } else if (e.key === 'Delete' || e.key === 'Backspace') {
        // Remove file with Delete/Backspace
        if (localValue) {
          e.preventDefault()
          handleRemoveFile()
        }
      }
      onKeyDown?.(e)
    }
    
    const handleBlur = () => {
      setIsEditing(false)
      onBlur?.()
    }

    return (
      <div>
        <input
          ref={fileInputRef}
          type="file"
          accept={acceptString}
          onChange={handleFileChange}
          onBlur={handleBlur}
          onKeyDown={handleKeyDown}
          disabled={disabled || isProcessing}
          className={inputClass}
          autoFocus={autoFocus}
          // Required attribute handled by FieldWrapper
        />
        
        {/* Processing state */}
        {isProcessing && (
          <div className="mt-2 p-2 bg-blue-50 dark:bg-blue-900 rounded border border-blue-200 dark:border-blue-700">
            <div className="flex items-center">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 dark:border-blue-400"></div>
              <p className="ml-2 text-sm text-blue-600 dark:text-blue-400">Processing file...</p>
            </div>
          </div>
        )}
        
        {/* File display */}
        {localValue && !isProcessing && (
          <div className="mt-2 p-2 bg-gray-50 dark:bg-gray-700 rounded border">
            <div className="flex items-center justify-between">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                  {typeof localValue === 'string' ? localValue : localValue.name}
                </p>
                {typeof localValue === 'object' && localValue.size && (
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {(localValue.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                )}
              </div>
              {!disabled && (
                <button
                  type="button"
                  onClick={handleRemoveFile}
                  className="ml-2 text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300 text-sm"
                >
                  Remove
                </button>
              )}
            </div>
          </div>
        )}
        
        {/* Validation info */}
        <div className="mt-1 space-y-1">
          {allowedTypes.length > 0 && (
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Allowed types: {allowedTypes.join(', ')}
            </p>
          )}
          
          {maxSize && (
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Maximum size: {Math.round(maxSize / 1024 / 1024)}MB
            </p>
          )}
          
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Press Delete/Backspace to remove • Enter to save • Escape to reset
          </p>
        </div>
        
        {/* Error messages */}
        {(fileError || error) && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">
            {fileError || error}
          </p>
        )}
      </div>
    )
  },

  formatValue: (value: any, field: Field, context?: string) => {
    if (!value) {
      if (context === 'table') {
        return <span className="text-gray-400 italic">No file</span>
      }
      return ''
    }
    
    const fileName = typeof value === 'string' ? value : value.name
    const fileSize = typeof value === 'object' && value.size ? 
      ` (${(value.size / 1024 / 1024).toFixed(2)} MB)` : ''
    
    if (context === 'table') {
      const displayName = fileName.length > 30 ? fileName.substring(0, 27) + '...' : fileName
      return (
        <span className="text-blue-600 dark:text-blue-400 font-mono text-sm">
          {displayName}{fileSize}
        </span>
      )
    }
    
    return `${fileName}${fileSize}`
  },

  validate: (value: any, field: Field): ValidationResult => {
    // Note: Required validation handled by permission system

    if (value) {
      const allowedTypes = getFieldConfig(field, 'allowed_types', [])
      const maxSize = getFieldConfig(field, 'max_size', 10485760)
      
      // Validate file type
      if (allowedTypes.length > 0) {
        const fileName = typeof value === 'string' ? value : value.name
        const fileExtension = fileName.split('.').pop()?.toLowerCase()
        
        if (!fileExtension || !allowedTypes.includes(fileExtension)) {
          return {
            isValid: false,
            error: `File type must be one of: ${allowedTypes.join(', ')}`
          }
        }
      }
      
      // Validate file size
      if (typeof value === 'object' && value.size && value.size > maxSize) {
        const maxSizeMB = Math.round(maxSize / 1024 / 1024)
        return {
          isValid: false,
          error: `File size must be less than ${maxSizeMB}MB`
        }
      }
    }

    return { isValid: true }
  },

  getDefaultValue: (field: Field) => {
    return getFieldConfig(field, 'default_value', null)
  },

  isEmpty: (value: any) => !value
}