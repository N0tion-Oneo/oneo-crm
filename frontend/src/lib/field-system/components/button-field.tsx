import React from 'react'
import { FieldComponent, FieldRenderProps, ValidationResult, Field } from '../types'
import { getFieldConfig } from '../field-registry'

export const ButtonFieldComponent: FieldComponent = {
  renderInput: (props: FieldRenderProps) => {
    const { field, value, onChange, disabled, error, className } = props
    
    const buttonText = getFieldConfig(field, 'button_text', 'Click Me')
    const buttonStyle = getFieldConfig(field, 'button_style', 'primary')
    const buttonSize = getFieldConfig(field, 'button_size', 'medium')
    const requireConfirmation = getFieldConfig(field, 'require_confirmation', false)
    const confirmationMessage = getFieldConfig(field, 'confirmation_message', 'Are you sure?')
    const disableAfterClick = getFieldConfig(field, 'disable_after_click', false)
    const workflowId = getFieldConfig(field, 'workflow_id')
    
    // Track if button has been clicked (for disable_after_click)
    const hasBeenClicked = value === true
    
    const buttonStyles = {
      primary: 'bg-blue-600 hover:bg-blue-700 text-white shadow-sm',
      secondary: 'bg-gray-600 hover:bg-gray-700 text-white shadow-sm',
      success: 'bg-green-600 hover:bg-green-700 text-white shadow-sm',
      warning: 'bg-yellow-600 hover:bg-yellow-700 text-white shadow-sm',
      danger: 'bg-red-600 hover:bg-red-700 text-white shadow-sm'
    }
    
    const buttonSizes = {
      small: 'px-3 py-1.5 text-sm',
      medium: 'px-4 py-2',
      large: 'px-6 py-3 text-lg'
    }
    
    const isDisabled = disabled || (disableAfterClick && hasBeenClicked)
    
    const handleClick = () => {
      if (requireConfirmation) {
        if (!window.confirm(confirmationMessage)) {
          return
        }
      }
      
      // Mark as clicked if disable_after_click is enabled
      if (disableAfterClick) {
        onChange(true)
      }
      
      // In a real implementation, this would trigger the workflow
      if (workflowId) {
        console.log(`Triggering workflow: ${workflowId}`)
        // TODO: Implement workflow trigger
      } else {
        console.log(`Button clicked: ${buttonText}`)
      }
    }

    return (
      <div className={className}>
        <button
          type="button"
          onClick={handleClick}
          disabled={isDisabled}
          className={`
            rounded-lg transition-all duration-200 font-medium focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500
            ${buttonStyles[buttonStyle as keyof typeof buttonStyles] || buttonStyles.primary}
            ${buttonSizes[buttonSize as keyof typeof buttonSizes] || buttonSizes.medium}
            ${isDisabled 
              ? 'opacity-50 cursor-not-allowed' 
              : 'hover:shadow-md transform hover:-translate-y-0.5'
            }
          `}
        >
          {buttonText}
        </button>
        
        {disableAfterClick && hasBeenClicked && (
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            Button has been clicked and is now disabled
          </p>
        )}
        
        {workflowId && (
          <p className="mt-1 text-xs text-blue-600 dark:text-blue-400">
            Triggers workflow: {workflowId}
          </p>
        )}
        
        {error && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error}</p>
        )}
      </div>
    )
  },

  formatValue: (value: any, field: Field, context?: string) => {
    const buttonText = getFieldConfig(field, 'button_text', 'Click Me')
    const buttonStyle = getFieldConfig(field, 'button_style', 'primary')
    const disableAfterClick = getFieldConfig(field, 'disable_after_click', false)
    const hasBeenClicked = value === true
    
    if (context === 'table') {
      const statusText = disableAfterClick && hasBeenClicked ? ' (clicked)' : ''
      return (
        <span className="text-sm text-gray-600 dark:text-gray-400 font-mono">
          {buttonText}{statusText}
        </span>
      )
    }
    
    if (context === 'detail') {
      const buttonStyles = {
        primary: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
        secondary: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
        success: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
        warning: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
        danger: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
      }
      
      return (
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${buttonStyles[buttonStyle as keyof typeof buttonStyles] || buttonStyles.primary}`}>
          {buttonText}
          {disableAfterClick && hasBeenClicked && ' (clicked)'}
        </span>
      )
    }
    
    return buttonText
  },

  validate: (value: any, field: Field): ValidationResult => {
    // Button fields don't typically need validation
    // They're action triggers, not data storage
    return { isValid: true }
  },

  getDefaultValue: (field: Field) => {
    // Button fields typically don't have default values
    // Unless disable_after_click is enabled, then false indicates not clicked
    const disableAfterClick = getFieldConfig(field, 'disable_after_click', false)
    return disableAfterClick ? false : null
  },

  isEmpty: (value: any) => {
    // Button fields are never considered "empty" since they're action triggers
    return false
  }
}