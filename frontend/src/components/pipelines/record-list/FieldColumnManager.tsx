// FieldColumnManager - Show/hide columns interface
import React, { useState } from 'react'
import { Eye, EyeOff, Columns, Check } from 'lucide-react'
import { RecordField } from '@/types/records'
import { FieldUtilsService } from '@/services/records'

export interface FieldColumnManagerProps {
  fields: RecordField[]
  visibleFields: Set<string>
  onVisibleFieldsChange: (visibleFields: Set<string>) => void
  className?: string
}

export function FieldColumnManager({
  fields,
  visibleFields,
  onVisibleFieldsChange,
  className = ""
}: FieldColumnManagerProps) {
  const [isOpen, setIsOpen] = useState(false)

  const toggleField = (fieldName: string) => {
    const newVisibleFields = new Set(visibleFields)
    if (newVisibleFields.has(fieldName)) {
      newVisibleFields.delete(fieldName)
    } else {
      newVisibleFields.add(fieldName)
    }
    onVisibleFieldsChange(newVisibleFields)
  }

  const showAll = () => {
    const allFields = new Set(fields.map(f => f.name))
    onVisibleFieldsChange(allFields)
  }

  const hideAll = () => {
    onVisibleFieldsChange(new Set())
  }

  const resetToDefault = () => {
    const defaultVisible = FieldUtilsService.getDefaultVisibleFields(fields)
    onVisibleFieldsChange(defaultVisible)
  }

  // Sort fields by display order
  const sortedFields = [...fields].sort((a, b) => (a.display_order || 0) - (b.display_order || 0))

  return (
    <div className={`relative ${className}`}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300"
      >
        <Columns className="w-4 h-4 mr-2" />
        Columns ({visibleFields.size}/{fields.length})
      </button>

      {isOpen && (
        <>
          {/* Backdrop */}
          <div 
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />
          
          {/* Dropdown */}
          <div className="absolute right-0 top-full mt-2 z-50 w-80 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg">
            <div className="p-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-medium text-gray-900 dark:text-white">
                  Manage Columns
                </h3>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={showAll}
                    className="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200"
                  >
                    Show All
                  </button>
                  <span className="text-gray-300 dark:text-gray-600">|</span>
                  <button
                    onClick={hideAll}
                    className="text-xs text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
                  >
                    Hide All
                  </button>
                  <span className="text-gray-300 dark:text-gray-600">|</span>
                  <button
                    onClick={resetToDefault}
                    className="text-xs text-green-600 dark:text-green-400 hover:text-green-800 dark:hover:text-green-200"
                  >
                    Reset
                  </button>
                </div>
              </div>

              <div className="max-h-64 overflow-y-auto space-y-1">
                {sortedFields.map((field) => {
                  const isVisible = visibleFields.has(field.name)
                  const IconComponent = FieldUtilsService.getFieldTypeIcon(field.field_type)
                  
                  return (
                    <div
                      key={field.id}
                      className="flex items-center justify-between p-2 rounded hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer"
                      onClick={() => toggleField(field.name)}
                    >
                      <div className="flex items-center space-x-2">
                        <div className="flex items-center justify-center w-5 h-5">
                          {isVisible ? (
                            <Check className="w-4 h-4 text-green-600 dark:text-green-400" />
                          ) : (
                            <div className="w-4 h-4" />
                          )}
                        </div>
                        
                        {/* Field icon would go here if we had dynamic icon rendering */}
                        <div className="w-4 h-4 text-gray-400">
                          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" />
                          </svg>
                        </div>
                        
                        <div className="flex-1">
                          <div className="text-sm font-medium text-gray-900 dark:text-white">
                            {field.display_name || field.name}
                          </div>
                          <div className="text-xs text-gray-500 dark:text-gray-400">
                            {field.field_type} • {field.is_required ? 'Required' : 'Optional'}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center space-x-1">
                        {isVisible ? (
                          <Eye className="w-4 h-4 text-green-600 dark:text-green-400" />
                        ) : (
                          <EyeOff className="w-4 h-4 text-gray-400" />
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>

              <div className="mt-4 pt-3 border-t border-gray-200 dark:border-gray-600">
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  {visibleFields.size} of {fields.length} columns visible
                </div>
                <button
                  onClick={() => setIsOpen(false)}
                  className="mt-2 w-full px-3 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 text-sm"
                >
                  Done
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}