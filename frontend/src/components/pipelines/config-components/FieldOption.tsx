'use client'

import {
  Checkbox,
  Input,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Textarea,
  RadioGroup,
  RadioGroupItem,
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger
} from '@/components/ui'
import { HelpCircle } from 'lucide-react'

interface FieldOptionProps {
  label: string
  description?: string
  helpText?: string
  type: 'text' | 'textarea' | 'number' | 'checkbox' | 'select' | 'radio'
  value: any
  onChange: (value: any) => void
  options?: { label: string; value: string | number }[]
  placeholder?: string
  disabled?: boolean
  required?: boolean
}

export function FieldOption({
  label,
  description,
  helpText,
  type,
  value,
  onChange,
  options = [],
  placeholder,
  disabled = false,
  required = false
}: FieldOptionProps) {
  const renderInput = () => {
    const id = label.toLowerCase().replace(/\s+/g, '-')

    switch (type) {
      case 'text':
        return (
          <Input
            id={id}
            type="text"
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            disabled={disabled}
            required={required}
          />
        )

      case 'textarea':
        return (
          <Textarea
            id={id}
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            disabled={disabled}
            required={required}
            rows={3}
          />
        )

      case 'number':
        return (
          <Input
            id={id}
            type="number"
            value={value || ''}
            onChange={(e) => onChange(e.target.value ? parseFloat(e.target.value) : null)}
            placeholder={placeholder}
            disabled={disabled}
            required={required}
          />
        )

      case 'checkbox':
        return (
          <div className="flex items-center space-x-2">
            <Checkbox
              id={id}
              checked={value || false}
              onCheckedChange={onChange}
              disabled={disabled}
            />
            <Label htmlFor={id} className="text-sm font-normal text-gray-700 dark:text-gray-300">
              {description || label}
            </Label>
          </div>
        )

      case 'select':
        return (
          <Select
            value={value?.toString() || ''}
            onValueChange={(selectedValue) => {
              // Try to parse as number if the original option was a number
              const option = options.find(opt => opt.value.toString() === selectedValue)
              const parsedValue = option && typeof option.value === 'number' 
                ? option.value 
                : selectedValue
              onChange(parsedValue)
            }}
            disabled={disabled}
          >
            <SelectTrigger>
              <SelectValue placeholder={placeholder || `Select ${label.toLowerCase()}...`} />
            </SelectTrigger>
            <SelectContent>
              {options.map((option) => (
                <SelectItem key={option.value.toString()} value={option.value.toString()}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )

      case 'radio':
        return (
          <RadioGroup
            value={value?.toString() || ''}
            onValueChange={(selectedValue) => {
              // Try to parse as number if the original option was a number
              const option = options.find(opt => opt.value.toString() === selectedValue)
              const parsedValue = option && typeof option.value === 'number' 
                ? option.value 
                : selectedValue
              onChange(parsedValue)
            }}
            disabled={disabled}
          >
            {options.map((option) => (
              <div key={option.value.toString()} className="flex items-center space-x-2">
                <RadioGroupItem value={option.value.toString()} id={`${id}-${option.value}`} />
                <Label htmlFor={`${id}-${option.value}`} className="text-sm font-normal text-gray-700 dark:text-gray-300">
                  {option.label}
                </Label>
              </div>
            ))}
          </RadioGroup>
        )

      default:
        return null
    }
  }

  return (
    <TooltipProvider>
      <div className="space-y-2">
        {type !== 'checkbox' && (
          <div className="flex items-center gap-2">
            <Label 
              htmlFor={label.toLowerCase().replace(/\s+/g, '-')} 
              className="text-sm font-medium"
            >
              {label}
              {required && <span className="text-destructive ml-1">*</span>}
            </Label>
            {helpText && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <HelpCircle className="h-4 w-4 text-muted-foreground" />
                </TooltipTrigger>
                <TooltipContent>
                  <p className="max-w-xs">{helpText}</p>
                </TooltipContent>
              </Tooltip>
            )}
          </div>
        )}

        {renderInput()}

        {description && type !== 'checkbox' && (
          <p className="text-xs text-muted-foreground">{description}</p>
        )}
      </div>
    </TooltipProvider>
  )
}