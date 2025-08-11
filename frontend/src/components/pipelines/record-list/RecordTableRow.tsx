// RecordTableRow - Individual record row with field rendering
import React from 'react'
import { CheckSquare, Square, Edit, Eye, Trash2 } from 'lucide-react'
import { Record, RecordField } from '@/types/records'
import { FieldUtilsService } from '@/services/records'
import { FieldResolver } from '@/lib/field-system/field-registry'
import { pipelinesApi } from '@/lib/api'

export interface RecordTableRowProps {
  record: Record
  fields: RecordField[]
  isSelected: boolean
  onSelectRecord: (recordId: string) => void
  onEditRecord: (record: Record) => void
  onDeleteRecord?: (recordId: string) => void
  pipelineId: string
  className?: string
}

export function RecordTableRow({
  record,
  fields,
  isSelected,
  onSelectRecord,
  onEditRecord,
  onDeleteRecord,
  pipelineId,
  className = ""
}: RecordTableRowProps) {

  const renderFieldValue = (field: RecordField, value: any) => {
    // Handle interactive fields (buttons, checkboxes)
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
      className={`hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer ${className}`}
      onClick={() => onEditRecord(record)}
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
      
      {/* Actions cell */}
      <td className="px-4 py-3">
        <div className="flex items-center space-x-2">
          <button
            onClick={(e) => {
              e.stopPropagation()
              onEditRecord(record)
            }}
            className="text-gray-400 hover:text-blue-600 dark:hover:text-blue-400"
            title="Edit record"
          >
            <Edit className="w-4 h-4" />
          </button>
          
          <button
            onClick={(e) => {
              e.stopPropagation()
              onEditRecord(record)
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