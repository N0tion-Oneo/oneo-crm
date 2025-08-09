'use client'

import {
  Checkbox,
  Input,
  Label,
  ArrayManager
} from '@/components/ui'
import { HelpTooltipWrapper } from '../config-components/HelpTooltipWrapper'
import { AlertCircle, CheckCircle, AlertTriangle } from 'lucide-react'

interface SelectFieldConfigProps {
  config: Record<string, any>
  onChange: (key: string, value: any) => void
  fieldType: 'select' | 'multiselect'
}

interface SelectOption {
  id: string
  label: string
  value: string
}

export function SelectFieldConfig({
  config,
  onChange,
  fieldType
}: SelectFieldConfigProps) {
  const options = config.options || []
  
  // Validation
  const hasEmptyOptions = options.some((opt: any) => !opt.label?.trim() || !opt.value?.trim())
  const duplicateValues = options.filter((opt: any, index: number) => 
    options.findIndex((o: any) => o.value === opt.value) !== index && opt.value?.trim()
  )
  const duplicateLabels = options.filter((opt: any, index: number) => 
    options.findIndex((o: any) => o.label === opt.label) !== index && opt.label?.trim()
  )

  const handleAddOption = (option: SelectOption) => {
    const newOptions = [...options, {
      value: option.value || option.label.toLowerCase().replace(/[^a-z0-9]/g, '_'),
      label: option.label
    }]
    onChange('options', newOptions)
  }

  const handleRemoveOption = (index: number) => {
    const newOptions = options.filter((_: any, i: number) => i !== index)
    onChange('options', newOptions)
  }

  const handleUpdateOption = (index: number, updatedOption: SelectOption) => {
    const newOptions = [...options]
    const newLabel = updatedOption.label
    // Auto-generate value from label if value is empty or matches old label
    const oldOption = options[index]
    const shouldAutoGenerate = !oldOption?.value || oldOption.value === (oldOption?.label || '').toLowerCase().replace(/[^a-z0-9]/g, '_')
    
    newOptions[index] = {
      ...updatedOption,
      value: shouldAutoGenerate ? newLabel.toLowerCase().replace(/[^a-z0-9]/g, '_') : updatedOption.value
    }
    onChange('options', newOptions)
  }

  const getValidationStatus = () => {
    if (options.length === 0) {
      return { type: 'warning', message: 'Add at least one option for users to select from' }
    }

    if (hasEmptyOptions || duplicateValues.length > 0 || duplicateLabels.length > 0) {
      const messages = []
      if (hasEmptyOptions) messages.push('Some options have empty labels or values')
      if (duplicateValues.length > 0) messages.push('Duplicate values found')
      if (duplicateLabels.length > 0) messages.push('Duplicate labels found')
      return { type: 'error', message: messages.join('. ') }
    }

    return { type: 'success', message: `${options.length} valid option${options.length !== 1 ? 's' : ''} configured` }
  }

  const validationStatus = getValidationStatus()

  return (
    <div className="space-y-6">
      {/* Options Management */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <HelpTooltipWrapper helpText="Define the options users can choose from. Values are used internally, labels are shown to users.">
            <Label className="text-base font-medium text-gray-900 dark:text-white">
              Options * 
              <span className="text-xs text-muted-foreground ml-2 font-normal">
                ({options.length} option{options.length !== 1 ? 's' : ''})
              </span>
            </Label>
          </HelpTooltipWrapper>
        </div>

        {/* Custom Options Management since ArrayManager doesn't support dual inputs */}
        <div className="space-y-2">
          {options.map((option: any, index: number) => (
            <div key={index} className="flex items-center space-x-2">
              <div className="flex-1">
                <Input
                  type="text"
                  placeholder="Label (what users see)"
                  value={option.label || ''}
                  onChange={(e) => {
                    const newLabel = e.target.value
                    const oldOption = options[index]
                    const shouldAutoGenerate = !oldOption?.value || oldOption.value === (oldOption?.label || '').toLowerCase().replace(/[^a-z0-9]/g, '_')
                    
                    const newOptions = [...options]
                    newOptions[index] = {
                      ...option,
                      label: newLabel,
                      value: shouldAutoGenerate ? newLabel.toLowerCase().replace(/[^a-z0-9]/g, '_') : option.value
                    }
                    onChange('options', newOptions)
                  }}
                />
              </div>
              <div className="flex-1">
                <Input
                  type="text"
                  placeholder="Value (internal)"
                  value={option.value || ''}
                  onChange={(e) => {
                    const newOptions = [...options]
                    newOptions[index] = { ...option, value: e.target.value }
                    onChange('options', newOptions)
                  }}
                />
              </div>
              <button
                onClick={() => handleRemoveOption(index)}
                className="p-2 text-destructive hover:text-destructive/80 transition-colors"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          ))}
          
          {/* Add new option button */}
          <button
            onClick={() => {
              const newOptions = [...options, { value: '', label: '' }]
              onChange('options', newOptions)
            }}
            className="w-full px-3 py-2 border-2 border-dashed border-muted-foreground/25 rounded-md text-muted-foreground hover:border-primary hover:text-primary transition-colors flex items-center justify-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
            </svg>
            <span>Add new option</span>
          </button>
        </div>

        {/* Validation Status */}
        <div className={`p-3 rounded-md border ${
          validationStatus.type === 'success' ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800' :
          validationStatus.type === 'warning' ? 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800' :
          'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
        }`}>
          <div className="flex items-center gap-2">
            {validationStatus.type === 'success' && <CheckCircle className="h-4 w-4 text-green-600" />}
            {validationStatus.type === 'warning' && <AlertTriangle className="h-4 w-4 text-yellow-600" />}
            {validationStatus.type === 'error' && <AlertCircle className="h-4 w-4 text-red-600" />}
            <span className={`text-xs ${
              validationStatus.type === 'success' ? 'text-green-700 dark:text-green-300' :
              validationStatus.type === 'warning' ? 'text-yellow-700 dark:text-yellow-300' :
              'text-red-700 dark:text-red-300'
            }`}>
              {validationStatus.message}
            </span>
          </div>
        </div>
      </div>

      {/* Field Type Info */}
      <div className={`p-3 rounded-md border ${
        fieldType === 'select' 
          ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800'
          : 'bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-800'
      }`}>
        <div className="flex items-center">
          <div className="w-2 h-2 rounded-full mr-2 bg-primary"></div>
          <span className={`text-sm font-medium ${
            fieldType === 'select' 
              ? 'text-blue-800 dark:text-blue-200'
              : 'text-purple-800 dark:text-purple-200'
          }`}>
            {fieldType === 'select' ? 'Single Selection' : 'Multiple Selection'}
          </span>
        </div>
        <p className={`text-xs mt-1 ${
          fieldType === 'select'
            ? 'text-blue-600 dark:text-blue-300'
            : 'text-purple-600 dark:text-purple-300'
        }`}>
          {fieldType === 'select' 
            ? 'Users can select only one option from this dropdown'
            : 'Users can select multiple options from this list'
          }
        </p>
      </div>

      {/* Advanced Options */}
      <div className="space-y-3">
        <Label className="text-base font-medium text-gray-900 dark:text-white">Advanced Options</Label>
        
        <div className="flex items-center space-x-2">
          <Checkbox
            id="allow-custom"
            checked={config.allow_custom || false}
            onCheckedChange={(checked) => onChange('allow_custom', checked)}
          />
          <HelpTooltipWrapper helpText="Allow users to enter custom values not in the predefined options list">
            <Label htmlFor="allow-custom" className="text-sm font-normal text-gray-700 dark:text-gray-300">
              Allow custom values
            </Label>
          </HelpTooltipWrapper>
        </div>

        {fieldType === 'multiselect' && (
          <>
            <div className="flex items-center space-x-2">
              <Checkbox
                id="allow-duplicate-values"
                checked={config.allow_duplicates || false}
                onCheckedChange={(checked) => onChange('allow_duplicates', checked)}
              />
              <HelpTooltipWrapper helpText="Allow the same value to be selected multiple times">
                <Label htmlFor="allow-duplicate-values" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                  Allow duplicate values
                </Label>
              </HelpTooltipWrapper>
            </div>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="maintain-order"
                checked={config.maintain_order !== false}
                onCheckedChange={(checked) => onChange('maintain_order', checked)}
              />
              <HelpTooltipWrapper helpText="Maintain the order in which options were selected">
                <Label htmlFor="maintain-order" className="text-sm font-normal text-gray-700 dark:text-gray-300">
                  Maintain selection order
                </Label>
              </HelpTooltipWrapper>
            </div>
          </>
        )}
      </div>

      {/* Configuration Summary */}
      {options.length > 0 && validationStatus.type === 'success' && (
        <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
          <div className="text-sm text-gray-700 dark:text-gray-300">
            <p className="font-medium text-blue-800 dark:text-blue-200 mb-1">
              {fieldType === 'select' ? 'Select' : 'Multiselect'} Field Configuration
            </p>
            <div className="text-blue-700 dark:text-blue-300 space-y-1">
              <div>• {options.length} option{options.length !== 1 ? 's' : ''} available</div>
              {config.allow_custom && <div>• Custom values allowed</div>}
              {fieldType === 'multiselect' && config.allow_duplicates && <div>• Duplicate values allowed</div>}
              {fieldType === 'multiselect' && config.maintain_order !== false && <div>• Selection order maintained</div>}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}