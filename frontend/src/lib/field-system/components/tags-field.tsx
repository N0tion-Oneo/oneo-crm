import React, { useState, useEffect } from 'react'
import { FieldComponent, FieldRenderProps, ValidationResult, Field } from '../types'
import { getFieldConfig } from '../field-registry'
import { X, Plus, Search } from 'lucide-react'

export const TagsFieldComponent: FieldComponent = {
  renderInput: (props: FieldRenderProps) => {
    const { field, value, onChange, onBlur, onKeyDown, disabled, error, className, autoFocus } = props
    
    console.log('TagsField render - props:', { fieldName: field.name, value, disabled, error }) // DEBUG
    
    const predefinedTags = getFieldConfig(field, 'predefined_tags', [])
    const allowCustomTags = getFieldConfig(field, 'allow_custom_tags', true)
    const caseSensitive = getFieldConfig(field, 'case_sensitive', false)
    const autoComplete = getFieldConfig(field, 'auto_complete', true)
    const allowDuplicates = getFieldConfig(field, 'allow_duplicates', false)
    const showCount = getFieldConfig(field, 'show_count', false)
    const sortable = getFieldConfig(field, 'sortable', false)
    const showSuggestions = getFieldConfig(field, 'show_suggestions', true)
    
    // Validation options
    const maxTags = getFieldConfig(field, 'max_tags')
    const minTags = getFieldConfig(field, 'min_tags')
    const minTagLength = getFieldConfig(field, 'min_tag_length', 1)
    const maxTagLength = getFieldConfig(field, 'max_tag_length')
    const forbiddenChars = getFieldConfig(field, 'forbidden_chars', '')
    
    console.log('TagsField comprehensive config:', { 
      predefinedTags, allowCustomTags, caseSensitive, autoComplete, 
      allowDuplicates, showCount, sortable, showSuggestions,
      maxTags, minTags, minTagLength, maxTagLength, forbiddenChars 
    }) // DEBUG
    
    // SIMPLIFIED: Use the actual prop value directly instead of complex local state
    const tagValues = Array.isArray(value) ? value : []
    const [searchInput, setSearchInput] = useState('')
    const [isModalOpen, setIsModalOpen] = useState(false)
    
    console.log('TagsField current tags:', tagValues) // DEBUG
    
    const inputClass = `flex-1 px-3 py-2 border rounded-lg transition-all duration-200 shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-0 ${
      error 
        ? 'border-red-300 dark:border-red-600 focus:border-red-500 focus:ring-red-500 dark:focus:ring-red-400' 
        : 'border-gray-300 dark:border-gray-600 focus:border-blue-500 focus:ring-blue-500 dark:focus:ring-blue-400'
    } ${disabled 
        ? 'bg-gray-50 dark:bg-gray-700 cursor-not-allowed text-gray-500 dark:text-gray-400' 
        : 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white hover:border-gray-400 dark:hover:border-gray-500'
    } ${className || ''}`

    const addTag = (tag: string) => {
      const trimmedTag = tag.trim()
      
      console.log('addTag called:', { tag: trimmedTag, currentLength: tagValues.length }) // DEBUG
      
      // Validation checks
      if (!trimmedTag) {
        console.log('Tag not added - empty tag') // DEBUG
        return
      }
      
      // Check tag length constraints
      if (trimmedTag.length < minTagLength) {
        console.log(`Tag not added - too short (min: ${minTagLength})`) // DEBUG
        return
      }
      
      if (maxTagLength && trimmedTag.length > maxTagLength) {
        console.log(`Tag not added - too long (max: ${maxTagLength})`) // DEBUG
        return
      }
      
      // Check forbidden characters
      if (forbiddenChars) {
        const hasForbiddenChar = forbiddenChars.split('').some(char => trimmedTag.includes(char))
        if (hasForbiddenChar) {
          console.log(`Tag not added - contains forbidden characters: ${forbiddenChars}`) // DEBUG
          return
        }
      }
      
      // Check max tags limit
      if (maxTags && tagValues.length >= maxTags) {
        console.log(`Tag not added - reached max tags limit: ${maxTags}`) // DEBUG
        return
      }
      
      // Check for duplicates (unless allowed)
      if (!allowDuplicates) {
        const normalizedTag = caseSensitive ? trimmedTag : trimmedTag.toLowerCase()
        const normalizedExisting = caseSensitive ? tagValues : tagValues.map((t: string) => t.toLowerCase())
        
        if (normalizedExisting.includes(normalizedTag)) {
          console.log('Tag not added - duplicate not allowed') // DEBUG
          return
        }
      }
      
      // All validations passed - add the tag
      const newTags = [...tagValues, trimmedTag]
      console.log('Adding tag - all validations passed:', { oldTags: tagValues, newTags }) // DEBUG
      onChange(newTags)
    }

    const removeTag = (indexToRemove: number) => {
      console.log('removeTag called:', { indexToRemove, currentTags: tagValues, onChange: typeof onChange }) // DEBUG
      const newTags = tagValues.filter((_: any, index: number) => index !== indexToRemove)
      console.log('SIMPLIFIED: Removing tag - calling onChange directly:', { oldTags: tagValues, newTags, finalValue: newTags.length > 0 ? newTags : null }) // DEBUG
      onChange(newTags.length > 0 ? newTags : null) // SIMPLIFIED: Direct onChange call
    }
    
    const handleSearchKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') {
        e.preventDefault()
        if (allowCustomTags && searchInput.trim()) {
          addTag(searchInput)
          setSearchInput('')
        }
      } else if (e.key === 'Escape') {
        setSearchInput('')
        onKeyDown?.(e)
      }
    }

    // Filter predefined tags based on search input
    const filteredPredefinedTags = predefinedTags.filter((tag: string) => {
      const normalizedTag = caseSensitive ? tag : tag.toLowerCase()
      const normalizedSearch = caseSensitive ? searchInput : searchInput.toLowerCase()
      const normalizedExisting = caseSensitive ? tagValues : tagValues.map((t: string) => t.toLowerCase())
      
      // Show tag if it matches search and isn't already added
      return normalizedTag.includes(normalizedSearch) && !normalizedExisting.includes(normalizedTag)
    })

    return (
      <div className={`focus:outline-none rounded-lg transition-all duration-200 ${
        error ? 'ring-1 ring-red-300 dark:ring-red-600' : ''
      }`}>
        {/* Add tag button */}
        {!disabled && (!maxTags || tagValues.length < maxTags) && (
          <button
            type="button"
            onClick={() => setIsModalOpen(true)}
            className="inline-flex items-center px-3 py-1.5 text-sm text-gray-600 dark:text-gray-300 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 hover:border-gray-400 dark:hover:border-gray-500 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 mb-3"
          >
            <Plus className="w-4 h-4 mr-1" />
            Add tag
          </button>
        )}

        {/* Display existing tags */}
        {tagValues.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {tagValues.map((tag: string, index: number) => (
              <span 
                key={index} 
                className="inline-flex items-center px-2.5 py-1 rounded-md text-sm font-medium bg-gradient-to-r from-blue-100 to-blue-50 text-blue-800 dark:from-blue-900/80 dark:to-blue-800/80 dark:text-blue-200 border border-blue-200 dark:border-blue-700 shadow-sm hover:shadow-md transition-all duration-200"
              >
                <span className="mr-1.5" style={{textTransform: 'none'}}>{tag}</span>
                {!disabled && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.preventDefault()
                      e.stopPropagation()
                      removeTag(index)
                    }}
                    className="ml-1 inline-flex items-center justify-center w-3.5 h-3.5 text-blue-500 hover:text-red-600 dark:text-blue-400 dark:hover:text-red-400 focus:outline-none hover:bg-white/50 dark:hover:bg-black/20 rounded-full transition-colors duration-200"
                    title="Remove tag"
                  >
                    <X className="w-3 h-3" />
                  </button>
                )}
              </span>
            ))}
          </div>
        )}

        {/* Modal for adding tags */}
        {isModalOpen && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={() => setIsModalOpen(false)}>
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 w-full max-w-md mx-4" onClick={(e) => e.stopPropagation()}>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Add Tags</h3>
                <button
                  onClick={() => setIsModalOpen(false)}
                  className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="space-y-4">
                {/* Search input */}
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Search className="w-4 h-4 text-gray-400" />
                  </div>
                  <input
                    type="text"
                    value={searchInput}
                    onChange={(e) => setSearchInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault()
                        if (allowCustomTags && searchInput.trim()) {
                          addTag(searchInput)
                          setSearchInput('')
                          setIsModalOpen(false)
                        }
                      } else if (e.key === 'Escape') {
                        setIsModalOpen(false)
                      }
                    }}
                    className={`pl-10 ${inputClass}`}
                    placeholder={
                      predefinedTags.length > 0 
                        ? allowCustomTags 
                          ? "Search predefined tags or type custom tag..."
                          : "Search predefined tags..."
                        : allowCustomTags 
                          ? "Type a new tag..."
                          : "No tags available"
                    }
                    autoFocus
                  />
                </div>

                {/* Search results */}
                <div className="max-h-60 overflow-y-auto">
                  {searchInput ? (
                    <div className="space-y-3">
                      {/* Predefined tag matches */}
                      {filteredPredefinedTags.length > 0 && (
                        <div>
                          <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">Suggested tags:</p>
                          <div className="flex flex-wrap gap-2">
                            {filteredPredefinedTags.map((tag: string) => (
                              <button
                                key={tag}
                                type="button"
                                onClick={(e) => {
                                  e.preventDefault()
                                  e.stopPropagation()
                                  addTag(tag)
                                  setSearchInput('')
                                  setIsModalOpen(false)
                                }}
                                className="inline-flex items-center px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-600 rounded-md hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:border-blue-300 dark:hover:border-blue-600 hover:text-blue-700 dark:hover:text-blue-300 transition-all duration-200"
                              >
                                <Plus className="w-3 h-3 mr-1" />
                                {tag}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Custom tag option */}
                      {allowCustomTags && searchInput.trim() && (
                        <div>
                          {filteredPredefinedTags.length > 0 && (
                            <p className="text-xs text-gray-500 dark:text-gray-400 mb-2 mt-3">Or add custom tag:</p>
                          )}
                          <button
                            type="button"
                            onClick={(e) => {
                              e.preventDefault()
                              e.stopPropagation()
                              addTag(searchInput.trim())
                              setSearchInput('')
                              setIsModalOpen(false)
                            }}
                            className="inline-flex items-center px-3 py-1.5 text-sm bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 border border-blue-300 dark:border-blue-600 rounded-md hover:bg-blue-200 dark:hover:bg-blue-900/40 transition-all duration-200"
                          >
                            <Plus className="w-3 h-3 mr-1" />
                            Add "{searchInput.trim()}"
                          </button>
                        </div>
                      )}

                      {/* No results */}
                      {filteredPredefinedTags.length === 0 && !allowCustomTags && (
                        <div className="text-center py-4">
                          <p className="text-sm text-gray-500 dark:text-gray-400">No matching tags found</p>
                        </div>
                      )}
                    </div>
                  ) : (
                    /* Show all predefined tags when no search */
                    predefinedTags.length > 0 && (
                      <div>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">Available tags:</p>
                        <div className="flex flex-wrap gap-2">
                          {predefinedTags.filter((tag: string) => {
                            const normalizedTag = caseSensitive ? tag : tag.toLowerCase()
                            const normalizedExisting = caseSensitive ? tagValues : tagValues.map((t: string) => t.toLowerCase())
                            return !normalizedExisting.includes(normalizedTag)
                          }).map((tag: string) => (
                            <button
                              key={tag}
                              type="button"
                              onClick={(e) => {
                                e.preventDefault()
                                e.stopPropagation()
                                addTag(tag)
                                setIsModalOpen(false)
                              }}
                              className="inline-flex items-center px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-600 rounded-md hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:border-blue-300 dark:hover:border-blue-600 hover:text-blue-700 dark:hover:text-blue-300 transition-all duration-200"
                            >
                              <Plus className="w-3 h-3 mr-1" />
                              {tag}
                            </button>
                          ))}
                        </div>
                      </div>
                    )
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
        
        {/* Footer info */}
        {(showCount || maxTags || minTags) && (
          <div className="flex items-center justify-between mt-3">
            <div className="flex items-center space-x-4">
              {/* Tag count display */}
              {(showCount || maxTags) && (
                <p className="text-xs text-gray-500 dark:text-gray-400 flex items-center">
                  <span className={`inline-flex items-center justify-center w-5 h-5 rounded-full text-xs font-medium mr-2 ${
                    (maxTags && tagValues.length >= maxTags) || (minTags && tagValues.length < minTags)
                      ? 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400' 
                      : 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400'
                  }`}>
                    {tagValues.length}
                  </span>
                  {maxTags ? `of ${maxTags} tags` : 'tags'}
                </p>
              )}
              
              {/* Min/Max tags validation info */}
              {minTags && tagValues.length < minTags && (
                <p className="text-xs text-red-600 dark:text-red-400">
                  Minimum {minTags} tag{minTags !== 1 ? 's' : ''} required
                </p>
              )}
            </div>
          </div>
        )}
        
        {error && (
          <div className="mt-3 p-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <p className="text-sm text-red-600 dark:text-red-400 flex items-center">
              <X className="w-4 h-4 mr-2 flex-shrink-0" />
              {error}
            </p>
          </div>
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
              <span key={index} className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gradient-to-r from-blue-100 to-blue-50 text-blue-800 dark:from-blue-900/60 dark:to-blue-800/60 dark:text-blue-200 border border-blue-200 dark:border-blue-700">
                {tag}
              </span>
            ))}
          </div>
        )
      } else {
        return (
          <div className="flex flex-wrap gap-1">
            {value.slice(0, 2).map((tag: string, index: number) => (
              <span key={index} className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gradient-to-r from-blue-100 to-blue-50 text-blue-800 dark:from-blue-900/60 dark:to-blue-800/60 dark:text-blue-200 border border-blue-200 dark:border-blue-700">
                {tag}
              </span>
            ))}
            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gradient-to-r from-gray-100 to-gray-50 text-gray-700 dark:from-gray-700/60 dark:to-gray-600/60 dark:text-gray-300 border border-gray-200 dark:border-gray-600">
              +{value.length - 2}
            </span>
          </div>
        )
      }
    }
    
    if (context === 'detail') {
      return (
        <div className="flex flex-wrap gap-2">
          {value.map((tag: string, index: number) => (
            <span key={index} className="inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium bg-gradient-to-r from-blue-100 to-blue-50 text-blue-800 dark:from-blue-900/80 dark:to-blue-800/80 dark:text-blue-200 border border-blue-200 dark:border-blue-700 shadow-sm">
              {tag}
            </span>
          ))}
        </div>
      )
    }
    
    return value.join(', ')
  },

  validate: (value: any, field: Field): ValidationResult => {
    // Note: Required validation handled by permission system
    const tags = Array.isArray(value) ? value : []
    
    // Get configuration
    const minTags = getFieldConfig(field, 'min_tags')
    const maxTags = getFieldConfig(field, 'max_tags')
    const minTagLength = getFieldConfig(field, 'min_tag_length', 1)
    const maxTagLength = getFieldConfig(field, 'max_tag_length')
    const forbiddenChars = getFieldConfig(field, 'forbidden_chars', '')
    const allowDuplicates = getFieldConfig(field, 'allow_duplicates', false)
    const caseSensitive = getFieldConfig(field, 'case_sensitive', false)

    // Check minimum tags
    if (minTags && tags.length < minTags) {
      return {
        isValid: false,
        error: `Minimum ${minTags} tag${minTags !== 1 ? 's' : ''} required`
      }
    }

    // Check maximum tags
    if (maxTags && tags.length > maxTags) {
      return {
        isValid: false,
        error: `Maximum ${maxTags} tag${maxTags !== 1 ? 's' : ''} allowed`
      }
    }

    if (tags.length > 0) {
      // Check for empty tags
      const emptyTags = tags.filter((tag: any) => !tag || !String(tag).trim())
      if (emptyTags.length > 0) {
        return {
          isValid: false,
          error: 'Tags cannot be empty'
        }
      }

      // Check tag length constraints
      for (const tag of tags) {
        const tagStr = String(tag).trim()
        
        if (tagStr.length < minTagLength) {
          return {
            isValid: false,
            error: `Tags must be at least ${minTagLength} character${minTagLength !== 1 ? 's' : ''} long`
          }
        }
        
        if (maxTagLength && tagStr.length > maxTagLength) {
          return {
            isValid: false,
            error: `Tags cannot exceed ${maxTagLength} character${maxTagLength !== 1 ? 's' : ''}`
          }
        }
        
        // Check forbidden characters
        if (forbiddenChars) {
          const hasForbiddenChar = forbiddenChars.split('').some(char => tagStr.includes(char))
          if (hasForbiddenChar) {
            return {
              isValid: false,
              error: `Tags cannot contain these characters: ${forbiddenChars}`
            }
          }
        }
      }

      // Check for duplicates (if not allowed)
      if (!allowDuplicates) {
        const normalizedTags = caseSensitive ? tags : tags.map((tag: string) => String(tag).toLowerCase())
        const uniqueTags = new Set(normalizedTags)
        
        if (uniqueTags.size !== tags.length) {
          return {
            isValid: false,
            error: 'Duplicate tags are not allowed'
          }
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