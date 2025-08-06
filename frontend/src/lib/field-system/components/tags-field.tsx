import React, { useState, useEffect } from 'react'
import { FieldComponent, FieldRenderProps, ValidationResult, Field } from '../types'
import { getFieldConfig } from '../field-registry'

export const TagsFieldComponent: FieldComponent = {
  renderInput: (props: FieldRenderProps) => {
    const { field, value, onChange, onBlur, onKeyDown, disabled, error, className, autoFocus } = props
    
    const predefinedTags = getFieldConfig(field, 'predefined_tags', [])
    const allowCustomTags = getFieldConfig(field, 'allow_custom_tags', true)
    const maxTags = getFieldConfig(field, 'max_tags')
    const caseSensitive = getFieldConfig(field, 'case_sensitive', false)
    
    // Local state management for tags array to prevent re-render issues
    const [localTagValues, setLocalTagValues] = useState(() => Array.isArray(value) ? value : [])
    const [isEditing, setIsEditing] = useState(false)
    const [tagInput, setTagInput] = useState('')
    
    // Update local tags when external value changes and not editing, or when value differs significantly
    useEffect(() => {
      const externalValue = Array.isArray(value) ? value : []
      
      if (!isEditing) {
        // Always sync when not editing
        setLocalTagValues(externalValue)
      } else {
        // Even when editing, sync if external value is significantly different
        // This handles cases where save completed and we have fresh saved data
        const currentSorted = [...localTagValues].sort().join(',')
        const externalSorted = [...externalValue].sort().join(',')
        
        if (currentSorted !== externalSorted && externalValue.length !== localTagValues.length) {
          setLocalTagValues(externalValue)
          setIsEditing(false) // Exit editing mode when syncing saved data
        }
      }
    }, [value, isEditing, localTagValues])
    
    const tagValues = localTagValues
    
    const inputClass = `flex-1 px-3 py-2 border rounded-lg transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-0 ${
      error 
        ? 'border-red-300 dark:border-red-600 focus:border-red-500 focus:ring-red-500 dark:focus:ring-red-400' 
        : 'border-gray-300 dark:border-gray-600 focus:border-blue-500 focus:ring-blue-500 dark:focus:ring-blue-400'
    } ${disabled 
        ? 'bg-gray-50 dark:bg-gray-700 cursor-not-allowed text-gray-500 dark:text-gray-400' 
        : 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white'
    } ${className || ''}`

    const addTag = (tag: string) => {
      const normalizedTag = caseSensitive ? tag : tag.toLowerCase()
      const normalizedExisting = caseSensitive ? tagValues : tagValues.map((t: string) => t.toLowerCase())
      
      if (tag.trim() && !normalizedExisting.includes(normalizedTag) && (!maxTags || tagValues.length < maxTags)) {
        const newTags = [...tagValues, tag.trim()]
        setLocalTagValues(newTags)
        setIsEditing(true)
        onChange(newTags.length > 0 ? newTags : null)
      }
    }

    const removeTag = (indexToRemove: number) => {
      const newTags = tagValues.filter((_: any, index: number) => index !== indexToRemove)
      setLocalTagValues(newTags)
      setIsEditing(true)
      onChange(newTags.length > 0 ? newTags : null)
    }
    
    const handleTagInputFocus = () => {
      setIsEditing(true)
    }
    
    const handleTagInputBlur = (e: React.FocusEvent<HTMLInputElement>) => {
      // If user leaves input empty, consider the field done editing
      if (!tagInput.trim()) {
        setIsEditing(false)
        onBlur?.()  // Signal parent that user is done
      }
      // Don't propagate if user is still typing
      e.stopPropagation()
    }
    
    const handleTagInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') {
        e.preventDefault()
        if (tagInput.trim()) {
          addTag(tagInput)
          setTagInput('')
        }
      } else if (e.key === 'Escape') {
        setTagInput('')
        setLocalTagValues(Array.isArray(value) ? value : []) // Reset to original
        setIsEditing(false)
        onKeyDown?.(e)
      }
      // Don't pass through other keys to avoid interfering with field value
    }
    
    const handleDoneClick = () => {
      setTagInput('')
      setIsEditing(false)
      onBlur?.()  // Signal parent that user is done editing
    }

    const handleContainerKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
      // Handle field-level keyboard shortcuts when not in input
      if (e.target === e.currentTarget) {
        if (e.key === 'Enter') {
          setIsEditing(false)
          onBlur?.()
        } else if (e.key === 'Escape') {
          setLocalTagValues(Array.isArray(value) ? value : [])
          setTagInput('')
          setIsEditing(false)
          onKeyDown?.(e)
        }
      }
    }

    return (
      <div 
        tabIndex={0}
        onKeyDown={handleContainerKeyDown}
        className="focus:outline-none"
      >
        {/* Display existing tags */}
        {tagValues.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-3">
            {tagValues.map((tag: string, index: number) => (
              <span key={index} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                {tag}
                {!disabled && (
                  <button
                    type="button"
                    onClick={() => removeTag(index)}
                    className="ml-1.5 inline-flex items-center justify-center w-4 h-4 text-blue-400 hover:text-blue-600 dark:text-blue-300 dark:hover:text-blue-100 focus:outline-none"
                  >
                    <span className="sr-only">Remove tag</span>
                    ×
                  </button>
                )}
              </span>
            ))}
          </div>
        )}
        
        {/* Predefined tags */}
        {predefinedTags.length > 0 && (
          <div className="mb-3">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Suggested tags:</p>
            <div className="flex flex-wrap gap-1">
              {predefinedTags.filter((tag: string) => {
                const normalizedTag = caseSensitive ? tag : tag.toLowerCase()
                const normalizedExisting = caseSensitive ? tagValues : tagValues.map((t: string) => t.toLowerCase())
                return !normalizedExisting.includes(normalizedTag)
              }).map((tag: string) => (
                <button
                  key={tag}
                  type="button"
                  onClick={() => addTag(tag)}
                  className="text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 px-2 py-1 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                  disabled={disabled || (maxTags && tagValues.length >= maxTags)}
                >
                  + {tag}
                </button>
              ))}
            </div>
          </div>
        )}
        
        {/* Custom tag input */}
        {allowCustomTags && !disabled && (!maxTags || tagValues.length < maxTags) && (
          <div className="flex gap-2">
            <input
              type="text"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onFocus={handleTagInputFocus}
              onBlur={handleTagInputBlur}
              onKeyDown={handleTagInputKeyDown}
              className={inputClass}
              placeholder="Add custom tag..."
              autoFocus={autoFocus}
            />
            <button
              type="button"
              onClick={() => {
                if (tagInput.trim()) {
                  addTag(tagInput)
                  setTagInput('')
                }
              }}
              className="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-600 text-sm transition-colors"
              disabled={!tagInput.trim()}
            >
              Add
            </button>
            <button
              type="button"
              onClick={handleDoneClick}
              className="px-3 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 dark:bg-gray-700 dark:hover:bg-gray-600 text-sm transition-colors"
            >
              Done
            </button>
          </div>
        )}
        
        {/* Tag count */}
        {maxTags && (
          <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
            {tagValues.length}/{maxTags} tags
          </p>
        )}
        
        {error && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error}</p>
        )}
      </div>
    )
  },

  formatValue: (value: any, field: Field, context?: string) => {
    if (!Array.isArray(value) || value.length === 0) {
      if (context === 'table') {
        return <span className="text-gray-400 italic">No tags</span>
      }
      return ''
    }
    
    if (context === 'table') {
      if (value.length <= 3) {
        return (
          <div className="flex flex-wrap gap-1">
            {value.map((tag: string, index: number) => (
              <span key={index} className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                {tag}
              </span>
            ))}
          </div>
        )
      } else {
        return (
          <div className="flex flex-wrap gap-1">
            {value.slice(0, 2).map((tag: string, index: number) => (
              <span key={index} className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                {tag}
              </span>
            ))}
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200">
              +{value.length - 2} more
            </span>
          </div>
        )
      }
    }
    
    if (context === 'detail') {
      return (
        <div className="flex flex-wrap gap-2">
          {value.map((tag: string, index: number) => (
            <span key={index} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-sm font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
              {tag}
            </span>
          ))}
        </div>
      )
    }
    
    return value.join(', ')
  },

  validate: (value: any, field: Field): ValidationResult => {
    if (field.is_required && (!Array.isArray(value) || value.length === 0)) {
      return {
        isValid: false,
        error: `${field.display_name || field.name} is required`
      }
    }

    if (Array.isArray(value) && value.length > 0) {
      const maxTags = getFieldConfig(field, 'max_tags')
      
      if (maxTags && value.length > maxTags) {
        return {
          isValid: false,
          error: `Maximum ${maxTags} tags allowed`
        }
      }
      
      // Check for empty tags
      const emptyTags = value.filter((tag: any) => !tag || !String(tag).trim())
      if (emptyTags.length > 0) {
        return {
          isValid: false,
          error: 'Tags cannot be empty'
        }
      }
      
      // Check for duplicates
      const caseSensitive = getFieldConfig(field, 'case_sensitive', false)
      const normalizedTags = caseSensitive ? value : value.map((tag: string) => tag.toLowerCase())
      const uniqueTags = new Set(normalizedTags)
      
      if (uniqueTags.size !== value.length) {
        return {
          isValid: false,
          error: 'Duplicate tags are not allowed'
        }
      }
    }

    return { isValid: true }
  },

  getDefaultValue: (field: Field) => {
    const defaultValue = getFieldConfig(field, 'default_value')
    
    if (Array.isArray(defaultValue)) {
      return defaultValue.length > 0 ? defaultValue : null
    }
    
    return null
  },

  isEmpty: (value: any) => !Array.isArray(value) || value.length === 0
}