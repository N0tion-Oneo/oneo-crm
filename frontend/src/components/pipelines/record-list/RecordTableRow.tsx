// RecordTableRow - Individual record row with field rendering
import React, { useState, useEffect } from 'react'
import { CheckSquare, Square, Edit, Eye, Trash2 } from 'lucide-react'
import { Record, RecordField } from '@/types/records'
import { FieldUtilsService } from '@/services/records'
import { FieldResolver, getFieldConfig } from '@/lib/field-system/field-registry'
import { pipelinesApi, savedFiltersApi } from '@/lib/api'

export interface RecordTableRowProps {
  record: Record
  fields: RecordField[]
  isSelected: boolean
  onSelectRecord: (recordId: string) => void
  onEditRecord?: (record: Record) => void
  onDeleteRecord?: (recordId: string) => void
  onOpenRelatedRecord?: (targetPipelineId: string, recordId: string) => void
  pipelineId: string
  className?: string
  sharedToken?: string // For public/shared access context
}

// Helper function to format system timestamps
const formatSystemTimestamp = (timestamp: string): string => {
  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString()
}

// Simplified relation value component for table chips
const RelationChip: React.FC<{
  relationItem: string | { id: string | number; display_value: string }
  field: RecordField
  onClick: () => void
  sharedToken?: string
}> = ({ relationItem, field, onClick, sharedToken }) => {
  // Extract record ID and display value based on item type
  const recordId = typeof relationItem === 'object' ? String(relationItem.id) : String(relationItem)
  const initialDisplay = typeof relationItem === 'object' && relationItem.display_value
    ? relationItem.display_value
    : `Record #${recordId}`

  const [displayText, setDisplayText] = useState<string>(initialDisplay)
  
  useEffect(() => {
    // If we already have display value from the object, don't fetch
    if (typeof relationItem === 'object' && relationItem.display_value) {
      return
    }

    const fetchRecordName = async () => {
      try {
        // Convert RecordField to Field type for getFieldConfig
        const fieldForConfig = FieldUtilsService.convertToFieldType(field)
        
        const targetPipelineId = getFieldConfig(fieldForConfig, 'target_pipeline_id')
        const displayField = getFieldConfig(fieldForConfig, 'display_field', 'title')
        
        console.log('🔍 RelationChip Debug:', {
          fieldName: field.name,
          fieldType: field.field_type,
          fieldConfig: field.field_config,
          fieldConfigRaw: field.config, // Legacy config
          fieldForConfig,
          targetPipelineId,
          displayField,
          recordId
        })
        
        if (!targetPipelineId) {
          console.warn('🔍 No target pipeline ID found')
          return
        }
        
        // Use public API if we're in a shared context, otherwise use authenticated API
        const response = sharedToken 
          ? await savedFiltersApi.public.getRelatedRecord(sharedToken, targetPipelineId.toString(), recordId)
          : await pipelinesApi.getRecord(targetPipelineId.toString(), recordId)
        console.log('🔍 API Response:', response.data)
        console.log('🔍 API Response structure:', {
          hasData: !!response.data,
          hasDataData: !!(response.data && response.data.data),
          responseKeys: response.data ? Object.keys(response.data) : [],
          dataKeys: response.data && response.data.data ? Object.keys(response.data.data) : []
        })
        
        if (response.data) {
          let recordName = `Record #${recordId}` // Default fallback
          
          console.log('🔍 Available fields in response.data.data:', response.data.data ? Object.keys(response.data.data) : 'No data.data field')
          console.log('🔍 Looking for display field:', displayField)
          console.log('🔍 Display field value:', response.data.data ? response.data.data[displayField] : 'No data.data field')
          
          // First priority: Use the configured display field (try exact match first)
          if (displayField && response.data[displayField] !== undefined && response.data[displayField] !== null && response.data[displayField] !== '') {
            recordName = String(response.data[displayField])
            console.log('🔍 Using display field (exact):', displayField, '=', recordName)
          }
          // Try slugified version of display field (convert "Email 2" to "email_2")
          else if (displayField && response.data.data) {
            const slugifiedDisplayField = displayField.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '')
            if (response.data.data[slugifiedDisplayField] !== undefined && response.data.data[slugifiedDisplayField] !== null && response.data.data[slugifiedDisplayField] !== '') {
              recordName = String(response.data.data[slugifiedDisplayField])
              console.log('🔍 Using display field (slugified):', slugifiedDisplayField, '=', recordName)
            }
            // Try partial match - look for field that contains the display field name
            else {
              const partialMatch = Object.keys(response.data.data).find(key => {
                const keyNormalized = key.toLowerCase().replace(/_/g, ' ')
                const displayNormalized = displayField.toLowerCase()
                return keyNormalized.includes(displayNormalized) || displayNormalized.includes(keyNormalized)
              })
              if (partialMatch && response.data.data[partialMatch] !== undefined && response.data.data[partialMatch] !== null && response.data.data[partialMatch] !== '') {
                recordName = String(response.data.data[partialMatch])
                console.log('🔍 Using display field (partial match):', partialMatch, '=', recordName)
              }
            }
          }
          
          // Second priority: Try common fallback fields like title, name
          if (recordName === `Record #${recordId}` && response.data.data) {
            const fallbackFields = ['title', 'name', 'display_name', 'label', 'test']
            for (const fallbackField of fallbackFields) {
              if (response.data.data[fallbackField] !== undefined && response.data.data[fallbackField] !== null && response.data.data[fallbackField] !== '') {
                recordName = String(response.data.data[fallbackField])
                console.log('🔍 Using fallback field:', fallbackField, '=', recordName)
                break
              }
            }
          }
          
          console.log('🔍 Final record name:', recordName)
          setDisplayText(recordName)
        }
      } catch (error) {
        console.error(`Failed to load relation record ${recordId}:`, error)
        // Keep the fallback display text
      }
    }
    
    fetchRecordName()
  }, [recordId, field, relationItem])
  
  return (
    <button
      onClick={(e) => {
        e.stopPropagation()
        onClick()
      }}
      className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200 hover:bg-emerald-200 dark:hover:bg-emerald-800 cursor-pointer transition-colors"
      title="Click to view related record"
    >
      {displayText}
    </button>
  )
}

export function RecordTableRow({
  record,
  fields,
  isSelected,
  onSelectRecord,
  onEditRecord,
  onDeleteRecord,
  onOpenRelatedRecord,
  pipelineId,
  className = "",
  sharedToken
}: RecordTableRowProps) {


  const renderFieldValue = (field: RecordField, value: any) => {
    // Handle interactive fields (buttons, checkboxes, relations)
    if (FieldUtilsService.isInteractiveField(field)) {
      return renderInteractiveField(field, value)
    }

    // Handle display-only fields
    const formattedValue = FieldUtilsService.formatFieldValue(field, value)
    
    if (value === null || value === undefined || value === '') {
      return (
        <span className="text-gray-400 dark:text-gray-500 italic text-xs">
          Empty
        </span>
      )
    }

    return (
      <div className="truncate" title={String(formattedValue || '')}>
        {formattedValue}
      </div>
    )
  }

  const renderInteractiveField = (field: RecordField, value: any) => {
    if (field.field_type === 'boolean') {
      const boolValue = Boolean(value)
      return (
        <button
          onClick={(e) => {
            e.stopPropagation()
            handleFieldUpdate(field.name, !boolValue)
          }}
          className="text-gray-600 dark:text-gray-400 hover:text-primary"
        >
          {boolValue ? (
            <CheckSquare className="w-4 h-4 text-primary" />
          ) : (
            <Square className="w-4 h-4" />
          )}
        </button>
      )
    }

    if (field.field_type === 'button') {
      const buttonConfig = field.field_config || {}
      const buttonText = buttonConfig.button_text || 'Click Me'
      const buttonStyle = buttonConfig.button_style || 'primary'
      const disableAfterClick = buttonConfig.disable_after_click || false
      const requireConfirmation = buttonConfig.require_confirmation || false
      const confirmationMessage = buttonConfig.confirmation_message || 'Are you sure?'
      
      const hasBeenClicked = value && typeof value === 'object' && value.triggered === true
      const isDisabled = disableAfterClick && hasBeenClicked

      const buttonStyles = {
        primary: 'bg-blue-600 hover:bg-blue-700 text-white',
        secondary: 'bg-gray-600 hover:bg-gray-700 text-white', 
        success: 'bg-green-600 hover:bg-green-700 text-white',
        warning: 'bg-yellow-600 hover:bg-yellow-700 text-white',
        danger: 'bg-red-600 hover:bg-red-700 text-white'
      }

      return (
        <button
          onClick={(e) => handleButtonClick(e, field, buttonText, requireConfirmation, confirmationMessage, disableAfterClick, value)}
          disabled={isDisabled}
          className={`px-2 py-1 text-xs rounded ${buttonStyles[buttonStyle as keyof typeof buttonStyles]} disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          {buttonText}
        </button>
      )
    }

    if (field.field_type === 'relation') {
      if (!value || !onOpenRelatedRecord) {
        const formattedValue = FieldUtilsService.formatFieldValue(field, value)
        return formattedValue
      }

      // Extract target pipeline ID from field configuration
      const targetPipelineId = field.field_config?.target_pipeline_id || field.field_config?.target_pipeline
      
      if (!targetPipelineId) {
        const formattedValue = FieldUtilsService.formatFieldValue(field, value)
        return formattedValue
      }

      // Handle multiple records - value can be array of objects/IDs or comma-separated string
      let relationItems: any[]
      if (Array.isArray(value)) {
        // Keep objects as-is, they have {id, display_value}
        relationItems = value
      } else if (typeof value === 'string' && value.includes(',')) {
        // Split comma-separated IDs
        relationItems = value.split(',').map((id: string) => id.trim())
      } else {
        // Single value - could be object or ID
        relationItems = [value]
      }

      // Display as chips like user fields - with emerald color for relations
      return (
        <div className="flex items-center gap-1 flex-wrap">
          {relationItems.map((item: any, index: number) => {
            // Extract ID for navigation
            const itemId = typeof item === 'object' ? item.id : item
            const key = `${itemId}-${index}`

            return (
              <RelationChip
                key={key}
                relationItem={item}
                field={field}
                sharedToken={sharedToken}
                onClick={() => {
                  console.log('🔗 Relation chip clicked:', {
                    fieldName: field.name,
                    targetPipelineId: targetPipelineId.toString(),
                    recordId: itemId
                  })
                  onOpenRelatedRecord(targetPipelineId.toString(), String(itemId))
                }}
              />
            )
          })}
        </div>
      )
    }

    return FieldUtilsService.formatFieldValue(field, value)
  }

  const handleFieldUpdate = async (fieldName: string, newValue: any) => {
    try {
      await pipelinesApi.updateRecord(pipelineId, record.id, {
        data: {
          [fieldName]: newValue
        }
      })
      // Real-time system will update the UI automatically
    } catch (error) {
      console.error('Failed to update field:', error)
    }
  }

  const handleButtonClick = async (
    e: React.MouseEvent,
    field: RecordField, 
    buttonText: string,
    requireConfirmation: boolean,
    confirmationMessage: string,
    disableAfterClick: boolean,
    currentValue: any
  ) => {
    e.stopPropagation()
    
    if (requireConfirmation && !window.confirm(confirmationMessage)) {
      return
    }

    try {
      const clickTimestamp = new Date().toISOString()
      const newValue = {
        type: 'button',
        triggered: true,
        last_triggered: clickTimestamp,
        click_count: ((currentValue?.click_count) || 0) + 1,
        config: {
          ...field.field_config,
          button_text: buttonText,
          disable_after_click: disableAfterClick,
          require_confirmation: requireConfirmation,
          confirmation_message: confirmationMessage
        }
      }

      await pipelinesApi.updateRecord(pipelineId, record.id, {
        data: {
          [field.name]: newValue
        }
      })
    } catch (error) {
      console.error('Failed to update button field:', error)
    }
  }

  return (
    <tr
      className={`hover:bg-gray-50 dark:hover:bg-gray-800 ${onEditRecord ? 'cursor-pointer' : ''} ${className}`}
      onClick={() => onEditRecord && onEditRecord(record)}
    >
      {/* Selection cell */}
      <td className="px-4 py-3">
        <button
          onClick={(e) => {
            e.stopPropagation()
            onSelectRecord(record.id)
          }}
          className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
        >
          {isSelected ? (
            <CheckSquare className="w-4 h-4 text-primary" />
          ) : (
            <Square className="w-4 h-4" />
          )}
        </button>
      </td>
      
      {/* Field cells */}
      {fields.map((field) => {
        const columnWidth = FieldUtilsService.getColumnWidth(field)
        const isInteractive = FieldUtilsService.isInteractiveField(field)
        
        return (
          <td 
            key={field.name} 
            className={`${columnWidth} px-4 py-3 text-sm text-gray-900 dark:text-white`}
            onClick={(e) => {
              // Prevent row click for interactive fields
              if (isInteractive) {
                e.stopPropagation()
              }
            }}
          >
            <div className={`${field.field_type === 'textarea' || field.field_type === 'ai_field' ? 'max-h-20 overflow-hidden' : ''}`}>
              {renderFieldValue(field, record.data[field.name])}
            </div>
          </td>
        )
      })}
      
      {/* System metadata columns */}
      {/* Created At */}
      <td className="w-32 px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
        <div className="truncate" title={new Date(record.created_at).toLocaleString()}>
          {formatSystemTimestamp(record.created_at)}
        </div>
      </td>
      
      {/* Updated At */}
      <td className="w-32 px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
        <div className="truncate" title={new Date(record.updated_at).toLocaleString()}>
          {formatSystemTimestamp(record.updated_at)}
        </div>
      </td>
      
      {/* Created By */}
      <td className="w-32 px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
        <div className="truncate" title={record.created_by ? `${record.created_by.first_name} ${record.created_by.last_name}` : 'System'}>
          {record.created_by ? `${record.created_by.first_name} ${record.created_by.last_name}` : 'System'}
        </div>
      </td>
      
      {/* Actions cell */}
      <td className="px-4 py-3">
        <div className="flex items-center space-x-2">
          <button
            onClick={(e) => {
              e.stopPropagation()
              if (onEditRecord) onEditRecord(record)
            }}
            className="text-gray-400 hover:text-blue-600 dark:hover:text-blue-400"
            title="Edit record"
          >
            <Edit className="w-4 h-4" />
          </button>
          
          <button
            onClick={(e) => {
              e.stopPropagation()
              if (onEditRecord) onEditRecord(record)
            }}
            className="text-gray-400 hover:text-green-600 dark:hover:text-green-400"
            title="View record"
          >
            <Eye className="w-4 h-4" />
          </button>
          
          {onDeleteRecord && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                onDeleteRecord(record.id)
              }}
              className="text-gray-400 hover:text-red-600 dark:hover:text-red-400"
              title="Delete record"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
        </div>
      </td>
    </tr>
  )
}