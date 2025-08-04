import React from 'react'
import { FieldComponent, FieldRenderProps, ValidationResult, Field } from '../types'
import { getFieldConfig } from '../field-registry'

export const AIFieldComponent: FieldComponent = {
  renderInput: (props: FieldRenderProps) => {
    const { field, value, onChange, onBlur, onKeyDown, disabled, error, className, autoFocus } = props
    
    // Get AI configuration from field.ai_config or field.field_config
    const aiConfig = (field as any).ai_config || getFieldConfig(field, 'ai_config', {})
    const outputType = aiConfig.output_type || 'text'
    const isEditable = aiConfig.is_editable !== false
    const model = aiConfig.model || 'gpt-4.1-mini'
    const enableTools = aiConfig.enable_tools || false
    const allowedTools = aiConfig.allowed_tools || []
    
    const inputClass = `w-full px-3 py-2 border rounded-lg transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-0 ${
      error 
        ? 'border-red-300 dark:border-red-600 focus:border-red-500 focus:ring-red-500 dark:focus:ring-red-400' 
        : 'border-gray-300 dark:border-gray-600 focus:border-blue-500 focus:ring-blue-500 dark:focus:ring-blue-400'
    } ${disabled || !isEditable
        ? 'bg-gray-50 dark:bg-gray-700 cursor-not-allowed text-gray-500 dark:text-gray-400' 
        : 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white'
    } ${className || ''}`

    return (
      <div>
        {/* AI Field Header */}
        <div className="bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg p-3 mb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <span className="w-2 h-2 bg-purple-500 rounded-full mr-2"></span>
              <span className="text-purple-800 dark:text-purple-200 text-sm font-medium">
                AI-Enhanced Field
              </span>
            </div>
            <div className="flex items-center gap-2 text-xs text-purple-600 dark:text-purple-300">
              <span>{model}</span>
              {enableTools && allowedTools.length > 0 && (
                <span className="bg-purple-200 dark:bg-purple-800 px-2 py-0.5 rounded">
                  +{allowedTools.length} tools
                </span>
              )}
            </div>
          </div>
          <p className="text-purple-600 dark:text-purple-300 text-xs mt-1">
            {outputType === 'text' ? 'AI will generate text content based on record data' : 
             outputType === 'tags' ? 'AI will generate relevant tags based on record data' :
             outputType === 'number' ? 'AI will calculate a numeric value based on record data' :
             outputType === 'url' ? 'AI will generate a relevant URL based on record data' :
             outputType === 'json' ? 'AI will generate structured JSON data' :
             'AI will process and generate content based on record data'}
          </p>
        </div>

        {/* Field Input based on output type */}
        {outputType === 'tags' ? (
          <div>
            {Array.isArray(value) && value.length > 0 ? (
              <div className="flex flex-wrap gap-2 mb-2">
                {value.map((tag: string, index: number) => (
                  <span key={index} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                    {tag}
                    {isEditable && !disabled && (
                      <button
                        type="button"
                        onClick={() => {
                          const newTags = value.filter((_: any, i: number) => i !== index)
                          onChange(newTags.length > 0 ? newTags : null)
                        }}
                        className="ml-1.5 inline-flex items-center justify-center w-4 h-4 text-blue-400 hover:text-blue-600 dark:text-blue-300 dark:hover:text-blue-100"
                      >
                        ×
                      </button>
                    )}
                  </span>
                ))}
              </div>
            ) : (
              <div className="text-gray-500 dark:text-gray-400 italic text-sm mb-2">
                AI will generate tags automatically
              </div>
            )}
            
            {isEditable && !disabled && (
              <input
                type="text"
                placeholder="Add custom tag..."
                className={inputClass}
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    const input = e.target as HTMLInputElement
                    const newTag = input.value.trim()
                    if (newTag) {
                      const currentTags = Array.isArray(value) ? value : []
                      if (!currentTags.includes(newTag)) {
                        onChange([...currentTags, newTag])
                      }
                      input.value = ''
                    }
                  }
                }}
                onBlur={onBlur}
                onKeyDown={onKeyDown}
                autoFocus={autoFocus}
              />
            )}
          </div>
        ) : outputType === 'number' ? (
          <input
            type="number"
            value={value || ''}
            onChange={(e) => {
              const numValue = e.target.value === '' ? null : parseFloat(e.target.value)
              onChange(numValue)
            }}
            onBlur={onBlur}
            onKeyDown={onKeyDown}
            disabled={disabled || !isEditable}
            className={inputClass}
            placeholder="AI will calculate value..."
            autoFocus={autoFocus}
            required={field.is_required}
            readOnly={!isEditable}
          />
        ) : outputType === 'url' ? (
          <div>
            <input
              type="url"
              value={value || ''}
              onChange={(e) => onChange(e.target.value)}
              onBlur={onBlur}
              onKeyDown={onKeyDown}
              disabled={disabled || !isEditable}
              className={inputClass}
              placeholder="AI will generate URL..."
              autoFocus={autoFocus}
              required={field.is_required}
              readOnly={!isEditable}
            />
            {value && (
              <div className="mt-1">
                <a
                  href={value}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 dark:text-blue-400 hover:underline text-sm"
                  onClick={(e) => e.stopPropagation()}
                >
                  Visit Link ↗
                </a>
              </div>
            )}
          </div>
        ) : outputType === 'json' ? (
          <textarea
            value={typeof value === 'object' ? JSON.stringify(value, null, 2) : (value || '')}
            onChange={(e) => {
              try {
                const parsed = JSON.parse(e.target.value)
                onChange(parsed)
              } catch {
                // Keep as string if invalid JSON
                onChange(e.target.value)
              }
            }}
            onBlur={onBlur}
            onKeyDown={onKeyDown}
            disabled={disabled || !isEditable}
            className={`${inputClass} min-h-[120px] resize-vertical font-mono text-sm`}
            placeholder="AI will generate JSON data..."
            autoFocus={autoFocus}
            required={field.is_required}
            readOnly={!isEditable}
          />
        ) : (
          // Default text output
          <textarea
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            onBlur={onBlur}
            onKeyDown={onKeyDown}
            disabled={disabled || !isEditable}
            className={`${inputClass} min-h-[100px] resize-vertical`}
            placeholder={field.placeholder || 'AI will generate content here...'}
            autoFocus={autoFocus}
            required={field.is_required}
            readOnly={!isEditable}
          />
        )}
        
        {!isEditable && (
          <p className="mt-1 text-xs text-purple-600 dark:text-purple-400">
            This field is AI-generated and read-only
          </p>
        )}
        
        {error && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error}</p>
        )}
      </div>
    )
  },

  formatValue: (value: any, field: Field, context?: string) => {
    if (value === null || value === undefined || value === '') {
      if (context === 'table') {
        return <span className="text-gray-400 italic">AI not run</span>
      }
      return ''
    }
    
    const aiConfig = (field as any).ai_config || getFieldConfig(field, 'ai_config', {})
    const outputType = aiConfig.output_type || 'text'
    
    if (outputType === 'tags' && Array.isArray(value)) {
      if (context === 'table') {
        if (value.length <= 2) {
          return (
            <div className="flex flex-wrap gap-1">
              {value.map((tag: string, index: number) => (
                <span key={index} className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200">
                  {tag}
                </span>
              ))}
            </div>
          )
        } else {
          return (
            <div className="flex flex-wrap gap-1">
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200">
                {value[0]}
              </span>
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200">
                +{value.length - 1} more
              </span>
            </div>
          )
        }
      }
      return value.join(', ')
    }
    
    if (outputType === 'json' && typeof value === 'object') {
      if (context === 'table') {
        return <span className="font-mono text-xs text-purple-600 dark:text-purple-400">JSON data</span>
      }
      return JSON.stringify(value, null, 2)
    }
    
    if (outputType === 'url') {
      const url = String(value)
      if (context === 'table' || context === 'detail') {
        const displayUrl = url.length > 30 ? url.substring(0, 27) + '...' : url
        return (
          <a 
            href={url} 
            target="_blank" 
            rel="noopener noreferrer"
            className="text-purple-600 hover:text-purple-800 dark:text-purple-400 dark:hover:text-purple-300 hover:underline"
            onClick={(e) => e.stopPropagation()}
          >
            {displayUrl}
          </a>
        )
      }
      return url
    }
    
    if (outputType === 'number') {
      const numValue = Number(value)
      if (!isNaN(numValue)) {
        return numValue.toLocaleString()
      }
    }
    
    // Default text formatting
    const stringValue = String(value)
    
    if (context === 'table' && stringValue.length > 100) {
      return (
        <span className="text-purple-700 dark:text-purple-300">
          {stringValue.substring(0, 97) + '...'}
        </span>
      )
    }
    
    if (context === 'table') {
      return <span className="text-purple-700 dark:text-purple-300">{stringValue}</span>
    }
    
    return stringValue
  },

  validate: (value: any, field: Field): ValidationResult => {
    if (field.is_required && (value === null || value === undefined || value === '')) {
      return {
        isValid: false,
        error: `${field.display_name || field.name} is required`
      }
    }

    // AI fields generally don't need additional validation since they're generated
    // The AI system should handle generating valid content
    return { isValid: true }
  },

  getDefaultValue: (field: Field) => {
    const aiConfig = (field as any).ai_config || getFieldConfig(field, 'ai_config', {})
    const outputType = aiConfig.output_type || 'text'
    const fallbackValue = aiConfig.fallback_value
    
    if (fallbackValue !== undefined) {
      return fallbackValue
    }
    
    // Return appropriate empty value based on output type
    switch (outputType) {
      case 'tags': return null
      case 'number': return null
      case 'json': return null
      case 'url': return ''
      default: return '' // text
    }
  },

  isEmpty: (value: any) => {
    if (value === null || value === undefined || value === '') return true
    if (Array.isArray(value)) return value.length === 0
    if (typeof value === 'object') return Object.keys(value).length === 0
    return false
  }
}